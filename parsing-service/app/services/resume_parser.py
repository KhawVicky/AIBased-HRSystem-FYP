"""Deterministic resume parser with optional grounded semantic enrichment."""

from __future__ import annotations

from collections import OrderedDict
from datetime import date
import re
from typing import Any, Mapping

from app.schemas.resume import (
    ApplicationData,
    AchievementEntry,
    CandidateProfile,
    CertificationEntry,
    DataConflict,
    EducationEntry,
    EvidenceRecord,
    EvidenceReference,
    ExperienceEntry,
    LanguageEntry,
    ProjectEntry,
    SemanticResumeOutput,
    SkillEntry,
)
from app.services.candidate_summary import build_candidate_summary, select_highest_education
from app.services.resume_dates import (
    DATE_RANGE_RE,
    DateRange,
    duration_confidence,
    duration_months,
    normalise_date,
    parse_date_range,
    unique_covered_months,
)
from app.services.resume_sections import (
    SECTION_DISPLAY_NAMES,
    detect_section_heading,
    is_generic_soft_skill,
    meaningful_tokens,
    non_empty_lines,
    segment_resume_sections,
    stem_token,
    strip_bullet,
)
from app.services.resume_semantics import ResumeSemanticClient, ResumeSemanticError
from app.services.resume_vocab import (
    DOMAIN_PATTERNS,
    GENERIC_SKILLS,
    LANGUAGE_NAMES,
    detect_domain,
    explicit_skills_in_text,
    normalise_skill_name,
)


PARSER_VERSION = "resume-parsing-v1"
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{6,}\d)(?!\d)")
CGPA_RE = re.compile(r"\b(?:c\s*g\s*p\s*a|gpa)\s*[:=\-]?\s*([0-4](?:\.\d{1,3})?)\b", re.IGNORECASE)
EXPERIENCE_YEARS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b",
    re.IGNORECASE,
)
NOTICE_RE = re.compile(
    r"\bnotice\s+period\s*[:\-]?\s*([^\n,;|]+)",
    re.IGNORECASE,
)
DEGREE_RE = re.compile(
    r"\b(?:ph\.?d|doctor(?:ate)?|master(?:'s)?|m\.?sc|m\.?a|mba|bachelor(?:'s)?|b\.?sc|b\.?a|"
    r"diploma|associate|foundation|matriculation|stpm|spm|certificate)\b",
    re.IGNORECASE,
)
INSTITUTION_RE = re.compile(
    r"\b(?:university|college|institute|school|academy|polytechnic)\b",
    re.IGNORECASE,
)
COMPANY_RE = re.compile(
    r"\b(?:sdn\.?\s*bhd\.?|berhad|ltd\.?|limited|inc\.?|corp\.?|corporation|llc|plc|"
    r"company|co\.?|university|college|hospital|agency|group)\b",
    re.IGNORECASE,
)
METRIC_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\b\d+\+?\s+(?:employees?|users?|clients?|projects?)\b|"
    r"\b(?:increased|reduced|improved|saved|achieved|delivered|cut|grew)\b)",
    re.IGNORECASE,
)
LABEL_RE = re.compile(r"^(?:name|full name|email|phone|mobile|tel|telephone|location|address)\s*[:\-]\s*(.+)$", re.IGNORECASE)
EXPLICIT_PROFICIENCY_RE = re.compile(
    r"(?:[-:]|\()\s*(fluent|native|conversational|intermediate|advanced|basic|beginner|professional|working proficiency)\b",
    re.IGNORECASE,
)


def _clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" \t:|-")
    return cleaned or None


def _collapsed(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _source_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index}"


def _add_evidence(
    evidence: list[EvidenceRecord],
    source_id: str,
    section: str,
    source_text: str,
    *,
    source_type: str = "resume",
) -> EvidenceRecord:
    record = EvidenceRecord(
        sourceId=source_id,
        sourceSection=section,
        sourceText=source_text.strip(),
        sourceType="application_form" if source_type == "application_form" else "resume",
    )
    evidence.append(record)
    return record


def _ref(record: EvidenceRecord) -> EvidenceReference:
    return EvidenceReference(
        sourceId=record.sourceId,
        text=record.sourceText,
        sourceSection=record.sourceSection,
    )


def _extract_labeled(text: str, labels: tuple[str, ...]) -> str | None:
    pattern = re.compile(
        rf"^(?:{'|'.join(re.escape(label) for label in labels)})\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return _clean_value(match.group(1))
    return None


def _extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0).strip() if match else None


def _extract_phone(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        if DATE_RANGE_RE.search(line) and "+" not in line:
            continue
        match = PHONE_RE.search(line)
        if match:
            value = match.group(0).strip()
            digits = re.sub(r"\D", "", value)
            if 7 <= len(digits) <= 15:
                # PDF text layers sometimes preserve only one side of a
                # phone number's parentheses (for example ``+60) 11-...``).
                return value.replace("(", "").replace(")", "")
    return None


def _extract_name(text: str, header: str) -> str | None:
    labelled = _extract_labeled(text, ("name", "full name"))
    if labelled and _plausible_name(labelled):
        return labelled
    for raw_line in header.splitlines():
        line = strip_bullet(raw_line)
        if not line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if LABEL_RE.match(line) or re.search(r"(linkedin|github|portfolio|http://|https://)", line, re.IGNORECASE):
            continue
        if _plausible_name(line):
            return line
    return None


def _plausible_name(value: str) -> bool:
    cleaned = _clean_value(value)
    if not cleaned or len(cleaned) > 80 or re.search(r"[.!?@|]", cleaned):
        return False
    if detect_section_heading(cleaned):
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'’-]*", cleaned)
    if not 2 <= len(tokens) <= 8:
        return False
    rejected = {
        "skills", "scoring", "education", "experience", "contact", "languages",
        "profile", "projects", "certifications", "achievements", "summary",
        "computer science student",
    }
    return cleaned.casefold() not in rejected and all(len(token) >= 1 for token in tokens)


def _extract_location(text: str, sections: Mapping[str, str]) -> str | None:
    labelled = _extract_labeled(text, ("location", "address", "current location", "based in"))
    if labelled:
        return labelled
    location_re = re.compile(
        r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?\s*,\s*[A-Z][A-Za-z]+(?:\s+[A-Za-z]+)?\b"
    )
    for source in (sections.get("contact", ""), sections.get("header", "")):
        for line in source.splitlines():
            match = location_re.search(line)
            if match:
                return _clean_value(match.group(0))
    return None


def _extract_personal_info(text: str, sections: Mapping[str, str]) -> dict[str, str | None]:
    header = sections.get("header", "")
    return {
        "name": _extract_name(text, header),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "location": _extract_location(text, sections),
    }


def _split_paragraphs(text: str) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            if current:
                paragraphs.append(current)
                current = []
            continue
        current.append(cleaned)
    if current:
        paragraphs.append(current)
    return paragraphs


def _qualification_level(value: str) -> str | None:
    lower = value.lower()
    if re.search(r"\b(ph\.?d|doctor(?:ate)?)\b", lower):
        return "PhD"
    if re.search(r"\b(master|m\.?sc|m\.?a|mba)\b", lower):
        return "Master Degree"
    if re.search(r"\b(bachelor|b\.?sc|b\.?a)\b", lower):
        return "Bachelor Degree"
    if "diploma" in lower or "associate" in lower:
        return "Diploma"
    if re.search(r"\b(stpm|foundation|matriculation)\b", lower):
        return "STPM / Foundation / Matriculation"
    if re.search(r"\bspm\b", lower):
        return "SPM"
    if "certificate" in lower:
        return "Certificate"
    return None


def _education_field(qualification: str) -> str | None:
    value = DATE_RANGE_RE.sub("", qualification)
    value = re.sub(r"\b(?:cgpa|gpa)\b.*$", "", value, flags=re.IGNORECASE)
    match = re.search(r"\b(?:in|of)\s+(.+?)(?=\s+(?:from|at|@)\s+|[|,;]|$)", value, re.IGNORECASE)
    if not match:
        return None
    field = _clean_value(match.group(1))
    if not field or len(field) > 80:
        return None
    return field


def _institution_like(value: str) -> bool:
    candidate = strip_bullet(value)
    if not candidate or DATE_RANGE_RE.search(candidate) or CGPA_RE.search(candidate):
        return False
    if DEGREE_RE.search(candidate):
        return False
    return bool(
        INSTITUTION_RE.search(candidate)
        or re.search(r"\b(?:UOWM|KDU|PG\s+UC|SEGI|UC)\b", candidate, re.IGNORECASE)
        or (candidate.isupper() and 2 <= len(candidate.split()) <= 8)
    )


def _institution(lines: list[str], qualification_line: str | None) -> str | None:
    if qualification_line:
        inline_parts = [part.strip() for part in qualification_line.split("|")]
        for part in inline_parts[1:]:
            if part and not DATE_RANGE_RE.search(part) and not CGPA_RE.search(part):
                return _clean_value(part)
    for line in lines:
        candidate = strip_bullet(line)
        if candidate == qualification_line or not _institution_like(candidate):
            continue
        return _clean_value(candidate)
    return None


def _education_groups(text: str) -> list[list[str]]:
    lines = non_empty_lines(text)
    if not lines:
        return []
    markers = [index for index, line in enumerate(lines) if DEGREE_RE.search(line)]
    if not markers:
        return _split_paragraphs(text) or [lines]
    groups: list[list[str]] = []
    for index, marker in enumerate(markers):
        previous_boundary = markers[index - 1] + 1 if index else 0
        next_marker = markers[index + 1] if index + 1 < len(markers) else len(lines)

        # Resume templates place the institution either immediately before
        # the qualification or immediately after it. Prefer a following
        # institution only when no date/CGPA marker appears first; otherwise
        # that institution belongs to the next education record.
        following_institution = next(
            (
                candidate_index
                for candidate_index in range(marker + 1, next_marker)
                if _institution_like(lines[candidate_index])
                and not any(
                    DATE_RANGE_RE.search(lines[between]) or CGPA_RE.search(lines[between])
                    for between in range(marker + 1, candidate_index)
                )
            ),
            None,
        )
        preceding_institution = next(
            (
                candidate_index
                for candidate_index in range(marker - 1, previous_boundary - 1, -1)
                if _institution_like(lines[candidate_index])
            ),
            None,
        )
        institution_index = following_institution or preceding_institution
        start = min(marker, institution_index) if institution_index is not None else marker
        groups.append(lines[start:next_marker])
    return groups


def _qualification_line(group: list[str]) -> str:
    degree_index = next(
        (index for index, line in enumerate(group) if DEGREE_RE.search(line)),
        0,
    )
    parts = [strip_bullet(group[degree_index])]
    if "|" in parts[0]:
        return parts[0]
    for line in group[degree_index + 1 :]:
        candidate = strip_bullet(line)
        if (
            not candidate
            or DATE_RANGE_RE.search(candidate)
            or CGPA_RE.search(candidate)
            or _institution_like(candidate)
            or DEGREE_RE.search(candidate)
        ):
            break
        if len(candidate) <= 80:
            parts.append(candidate)
    return " ".join(parts)


def _parse_education(text: str, evidence: list[EvidenceRecord]) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    for index, group in enumerate(_education_groups(text), start=1):
        source_text = "\n".join(group).strip()
        if not source_text:
            continue
        qualification_line = _qualification_line(group)
        date_range = parse_date_range(source_text)
        cgpa_match = CGPA_RE.search(source_text)
        cgpa = float(cgpa_match.group(1)) if cgpa_match else None
        level = _qualification_level(qualification_line)
        qualification_value = qualification_line.split("|", 1)[0].strip()
        source = _add_evidence(evidence, _source_id("education", index), "Education", source_text)
        end_date = normalise_date(date_range.end) if date_range and not date_range.is_current else None
        graduation_year = int(end_date[:4]) if end_date and end_date[:4].isdigit() else None
        entries.append(
            EducationEntry(
                id=source.sourceId,
                level=level,
                rawQualification=qualification_line,
                qualification=_clean_value(DATE_RANGE_RE.sub("", qualification_value)),
                field=_education_field(qualification_line),
                institution=_institution(group, qualification_line),
                startDate=normalise_date(date_range.start) if date_range else None,
                endDate=end_date,
                graduationYear=graduation_year,
                cgpa=cgpa,
                sourceId=source.sourceId,
                sourceText=source_text,
            )
        )
    return entries


def _company_like(value: str) -> bool:
    return bool(COMPANY_RE.search(value))


def _header_candidates(group: list[str], date_line_index: int | None) -> list[str]:
    candidates: list[str] = []
    for index, line in enumerate(group):
        if index == date_line_index:
            continue
        if date_line_index is not None and abs(index - date_line_index) > 1:
            continue
        if date_line_index is None and index > 1:
            continue
        if not line or line.startswith(("-", "*", "•", "▪")):
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if line.lower().startswith(("responsibilities:", "duties:", "achievements:")):
            continue
        candidates.append(strip_bullet(line))
    return candidates


def _role_header(group: list[str], date_line_index: int | None) -> tuple[str | None, str | None]:
    metadata_lines: list[str] = []
    if date_line_index is not None:
        date_line = group[date_line_index]
        remainder = DATE_RANGE_RE.sub("", date_line).strip(" |,;:-–—")
        if remainder:
            metadata_lines.append(remainder)
    metadata_lines.extend(_header_candidates(group, date_line_index))

    for line in metadata_lines:
        parts = [part.strip() for part in re.split(r"\s*(?:\||•|·)\s*", line) if part.strip()]
        if len(parts) >= 2:
            first, second = parts[0], parts[1]
            if _company_like(first) and not _company_like(second):
                return second, first
            return first, second

    candidates = [line for line in metadata_lines if line]
    if len(candidates) >= 2:
        first, second = candidates[0], candidates[1]
        if _company_like(first) and not _company_like(second):
            return second, first
        if _company_like(second):
            return first, second
        return first, second
    if candidates:
        return (None, candidates[0]) if _company_like(candidates[0]) else (candidates[0], None)
    return None, None


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*+•▪◦‣]|\(?\d+[.)]|[a-zA-Z][.)])\s+", line))


def _experience_groups(text: str) -> list[tuple[list[str], int | None]]:
    lines = non_empty_lines(text)
    if not lines:
        return []
    date_indices = [
        index
        for index, line in enumerate(lines)
        if DATE_RANGE_RE.search(line) and not _is_bullet(line)
    ]
    if not date_indices:
        return [(lines, None)]

    groups: list[tuple[list[str], int | None]] = []
    for index, date_index in enumerate(date_indices):
        start = 0 if index == 0 else date_indices[index - 1] + 1
        end = date_indices[index + 1] if index + 1 < len(date_indices) else len(lines)
        group = lines[start:end]
        local_date_index = date_index - start
        groups.append((group, local_date_index))
    return groups


def _is_metadata_line(line: str) -> bool:
    lower = line.lower().strip()
    return lower.startswith(
        (
            "responsibilities:",
            "responsibility:",
            "duties:",
            "achievements:",
            "technologies:",
            "tools:",
        )
    )


def _parse_experience(
    text: str,
    evidence: list[EvidenceRecord],
    *,
    as_of: date | None = None,
) -> tuple[list[ExperienceEntry], list[DateRange]]:
    entries: list[ExperienceEntry] = []
    ranges: list[DateRange] = []
    for index, (group, date_line_index) in enumerate(_experience_groups(text), start=1):
        source_text = "\n".join(group).strip()
        if not source_text:
            continue
        date_range = parse_date_range(source_text)
        if date_range:
            ranges.append(date_range)
        job_title, company = _role_header(group, date_line_index)
        header_lines = set(_header_candidates(group, date_line_index))
        responsibilities: list[str] = []
        achievements: list[str] = []
        date_line = group[date_line_index] if date_line_index is not None else None
        for line in group:
            if line == date_line or line in header_lines or _is_metadata_line(line):
                continue
            value = strip_bullet(line)
            if not value or DATE_RANGE_RE.search(value):
                continue
            if _is_bullet(line) or date_line_index is not None:
                if METRIC_RE.search(value):
                    achievements.append(value)
                responsibilities.append(value)

        source = _add_evidence(
            evidence,
            _source_id("experience", index),
            "Work Experience",
            source_text,
        )
        role_skills = explicit_skills_in_text(source_text)
        skill_refs = (
            [
                EvidenceReference(
                    sourceId=source.sourceId,
                    text=source_text,
                    sourceSection=source.sourceSection,
                )
            ]
            if role_skills
            else []
        )
        entries.append(
            ExperienceEntry(
                id=source.sourceId,
                jobTitle=job_title,
                company=company,
                startDate=normalise_date(date_range.start) if date_range else None,
                endDate=normalise_date(date_range.end) if date_range and not date_range.is_current else None,
                isCurrent=bool(date_range and date_range.is_current),
                durationMonths=duration_months(date_range, as_of),
                durationConfidence=duration_confidence(date_range),
                responsibilities=list(dict.fromkeys(responsibilities)),
                achievements=list(dict.fromkeys(achievements)),
                skillsEvidence=skill_refs,
                workDomain=detect_domain(source_text),
                sourceId=source.sourceId,
                sourceText=source_text,
            )
        )
    return entries, ranges


def _add_skill(
    skill_map: OrderedDict[str, SkillEntry],
    value: str,
    source: EvidenceRecord,
) -> None:
    name = normalise_skill_name(value)
    if not name or is_generic_soft_skill(name) or name.lower() in GENERIC_SKILLS:
        return
    key = name.casefold()
    reference = _ref(source)
    existing = skill_map.get(key)
    if existing:
        if not any(item.sourceId == reference.sourceId and item.text == reference.text for item in existing.evidence):
            existing.evidence.append(reference)
        return
    skill_map[key] = SkillEntry(
        id=f"skill-{len(skill_map) + 1}",
        name=value.strip(),
        normalizedName=name,
        evidence=[reference],
    )


def _skill_tokens_from_section_line(line: str) -> list[str]:
    value = strip_bullet(line)
    value = re.sub(r"^(?:technical|core|key)?\s*skills?\s*[:\-]\s*", "", value, flags=re.IGNORECASE)
    if ":" in value:
        label, body = value.split(":", 1)
        if (
            len(label.strip()) <= 40
            and re.search(
                r"\b(?:ai|nlp|machine\s+learning|programming|language|framework|web\s+development|database|tools?|skills?)\b",
                label,
                re.IGNORECASE,
            )
        ):
            value = body.strip()
    pieces = [piece.strip() for piece in re.split(r"[,;|/]", value) if piece.strip()]
    return [
        piece
        for piece in pieces
        if len(piece) <= 60
        and not piece.endswith(":")
        and not is_generic_soft_skill(piece)
    ]


def _parse_skills(
    text: str,
    evidence: list[EvidenceRecord],
    skill_map: OrderedDict[str, SkillEntry],
) -> None:
    for index, line in enumerate(non_empty_lines(text), start=1):
        source = _add_evidence(evidence, _source_id("skills", index), "Skills", line)
        explicit = explicit_skills_in_text(line)
        tokens = explicit or _skill_tokens_from_section_line(line)
        for token in tokens:
            _add_skill(skill_map, token, source)


def _project_groups(text: str) -> list[list[str]]:
    lines = non_empty_lines(text)
    if not lines:
        return []
    metadata_indices = [
        index
        for index, line in enumerate(lines)
        if "|" in line
        and re.search(r"\bproject\b", line, re.IGNORECASE)
    ]
    if metadata_indices:
        starts: list[int] = []
        for metadata_index in metadata_indices:
            title_index = metadata_index - 1
            while title_index >= 0 and DATE_RANGE_RE.search(lines[title_index]):
                title_index -= 1
            if (
                title_index < 0
                or _is_bullet(lines[title_index])
                or "|" in lines[title_index]
            ):
                title_index = metadata_index
            start = title_index
            if start > 0 and DATE_RANGE_RE.search(lines[start - 1]):
                start -= 1
            if start not in starts:
                starts.append(start)

        groups: list[list[str]] = []
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(lines)
            group = lines[start:end]
            if group:
                groups.append(group)
        return groups

    date_indices = [
        index for index, line in enumerate(lines) if DATE_RANGE_RE.search(line)
    ]
    if not date_indices:
        return _split_paragraphs(text) or [lines]

    groups: list[list[str]] = []
    for index, date_index in enumerate(date_indices):
        start = date_index
        if start > 0 and not DATE_RANGE_RE.search(lines[start - 1]):
            previous = lines[start - 1]
            if not previous.lstrip().startswith(("-", "*", "+")):
                start -= 1
        end = date_indices[index + 1] if index + 1 < len(date_indices) else len(lines)
        group = lines[start:end]
        if group:
            groups.append(group)
    return groups


def _project_title_and_description(group: list[str]) -> tuple[str, list[str]]:
    if "|" in group[0] and re.search(r"\bproject\b", group[0], re.IGNORECASE):
        title_index = 0
    else:
        title_index = next(
            (
                index
                for index, line in enumerate(group)
                if not DATE_RANGE_RE.search(line)
                and not _is_bullet(line)
                and "|" not in line
            ),
            0,
        )
    first = strip_bullet(group[title_index])
    metadata_parts = [
        part.strip()
        for line in group
        if "|" in line and not DATE_RANGE_RE.search(line)
        for part in line.split("|")
        if part.strip()
    ]
    title = first
    if "|" in group[title_index]:
        title = group[title_index].split("|", 1)[0].strip()
    if ":" in title:
        label, candidate = title.split(":", 1)
        if label.lower().strip() in {"project", "project title", "name"}:
            title = candidate.strip()

    description_lines: list[str] = []
    for index, line in enumerate(group):
        if index == title_index:
            continue
        value = strip_bullet(line)
        if not value or DATE_RANGE_RE.search(value):
            continue
        if "|" in value or value in metadata_parts:
            continue
        description_lines.append(value)
    return title, description_lines


def _parse_projects(
    text: str,
    evidence: list[EvidenceRecord],
    skill_map: OrderedDict[str, SkillEntry],
) -> list[ProjectEntry]:
    entries: list[ProjectEntry] = []
    for index, group in enumerate(_project_groups(text), start=1):
        if not group:
            continue
        source_text = "\n".join(group).strip()
        source = _add_evidence(evidence, _source_id("project", index), "Projects", source_text)
        title, description_lines = _project_title_and_description(group)
        technologies = explicit_skills_in_text(source_text)
        for technology in technologies:
            _add_skill(skill_map, technology, source)
        entries.append(
            ProjectEntry(
                id=source.sourceId,
                title=_clean_value(title),
                description=" ".join(description_lines) or None,
                technologies=technologies,
                responsibilities=description_lines,
                sourceId=source.sourceId,
                sourceText=source_text,
            )
        )
    return entries


def _parse_certifications(text: str, evidence: list[EvidenceRecord]) -> list[CertificationEntry]:
    entries: list[CertificationEntry] = []
    groups = _split_paragraphs(text)
    if not groups:
        groups = [[line] for line in non_empty_lines(text)]
    for index, group in enumerate(groups, start=1):
        source_text = "\n".join(group).strip()
        if not source_text:
            continue
        source = _add_evidence(
            evidence,
            _source_id("certification", index),
            "Certifications",
            source_text,
        )
        first = strip_bullet(group[0])
        issuer_match = re.search(r"\b(?:issued by|from|by)\s+(.+?)(?=\s*[|,;]|$)", source_text, re.IGNORECASE)
        issuer = _clean_value(issuer_match.group(1)) if issuer_match else None
        name = re.split(r"\s*[|;]\s*|\s+-\s+", first, maxsplit=1)[0].strip()
        credential_match = re.search(r"\b(?:credential|certificate|certification)\s*(?:id|no\.?|number)?\s*[:#-]\s*([A-Za-z0-9-]+)", source_text, re.IGNORECASE)
        date_matches = list(re.finditer(r"\b(?:19|20)\d{2}(?:-\d{2})?\b", source_text))
        issue_date = date_matches[0].group(0) if date_matches else None
        expiry_date = date_matches[1].group(0) if len(date_matches) > 1 else None
        entries.append(
            CertificationEntry(
                id=source.sourceId,
                name=name,
                issuer=issuer,
                issueDate=issue_date,
                expiryDate=expiry_date,
                credentialId=credential_match.group(1) if credential_match else None,
                sourceId=source.sourceId,
                sourceText=source_text,
            )
        )
    return entries


def _language_from_text(value: str) -> tuple[str, str | None] | None:
    for language in sorted(LANGUAGE_NAMES, key=len, reverse=True):
        match = re.search(rf"(?<![A-Za-z]){re.escape(language)}(?![A-Za-z])", value, re.IGNORECASE)
        if not match:
            continue
        remainder = value[match.end() :].strip()
        proficiency_match = EXPLICIT_PROFICIENCY_RE.search(remainder)
        proficiency = _clean_value(proficiency_match.group(1)) if proficiency_match else None
        return language, proficiency
    return None


def _parse_languages(
    text: str,
    evidence: list[EvidenceRecord],
) -> list[LanguageEntry]:
    entries: list[LanguageEntry] = []
    for index, line in enumerate(non_empty_lines(text), start=1):
        source = _add_evidence(evidence, _source_id("language", index), "Languages", line)
        parts = [part.strip() for part in re.split(r"[,;/|]", strip_bullet(line)) if part.strip()]
        parts = parts or [strip_bullet(line)]
        for part in parts:
            parsed = _language_from_text(part)
            if not parsed:
                continue
            language, proficiency = parsed
            entry_id = f"{source.sourceId}-{len(entries) + 1}"
            entries.append(
                LanguageEntry(
                    id=entry_id,
                    language=language,
                    proficiency=proficiency,
                    sourceId=source.sourceId,
                    sourceText=source.sourceText,
                )
            )
    return entries


def _parse_achievements(text: str, evidence: list[EvidenceRecord]) -> list[AchievementEntry]:
    entries: list[AchievementEntry] = []
    for index, line in enumerate(non_empty_lines(text), start=1):
        value = strip_bullet(line)
        if not value:
            continue
        source = _add_evidence(evidence, _source_id("achievement", index), "Achievements", value)
        entries.append(
            AchievementEntry(
                id=source.sourceId,
                text=value,
                sourceId=source.sourceId,
                sourceText=source.sourceText,
            )
        )
    return entries


def _merge_language(
    language_map: OrderedDict[str, LanguageEntry],
    entry: LanguageEntry,
) -> None:
    key = entry.language.casefold()
    existing = language_map.get(key)
    if not existing:
        language_map[key] = entry
        return
    if not existing.proficiency and entry.proficiency:
        existing.proficiency = entry.proficiency


def _normalise_application_data(value: Mapping[str, Any] | None) -> ApplicationData | None:
    if not value:
        return None
    try:
        return ApplicationData.model_validate(value)
    except Exception:
        return None


def _merge_application_data(
    profile: CandidateProfile,
    application: ApplicationData | None,
    evidence: list[EvidenceRecord],
) -> None:
    if not application:
        return
    profile.applicationData = application

    personal_fields = ("name", "email", "phone", "location")
    for field in personal_fields:
        application_value = getattr(application, field)
        if not application_value:
            continue
        resume_value = getattr(profile.personalInfo, field)
        if resume_value and resume_value.casefold() != application_value.casefold():
            profile.dataConflicts.append(
                DataConflict(
                    field=field,
                    resumeValue=resume_value,
                    applicationValue=application_value,
                    resolution="Application form value retained as the authoritative structured value; resume value remains in evidence.",
                )
            )
        setattr(profile.personalInfo, field, application_value)

    resume_cgpa = profile.cgpa
    if application.cgpa is not None:
        if resume_cgpa is not None and abs(resume_cgpa - application.cgpa) > 0.001:
            profile.dataConflicts.append(
                DataConflict(
                    field="cgpa",
                    resumeValue=resume_cgpa,
                    applicationValue=application.cgpa,
                    resolution="Application form value retained as the trusted eligibility value; resume value remains in evidence.",
                )
            )
        profile.cgpa = application.cgpa
    if application.noticePeriod:
        if profile.noticePeriod and profile.noticePeriod.casefold() != application.noticePeriod.casefold():
            profile.dataConflicts.append(
                DataConflict(
                    field="noticePeriod",
                    resumeValue=profile.noticePeriod,
                    applicationValue=application.noticePeriod,
                    resolution="Application form value retained as the authoritative structured value; resume value remains in evidence.",
                )
            )
        profile.noticePeriod = application.noticePeriod

    if application.yearsExperience is not None:
        if (
            profile.totalExperienceYears is not None
            and abs(profile.totalExperienceYears - application.yearsExperience) > 0.05
        ):
            profile.dataConflicts.append(
                DataConflict(
                    field="yearsExperience",
                    resumeValue=profile.totalExperienceYears,
                    applicationValue=application.yearsExperience,
                    resolution="Application form value retained as the authoritative structured value; resume-derived duration remains in evidence.",
                )
            )
        profile.totalExperienceYears = application.yearsExperience
        profile.totalExperienceMonths = round(application.yearsExperience * 12)

    if application.languages:
        application_entries: list[LanguageEntry] = []
        for index, item in enumerate(application.languages, start=1):
            language = _clean_value(str(item.get("language", "")))
            if not language:
                continue
            proficiency = _clean_value(str(item.get("level", item.get("proficiency", ""))))
            source = _add_evidence(
                evidence,
                _source_id("application-language", index),
                "Application Form",
                " | ".join(value for value in [language, proficiency] if value),
                source_type="application_form",
            )
            application_entries.append(
                LanguageEntry(
                    id=source.sourceId,
                    language=language,
                    proficiency=proficiency,
                    sourceId=source.sourceId,
                    sourceText=source.sourceText,
                    sourceSection="Application Form",
                )
            )
        if application_entries:
            resume_languages = [entry.language for entry in profile.languages]
            application_languages = [entry.language for entry in application_entries]
            if {item.casefold() for item in resume_languages} != {
                item.casefold() for item in application_languages
            }:
                profile.dataConflicts.append(
                    DataConflict(
                        field="languages",
                        resumeValue=resume_languages,
                        applicationValue=application_languages,
                        resolution="Application form languages retained as the authoritative structured value; resume language evidence remains indexed.",
                    )
                )
            profile.languages = application_entries


def _supported_semantic_label(label: str, source_text: str) -> bool:
    if not label or is_generic_soft_skill(label):
        return False
    label_tokens = {stem_token(token) for token in meaningful_tokens(label)}
    source_tokens = {stem_token(token) for token in meaningful_tokens(source_text)}
    if not label_tokens or not source_tokens:
        return False
    return bool(label_tokens & source_tokens)


def _source_text_matches(candidate: str | None, source_text: str) -> bool:
    if not candidate:
        return True
    candidate_value = _collapsed(candidate)
    source_value = _collapsed(source_text)
    return candidate_value in source_value or source_value in candidate_value


def _semantic_items(
    output: SemanticResumeOutput,
) -> list[tuple[str, str, str | None, str]]:
    items: list[tuple[str, str, str | None, str]] = []
    for item in output.experienceEvidence:
        for label in item.semanticCapabilities:
            items.append((item.sourceId, label, item.sourceText, "experience"))
    for item in output.educationSemantics:
        for label in item.semanticCapabilities:
            items.append((item.sourceId, label, item.sourceText, "education"))
    for item in output.projectEvidence:
        for label in item.semanticCapabilities:
            items.append((item.sourceId, label, item.sourceText, "project"))
    for item in output.skillEvidence:
        for label in item.skills:
            items.append((item.sourceId, label, item.sourceText, "skill"))
    return items


def _apply_semantic_output(
    profile: CandidateProfile,
    output: SemanticResumeOutput,
) -> int:
    evidence_by_id = {record.sourceId: record for record in profile.evidenceIndex}
    rejection_count = 0
    experience_by_id = {entry.sourceId: entry for entry in profile.experience}
    project_by_id = {entry.sourceId: entry for entry in profile.projects}
    skill_map = OrderedDict((entry.normalizedName.casefold(), entry) for entry in profile.skills)

    for source_id, label, source_text, kind in _semantic_items(output):
        record = evidence_by_id.get(source_id)
        if (
            record is None
            or record.sourceType != "resume"
            or not _source_text_matches(source_text, record.sourceText)
            or not _supported_semantic_label(label, record.sourceText)
        ):
            rejection_count += 1
            continue
        normalized_label = re.sub(r"\s+", " ", label).strip(" .")
        if normalized_label not in record.normalizedConcepts:
            record.normalizedConcepts.append(normalized_label)
        if kind in {"experience", "project"}:
            if normalized_label.casefold() not in {item.casefold() for item in profile.keyStrengths}:
                profile.keyStrengths.append(normalized_label)
        if kind == "skill":
            _add_skill(skill_map, normalized_label, record)

    if output.primaryDomain and output.primaryDomainSourceIds:
        domain_sources = [
            evidence_by_id.get(source_id)
            for source_id in output.primaryDomainSourceIds
        ]
        domain_sources = [source for source in domain_sources if source is not None]
        if domain_sources and any(
            _supported_semantic_label(output.primaryDomain, source.sourceText)
            for source in domain_sources
        ):
            profile.primaryDomain = re.sub(r"\s+", " ", output.primaryDomain).strip(" .")
        else:
            rejection_count += 1

    # Keep semantic additions compatible with the same deterministic skill schema.
    profile.skills = list(skill_map.values())
    for experience in experience_by_id.values():
        experience.skillsEvidence = list(
            OrderedDict(
                (reference.sourceId, reference) for reference in experience.skillsEvidence
            ).values()
        )
    for project in project_by_id.values():
        project.technologies = list(dict.fromkeys(project.technologies))
    return rejection_count


def _dedupe_profile(profile: CandidateProfile) -> None:
    skill_map: OrderedDict[str, SkillEntry] = OrderedDict()
    for skill in profile.skills:
        key = skill.normalizedName.casefold()
        existing = skill_map.get(key)
        if existing is None:
            skill.id = f"skill-{len(skill_map) + 1}"
            skill_map[key] = skill
            continue
        known_refs = {(item.sourceId, item.text) for item in existing.evidence}
        existing.evidence.extend(
            item for item in skill.evidence if (item.sourceId, item.text) not in known_refs
        )
    profile.skills = list(skill_map.values())

    language_map: OrderedDict[str, LanguageEntry] = OrderedDict()
    for language in profile.languages:
        _merge_language(language_map, language)
    profile.languages = list(language_map.values())
    profile.keyStrengths = list(
        OrderedDict(
            (re.sub(r"\s+", " ", value).strip().casefold(), re.sub(r"\s+", " ", value).strip())
            for value in profile.keyStrengths
            if value.strip() and not is_generic_soft_skill(value)
        ).values()
    )[:6]


def _highest_education_level(profile: CandidateProfile) -> str | None:
    highest = select_highest_education(profile.education)
    return highest.level if highest else None


def _validate_profile_evidence(profile: CandidateProfile) -> None:
    seen_ids: set[str] = set()
    clean_evidence: list[EvidenceRecord] = []
    for record in profile.evidenceIndex:
        source_id = record.sourceId.strip()
        source_text = re.sub(r"[\x00-\x1f\x7f]", " ", record.sourceText).strip()
        if not source_id or not source_text or source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        record.sourceId = source_id
        record.sourceText = source_text
        record.sourceSection = re.sub(r"\s+", " ", record.sourceSection).strip()
        clean_evidence.append(record)
    profile.evidenceIndex = clean_evidence
    valid_ids = {record.sourceId for record in profile.evidenceIndex}
    for skill in profile.skills:
        skill.evidence = [reference for reference in skill.evidence if reference.sourceId in valid_ids]
    for experience in profile.experience:
        experience.skillsEvidence = [
            reference for reference in experience.skillsEvidence if reference.sourceId in valid_ids
        ]
    profile.education = [entry for entry in profile.education if entry.sourceId in valid_ids]
    profile.experience = [entry for entry in profile.experience if entry.sourceId in valid_ids]
    profile.projects = [entry for entry in profile.projects if entry.sourceId in valid_ids]
    profile.certifications = [entry for entry in profile.certifications if entry.sourceId in valid_ids]
    profile.languages = [entry for entry in profile.languages if entry.sourceId in valid_ids]
    profile.achievements = [entry for entry in profile.achievements if entry.sourceId in valid_ids]


def _profile_quality_gate(
    text: str,
    sections: Mapping[str, str],
    profile: CandidateProfile,
    extraction_diagnostics: Mapping[str, Any] | None,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    critical: list[str] = []
    meaningful_length = len(re.sub(r"\s", "", text))
    non_header_sections = [key for key in sections if key != "header"]

    if profile.personalInfo.name and detect_section_heading(profile.personalInfo.name):
        critical.append("candidate name matches a section heading")
    if meaningful_length > 300 and not non_header_sections:
        critical.append("substantial resume text has no recognized sections")
    if meaningful_length > 300 and not profile.evidenceIndex:
        critical.append("substantial resume text produced no evidence")
    if "@" in text and not profile.personalInfo.email:
        warnings.append("an email-like value was present but no valid email was extracted")
    if profile.personalInfo.name is None:
        warnings.append("candidate name could not be extracted confidently")
    if "education" in sections and not profile.education:
        warnings.append("education section detected but no education record was extracted")
    if "languages" in sections and not profile.languages:
        warnings.append("languages section detected but no spoken language was extracted")
    if "projects" in sections and not profile.projects:
        warnings.append("projects section detected but no project record was extracted")
    if "experience" in sections and not profile.experience:
        warnings.append("experience section detected but no work record was extracted")

    forbidden_in_experience = {"projects", "contact", "education", "languages"}
    for record in profile.evidenceIndex:
        headings = {
            heading[0]
            for line in record.sourceText.splitlines()
            if (heading := detect_section_heading(line)) is not None
        }
        if len(headings) > 1:
            warnings.append(f"evidence {record.sourceId} contains multiple section headings")
        if record.sourceSection == "Work Experience" and headings & forbidden_in_experience:
            warnings.append(f"evidence {record.sourceId} crosses a non-work section boundary")

    if extraction_diagnostics:
        score = extraction_diagnostics.get("extractionQualityScore")
        if isinstance(score, (int, float)):
            if score < 50:
                critical.append("PDF extraction quality remained critically low after fallback")
            elif score < 78:
                warnings.append("PDF extraction quality is below the review threshold")
        warnings.extend(
            str(value)
            for value in extraction_diagnostics.get("extractionQualitySignals", [])
            if value in {"character_spacing_corruption", "control_characters", "section_headings_not_recognized"}
        )

    if critical:
        return "failed", list(dict.fromkeys(critical + warnings))
    if warnings:
        return "review_required", list(dict.fromkeys(warnings))
    return "healthy", []


def parse_resume_text(
    text: str,
    *,
    candidate_id: int | str | None = None,
    application_data: Mapping[str, Any] | None = None,
    semantic_client: ResumeSemanticClient | None = None,
    require_semantic: bool = False,
    as_of: date | None = None,
    extraction_diagnostics: Mapping[str, Any] | None = None,
) -> tuple[CandidateProfile, OrderedDict[str, str], dict[str, Any]]:
    """Parse cleaned resume text and return profile, sections, and stage diagnostics."""

    if not text or len(re.sub(r"\s", "", text)) < 20:
        raise ValueError("Resume text is empty or too short to parse")

    sections = segment_resume_sections(text)
    evidence: list[EvidenceRecord] = []
    personal = _extract_personal_info(text, sections)
    profile_summary = sections.get("profile")
    education = _parse_education(sections.get("education", ""), evidence)
    experience, date_ranges = _parse_experience(
        sections.get("experience", ""),
        evidence,
        as_of=as_of,
    )
    skill_map: OrderedDict[str, SkillEntry] = OrderedDict()
    if sections.get("skills"):
        _parse_skills(sections["skills"], evidence, skill_map)
    for experience_entry in experience:
        role_source = next(
            record for record in evidence if record.sourceId == experience_entry.sourceId
        )
        for skill in explicit_skills_in_text(experience_entry.sourceText):
            _add_skill(skill_map, skill, role_source)
    projects = _parse_projects(sections.get("projects", ""), evidence, skill_map)
    certifications = _parse_certifications(sections.get("certifications", ""), evidence)
    languages = _parse_languages(sections.get("languages", ""), evidence)
    achievements = _parse_achievements(sections.get("achievements", ""), evidence)

    # Explicit CGPA/notice values are deterministic resume facts. Application data
    # may later be retained as the trusted source for eligibility without erasing them.
    cgpa_values = [entry.cgpa for entry in education if entry.cgpa is not None]
    cgpa_match = CGPA_RE.search(text)
    resume_cgpa = cgpa_values[0] if cgpa_values else (float(cgpa_match.group(1)) if cgpa_match else None)
    explicit_years_match = EXPERIENCE_YEARS_RE.search(text)
    explicit_years = float(explicit_years_match.group(1)) if explicit_years_match else None
    notice_match = NOTICE_RE.search(text)
    notice_period = _clean_value(notice_match.group(1)) if notice_match else None
    covered_months = unique_covered_months(date_ranges, as_of)
    total_years = round(covered_months / 12, 1) if covered_months else explicit_years

    profile = CandidateProfile(
        candidateId=candidate_id,
        personalInfo=personal,
        profileSummary=profile_summary,
        education=education,
        experience=experience,
        skills=list(skill_map.values()),
        certifications=certifications,
        languages=languages,
        projects=projects,
        achievements=achievements,
        cgpa=resume_cgpa,
        noticePeriod=notice_period,
        totalExperienceYears=total_years,
        totalExperienceMonths=covered_months or (round(explicit_years * 12) if explicit_years else None),
        evidenceIndex=evidence,
    )
    profile.primaryDomain = (
        experience[0].workDomain
        if experience and experience[0].workDomain
        else detect_domain(profile_summary or text)
    )
    profile.keyStrengths = list(
        dict.fromkeys(
            entry.workDomain
            for entry in experience
            if entry.workDomain and entry.workDomain != profile.primaryDomain
        )
    )
    application = _normalise_application_data(application_data)
    # CandidateProfile owns a validated copy of the initial evidence list. Add
    # application-form evidence to that canonical index so later validation
    # does not discard otherwise valid merged fields.
    _merge_application_data(profile, application, profile.evidenceIndex)

    quality_status, quality_warnings = _profile_quality_gate(
        text,
        sections,
        profile,
        extraction_diagnostics,
    )
    if quality_status == "failed":
        raise ValueError(
            "Resume parsing quality gate failed: " + "; ".join(quality_warnings)
        )

    stages = [
        "pdf_text_extraction",
        "text_cleanup",
        "section_detection",
        "deterministic_field_extraction",
        "normalization",
    ]
    warnings: list[str] = list(quality_warnings)
    grounding_rejections = 0
    if semantic_client is None:
        qwen_status = "skipped_no_endpoint" if not require_semantic else "failed"
        if require_semantic:
            raise ResumeSemanticError("Semantic resume parsing was required but no Qwen client is configured")
    else:
        try:
            semantic_output = semantic_client.understand(
                resume_text=text,
                sections=sections,
                evidence_index=profile.evidenceIndex,
            )
            grounding_rejections = _apply_semantic_output(profile, semantic_output)
            qwen_status = "completed"
            stages.extend(["qwen_semantic_understanding", "evidence_grounding_validation"])
            if grounding_rejections:
                warnings.append(f"{grounding_rejections} semantic item(s) were rejected during grounding")
        except ResumeSemanticError:
            qwen_status = "failed"
            warnings.append("Qwen semantic understanding failed; deterministic resume facts were retained")
            if require_semantic:
                raise

    _dedupe_profile(profile)
    profile.highestEducationLevel = _highest_education_level(profile)
    _validate_profile_evidence(profile)
    profile.candidateSummary = build_candidate_summary(profile)
    stages.extend(["evidence_validation", "fixed_candidate_summary"])
    diagnostics = {
        "parserVersion": PARSER_VERSION,
        "detectedSectionCount": len([key for key in sections if key != "header"]),
        "evidenceCount": len(profile.evidenceIndex),
        "educationCount": len(profile.education),
        "experienceCount": len(profile.experience),
        "normalizedSkillCount": len(profile.skills),
        "summaryGenerated": bool(profile.candidateSummary),
        "qwenStatus": qwen_status,
        "groundingRejectionCount": grounding_rejections,
        "qualityStatus": quality_status,
        "qualityWarnings": quality_warnings,
        "stages": stages,
        "warnings": warnings,
    }
    if extraction_diagnostics:
        diagnostics.update(dict(extraction_diagnostics))
    return profile, sections, diagnostics


# Keep role-header parsing tolerant of PDF layouts that place the date before
# the role and use an em dash between the title and employer.  This late
# definition intentionally overrides the legacy helper above, whose source
# contains historical mojibake bullet literals.
def _role_header(group: list[str], date_line_index: int | None) -> tuple[str | None, str | None]:
    metadata_lines: list[str] = []
    if date_line_index is not None:
        date_line = group[date_line_index]
        remainder = DATE_RANGE_RE.sub("", date_line).strip(" |,;:-")
        if remainder:
            metadata_lines.append(remainder)
    metadata_lines.extend(_header_candidates(group, date_line_index))

    for line in metadata_lines:
        parts = [
            part.strip()
            for part in re.split(r"\s*(?:\||\u2022|\u00b7|\u2014|\u2013)\s*", line)
            if part.strip()
        ]
        if len(parts) >= 2:
            first, second = parts[0], parts[1]
            if _company_like(first) and not _company_like(second):
                return second, first
            return first, second

    candidates = [line for line in metadata_lines if line]
    if len(candidates) >= 2:
        first, second = candidates[0], candidates[1]
        if _company_like(first) and not _company_like(second):
            return second, first
        if _company_like(second):
            return first, second
        return first, second
    if candidates:
        return (None, candidates[0]) if _company_like(candidates[0]) else (candidates[0], None)
    return None, None
