"""Safe criterion-name validation fixes applied outside the frozen pipeline."""

from __future__ import annotations

import json
import re
from typing import Any, Callable


_MORPHOLOGICAL_EQUIVALENTS = {
    "handle": "manage",
    "handling": "manage",
    "handled": "manage",
    "maintain": "maintain",
    "maintenance": "maintain",
    "maintaining": "maintain",
    "monitor": "monitor",
    "monitoring": "monitor",
    "monitored": "monitor",
    "comply": "comply",
    "compliance": "comply",
    "compliant": "comply",
    "manag": "manage",
    "manage": "manage",
    "managed": "manage",
    "management": "manage",
    "managing": "manage",
    "supervis": "supervise",
    "supervise": "supervise",
    "supervised": "supervise",
    "supervision": "supervise",
    "supervising": "supervise",
    "advise": "advise",
    "advice": "advise",
    "advisory": "advise",
    "document": "document",
    "documentation": "document",
    "documenting": "document",
    "develop": "develop",
    "developed": "develop",
    "developing": "develop",
    "development": "develop",
    "produce": "produce",
    "producing": "produce",
    "production": "produce",
    "analyse": "analyse",
    "analyze": "analyse",
    "analysis": "analyse",
    "analyses": "analyse",
    "analysi": "analyse",
    "analysing": "analyse",
    "analyzing": "analyse",
    "investigate": "investigate",
    "investigation": "investigate",
    "investigating": "investigate",
    "reconcile": "reconcile",
    "reconciliation": "reconcile",
    "reconciling": "reconcile",
    "prepare": "prepare",
    "prepared": "prepare",
    "preparing": "prepare",
    "preparation": "prepare",
    "verify": "verify",
    "verified": "verify",
    "verifying": "verify",
    "verification": "verify",
    "invoice": "invoice",
    "invoices": "invoice",
    "invoicing": "invoice",
    "discrepancy": "discrepancy",
    "discrepancies": "discrepancy",
    "policy": "policy",
    "policies": "policy",
    "law": "law",
    "laws": "law",
    "administer": "administer",
    "administration": "administer",
    "administering": "administer",
    "coordinate": "coordinate",
    "coordination": "coordinate",
    "coordinating": "coordinate",
    "source": "source",
    "sourced": "source",
    "sourcing": "source",
    "screen": "screen",
    "screened": "screen",
    "screening": "screen",
    "schedule": "schedule",
    "scheduled": "schedule",
    "scheduling": "schedule",
}

_GENERIC_NAME_TOKENS = {
    "academic", "education", "field", "relevance", "technical",
    "work", "working", "candidate", "quality", "professional",
    "tool", "statutory",
}

_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in",
    "of", "on", "or", "the", "to", "with", "this", "that", "their",
}

_ACTION_NOUNS = {
    "maintain": "Maintenance",
    "monitor": "Monitoring",
    "comply": "Compliance",
    "manage": "Management",
    "supervise": "Supervision",
    "advise": "Advice",
    "document": "Documentation",
    "produce": "Production",
    "analyse": "Analysis",
    "investigate": "Investigation",
    "reconcile": "Reconciliation",
    "administer": "Administration",
    "coordinate": "Coordination",
}

_MANAGEMENT_ACTIONS = {
    "administer", "coordinate", "handle", "lead", "manage", "oversee",
    "supervise",
}

_GENERIC_HEAD_ROOTS = {
    "administer",
    "comply",
    "coordinate",
    "control",
    "develop",
    "manage",
    "maintain",
    "monitor",
    "process",
    "report",
    "secure",
    "support",
}

_SOURCE_OBJECT_STOPWORDS = {
    "a", "an", "and", "are", "be", "by", "for", "from", "in", "into",
    "is", "of", "on", "or", "the", "to", "with",
    "activities", "activity", "arrangements", "assigned", "company",
    "documentation", "duties", "matters", "processes", "records", "tasks",
    "work", "working",
}


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def morphological_root(token: str) -> str:
    """Return a conservative root for common capability word forms."""

    cleaned = re.sub(r"[^a-z0-9]", "", token.lower())
    if cleaned in _MORPHOLOGICAL_EQUIVALENTS:
        return _MORPHOLOGICAL_EQUIVALENTS[cleaned]
    # The frozen grounding tokenizer has already reduced some ``-ities``
    # plurals to ``-itie`` (for example opportunities -> opportunitie).
    # Restore the shared singular root before comparing model names to JD
    # evidence.
    if len(cleaned) > 5 and cleaned.endswith("itie"):
        return cleaned[:-2] + "y"
    if len(cleaned) > 6 and cleaned.endswith("ing"):
        return cleaned[:-3]
    if len(cleaned) > 5 and cleaned.endswith("ed"):
        return cleaned[:-2]
    if len(cleaned) > 5 and cleaned.endswith("ies"):
        return cleaned[:-3] + "y"
    if len(cleaned) > 5 and cleaned.endswith("s"):
        return cleaned[:-1]
    return cleaned


def source_contributes_to_name(name: str, source_text: str) -> bool:
    """Return whether one source supplies a concrete object in the name.

    Multi-source extraction can make every reference look accounted for while
    attaching a sentence to a criterion whose name describes only the other
    sentences. This deliberately ignores generic capability heads so shared
    words such as ``management`` or ``monitoring`` cannot count as concrete
    support.
    """

    name_roots = {
        morphological_root(token)
        for token in _tokenize(name)
        if token not in _STOPWORDS
        and token not in _GENERIC_NAME_TOKENS
        and morphological_root(token) not in _GENERIC_HEAD_ROOTS
        and morphological_root(token) not in _ACTION_NOUNS
        and len(morphological_root(token)) > 2
    }
    if not name_roots:
        # The frozen name validator remains responsible for generic names.
        return True
    source_roots = {
        morphological_root(token)
        for token in _tokenize(source_text)
        if token not in _STOPWORDS
    }
    return bool(name_roots & source_roots)


def normalised_unsupported_tokens(
    original_detector: Callable[[str, str], list[str]],
    name: str,
    source_text: str,
) -> list[str]:
    """Keep the frozen detector's boundaries but accept equivalent word forms."""

    raw_unsupported = original_detector(name, source_text)
    source_roots = {
        morphological_root(token)
        for token in _tokenize(source_text)
        if token not in _STOPWORDS
    }
    source_tokens = set(_tokenize(source_text))
    if any(token in source_tokens for token in _MANAGEMENT_ACTIONS):
        raw_unsupported = [
            token for token in raw_unsupported
            if morphological_root(token) != "manage"
        ]
    return sorted(
        token
        for token in raw_unsupported
        if morphological_root(token) not in source_roots
    )


def _related_source_context(
    frozen_module: Any,
    raw_source_text: str,
    name: str,
    allowed_source_texts: list[str],
) -> str:
    """Collect adjacent same-capability evidence without mixing unrelated work."""

    raw_parts = [
        frozen_module.normalise_text(part)
        for part in raw_source_text.split("|")
        if frozen_module.normalise_text(part)
    ]
    if not raw_parts:
        return raw_source_text

    # A broad scope-list sentence may legitimately be the evidence for one
    # role-level capability. Do not widen it with neighbouring sentences
    # during name repair; that would make grounding judge unrelated domains
    # as one capability. Explicit multi-sentence model evidence is still
    # handled by the grounding adapter.
    if (
        len(raw_parts) == 1
        and raw_parts[0].count(",") >= 5
        and raw_parts[0].casefold().count(" and ") >= 2
    ):
        return raw_parts[0]

    raw_roots = {
        morphological_root(token)
        for token in _tokenize(" ".join(raw_parts))
        if token not in _STOPWORDS
    }
    name_roots = {
        morphological_root(token)
        for token in _tokenize(name)
        if token not in _STOPWORDS and token not in _GENERIC_NAME_TOKENS
    }
    selected: list[str] = list(raw_parts)
    for source in allowed_source_texts:
        cleaned = frozen_module.normalise_text(source)
        if not cleaned or cleaned in selected:
            continue
        source_roots = {
            morphological_root(token)
            for token in _tokenize(cleaned)
            if token not in _STOPWORDS
        }
        raw_overlap = len(raw_roots & source_roots)
        name_overlap = len(name_roots & source_roots)
        if (
            raw_overlap >= 2
            or (raw_overlap >= 1 and name_overlap >= 1)
            or name_overlap >= 2
        ):
            selected.append(cleaned)
    return " | ".join(dict.fromkeys(selected))


def _supported_name_tokens(
    original_detector: Callable[[str, str], list[str]],
    name: str,
    source_text: str,
) -> set[str]:
    source_roots = {
        morphological_root(token)
        for token in _tokenize(source_text)
        if token not in _STOPWORDS
    }
    return {
        token
        for token in _tokenize(name)
        if token in _GENERIC_NAME_TOKENS
        or morphological_root(token) in source_roots
        or token not in original_detector(name, source_text)
    }


def _title_phrase(tokens: list[str]) -> str:
    return " ".join(token.capitalize() for token in tokens)


def _token_variants(token: str) -> set[str]:
    """Return conservative lexical forms for phrase grounding."""

    cleaned = morphological_root(token)
    variants = {cleaned}
    if cleaned.endswith("y") and len(cleaned) > 3:
        variants.add(cleaned[:-1] + "ies")
    return variants


def _is_generic_head_name(name: str) -> bool:
    tokens = [
        token
        for token in _tokenize(name)
        if token not in _STOPWORDS and token not in _GENERIC_NAME_TOKENS
    ]
    return len(tokens) == 1 and morphological_root(tokens[0]) in _GENERIC_HEAD_ROOTS


def _source_object_tokens(source_text: str) -> list[str]:
    """Extract a short, evidence-bound object phrase after a source action."""

    tokens = _tokenize(source_text)
    action_roots = set(_ACTION_NOUNS) | _MANAGEMENT_ACTIONS | {
        "control", "develop", "process", "report", "secure", "support",
    }
    action_index = next(
        (
            index
            for index, token in enumerate(tokens)
            if morphological_root(token) in action_roots
        ),
        -1,
    )
    candidates = tokens[action_index + 1 :] if action_index >= 0 else tokens
    result: list[str] = []
    for token in candidates:
        root = morphological_root(token)
        if token in _SOURCE_OBJECT_STOPWORDS or root in _ACTION_NOUNS:
            if result and root in _ACTION_NOUNS:
                break
            continue
        if len(token) <= 2:
            continue
        result.append(token)
        if len(result) >= 3:
            break
    return result


def _specific_name_from_evidence(
    original_name: str,
    source_text: str,
) -> str | None:
    """Keep a supported domain phrase when a repair would become generic."""

    source_tokens = _source_object_tokens(source_text)
    if not source_tokens:
        return None

    action_root = next(
        (
            morphological_root(token)
            for token in _tokenize(original_name)
            if morphological_root(token) in _ACTION_NOUNS
        ),
        None,
    )
    if action_root is None:
        action_root = next(
            (
                morphological_root(token)
                for token in _tokenize(source_text)
                if morphological_root(token) in _ACTION_NOUNS
            ),
            None,
        )
    action_noun = _ACTION_NOUNS.get(action_root or "")

    source_roots = {
        morphological_root(token)
        for token in _tokenize(source_text)
        if token not in _STOPWORDS
    }
    supported_original = [
        token
        for token in _tokenize(original_name)
        if token not in _STOPWORDS
        and morphological_root(token) not in _GENERIC_HEAD_ROOTS
        and morphological_root(token) in source_roots
    ]
    object_tokens = list(dict.fromkeys(supported_original + source_tokens))[:2]
    if not object_tokens:
        return None

    candidate_tokens = object_tokens + ([action_noun.lower()] if action_noun else [])
    candidate = _title_phrase(candidate_tokens[:6])
    if not candidate or _is_generic_head_name(candidate):
        return None
    return candidate


def _longest_supported_prefix(prefix: list[str], source_text: str) -> int:
    """Find the longest contiguous name prefix present in the evidence."""

    source_tokens = _tokenize(source_text)
    if not source_tokens:
        return 0
    for length in range(len(prefix), 1, -1):
        for start in range(len(prefix) - length + 1):
            phrase = prefix[start : start + length]
            for source_start in range(len(source_tokens) - length + 1):
                if all(
                    _token_variants(name_token)
                    & _token_variants(source_tokens[source_start + offset])
                    for offset, name_token in enumerate(phrase)
                ):
                    return length
    return 1 if any(
        _token_variants(token) & {
            morphological_root(source_token) for source_token in source_tokens
        }
        for token in prefix
    ) else 0


def _compact_multisource_name(
    original_detector: Callable[[str, str], list[str]],
    name: str,
    source_text: str,
) -> str:
    """Keep the main supported phrase when a multi-source name is too broad.

    A corrected name can contain several supported nouns from a source list.
    When those nouns are not one capability phrase, retain the longest grounded
    context phrase and the supported capability head instead of selecting the
    last operational keyword.
    """

    if "|" not in source_text:
        return name
    tokens = [token for token in _tokenize(name) if token not in _STOPWORDS]
    if len(tokens) < 4:
        return name

    head_index = next(
        (
            index
            for index in range(len(tokens) - 1, -1, -1)
            if morphological_root(tokens[index]) in _ACTION_NOUNS
            or morphological_root(tokens[index]) == "manage"
        ),
        None,
    )
    if head_index is None or head_index < 2:
        return name

    prefix = tokens[:head_index]
    supported_length = _longest_supported_prefix(prefix, source_text)
    if supported_length >= len(prefix) or supported_length < 2:
        return name

    candidate = _title_phrase(prefix[:supported_length] + [tokens[head_index]])
    if not normalised_unsupported_tokens(
        original_detector,
        candidate,
        source_text,
    ):
        return candidate
    return name


def _concise_supported_name_with_context(
    original_detector: Callable[[str, str], list[str]],
    name: str,
    source_text: str,
) -> tuple[str | None, str | None]:
    """Repair a name without copying the complete JD sentence."""

    unsupported = set(
        normalised_unsupported_tokens(original_detector, name, source_text)
    )
    if not unsupported:
        if _is_generic_head_name(name):
            specific = _specific_name_from_evidence(name, source_text)
            if specific and not normalised_unsupported_tokens(
                original_detector,
                specific,
                source_text,
            ):
                return specific, specific
            return None, None
        return name, name

    kept = [
        token
        for token in _tokenize(name)
        if token not in unsupported
        and (token in _GENERIC_NAME_TOKENS or token not in unsupported)
    ]
    kept = [token for token in kept if token not in {"and", "or", "of", "in", "to"}]
    if kept:
        candidate = _title_phrase(kept[:8])
        if not normalised_unsupported_tokens(original_detector, candidate, source_text):
            if _is_generic_head_name(candidate):
                specific = _specific_name_from_evidence(name, source_text)
                if specific and not normalised_unsupported_tokens(
                    original_detector,
                    specific,
                    source_text,
                ):
                    return specific, specific
                return None, None
            compacted = _compact_multisource_name(
                original_detector,
                candidate,
                source_text,
            )
            return compacted, candidate

    source_tokens = [
        token for token in _tokenize(source_text)
        if token not in _STOPWORDS
    ]
    if not source_tokens:
        return None, None

    action_root = morphological_root(source_tokens[0])
    object_tokens = source_tokens[1:6]
    if not object_tokens:
        object_tokens = source_tokens[:5]
    action_noun = _ACTION_NOUNS.get(action_root)
    candidate_tokens = object_tokens + ([action_noun.lower()] if action_noun else [])
    candidate = _title_phrase(candidate_tokens[:8])
    if not candidate or normalised_unsupported_tokens(original_detector, candidate, source_text):
        return None, None
    return candidate, candidate


def concise_supported_name(
    original_detector: Callable[[str, str], list[str]],
    name: str,
    source_text: str,
) -> str | None:
    """Repair a name without copying the complete JD sentence."""

    repaired, _support_name = _concise_supported_name_with_context(
        original_detector,
        name,
        source_text,
    )
    return repaired


class CriterionNameValidationAdapter:
    """Repair unsupported names before calling the unchanged frozen validator."""

    def __init__(self, frozen_module: Any) -> None:
        self.frozen = frozen_module
        self.original_detector = frozen_module.criterion_name_unsupported_tokens

    def normalised_detector(self, name: str, source_text: str) -> list[str]:
        return normalised_unsupported_tokens(
            self.original_detector,
            name,
            source_text,
        )

    def _repair_raw_output(
        self,
        raw_text: str,
        allowed_source_texts: list[str],
        *,
        expand_evidence: bool = True,
    ) -> tuple[str, list[str]]:
        payload, parse_error = self.frozen.extract_json_object(raw_text)
        if parse_error or not isinstance(payload, dict):
            return raw_text, []
        raw_criteria = payload.get("criteria")
        if not isinstance(raw_criteria, list):
            return raw_text, []

        corrections: list[str] = []
        updated_criteria: list[Any] = []
        for index, item in enumerate(raw_criteria, start=1):
            if not isinstance(item, dict):
                updated_criteria.append(item)
                continue
            name = self.frozen.normalise_text(item.get("name"))
            source_text = self.frozen.normalise_text(item.get("sourceText"))
            if not name or not source_text:
                updated_criteria.append(item)
                continue
            evidence_text = (
                _related_source_context(
                    self.frozen,
                    source_text,
                    name,
                    allowed_source_texts,
                )
                if expand_evidence
                else source_text
            )
            repaired, support_name = _concise_supported_name_with_context(
                self.original_detector,
                name,
                evidence_text,
            )
            if repaired is None and _is_generic_head_name(name):
                corrections.append(
                    f"Criterion {index} generic name '{name}' was rejected "
                    "because no evidence-supported specific capability name "
                    "could be derived."
                )
                continue
            evidence_changed = evidence_text != source_text
            if repaired and (
                repaired != name
                or (
                    evidence_changed
                    and not normalised_unsupported_tokens(
                        self.original_detector,
                        name,
                        evidence_text,
                    )
                )
            ):
                updated = dict(item)
                updated["name"] = repaired
                if evidence_changed:
                    updated["sourceText"] = evidence_text
                if support_name and support_name != repaired:
                    # Internal adapter metadata lets multi-source grounding
                    # validate the broader pre-compaction capability phrase.
                    # The frozen validator ignores unknown model fields.
                    updated["_nameValidationSupportName"] = support_name
                updated_criteria.append(updated)
                corrections.append(
                    f"Criterion {index} name corrected from '{name}' to '{repaired}'."
                )
            else:
                updated_criteria.append(item)

        if not corrections:
            return raw_text, []
        repaired_payload = dict(payload)
        repaired_payload["criteria"] = updated_criteria
        return json.dumps(repaired_payload, ensure_ascii=False), corrections

    def validate(
        self,
        original_validate: Callable[..., tuple[list[dict[str, Any]], dict[str, Any]]],
        raw_text: str,
        allowed_source_texts: list[str],
        source_id_prefix: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        repaired_raw_text, corrections = self.prepare(
            raw_text,
            allowed_source_texts,
        )
        # The frozen validator resolves its detector through the module global.
        # Use the enhanced detector for this adapter call, then restore the
        # frozen function immediately so frozen parity remains untouched.
        previous_detector = self.frozen.criterion_name_unsupported_tokens
        self.frozen.criterion_name_unsupported_tokens = self.normalised_detector
        try:
            criteria, diagnostics = original_validate(
                repaired_raw_text,
                allowed_source_texts,
                source_id_prefix=source_id_prefix,
            )
        finally:
            self.frozen.criterion_name_unsupported_tokens = previous_detector
        if corrections:
            diagnostics.setdefault("normalisations", []).extend(corrections)
            diagnostics.setdefault("warnings", []).extend(corrections)
            diagnostics["nameCorrections"] = corrections
            diagnostics["finalRawModelOutput"] = repaired_raw_text
        return criteria, diagnostics

    def prepare(
        self,
        raw_text: str,
        allowed_source_texts: list[str],
        *,
        expand_evidence: bool = True,
    ) -> tuple[str, list[str]]:
        return self._repair_raw_output(
            raw_text,
            allowed_source_texts,
            expand_evidence=expand_evidence,
        )


__all__ = [
    "CriterionNameValidationAdapter",
    "concise_supported_name",
    "morphological_root",
    "normalised_unsupported_tokens",
    "source_contributes_to_name",
]
