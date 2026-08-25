"""Narrow adapter for criteria grounded by multiple JD sentences.

The frozen validator intentionally exposes a single-source grounding contract.
This module broadens that contract for exact, same-section multi-source matches
and can temporarily apply the surrounding morphology-aware name detector during
the same validation call. The frozen source and single-source boundaries remain
unchanged.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable

from .name_validation import morphological_root
from .evidence_safety import is_broad_overview_source, is_generic_duty_safe


@dataclass(frozen=True)
class MultiSentenceMatch:
    """Metadata needed to restore all source IDs after frozen validation."""

    source_indices: tuple[int, ...]
    source_texts: tuple[str, ...]
    scores: tuple[float, ...]


class MultiSentenceGroundingAdapter:
    """Temporarily adapt frozen single-source grounding for one validation call."""

    def __init__(
        self,
        frozen_module: Any,
        generic_duty_detector: Callable[[str], bool] | None = None,
    ) -> None:
        self.frozen = frozen_module
        self.generic_duty_detector = generic_duty_detector or (
            lambda value: is_generic_duty_safe(value, frozen_module)
        )
        self.matches: dict[tuple[str, str], MultiSentenceMatch] = {}
        self._candidate_queues: dict[
            str, deque[tuple[str, str, str, str]]
        ] = {}

    @staticmethod
    def _key(value: Any) -> str:
        return str(value or "").strip().casefold()

    def _exact_sources_in_candidate(
        self,
        candidate: str,
        allowed_sources: list[str],
    ) -> list[tuple[int, str]]:
        candidate_text = self.frozen.comparable_text(candidate)
        matches: list[tuple[int, str]] = []
        for index, source in enumerate(allowed_sources, start=1):
            cleaned = self.frozen.normalise_text(source)
            if (
                cleaned
                and not self.generic_duty_detector(cleaned)
                and self.frozen.comparable_text(cleaned) in candidate_text
            ):
                matches.append((index, cleaned))
        return matches

    def _find_multi_source_match(
        self,
        candidate: str,
        name: str,
        allowed_sources: list[str],
    ) -> tuple[str, float, MultiSentenceMatch] | None:
        exact_sources = self._exact_sources_in_candidate(candidate, allowed_sources)
        if len(exact_sources) < 2:
            return None

        name_tokens = self.frozen.grounding_tokens(name)
        if not name_tokens:
            return None

        def token_variants(token: str) -> set[str]:
            variants = {token, morphological_root(token)}
            if len(token) > 6 and token.endswith("ing"):
                variants.add(token[:-3])
            if len(token) > 6 and token.startswith("pre"):
                without_prefix = token[3:]
                variants.add(without_prefix)
                if len(without_prefix) > 6 and without_prefix.endswith("ing"):
                    variants.add(without_prefix[:-3])
            return variants

        def supports_abstract_capability(name_token: str, source: str) -> bool:
            """Allow an abstract capability head for operational source lists.

            JD sections often list responsibilities as noun phrases rather
            than repeating a verb such as ``manage`` in every sentence. This
            exception is limited to multi-source matches and requires clear
            operational evidence such as a list, colon-delimited scope, or an
            explicit work action. Single-source validation remains frozen.
            """

            if morphological_root(name_token) not in {
                "manage", "supervise", "coordinate"
            }:
                return False
            lowered = source.casefold()
            has_operational_shape = ":" in source or source.count(",") >= 1
            has_work_action = bool(
                self.frozen.WORKFLOW_STEP_ACTION_PATTERN.search(lowered)
            )
            return has_operational_shape or has_work_action

        contributing: list[tuple[int, str, set[str]]] = []
        for index, source in exact_sources:
            source_tokens = self.frozen.grounding_tokens(source)
            direct_contribution = {
                name_token
                for name_token in name_tokens
                if any(
                    token_variants(name_token) & token_variants(source_token)
                    for source_token in source_tokens
                )
            }
            # A source must contain at least one concrete capability/object
            # term from the name. Generic action heads such as ``management``
            # are only supplemental; they cannot make an unrelated source a
            # contributor on their own.
            concrete_contribution = {
                name_token
                for name_token in direct_contribution
                if morphological_root(name_token)
                not in {"manage", "supervise", "coordinate"}
            }
            if not concrete_contribution:
                continue
            contribution = set(direct_contribution)
            contribution.update(
                name_token
                for name_token in name_tokens
                if supports_abstract_capability(name_token, source)
            )
            if contribution:
                contributing.append((index, source, contribution))

        # A wide scope-list sentence is useful context, but it should not be
        # attached to every specific capability in the same section.  Keep it
        # only when no more specific source supports the candidate.
        specific_contributing = [
            item for item in contributing
            if not is_broad_overview_source(item[1])
        ]
        if specific_contributing:
            contributing = specific_contributing

        # Every retained sentence must contribute to the name, and the name
        # must be supported by the union. This prevents unrelated sentences
        # from being added merely because the model concatenated them. When a
        # broad context sentence was dropped, a single remaining specific
        # source is still a valid conservative grounding result.
        single_specific_source = (
            len(contributing) == 1
            and bool(specific_contributing)
            and any(is_broad_overview_source(source) for _, source in exact_sources)
        )
        if len(contributing) < 2 and not single_specific_source:
            return None
        covered = set().union(*(item[2] for item in contributing))
        if not name_tokens.issubset(covered):
            return None

        contributing.sort(key=lambda item: item[0])
        source_indices = tuple(item[0] for item in contributing)
        source_texts = tuple(item[1] for item in contributing)
        scores = tuple(
            self.frozen.source_grounding_score(source, source)
            for source in source_texts
        )
        joined = " | ".join(source_texts)
        return joined, min(scores), MultiSentenceMatch(
            source_indices,
            source_texts,
            scores,
        )

    def _build_candidate_context(
        self,
        raw_text: str,
        source_id_prefix: str,
    ) -> None:
        payload, parse_error = self.frozen.extract_json_object(raw_text)
        if parse_error or not isinstance(payload, dict):
            return
        raw_criteria = payload.get("criteria", [])
        if not isinstance(raw_criteria, list):
            return

        queues: dict[str, deque[tuple[str, str, str, str]]] = defaultdict(deque)
        for index, item in enumerate(raw_criteria, start=1):
            if not isinstance(item, dict):
                continue
            source_text = self.frozen.normalise_text(item.get("sourceText"))
            name = self.frozen.normalise_text(item.get("name"))
            if source_text and name:
                criterion_key = f"{source_id_prefix}-criterion-{index}"
                support_name = self.frozen.normalise_text(
                    item.get("_nameValidationSupportName")
                ) or name
                queues[self._key(source_text)].append(
                    (criterion_key, support_name, source_text, name)
                )
        self._candidate_queues = queues

    def validate(
        self,
        original_validate: Callable[..., tuple[list[dict[str, Any]], dict[str, Any]]],
        original_find: Callable[..., tuple[str | None, float]],
        raw_text: str,
        allowed_sources: list[str],
        source_id_prefix: str,
        unsupported_token_detector: Callable[[str, str], list[str]] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        self._build_candidate_context(raw_text, source_id_prefix)

        validation_raw_text = raw_text
        payload, parse_error = self.frozen.extract_json_object(raw_text)
        if not parse_error and isinstance(payload, dict):
            raw_criteria = payload.get("criteria")
            if isinstance(raw_criteria, list):
                cleaned_criteria = [
                    {
                        key: value
                        for key, value in item.items()
                        if key != "_nameValidationSupportName"
                    }
                    if isinstance(item, dict)
                    else item
                    for item in raw_criteria
                ]
                if cleaned_criteria != raw_criteria:
                    clean_payload = dict(payload)
                    clean_payload["criteria"] = cleaned_criteria
                    validation_raw_text = json.dumps(
                        clean_payload,
                        ensure_ascii=False,
                    )

        def adapted_find(
            candidate: str,
            candidate_sources: list[str],
        ) -> tuple[str | None, float]:
            candidate_parts = [part.strip() for part in candidate.split("|")]
            non_generic_parts = [
                part
                for part in candidate_parts
                if part and not self.generic_duty_detector(part)
            ]
            if candidate_parts and not non_generic_parts:
                return None, 0.0
            cleaned_candidate = " | ".join(non_generic_parts) or candidate
            queue = self._candidate_queues.get(self._key(candidate))
            context = queue.popleft() if queue else None
            if context is not None:
                criterion_id, support_name, _, _output_name = context
                multi = self._find_multi_source_match(
                    cleaned_candidate,
                    support_name,
                    candidate_sources,
                )
                if multi is not None:
                    joined, score, metadata = multi
                    if len(metadata.source_texts) > 1:
                        self.matches[(source_id_prefix, criterion_id)] = metadata
                    return joined, score
            exact_sources = self._exact_sources_in_candidate(
                cleaned_candidate,
                candidate_sources,
            )
            has_broad_and_specific = (
                any(is_broad_overview_source(source) for _, source in exact_sources)
                and any(not is_broad_overview_source(source) for _, source in exact_sources)
            )
            if has_broad_and_specific:
                # Do not let the frozen fuzzy fallback select the broad scope
                # sentence when the proposed name is not supported by the
                # specific source(s). Rejecting is safer than contaminating
                # the criterion with unrelated evidence.
                return None, 0.0
            return original_find(cleaned_candidate, candidate_sources)

        previous_detector = self.frozen.criterion_name_unsupported_tokens
        self.frozen.find_grounded_source = adapted_find
        if unsupported_token_detector is not None:
            self.frozen.criterion_name_unsupported_tokens = (
                unsupported_token_detector
            )
        try:
            return original_validate(
                validation_raw_text,
                allowed_sources,
                source_id_prefix=source_id_prefix,
            )
        finally:
            self.frozen.find_grounded_source = original_find
            self.frozen.criterion_name_unsupported_tokens = previous_detector

    def restore_metadata(
        self,
        criteria: list[dict[str, Any]],
        diagnostics: dict[str, Any],
        source_id_prefix: str,
    ) -> None:
        """Replace frozen single-source metadata only for accepted multi-matches."""

        for criterion in criteria:
            source_criterion_ids = criterion.get("sourceCriterionIds", [])
            if not source_criterion_ids:
                continue
            match = self.matches.get((source_id_prefix, source_criterion_ids[0]))
            if match is None:
                continue
            criterion["sourceText"] = " | ".join(match.source_texts)
            criterion["sourceIds"] = [
                f"{source_id_prefix}-{index}"
                for index in match.source_indices
            ]
            criterion["groundingScores"] = [
                round(score, 4) for score in match.scores
            ]

        for grounding_match in diagnostics.get("groundingMatches", []):
            criterion_index = grounding_match.get("criterionIndex")
            criterion_id = f"{source_id_prefix}-criterion-{criterion_index}"
            match = self.matches.get((source_id_prefix, criterion_id))
            if match is None:
                continue
            grounding_match["matchedSourceTexts"] = list(match.source_texts)
            grounding_match["sourceIds"] = [
                f"{source_id_prefix}-{index}"
                for index in match.source_indices
            ]
            grounding_match["groundingScores"] = [
                round(score, 4) for score in match.scores
            ]
            grounding_match["score"] = round(min(match.scores), 4)
            diagnostics["multiSentenceGroundingCount"] = (
                diagnostics.get("multiSentenceGroundingCount", 0) + 1
            )


__all__ = ["MultiSentenceGroundingAdapter", "MultiSentenceMatch"]
