"""Deterministic extraction of explicit JD eligibility requirements.

This module handles only wording that is structured enough to be extracted
without semantic inference. It deliberately keeps hard eligibility separate
from the six scoring-criterion types.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .source_accounting import SourceRecord


_MINIMUM_EXPERIENCE = re.compile(
    r"\b(?:minimum|min\.?|at\s+least)\s*(?:of\s+)?"
    r"(?P<years>\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*years?\b",
    flags=re.IGNORECASE,
)
# A bare duration is a hard threshold only when it is explicitly tied to
# experience.  The optional intervening words cover common forms such as
# ``3 years' relevant experience`` without allowing the pattern to cross a
# sentence or list item boundary.
_BARE_EXPERIENCE = re.compile(
    r"\b(?P<years>\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*years?"
    r"(?:['’]s?)?(?:\s+of)?\s+"
    r"(?:(?![.;,\n])[A-Za-z][A-Za-z0-9/&+#-]*\s+){0,6}experience\b",
    flags=re.IGNORECASE,
)
_CGPA = re.compile(
    r"\b(?:cgpa|gpa)\s*(?:of|at\s+least|minimum|min\.?|[:>=-])*\s*"
    r"([0-4](?:\.\d{1,2})?)\b",
    flags=re.IGNORECASE,
)
_MANDATORY = re.compile(
    r"\b(?:mandatory|required|must\s+(?:have|hold|possess)|essential)\b",
    flags=re.IGNORECASE,
)
_PREFERRED = re.compile(
    r"\b(?:preferred|desirable|advantage|beneficial|nice\s+to\s+have)\b",
    flags=re.IGNORECASE,
)
_CERTIFICATE = re.compile(
    r"\b(?P<name>[A-Za-z][A-Za-z0-9&/+.()' -]{1,80}?)\s+"
    r"(?P<kind>certification|certificate|licen[cs]e)\b",
    flags=re.IGNORECASE,
)
_EDUCATION_FIELD = re.compile(
    r"\b(?:ph\.?d\.?|doctorate|master'?s?(?:\s+degree)?|mba|"
    r"bachelor'?s?(?:\s+degree)?|degree|diploma)\s+"
    r"(?:in|of)\s+(?P<field>[^.;]+)",
    flags=re.IGNORECASE,
)

_EDUCATION_LEVELS: tuple[tuple[int, str, re.Pattern[str]], ...] = (
    (
        6,
        "PhD",
        re.compile(r"\b(?:ph\.?d\.?|doctorate(?:\s+degree)?|doctoral\s+degree)\b", re.I),
    ),
    (5, "Master Degree", re.compile(r"\b(?:master'?s?(?: degree)?|mba)\b", re.I)),
    (
        4,
        "Bachelor Degree",
        re.compile(r"\b(?:bachelor'?s?(?: degree)?|degree)\b", re.I),
    ),
    (3, "Diploma", re.compile(r"\bdiploma\b", re.I)),
    (
        2,
        "STPM / Foundation / Matriculation",
        re.compile(r"\b(?:stpm|foundation|matriculation|a[ -]?levels?)\b", re.I),
    ),
    (1, "SPM", re.compile(r"\b(?:spm|pmr)\b", re.I)),
)
_EDUCATION_ALTERNATIVE = re.compile(r"(?:\bor\b|/)", re.IGNORECASE)

_LANGUAGES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("English", re.compile(r"\benglish\b", re.I)),
    ("Bahasa Malaysia", re.compile(r"\b(?:bahasa malaysia|bahasa melayu|malay)\b", re.I)),
    ("Mandarin", re.compile(r"\b(?:mandarin|chinese)\b", re.I)),
    ("Tamil", re.compile(r"\btamil\b", re.I)),
    ("Japanese", re.compile(r"\bjapanese\b", re.I)),
    ("Korean", re.compile(r"\bkorean\b", re.I)),
)


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _normalise_grammar_text(text: str) -> str:
    """Normalise punctuation variants without changing the retained source."""

    return text.replace("\u2018", "'").replace("\u2019", "'")


def _experience_option(years: float) -> str:
    if years <= 0:
        return "0 year"
    if years < 1:
        return "Internship"
    rounded = int(years)
    if rounded <= 4:
        return f"{rounded} year" + ("s" if rounded != 1 else "")
    if rounded < 8:
        return "5+ years"
    if rounded < 10:
        return "8+ years"
    return "10+ years"


def _education_level(text: str) -> tuple[int, str] | None:
    """Return the normalized hard-eligibility education threshold.

    Complete qualification phrases are collected before the generic
    ``degree`` keyword is considered.  When the JD explicitly joins
    qualifications with ``or`` or ``/``, those qualifications are accepted
    alternatives, so the lowest level is the minimum threshold.  For
    unrelated mentions, retain the historical highest-level behaviour.
    """

    candidates: list[tuple[int, int, int, str]] = []
    for rank, label, pattern in _EDUCATION_LEVELS:
        for match in pattern.finditer(text):
            raw = match.group(0).strip()
            # ``degree`` is the generic Bachelor-level fallback.  Do not let
            # it create a false lower alternative inside a complete phrase
            # such as ``Master's Degree`` or ``Doctorate Degree``.
            if (
                label == "Bachelor Degree"
                and re.fullmatch(r"degree", raw, flags=re.IGNORECASE)
                and any(
                    other_label != "Bachelor Degree"
                    and other_start <= match.start()
                    and other_end >= match.end()
                    for other_start, other_end, _other_rank, other_label in candidates
                )
            ):
                continue
            candidates.append((match.start(), match.end(), rank, label))

    # The level patterns are declared from highest to lowest, not by source
    # position.  Sort spans so alternative connectors can be inspected in the
    # original JD wording.
    candidates.sort(key=lambda item: (item[0], item[1]))
    if not candidates:
        return None

    levels = [(rank, label) for _start, _end, rank, label in candidates]
    for left, right in zip(candidates, candidates[1:]):
        between = text[left[1] : right[0]]
        if _EDUCATION_ALTERNATIVE.search(between):
            return min(levels, key=lambda item: item[0])
    return max(levels, default=None)


def _has_education_field(text: str) -> bool:
    match = _EDUCATION_FIELD.search(text)
    if not match:
        return False
    field = re.sub(
        r"\b(?:or\s+)?related\s+(?:field|discipline)s?\b.*$",
        "",
        match.group("field"),
        flags=re.IGNORECASE,
    ).strip(" ,/-")
    return bool(re.search(r"[A-Za-z]{2,}", field))


def _education_is_hard(text: str) -> bool:
    """Return whether the qualification wording expresses eligibility.

    A bare qualification is treated as a stated requirement for backwards
    compatibility, while an explicit preferred/desirable marker makes it a
    soft signal unless a mandatory marker occurs before it.  This keeps a
    preferred degree from becoming a hard threshold when the same sentence
    also contains a separate minimum-years requirement.
    """

    preferred = _PREFERRED.search(text)
    if preferred is None:
        return True
    mandatory = re.search(
        r"\b(?:minimum|min\.?|at\s+least|required|mandatory|must|essential)\b",
        text,
        flags=re.IGNORECASE,
    )
    return mandatory is not None and mandatory.start() < preferred.start()


def _has_experience_scope(text: str, threshold_match: re.Match[str]) -> bool:
    remainder = text[threshold_match.end() :]
    remainder = re.sub(r"^[\s,;:/-]*(?:of\s+)?(?:work(?:ing)?\s+)?experience\b", "", remainder, flags=re.I)
    remainder = re.sub(r"\b(?:is\s+)?(?:required|mandatory|essential|preferred)\b.*$", "", remainder, flags=re.I)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", remainder)
    insignificant = {"in", "of", "the", "a", "an", "field", "role", "minimum"}
    return any(token.casefold() not in insignificant for token in tokens)


def _experience_match(text: str) -> tuple[re.Match[str], bool] | None:
    """Return an explicit experience threshold and whether it is mandatory.

    Prefixes such as ``minimum`` and ``at least`` are unambiguously hard.  A
    bare numeric duration is accepted for the common JD shorthand, but a
    nearby preferred/desirable marker keeps it as soft evidence instead of
    silently turning it into an eligibility filter.
    """

    explicit = _MINIMUM_EXPERIENCE.search(text)
    if explicit is not None:
        return explicit, True

    bare = _BARE_EXPERIENCE.search(text)
    if bare is None:
        return None

    clause_start = max(
        text.rfind(mark, 0, bare.start()) for mark in (".", ";", ":", "\n")
    ) + 1
    clause_end_candidates = [
        text.find(mark, bare.end())
        for mark in (".", ";", ":", "\n")
        if text.find(mark, bare.end()) >= 0
    ]
    clause_end = min(clause_end_candidates, default=len(text))
    clause = text[clause_start:clause_end]
    if _PREFERRED.search(clause) and not _MANDATORY.search(clause):
        return bare, False
    return bare, True


def _mandatory_certificate_name(text: str) -> str | None:
    if not _MANDATORY.search(text):
        return None
    match = _CERTIFICATE.search(text)
    if not match:
        return None
    name = re.sub(
        r"^(?:a|an|the)\s+(?:valid\s+|current\s+)?",
        "",
        match.group("name").strip(),
        flags=re.IGNORECASE,
    )
    name = re.sub(
        r"^(?:valid|required|mandatory|current)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    return name or match.group("kind").title()


@dataclass(frozen=True)
class HardRequirement:
    kind: str
    value: Any
    source_ref: str
    source_id: str
    source_hash: str

    def safe_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "sourceRef": self.source_ref,
            "sourceId": self.source_id,
            "sourceHash": self.source_hash,
        }


@dataclass
class HardRequirementResult:
    eligibility_suggestions: dict[str, Any]
    requirements: list[HardRequirement] = field(default_factory=list)
    scoring_signals_by_ref: dict[str, set[str]] = field(default_factory=dict)
    exact_values: dict[str, Any] = field(default_factory=dict)

    def has_kind(self, source_ref: str, kind: str) -> bool:
        return any(
            item.source_ref == source_ref and item.kind == kind
            for item in self.requirements
        )

    def has_scoring_signal(self, source_ref: str, signal: str) -> bool:
        return signal in self.scoring_signals_by_ref.get(source_ref, set())

    def is_hard_only(self, source_ref: str) -> bool:
        return (
            any(item.source_ref == source_ref for item in self.requirements)
            and not self.scoring_signals_by_ref.get(source_ref)
        )

    def safe_audit(self) -> dict[str, Any]:
        return {
            "requirements": [item.safe_dict() for item in self.requirements],
            "exactValues": dict(self.exact_values),
        }


def extract_hard_requirements(
    _job: dict[str, Any],
    source_records: list[SourceRecord],
) -> HardRequirementResult:
    """Extract only explicit, structurally reliable hard requirements."""

    eligibility = {
        "minCGPA": None,
        "minExperience": None,
        "educationLevel": None,
        "requiredLanguage": None,
        "requiredLocation": None,
        "enabledFilters": [],
    }
    result = HardRequirementResult(eligibility_suggestions=eligibility)
    education_candidates: list[tuple[int, str]] = []
    experience_values: list[float] = []
    cgpa_values: list[float] = []
    required_languages: list[str] = []

    def add(record: SourceRecord, kind: str, value: Any) -> None:
        result.requirements.append(
            HardRequirement(
                kind=kind,
                value=value,
                source_ref=record.source_ref,
                source_id=record.source_id,
                source_hash=_source_hash(record.source_text),
            )
        )

    for record in source_records:
        text = _normalise_grammar_text(record.source_text)
        level = _education_level(text)
        if level:
            rank, label = level
            result.scoring_signals_by_ref.setdefault(record.source_ref, set()).add(
                "education_evidence"
            )
            if _education_is_hard(text):
                education_candidates.append((rank, label))
                add(record, "education_level", label)
            if _has_education_field(text):
                result.scoring_signals_by_ref.setdefault(record.source_ref, set()).add(
                    "education_field"
                )

        experience_info = _experience_match(text)
        if experience_info:
            experience, is_hard = experience_info
            years = float(experience.group("years"))
            if is_hard:
                experience_values.append(years)
                add(record, "minimum_experience", years)
            if _has_experience_scope(text, experience):
                result.scoring_signals_by_ref.setdefault(record.source_ref, set()).add(
                    "experience_scope"
                )

        cgpa = _CGPA.search(text)
        if cgpa:
            value = float(cgpa.group(1))
            cgpa_values.append(value)
            add(record, "minimum_cgpa", value)

        if _MANDATORY.search(text):
            for language, pattern in _LANGUAGES:
                if not pattern.search(text):
                    continue
                if language not in required_languages:
                    required_languages.append(language)
                add(record, "required_language", language)
                result.scoring_signals_by_ref.setdefault(record.source_ref, set()).add(
                    "required_language"
                )

        certificate_name = _mandatory_certificate_name(text)
        if certificate_name:
            add(record, "mandatory_certification", certificate_name)

    if education_candidates:
        eligibility["educationLevel"] = max(education_candidates)[1]
    if experience_values:
        exact_experience = max(experience_values)
        result.exact_values["minExperience"] = exact_experience
        eligibility["minExperience"] = _experience_option(exact_experience)
    if cgpa_values:
        exact_cgpa = max(cgpa_values)
        result.exact_values["minCGPA"] = exact_cgpa
        eligibility["minCGPA"] = exact_cgpa
    if required_languages:
        result.exact_values["requiredLanguages"] = required_languages
        eligibility["requiredLanguage"] = required_languages[0]
    eligibility["enabledFilters"] = [
        key
        for key in (
            "minCGPA",
            "minExperience",
            "educationLevel",
            "requiredLanguage",
            "requiredLocation",
        )
        if eligibility.get(key) is not None
    ]
    return result


__all__ = [
    "HardRequirement",
    "HardRequirementResult",
    "extract_hard_requirements",
]
