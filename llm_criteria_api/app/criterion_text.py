"""Deterministic HR-facing criterion text generated after validation."""

from __future__ import annotations

from typing import Any


DESCRIPTION_TEMPLATES = {
    "relevant_skill": "Evaluates demonstrated ability in {name}.",
    "relevant_experience": (
        "Evaluates the relevance, depth, responsibility scope, duration and outcomes "
        "of the candidate's {name}."
    ),
    "education_relevance": (
        "Evaluates how directly the candidate's education level, field or academic "
        "background supports {name}."
    ),
    "domain_knowledge": "Evaluates the candidate's knowledge and practical understanding of {name}.",
    "preferred_certification": "Evaluates possession and relevance of {name}.",
    "job_related_language": "Evaluates job-related proficiency in {name}.",
}


EVIDENCE_RULE_TEMPLATES = {
    "relevant_skill": (
        "The resume should show this skill in work experience, projects, "
        "achievements, or a skills section."
    ),
    "relevant_experience": (
        "The resume should show relevant roles, responsibility scope, duration, "
        "working environment and measurable outcomes beyond the minimum requirement."
    ),
    "education_relevance": (
        "The resume should show the required or relevant qualification level and, "
        "when stated by the JD, a matching field of study, coursework, academic "
        "projects or equivalent job-related learning; higher qualifications are "
        "not rewarded unless they remain relevant."
    ),
    "domain_knowledge": (
        "The resume should show this knowledge through relevant roles, responsibilities, "
        "projects, training, compliance work or achievements."
    ),
    "preferred_certification": (
        "The resume should show the named certification and its current or relevant status."
    ),
    "job_related_language": (
        "The resume should show the named language through a language section, work "
        "experience, education or job-related communication evidence."
    ),
}


def apply_deterministic_criterion_texts(
    criteria: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace model-facing text fields with stable Python-generated values."""

    result: list[dict[str, Any]] = []
    for item in criteria:
        criterion_type = str(item.get("type", ""))
        name = str(item.get("name", "")).strip()
        updated = dict(item)
        if criterion_type in DESCRIPTION_TEMPLATES:
            updated["description"] = DESCRIPTION_TEMPLATES[criterion_type].format(
                name=name
            )
            updated["evidenceRule"] = EVIDENCE_RULE_TEMPLATES[criterion_type]
        result.append(updated)
    return result


__all__ = [
    "DESCRIPTION_TEMPLATES",
    "EVIDENCE_RULE_TEMPLATES",
    "apply_deterministic_criterion_texts",
]
