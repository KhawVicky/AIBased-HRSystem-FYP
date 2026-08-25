"""FastAPI adapter for the literal frozen notebook pipeline."""

from __future__ import annotations

import json
import hashlib
import logging
import time
import uuid
from typing import Any

from . import frozen_pipeline
from .model_output import normalise_model_output
from .multisentence_grounding import MultiSentenceGroundingAdapter
from .name_validation import CriterionNameValidationAdapter
from .enhanced_weighting import apply_enhanced_weights
from .config import deployment_metadata
from .criterion_text import apply_deterministic_criterion_texts
from .source_accounting import (
    build_source_accounting,
    build_source_records,
)
from .explicit_requirement_recovery import (
    collapse_explicit_requirement_duplicates,
    consolidate_broad_specific_experience,
    recover_explicit_requirements,
)
from .extraction_prompt import (
    build_extraction_messages,
    build_extraction_retry_messages,
    build_semantic_consolidation_messages,
)
from .extraction_schema import (
    SOURCE_ACCOUNTING_ERROR_PREFIX,
    normalise_extraction_output,
)
from .hard_requirements import extract_hard_requirements
from .role_context import build_role_context
from .evidence_safety import (
    apply_semantic_consolidation_plan,
    consolidate_adjacent_supply_operations,
    consolidate_grounded_workflow_relations,
    decompose_incoherent_multisource_criteria,
    is_broad_overview_source,
    safe_can_merge_group,
    safe_merge_duplicate_criteria,
    same_capability_with_object_alignment,
    final_evidence_safety_pass,
    is_generic_duty_safe,
)


logger = logging.getLogger(__name__)


def _assign_recovery_criterion_ids(
    existing: list[dict[str, Any]],
    recovered: list[dict[str, Any]],
) -> None:
    """Give recovered criteria unique IDs before semantic consolidation."""

    used = {
        str(item.get("criterionId", "")).strip().casefold()
        for item in existing
        if str(item.get("criterionId", "")).strip()
    }
    next_index = len(existing) + 1
    for criterion in recovered:
        criterion_id = str(criterion.get("criterionId", "")).strip()
        if criterion_id and criterion_id.casefold() not in used:
            used.add(criterion_id.casefold())
            continue
        candidate = f"criterion-{next_index}"
        while candidate.casefold() in used:
            next_index += 1
            candidate = f"criterion-{next_index}"
        criterion["criterionId"] = candidate
        used.add(candidate.casefold())
        next_index += 1


def _source_parts_for_trace(criterion: dict[str, Any]) -> list[str]:
    source_refs = criterion.get("sourceRefs")
    if isinstance(source_refs, list):
        return [str(part).strip() for part in source_refs if str(part).strip()]
    source_texts = criterion.get("sourceTexts")
    if isinstance(source_texts, list):
        return [str(part).strip() for part in source_texts if str(part).strip()]
    return [
        part.strip()
        for part in str(criterion.get("sourceText", "")).split("|")
        if part.strip()
    ]


def _criterion_trace_snapshot(
    criteria: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return non-content diagnostics suitable for logs and audit output."""

    snapshot: list[dict[str, Any]] = []
    for item in criteria:
        parts = _source_parts_for_trace(item)
        snapshot.append(
            {
                "criterionId": item.get("criterionId") or item.get("id"),
                "type": item.get("type"),
                "name": item.get("name"),
                "sourceIds": list(item.get("sourceIds", [])),
                "sourceCriterionIds": list(item.get("sourceCriterionIds", [])),
                "mergedFromIds": list(item.get("mergedFromIds", [])),
                "sourceCount": len(parts),
                "sourceTextHashes": [
                    hashlib.sha256(part.encode("utf-8")).hexdigest()[:12]
                    for part in parts
                ],
                "groundingScores": list(item.get("groundingScores", [])),
                "suggestedWeight": item.get("suggestedWeight"),
            }
        )
    return snapshot


def _is_broad_overview_source(source_text: str) -> bool:
    """Identify a wide scope-list sentence used as shared context.

    This is intentionally structural rather than job-specific: a sentence
    with many comma-separated areas and multiple conjunctions usually
    summarises a role's scope instead of defining one independently scorable
    capability.
    """

    return is_broad_overview_source(source_text)


def _without_shared_broad_sources(
    criterion: dict[str, Any],
    shared_sources: set[str],
) -> dict[str, Any]:
    parts = [
        part.strip()
        for part in str(criterion.get("sourceText", "")).split("|")
        if part.strip() and part.strip() not in shared_sources
    ]
    copy = dict(criterion)
    copy["sourceText"] = " | ".join(parts)
    return copy


def _same_capability_without_broad_context(
    original_same: Any,
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    """Prevent a shared overview sentence from merging distinct criteria."""

    left_sources = {
        part.strip()
        for part in str(left.get("sourceText", "")).split("|")
        if part.strip()
    }
    right_sources = {
        part.strip()
        for part in str(right.get("sourceText", "")).split("|")
        if part.strip()
    }
    broad_sources = {
        source
        for source in left_sources | right_sources
        if _is_broad_overview_source(source)
    }
    if not broad_sources:
        return original_same(left, right)

    left_without_context = _without_shared_broad_sources(
        left,
        broad_sources,
    )
    right_without_context = _without_shared_broad_sources(
        right,
        broad_sources,
    )
    if not left_without_context["sourceText"] or not right_without_context["sourceText"]:
        return False
    return original_same(left_without_context, right_without_context)


def _same_capability_with_broad_context_guard(
    original_same: Any,
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    """Run object/domain matching only on specific evidence when available."""

    left_sources = {
        part.strip()
        for part in str(left.get("sourceText", "")).split("|")
        if part.strip()
    }
    right_sources = {
        part.strip()
        for part in str(right.get("sourceText", "")).split("|")
        if part.strip()
    }
    broad_sources = {
        source
        for source in left_sources | right_sources
        if _is_broad_overview_source(source)
    }
    if broad_sources:
        left = _without_shared_broad_sources(left, broad_sources)
        right = _without_shared_broad_sources(right, broad_sources)
        if not left["sourceText"] or not right["sourceText"]:
            return False
    return same_capability_with_object_alignment(original_same, left, right)


def _restore_merged_grounding_metadata(
    criteria: list[dict[str, Any]],
    section_diagnostics: dict[str, Any],
) -> None:
    """Restore per-source IDs and scores after frozen job-level merging.

    The frozen finalisation step can merge criteria before the API adapter's
    multi-sentence metadata restoration runs. Rebuild the metadata from the
    section grounding diagnostics so merged sourceText remains aligned with
    sourceIds and groundingScores.
    """

    metadata_by_criterion_id: dict[str, list[tuple[str, Any]]] = {}
    for section_name, diagnostics in section_diagnostics.items():
        for match in diagnostics.get("groundingMatches", []):
            criterion_index = match.get("criterionIndex")
            if not isinstance(criterion_index, int):
                continue
            criterion_id = f"{section_name}-criterion-{criterion_index}"
            matched_texts = match.get("matchedSourceTexts")
            if not isinstance(matched_texts, list) or not matched_texts:
                grounded = match.get("groundedSourceText")
                matched_texts = [grounded] if grounded else []
            source_ids = match.get("sourceIds")
            if not isinstance(source_ids, list) or len(source_ids) != len(matched_texts):
                source_ids = [
                    f"{section_name}-{criterion_index + offset}"
                    for offset in range(len(matched_texts))
                ]
            scores = match.get("groundingScores")
            if not isinstance(scores, list) or len(scores) != len(matched_texts):
                score = match.get("score", 0.0)
                scores = [score for _ in matched_texts]
            metadata_by_criterion_id[criterion_id] = [
                (str(source_id), score)
                for source_id, score in zip(source_ids, scores, strict=True)
            ]

    for criterion in criteria:
        parts = [
            part.strip()
            for part in str(criterion.get("sourceText", "")).split("|")
            if part.strip()
        ]
        if not parts:
            continue
        current_ids = criterion.get("sourceIds")
        current_scores = criterion.get("groundingScores")
        if (
            isinstance(current_ids, list)
            and isinstance(current_scores, list)
            and len(current_ids) == len(parts)
            and len(current_scores) == len(parts)
        ):
            continue

        candidates: dict[str, tuple[str, Any]] = {}
        for criterion_id in criterion.get("sourceCriterionIds", []):
            for source_id, score in metadata_by_criterion_id.get(
                str(criterion_id), []
            ):
                candidates.setdefault(source_id, (source_id, score))
        if len(candidates) < len(parts):
            continue

        aligned: list[tuple[str, Any]] = []
        for index, part in enumerate(parts, start=1):
            source_id = f"responsibilities-{index}"
            if source_id in candidates:
                aligned.append(candidates[source_id])
                continue
            source_id = f"requirements-{index}"
            if source_id in candidates:
                aligned.append(candidates[source_id])
                continue
            aligned = []
            break
        if len(aligned) == len(parts):
            criterion["sourceIds"] = [item[0] for item in aligned]
            criterion["groundingScores"] = [item[1] for item in aligned]


def _filtered_job_sources(
    values: list[Any],
    generic_duty_detector: Any,
    frozen_module: Any,
) -> list[str]:
    """Prepare source sentences using the same boundary as the frozen parser."""

    result: list[str] = []
    for value in values:
        cleaned = frozen_module.normalise_text(value)
        if cleaned and not generic_duty_detector(cleaned):
            result.append(cleaned)
    return result


def _restore_live_source_metadata(
    criteria: list[dict[str, Any]],
    job: dict[str, Any],
    generic_duty_detector: Any,
    frozen_module: Any,
) -> None:
    """Restore API source IDs to the original responsibility/requirement lists.

    The frozen validator receives a single combined source list for the live
    extraction response. This pass converts those temporary grounding IDs back
    to the public section-specific IDs without changing the grounded evidence.
    """

    source_locations: list[tuple[str, int, str]] = []
    for section_name, key in (
        ("responsibilities", "responsibilities"),
        ("requirements", "requirements"),
        ("qualifications", "qualifications"),
    ):
        position = 0
        for value in job.get(key, []):
            cleaned = frozen_module.normalise_text(value)
            if not cleaned or generic_duty_detector(cleaned):
                continue
            position += 1
            source_locations.append((section_name, position, cleaned))

    used_locations: set[tuple[str, int]] = set()
    for criterion in criteria:
        parts = [
            part.strip()
            for part in str(criterion.get("sourceText", "")).split("|")
            if part.strip()
        ]
        if not parts:
            continue

        old_scores = criterion.get("groundingScores")
        if not isinstance(old_scores, list):
            old_scores = []
        old_score_by_part = {
            part: old_scores[index]
            for index, part in enumerate(parts)
            if index < len(old_scores)
        }
        source_ids: list[str] = []
        grounding_scores: list[float] = []
        restored_parts: list[str] = []
        local_used: set[tuple[str, int]] = set()
        for part in parts:
            cleaned_part = frozen_module.normalise_text(part)
            match = next(
                (
                    location
                    for location in source_locations
                    if (location[0], location[1]) not in used_locations
                    and (location[0], location[1]) not in local_used
                    and (
                        location[2].casefold() == cleaned_part.casefold()
                        or frozen_module.comparable_text(location[2])
                        == frozen_module.comparable_text(cleaned_part)
                    )
                ),
                None,
            )
            if match is None:
                # A criterion can legitimately reuse one JD sentence. Allow a
                # second lookup without consuming the global location twice.
                match = next(
                    (
                        location
                        for location in source_locations
                        if location[2].casefold() == cleaned_part.casefold()
                        or frozen_module.comparable_text(location[2])
                        == frozen_module.comparable_text(cleaned_part)
                    ),
                    None,
                )
            if match is None:
                continue
            location_key = (match[0], match[1])
            local_used.add(location_key)
            used_locations.add(location_key)
            source_ids.append(f"{match[0]}-{match[1]}")
            score = old_score_by_part.get(part, 1.0)
            try:
                grounding_scores.append(round(float(score), 4))
            except (TypeError, ValueError):
                grounding_scores.append(1.0)
            restored_parts.append(match[2])

        if len(restored_parts) != len(parts):
            # Preserve the frozen output if a future grounding representation
            # cannot be mapped back to a section-specific source.
            continue
        criterion["sourceText"] = " | ".join(restored_parts)
        criterion["sourceIds"] = source_ids
        criterion["groundingScores"] = grounding_scores


def _importance_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 2)


def _restore_live_importance(
    criteria: list[dict[str, Any]],
    importance_by_criterion_id: dict[str, str],
) -> None:
    """Carry Qwen's bounded importance signal through frozen merging."""

    for criterion in criteria:
        values = [
            importance_by_criterion_id.get(str(source_id), "medium")
            for source_id in criterion.get("sourceCriterionIds", [])
        ]
        criterion["importance"] = max(values, key=_importance_rank) if values else "medium"


def _restore_lineage_metadata(criteria: list[dict[str, Any]]) -> None:
    """Ensure every final criterion has explicit, non-empty merge lineage."""

    for criterion in criteria:
        existing = criterion.get("mergedFromIds")
        if isinstance(existing, list):
            cleaned = list(
                dict.fromkeys(
                    str(value).strip()
                    for value in existing
                    if str(value).strip()
                )
            )
            if cleaned:
                criterion["mergedFromIds"] = cleaned
                continue
        criterion_id = str(criterion.get("criterionId", "")).strip()
        if criterion_id:
            criterion["mergedFromIds"] = [criterion_id]


class CriteriaPipeline:
    """Inject API dependencies, then call the notebook's exact entrypoint."""

    def __init__(self, loader: Any) -> None:
        self.loader = loader

    def _configure_frozen_runtime(self) -> None:
        frozen_pipeline.model = self.loader.model
        frozen_pipeline.tokenizer = self.loader.tokenizer
        frozen_pipeline.MAX_NEW_TOKENS = self.loader.config.max_new_tokens

    @staticmethod
    def _mock_section_output(
        _job: dict[str, Any], _section: str, texts: list[str]
    ) -> str:
        if not texts:
            return '{"criteria": []}'
        return json.dumps(
            {
                "criteria": [
                    {
                        "type": "relevant_skill",
                        # The frozen validator requires all name terms to be
                        # grounded. The mock therefore uses its supplied
                        # evidence rather than inventing a placeholder label.
                        "name": texts[0],
                        "sourceText": texts[0],
                    }
                ]
            }
        )

    @staticmethod
    def _mock_consolidation_output(criteria: list[dict[str, Any]]) -> str:
        # Valid frozen consolidation shape retaining every input criterion once.
        return json.dumps(
            {
                "groups": [
                    {
                        "type": item["type"],
                        "name": item["name"],
                        "memberIds": [item["id"]],
                    }
                    for item in criteria
                ]
            }
        )

    def generate(self, job: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        """Run the frozen JD pipeline while recording safe stage-level trace metadata."""

        request_id = request_id or str(uuid.uuid4())
        started = time.perf_counter()
        debug_trace: list[dict[str, Any]] = []

        def record_stage(
            stage: str,
            criteria: list[dict[str, Any]] | None = None,
            **details: Any,
        ) -> None:
            snapshot = _criterion_trace_snapshot(criteria or [])
            event = {
                "stage": stage,
                "criteriaCount": len(snapshot),
                "criteria": snapshot,
                **details,
            }
            debug_trace.append(event)
            logger.info(
                "criteria_stage request_id=%s stage=%s criteria_count=%d names=%s",
                request_id,
                stage,
                len(snapshot),
                [item.get("name") for item in snapshot],
            )

        self._configure_frozen_runtime()

        use_enhanced_extraction = (
            not bool(getattr(self.loader.config, "mock_llm", False))
            and not hasattr(self.loader, "raw_output_generator")
        )
        original_model_generator = frozen_pipeline.generate_model_output
        original_section_generator = frozen_pipeline.generate_section_raw_output
        original_retry_generator = frozen_pipeline.generate_json_retry_output
        original_consolidation_generator = frozen_pipeline.generate_consolidation_raw_output
        original_validate = frozen_pipeline.validate_section_output
        original_find_grounded_source = frozen_pipeline.find_grounded_source
        original_name_detector = frozen_pipeline.criterion_name_unsupported_tokens
        original_same_capability = (
            frozen_pipeline.same_independently_scorable_capability
        )
        original_merge_duplicate = frozen_pipeline.merge_duplicate_criteria
        original_can_merge_group = frozen_pipeline.can_merge_criteria_group
        original_is_generic_duty = frozen_pipeline.is_generic_duty
        transport_records: dict[str, dict[str, Any]] = {}
        generic_duty_detector = lambda text: is_generic_duty_safe(
            text, frozen_detector=original_is_generic_duty
        )
        source_records = build_source_records(job)
        complete_source_lookup = {
            item.source_ref: item.source_text for item in source_records
        }
        hard_requirements = extract_hard_requirements(job, source_records)
        complete_responsibilities = _filtered_job_sources(
            list(job.get("responsibilities", [])),
            generic_duty_detector,
            frozen_pipeline,
        )
        complete_requirements = _filtered_job_sources(
            list(job.get("requirements", [])),
            generic_duty_detector,
            frozen_pipeline,
        )
        complete_qualifications = _filtered_job_sources(
            list(job.get("qualifications", [])),
            generic_duty_detector,
            frozen_pipeline,
        )
        complete_source_texts = list(
            dict.fromkeys(
                complete_responsibilities
                + complete_requirements
                + complete_qualifications
            )
        )
        # Semantic formation sees the complete source set. Generic boilerplate
        # remains available for source accounting, while the frozen fallback
        # still uses its deterministic grounding safeguard.
        formation_source_lookup = dict(complete_source_lookup)
        enhanced_state: dict[str, Any] = {
            "called": False,
            "rawOutput": None,
            "ignoredTexts": [],
            "unmappedSourceRefs": set(),
            "unknownSourceRefs": set(),
            "duplicateSourceRefs": set(),
            "importanceByCriterionId": {},
        }
        grounding_adapter = MultiSentenceGroundingAdapter(
            frozen_pipeline,
            generic_duty_detector=generic_duty_detector,
        )
        name_validation_adapter = CriterionNameValidationAdapter(frozen_pipeline)

        def normalised_section_output(
            jd_input: dict[str, Any], section_name: str, section_texts: list[str]
        ) -> str:
            complete_jd_call = use_enhanced_extraction and not transport_records
            raw_output = frozen_pipeline_section_generator(jd_input, section_name, section_texts)
            if use_enhanced_extraction:
                extraction = normalise_extraction_output(
                    raw_output,
                    source_lookup=(
                        formation_source_lookup if complete_jd_call else None
                    ),
                    required_source_refs=None,
                    debug=bool(getattr(self.loader.config, "debug_mode", False)),
                )
                raw_payload = extraction.raw_payload or {}
                raw_criteria = raw_payload.get("candidateCriteria")
                if not isinstance(raw_criteria, list):
                    raw_criteria = raw_payload.get("criteria", [])
                if complete_jd_call:
                    record_stage(
                        "qwen_generation:complete_jd",
                        raw_criteria if isinstance(raw_criteria, list) else [],
                        executed=True,
                        sourceSections=[
                            "responsibilities",
                            "requirements",
                            "qualifications",
                        ],
                        parseError=extraction.parse_error,
                        rawOutputLength=len(raw_output),
                        schema=extraction.schema_name,
                        schemaWarnings=extraction.warnings,
                        fenceNormalisationApplied=extraction.fence_applied,
                    )
                transport_records[section_name] = {
                    "original": raw_output,
                    "normalised": extraction.legacy_json,
                    "originalFenceApplied": extraction.fence_applied,
                    "retry": None,
                    "retryNormalised": None,
                    "retryFenceApplied": False,
                    "importanceByIndex": dict(extraction.importance_by_index),
                    "schemaWarnings": list(extraction.warnings),
                    "ignoredTexts": list(extraction.ignored_texts),
                    "parseError": extraction.parse_error,
                    "schemaName": extraction.schema_name,
                    "accountingRequired": complete_jd_call,
                    "missingSourceRefs": sorted(extraction.missing_source_refs),
                    "misalignedSourceRefs": sorted(
                        extraction.misaligned_source_refs
                    ),
                    "unmappedSourceRefs": sorted(extraction.unmapped_source_refs),
                    "unknownSourceRefs": sorted(extraction.unknown_source_refs),
                }
                enhanced_state["ignoredTexts"].extend(extraction.ignored_texts)
                enhanced_state["unmappedSourceRefs"].update(
                    extraction.unmapped_source_refs
                )
                enhanced_state["unknownSourceRefs"].update(
                    extraction.unknown_source_refs
                )
                for index, importance in extraction.importance_by_index.items():
                    enhanced_state["importanceByCriterionId"][
                        f"{section_name}-criterion-{index}"
                    ] = importance
                # Keep the frozen retry decision intact for malformed output.
                # A valid new-schema response is converted to the legacy-shaped
                # payload only after schema normalisation.
                return (
                    extraction.legacy_json
                    if extraction.parse_error is None
                    else raw_output
                )

            raw_payload, raw_parse_error = frozen_pipeline.extract_json_object(raw_output)
            raw_criteria = (
                raw_payload.get("criteria", [])
                if isinstance(raw_payload, dict)
                and isinstance(raw_payload.get("criteria"), list)
                else []
            )
            record_stage(
                f"qwen_generation:{section_name}",
                raw_criteria,
                parseError=raw_parse_error,
                rawOutputLength=len(raw_output),
            )
            normalised_output, fence_applied = normalise_model_output(raw_output)
            transport_records[section_name] = {
                "original": raw_output,
                "originalFenceApplied": fence_applied,
                "retry": None,
                "retryFenceApplied": False,
            }
            return normalised_output

        def normalised_retry_output(
            jd_input: dict[str, Any],
            section_name: str,
            section_texts: list[str],
            previous_raw_output: str,
        ) -> str:
            raw_output = frozen_pipeline_retry_generator(
                jd_input, section_name, section_texts, previous_raw_output
            )
            if use_enhanced_extraction:
                accounting_required = bool(
                    transport_records.get(section_name, {}).get(
                        "accountingRequired",
                        False,
                    )
                )
                extraction = normalise_extraction_output(
                    raw_output,
                    source_lookup=(
                        formation_source_lookup if accounting_required else None
                    ),
                    required_source_refs=None,
                    debug=bool(getattr(self.loader.config, "debug_mode", False)),
                )
                retry_payload = extraction.raw_payload or {}
                retry_criteria = retry_payload.get("candidateCriteria")
                if not isinstance(retry_criteria, list):
                    retry_criteria = retry_payload.get("criteria", [])
                if accounting_required:
                    record_stage(
                        "qwen_retry:complete_jd",
                        retry_criteria if isinstance(retry_criteria, list) else [],
                        executed=True,
                        parseError=extraction.parse_error,
                        rawOutputLength=len(raw_output),
                        schema=extraction.schema_name,
                        schemaWarnings=extraction.warnings,
                        fenceNormalisationApplied=extraction.fence_applied,
                    )
                record = transport_records.setdefault(
                    section_name,
                    {
                        "original": previous_raw_output,
                        "normalised": previous_raw_output,
                        "originalFenceApplied": False,
                        "retry": None,
                        "retryNormalised": None,
                        "retryFenceApplied": False,
                        "importanceByIndex": {},
                        "schemaWarnings": [],
                        "ignoredTexts": [],
                        "parseError": None,
                        "schemaName": "candidateCriteria",
                        "accountingRequired": accounting_required,
                    },
                )
                record["retry"] = raw_output
                record["retryNormalised"] = extraction.legacy_json
                record["retryFenceApplied"] = extraction.fence_applied
                record["retrySchemaWarnings"] = list(extraction.warnings)
                record["retryParseError"] = extraction.parse_error
                record["retrySchemaName"] = extraction.schema_name
                record["retryUnmappedSourceRefs"] = sorted(
                    extraction.unmapped_source_refs
                )
                record["retryUnknownSourceRefs"] = sorted(
                    extraction.unknown_source_refs
                )
                enhanced_state["ignoredTexts"].extend(extraction.ignored_texts)
                enhanced_state["unmappedSourceRefs"].update(
                    extraction.unmapped_source_refs
                )
                enhanced_state["unknownSourceRefs"].update(
                    extraction.unknown_source_refs
                )
                for index, importance in extraction.importance_by_index.items():
                    enhanced_state["importanceByCriterionId"][
                        f"{section_name}-criterion-{index}"
                    ] = importance
                retry_is_accounting_only = bool(
                    extraction.parse_error
                    and extraction.parse_error.startswith(
                        SOURCE_ACCOUNTING_ERROR_PREFIX
                    )
                )
                return (
                    extraction.legacy_json
                    if extraction.parse_error is None or retry_is_accounting_only
                    else raw_output
                )
            normalised_output, fence_applied = normalise_model_output(raw_output)
            record = transport_records.setdefault(
                section_name,
                {
                    "original": previous_raw_output,
                    "originalFenceApplied": False,
                    "retry": None,
                    "retryFenceApplied": False,
                },
            )
            record["retry"] = raw_output
            record["retryFenceApplied"] = fence_applied
            return normalised_output

        # Keep these references separate from the module globals because the
        # frozen entrypoint resolves its generators dynamically at call time.
        frozen_pipeline_section_generator = original_section_generator
        frozen_pipeline_retry_generator = original_retry_generator
        def enhanced_model_output(messages: list[dict[str, str]]) -> str:
            generator = getattr(self.loader, "enhanced_raw_output_generator", None)
            if generator is not None:
                return generator(messages)
            return frozen_pipeline.generate_model_output(messages)

        def enhanced_section_generator(
            jd_input: dict[str, Any], _section_name: str, _section_texts: list[str]
        ) -> str:
            if enhanced_state["called"]:
                return json.dumps({"candidateCriteria": [], "ignoredTexts": []})
            enhanced_state["called"] = True
            raw_output = enhanced_model_output(
                build_extraction_messages(
                    jd_input,
                    source_lookup=formation_source_lookup,
                )
            )
            enhanced_state["rawOutput"] = raw_output
            return raw_output

        def enhanced_retry_generator(
            jd_input: dict[str, Any],
            section_name: str,
            _section_texts: list[str],
            previous_raw_output: str,
        ) -> str:
            missing_source_refs = transport_records.get(
                section_name, {}
            ).get("missingSourceRefs", [])
            misaligned_source_refs = transport_records.get(
                section_name, {}
            ).get("misalignedSourceRefs", [])
            return enhanced_model_output(
                build_extraction_retry_messages(
                    jd_input,
                    previous_raw_output,
                    missing_source_refs,
                    misaligned_source_refs,
                    source_lookup=formation_source_lookup,
                )
            )

        if self.loader.config.mock_llm:
            # Dependency injection only. The extraction, retry, validation,
            # fallback, grounding, metadata, consolidation, and weighting code
            # below still executes through the frozen notebook entrypoint.
            frozen_pipeline.generate_section_raw_output = self._mock_section_output
            frozen_pipeline.generate_consolidation_raw_output = self._mock_consolidation_output
        elif use_enhanced_extraction:
            # The live path uses one complete-JD Qwen extraction. The frozen
            # post-processing entrypoint still drives validation and fallback;
            # its second section call is intentionally empty and its LLM job
            # consolidation call is disabled because Python owns that stage.
            frozen_pipeline.generate_section_raw_output = enhanced_section_generator
            frozen_pipeline.generate_json_retry_output = enhanced_retry_generator
            frozen_pipeline.generate_consolidation_raw_output = lambda _criteria: None
        elif hasattr(self.loader, "raw_output_generator"):
            # Test-only seam: exact frozen section/retry/consolidation functions
            # remain in use, while this supplies previously cached model strings.
            frozen_pipeline.generate_model_output = self.loader.raw_output_generator
        frozen_pipeline_section_generator = frozen_pipeline.generate_section_raw_output
        frozen_pipeline_retry_generator = frozen_pipeline.generate_json_retry_output
        frozen_pipeline.generate_section_raw_output = normalised_section_output
        frozen_pipeline.generate_json_retry_output = normalised_retry_output

        def multi_sentence_validate(
            raw_text: str,
            allowed_source_texts: list[str],
            source_id_prefix: str = "source",
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            validation_sources = (
                complete_source_texts
                if use_enhanced_extraction
                else allowed_source_texts
            )
            repaired_raw_text, corrections = name_validation_adapter.prepare(
                raw_text,
                validation_sources,
                expand_evidence=not use_enhanced_extraction,
            )
            criteria, diagnostics = grounding_adapter.validate(
                original_validate,
                original_find_grounded_source,
                repaired_raw_text,
                validation_sources,
                source_id_prefix,
                name_validation_adapter.normalised_detector,
            )
            for criterion in criteria:
                criterion_text = (
                    f"{criterion.get('name', '')} "
                    f"{criterion.get('sourceText', '')}"
                )
                if (
                    criterion.get("type") == "relevant_experience"
                    and not frozen_pipeline.EXPERIENCE_EVIDENCE_PATTERN.search(
                        criterion_text
                    )
                ):
                    criterion["type"] = "relevant_skill"
                    diagnostics.setdefault("warnings", []).append(
                        "Criterion remapped from relevant_experience to "
                        "relevant_skill because its evidence describes work "
                        "to perform rather than prior experience."
                    )
            if use_enhanced_extraction:
                for criterion in criteria:
                    criterion["importance"] = max(
                        (
                            enhanced_state["importanceByCriterionId"].get(
                                str(source_id),
                                "medium",
                            )
                            for source_id in criterion.get(
                                "sourceCriterionIds", []
                            )
                        ),
                        key=_importance_rank,
                        default="medium",
                    )
                schema_warnings = []
                for record in transport_records.values():
                    schema_warnings.extend(record.get("schemaWarnings", []))
                    schema_warnings.extend(record.get("retrySchemaWarnings", []))
                if schema_warnings:
                    diagnostics.setdefault("warnings", []).extend(
                        warning
                        for warning in schema_warnings
                        if warning not in diagnostics.get("warnings", [])
                    )
            record_stage(
                f"multi_sentence_grounding:{source_id_prefix}",
                criteria,
                warnings=list(diagnostics.get("warnings", [])),
                groundingMatchCount=len(diagnostics.get("groundingMatches", [])),
            )
            record_stage(
                f"type_correction:{source_id_prefix}",
                criteria,
                warnings=[
                    warning
                    for warning in diagnostics.get("warnings", [])
                    if "remapped" in warning.casefold()
                    or "type" in warning.casefold()
                ],
            )
            record_stage(
                f"education_validation:{source_id_prefix}",
                criteria,
                warnings=[
                    warning
                    for warning in diagnostics.get("warnings", [])
                    if "education" in warning.casefold()
                ],
            )
            if corrections:
                diagnostics.setdefault("normalisations", []).extend(corrections)
                diagnostics.setdefault("warnings", []).extend(corrections)
                diagnostics["nameCorrections"] = corrections
                diagnostics["finalRawModelOutput"] = repaired_raw_text
            return criteria, diagnostics

        # Keep the frozen validator and finalisation flow unchanged while
        # supplying a conservative morphological support detector.
        frozen_pipeline.criterion_name_unsupported_tokens = (
            name_validation_adapter.normalised_detector
        )
        # The frozen entrypoint filters section inputs before validation. Use
        # the API boundary wrapper for common generic-duty wording variants,
        # then restore the frozen function after this request.
        frozen_pipeline.is_generic_duty = generic_duty_detector
        frozen_pipeline.same_independently_scorable_capability = (
            lambda left, right: _same_capability_with_broad_context_guard(
                original_same_capability,
                left,
                right,
            )
        )
        frozen_pipeline.merge_duplicate_criteria = lambda criteria: safe_merge_duplicate_criteria(
            criteria,
            frozen_pipeline,
            frozen_pipeline.same_independently_scorable_capability,
        )
        frozen_pipeline.can_merge_criteria_group = lambda members: safe_can_merge_group(
            members,
            frozen_pipeline.same_independently_scorable_capability,
        )
        original_apply_consolidation = frozen_pipeline.apply_consolidation

        def traced_apply_consolidation(
            criteria_with_ids: list[dict[str, str]],
            raw_text: str,
        ) -> tuple[list[dict[str, str]], dict[str, Any]]:
            consolidated, consolidation_diagnostics = original_apply_consolidation(
                criteria_with_ids,
                raw_text,
            )
            record_stage(
                "consolidation",
                consolidated,
                method=consolidation_diagnostics.get("consolidationMethod"),
                succeeded=consolidation_diagnostics.get("consolidationSucceeded"),
                failureCategories=consolidation_diagnostics.get(
                    "consolidationFailureCategories", []
                ),
                inputCriterionIds=[item.get("id") for item in criteria_with_ids],
            )
            return consolidated, consolidation_diagnostics

        frozen_pipeline.apply_consolidation = traced_apply_consolidation
        frozen_pipeline.validate_section_output = multi_sentence_validate
        try:
            outputs, diagnostics = frozen_pipeline.extract_soft_criteria_llm([job])
        finally:
            if self.loader.config.mock_llm:
                frozen_pipeline.generate_section_raw_output = original_section_generator
            elif use_enhanced_extraction:
                frozen_pipeline.generate_section_raw_output = original_section_generator
            else:
                frozen_pipeline.generate_section_raw_output = original_section_generator
            frozen_pipeline.generate_consolidation_raw_output = original_consolidation_generator
            frozen_pipeline.generate_json_retry_output = original_retry_generator
            frozen_pipeline.generate_model_output = original_model_generator
            frozen_pipeline.validate_section_output = original_validate
            frozen_pipeline.is_generic_duty = original_is_generic_duty
            frozen_pipeline.criterion_name_unsupported_tokens = original_name_detector
            frozen_pipeline.same_independently_scorable_capability = (
                original_same_capability
            )
            frozen_pipeline.merge_duplicate_criteria = original_merge_duplicate
            frozen_pipeline.can_merge_criteria_group = original_can_merge_group
            frozen_pipeline.apply_consolidation = original_apply_consolidation

        for section_name in ("responsibilities", "requirements"):
            section_item = diagnostics[0]["sectionDiagnostics"].get(section_name)
            if section_item is not None:
                grounding_adapter.restore_metadata(
                    outputs[0]["softCriteria"],
                    section_item,
                    section_name,
                )
        _restore_merged_grounding_metadata(
            outputs[0]["softCriteria"],
            diagnostics[0]["sectionDiagnostics"],
        )
        if use_enhanced_extraction:
            _restore_live_source_metadata(
                outputs[0]["softCriteria"],
                job,
                generic_duty_detector,
                frozen_pipeline,
            )
            _restore_live_importance(
                outputs[0]["softCriteria"],
                enhanced_state["importanceByCriterionId"],
            )
            (
                outputs[0]["softCriteria"],
                decomposition_warnings,
                decomposition_audit,
            ) = decompose_incoherent_multisource_criteria(
                outputs[0]["softCriteria"]
            )
            diagnostics[0]["warnings"].extend(decomposition_warnings)
            record_stage(
                "multisource_capability_decomposition",
                outputs[0]["softCriteria"],
                changes=decomposition_audit,
                changeCount=len(decomposition_audit),
            )

            # Source accounting is intentionally post-validation. A source that
            # was not grouped is recorded for HR review; it does not trigger a
            # semantic importance filter or an automatic criterion recovery.
            record_stage(
                "source_accounting_preconsolidation",
                outputs[0]["softCriteria"],
                sourceCount=len(source_records),
            )
            semantic_plan_generator = getattr(
                self.loader,
                "semantic_consolidation_raw_output_generator",
                None,
            )
            semantic_review_enabled = (
                semantic_plan_generator is not None
            )
            semantic_review_candidates = [
                item
                for item in outputs[0]["softCriteria"]
                if item.get("type") == "relevant_skill"
                and len(_source_parts_for_trace(item)) == 1
            ]
            if semantic_review_enabled and len(semantic_review_candidates) >= 2:
                try:
                    semantic_messages = build_semantic_consolidation_messages(
                        outputs[0]["softCriteria"]
                    )
                    semantic_raw_plan = (
                        semantic_plan_generator(semantic_messages)
                        if semantic_plan_generator is not None
                        else enhanced_model_output(semantic_messages)
                    )
                    (
                        outputs[0]["softCriteria"],
                        semantic_warnings,
                        semantic_audit,
                        semantic_errors,
                    ) = apply_semantic_consolidation_plan(
                        outputs[0]["softCriteria"],
                        semantic_raw_plan,
                        frozen_pipeline,
                    )
                    diagnostics[0]["warnings"].extend(semantic_warnings)
                    diagnostics[0]["warnings"].extend(
                        f"semantic consolidation: {error}"
                        for error in semantic_errors
                    )
                    semantic_groups = [
                        item
                        for item in semantic_audit
                        if item.get("kind") == "group"
                    ]
                    semantic_renames = [
                        item
                        for item in semantic_audit
                        if item.get("kind") == "rename"
                    ]
                    record_stage(
                        "semantic_consolidation_review",
                        outputs[0]["softCriteria"],
                        executed=True,
                        rawOutputLength=len(semantic_raw_plan),
                        acceptedGroupCount=len(semantic_groups),
                        acceptedRenameCount=len(semantic_renames),
                        groups=semantic_groups,
                        renames=semantic_renames,
                        validationErrors=semantic_errors,
                    )
                except Exception as error:  # pragma: no cover - live fail-open boundary
                    warning = (
                        "semantic consolidation review failed open: "
                        f"{type(error).__name__}"
                    )
                    diagnostics[0]["warnings"].append(warning)
                    record_stage(
                        "semantic_consolidation_review",
                        outputs[0]["softCriteria"],
                        executed=True,
                        acceptedGroupCount=0,
                        acceptedRenameCount=0,
                        validationErrors=[warning],
                    )
            (
                outputs[0]["softCriteria"],
                supply_warnings,
                supply_audit,
            ) = consolidate_adjacent_supply_operations(
                outputs[0]["softCriteria"]
            )
            diagnostics[0]["warnings"].extend(supply_warnings)
            record_stage(
                "supply_operations_consolidation",
                outputs[0]["softCriteria"],
                groups=supply_audit,
            )
            (
                outputs[0]["softCriteria"],
                workflow_warnings,
                workflow_audit,
            ) = consolidate_grounded_workflow_relations(
                outputs[0]["softCriteria"]
            )
            diagnostics[0]["warnings"].extend(workflow_warnings)
            record_stage(
                "workflow_relation_consolidation",
                outputs[0]["softCriteria"],
                groups=workflow_audit,
            )
            record_stage(
                "source_metadata_restoration",
                outputs[0]["softCriteria"],
                sourceSections=[
                    "responsibilities",
                    "requirements",
                    "qualifications",
                ],
            )
            ignored = [
                *outputs[0].get("ignoredTexts", []),
                *enhanced_state["ignoredTexts"],
            ]
            unique_ignored: dict[str, dict[str, str]] = {}
            for item in ignored:
                source_text = str(item.get("sourceText", "")).strip()
                if source_text:
                    unique_ignored.setdefault(source_text.casefold(), item)
            outputs[0]["ignoredTexts"] = list(unique_ignored.values())

        role_context = build_role_context(job)
        record_stage(
            "role_context",
            outputs[0]["softCriteria"],
            jobTitle=role_context["jobTitle"],
            department=role_context["department"],
            titleTokens=sorted(role_context["titleTokens"]),
            departmentTokens=sorted(role_context["departmentTokens"]),
            responsibilityCount=len(role_context["responsibilities"]),
            requirementCount=len(role_context["requirements"]),
        )

        # The frozen parser saw only the normalised string. Restore the exact
        # transport response in its diagnostics while retaining normalised
        # rawModelOutput/finalRawModelOutput values used by parsing.
        section_diagnostics = diagnostics[0]["sectionDiagnostics"]
        for section_name, record in transport_records.items():
            item = section_diagnostics.get(section_name)
            if item is None:
                continue
            if use_enhanced_extraction:
                item["originalRawModelOutput"] = record["original"]
                item["rawModelOutput"] = record.get(
                    "normalised",
                    record["original"],
                )
                item["finalRawModelOutput"] = record.get(
                    "retryNormalised"
                ) or record.get("normalised", record["original"])
                item["retryRawModelOutput"] = record.get("retryNormalised")
                item["originalRetryRawModelOutput"] = record.get("retry")
                item["schemaName"] = record.get("schemaName", "candidateCriteria")
                item["schemaWarnings"] = list(record.get("schemaWarnings", []))
                item["fenceNormalisationApplied"] = bool(
                    record.get("originalFenceApplied")
                    or record.get("retryFenceApplied")
                )
                item["fenceNormalisation"] = {
                    "original": bool(record.get("originalFenceApplied")),
                    "retry": bool(record.get("retryFenceApplied")),
                }
                continue
            if record["originalFenceApplied"] or record["retryFenceApplied"]:
                item["originalRawModelOutput"] = record["original"]
                item["originalRetryRawModelOutput"] = record["retry"]
                item["fenceNormalisationApplied"] = True
                item["fenceNormalisation"] = {
                    "original": record["originalFenceApplied"],
                    "retry": record["retryFenceApplied"],
                }

        output = outputs[0]
        diagnostic = diagnostics[0]
        recovered_criteria = output["softCriteria"]
        explicit_recoveries: list[dict[str, Any]] = []
        explicit_recovery_warnings: list[str] = []
        for source_section, source_texts in (
            ("requirements", complete_requirements),
            ("qualifications", complete_qualifications),
            ("responsibilities", complete_responsibilities),
        ):
            recovered_criteria, section_recoveries, section_warnings = (
                recover_explicit_requirements(
                    recovered_criteria,
                    source_texts,
                    source_section=source_section,
                )
            )
            explicit_recoveries.extend(section_recoveries)
            explicit_recovery_warnings.extend(section_warnings)
        (
            recovered_criteria,
            experience_consolidation_warnings,
            experience_consolidation_audit,
        ) = consolidate_broad_specific_experience(recovered_criteria)
        explicit_recovery_warnings.extend(experience_consolidation_warnings)
        output["softCriteria"] = recovered_criteria
        if explicit_recovery_warnings:
            diagnostic["warnings"].extend(explicit_recovery_warnings)
        # Replace the frozen fallback audit entries with the safe, explicit
        # recovery contract. The frozen criteria themselves remain unchanged;
        # only raw sourceText-bearing diagnostics are removed from the API audit.
        output["fallbackRecoveries"] = explicit_recoveries
        output["domainKnowledgeFallbackRecoveryCount"] = sum(
            item.get("recoveryType") == "explicit_law_or_standard"
            for item in explicit_recoveries
        )
        output["preferredCertificationFallbackRecoveryCount"] = sum(
            item.get("recoveryType") == "explicit_certification"
            for item in explicit_recoveries
        )
        output["relevantExperienceFallbackRecoveryCount"] = sum(
            item.get("recoveryType") == "explicit_experience"
            for item in explicit_recoveries
        )
        diagnostic["fallbackRecoveries"] = output["fallbackRecoveries"]
        record_stage(
            "explicit_requirement_recovery",
            output["softCriteria"],
            recoveryCount=len(explicit_recoveries),
            recoveryTypes=sorted(
                {
                    item.get("recoveryType")
                    for item in explicit_recoveries
                    if item.get("recoveryType")
                }
            ),
        )
        record_stage(
            "experience_requirement_consolidation",
            output["softCriteria"],
            consolidatedGroupCount=len(experience_consolidation_audit),
            groups=experience_consolidation_audit,
        )
        trusted_source_texts_by_criterion_id: dict[str, set[str]] = {}
        for (source_id_prefix, criterion_id), match in grounding_adapter.matches.items():
            trusted_source_texts_by_criterion_id.setdefault(
                criterion_id, set()
            ).update(match.source_texts)
        for criterion in output["softCriteria"]:
            if not any(
                item.get("criterionId") == criterion.get("criterionId")
                for item in explicit_recoveries
            ):
                continue
            parts = _source_parts_for_trace(criterion)
            for source_criterion_id in criterion.get("sourceCriterionIds", []):
                trusted_source_texts_by_criterion_id.setdefault(
                    str(source_criterion_id), set()
                ).update(parts)
        cleaned_criteria, evidence_warnings, evidence_rejections, evidence_audit = final_evidence_safety_pass(
            output["softCriteria"],
            frozen_pipeline,
            trusted_source_texts_by_criterion_id,
        )
        output["softCriteria"] = cleaned_criteria
        warnings = diagnostic["warnings"]
        warnings.extend(evidence_warnings)
        if evidence_rejections:
            diagnostic.setdefault("rejectedCriteria", []).extend(evidence_rejections)
        record_stage(
            "final_evidence_safety",
            output["softCriteria"],
            removedSourceTextCount=len(evidence_audit.get("removedSourceText", [])),
            rejectedCriteriaCount=len(evidence_rejections),
        )
        (
            output["softCriteria"],
            duplicate_warnings,
            duplicate_audit,
        ) = collapse_explicit_requirement_duplicates(output["softCriteria"])
        warnings.extend(duplicate_warnings)
        record_stage(
            "explicit_requirement_deduplication",
            output["softCriteria"],
            collapsedGroupCount=len(duplicate_audit),
            groups=duplicate_audit,
        )
        source_accounting_audit = build_source_accounting(
            source_records,
            output["softCriteria"],
            hard_requirements,
            unknown_source_refs=enhanced_state.get("unknownSourceRefs", set()),
            duplicate_source_refs=enhanced_state.get("duplicateSourceRefs", set()),
            model_unmapped_refs=enhanced_state.get("unmappedSourceRefs", set()),
            generic_duty_detector=generic_duty_detector,
        )
        record_stage(
            "source_accounting_audit",
            output["softCriteria"],
            valid=source_accounting_audit["valid"],
            sourceCount=len(source_accounting_audit["sources"]),
            mappedSourceCount=sum(
                item["mapped"] for item in source_accounting_audit["sources"]
            ),
            unmappedSourceRefs=source_accounting_audit["unmappedSourceRefs"],
        )
        if use_enhanced_extraction:
            _restore_lineage_metadata(output["softCriteria"])
            record_stage(
                "lineage_restoration",
                output["softCriteria"],
                singletonFallbackApplied=True,
            )
        output["softCriteria"] = apply_enhanced_weights(
            output["softCriteria"],
            job,
        )
        output["softCriteria"] = apply_deterministic_criterion_texts(
            output["softCriteria"]
        )
        record_stage(
            "role_context_weighting",
            output["softCriteria"],
            roleContextApplied=True,
        )
        record_stage(
            "deterministic_criterion_texts",
            output["softCriteria"],
            modelTextFieldsIgnored=True,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "criteria generated request_id=%s duration_ms=%d count=%d warnings=%d",
            request_id,
            elapsed_ms,
            len(output["softCriteria"]),
            len(warnings),
        )
        record_stage(
            "api_payload_ready",
            output["softCriteria"],
            weightTotal=sum(
                item["suggestedWeight"] for item in output["softCriteria"]
            ),
            cleanedCriteriaObject=True,
        )
        return {
            "criteria": output["softCriteria"],
            "ignoredTexts": output["ignoredTexts"],
            "warnings": warnings,
            "weightTotal": sum(item["suggestedWeight"] for item in output["softCriteria"]),
            "eligibilitySuggestions": hard_requirements.eligibility_suggestions,
            "audit": {
                "fallbackRecoveries": output["fallbackRecoveries"],
                "rejectedCriteria": [
                    issue
                    for section in diagnostic["sectionDiagnostics"].values()
                    for issue in section.get("fatalErrors", [])
                ] + evidence_rejections,
                "sectionDiagnostics": diagnostic["sectionDiagnostics"],
                "consolidation": output["consolidationDiagnostics"],
                "evidenceSafety": evidence_audit,
                "hardRequirements": hard_requirements.safe_audit(),
                "sourceAccounting": source_accounting_audit,
                "deployment": deployment_metadata(),
                "debugTrace": debug_trace,
            },
        }
