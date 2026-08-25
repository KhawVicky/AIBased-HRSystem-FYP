"""Normalisation for the non-frozen live Qwen extraction schema."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Collection, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .extraction_prompt import ALLOWED_CRITERION_TYPES
from .model_output import normalise_model_output
from .name_validation import source_contributes_to_name


Importance = Literal["high", "medium", "low"]
SOURCE_ACCOUNTING_ERROR_PREFIX = "Source reference accounting failed:"


class QwenCriterion(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    name: str
    sourceText: str
    importance: Importance = "medium"


class QwenIgnoredText(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sourceText: str
    reason: str


class QwenExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidateCriteria: list[QwenCriterion] = Field(default_factory=list)
    ignoredTexts: list[QwenIgnoredText] = Field(default_factory=list)


@dataclass
class NormalisedExtraction:
    """A parser result that can be consumed by the frozen validator."""

    legacy_json: str
    importance_by_index: dict[int, Importance] = field(default_factory=dict)
    ignored_texts: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_error: str | None = None
    fence_applied: bool = False
    schema_name: str = "candidateCriteria"
    raw_payload: dict[str, Any] | None = None
    missing_source_refs: set[str] = field(default_factory=set)
    misaligned_source_refs: set[str] = field(default_factory=set)
    unknown_source_refs: set[str] = field(default_factory=set)
    contradictory_source_refs: set[str] = field(default_factory=set)
    unmapped_source_refs: set[str] = field(default_factory=set)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


_EDUCATION_FIELD_PATTERN = re.compile(
    r"\b(?:degree|diploma|bachelor'?s?|master'?s?|ph\.?d\.?)\s+"
    r"(?:in|of)\s+[A-Za-z]",
    flags=re.IGNORECASE,
)
_EXPERIENCE_PATTERN = re.compile(r"\bexperience\b", flags=re.IGNORECASE)
_FORMAL_DOMAIN_PATTERN = re.compile(
    r"\b(?:law|laws|regulation|regulations|act|standard|standards|iso\s*\d*)\b",
    flags=re.IGNORECASE,
)
_LANGUAGE_PATTERN = re.compile(
    r"\b(?:english|bahasa malaysia|bahasa melayu|malay|mandarin|chinese|"
    r"tamil|japanese|korean)\b",
    flags=re.IGNORECASE,
)
_PREFERRED_CERTIFICATION_PATTERN = re.compile(
    r"\b(?:preferred|desirable|advantageous|an advantage)\b.*"
    r"\b(?:certification|certificate|licen[cs]e)\b"
    r"|\b(?:certification|certificate|licen[cs]e)\b.*"
    r"\b(?:preferred|desirable|advantageous|an advantage)\b",
    flags=re.IGNORECASE,
)
_PRACTICAL_REQUIREMENT_PATTERN = re.compile(
    r"\b(?:skill|proficien|knowledge of|ability to|using|with|tool|system|"
    r"platform|software|method|process|workflow)\b",
    flags=re.IGNORECASE,
)


def _safe_taxonomy_correction(
    proposed_type: str,
    name: str,
    source_text: str,
    source_refs: list[str],
) -> str | None:
    """Map an invalid model label only when generic evidence is unambiguous."""

    if proposed_type in ALLOWED_CRITERION_TYPES:
        return proposed_type
    combined = f"{name} {source_text}"
    if _EDUCATION_FIELD_PATTERN.search(source_text):
        return "education_relevance"
    if _EXPERIENCE_PATTERN.search(combined):
        return "relevant_experience"
    if _PREFERRED_CERTIFICATION_PATTERN.search(source_text):
        return "preferred_certification"
    if _LANGUAGE_PATTERN.search(source_text):
        return "job_related_language"
    if _FORMAL_DOMAIN_PATTERN.search(combined):
        return "domain_knowledge"
    if any(source_ref.startswith("R") for source_ref in source_refs):
        return "relevant_skill"
    if _PRACTICAL_REQUIREMENT_PATTERN.search(combined):
        return "relevant_skill"
    return None


def _normalise_source_text(
    raw_item: dict[str, Any],
    index: int,
    warnings: list[str],
    source_lookup: Mapping[str, str],
    unknown_refs: set[str],
) -> tuple[str, list[str]]:
    """Resolve compact refs, then join exact evidence for the frozen validator."""

    raw_source_refs = raw_item.get("sourceRefs")
    if raw_source_refs is not None:
        if isinstance(raw_source_refs, str):
            warnings.append(
                f"Criterion {index} sourceRefs is a string; treated as one reference."
            )
            raw_source_refs = [raw_source_refs]
        if isinstance(raw_source_refs, list):
            source_texts: list[str] = []
            resolved_refs: list[str] = []
            seen_refs: set[str] = set()
            for value in raw_source_refs:
                source_ref = _clean_text(value).upper()
                if not source_ref or source_ref in seen_refs:
                    continue
                seen_refs.add(source_ref)
                source_text = _clean_text(source_lookup.get(source_ref))
                if not source_text:
                    unknown_refs.add(source_ref)
                    warnings.append(
                        f"Criterion {index} contains unknown sourceRef {source_ref!r}."
                    )
                    continue
                resolved_refs.append(source_ref)
                source_texts.append(source_text)
            if source_texts:
                return " | ".join(source_texts), resolved_refs
            warnings.append(
                f"Criterion {index} has no resolvable sourceRefs; legacy evidence was used."
            )
        else:
            warnings.append(
                f"Criterion {index} sourceRefs is not a list; legacy evidence was used."
            )

    raw_source_texts = raw_item.get("sourceTexts")
    if isinstance(raw_source_texts, list):
        source_texts: list[str] = []
        seen: set[str] = set()
        for value in raw_source_texts:
            cleaned = _clean_text(value)
            key = cleaned.casefold()
            if not cleaned or key in seen:
                continue
            seen.add(key)
            source_texts.append(cleaned)
        if source_texts:
            return " | ".join(source_texts), []
        warnings.append(
            f"Criterion {index} has no usable sourceTexts; legacy sourceText was used."
        )
    elif raw_source_texts is not None:
        warnings.append(
            f"Criterion {index} sourceTexts is not a list; legacy sourceText was used."
        )
    return _clean_text(raw_item.get("sourceText")), []


def _normalise_importance(
    value: Any,
    index: int,
    warnings: list[str],
) -> Importance:
    if value is None or not _clean_text(value):
        warnings.append(
            f"Criterion {index} is missing importance; defaulted to medium."
        )
        return "medium"
    normalised = _clean_text(value).casefold()
    if normalised in {"high", "medium", "low"}:
        return normalised  # type: ignore[return-value]
    warnings.append(
        f"Criterion {index} has invalid importance {value!r}; defaulted to medium."
    )
    return "medium"


def _payload_from_raw(
    raw_output: str,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    normalised, fence_applied = normalise_model_output(raw_output)
    try:
        payload = json.loads(normalised)
    except json.JSONDecodeError as error:
        return None, f"Malformed JSON: {error.msg}", fence_applied
    if not isinstance(payload, dict):
        return None, "Top-level model output is not an object.", fence_applied
    return payload, None, fence_applied


def normalise_extraction_output(
    raw_output: str,
    *,
    source_lookup: Mapping[str, str] | None = None,
    required_source_refs: Collection[str] | None = None,
    debug: bool = False,
) -> NormalisedExtraction:
    """Parse new output and expose a legacy-shaped JSON for frozen validation.

    The conversion is transport/schema-only. Frozen grounding, type validation,
    fallbacks, consolidation and evidence safety still decide acceptance.
    """

    payload, parse_error, fence_applied = _payload_from_raw(raw_output)
    if parse_error or payload is None:
        return NormalisedExtraction(
            legacy_json=json.dumps({"criteria": []}),
            parse_error=parse_error,
            fence_applied=fence_applied,
            raw_payload=payload,
        )

    raw_items = payload.get("candidateCriteria")
    schema_name = "candidateCriteria"
    if not isinstance(raw_items, list):
        # Legacy cached outputs remain accepted for tests and older workers.
        raw_items = payload.get("criteria")
        schema_name = "criteria"
    if not isinstance(raw_items, list):
        return NormalisedExtraction(
            legacy_json=json.dumps({"criteria": []}),
            parse_error="candidateCriteria is not a list.",
            fence_applied=fence_applied,
            schema_name=schema_name,
            raw_payload=payload,
        )

    warnings: list[str] = []
    resolved_source_lookup = {
        _clean_text(key).upper(): _clean_text(value)
        for key, value in (source_lookup or {}).items()
        if _clean_text(key) and _clean_text(value)
    }
    resolved_required_refs = {
        _clean_text(source_ref).upper()
        for source_ref in (required_source_refs or [])
        if _clean_text(source_ref).upper() in resolved_source_lookup
    }
    refs_by_source_text: dict[str, set[str]] = {}
    for source_ref, source_text in resolved_source_lookup.items():
        refs_by_source_text.setdefault(source_text.casefold(), set()).add(source_ref)
    candidate_source_refs: set[str] = set()
    supported_candidate_source_refs: set[str] = set()
    ignored_source_refs: set[str] = set()
    unknown_source_refs: set[str] = set()
    legacy_items: list[dict[str, str]] = []
    importance_by_index: dict[int, Importance] = {}
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            warnings.append(f"Criterion {index} is not an object and was rejected.")
            continue

        raw_importance = raw_item.get("importance")
        importance = _normalise_importance(raw_importance, index, warnings)
        source_text, resolved_refs = _normalise_source_text(
            raw_item,
            index,
            warnings,
            resolved_source_lookup,
            unknown_source_refs,
        )
        proposed_type = _clean_text(raw_item.get("type"))
        corrected_type = _safe_taxonomy_correction(
            proposed_type,
            _clean_text(raw_item.get("name")),
            source_text,
            resolved_refs,
        )
        if corrected_type and corrected_type != proposed_type:
            warnings.append(
                f"Criterion {index} taxonomy type {proposed_type!r} was safely "
                f"corrected to {corrected_type!r} from its grounded evidence."
            )
        candidate = {
            "type": corrected_type or proposed_type,
            "name": _clean_text(raw_item.get("name")),
            "sourceText": source_text,
            "importance": importance,
        }
        try:
            validated = QwenCriterion.model_validate(candidate)
        except ValidationError as error:
            warnings.append(f"Criterion {index} failed schema validation: {error.errors()}")
            continue

        if debug and any(key in raw_item for key in ("suggestedWeight", "weight")):
            warnings.append(
                f"Criterion {index} model-generated weight was ignored in debug mode."
            )
        legacy_items.append(
            {
                "type": validated.type,
                "name": validated.name,
                "sourceText": validated.sourceText,
            }
        )
        if raw_item.get("sourceRefs") is not None:
            candidate_source_refs.update(resolved_refs)
            supported_candidate_source_refs.update(
                source_ref
                for source_ref in resolved_refs
                if source_contributes_to_name(
                    validated.name,
                    resolved_source_lookup[source_ref],
                )
            )
        else:
            for source_part in validated.sourceText.split(" | "):
                candidate_source_refs.update(
                    refs_by_source_text.get(source_part.strip().casefold(), set())
                )
        # Frozen grounding IDs are assigned from the converted legacy list,
        # so map importance to the post-schema-validation criterion index.
        importance_by_index[len(legacy_items)] = validated.importance

    ignored_texts: list[dict[str, str]] = []
    raw_ignored = payload.get("ignoredTexts", [])
    if isinstance(raw_ignored, list):
        for index, item in enumerate(raw_ignored, start=1):
            if not isinstance(item, dict):
                warnings.append(f"Ignored text {index} is not an object and was skipped.")
                continue
            source_text = _clean_text(item.get("sourceText"))
            reason = _clean_text(item.get("reason"))
            if not source_text:
                warnings.append(f"Ignored text {index} has no sourceText and was skipped.")
                continue
            ignored_texts.append(
                {"sourceText": source_text, "reason": reason or "Not useful for resume scoring."}
            )
            ignored_source_refs.update(
                refs_by_source_text.get(source_text.casefold(), set())
            )

    raw_ignored_refs = payload.get("ignoredSourceRefs", [])
    if isinstance(raw_ignored_refs, str):
        warnings.append("ignoredSourceRefs is a string; treated as one reference.")
        raw_ignored_refs = [raw_ignored_refs]
    if isinstance(raw_ignored_refs, list):
        known_ignored_texts = {item["sourceText"].casefold() for item in ignored_texts}
        for value in raw_ignored_refs:
            source_ref = _clean_text(value).upper()
            source_text = _clean_text(resolved_source_lookup.get(source_ref))
            if not source_text:
                unknown_source_refs.add(source_ref)
                warnings.append(f"Ignored sourceRef {source_ref!r} is unknown and was skipped.")
                continue
            ignored_source_refs.add(source_ref)
            if source_text.casefold() in known_ignored_texts:
                continue
            known_ignored_texts.add(source_text.casefold())
            ignored_texts.append(
                {
                    "sourceText": source_text,
                    "reason": "Model classified this supplied source as non-assessable.",
                }
            )
    elif raw_ignored_refs is not None:
        warnings.append("ignoredSourceRefs is not a list and was skipped.")

    raw_unmapped_refs = payload.get("unmappedSourceRefs", [])
    if isinstance(raw_unmapped_refs, str):
        raw_unmapped_refs = [raw_unmapped_refs]
    unmapped_source_refs: set[str] = set()
    if isinstance(raw_unmapped_refs, list):
        for value in raw_unmapped_refs:
            source_ref = _clean_text(value).upper()
            if not source_ref:
                continue
            if source_ref not in resolved_source_lookup:
                unknown_source_refs.add(source_ref)
                warnings.append(f"Unmapped sourceRef {source_ref!r} is unknown and was skipped.")
                continue
            unmapped_source_refs.add(source_ref)
    elif raw_unmapped_refs is not None:
        warnings.append("unmappedSourceRefs is not a list and was skipped.")

    accounting_errors: list[str] = []
    contradictory_refs: set[str] = set()
    missing_refs: set[str] = set()
    misaligned_refs: set[str] = set()
    if resolved_source_lookup:
        if unknown_source_refs:
            accounting_errors.append(
                "unknown source references: "
                + ", ".join(sorted(unknown_source_refs))
            )
        contradictory_refs = candidate_source_refs & (
            ignored_source_refs | unmapped_source_refs
        )
        if contradictory_refs:
            accounting_errors.append(
                "references classified as both criteria and unmapped: "
                + ", ".join(sorted(contradictory_refs))
            )
        misaligned_refs = candidate_source_refs - supported_candidate_source_refs
        if misaligned_refs:
            accounting_errors.append(
                "source references assigned only to criteria whose names they "
                "do not concretely support: "
                + ", ".join(sorted(misaligned_refs))
            )
        missing_refs = resolved_required_refs - (
            candidate_source_refs | ignored_source_refs | unmapped_source_refs
        )
        if missing_refs:
            accounting_errors.append(
                "unaccounted source references: "
                + ", ".join(sorted(missing_refs))
            )
    accounting_error = None
    if accounting_errors:
        accounting_error = SOURCE_ACCOUNTING_ERROR_PREFIX + " " + "; ".join(
            accounting_errors
        )
        warnings.append(accounting_error)

    if schema_name == "criteria":
        warnings.append("Legacy criteria schema accepted; importance defaults were applied.")
    unknown_output_keys = set(payload) - {
        "candidateCriteria",
        "ignoredSourceRefs",
        "ignoredTexts",
        "unmappedSourceRefs",
        "unmappedTexts",
        "criteria",
    }
    if debug and unknown_output_keys:
        warnings.append(
            "Ignored extra extraction fields in debug mode: "
            + ", ".join(sorted(unknown_output_keys))
        )

    return NormalisedExtraction(
        legacy_json=json.dumps({"criteria": legacy_items}, ensure_ascii=False),
        importance_by_index=importance_by_index,
        ignored_texts=ignored_texts,
        warnings=warnings,
        parse_error=accounting_error,
        fence_applied=fence_applied,
        schema_name=schema_name,
        raw_payload=payload,
        missing_source_refs=missing_refs,
        misaligned_source_refs=misaligned_refs,
        unknown_source_refs=unknown_source_refs,
        contradictory_source_refs=contradictory_refs,
        unmapped_source_refs=unmapped_source_refs | ignored_source_refs,
    )


__all__ = [
    "Importance",
    "NormalisedExtraction",
    "QwenCriterion",
    "QwenExtractionResponse",
    "QwenIgnoredText",
    "SOURCE_ACCOUNTING_ERROR_PREFIX",
    "normalise_extraction_output",
]
