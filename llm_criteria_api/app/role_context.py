"""Generic role-context signals for post-processing JD criteria.

The context is used only to rank already grounded criteria.  It never creates
criteria or adds evidence that is absent from the JD.
"""

from __future__ import annotations

import re
from typing import Any

from .name_validation import morphological_root


_CONTEXT_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "of", "on", "or", "the", "to", "with", "work",
    "job", "role", "position", "department", "team", "responsibility",
    "responsibilities", "requirement", "requirements", "experience",
    "relevant", "professional", "skill", "skills", "knowledge", "ability",
}

_GENERIC_ROLE_TITLE_WORDS = {
    "assistant", "chief", "coordinator", "director", "executive", "head",
    "lead", "leader", "manager", "officer", "specialist", "supervisor",
    "senior", "junior", "analyst", "engineer",
}


def context_tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", str(value or "").casefold())
    result: set[str] = set()
    for token in tokens:
        if token in _CONTEXT_STOPWORDS:
            continue
        root = morphological_root(token)
        if root in _CONTEXT_STOPWORDS or len(root) <= 2:
            continue
        result.add(root)
    return result


def role_title_tokens(value: str) -> set[str]:
    return context_tokens(value) - {
        morphological_root(token) for token in _GENERIC_ROLE_TITLE_WORDS
    }


def build_role_context(job: dict[str, Any]) -> dict[str, Any]:
    responsibilities = [
        str(value).strip()
        for value in job.get("responsibilities", [])
        if str(value).strip()
    ]
    requirements = [
        str(value).strip()
        for value in job.get("requirements", [])
        if str(value).strip()
    ]
    qualifications = [
        str(value).strip()
        for value in job.get("qualifications", [])
        if str(value).strip()
    ]
    full_text = " ".join(
        [
            str(job.get("jobTitle", "")),
            str(job.get("department", "")),
            *responsibilities,
            *requirements,
            *qualifications,
        ]
    )
    return {
        "jobTitle": str(job.get("jobTitle", "")),
        "department": str(job.get("department", "")),
        "titleTokens": role_title_tokens(job.get("jobTitle", "")),
        "departmentTokens": context_tokens(job.get("department", "")),
        "fullTokens": context_tokens(full_text),
        "responsibilities": responsibilities,
        "requirements": requirements,
        "qualifications": qualifications,
        "allTexts": [*responsibilities, *requirements, *qualifications],
    }


def criterion_context_signals(
    criterion: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, float | int | bool]:
    """Measure contextual support without inferring new criterion content."""

    name_tokens = context_tokens(criterion.get("name", ""))
    source_text = str(criterion.get("sourceText", ""))
    source_tokens = context_tokens(source_text)
    title_tokens = set(context.get("titleTokens", set()))
    department_tokens = set(context.get("departmentTokens", set()))
    all_texts = list(context.get("allTexts", []))

    jd_support_count = sum(
        bool(name_tokens & context_tokens(text))
        for text in all_texts
    )
    title_overlap = len(name_tokens & title_tokens)
    department_overlap = len(name_tokens & department_tokens)
    source_parts = [part.strip() for part in source_text.split("|") if part.strip()]
    is_responsibility = any(
        str(source_id).casefold().startswith("responsibilities-")
        for source_id in [
            *criterion.get("sourceIds", []),
            *criterion.get("sourceCriterionIds", []),
        ]
    )
    return {
        "titleOverlap": title_overlap,
        "departmentOverlap": department_overlap,
        "jdSupportCount": jd_support_count,
        "sourceEvidenceCount": len(source_parts),
        "isResponsibility": is_responsibility,
        "sourceTokenCount": len(source_tokens),
    }


__all__ = [
    "build_role_context",
    "context_tokens",
    "criterion_context_signals",
    "role_title_tokens",
]
