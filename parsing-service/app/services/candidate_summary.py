"""Fixed, neutral Candidate Summary generation from validated profile fields."""

from __future__ import annotations

import re

from app.schemas.resume import CandidateProfile, EducationEntry, SkillEntry
from app.services.resume_sections import is_generic_soft_skill


EDUCATION_RANK = {
    "SPM": 1,
    "STPM / Foundation / Matriculation": 2,
    "Diploma": 3,
    "Bachelor Degree": 4,
    "Master Degree": 5,
    "PhD": 6,
}


def select_highest_education(entries: list[EducationEntry]) -> EducationEntry | None:
    if not entries:
        return None
    return max(
        entries,
        key=lambda entry: (
            EDUCATION_RANK.get(entry.level or "", 0),
            entry.graduationYear or 0,
        ),
    )


def select_top_skills(profile: CandidateProfile, limit: int = 5) -> list[SkillEntry]:
    def score(skill: SkillEntry) -> tuple[int, int, int]:
        practical = sum(
            1
            for reference in skill.evidence
            if reference.sourceSection in {"Work Experience", "Projects"}
        )
        recency = sum(
            1 for reference in skill.evidence if reference.sourceSection == "Work Experience"
        )
        return (practical, len(skill.evidence), recency)

    return sorted(profile.skills, key=score, reverse=True)[:limit]


def _display_name(profile: CandidateProfile) -> str:
    return (profile.personalInfo.name or "The candidate").strip() or "The candidate"


def _format_experience(years: float | None, months: int | None) -> str:
    if months is not None and 0 < months < 12:
        return f"{months} month" if months == 1 else f"{months} months"
    if years is None or years <= 0:
        return ""
    display_years = months / 12 if months is not None and months >= 12 else years
    if display_years == int(display_years):
        number = str(int(display_years))
    else:
        number = f"{display_years:.1f}".rstrip("0").rstrip(".")
    return f"{number} year" if number == "1" else f"{number} years"


def _join_items(items: list[str]) -> str:
    values = [item.strip() for item in items if item and item.strip()]
    if len(values) <= 1:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])} and {values[-1]}"


def _qualification_phrase(entry: EducationEntry) -> str:
    base = (entry.qualification or entry.rawQualification or entry.level or "").strip()
    if not base:
        return ""
    if entry.field and not re.search(
        rf"\b{re.escape(entry.field)}\b", base, re.IGNORECASE
    ):
        base = f"{base} in {entry.field}"
    if entry.institution:
        base = f"{base} from {entry.institution}"
    return base


def _qualification_with_article(entry: EducationEntry) -> str:
    phrase = _qualification_phrase(entry)
    if not phrase or entry.level in {"SPM", "STPM / Foundation / Matriculation"}:
        return phrase
    article = "an" if phrase[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {phrase}"


def _strengths(profile: CandidateProfile) -> list[str]:
    values: list[str] = []
    for value in profile.keyStrengths:
        cleaned = re.sub(r"\s+", " ", value).strip(" .")
        if (
            cleaned
            and not is_generic_soft_skill(cleaned)
            and cleaned.lower() not in {item.lower() for item in values}
        ):
            values.append(cleaned)
    if not values:
        for experience in profile.experience:
            if (
                experience.workDomain
                and experience.workDomain.casefold() != (profile.primaryDomain or "").casefold()
                and experience.workDomain.lower() not in {item.lower() for item in values}
            ):
                values.append(experience.workDomain)
    return values[:3]


def build_candidate_summary(profile: CandidateProfile) -> str:
    """Build up to four factual sentences; omit unavailable clauses naturally."""

    name = _display_name(profile)
    sentences: list[str] = []

    has_experience = (
        profile.totalExperienceYears is not None and profile.totalExperienceYears > 0
    ) or (profile.totalExperienceMonths is not None and profile.totalExperienceMonths > 0)
    if has_experience:
        experience_sentence = (
            f"{name} has {_format_experience(profile.totalExperienceYears, profile.totalExperienceMonths)} of experience"
        )
        if profile.primaryDomain:
            experience_sentence += f" in {profile.primaryDomain}"
        sentences.append(experience_sentence + ".")

    highest = select_highest_education(profile.education)
    top_skills = [entry.normalizedName or entry.name for entry in select_top_skills(profile)]
    if highest:
        education_sentence = f"The candidate holds {_qualification_with_article(highest)}"
        if top_skills:
            education_sentence += f" and has experience with {_join_items(top_skills)}"
        sentences.append(education_sentence + ".")
    elif top_skills:
        sentences.append(f"The candidate has experience with {_join_items(top_skills)}.")

    strengths = _strengths(profile)
    if strengths:
        sentences.append(f"Their profile shows experience in {_join_items(strengths)}.")

    fact_clauses: list[str] = []
    if profile.cgpa is not None:
        fact_clauses.append(f"has a CGPA of {profile.cgpa:g}")
    if profile.languages:
        language_labels: list[str] = []
        for language in profile.languages:
            label = language.language
            if language.proficiency:
                label = f"{label} ({language.proficiency})"
            language_labels.append(label)
        fact_clauses.append(f"is proficient in {_join_items(language_labels)}")
    if profile.noticePeriod:
        fact_clauses.append(f"has a notice period of {profile.noticePeriod}")

    if fact_clauses:
        sentences.append(f"{name} {_join_items(fact_clauses)}.")

    return " ".join(sentence.strip() for sentence in sentences if sentence.strip())
