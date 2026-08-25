"""Prompt construction for the live production Qwen extraction call.

The frozen notebook prompt remains in ``frozen_pipeline.py`` for parity tests.
This module is used only by the enhanced production path and asks Qwen for
language-understanding signals, never final percentages or eligibility
decisions.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from typing import Any, Mapping


ALLOWED_CRITERION_TYPES = (
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
)


SYSTEM_PROMPT = """You form evidence-backed candidate resume-scoring capabilities from the complete JD.

Do not evaluate a resume. Do not make a hiring, eligibility or final HR decision.
Python extracts explicit hard requirements separately, validates evidence and
taxonomy, preserves source lineage, consolidates safe duplicates and suggests
weights. HR remains the final decision maker and may edit, remove, merge, rename
or add criteria after this response.

Capability-formation process:

1. Read the job title, department and every supplied JD source together. The
   source set is the complete responsibilities, requirements and qualifications
   context; do not remove legitimate evidence before understanding its meaning.
2. Identify the concrete capability, experience, field of study, domain,
   certification or language described by each source. Form a criterion only
   when the source meaning can be grounded as candidate-assessable evidence.
   Generic assigned-duty boilerplate with no defensible capability must not be
   turned into a trait or an invented criterion; leave it for Python's audit.
3. Create one criterion per independently assessable capability, not one per
   sentence. Combine related evidence when one normal resume example would
   ordinarily demonstrate it, including adjacent stages of one coherent
   business, technical or functional outcome.
4. Keep genuinely different capabilities separate when their business objects,
   outcomes, methods or resume evidence differ. Shared verbs, departments or
   broad themes never justify a merge by themselves.
5. Preserve every relevant supporting sourceRef under the criterion it supports.
   A source may support more than one criterion only when its sentence explicitly
   contains more than one independently assessable capability.
6. It is valid for a source to remain unmapped when no grounded candidate
   capability can be formed. Do not invent a criterion merely to increase source
   coverage, and do not treat an unmapped source as an HR importance judgement.
   Python will retain that source in source-accounting metadata for HR review.
7. Use the supplied sourceRefs exactly. Never copy or paraphrase source text in
   the response; Python expands each accepted reference back to the exact JD
   sentence so the final payload remains evidence-preserving.

Resume-assessable evidence includes a practical capability or business process;
a named tool, technology, platform, system or method; specific work, project,
functional or industry experience; an explicit education level or qualification
and, when supplied, a named field of study; knowledge of a named law, regulation,
standard, product or domain; an explicitly preferred named certification; or an
explicitly named job-related language.

Use only these type IDs:

- relevant_skill: a practical capability, method, tool, system, workflow or
  job-related activity that can be demonstrated in a resume.
- relevant_experience: a specific kind of work, project, functional, industry
  or responsibility experience. A minimum-duration statement may also support
  relevance, scope and depth scoring without duplicating eligibility. In a
  construction such as "5 years experience in X", X belongs to experience and
  must not be attached to an education criterion.
- education_relevance: explicit education level, qualification or field-of-study
  evidence. When no field is stated, use the neutral name "Education"; never
  invent a discipline from nearby experience wording. The same source may also
  supply a deterministic hard education threshold because eligibility and soft
  ranking are separate dimensions.
- domain_knowledge: knowledge of a specific law, regulation, formal standard,
  industry, business process, product, function or technical domain.
- preferred_certification: a named certification explicitly described as
  preferred, desirable or advantageous. Do not use it for a mandatory licence
  or certification.
- job_related_language: an explicitly named language required or preferred for
  the role. Never infer a language from location, nationality or title.

Naming rules:

- Use a concise, professional noun phrase, normally 2 to 8 meaningful words.
- Include the concrete domain, object, method or outcome supported by the source.
- Prefer meaningful nouns that occur in the supplied source sentences.
- When several criteria have the same type, make each name distinguish its
  concrete object or outcome. Do not create near-duplicate names that differ
  only through generic words such as Management, Coordination or Support.
- For a criterion with multiple sourceRefs, ensure its name contains a
  concrete noun, method or outcome supported by every referenced sentence. If
  one sentence has no concrete support for the shared name, broaden the name
  with supplied wording or keep that source in a separate criterion.
- Never use a bare generic name such as Management, Development, Support,
  Administration, Coordination, Monitoring, Reporting, Process, System,
  Frontend, Documentation, Technical Skills or Relevant Experience.
- Do not copy a complete sentence or add an unsupported concept.
- Do not include minimum, required, preferred, strong, excellent or must have.

Source reference rules:

- sourceRefs is a non-empty JSON array containing only supplied R#/Q# labels.
- Use multiple sourceRefs only for one coherent capability. Never combine
  unrelated references.
- Do not copy, rewrite, shorten or paraphrase source sentences in the response;
  Python will expand each reference back to the exact supplied sentence.
- Do not return source text, weights, eligibility filters or HR decisions. A
  source that cannot be grounded may remain unmapped; Python records that
  outcome for HR review.

Importance is a relative signal for the initial weight suggestion, never a final
HR decision or a reason to remove evidence. Return exactly high, medium or low.

Do not calculate percentage weights. Do not return suggestedWeight, weight,
eligibility filters, reasoning, markdown or a code fence. Return valid JSON only.
"""


OUTPUT_SHAPE = {
    "candidateCriteria": [
        {
            "type": "<one allowed type ID>",
            "name": "<specific capability noun phrase>",
            "sourceRefs": ["<one or more supplied R#/Q# labels>"],
            "importance": "<high, medium, or low>",
        }
    ]
}


SEMANTIC_CONSOLIDATION_SYSTEM_PROMPT = """You review already validated resume-scoring criteria and identify only clear fragments of the same independently scorable capability.

This is a conservative consolidation review. Do not create criteria, remove
evidence, change types, or group items merely because they share a role,
department, broad theme or common action verb.

Propose a pair only when both criteria describe adjacent parts of one practical
capability, share the same concrete business or technical object, and one
normal resume example would ordinarily demonstrate both. Different outcomes,
separately useful operations, and activities performed at different cadences
remain separate.

Each proposal must contain exactly two supplied criterion IDs of type
relevant_skill. Use each ID at most once. The shared name must be a concise
2-to-8-word noun phrase grounded in both source texts. It must not introduce a
new object, method or outcome.

You may also propose a rename for an unchanged singleton relevant_skill only
when its current name materially omits coordinated concrete objects that are
explicit in its one source text. The replacement must add the omitted supplied
object wording without inventing a broader domain. Do not rename a multi-source
criterion or an item used in a group.

Return empty groups and renames arrays when no change is clearly safe. Return
valid JSON only, with no reasoning, markdown or copied source text."""


SEMANTIC_CONSOLIDATION_OUTPUT_SHAPE = {
    "groups": [
        {
            "type": "<relevant_skill>",
            "name": "<shared grounded capability noun phrase>",
            "memberIds": ["<first supplied criterion ID>", "<second supplied criterion ID>"],
        }
    ],
    "renames": [
        {
            "id": "<one unchanged singleton relevant_skill criterion ID>",
            "name": "<more complete grounded capability noun phrase>",
        }
    ],
}


RESPONSIBILITY_RECOVERY_SYSTEM_PROMPT = """You review JD sources that were not mapped by a previous grounded extraction.

This is a bounded grounding repair, not an importance or HR decision. Add a
criterion only when the supplied source text defensibly supports a candidate-
assessable capability; otherwise it may remain unmapped for HR review.

Create one criterion per independently resume-assessable capability. Group two
or more references only when they describe one coherent capability and one
normal resume example would demonstrate them together. A shared role, verb or
department is not enough. Keep different business objects, outcomes, methods
or evidence separate.

Use only the six allowed criterion type IDs. A practical responsibility is
normally relevant_skill. Use a concise, specific 2-to-8-word noun phrase whose
concrete wording is supported by every referenced sentence. Do not invent
domain terms, weights, eligibility filters or evidence. Return valid JSON only,
without reasoning, markdown or a code fence."""


def _numbered_texts(values: list[str], prefix: str) -> str:
    if not values:
        return "(none)"
    return "\n".join(
        f"{prefix}{index}. {value}" for index, value in enumerate(values, 1)
    )


def _requirement_and_qualification_texts(job: dict[str, Any]) -> list[str]:
    """Return distinct Q# sources while retaining their supplied order."""

    values: list[str] = []
    seen: set[str] = set()
    for key in ("requirements", "qualifications"):
        for value in job.get(key, []):
            cleaned = str(value).strip()
            identity = cleaned.casefold()
            if not cleaned or identity in seen:
                continue
            seen.add(identity)
            values.append(cleaned)
    return values


def build_source_lookup(job: dict[str, Any]) -> dict[str, str]:
    """Map compact prompt references to the exact current-JD source text."""

    lookup: dict[str, str] = {}
    for prefix, values in (
        (
            "R",
            [
                str(value).strip()
                for value in job.get("responsibilities", [])
                if str(value).strip()
            ],
        ),
        ("Q", _requirement_and_qualification_texts(job)),
    ):
        lookup.update(
            {f"{prefix}{index}": value for index, value in enumerate(values, 1)}
        )
    return lookup


def build_extraction_messages(
    job: dict[str, Any],
    *,
    source_lookup: Mapping[str, str] | None = None,
    required_source_refs: Collection[str] | None = None,
    supporting_use_by_ref: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build capability formation from the complete supplied JD evidence set.

    Legacy keyword arguments remain accepted for caller compatibility, but they
    no longer filter semantic input or create mandatory coverage obligations.
    """

    resolved_lookup = {
        str(key).strip().upper(): str(value).strip()
        for key, value in (source_lookup or build_source_lookup(job)).items()
        if str(key).strip() and str(value).strip()
    }
    formation_sources = [
        {
            "sourceRef": source_ref,
            "text": source_text,
            "section": (
                "responsibilities"
                if source_ref.startswith("R")
                else "requirements_or_qualifications"
            ),
        }
        for source_ref, source_text in resolved_lookup.items()
    ]
    user_prompt = (
        f"Job title:\n{str(job.get('jobTitle', '')).strip()}\n\n"
        f"Department:\n{str(job.get('department', '')).strip()}\n\n"
        "Complete JD evidence:\n"
        + json.dumps(formation_sources, ensure_ascii=False, indent=2)
        + "\n\n"
        "Return this exact JSON structure:\n"
        + json.dumps(OUTPUT_SHAPE, indent=2)
        + "\n\nThe text between <angle brackets> specifies a field and is not an "
        "example value. Never copy placeholder text. The object shown inside "
        "candidateCriteria defines fields only; repeat it for every actual "
        "capability needed.\n\n"
        "Available source-reference checklist:\n"
        + json.dumps(list(resolved_lookup))
        + "\nUse only labels from this checklist. It is valid for a supplied source "
        "to remain unmapped when no grounded candidate capability can be formed; "
        "do not invent a criterion or an HR importance judgement.\n\n"
        "Requirements for this response:\n"
        "- understand all listed sources before grouping;\n"
        "- preserve every sourceRef used by a grouped criterion;\n"
        "- leave generic assigned-duty boilerplate unmapped unless the text itself "
        "provides grounded candidate-assessable evidence;\n"
        "- use only the six allowed type IDs;\n"
        "- do not return suggestedWeight or percentage weights;\n"
        "- do not return eligibility filters;\n"
        "- do not create evidence absent from the JD;\n"
        "- do not return markdown or wrap JSON in a code block."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_extraction_retry_messages(
    job: dict[str, Any],
    previous_raw_output: str,
    missing_source_refs: Collection[str] | None = None,
    misaligned_source_refs: Collection[str] | None = None,
    *,
    source_lookup: Mapping[str, str] | None = None,
    required_source_refs: Collection[str] | None = None,
    supporting_use_by_ref: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build one focused repair request without changing the JD evidence."""

    user_prompt = build_extraction_messages(
        job,
        source_lookup=source_lookup,
        required_source_refs=required_source_refs,
        supporting_use_by_ref=supporting_use_by_ref,
    )[1]["content"]
    missing_refs = sorted(
        {
            str(source_ref).strip().upper()
            for source_ref in (missing_source_refs or [])
            if str(source_ref).strip()
        }
    )
    accounting_repair = ""
    if missing_refs:
        accounting_repair = (
            "\n\nThe previous response left these supplied references "
            "unaccounted for:\n"
            + json.dumps(missing_refs)
            + "\nReview each listed reference. Put it in an appropriately grounded "
            "criterion sourceRefs array only when the JD text supports a "
            "candidate-assessable capability; otherwise leave it unmapped."
        )
    misaligned_refs = sorted(
        {
            str(source_ref).strip().upper()
            for source_ref in (misaligned_source_refs or [])
            if str(source_ref).strip()
        }
    )
    alignment_repair = ""
    if misaligned_refs:
        alignment_repair = (
            "\n\nThe previous response used these references only inside "
            "criteria whose names contain no concrete noun, method or outcome "
            "supported by that sentence:\n"
            + json.dumps(misaligned_refs)
            + "\nFor each listed reference, move it to a correctly named "
            "criterion, revise the shared name with concrete supplied wording "
            "from every referenced sentence, or separate it into a new "
            "criterion. Do not leave a substantive reference attached only to "
            "an unsupported name."
        )
    user_prompt = (
        "Repair your previous response for the same complete JD. Preserve its "
        "valid criteria and source-reference decisions unless they conflict "
        "with the supplied JD or schema. Add, regroup or remove entries only "
        "as needed to fix the stated grounding/accounting problem. Return the complete "
        "corrected JSON response, not a patch. Return valid JSON only."
        + accounting_repair
        + alignment_repair
        + "\n\n"
        + user_prompt
        + "\n\nPrevious response for diagnosis only:\n"
        + previous_raw_output
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_responsibility_recovery_messages(
    job: dict[str, Any],
    missing_source_lookup: dict[str, str],
    existing_criteria: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build a bounded recovery request for already identified coverage gaps."""

    missing_sources = [
        {"ref": source_ref, "text": source_text}
        for source_ref, source_text in missing_source_lookup.items()
    ]
    existing_summary = [
        {
            "type": str(item.get("type", "")).strip(),
            "name": str(item.get("name", "")).strip(),
            "sourceIds": list(item.get("sourceIds", [])),
        }
        for item in existing_criteria
    ]
    user_prompt = (
        f"Job title:\n{str(job.get('jobTitle', '')).strip()}\n\n"
        f"Department:\n{str(job.get('department', '')).strip()}\n\n"
        "Validated criteria already retained (context only; do not repeat or "
        "modify them):\n"
        + json.dumps(existing_summary, ensure_ascii=False, indent=2)
        + "\n\nJD source references still unmapped after validation:\n"
        + json.dumps(missing_sources, ensure_ascii=False, indent=2)
        + "\n\nReturn this exact JSON structure:\n"
        + json.dumps(OUTPUT_SHAPE, ensure_ascii=False, indent=2)
        + "\nThe angle-bracket text defines fields only; never copy it. "
        "Use only supplied refs. Do not repeat an existing "
        "criterion unless a missing source genuinely adds evidence to the same "
        "capability. Do not return weights, eligibility, reasoning or markdown."
    )
    return [
        {"role": "system", "content": RESPONSIBILITY_RECOVERY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_semantic_consolidation_messages(
    criteria: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build an isolated review that cannot alter primary extraction."""

    review_items = [
        {
            "id": str(item.get("criterionId", "")).strip(),
            "type": str(item.get("type", "")).strip(),
            "name": str(item.get("name", "")).strip(),
            "sourceIds": list(item.get("sourceIds", [])),
            "sourceTexts": [
                part.strip()
                for part in str(item.get("sourceText", "")).split("|")
                if part.strip()
            ],
        }
        for item in criteria
        if str(item.get("criterionId", "")).strip()
    ]
    user_prompt = (
        "Validated criteria for conservative pair review:\n"
        + json.dumps(review_items, ensure_ascii=False, indent=2)
        + "\n\nReturn this exact JSON structure:\n"
        + json.dumps(
            SEMANTIC_CONSOLIDATION_OUTPUT_SHAPE,
            ensure_ascii=False,
            indent=2,
        )
        + "\nThe angle-bracket text specifies fields only; never copy it. "
        "Omit unchanged singleton criteria from groups and renames. Return "
        "JSON only."
    )
    return [
        {"role": "system", "content": SEMANTIC_CONSOLIDATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


__all__ = [
    "ALLOWED_CRITERION_TYPES",
    "OUTPUT_SHAPE",
    "SYSTEM_PROMPT",
    "build_source_lookup",
    "build_extraction_messages",
    "build_extraction_retry_messages",
    "build_responsibility_recovery_messages",
    "build_semantic_consolidation_messages",
]
