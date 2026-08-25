"""Deterministic recovery for explicit JD requirements.

This module deliberately handles only requirements that can be identified from
the requirement sentence itself. Broad job capability extraction remains a
model responsibility.
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any, Callable


ALLOWED_RECOVERY_TYPES = {
    "explicit_education_field",
    "explicit_education_level",
    "explicit_experience",
    "explicit_language",
    "explicit_certification",
    "explicit_law_or_standard",
    "explicit_tool_or_system",
}

IMPORTANCE_VALUES = {"high", "medium", "low"}

_EDUCATION_FIELD_RE = re.compile(
    r"\b(?:diploma|degree|bachelor(?:['\u2019]s)?|master(?:['\u2019]s)?|phd|"
    r"academic qualification|professional qualification)\b\s+"
    r"(?:in|of)\s+"
    r"(?P<field>[A-Za-z][A-Za-z0-9&/(),.\- ]{2,120}?)(?="
    r"\s+(?:is|are|was|were)\s+(?:required|essential|preferred|desirable)"
    r"\b|[.;]|$)",
    re.IGNORECASE,
)
_EDUCATION_LEVEL_RE = re.compile(
    r"\b(?:stpm|foundation|matriculation|a[ -]?levels?|spm|pmr|"
    r"diploma|degree|bachelor(?:['\u2019]s)?|master(?:['\u2019]s)?|"
    r"mba|ph\.?d\.?|doctorate|doctoral degree|academic qualification|"
    r"professional qualification)\b",
    re.IGNORECASE,
)

_EXPERIENCE_PATTERNS = (
    re.compile(
        r"\b(?:at\s+least|minimum|min\.?)\s+"
        r"(?:\d+(?:\s*[-\u2013]\s*\d+)?\+?|"
        r"one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"years?(?:\s+of)?\s+experience\s+(?:in|within|across|with)\s+"
        r"(?P<scope>[^.;]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:at\s+least|minimum|min\.?)\s+"
        r"(?:\d+(?:\s*[-\u2013]\s*\d+)?\+?|"
        r"one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"years?\s+of\s+(?P<scope>[^.;]+?)\s+experience"
        r"(?P<tail>[^.;]*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexperience\s+(?:in|within|across|with|delivering|working\s+in)\s+"
        r"(?P<scope>[^.;]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<scope>[A-Za-z][A-Za-z0-9&/(),\- ]{2,90}?)\s+"
        r"experience(?P<tail>[^.;]*)",
        re.IGNORECASE,
    ),
)

_EXPERIENCE_CONTEXT_RE = re.compile(
    r"\b(?:environment|industry|scope|team|supervis\w*|lead\w*|"
    r"responsibil\w*|deliver\w*|production|regulated|high[- ]volume|"
    r"multi[- ]site|including|scale|result\w*|outcome\w*)\b",
    re.IGNORECASE,
)
_THRESHOLD_RE = re.compile(
    r"\b(?:minimum|at\s+least|\d+\+?|one|two|three|four|five|six|"
    r"seven|eight|nine|ten)\b.*\byears?\b",
    re.IGNORECASE,
)

_TOOL_OR_SYSTEM_REQUIREMENT_RE = re.compile(
    r"\bexperience\s+(?:using|with)\s+(?:an?\s+|the\s+)?"
    r"(?P<subject>[^.;]+?\b(?:application|database|framework|platform|"
    r"software|suite|system|systems|technology|tool|tools)\b[^.;]*?)"
    r"(?=\s+(?:is|are|was|were)\s+(?:an?\s+)?(?:advantage|preferred|"
    r"required|desirable|essential)\b|[.;]|$)",
    re.IGNORECASE,
)

_LANGUAGE_RE = re.compile(
    r"\b(?:English|Bahasa Malaysia|Bahasa Melayu|Malay|Mandarin|Chinese|"
    r"Japanese|Tamil|Korean|Thai|Vietnamese|Arabic|German|French|Spanish)\b",
    re.IGNORECASE,
)
_LANGUAGE_CONTEXT_RE = re.compile(
    r"\b(?:proficien\w*|fluen\w*|written|spoken|language|communicat\w*|"
    r"serve|customer\w*|client\w*|office|report\w*|required|preferred|"
    r"advantage|liais\w*)\b",
    re.IGNORECASE,
)
_PREFERRED_RE = re.compile(
    r"\b(?:preferred|desirable|advantage|added\s+advantage|beneficial)\b",
    re.IGNORECASE,
)
_MANDATORY_RE = re.compile(
    r"\b(?:mandatory|required|must|essential|compulsory)\b",
    re.IGNORECASE,
)
_CERTIFICATION_RE = re.compile(
    r"\b(?P<credential>(?:[A-Z]{2,}[A-Za-z0-9&/().+\-]*|"
    r"[A-Z][a-z]+)(?:\s+(?:[A-Z][A-Za-z0-9&/().+\-]*|"
    r"[a-z][A-Za-z0-9&/().+\-]*)){0,5}\s+"
    r"(?:certification|certificate|licen[cs]e|registration))\b",
)
_CERTIFIED_TITLE_RE = re.compile(
    r"\b(?P<credential>(?:[A-Z][A-Za-z0-9+./\-]*\s+){1,5}"
    r"Certified(?:\s+[A-Z][A-Za-z0-9+./\-]*){0,5})\b"
)
_GENERIC_CERTIFICATION_RE = re.compile(
    r"^\s*(?:relevant|professional|appropriate|recognised|recognized)\s+"
    r"(?:certification|certificate|qualification)\s*$",
    re.IGNORECASE,
)

_ISO_RE = re.compile(r"\bISO\s+\d{3,5}(?:\s*:\s*\d{4})?\b", re.IGNORECASE)
_FORMAL_STANDARD_CODE_RE = re.compile(
    r"\b(?:OHSAS|IATF|IEC|ASTM|GDPR)\s*\d*[A-Z0-9-]*\b",
    re.IGNORECASE,
)
_ACRONYM_REGULATION_RE = re.compile(
    r"\b(?P<subject>[A-Z]{2,}(?:\s*,?\s*(?:and\s+)?[A-Z]{2,}){0,5})\s+"
    r"regulations?\b"
)
_LAW_TOPIC_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,7}\s+"
    r"(?:Act|Law|Regulation|Regulations|Code|Standard|Framework))\b"
)
_LABOUR_LAW_RE = re.compile(
    r"\b(?:Malaysian\s+labou?r\s+law\w*|employment\s+law\w*|"
    r"labou?r\s+law\w*|employment\s+regulation\w*)\b",
    re.IGNORECASE,
)
_E_INVOICE_RE = re.compile(r"\b(?:Malaysia\s+)?e[- ]?invoice\b", re.IGNORECASE)
_EXPLICIT_FORMAL_RE = re.compile(
    r"\b(?:formal\s+(?:procedures?|business rules?|principles?)|"
    r"statutory\s+requirements?|financial\s+controls?|"
    r"professional\s+principles?)\b",
    re.IGNORECASE,
)
_FORMAL_INTRO_RE = re.compile(
    r"\b(?:knowledge|understanding|familiarity)\s+of\s+"
    r"(?P<subject>[^.;]+)",
    re.IGNORECASE,
)

_SMALL_WORDS = {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with"}
_KNOWN_CAPITALISATIONS = {
    "acca": "ACCA",
    "api": "API",
    "aws": "AWS",
    "b2b": "B2B",
    "cad": "CAD",
    "cfa": "CFA",
    "cpa": "CPA",
    "crm": "CRM",
    "erp": "ERP",
    "excel": "Excel",
    "hr": "HR",
    "hris": "HRIS",
    "iso": "ISO",
    "it": "IT",
    "itil": "ITIL",
    "qms": "QMS",
    "spc": "SPC",
    "wms": "WMS",
}


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _title_phrase(value: str) -> str:
    cleaned = _normalise_text(value).strip(" ,.;:")
    words = cleaned.split()
    formatted: list[str] = []
    for index, word in enumerate(words):
        raw = word.strip(" ,.;:")
        lower = raw.casefold()
        if lower in _KNOWN_CAPITALISATIONS:
            formatted.append(_KNOWN_CAPITALISATIONS[lower])
        elif index and lower in _SMALL_WORDS:
            formatted.append(lower)
        else:
            formatted.append(raw[:1].upper() + raw[1:])
    return " ".join(formatted)


def _strip_requirement_suffix(value: str) -> str:
    cleaned = _normalise_text(value)
    cleaned = re.sub(
        r"\s+(?:is|are|was|were)?\s*(?:required|essential|preferred|"
        r"desirable|beneficial|an?\s+advantage|an?\s+added\s+advantage)\s*[.;]?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" ,.;:")


def _education_label(field: str) -> str | None:
    cleaned = _strip_requirement_suffix(field)
    cleaned = re.sub(
        r"\s+(?:or|and)\s+(?:a|an)\s+(?:related|relevant)\s+"
        r"(?:field|discipline|area)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip(" ,.;:")
    if not cleaned or re.fullmatch(
        r"(?:any|a|an|related|relevant)?\s*(?:field|discipline|area)?",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return None

    lower = cleaned.casefold()
    if re.search(r"computer\s+science|software\s+engineering|"
                 r"information\s+technology|computing", lower):
        label = "Computing"
    elif re.search(r"accounting|finance", lower):
        label = "Accounting and Finance"
    elif re.search(r"business\s+administration", lower) and re.search(
        r"marketing",
        lower,
    ):
        label = "Business and Marketing"
    elif re.search(r"business\s+administration", lower):
        label = "Business Administration"
    elif re.search(r"human\s+resources|industrial\s+relations", lower):
        label = "Human Resources"
    elif re.search(r"engineering|materials\s+science", lower):
        label = "Engineering"
    else:
        label = _title_phrase(cleaned)
    return f"{label} Education" if label else None


def _extract_education(text: str) -> str | None:
    match = _EDUCATION_FIELD_RE.search(text)
    return _education_label(match.group("field")) if match else None


def _education_name_and_recovery(text: str) -> tuple[str, str, str] | None:
    """Return a grounded education criterion without inventing a field.

    A direct ``degree/diploma in ...`` construction gets the existing
    field-specific name.  A level-only statement still supports the neutral
    ``Education`` soft dimension, while its deterministic level remains an
    eligibility value when the wording is mandatory.
    """

    field_name = _extract_education(text)
    if field_name:
        return (
            field_name,
            "explicit_education_field",
            "The requirement names a specific education field.",
        )
    if _EDUCATION_LEVEL_RE.search(text):
        return (
            "Education",
            "explicit_education_level",
            "The requirement states an education level without naming a field.",
        )
    return None


def _experience_name_and_importance(text: str) -> tuple[str, str] | None:
    cleaned = _strip_requirement_suffix(text)
    match = None
    for pattern in _EXPERIENCE_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            break
    if match is None:
        return None

    scope = _normalise_text(match.groupdict().get("scope", ""))
    tail = _normalise_text(match.groupdict().get("tail", ""))
    if tail and re.search(r"\b(?:including|covering|with|in)\b", tail, re.I):
        scope = f"{scope} {tail}"
    scope = re.sub(r"\b(?:is|are|was|were)\s*$", "", scope, flags=re.I)
    scope = re.sub(r"\b(?:required|essential|preferred|desirable)\b", "", scope, flags=re.I)
    scope = re.sub(r"\s+", " ", scope).strip(" ,.;:")
    scope = re.sub(r"^(?:the|a|an)\s+", "", scope, flags=re.IGNORECASE)
    scope = re.sub(r"\b(?:of|in)\s+experience\b", "", scope, flags=re.I)
    scope = re.sub(
        r"^(?:minimum|at\s+least)\s+"
        r"(?:\d+(?:\s*[-\u2013]\s*\d+)?\+?|one|two|three|four|five|six|"
        r"seven|eight|nine|ten)\s+years?(?:\s+of)?\s*",
        "",
        scope,
        flags=re.IGNORECASE,
    )
    if not scope or re.fullmatch(r"(?:the|relevant|related|professional)\s*", scope, re.I):
        return None

    name_scope = re.sub(r"\s+including\s+.*$", "", scope, flags=re.IGNORECASE)
    name_scope = name_scope.replace("-", " ")
    environment_match = re.search(
        r"\s+in\s+(?:a|an)\s+(?P<environment>.+)$",
        name_scope,
        re.IGNORECASE,
    )
    if environment_match:
        domain = name_scope[: environment_match.start()].strip()
        environment = environment_match.group("environment").strip()
        environment = re.sub(r"\benvironment\b", "", environment, flags=re.IGNORECASE).strip()
        domain = re.sub(r"\bquality\s+assurance\b", "quality", domain, flags=re.IGNORECASE)
        name_scope = f"{environment} {domain}".strip()
    name_scope = re.sub(r"\bapplications\b", "application", name_scope, flags=re.IGNORECASE)
    name = _title_phrase(name_scope)
    if not name.casefold().endswith("experience"):
        name = f"{name} Experience"
    contextual = bool(_EXPERIENCE_CONTEXT_RE.search(scope))
    minimum_only = bool(_THRESHOLD_RE.search(cleaned)) and not contextual
    return name, "low" if minimum_only else "medium"


def _extract_tool_or_system(text: str) -> tuple[str, str] | None:
    """Return an explicitly required named tool/system capability."""

    match = _TOOL_OR_SYSTEM_REQUIREMENT_RE.search(text)
    if match is None:
        return None
    subject = _normalise_text(match.group("subject"))
    subject = re.sub(
        r"\s+(?:such\s+as|including|for\s+example)\s+.*$",
        "",
        subject,
        flags=re.IGNORECASE,
    ).strip(" ,.;:")
    subject = re.sub(r"^(?:a|an|the)\s+", "", subject, flags=re.IGNORECASE)
    if not subject or len(subject.split()) > 8:
        return None
    name = _title_phrase(subject)
    return name, "low" if _PREFERRED_RE.search(text) else "medium"


def _extract_languages(text: str) -> tuple[str, str] | None:
    if not _LANGUAGE_CONTEXT_RE.search(text):
        return None
    names: list[str] = []
    canonical = {
        "bahasa malaysia": "Bahasa Malaysia",
        "bahasa melayu": "Bahasa Melayu",
        "english": "English",
        "malay": "Malay",
        "mandarin": "Mandarin",
        "chinese": "Chinese",
        "japanese": "Japanese",
        "tamil": "Tamil",
        "korean": "Korean",
        "thai": "Thai",
        "vietnamese": "Vietnamese",
        "arabic": "Arabic",
        "german": "German",
        "french": "French",
        "spanish": "Spanish",
    }
    for match in _LANGUAGE_RE.finditer(text):
        language = canonical[match.group(0).casefold()]
        if language not in names:
            names.append(language)
    if not names:
        return None
    importance = "low" if _PREFERRED_RE.search(text) else "medium"
    return f"{' and '.join(names)} Language", importance


def _extract_certification(text: str) -> tuple[str, str] | None:
    if not _PREFERRED_RE.search(text):
        return None
    match = _CERTIFIED_TITLE_RE.search(text) or _CERTIFICATION_RE.search(text)
    if match is None:
        return None
    credential = _normalise_text(match.group("credential")).strip(" ,.;:")
    credential = re.sub(r"^(?:the|a|an)\s+", "", credential, flags=re.IGNORECASE)
    credential = re.sub(r"\s+(?:is\s+)?(?:required|preferred|desirable|"
                       r"an?\s+advantage)\b.*$", "", credential, flags=re.I)
    if re.search(
        r"\b(?:communication|skill|relevant|professional|appropriate|"
        r"qualified|qualification)\w*\b",
        credential,
        re.IGNORECASE,
    ):
        return None
    credential = _title_phrase(credential)
    if not credential or _GENERIC_CERTIFICATION_RE.fullmatch(credential):
        return None
    return credential, "low"


def _extract_formal_knowledge(text: str) -> str | None:
    # A named ISO or standard used as a certification/licence requirement is
    # handled by the certification boundary. It must not be duplicated as
    # domain knowledge, whether the certification is preferred or mandatory.
    if re.search(
        r"\b(?:certification|certificate|licen[cs]e|registration)\b",
        text,
        re.IGNORECASE,
    ):
        return None
    subjects: list[str] = []
    iso_values = [match.group(0).upper().replace(" ", " ") for match in _ISO_RE.finditer(text)]
    if iso_values:
        subjects.extend(dict.fromkeys(iso_values))
    standard_values = [
        _title_phrase(match.group(0))
        for match in _FORMAL_STANDARD_CODE_RE.finditer(text)
    ]
    if standard_values:
        subjects.extend(item for item in standard_values if item.casefold() not in {value.casefold() for value in subjects})
    acronym_regulation = _ACRONYM_REGULATION_RE.search(text)
    if acronym_regulation:
        subjects.append(f"{_title_phrase(acronym_regulation.group('subject'))} Regulations")
    if _E_INVOICE_RE.search(text):
        subjects.append("Malaysia e-Invoice" if re.search(r"Malaysia\s+e", text, re.I) else "e-Invoice")
    if _LABOUR_LAW_RE.search(text):
        subjects.append("Malaysian Labour Law" if re.search(r"Malaysian", text, re.I) else "Employment Regulations")
    for match in _LAW_TOPIC_RE.finditer(text):
        subject = _title_phrase(match.group(0))
        if subject.casefold() not in {item.casefold() for item in subjects}:
            subjects.append(subject)
    if not subjects and _EXPLICIT_FORMAL_RE.search(text):
        intro = _FORMAL_INTRO_RE.search(text)
        if intro:
            subject = _strip_requirement_suffix(intro.group("subject"))
            if subject and len(subject.split()) <= 8:
                subjects.append(_title_phrase(subject))
    if not subjects:
        return None
    if len(subjects) == 1:
        subject = subjects[0]
    else:
        subject = " and ".join(subjects)
    if re.search(r"ISO", subject, re.I):
        return f"{subject} Quality Standards"
    if re.search(r"e-Invoice", subject, re.I):
        return f"{subject} Compliance"
    if re.search(r"Law|Regulation|Act|Code|Standard|Framework", subject, re.I):
        return subject
    return f"{subject} Knowledge"


def _criterion_text(item: dict[str, Any]) -> str:
    return f"{item.get('name', '')} {item.get('sourceText', '')}".casefold()


def _similar(left: str, right: str) -> float:
    return SequenceMatcher(None, re.sub(r"[^a-z0-9]+", " ", left.casefold()).strip(), re.sub(r"[^a-z0-9]+", " ", right.casefold()).strip()).ratio()


def _formal_identifiers(value: str) -> set[str]:
    """Return named formal identifiers that can safely anchor reconciliation."""

    text = _normalise_text(value)
    identifiers: set[str] = set()
    for pattern in (_ISO_RE, _FORMAL_STANDARD_CODE_RE):
        for match in pattern.finditer(text):
            identifiers.add(re.sub(r"\s+", " ", match.group(0)).casefold())
    if _LABOUR_LAW_RE.search(text):
        identifiers.add(
            "malaysian labour law"
            if re.search(r"malaysian", text, re.IGNORECASE)
            else "employment law"
        )
    if _E_INVOICE_RE.search(text):
        identifiers.add("e-invoice")
    return identifiers


def _evidence_parts(item: dict[str, Any]) -> list[str]:
    return [
        _normalise_text(part)
        for part in str(item.get("sourceText", "")).split("|")
        if _normalise_text(part)
    ]


def _formal_evidence_matches(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    existing_ids = {
        str(value).casefold()
        for value in (
            existing.get("sourceIds", [])
            if isinstance(existing.get("sourceIds", []), list)
            else []
        )
        if value is not None
    }
    candidate_ids = {
        str(value).casefold()
        for value in (
            candidate.get("sourceIds", [])
            if isinstance(candidate.get("sourceIds", []), list)
            else []
        )
        if value is not None
    }
    existing_parts = _evidence_parts(existing)
    candidate_parts = _evidence_parts(candidate)
    if existing_ids & candidate_ids and len(existing_parts) == len(candidate_parts):
        return True

    if len(existing_parts) != len(candidate_parts):
        return False
    if {
        value.casefold() for value in existing_parts
    } == {value.casefold() for value in candidate_parts}:
        return True
    return any(
        _similar(left, right) >= 0.88
        for left in existing_parts
        for right in candidate_parts
    )


def _merge_grounded_metadata(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    """Merge same-evidence metadata without inventing IDs or scores."""

    records: dict[str, dict[str, Any]] = {}
    for item in (existing, candidate):
        parts = _evidence_parts(item)
        source_ids = item.get("sourceIds")
        scores = item.get("groundingScores")
        for index, part in enumerate(parts):
            key = part.casefold()
            record = records.setdefault(key, {"sourceText": part})
            if (
                "sourceId" not in record
                and isinstance(source_ids, list)
                and index < len(source_ids)
            ):
                record["sourceId"] = source_ids[index]
            if (
                "groundingScore" not in record
                and isinstance(scores, list)
                and index < len(scores)
            ):
                record["groundingScore"] = scores[index]

    ordered = list(records.values())
    existing["sourceText"] = " | ".join(
        str(item["sourceText"]) for item in ordered
    )
    if ordered and all("sourceId" in item for item in ordered):
        existing["sourceIds"] = [item["sourceId"] for item in ordered]
    elif "sourceIds" in existing:
        existing.pop("sourceIds", None)
    if ordered and all("groundingScore" in item for item in ordered):
        existing["groundingScores"] = [
            item["groundingScore"] for item in ordered
        ]
    elif "groundingScores" in existing:
        existing.pop("groundingScores", None)


def _find_formal_reconciliation(
    criteria: list[dict[str, Any]],
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    if candidate.get("type") != "domain_knowledge":
        return None
    candidate_identifiers = _formal_identifiers(
        f"{candidate.get('name', '')} {candidate.get('sourceText', '')}"
    )
    if not candidate_identifiers:
        return None
    for existing in criteria:
        if existing.get("type") == candidate.get("type"):
            continue
        existing_identifiers = _formal_identifiers(
            f"{existing.get('name', '')} {existing.get('sourceText', '')}"
        )
        if candidate_identifiers & existing_identifiers and _formal_evidence_matches(
            existing,
            candidate,
        ):
            return existing
    return None


def _find_tool_or_system_reconciliation(
    criteria: list[dict[str, Any]],
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    if candidate.get("type") != "relevant_skill":
        return None
    for existing in criteria:
        if existing.get("type") != "relevant_experience":
            continue
        if _formal_evidence_matches(existing, candidate):
            return existing
    return None


def _is_duplicate(existing: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if existing.get("type") != candidate.get("type"):
        return False
    existing_formal = _formal_identifiers(
        f"{existing.get('name', '')} {existing.get('sourceText', '')}"
    )
    candidate_formal = _formal_identifiers(
        f"{candidate.get('name', '')} {candidate.get('sourceText', '')}"
    )
    if existing_formal and candidate_formal and not (
        existing_formal & candidate_formal
    ):
        return False
    existing_source = _normalise_text(existing.get("sourceText", "")).casefold()
    candidate_source = _normalise_text(candidate.get("sourceText", "")).casefold()
    if existing_source == candidate_source:
        return True
    existing_parts = {
        part.casefold() for part in _evidence_parts(existing) if part
    }
    candidate_parts = {
        part.casefold() for part in _evidence_parts(candidate) if part
    }
    if candidate_parts and candidate_parts <= existing_parts:
        return True
    generic_name_words = {
        "and", "certification", "certificate", "education", "experience",
        "field", "language", "knowledge", "relevance", "relevant",
        "preferred", "proficiency", "qualification",
    }
    existing_name_topics = {
        token
        for token in re.findall(r"[a-z0-9]+", str(existing.get("name", "")).casefold())
        if token not in generic_name_words
    }
    candidate_name_topics = {
        token
        for token in re.findall(r"[a-z0-9]+", str(candidate.get("name", "")).casefold())
        if token not in generic_name_words
    }
    if existing_name_topics and candidate_name_topics and not (
        existing_name_topics & candidate_name_topics
    ):
        return False
    if _similar(existing_source, candidate_source) >= 0.9:
        return True
    return _similar(str(existing.get("name", "")), str(candidate.get("name", ""))) >= 0.84


def _next_criterion_id(criteria: list[dict[str, Any]]) -> str:
    used = {str(item.get("criterionId", "")) for item in criteria}
    index = len(criteria) + 1
    candidate = f"criterion-{index}"
    while candidate in used:
        index += 1
        candidate = f"criterion-{index}"
    return candidate


def _recovery_entry(
    recovery_type: str,
    criterion: dict[str, Any],
    source_section: str,
    source_index: int,
    reason: str,
    importance: str,
) -> dict[str, Any]:
    source_text = _normalise_text(criterion.get("sourceText", ""))
    entry = {
        "recoveryId": f"{recovery_type}-{source_section}-{source_index}",
        "criterionId": criterion.get("criterionId"),
        "recoveryType": recovery_type,
        "criterionType": criterion.get("type"),
        "criterionName": criterion.get("name"),
        "sourceIds": list(criterion.get("sourceIds", [])),
        "sourceCriterionIds": list(criterion.get("sourceCriterionIds", [])),
        "sourceTextHashes": [_hash_text(part.strip()) for part in source_text.split("|") if part.strip()],
        "reason": reason,
        "importance": importance if importance in IMPORTANCE_VALUES else "medium",
    }
    for key in (
        "reconciledFromCriterionId",
        "reconciledFromType",
        "reconciledFromName",
    ):
        if criterion.get(key):
            entry[key] = criterion[key]
    return entry


def recover_explicit_requirements(
    criteria: list[dict[str, Any]],
    requirement_texts: list[str],
    source_section: str = "requirements",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Recover only explicit education, experience, language, certification and formal knowledge."""

    result = [dict(item) for item in criteria]
    recoveries: list[dict[str, Any]] = []
    warnings: list[str] = []

    def add_candidate(
        candidate_type: str,
        name: str,
            source_text: str,
        source_index: int,
        importance: str,
        recovery_type: str,
        reason: str,
    ) -> None:
        candidate = {
            "criterionId": "",
            "type": candidate_type,
            "name": name,
            "sourceText": source_text,
            "sourceIds": [f"{source_section}-{source_index}"],
            "sourceCriterionIds": [
                f"{source_section}-explicit-{candidate_type}-{source_index}"
            ],
            "groundingScores": [1.0],
            "importance": importance,
            "suggestedWeight": 0,
        }
        reconciled = _find_formal_reconciliation(result, candidate)
        if reconciled is None and recovery_type == "explicit_tool_or_system":
            reconciled = _find_tool_or_system_reconciliation(result, candidate)
        if reconciled is not None:
            previous_type = reconciled.get("type")
            previous_name = reconciled.get("name")
            previous_id = reconciled.get("criterionId")
            reconciled["reconciledFromCriterionId"] = previous_id
            reconciled["reconciledFromType"] = previous_type
            reconciled["reconciledFromName"] = previous_name
            reconciled["type"] = candidate_type
            reconciled["name"] = name
            _merge_grounded_metadata(reconciled, candidate)
            source_criterion_ids = list(
                reconciled.get("sourceCriterionIds", [])
                if isinstance(reconciled.get("sourceCriterionIds", []), list)
                else []
            )
            for source_criterion_id in candidate.get("sourceCriterionIds", []):
                if source_criterion_id not in source_criterion_ids:
                    source_criterion_ids.append(source_criterion_id)
            reconciled["sourceCriterionIds"] = source_criterion_ids
            if reconciled.get("importance") not in IMPORTANCE_VALUES:
                reconciled["importance"] = importance
            recovery = _recovery_entry(
                recovery_type,
                reconciled,
                source_section,
                source_index,
                reason
                + "; reconciled an existing criterion with the same named formal "
                "standard and JD evidence.",
                str(reconciled.get("importance", importance)),
            )
            recoveries.append(recovery)
            warnings.append(
                f"Reconciled {previous_type} criterion '{previous_name}' "
                f"to {candidate_type} '{name}' using the same named formal "
                "standard and JD evidence."
            )
            return
        existing = next((item for item in result if _is_duplicate(item, candidate)), None)
        if existing is not None:
            source_criterion_ids = existing.get("sourceCriterionIds", [])
            is_legacy_fallback = any("fallback" in str(value).casefold() for value in source_criterion_ids)
            if is_legacy_fallback and existing.get("name") == "Relevant Education Field" and candidate_type == "education_relevance":
                existing["name"] = name
                existing["importance"] = importance
                recoveries.append(_recovery_entry(recovery_type, existing, source_section, source_index, reason + "; repaired an existing generic fallback name.", importance))
            elif is_legacy_fallback:
                existing["name"] = name
                if existing.get("importance") not in IMPORTANCE_VALUES:
                    existing["importance"] = importance
                recoveries.append(
                    _recovery_entry(
                        recovery_type,
                        existing,
                        source_section,
                        source_index,
                        reason + "; retained an existing explicit fallback criterion.",
                        str(existing.get("importance", importance)),
                    )
                )
            return
        candidate["criterionId"] = _next_criterion_id(result)
        result.append(candidate)
        recoveries.append(
            _recovery_entry(
                recovery_type,
                candidate,
                source_section,
                source_index,
                reason,
                importance,
            )
        )

    for source_index, raw_text in enumerate(requirement_texts, start=1):
        source_text = _normalise_text(raw_text)
        if not source_text:
            continue

        education = _education_name_and_recovery(source_text)
        if education:
            education_name, education_recovery_type, education_reason = education
            add_candidate(
                "education_relevance",
                education_name,
                source_text,
                source_index,
                "medium" if education_recovery_type == "explicit_education_field" else "low",
                education_recovery_type,
                education_reason,
            )

        experience = _experience_name_and_importance(source_text)
        if experience:
            experience_name, importance = experience
            add_candidate(
                "relevant_experience",
                experience_name,
                source_text,
                source_index,
                importance,
                "explicit_experience",
                "The requirement names an experience scope beyond a bare year threshold.",
            )

        tool_or_system = _extract_tool_or_system(source_text)
        if tool_or_system:
            tool_or_system_name, importance = tool_or_system
            add_candidate(
                "relevant_skill",
                tool_or_system_name,
                source_text,
                source_index,
                importance,
                "explicit_tool_or_system",
                "The requirement explicitly names a tool or system used in prior work.",
            )

        language = _extract_languages(source_text)
        if language:
            language_name, importance = language
            add_candidate(
                "job_related_language",
                language_name,
                source_text,
                source_index,
                importance,
                "explicit_language",
                "The requirement names a language and connects it to job communication or service.",
            )

        certification = _extract_certification(source_text)
        if certification:
            certification_name, importance = certification
            add_candidate(
                "preferred_certification",
                certification_name,
                source_text,
                source_index,
                importance,
                "explicit_certification",
                "The requirement names a specific certification or licence.",
            )

        formal_name = _extract_formal_knowledge(source_text)
        if formal_name:
            add_candidate(
                "domain_knowledge",
                formal_name,
                source_text,
                source_index,
                "medium",
                "explicit_law_or_standard",
                "The requirement explicitly names a law, regulation, formal standard or professional control.",
            )

    return result, recoveries, warnings


def collapse_explicit_requirement_duplicates(
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Collapse same-type/same-evidence duplicates around explicit recovery.

    One compound model criterion can temporarily retain unrelated evidence and
    therefore evade duplicate detection before the final evidence pass. Once
    that evidence is narrowed, prefer the canonical deterministic recovery and
    merge only an exact type-and-source duplicate. Criteria that independently
    interpret the same responsibility remain untouched because neither carries
    an explicit-recovery lineage ID.
    """

    keyed: dict[tuple[str, tuple[str, ...]], list[int]] = {}
    for index, criterion in enumerate(criteria):
        parts = tuple(
            sorted(
                part.casefold()
                for part in _evidence_parts(criterion)
                if part
            )
        )
        if not parts:
            continue
        key = (str(criterion.get("type", "")), parts)
        keyed.setdefault(key, []).append(index)

    replacements: dict[int, dict[str, Any]] = {}
    consumed: set[int] = set()
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []
    for indices in keyed.values():
        if len(indices) < 2:
            continue
        members = [criteria[index] for index in indices]
        explicit_members = [
            item
            for item in members
            if any(
                "-explicit-" in str(source_id)
                for source_id in item.get("sourceCriterionIds", [])
            )
        ]
        if not explicit_members:
            continue
        chosen = dict(explicit_members[0])
        for member in members:
            if member is explicit_members[0]:
                continue
            _merge_grounded_metadata(chosen, member)
        chosen["sourceCriterionIds"] = list(
            dict.fromkeys(
                source_id
                for item in members
                for source_id in item.get("sourceCriterionIds", [])
                if str(source_id).strip()
            )
        )
        lineage: list[str] = []
        for item in members:
            prior = item.get("mergedFromIds")
            if isinstance(prior, list) and prior:
                lineage.extend(str(value) for value in prior if str(value).strip())
            elif str(item.get("criterionId", "")).strip():
                lineage.append(str(item["criterionId"]))
        if lineage:
            chosen["mergedFromIds"] = list(dict.fromkeys(lineage))
        first_index = min(indices)
        replacements[first_index] = chosen
        consumed.update(indices)
        warnings.append(
            f"Collapsed {len(members)} exact explicit-requirement duplicates "
            f"for '{chosen.get('name', '')}'."
        )
        audit.append(
            {
                "criterionType": chosen.get("type"),
                "criterionName": chosen.get("name"),
                "memberCriterionIds": [
                    item.get("criterionId") for item in members
                ],
            }
        )

    result: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if index in replacements:
            result.append(replacements[index])
        elif index not in consumed:
            result.append(criterion)
    return result, warnings, audit


_MINIMUM_EXPERIENCE_SENTENCE_RE = re.compile(
    r"\b(?:minimum|at\s+least)\b.{0,30}\byears?\b.{0,60}\bexperience\b|"
    r"\b(?:minimum|at\s+least)\b.{0,30}\byears?\s+of\b.{0,60}\bexperience\b",
    re.IGNORECASE,
)
_DISTINCT_EXPERIENCE_CONTEXT_RE = re.compile(
    r"\b(?:country|environment|industry|market|region|sector)\b",
    re.IGNORECASE,
)


def consolidate_broad_specific_experience(
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Join a broad duration requirement to one adjacent preferred outcome.

    A preferred environment, industry, market or regional background remains
    independently scorable. The narrow merge covers the common case where a
    broad minimum-duration requirement and a more specific work-delivery
    requirement describe one experience record.
    """

    replacements: dict[int, dict[str, Any]] = {}
    consumed: set[int] = set()
    warnings: list[str] = []
    audit: list[dict[str, Any]] = []

    for left_index, left in enumerate(criteria):
        if left_index in consumed or left.get("type") != "relevant_experience":
            continue
        left_parts = _evidence_parts(left)
        left_ids = left.get("sourceIds", [])
        if len(left_parts) != 1 or not isinstance(left_ids, list) or len(left_ids) != 1:
            continue
        for right_index in range(left_index + 1, len(criteria)):
            if right_index in consumed:
                continue
            right = criteria[right_index]
            if right.get("type") != "relevant_experience":
                continue
            right_parts = _evidence_parts(right)
            right_ids = right.get("sourceIds", [])
            if (
                len(right_parts) != 1
                or not isinstance(right_ids, list)
                or len(right_ids) != 1
            ):
                continue
            left_source_id = str(left_ids[0])
            right_source_id = str(right_ids[0])
            left_match = re.fullmatch(r"(requirements|qualifications)-(\d+)", left_source_id)
            right_match = re.fullmatch(r"(requirements|qualifications)-(\d+)", right_source_id)
            if (
                left_match is None
                or right_match is None
                or left_match.group(1) != right_match.group(1)
                or abs(int(left_match.group(2)) - int(right_match.group(2))) != 1
            ):
                continue

            candidates = [(left_index, left, left_parts[0]), (right_index, right, right_parts[0])]
            minimum = next(
                (
                    item
                    for item in candidates
                    if _MINIMUM_EXPERIENCE_SENTENCE_RE.search(item[2])
                ),
                None,
            )
            preferred = next(
                (item for item in candidates if _PREFERRED_RE.search(item[2])),
                None,
            )
            if minimum is None or preferred is None or minimum[0] == preferred[0]:
                continue
            if _DISTINCT_EXPERIENCE_CONTEXT_RE.search(preferred[2]):
                continue

            ordered = sorted(
                (minimum, preferred),
                key=lambda item: int(
                    re.search(r"(\d+)$", str(item[1]["sourceIds"][0])).group(1)  # type: ignore[union-attr]
                ),
            )
            merged = dict(preferred[1])
            merged["sourceText"] = " | ".join(item[2] for item in ordered)
            merged["sourceIds"] = [item[1]["sourceIds"][0] for item in ordered]
            merged["groundingScores"] = [
                (
                    item[1].get("groundingScores", [1.0])[0]
                    if isinstance(item[1].get("groundingScores"), list)
                    and item[1].get("groundingScores")
                    else 1.0
                )
                for item in ordered
            ]
            merged["sourceCriterionIds"] = list(
                dict.fromkeys(
                    source_id
                    for item in ordered
                    for source_id in item[1].get("sourceCriterionIds", [])
                    if str(source_id).strip()
                )
            )
            lineage = [
                str(item[1].get("criterionId", "")).strip()
                for item in ordered
                if str(item[1].get("criterionId", "")).strip()
            ]
            if lineage:
                merged["mergedFromIds"] = lineage
            merged["importance"] = max(
                (str(item[1].get("importance", "medium")) for item in ordered),
                key=lambda value: {"low": 1, "medium": 2, "high": 3}.get(value, 2),
            )

            first_index = min(minimum[0], preferred[0])
            replacements[first_index] = merged
            consumed.update({minimum[0], preferred[0]})
            warnings.append(
                f"Consolidated a broad duration requirement into specific "
                f"experience '{merged.get('name', '')}'."
            )
            audit.append(
                {
                    "criterionName": merged.get("name"),
                    "memberCriterionIds": lineage,
                    "sourceIds": list(merged["sourceIds"]),
                }
            )
            break

    result: list[dict[str, Any]] = []
    for index, criterion in enumerate(criteria):
        if index in replacements:
            result.append(replacements[index])
        elif index not in consumed:
            result.append(criterion)
    return result, warnings, audit


__all__ = [
    "ALLOWED_RECOVERY_TYPES",
    "collapse_explicit_requirement_duplicates",
    "consolidate_broad_specific_experience",
    "recover_explicit_requirements",
]
