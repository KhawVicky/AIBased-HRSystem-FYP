"""Role-aware source triage contracts for the enhanced criteria path."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Literal

from .hard_requirements import HardRequirementResult
from .model_output import normalise_model_output


Disposition = Literal["CORE", "SUPPORTING", "IGNORE"]
CriterionUse = Literal["NONE", "STRENGTHEN_ONLY", "STANDALONE_ELIGIBLE"]
Importance = Literal["high", "medium", "low"]

_DISPOSITIONS = {"CORE", "SUPPORTING", "IGNORE"}
_CRITERION_USES = {"NONE", "STRENGTHEN_ONLY", "STANDALONE_ELIGIBLE"}
_IMPORTANCE = {"high", "medium", "low"}


TRIAGE_SYSTEM_PROMPT = """You perform role-aware evidence triage before resume-scoring criteria are formed.

Read the job title, department and every supplied JD source as one complete role.
Classify each source exactly once as CORE, SUPPORTING or IGNORE. These are
internal evidence-significance labels, never scoring-criterion types.

For every source decide whether it: (1) represents an actual role capability,
(2) can meaningfully differentiate candidates, (3) can reasonably be evidenced
from resume evidence, and (4) is important relative to the complete role and its
overall responsibility distribution.

CORE means central, differentiating, resume-assessable evidence that must be
represented in scoring. SUPPORTING means real but secondary evidence. IGNORE
means routine participation, generic assigned work, traits, boilerplate, or work
that is not useful for resume scoring in this role context. The same activity can
have different significance in different roles; do not apply a global keyword
decision.

For SUPPORTING evidence set criterionUse to:
- NONE when it should remain supporting-only;
- STRENGTHEN_ONLY when it may strengthen a CORE capability but must not create a
  standalone criterion;
- STANDALONE_ELIGIBLE only when it is a distinct resume-assessable capability
  with meaningful candidate differentiation.

CORE always uses STANDALONE_ELIGIBLE. IGNORE always uses NONE. Return a short,
defensible role-relative reason and high, medium or low importance. Do not form
criteria, assign a six-type taxonomy, calculate weights, infer evidence, or make
an eligibility decision. Return valid JSON only without markdown."""


_TRIAGE_OUTPUT_SHAPE = {
    "sourceDispositions": [
        {
            "sourceRef": "<one supplied R#/Q# label>",
            "disposition": "<CORE, SUPPORTING or IGNORE>",
            "resumeAssessable": "<true or false>",
            "importance": "<high, medium or low>",
            "criterionUse": "<NONE, STRENGTHEN_ONLY or STANDALONE_ELIGIBLE>",
            "reason": "<short role-relative reason>",
        }
    ]
}


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
    """Build stable prompt refs plus caller-facing source identities."""

    records: list[SourceRecord] = []
    for index, value in enumerate(job.get("responsibilities", []), start=1):
        text = _clean(value)
        if not text:
            continue
        records.append(
            SourceRecord(
                source_ref=f"R{len([item for item in records if item.section == 'responsibilities']) + 1}",
                source_id=f"responsibilities-{index}",
                section="responsibilities",
                source_text=text,
                source_hash=_hash(text),
            )
        )

    seen_requirements: set[str] = set()
    q_index = 0
    for section in ("requirements", "qualifications"):
        for index, value in enumerate(job.get(section, []), start=1):
            text = _clean(value)
            identity = text.casefold()
            if not text or identity in seen_requirements:
                continue
            seen_requirements.add(identity)
            q_index += 1
            records.append(
                SourceRecord(
                    source_ref=f"Q{q_index}",
                    source_id=f"{section}-{index}",
                    section=section,
                    source_text=text,
                    source_hash=_hash(text),
                )
            )
    return records


def build_evidence_triage_messages(
    job: dict[str, Any], source_records: list[SourceRecord]
) -> list[dict[str, str]]:
    """Build the semantic triage call over the complete JD evidence set."""

    sources = [
        {
            "sourceRef": item.source_ref,
            "section": item.section,
            "text": item.source_text,
        }
        for item in source_records
    ]
    user_prompt = (
        f"Job title:\n{_clean(job.get('jobTitle'))}\n\n"
        f"Department:\n{_clean(job.get('department'))}\n\n"
        "Complete JD sources:\n"
        + json.dumps(sources, ensure_ascii=False, indent=2)
        + "\n\nReturn this exact JSON structure:\n"
        + json.dumps(_TRIAGE_OUTPUT_SHAPE, ensure_ascii=False, indent=2)
        + "\n\nReturn every supplied sourceRef exactly once and no unknown refs. "
        "The angle-bracket text describes fields and is not example content."
    )
    return [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_evidence_triage_retry_messages(
    job: dict[str, Any],
    source_records: list[SourceRecord],
    previous_raw_output: str,
    errors: list[str],
) -> list[dict[str, str]]:
    """Request one schema/accountability repair without changing semantics."""

    base = build_evidence_triage_messages(job, source_records)
    base[1]["content"] = (
        "Repair the previous triage response. Keep valid role-relative decisions, "
        "but return every supplied source exactly once using the closed enums and "
        "field types. Return a complete corrected JSON object, not a patch.\n\n"
        "Validation errors:\n"
        + json.dumps(errors, ensure_ascii=False)
        + "\n\n"
        + base[1]["content"]
        + "\n\nPrevious response for diagnosis only:\n"
        + previous_raw_output
    )
    return base


@dataclass(frozen=True)
class SourceDisposition:
    source_ref: str
    source_id: str
    source_hash: str
    disposition: Disposition
    resume_assessable: bool
    importance: Importance
    criterion_use: CriterionUse
    reason: str
    decision_source: str = "qwen_role_triage"
    processing_outcome: str = "criterion_eligible"

    def safe_dict(self) -> dict[str, Any]:
        return {
            "sourceRef": self.source_ref,
            "sourceId": self.source_id,
            "sourceHash": self.source_hash,
            "disposition": self.disposition,
            "resumeAssessable": self.resume_assessable,
            "importance": self.importance,
            "criterionUse": self.criterion_use,
            "reason": self.reason,
            "decisionSource": self.decision_source,
            "processingOutcome": self.processing_outcome,
        }


@dataclass
class TriageResult:
    dispositions: list[SourceDisposition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing_source_refs: set[str] = field(default_factory=set)
    duplicate_source_refs: set[str] = field(default_factory=set)
    unknown_source_refs: set[str] = field(default_factory=set)
    parse_error: str | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.parse_error is None

    @property
    def by_ref(self) -> dict[str, SourceDisposition]:
        return {item.source_ref: item for item in self.dispositions}

    @property
    def required_source_refs(self) -> set[str]:
        return {
            item.source_ref
            for item in self.dispositions
            if item.disposition == "CORE"
        }

    @property
    def formation_source_refs(self) -> set[str]:
        return {
            item.source_ref
            for item in self.dispositions
            if item.disposition == "CORE"
            or (
                item.disposition == "SUPPORTING"
                and item.criterion_use != "NONE"
            )
        }

    @property
    def strengthen_only_source_refs(self) -> set[str]:
        return {
            item.source_ref
            for item in self.dispositions
            if item.disposition == "SUPPORTING"
            and item.criterion_use == "STRENGTHEN_ONLY"
        }

    def safe_audit(
        self, criteria: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        criteria = criteria or []
        linked_by_source_id: dict[str, list[str]] = {}
        for criterion in criteria:
            criterion_id = _clean(criterion.get("criterionId"))
            for source_id in criterion.get("sourceIds", []) or []:
                cleaned_source_id = _clean(source_id)
                if cleaned_source_id and criterion_id:
                    linked_by_source_id.setdefault(cleaned_source_id, []).append(
                        criterion_id
                    )
        sources: list[dict[str, Any]] = []
        for item in self.dispositions:
            entry = item.safe_dict()
            linked = list(dict.fromkeys(linked_by_source_id.get(item.source_id, [])))
            entry["generatedCriterionIds"] = linked
            if linked:
                entry["processingOutcome"] = "criterion_contribution"
            sources.append(entry)
        return {
            "valid": self.is_valid,
            "sources": sources,
            "missingSourceRefs": sorted(self.missing_source_refs),
            "unknownSourceRefs": sorted(self.unknown_source_refs),
            "duplicateSourceRefs": sorted(self.duplicate_source_refs),
        }


def _normalise_disposition(
    raw_item: dict[str, Any],
    record: SourceRecord,
    errors: list[str],
) -> SourceDisposition | None:
    disposition = _clean(raw_item.get("disposition")).upper()
    criterion_use = _clean(raw_item.get("criterionUse")).upper()
    importance = _clean(raw_item.get("importance")).casefold()
    reason = " ".join(_clean(raw_item.get("reason")).split())[:240]
    resume_assessable = raw_item.get("resumeAssessable")
    if disposition not in _DISPOSITIONS:
        errors.append(f"{record.source_ref} has invalid disposition {disposition!r}.")
        return None
    if criterion_use not in _CRITERION_USES:
        errors.append(f"{record.source_ref} has invalid criterionUse {criterion_use!r}.")
        return None
    if importance not in _IMPORTANCE:
        errors.append(f"{record.source_ref} has invalid importance {importance!r}.")
        return None
    if not isinstance(resume_assessable, bool):
        errors.append(f"{record.source_ref} resumeAssessable must be boolean.")
        return None
    if not reason:
        errors.append(f"{record.source_ref} requires a short reason.")
        return None

    if disposition == "CORE":
        criterion_use = "STANDALONE_ELIGIBLE"
        resume_assessable = True
        outcome = "criterion_required"
    elif disposition == "IGNORE":
        criterion_use = "NONE"
        resume_assessable = False
        outcome = "ignored"
    else:
        outcome = (
            "supporting_only"
            if criterion_use == "NONE"
            else "criterion_eligible"
        )

    return SourceDisposition(
        source_ref=record.source_ref,
        source_id=record.source_id,
        source_hash=record.source_hash,
        disposition=disposition,  # type: ignore[arg-type]
        resume_assessable=resume_assessable,
        importance=importance,  # type: ignore[arg-type]
        criterion_use=criterion_use,  # type: ignore[arg-type]
        reason=reason,
        processing_outcome=outcome,
    )


def normalise_triage_output(
    raw_output: str,
    source_records: list[SourceRecord],
    *,
    hard_requirements: HardRequirementResult,
    generic_duty_detector: Callable[[str], bool],
) -> TriageResult:
    """Validate closed triage output and apply only certainty-based overrides."""

    normalised, _fence_applied = normalise_model_output(raw_output)
    try:
        payload = json.loads(normalised)
    except json.JSONDecodeError as error:
        refs = {item.source_ref for item in source_records}
        return TriageResult(
            parse_error=f"Malformed triage JSON: {error.msg}",
            errors=["Triage output is not valid JSON."],
            missing_source_refs=refs,
        )
    if not isinstance(payload, dict) or not isinstance(
        payload.get("sourceDispositions"), list
    ):
        refs = {item.source_ref for item in source_records}
        return TriageResult(
            parse_error="sourceDispositions is not a list.",
            errors=["Triage output must contain a sourceDispositions list."],
            missing_source_refs=refs,
        )

    records_by_ref = {item.source_ref: item for item in source_records}
    seen: set[str] = set()
    duplicates: set[str] = set()
    unknown: set[str] = set()
    dispositions: list[SourceDisposition] = []
    errors: list[str] = []
    for index, raw_item in enumerate(payload["sourceDispositions"], start=1):
        if not isinstance(raw_item, dict):
            errors.append(f"Triage item {index} is not an object.")
            continue
        source_ref = _clean(raw_item.get("sourceRef")).upper()
        if source_ref in seen:
            duplicates.add(source_ref)
            continue
        seen.add(source_ref)
        record = records_by_ref.get(source_ref)
        if record is None:
            unknown.add(source_ref or "<blank>")
            continue
        item = _normalise_disposition(raw_item, record, errors)
        if item is not None:
            dispositions.append(item)

    missing = set(records_by_ref) - seen
    if duplicates:
        errors.append("Duplicate source refs: " + ", ".join(sorted(duplicates)))
    if unknown:
        errors.append("Unknown source refs: " + ", ".join(sorted(unknown)))
    if missing:
        errors.append("Missing source refs: " + ", ".join(sorted(missing)))

    overridden: list[SourceDisposition] = []
    for item in dispositions:
        record = records_by_ref[item.source_ref]
        if generic_duty_detector(record.source_text):
            overridden.append(
                replace(
                    item,
                    disposition="IGNORE",
                    resume_assessable=False,
                    importance="low",
                    criterion_use="NONE",
                    reason="Generic assigned duty has no concrete resume evidence.",
                    decision_source="deterministic_generic_duty",
                    processing_outcome="ignored",
                )
            )
        elif hard_requirements.is_hard_only(item.source_ref):
            overridden.append(
                replace(
                    item,
                    disposition="IGNORE",
                    resume_assessable=False,
                    importance="low",
                    criterion_use="NONE",
                    reason="Explicit hard requirement has no separate scoring signal.",
                    decision_source="deterministic_hard_only",
                    processing_outcome="hard_requirement",
                )
            )
        else:
            overridden.append(item)

    return TriageResult(
        dispositions=overridden,
        errors=errors,
        missing_source_refs=missing,
        duplicate_source_refs=duplicates,
        unknown_source_refs=unknown,
    )


__all__ = [
    "CriterionUse",
    "Disposition",
    "SourceDisposition",
    "SourceRecord",
    "TriageResult",
    "build_evidence_triage_messages",
    "build_evidence_triage_retry_messages",
    "build_source_records",
    "normalise_triage_output",
]
