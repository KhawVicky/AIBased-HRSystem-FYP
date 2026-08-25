"""Stable JD source identities and post-validation accounting.

This module deliberately does not decide whether HR should care about a source.
It records how each supplied source was processed after semantic grouping and
deterministic validation: it contributed to a criterion, supplied an explicit
hard requirement, or could not be mapped without unsupported inference.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Iterable


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SourceRecord:
    source_ref: str
    source_id: str
    section: str
    source_text: str
    source_hash: str


def build_source_records(job: dict[str, Any]) -> list[SourceRecord]:
    """Build stable prompt references and caller-facing source identities."""

    records: list[SourceRecord] = []
    responsibility_index = 0
    for index, value in enumerate(job.get("responsibilities", []), start=1):
        text = _clean(value)
        if not text:
            continue
        responsibility_index += 1
        records.append(
            SourceRecord(
                source_ref=f"R{responsibility_index}",
                source_id=f"responsibilities-{index}",
                section="responsibilities",
                source_text=text,
                source_hash=_hash(text),
            )
        )

    seen_requirements: set[str] = set()
    qualification_index = 0
    for section in ("requirements", "qualifications"):
        for index, value in enumerate(job.get(section, []), start=1):
            text = _clean(value)
            identity = text.casefold()
            if not text or identity in seen_requirements:
                continue
            seen_requirements.add(identity)
            qualification_index += 1
            records.append(
                SourceRecord(
                    source_ref=f"Q{qualification_index}",
                    source_id=f"{section}-{index}",
                    section=section,
                    source_text=text,
                    source_hash=_hash(text),
                )
            )
    return records


def _criterion_parts(criterion: dict[str, Any]) -> list[str]:
    source_refs = criterion.get("sourceRefs")
    if isinstance(source_refs, list):
        return [_clean(value) for value in source_refs if _clean(value)]
    source_texts = criterion.get("sourceTexts")
    if isinstance(source_texts, list):
        return [_clean(value) for value in source_texts if _clean(value)]
    return [_clean(part) for part in str(criterion.get("sourceText", "")).split("|") if _clean(part)]


def build_source_accounting(
    source_records: Iterable[SourceRecord],
    criteria: list[dict[str, Any]],
    hard_requirements: Any,
    *,
    unknown_source_refs: Iterable[str] = (),
    duplicate_source_refs: Iterable[str] = (),
    model_unmapped_refs: Iterable[str] = (),
    generic_duty_detector: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Return a safe, source-complete processing outcome audit.

    A source is never removed because of this accounting. The outcome only
    describes what the already validated pipeline did with it.
    """

    records = list(source_records)
    by_source_id = {record.source_id: record for record in records}
    by_source_ref = {record.source_ref: record for record in records}
    # Keep all records for duplicate text. Responsibilities are intentionally
    # not de-duplicated because two separate JD bullets are both evidence and
    # must remain traceable even when their wording happens to match.
    by_text: dict[str, list[SourceRecord]] = {}
    for record in records:
        by_text.setdefault(record.source_text.casefold(), []).append(record)
    criterion_ids_by_ref: dict[str, list[str]] = {record.source_ref: [] for record in records}

    for criterion in criteria:
        criterion_id = _clean(criterion.get("criterionId"))
        if not criterion_id:
            continue
        linked_records: list[SourceRecord] = []
        raw_source_ids = criterion.get("sourceIds", [])
        if isinstance(raw_source_ids, str):
            raw_source_ids = [raw_source_ids]
        for source_id in raw_source_ids if isinstance(raw_source_ids, list) else []:
            cleaned_source_id = _clean(source_id)
            record = by_source_id.get(cleaned_source_id) or by_source_ref.get(
                cleaned_source_id.upper()
            )
            if record is not None:
                linked_records.append(record)
        for part in _criterion_parts(criterion):
            ref_record = by_source_ref.get(part.upper())
            if ref_record is not None and ref_record not in linked_records:
                linked_records.append(ref_record)
            for record in by_text.get(part.casefold(), []):
                if record not in linked_records:
                    linked_records.append(record)
        for record in linked_records:
            criterion_ids_by_ref.setdefault(record.source_ref, []).append(criterion_id)

    hard_by_ref: dict[str, list[str]] = {record.source_ref: [] for record in records}
    for item in getattr(hard_requirements, "requirements", []) or []:
        source_ref = _clean(getattr(item, "source_ref", ""))
        kind = _clean(getattr(item, "kind", ""))
        if source_ref in hard_by_ref and kind:
            hard_by_ref[source_ref].append(kind)

    model_unmapped = {
        str(ref).strip().upper()
        for ref in model_unmapped_refs
        if str(ref).strip()
    }
    unknown_refs = {
        str(ref).strip().upper()
        for ref in unknown_source_refs
        if str(ref).strip()
    }
    duplicate_refs = {
        str(ref).strip().upper()
        for ref in duplicate_source_refs
        if str(ref).strip()
    }
    sources: list[dict[str, Any]] = []
    for record in records:
        criterion_ids = list(dict.fromkeys(criterion_ids_by_ref.get(record.source_ref, [])))
        hard_kinds = list(dict.fromkeys(hard_by_ref.get(record.source_ref, [])))
        if criterion_ids:
            outcome = "criterion_contribution"
            reason = "Source text is preserved under a grounded scoring criterion."
            mapped = True
        elif hard_kinds and getattr(hard_requirements, "is_hard_only", lambda _ref: False)(record.source_ref):
            outcome = "hard_requirement_processing"
            reason = "Source is represented by deterministic eligibility extraction; no separate scoring evidence was formed."
            mapped = False
        elif generic_duty_detector is not None and generic_duty_detector(record.source_text):
            outcome = "not_mapped_grounding_safeguard"
            reason = "Source is retained for audit but does not provide a defensible candidate-assessable capability."
            mapped = False
        elif record.source_ref in model_unmapped:
            outcome = "not_mapped_after_model_review"
            reason = "No grounded criterion was returned for this source; HR may review the original JD evidence."
            mapped = False
        else:
            outcome = "not_mapped_after_validation"
            reason = "No grounded criterion survived deterministic validation; the original source remains traceable."
            mapped = False
        sources.append(
            {
                "sourceRef": record.source_ref,
                "sourceId": record.source_id,
                "sourceHash": record.source_hash,
                "section": record.section,
                "processingOutcome": outcome,
                "mapped": mapped,
                "hardRequirementKinds": hard_kinds,
                "generatedCriterionIds": criterion_ids,
                "reason": reason,
            }
        )

    return {
        "valid": not unknown_refs and not duplicate_refs,
        "sources": sources,
        "unknownSourceRefs": sorted(unknown_refs),
        "duplicateSourceRefs": sorted(duplicate_refs),
        "unmappedSourceRefs": [item["sourceRef"] for item in sources if not item["mapped"]],
    }


__all__ = ["SourceRecord", "build_source_records", "build_source_accounting"]
