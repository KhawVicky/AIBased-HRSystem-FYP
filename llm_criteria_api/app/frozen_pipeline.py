import json
import re
from difflib import SequenceMatcher
from typing import Any

import torch
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
except ImportError:  # FastAPI mock and cached-fixture modes do not load a model.
    AutoModelForCausalLM = AutoTokenizer = BitsAndBytesConfig = None

MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
MAX_NEW_TOKENS = 900
USE_4BIT = torch.cuda.is_available()
DEVICE_LABEL = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"


SOFT_CRITERIA_FRAMEWORK = {
    "relevant_skill": {
        "label": "Relevant Skill",
        "description": (
            "Specific technical skills, tools, systems, work activities, "
            "and practical abilities required by the JD."
        ),
    },
    "relevant_experience": {
        "label": "Relevant Experience",
        "description": (
            "Strength, depth, responsibility match, industry relevance, "
            "and working-environment relevance beyond a minimum threshold."
        ),
    },
    "education_relevance": {
        "label": "Education Relevance",
        "description": (
            "Relevance of the candidate's education field to the work, "
            "without automatically preferring a higher qualification level."
        ),
    },
    "domain_knowledge": {
        "label": "Domain Knowledge",
        "description": (
            "Professional processes, regulations, standards, business "
            "knowledge, or technical principles explicitly required by the JD."
        ),
    },
    "preferred_certification": {
        "label": "Preferred Certification",
        "description": (
            "A certification or licence explicitly described as preferred, "
            "desirable, advantageous, or an added advantage."
        ),
    },
    "job_related_language": {
        "label": "Job-Related Language",
        "description": (
            "A language explicitly required or preferred for the work. "
            "Never infer a language from the job title or department."
        ),
    },
}

ALLOWED_SOFT_CRITERIA_TYPES = set(SOFT_CRITERIA_FRAMEWORK)

SYSTEM_PROMPT = """You extract resume-scoring soft criteria from one JD section.

Allowed type IDs:
- relevant_skill
- relevant_experience
- education_relevance
- domain_knowledge
- preferred_certification
- job_related_language

Rules:
1. Use only explicit evidence from the supplied section text. Never infer from job title or department.
2. Extract every clearly supported, meaningful criterion. Aim for 1 to 4 concise criteria for this section, but do not omit a distinct core capability or an explicit language, education, experience, knowledge, or preferred-certification criterion only to meet that range.
3. Merge duties only when they evaluate the same overall capability. Do not create one criterion per sentence or minor task. Do not copy criterion names from examples or instructions. Create every criterion name only from the supplied JD section. Each name must accurately describe its own sourceText and must not introduce another job function, technology, industry, or process that the sourceText does not explicitly support.
4. Never create another type ID and do not force all types to appear.
5. Practical work activities, tools, systems, and abilities are relevant_skill.
6. Education qualifications, degrees, diplomas, fields of study, and related disciplines are education_relevance, not relevant_skill.
7. Laws, regulations, standards, statutory requirements, compliance frameworks, professional principles, and formal business rules are domain_knowledge.
8. Performing or managing a process is relevant_skill; only understanding its rules, standards, or principles is domain_knowledge.
9. relevant_experience evaluates strength, relevance, depth, responsibility scope, industry context, and working environment beyond eligibility.
10. Never use the word minimum in a soft criterion name.
11. job_related_language requires an exact language name in sourceText, such as English, Bahasa Malaysia, Mandarin, or Japanese.
12. Mandatory certifications or licences are hard criteria. preferred_certification requires preferred, desirable, advantage, or added advantage wording.
13. Every sourceText must be a short grounded quote or close excerpt from one supplied section item. Keep the distinctive job-specific terms; do not invent unsupported evidence.
14. Return only criterion type, name, and sourceText. Do not assign weights, descriptions, evidence rules, or ignored texts.
15. Return JSON only. HR will review the Python-validated result.
"""

SECTION_OUTPUT_SHAPE = {
    "criteria": [
        {
            "type": "allowed_type_id",
            "name": "Concise HR-facing criterion name",
            "sourceText": "Grounded evidence from the JD.",
        }
    ],
}

SECTION_GUIDANCE = {
    "responsibilities": (
        "Merge duties only when they evaluate the same overall capability. "
        "Do not copy criterion names from examples or instructions. Create every "
        "criterion name only from the supplied JD section. The criterion name must "
        "accurately describe its own sourceText. Do not introduce another job function, "
        "technology, industry, or process that is not explicitly supported by the "
        "sourceText. Focus on concrete work activities, tools, systems, and processes. "
        "Do not infer education, certification, language, or experience years from "
        "duties alone."
    ),
    "requirements": (
        "Group related requirements into concise job-level criteria without dropping "
        "a distinct, explicitly stated requirement merely to reduce the count. Focus "
        "on explicitly stated skills, experience relevance, education-field "
        "relevance, professional knowledge, preferred certifications, and named "
        "languages. Mandatory certifications are hard criteria and must not become "
        "preferred_certification. Convert minimum education or experience only into "
        "a soft measure of relevance or depth beyond the threshold."
    ),
}

def build_section_messages(
    jd_input: dict[str, Any],
    section_name: str,
    section_texts: list[str],
) -> list[dict[str, str]]:
    user_prompt = (
        "Soft criteria framework:\\n"
        + json.dumps(SOFT_CRITERIA_FRAMEWORK, indent=2)
        + "\\n\\nSupporting context (do not extract from context alone):\\n"
        + json.dumps(
            {
                "jobTitle": jd_input.get("jobTitle", ""),
                "department": jd_input.get("department", ""),
            },
            indent=2,
        )
        + f"\\n\\nSection: {section_name}\\n"
        + "Section-specific guidance:\\n"
        + SECTION_GUIDANCE[section_name]
        + "\\n\\nSection texts:\\n"
        + json.dumps(section_texts, indent=2)
        + "\\n\\nReturn exactly this JSON structure:\\n"
        + json.dumps(SECTION_OUTPUT_SHAPE, indent=2)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

GENERIC_DUTY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(?:(?:perform|complete|carry out|handle|undertake)\s+)?"
        r"(?:any\s+)?(?:other\s+)?(?:ad[ -]?hoc\s+)?"
        r"(?:duties|tasks|assignments|responsibilit(?:y|ies))"
        r"(?:\s+(?:as|when|which may be|to be))?\s+"
        r"(?:assigned|instructed|required|requested)"
        r"(?:\s+(?:from time to time|by\s+(?:the\s+)?"
        r"(?:manager|management|superior|department head)))?"
        r"(?:\s+from time to time)?",
        r"(?:follow|adhere to|comply with|maintain consistent application of)"
        r"\s+(?:all\s+)?(?:company\s+)?"
        r"(?:policies|procedures|rules|guidelines)"
        r"(?:\s*(?:,|and)\s*(?:policies|procedures|rules|guidelines))*",
        r"report\s+to\s+(?:the\s+)?(?:manager|management|supervisor|superior)",
    )
]

GENERIC_DUTY_REASON = (
    "Generic duty that is not useful for candidate scoring."
)

DEFAULT_TYPE_WEIGHTS = {
    "relevant_skill": 30,
    "relevant_experience": 25,
    "domain_knowledge": 20,
    "education_relevance": 10,
    "preferred_certification": 8,
    "job_related_language": 7,
}

PREFERRED_MAX_SECTION_CRITERIA = 4
DUPLICATE_SIMILARITY_THRESHOLD = 0.75
STRICT_NAME_SIMILARITY_THRESHOLD = 0.82
EXPLICIT_LANGUAGE_PATTERN = re.compile(
    r"\b(?:English|Bahasa Malaysia|Bahasa Melayu|Malay|Mandarin|Chinese|"
    r"Japanese|Tamil|Korean)\b",
    re.IGNORECASE,
)
EDUCATION_SOURCE_PATTERN = re.compile(
    r"\b(?:education|academic|diploma|degree|bachelor|master|phd|"
    r"field of study|related field|discipline|academic qualification)\b",
    re.IGNORECASE,
)
EDUCATION_CREDENTIAL_PATTERN = re.compile(
    r"\b(?:diploma|degree|bachelor(?:'s)?|master(?:'s)?|phd|"
    r"academic qualification|professional qualification)\b",
    re.IGNORECASE,
)
EDUCATION_FIELD_LINK_PATTERN = re.compile(
    r"\b(?:diploma|degree|bachelor(?:'s)?|master(?:'s)?|phd|"
    r"academic qualification|professional qualification)\b"
    r".{0,60}?\b(?:in|of)\s+"
    r"(?P<field>[A-Za-z][A-Za-z0-9&/(),.\- ]{2,100})",
    re.IGNORECASE,
)
GENERIC_EDUCATION_FIELD_PATTERN = re.compile(
    r"^(?:an?\s+)?(?:any|related|relevant|appropriate|recognised)?\s*"
    r"(?:field|discipline|subject|qualification|degree)?"
    r"(?:\s+or\s+(?:an?\s+)?related\s+(?:field|discipline))?"
    r"\s*(?:is\s+required|required|preferred)?\s*[.;]?$",
    re.IGNORECASE,
)
EXPERIENCE_EVIDENCE_PATTERN = re.compile(
    r"\b(?:at least\s+\d+(?:\s*[-–]\s*\d+)?\s+years?|"
    r"\d+\+?\s+years?|years?\s+of|past\s+working\s+experience|"
    r"work(?:ing)?\s+experience|experience\s+(?:in|as|with)|"
    r"experienced\s+(?:in|with)|worked\s+(?:in|as|with)|track record)\b",
    re.IGNORECASE,
)
FORMAL_DOMAIN_SUBJECT_PATTERN = re.compile(
    r"\b(?:laws?|legislation|regulations?|codes?|standards?|"
    r"statutory requirements?|compliance frameworks?|"
    r"compliance requirements?|professional principles?|"
    r"formal procedures?|formal business rules?|safety practices?|"
    r"financial controls?|quality systems?|accounting principles?|"
    r"procedures?|methods?|controls?|practices?)\b",
    re.IGNORECASE,
)
FORMAL_DOMAIN_KNOWLEDGE_PATTERN = re.compile(
    r"\b(?:knowledge\s+of|understanding\s+of|familiar(?:ity)?\s+with)"
    r"\b.{0,120}?"
    r"(?:laws?|legislation|regulations?|codes?|standards?|"
    r"statutory requirements?|compliance frameworks?|"
    r"compliance requirements?|professional principles?|"
    r"formal procedures?|formal business rules?|safety practices?|"
    r"financial controls?|quality systems?|accounting principles?|"
    r"procedures?|methods?|controls?|practices?)\b",
    re.IGNORECASE,
)
TOOL_OR_SOFTWARE_PATTERN = re.compile(
    r"\b(?:software|system|platform|application|tool|ERP|HRIS|WMS|"
    r"CAD|AutoCAD|SolidWorks|Excel|spreadsheet|database)\b",
    re.IGNORECASE,
)
PEOPLE_MANAGEMENT_PATTERN = re.compile(
    r"\b(?:staff|team|people|personnel|employee|workforce)\b.{0,60}"
    r"\b(?:manage|management|supervise|supervision|lead|leadership|"
    r"allocate|coach|mentor)\w*\b|"
    r"\b(?:manage|management|supervise|supervision|lead|leadership|"
    r"allocate|coach|mentor)\w*\b.{0,60}"
    r"\b(?:staff|team|people|personnel|employee|workforce)\b",
    re.IGNORECASE,
)
ANALYSIS_PROBLEM_SOLVING_PATTERN = re.compile(
    r"\b(?:analy(?:se|sis|ze)|problem solving|root cause|investigat(?:e|ion)|"
    r"troubleshoot(?:ing)?|optim(?:ise|ize|isation|ization)|"
    r"improv(?:e|ement))\b",
    re.IGNORECASE,
)
REPORTING_DOCUMENTATION_PATTERN = re.compile(
    r"\b(?:report(?:ing)?|document(?:ation)?|record(?:s| keeping)?|"
    r"write|writing|register)\b",
    re.IGNORECASE,
)
SOURCE_GROUNDING_THRESHOLD = 0.68
SOURCE_GROUNDING_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in",
    "of", "on", "or", "the", "to", "with",
}
PREFERRED_CERTIFICATION_PATTERN = re.compile(
    r"\b(?:preferred|desirable|advantage|added advantage)\b",
    re.IGNORECASE,
)
MANDATORY_CERTIFICATION_PATTERN = re.compile(
    r"\b(?:mandatory|required|must|essential|compulsory)\b",
    re.IGNORECASE,
)

DOMAIN_KNOWLEDGE_FALLBACK_INTRO_PATTERN = re.compile(
    r"\b(?:knowledge\s+of|understanding\s+of|familiarity\s+with)\s+"
    r"(?P<subject>.+?)(?:\s+is\s+(?:required|essential|preferred))?[.;]?$",
    re.IGNORECASE,
)
DOMAIN_KNOWLEDGE_FALLBACK_SUBJECT_PATTERN = re.compile(
    r"\b(?:laws?|legislation|regulations?|codes?|standards?|principles?|"
    r"formal\s+procedures?|safety\s+practices?|compliance\s+requirements?|"
    r"financial\s+controls?|statutory\s+requirements?)\b",
    re.IGNORECASE,
)
PREFERRED_CERTIFICATION_FALLBACK_CONTEXT_PATTERN = re.compile(
    r"\b(?P<credential>(?:[A-Za-z0-9&/()\-]+\s+){0,8}"
    r"(?:certification|certificate|licen[cs]e|registration))\b",
    re.IGNORECASE,
)
EXPERIENCE_FALLBACK_CONTEXT_PATTERN = re.compile(
    r"\bexperience\s+(?:in|within|across|including|covering)\s+"
    r"[A-Za-z0-9&/(),\- ]{3,100}|"
    r"\b(?:industrial|manufacturing|regulated|high-volume|multi-site|"
    r"supervisory|leadership)\b"
    r"[A-Za-z0-9&/(),\- ]{0,60}\bexperience\b|"
    r"\bexperience\b[A-Za-z0-9&/(),\- ]{0,60}"
    r"\b(?:team\s+supervision|responsibility\s+scope|production\s+environment|"
    r"manufacturing\s+environment|regulated\s+environment)\b",
    re.IGNORECASE,
)
EXPERIENCE_LEADING_THRESHOLD_PATTERN = re.compile(
    r"^\s*(?:at\s+least\s+)?"
    r"(?:\d+(?:\s*[-–]\s*\d+)?\+?|"
    r"one|two|three|four|five|six|seven|eight|nine|ten)"
    r"\s+years?(?:\s+of)?\s+",
    re.IGNORECASE,
)

DEFAULT_DESCRIPTION_TEMPLATES = {
    "relevant_skill": "Evaluates demonstrated ability in {name}.",
    "relevant_experience": (
        "Evaluates the depth, relevance, and results of the candidate's {name}."
    ),
    "education_relevance": (
        "Evaluates how directly the candidate's education supports {name}."
    ),
    "domain_knowledge": (
        "Evaluates practical understanding and application of {name}."
    ),
    "preferred_certification": (
        "Evaluates the relevance and current validity of {name}."
    ),
    "job_related_language": (
        "Evaluates job-related written or spoken ability in {name}."
    ),
}

DEFAULT_EVIDENCE_RULES = {
    "relevant_skill": (
        "The resume should show this skill in work experience, projects, "
        "achievements, or a skills section."
    ),
    "relevant_experience": (
        "The resume should show relevant roles, responsibility scope, duration, "
        "working environment, and measurable outcomes beyond the minimum."
    ),
    "education_relevance": (
        "The resume should show a directly relevant field of study, coursework, "
        "academic projects, or equivalent job-related learning."
    ),
    "domain_knowledge": (
        "The resume should show practical use of the named process, regulation, "
        "standard, or professional knowledge."
    ),
    "preferred_certification": (
        "The resume should show the certification title, issuer, validity, and "
        "relevance to the work."
    ),
    "job_related_language": (
        "The resume should show explicit language proficiency used in a relevant "
        "work or professional context."
    ),
}

def normalise_identifier(value: str) -> str:
    normalised = re.sub(r"[\s-]+", "_", value.strip().lower())
    return normalised.strip("_")

def normalise_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def comparable_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(
        None, comparable_text(left), comparable_text(right)
    ).ratio()

CAPABILITY_STOPWORDS = {
    "ability", "activities", "activity", "administration", "and",
    "candidate", "capability", "carry", "conduct", "coordinate",
    "coordination", "demonstrated", "ensure", "execution", "experience",
    "handling", "job", "knowledge", "manage", "management", "monitor",
    "of", "operation", "operations", "perform", "process", "processing",
    "professional", "proficiency", "provide", "relevant", "responsible",
    "review", "skill", "skills", "support", "the", "using",
}

WORKFLOW_ACTIVITY_PATTERNS = {
    "quantitative_analysis": re.compile(
        r"\b(?:variance|benchmark(?:ing)?|dashboard|quantitative|"
        r"statistical|profitability|yield|capacity|forecast|"
        r"model(?:ing|ling)?|calculate|calculation)\b|"
        r"\bdata\s+analysis\b|"
        r"\banaly(?:se|ze|sis)(?:\s+\w+){0,2}\s+data\b|"
        r"\btrend\s+analysis\b",
        re.IGNORECASE,
    ),
    "administration": re.compile(
        r"\b(?:maintain|record|reconcile|invoice|enrol(?:ment)?|register|"
        r"update|document(?:ation)?)\b",
        re.IGNORECASE,
    ),
    "lifecycle_review": re.compile(
        r"\b(?:review|verify|verification|validate|validation|prototype|"
        r"change|revision|resolve|test|trial|qualification|commission)\b",
        re.IGNORECASE,
    ),
    "improvement": re.compile(
        r"\b(?:root cause|corrective|preventive|improv(?:e|ement)|"
        r"optim(?:ise|ize|isation|ization)|problem solving|defect|"
        r"nonconform(?:ity|ities)?|instability)\b",
        re.IGNORECASE,
    ),
    "inspection": re.compile(
        r"\b(?:inspect(?:ion)?|measure(?:ment)?|gauge|instrument|drawing|"
        r"tolerance|sampling|first[ -]?piece|sample)\b",
        re.IGNORECASE,
    ),
    "audit": re.compile(
        r"\b(?:audit|compliance|controlled procedure|audit requirement|"
        r"process owner training)\b",
        re.IGNORECASE,
    ),
}

# Workflow objectives connect adjacent operational steps even when their wording
# has little lexical overlap. Matching is based on criterion evidence only;
# job title and department are intentionally not used.
WORKFLOW_OBJECTIVE_PATTERNS = {
    "candidate_acquisition": re.compile(
        r"\b(?:recruit(?:ment|ing)|job\s+post(?:ing)?|candidate(?:s)?|"
        r"pre[ -]?screen(?:ing)?|screen(?:ing)?|shortlist(?:ing)?|"
        r"interview(?:ing)?)\b",
        re.IGNORECASE,
    ),
}
WORKFLOW_STEP_ACTION_PATTERN = re.compile(
    r"\b(?:assist|handle|manage|post|source|pre[ -]?screen|screen|"
    r"shortlist|arrange|schedule|coordinate|conduct)\w*\b",
    re.IGNORECASE,
)
WORKFLOW_SUPPORTING_CAPABILITY_PATTERN = re.compile(
    r"\b(?:proficien(?:t|cy)|familiar(?:ity)?|tool|platform|software|"
    r"system)\b",
    re.IGNORECASE,
)

def capability_tokens(value: str) -> set[str]:
    tokens = comparable_text(value).split()
    return {
        token[:-1] if len(token) > 4 and token.endswith("s") else token
        for token in tokens
        if len(token) > 2 and token not in CAPABILITY_STOPWORDS
    }

def token_overlap_score(left: str, right: str) -> tuple[float, int]:
    left_tokens = capability_tokens(left)
    right_tokens = capability_tokens(right)
    shared_count = len(left_tokens & right_tokens)
    if not left_tokens or not right_tokens:
        return 0.0, shared_count
    return (
        shared_count / min(len(left_tokens), len(right_tokens)),
        shared_count,
    )

def workflow_activity_families(item: dict[str, str]) -> set[str]:
    combined = item["name"] + " " + item["sourceText"]
    return {
        family
        for family, pattern in WORKFLOW_ACTIVITY_PATTERNS.items()
        if pattern.search(combined)
    }

def workflow_objective_families(
    item: dict[str, str],
) -> set[str]:
    combined = item["name"] + " " + item["sourceText"]
    return {
        family
        for family, pattern in WORKFLOW_OBJECTIVE_PATTERNS.items()
        if pattern.search(combined)
    }

def is_operational_workflow_step(item: dict[str, str]) -> bool:
    combined = item["name"] + " " + item["sourceText"]
    return bool(WORKFLOW_STEP_ACTION_PATTERN.search(combined))

def is_supporting_workflow_capability(item: dict[str, str]) -> bool:
    combined = item["name"] + " " + item["sourceText"]
    return bool(WORKFLOW_SUPPORTING_CAPABILITY_PATTERN.search(combined))

def fallback_criteria_match(
    left: dict[str, str],
    right: dict[str, str],
) -> bool:
    if left["type"] != right["type"]:
        return False
    if (
        normalise_text(left["sourceText"]).casefold()
        == normalise_text(right["sourceText"]).casefold()
    ):
        return True
    shared_workflow_objectives = (
        workflow_objective_families(left)
        & workflow_objective_families(right)
    )
    if shared_workflow_objectives and (
        (
            is_operational_workflow_step(left)
            and not is_supporting_workflow_capability(left)
            and is_supporting_workflow_capability(right)
        )
        or (
            is_operational_workflow_step(right)
            and not is_supporting_workflow_capability(right)
            and is_supporting_workflow_capability(left)
        )
    ):
        return False
    if (
        text_similarity(left["name"], right["name"])
        >= DUPLICATE_SIMILARITY_THRESHOLD
    ):
        return True
    name_overlap, shared_name_tokens = token_overlap_score(
        left["name"],
        right["name"],
    )
    if shared_name_tokens >= 1 and name_overlap >= 0.5:
        return True
    evidence_overlap, shared_evidence_tokens = token_overlap_score(
        left["sourceText"],
        right["sourceText"],
    )
    if shared_evidence_tokens >= 2 and evidence_overlap >= 0.6:
        return True
    combined_overlap, shared_combined_tokens = token_overlap_score(
        left["name"] + " " + left["sourceText"],
        right["name"] + " " + right["sourceText"],
    )
    if shared_combined_tokens >= 2 and combined_overlap >= 0.45:
        return True
    if (
        shared_workflow_objectives
        and is_operational_workflow_step(left)
        and is_operational_workflow_step(right)
        and not is_supporting_workflow_capability(left)
        and not is_supporting_workflow_capability(right)
    ):
        return True
    left_activity_families = workflow_activity_families(left)
    right_activity_families = workflow_activity_families(right)
    shared_activity_families = (
        left_activity_families & right_activity_families
    )
    if (
        shared_activity_families == {"improvement"}
        and ("quantitative_analysis" in left_activity_families)
        != ("quantitative_analysis" in right_activity_families)
    ):
        return False
    return bool(shared_activity_families) and (
        shared_combined_tokens >= 1
        or text_similarity(left["name"], right["name"]) >= 0.4
    )

def grounding_tokens(value: str) -> set[str]:
    tokens = comparable_text(value).split()
    return {
        token[:-1] if len(token) > 4 and token.endswith("s") else token
        for token in tokens
        if token not in SOURCE_GROUNDING_STOPWORDS
    }

def source_grounding_score(candidate: str, source: str) -> float:
    candidate_text = comparable_text(candidate)
    source_text = comparable_text(source)
    if not candidate_text or not source_text:
        return 0.0
    if candidate_text == source_text:
        return 1.0
    candidate_tokens = grounding_tokens(candidate)
    source_tokens = grounding_tokens(source)
    shared = candidate_tokens & source_tokens
    if len(shared) < 2:
        return 0.0
    shorter_size = min(len(candidate_tokens), len(source_tokens))
    token_coverage = len(shared) / max(shorter_size, 1)
    sequence_score = SequenceMatcher(None, candidate_text, source_text).ratio()
    if candidate_text in source_text or source_text in candidate_text:
        return min(0.99, max(0.9, token_coverage))
    return (0.7 * token_coverage) + (0.3 * sequence_score)

def find_grounded_source(
    candidate: str,
    allowed_source_texts: list[str],
) -> tuple[str | None, float]:
    cleaned_sources = [normalise_text(source) for source in allowed_source_texts]
    exact_lookup = {source.casefold(): source for source in cleaned_sources}
    exact = exact_lookup.get(normalise_text(candidate).casefold())
    if exact is not None:
        return exact, 1.0
    scored = [
        (source_grounding_score(candidate, source), source)
        for source in cleaned_sources
    ]
    if not scored:
        return None, 0.0
    score, source = max(scored, key=lambda item: item[0])
    if score < SOURCE_GROUNDING_THRESHOLD:
        return None, score
    return source, score

def is_generic_duty(text: str) -> bool:
    normalised = normalise_text(text).strip(" .;:")
    return any(pattern.fullmatch(normalised) for pattern in GENERIC_DUTY_PATTERNS)

def has_explicit_education_field(text: str) -> bool:
    cleaned = normalise_text(text)
    if not EDUCATION_CREDENTIAL_PATTERN.search(cleaned):
        return False
    match = EDUCATION_FIELD_LINK_PATTERN.search(cleaned)
    if match is None:
        return False
    field = match.group("field").strip()
    field = re.split(
        r"\b(?:is|are|was|were|will|with|and\s+at\s+least)\b",
        field,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.;")
    return bool(field) and not GENERIC_EDUCATION_FIELD_PATTERN.fullmatch(
        field
    )

def filter_generic_duties(
    texts: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    kept: list[str] = []
    ignored: list[dict[str, str]] = []
    for text in texts:
        cleaned = normalise_text(text)
        if not cleaned:
            continue
        if is_generic_duty(cleaned):
            ignored.append(
                {"sourceText": cleaned, "reason": GENERIC_DUTY_REASON}
            )
        else:
            kept.append(cleaned)
    return kept, ignored

def extract_json_object(
    raw_text: str,
) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = normalise_text(raw_text)
    if not cleaned:
        return None, "No JSON object found."
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"Malformed JSON: {exc.msg}"
    if not isinstance(payload, dict):
        return None, "Top-level model output is not an object."
    return payload, None

def section_output_retry_reason(raw_text: str) -> str | None:
    payload, parse_error = extract_json_object(raw_text)
    if parse_error:
        return parse_error
    if not isinstance(payload.get("criteria"), list):
        return "criteria is not a list."
    return None

def weights_are_valid(criteria: list[dict[str, Any]]) -> bool:
    if not criteria:
        return False
    weights = [item.get("suggestedWeight") for item in criteria]
    return (
        all(isinstance(weight, (int, float)) for weight in weights)
        and all(0 <= float(weight) <= 100 for weight in weights)
        and abs(sum(float(weight) for weight in weights) - 100) < 0.001
    )

def merge_metadata_values(
    items: list[dict[str, Any]],
    key: str,
) -> list[Any]:
    values: list[Any] = []
    for item in items:
        raw_values = item.get(key, [])
        if not isinstance(raw_values, list):
            raw_values = [raw_values]
        for value in raw_values:
            if value not in values:
                values.append(value)
    return values


def criterion_name_unsupported_tokens(
    name: str,
    source_text: str,
) -> list[str]:
    def token_variants(token: str) -> set[str]:
        variants = {token}
        if len(token) > 6 and token.endswith("ing"):
            variants.add(token[:-3])
        if len(token) > 6 and token.startswith("pre"):
            without_prefix = token[3:]
            variants.add(without_prefix)
            if len(without_prefix) > 6 and without_prefix.endswith("ing"):
                variants.add(without_prefix[:-3])
        return variants

    name_tokens = capability_tokens(name)
    source_tokens = capability_tokens(source_text)
    generic_name_tokens = {
        "academic", "education", "field", "relevance", "technical",
        "work", "working", "candidate", "quality", "professional",
        "tool", "statutory",
    }
    unsupported: list[str] = []
    for token in name_tokens - generic_name_tokens:
        name_variants = token_variants(token)
        supported = any(
            bool(name_variants & token_variants(source_token))
            or (
                min(len(token), len(source_token)) >= 5
                and (
                    token.startswith(source_token)
                    or source_token.startswith(token)
                )
            )
            for source_token in source_tokens
        )
        if not supported:
            unsupported.append(token)
    return sorted(unsupported)


def normalise_education_criterion_name(
    name: str,
    source_text: str,
) -> tuple[str, bool]:
    contains_experience = bool(
        re.search(r"\bexperience\b", name, re.IGNORECASE)
    )
    unsupported = criterion_name_unsupported_tokens(name, source_text)
    if contains_experience or unsupported:
        return "Relevant Education Field", True
    return name, False


def merge_duplicate_criteria(
    criteria: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for candidate in criteria:
        duplicate = next(
            (
                existing
                for existing in merged
                if existing["type"] == candidate["type"]
                and text_similarity(existing["name"], candidate["name"])
                >= DUPLICATE_SIMILARITY_THRESHOLD
                and not criterion_name_unsupported_tokens(
                    existing["name"],
                    existing["sourceText"] + " | " + candidate["sourceText"],
                )
            ),
            None,
        )
        if duplicate is None:
            merged.append(candidate.copy())
            continue
        sources = (
            duplicate["sourceText"].split(" | ")
            + candidate["sourceText"].split(" | ")
        )
        duplicate["sourceText"] = " | ".join(dict.fromkeys(sources))
        for metadata_key in (
            "sourceIds",
            "sourceCriterionIds",
            "groundingScores",
        ):
            duplicate[metadata_key] = merge_metadata_values(
                [duplicate, candidate],
                metadata_key,
            )
    return merged

def assign_default_weights(criteria: list[dict[str, Any]]) -> None:
    if not criteria:
        return
    type_counts = {
        type_id: sum(item["type"] == type_id for item in criteria)
        for type_id in ALLOWED_SOFT_CRITERIA_TYPES
    }
    scores = [
        DEFAULT_TYPE_WEIGHTS[item["type"]] / type_counts[item["type"]]
        for item in criteria
    ]
    total = sum(scores)
    exact = [score * 100 / total for score in scores]
    rounded = [int(value) for value in exact]
    remainder = 100 - sum(rounded)
    order = sorted(
        range(len(exact)),
        key=lambda index: exact[index] - rounded[index],
        reverse=True,
    )
    for index in order[:remainder]:
        rounded[index] += 1
    for item, weight in zip(criteria, rounded):
        item["suggestedWeight"] = weight

def validate_section_output(
    raw_text: str,
    allowed_source_texts: list[str],
    source_id_prefix: str = "source",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload, parse_error = extract_json_object(raw_text)
    fatal_errors: list[str] = []
    warnings: list[str] = []
    normalisations: list[str] = []
    grounding_matches: list[dict[str, Any]] = []
    grounding_check_count = 0
    grounding_exact_match_count = 0
    grounding_fuzzy_match_count = 0
    grounding_normalised_count = 0
    grounding_failure_count = 0
    grounding_rejected_criterion_count = 0
    if parse_error:
        fatal_errors.append(parse_error)
        payload = {"criteria": []}

    raw_criteria = payload.get("criteria", [])
    if not isinstance(raw_criteria, list):
        fatal_errors.append("criteria is not a list.")
        raw_criteria = []
    if len(raw_criteria) > PREFERRED_MAX_SECTION_CRITERIA:
        warnings.append(
            "Section returned more than "
            f"{PREFERRED_MAX_SECTION_CRITERIA} criteria; all were preserved "
            "for job-level deduplication and consolidation."
        )

    criteria: list[dict[str, str]] = []
    unknown_types: list[str] = []
    for index, raw_item in enumerate(raw_criteria):
        if not isinstance(raw_item, dict):
            warnings.append(f"Criterion {index + 1} is not an object and was rejected.")
            continue
        unexpected_fields = set(raw_item) - {"type", "name", "sourceText"}
        if unexpected_fields:
            warnings.append(
                f"Criterion {index + 1} contains unexpected fields: "
                + ", ".join(sorted(unexpected_fields))
                + "; they were ignored."
            )
        raw_type = normalise_text(raw_item.get("type"))
        criterion_type = normalise_identifier(raw_type)
        if criterion_type not in ALLOWED_SOFT_CRITERIA_TYPES:
            unknown_types.append(raw_type)
            warnings.append(f"Criterion {index + 1} has an unknown type and was rejected.")
            continue
        name = normalise_text(raw_item.get("name"))
        raw_source_text = normalise_text(raw_item.get("sourceText"))
        if not name or not raw_source_text:
            warnings.append(
                f"Criterion {index + 1} is missing name or sourceText and was rejected."
            )
            continue
        grounding_check_count += 1
        source_text, grounding_score = find_grounded_source(
            raw_source_text,
            allowed_source_texts,
        )
        if source_text is None:
            grounding_failure_count += 1
            grounding_rejected_criterion_count += 1
            warnings.append(
                f"Criterion {index + 1} sourceText cannot be grounded and was rejected."
            )
            continue
        grounding_matches.append(
            {
                "criterionIndex": index + 1,
                "rawSourceText": raw_source_text,
                "groundedSourceText": source_text,
                "score": round(grounding_score, 4),
            }
        )
        is_exact_grounding = (
            normalise_text(raw_source_text)
            == normalise_text(source_text)
        )
        if is_exact_grounding:
            grounding_exact_match_count += 1
        else:
            grounding_fuzzy_match_count += 1
        if normalise_text(raw_source_text) != normalise_text(source_text):
            grounding_normalised_count += 1
        if grounding_score < 1.0:
            message = f"Criterion {index + 1} sourceText grounded to the closest JD sentence."
            normalisations.append(message)
            warnings.append(message)
        if criterion_type == "relevant_skill" and (
            EDUCATION_SOURCE_PATTERN.search(name)
            or EDUCATION_SOURCE_PATTERN.search(source_text)
        ):
            criterion_type = "education_relevance"
            message = f"Criterion {index + 1} remapped from relevant_skill to education_relevance."
            normalisations.append(message)
            warnings.append(message)
        elif criterion_type == "relevant_skill" and (
            EXPERIENCE_EVIDENCE_PATTERN.search(name)
            or EXPERIENCE_EVIDENCE_PATTERN.search(source_text)
        ):
            criterion_type = "relevant_experience"
            message = f"Criterion {index + 1} remapped from relevant_skill to relevant_experience."
            normalisations.append(message)
            warnings.append(message)
        elif (
            criterion_type == "relevant_skill"
            and FORMAL_DOMAIN_KNOWLEDGE_PATTERN.search(source_text)
        ):
            criterion_type = "domain_knowledge"
            message = f"Criterion {index + 1} remapped from relevant_skill to domain_knowledge."
            normalisations.append(message)
            warnings.append(message)
        elif (
            criterion_type == "domain_knowledge"
            and not FORMAL_DOMAIN_KNOWLEDGE_PATTERN.search(source_text)
        ):
            criterion_type = "relevant_skill"
            message = (
                f"Criterion {index + 1} remapped from domain_knowledge "
                "to relevant_skill because its evidence describes practical "
                "work or tool proficiency rather than formal knowledge."
            )
            normalisations.append(message)
            warnings.append(message)
        if criterion_type == "relevant_experience" and re.search(
            r"^\s*minimum\s+", name, re.IGNORECASE
        ):
            name = re.sub(
                r"^\s*minimum\s+",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()
            message = f"Criterion {index + 1} removed minimum from the experience criterion name."
            normalisations.append(message)
            warnings.append(message)
        if re.search(r"\bminimum\b", name, re.IGNORECASE):
            warnings.append(
                f"Criterion {index + 1} uses minimum in a non-experience name and was rejected."
            )
            continue
        if criterion_type == "education_relevance":
            name, education_name_corrected = (
                normalise_education_criterion_name(name, source_text)
            )
            if education_name_corrected:
                message = (
                    f"Criterion {index + 1} education name was restricted "
                    "to education-field relevance."
                )
                normalisations.append(message)
                warnings.append(message)
        if (
            criterion_type == "education_relevance"
            and not has_explicit_education_field(source_text)
        ):
            warnings.append(
                f"Criterion {index + 1} contains only an education level "
                "without a specific field of study and was rejected."
            )
            continue
        if (
            criterion_type == "job_related_language"
            and not EXPLICIT_LANGUAGE_PATTERN.search(source_text)
        ):
            warnings.append(
                f"Criterion {index + 1} has no explicit language and was rejected."
            )
            continue
        if criterion_type == "preferred_certification" and (
            MANDATORY_CERTIFICATION_PATTERN.search(source_text)
            or not PREFERRED_CERTIFICATION_PATTERN.search(source_text)
        ):
            warnings.append(
                f"Criterion {index + 1} is not an explicitly preferred certification and was rejected."
            )
            continue
        unsupported_name_tokens = criterion_name_unsupported_tokens(
            name,
            source_text,
        )
        if unsupported_name_tokens:
            warnings.append(
                f"Criterion {index + 1} name introduces unsupported "
                "concepts and was rejected: "
                + ", ".join(unsupported_name_tokens)
            )
            continue
        source_position = next(
            (
                source_index
                for source_index, allowed_source in enumerate(
                    allowed_source_texts,
                    start=1,
                )
                if normalise_text(allowed_source).casefold()
                == source_text.casefold()
            ),
            index + 1,
        )
        criteria.append(
            {
                "type": criterion_type,
                "name": name,
                "sourceText": source_text,
                "sourceIds": [f"{source_id_prefix}-{source_position}"],
                "sourceCriterionIds": [
                    f"{source_id_prefix}-criterion-{index + 1}"
                ],
                "groundingScores": [round(grounding_score, 4)],
            }
        )

    if raw_criteria and not criteria and not fatal_errors:
        fatal_errors.append(
            "The non-empty criteria list was completely rejected; no valid criterion remains."
        )
    issues = fatal_errors + warnings
    diagnostics = {
        "invalidOutput": bool(fatal_errors),
        "fatalErrors": fatal_errors,
        "warnings": warnings,
        "issues": issues,
        "normalisations": normalisations,
        "groundingMatches": grounding_matches,
        "sourceTextGroundingCheckCount": grounding_check_count,
        "sourceTextGroundingExactMatchCount": grounding_exact_match_count,
        "sourceTextGroundingFuzzyMatchCount": grounding_fuzzy_match_count,
        "sourceTextGroundingNormalisedCount": grounding_normalised_count,
        "sourceTextGroundingFailureCount": grounding_failure_count,
        "sourceTextGroundingRejectedCriterionCount": (
            grounding_rejected_criterion_count
        ),
        "sourceTextGroundingFailureRate": (
            grounding_failure_count / grounding_check_count
            if grounding_check_count
            else 0.0
        ),
        "unknownTypes": unknown_types,
        "rawModelOutput": raw_text,
    }
    return criteria, diagnostics

def add_education_fallback(
    criteria: list[dict[str, str]],
    requirement_texts: list[str],
) -> None:
    has_education = any(
        item["type"] == "education_relevance" for item in criteria
    )
    if has_education:
        return
    for source_index, text in enumerate(requirement_texts, start=1):
        cleaned = normalise_text(text)
        if has_explicit_education_field(cleaned):
            criteria.append(
                {
                    "type": "education_relevance",
                    "name": "Relevant Education Field",
                    "sourceText": cleaned,
                    "sourceIds": [f"requirements-{source_index}"],
                    "sourceCriterionIds": [
                        f"requirements-education-fallback-{source_index}"
                    ],
                    "groundingScores": [1.0],
                }
            )
            break


def fallback_display_name(value: str) -> str:
    cleaned = normalise_text(value)
    cleaned = re.sub(
        r"\s+is\s+(?:required|essential|preferred|desirable)\s*[.;]?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(?:is\s+)?(?:an?\s+)?(?:added\s+)?advantage\s*[.;]?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip(" .;,")
    small_words = {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with"}
    words = cleaned.split()
    return " ".join(
        word.lower()
        if index and word.casefold() in small_words
        else word[:1].upper() + word[1:]
        for index, word in enumerate(words)
    )


def add_domain_knowledge_fallback(
    criteria: list[dict[str, str]],
    requirement_texts: list[str],
) -> list[dict[str, Any]]:
    if any(item["type"] == "domain_knowledge" for item in criteria):
        return []
    for source_index, text in enumerate(requirement_texts, start=1):
        source_text = normalise_text(text)
        intro_match = DOMAIN_KNOWLEDGE_FALLBACK_INTRO_PATTERN.search(source_text)
        if not intro_match:
            continue
        subject = intro_match.group("subject")
        if not DOMAIN_KNOWLEDGE_FALLBACK_SUBJECT_PATTERN.search(subject):
            continue
        grounded_source, grounding_score = find_grounded_source(
            source_text,
            requirement_texts,
        )
        if grounded_source is None:
            continue
        criterion = {
            "type": "domain_knowledge",
            "name": fallback_display_name(subject),
            "sourceText": grounded_source,
            "sourceIds": [f"requirements-{source_index}"],
            "sourceCriterionIds": [
                f"requirements-domain-fallback-{source_index}"
            ],
            "groundingScores": [round(grounding_score, 4)],
        }
        criteria.append(criterion)
        return [
            {
                "module": "domain_knowledge_fallback",
                "sourceId": f"requirement-{source_index}",
                "groundingScore": grounding_score,
                **criterion,
            }
        ]
    return []


def add_preferred_certification_fallback(
    criteria: list[dict[str, str]],
    requirement_texts: list[str],
) -> list[dict[str, Any]]:
    if any(item["type"] == "preferred_certification" for item in criteria):
        return []
    for source_index, text in enumerate(requirement_texts, start=1):
        source_text = normalise_text(text)
        if (
            not PREFERRED_CERTIFICATION_PATTERN.search(source_text)
            or MANDATORY_CERTIFICATION_PATTERN.search(source_text)
        ):
            continue
        credential_match = (
            PREFERRED_CERTIFICATION_FALLBACK_CONTEXT_PATTERN.search(source_text)
        )
        if not credential_match:
            continue
        credential = re.sub(
            r"^(?:an?|the)\s+",
            "",
            credential_match.group("credential"),
            flags=re.IGNORECASE,
        )
        grounded_source, grounding_score = find_grounded_source(
            source_text,
            requirement_texts,
        )
        if grounded_source is None:
            continue
        criterion = {
            "type": "preferred_certification",
            "name": fallback_display_name(credential),
            "sourceText": grounded_source,
            "sourceIds": [f"requirements-{source_index}"],
            "sourceCriterionIds": [
                f"requirements-certification-fallback-{source_index}"
            ],
            "groundingScores": [round(grounding_score, 4)],
        }
        criteria.append(criterion)
        return [
            {
                "module": "preferred_certification_fallback",
                "sourceId": f"requirement-{source_index}",
                "groundingScore": grounding_score,
                **criterion,
            }
        ]
    return []


def add_contextual_relevant_experience_fallback(
    criteria: list[dict[str, str]],
    requirement_texts: list[str],
) -> list[dict[str, Any]]:
    if any(item["type"] == "relevant_experience" for item in criteria):
        return []
    for source_index, text in enumerate(requirement_texts, start=1):
        source_text = normalise_text(text)
        if (
            not EXPERIENCE_EVIDENCE_PATTERN.search(source_text)
            or not EXPERIENCE_FALLBACK_CONTEXT_PATTERN.search(source_text)
        ):
            continue
        grounded_source, grounding_score = find_grounded_source(
            source_text,
            requirement_texts,
        )
        if grounded_source is None:
            continue
        experience_name = EXPERIENCE_LEADING_THRESHOLD_PATTERN.sub(
            "",
            source_text,
        )
        experience_name = re.sub(
            r"\s+is\s+(?:required|essential)\s*[.;]?$",
            "",
            experience_name,
            flags=re.IGNORECASE,
        )
        criterion = {
            "type": "relevant_experience",
            "name": fallback_display_name(experience_name),
            "sourceText": grounded_source,
            "sourceIds": [f"requirements-{source_index}"],
            "sourceCriterionIds": [
                f"requirements-experience-fallback-{source_index}"
            ],
            "groundingScores": [round(grounding_score, 4)],
        }
        criteria.append(criterion)
        return [
            {
                "module": "relevant_experience_fallback",
                "sourceId": f"requirement-{source_index}",
                "groundingScore": grounding_score,
                **criterion,
            }
        ]
    return []

CONSOLIDATION_SYSTEM_PROMPT = """You consolidate already validated job-scoring criteria into a complete job-level set.

The six criterion types are fixed and cannot be changed.

Return a complete partition of all supplied criteria. Every input criterion ID must appear exactly once.
Include a one-member group for every criterion that should not be merged.

First process criteria within one criteriaByType key at a time.
A group may contain memberIds from exactly one criteriaByType key, and its type must exactly match that key.
Never combine memberIds from different criteriaByType keys, even when the total result remains above six groups.

Merge criteria only when they have the same type and evaluate the same overall candidate capability.
Judge this from the complete set of names and sourceText, not from one keyword.
Merge adjacent workflow steps only when they remain one independently scorable capability.
Keep capabilities separate when the resume would need materially different evidence to score them.
Do not merge people management with tool or system proficiency.
Do not merge analysis or problem solving with report writing or documentation unless the supplied evidence explicitly describes one combined capability.
Do not merge distinct tools, systems, professional functions or knowledge areas.

Do not merge criteria across different types.
Do not remove supported criteria or source evidence.
Do not create a new job function, tool, technology, industry, process or requirement.

Create each consolidated name only from the supplied criterion names and sourceText.
Keep names concise, professional, and broad enough to describe every member of the group.

A group may contain several responsibility steps only when they test the same independently scorable capability.
The six configured items are criterion types, not a maximum number of final criteria.
Never merge criteria to reach a target count. Preserve every distinct capability as a one-member group.

Before returning, verify that the memberIds across all groups exactly equal the supplied input IDs.

Return JSON only.
"""

CONSOLIDATION_OUTPUT_SHAPE = {
    "groups": [
        {
            "type": "allowed_type_id",
            "name": "Consolidated HR-facing criterion name",
            "memberIds": ["c1", "c2"],
        }
    ]
}

def assign_stable_criterion_ids(
    criteria: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        {"id": f"c{index}", **item}
        for index, item in enumerate(criteria, start=1)
    ]

def has_people_tool_boundary(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_text = left["name"] + " " + left["sourceText"]
    right_text = right["name"] + " " + right["sourceText"]
    return (
        bool(PEOPLE_MANAGEMENT_PATTERN.search(left_text))
        != bool(PEOPLE_MANAGEMENT_PATTERN.search(right_text))
        and bool(TOOL_OR_SOFTWARE_PATTERN.search(left_text))
        != bool(TOOL_OR_SOFTWARE_PATTERN.search(right_text))
    )


def has_analysis_documentation_boundary(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    left_text = left["name"] + " " + left["sourceText"]
    right_text = right["name"] + " " + right["sourceText"]
    left_analysis = bool(ANALYSIS_PROBLEM_SOLVING_PATTERN.search(left_text))
    right_analysis = bool(ANALYSIS_PROBLEM_SOLVING_PATTERN.search(right_text))
    left_docs = bool(REPORTING_DOCUMENTATION_PATTERN.search(left_text))
    right_docs = bool(REPORTING_DOCUMENTATION_PATTERN.search(right_text))
    return (left_analysis and right_docs and not right_analysis) or (
        right_analysis and left_docs and not left_analysis
    )


def same_independently_scorable_capability(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    if left["type"] != right["type"]:
        return False
    if has_people_tool_boundary(left, right):
        return False
    if has_analysis_documentation_boundary(left, right):
        return False
    if (
        normalise_text(left["sourceText"]).casefold()
        == normalise_text(right["sourceText"]).casefold()
    ):
        return True
    if (
        text_similarity(left["name"], right["name"])
        >= STRICT_NAME_SIMILARITY_THRESHOLD
    ):
        return True
    shared_workflow_objectives = (
        workflow_objective_families(left)
        & workflow_objective_families(right)
    )
    if (
        shared_workflow_objectives
        and is_operational_workflow_step(left)
        and is_operational_workflow_step(right)
        and not is_supporting_workflow_capability(left)
        and not is_supporting_workflow_capability(right)
    ):
        return True
    name_overlap, shared_name_tokens = token_overlap_score(
        left["name"],
        right["name"],
    )
    return shared_name_tokens >= 2 and name_overlap >= 0.75


def can_merge_criteria_group(
    members: list[dict[str, Any]],
) -> bool:
    if len(members) <= 1:
        return True
    if len({item["type"] for item in members}) != 1:
        return False
    shared_workflow_objectives = set.intersection(
        *(workflow_objective_families(item) for item in members)
    )
    if shared_workflow_objectives and all(
        is_operational_workflow_step(item)
        and not is_supporting_workflow_capability(item)
        for item in members
    ):
        return True
    return all(
        same_independently_scorable_capability(left, right)
        for left_index, left in enumerate(members)
        for right in members[left_index + 1 :]
    )


def needs_job_consolidation(criteria: list[dict[str, Any]]) -> bool:
    return any(
        same_independently_scorable_capability(left, right)
        for left_index, left in enumerate(criteria)
        for right in criteria[left_index + 1 :]
    )


def validate_final_criteria_count(
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    type_counts = {
        type_id: sum(item["type"] == type_id for item in criteria)
        for type_id in ALLOWED_SOFT_CRITERIA_TYPES
    }
    return {
        "valid": True,
        "limitEnabled": False,
        "totalCount": len(criteria),
        "typeCounts": type_counts,
        "note": (
            "The six configured items are criterion types, not a final "
            "criterion-count limit."
        ),
    }

def build_consolidation_payload(
    criteria_with_ids: list[dict[str, str]],
) -> dict[str, dict[str, list[dict[str, str]]]]:
    criteria_by_type: dict[str, list[dict[str, str]]] = {}
    for type_id in sorted(ALLOWED_SOFT_CRITERIA_TYPES):
        type_items = [
            {
                "id": item["id"],
                "name": item["name"],
                "sourceText": item["sourceText"],
            }
            for item in criteria_with_ids
            if item["type"] == type_id
        ]
        if type_items:
            criteria_by_type[type_id] = type_items
    return {"criteriaByType": criteria_by_type}

def build_consolidation_messages(
    criteria_with_ids: list[dict[str, str]],
) -> list[dict[str, str]]:
    payload = build_consolidation_payload(criteria_with_ids)
    user_prompt = (
        "Validated criteria to consolidate. Each criteriaByType key is a strict grouping boundary:\n"
        + json.dumps(payload, indent=2)
        + "\n\nRequired JSON structure:\n"
        + json.dumps(CONSOLIDATION_OUTPUT_SHAPE, indent=2)
        + "\n\nReturn JSON only."
    )
    return [
        {"role": "system", "content": CONSOLIDATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

def validate_consolidation_output(
    raw_text: str,
    criteria_with_ids: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    payload, parse_error = extract_json_object(raw_text)
    errors: list[str] = []
    warnings: list[str] = []
    parsed_groups: list[dict[str, Any]] = []
    failure_categories: list[str] = []
    def record_failure_category(category: str) -> None:
        if category not in failure_categories:
            failure_categories.append(category)
    diagnostics = {
        "consolidationParseError": parse_error,
        "consolidationValidationErrors": errors,
        "consolidationWarnings": warnings,
        "parsedConsolidationGroups": parsed_groups,
        "consolidationFailureCategories": failure_categories,
    }
    if parse_error:
        record_failure_category("parse_failure")
        return [], diagnostics
    top_level_extras = set(payload) - {"groups"}
    if top_level_extras:
        warnings.append(
            "Ignored extra top-level fields: "
            + ", ".join(sorted(top_level_extras))
        )
    groups = payload.get("groups")
    if not isinstance(groups, list):
        record_failure_category("missing_id")
        errors.append("groups is not a list.")
        return [], diagnostics
    input_by_id = {
        normalise_text(item["id"]).lower(): item for item in criteria_with_ids
    }
    seen_ids: set[str] = set()
    consolidated: list[dict[str, str]] = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"Group {index + 1} is not an object.")
            continue
        extra_fields = set(group) - {"type", "name", "memberIds"}
        if extra_fields:
            warnings.append(
                f"Group {index + 1} ignored extra fields: "
                + ", ".join(sorted(extra_fields))
            )
        group_type = normalise_identifier(normalise_text(group.get("type")))
        name = normalise_text(group.get("name"))
        raw_member_ids = group.get("memberIds")
        if group_type not in ALLOWED_SOFT_CRITERIA_TYPES:
            errors.append(f"Group {index + 1} has an unknown type.")
            continue
        if not name:
            errors.append(f"Group {index + 1} has no name.")
            continue
        if not isinstance(raw_member_ids, list) or not raw_member_ids:
            errors.append(f"Group {index + 1} has empty or invalid memberIds.")
            continue
        member_ids = [
            normalise_text(member_id).lower() for member_id in raw_member_ids
        ]
        if any(not member_id for member_id in member_ids):
            errors.append(f"Group {index + 1} contains an empty member ID.")
            continue
        parsed_groups.append(
            {
                "type": group_type,
                "name": name,
                "memberIds": member_ids,
            }
        )
        if len(member_ids) != len(set(member_ids)):
            record_failure_category("duplicate_id")
            errors.append(f"Group {index + 1} contains duplicate member IDs.")
            continue
        unknown_ids = [member_id for member_id in member_ids if member_id not in input_by_id]
        if unknown_ids:
            record_failure_category("unknown_id")
            errors.append(
                f"Group {index + 1} contains unknown member IDs: "
                + ", ".join(unknown_ids)
            )
            continue
        repeated_ids = [member_id for member_id in member_ids if member_id in seen_ids]
        if repeated_ids:
            record_failure_category("duplicate_id")
            errors.append(
                "Member IDs appear in more than one group: "
                + ", ".join(repeated_ids)
            )
            continue
        members = [input_by_id[member_id] for member_id in member_ids]
        member_types = {item["type"] for item in members}
        if len(member_types) != 1 or group_type not in member_types:
            record_failure_category("mixed_type")
            errors.append(f"Group {index + 1} merges different criterion types.")
            continue
        if not can_merge_criteria_group(members):
            record_failure_category("overbroad_capability")
            errors.append(
                f"Group {index + 1} combines independently scorable "
                "capabilities."
            )
            continue
        sources = [item["sourceText"] for item in members]
        final_name = members[0]["name"] if len(members) == 1 else name
        merged_source_text = " | ".join(dict.fromkeys(sources))
        unsupported_name_tokens = criterion_name_unsupported_tokens(
            final_name,
            merged_source_text,
        )
        if unsupported_name_tokens:
            record_failure_category("unsupported_name")
            errors.append(
                f"Group {index + 1} name introduces unsupported concepts: "
                + ", ".join(unsupported_name_tokens)
            )
            continue
        seen_ids.update(member_ids)
        consolidated.append(
            {
                "type": group_type,
                "name": final_name,
                "sourceText": merged_source_text,
                "sourceIds": merge_metadata_values(members, "sourceIds"),
                "sourceCriterionIds": merge_metadata_values(
                    members,
                    "sourceCriterionIds",
                ),
                "groundingScores": merge_metadata_values(
                    members,
                    "groundingScores",
                ),
                "mergedFromIds": member_ids,
            }
        )
    missing_ids = sorted(set(input_by_id) - seen_ids)
    if missing_ids and not errors:
        for member_id in missing_ids:
            member = input_by_id[member_id]
            singleton_group = {
                "type": member["type"],
                "name": member["name"],
                "memberIds": [member_id],
            }
            parsed_groups.append(singleton_group)
            consolidated.append(
                {
                    "type": member["type"],
                    "name": member["name"],
                    "sourceText": member["sourceText"],
                    "sourceIds": list(member.get("sourceIds", [])),
                    "sourceCriterionIds": list(
                        member.get("sourceCriterionIds", [])
                    ),
                    "groundingScores": list(
                        member.get("groundingScores", [])
                    ),
                    "mergedFromIds": [member_id],
                }
            )
            seen_ids.add(member_id)
        warnings.append(
            "Restored omitted input criterion IDs as unchanged singleton "
            "groups: " + ", ".join(missing_ids)
        )
    elif missing_ids:
        record_failure_category("missing_id")
        errors.append("Input criterion IDs are missing: " + ", ".join(missing_ids))
    if not errors:
        input_types = {item["type"] for item in criteria_with_ids}
        output_types = {item["type"] for item in consolidated}
        if input_types - output_types:
            errors.append("Consolidation removed an existing criterion type.")
        if output_types - input_types:
            errors.append("Consolidation created a new criterion type.")
        input_evidence = {item["sourceText"] for item in criteria_with_ids}
        output_evidence = {
            source
            for item in consolidated
            for source in item["sourceText"].split(" | ")
        }
        if input_evidence != output_evidence:
            errors.append("Consolidation did not preserve all sourceText evidence.")
    if errors:
        return [], diagnostics
    return consolidated, diagnostics

def apply_python_fallback_consolidation(
    criteria: list[dict[str, str]],
) -> tuple[list[dict[str, str]], bool]:
    def member_ids_for(item: dict[str, str]) -> list[str]:
        existing = item.get("mergedFromIds")
        if isinstance(existing, list):
            return existing
        item_id = normalise_text(item.get("id")).lower()
        return [item_id] if item_id else []

    groups: list[list[dict[str, Any]]] = []
    for criterion in criteria:
        matching_group = next(
            (
                group
                for group in groups
                if can_merge_criteria_group(group + [criterion])
            ),
            None,
        )
        if matching_group is None:
            groups.append([criterion])
        else:
            matching_group.append(criterion)
    consolidated: list[dict[str, str]] = []
    for group in groups:
        if len(group) == 1:
            item = {
                key: value for key, value in group[0].items() if key != "id"
            }
            item["mergedFromIds"] = member_ids_for(group[0])
            consolidated.append(item)
            continue
        shared_workflow_objectives = set.intersection(
            *(workflow_objective_families(item) for item in group)
        )
        if shared_workflow_objectives and all(
            is_operational_workflow_step(item)
            and not is_supporting_workflow_capability(item)
            for item in group
        ):
            longest_name = max(
                (item["name"] for item in group),
                key=lambda value: (len(value), value),
            )
        else:
            longest_name = max(
                (item["name"] for item in group),
                key=lambda value: (
                    sum(
                        text_similarity(value, other["name"])
                        for other in group
                    ),
                    len(value),
                    value,
                ),
            )
        sources = [item["sourceText"] for item in group]
        merged_from_ids = [
            member_id
            for item in group
            for member_id in member_ids_for(item)
        ]
        consolidated.append(
            {
                "type": group[0]["type"],
                "name": longest_name,
                "sourceText": " | ".join(dict.fromkeys(sources)),
                "sourceIds": merge_metadata_values(group, "sourceIds"),
                "sourceCriterionIds": merge_metadata_values(
                    group,
                    "sourceCriterionIds",
                ),
                "groundingScores": merge_metadata_values(
                    group,
                    "groundingScores",
                ),
                "mergedFromIds": merged_from_ids,
            }
        )
    return consolidated, len(consolidated) < len(criteria)

def apply_consolidation(
    criteria_with_ids: list[dict[str, str]],
    raw_text: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    original = [
        {
            **{key: value for key, value in item.items() if key != "id"},
            "mergedFromIds": [normalise_text(item["id"]).lower()],
        }
        for item in criteria_with_ids
    ]
    consolidated, validation_diagnostics = validate_consolidation_output(
        raw_text,
        criteria_with_ids,
    )
    validation_errors = validation_diagnostics[
        "consolidationValidationErrors"
    ]
    parse_error = validation_diagnostics["consolidationParseError"]
    llm_valid = parse_error is None and not validation_errors
    llm_changed = llm_valid and len(consolidated) < len(original)
    result = consolidated if llm_changed else original
    method = "llm" if llm_changed else "none"
    succeeded = llm_changed
    fallback_needed = not llm_valid
    if fallback_needed:
        fallback, fallback_changed = apply_python_fallback_consolidation(
            result
        )
        if fallback_changed:
            result = fallback
            method = (
                "llm_python_fallback"
                if llm_changed
                else "python_fallback"
            )
            succeeded = True
            warning = (
                "LLM consolidation was invalid; conservative Python "
                "same-capability fallback was applied."
            )
            validation_diagnostics["consolidationWarnings"].append(warning)
    final_count_validation = validate_final_criteria_count(result)
    types_before = sorted({item["type"] for item in original})
    types_after = sorted({item["type"] for item in result})
    criterion_ids_before = [
        normalise_text(item["id"]).lower() for item in criteria_with_ids
    ]
    merged_from_ids = [
        {
            "criterionIndex": index,
            "name": item["name"],
            "mergedFromIds": list(item.get("mergedFromIds", [])),
        }
        for index, item in enumerate(result, start=1)
    ]
    criterion_ids_after = [
        member_id
        for item in result
        for member_id in item.get("mergedFromIds", [])
    ]
    diagnostics = {
        "consolidationSucceeded": succeeded,
        "consolidationMethod": method,
        "consolidationRawModelOutput": raw_text,
        "consolidationParseError": parse_error,
        "consolidationValidationErrors": validation_errors,
        "consolidationWarnings": validation_diagnostics[
            "consolidationWarnings"
        ],
        "inputCriteriaWithIds": criteria_with_ids,
        "parsedConsolidationGroups": validation_diagnostics[
            "parsedConsolidationGroups"
        ],
        "consolidationFailureCategories": validation_diagnostics[
            "consolidationFailureCategories"
        ],
        "typesBeforeConsolidation": types_before,
        "typesAfterConsolidation": types_after,
        "lostTypesDuringConsolidation": sorted(
            set(types_before) - set(types_after)
        ),
        "addedTypesDuringConsolidation": sorted(
            set(types_after) - set(types_before)
        ),
        "criterionIdsBeforeConsolidation": criterion_ids_before,
        "criterionIdsAfterConsolidation": criterion_ids_after,
        "mergedFromIds": merged_from_ids,
        "finalCriteriaLimitValid": final_count_validation["valid"],
        "finalCriteriaCountValidation": final_count_validation,
    }
    return result, diagnostics

def finalise_extraction(
    section_criteria: list[dict[str, str]],
    ignored_texts: list[dict[str, str]],
    requirement_texts: list[str] | None = None,
    consolidation_raw_output: str | None = None,
    consolidation_generator: Any = None,
) -> dict[str, Any]:
    criteria_with_fallback = [item.copy() for item in section_criteria]
    cleaned_requirement_texts = [
        normalise_text(text) for text in (requirement_texts or [])
    ]
    add_education_fallback(
        criteria_with_fallback,
        cleaned_requirement_texts,
    )
    fallback_recoveries: list[dict[str, Any]] = []
    fallback_recoveries.extend(
        add_domain_knowledge_fallback(
            criteria_with_fallback,
            cleaned_requirement_texts,
        )
    )
    fallback_recoveries.extend(
        add_preferred_certification_fallback(
            criteria_with_fallback,
            cleaned_requirement_texts,
        )
    )
    fallback_recoveries.extend(
        add_contextual_relevant_experience_fallback(
            criteria_with_fallback,
            cleaned_requirement_texts,
        )
    )
    merged = merge_duplicate_criteria(criteria_with_fallback)
    criteria_with_diagnostic_ids = assign_stable_criterion_ids(merged)
    for recovery in fallback_recoveries:
        matching_item = next(
            (
                item for item in criteria_with_diagnostic_ids
                if item["type"] == recovery["type"]
                and recovery["sourceText"] in item["sourceText"].split(" | ")
            ),
            None,
        )
        recovery["criterionId"] = (
            matching_item["id"] if matching_item is not None else None
        )
    criteria_count_before = len(merged)
    consolidation_required = needs_job_consolidation(merged)
    consolidation_attempted = False
    consolidation_succeeded = False
    consolidation_diagnostics = {
        "consolidationSucceeded": False,
        "consolidationMethod": "none",
        "consolidationRawModelOutput": consolidation_raw_output,
        "consolidationParseError": None,
        "consolidationValidationErrors": [],
        "consolidationWarnings": [],
        "inputCriteriaWithIds": [],
        "parsedConsolidationGroups": [],
        "consolidationFailureCategories": [],
        "typesBeforeConsolidation": [],
        "typesAfterConsolidation": [],
        "lostTypesDuringConsolidation": [],
        "addedTypesDuringConsolidation": [],
        "criterionIdsBeforeConsolidation": [],
        "criterionIdsAfterConsolidation": [],
        "mergedFromIds": [],
        "finalCriteriaLimitValid": True,
        "finalCriteriaCountValidation": validate_final_criteria_count(merged),
    }
    final_merged = merged
    if consolidation_required:
        criteria_with_ids = assign_stable_criterion_ids(merged)
        if consolidation_raw_output is None and consolidation_generator is not None:
            consolidation_raw_output = consolidation_generator(criteria_with_ids)
        if consolidation_raw_output is not None:
            consolidation_attempted = True
            final_merged, consolidation_diagnostics = apply_consolidation(
                criteria_with_ids,
                consolidation_raw_output,
            )
            consolidation_succeeded = consolidation_diagnostics[
                "consolidationSucceeded"
            ]
    consolidation_method = consolidation_diagnostics["consolidationMethod"]
    unresolved_consolidation = (
        consolidation_required and needs_job_consolidation(final_merged)
    )
    criteria: list[dict[str, Any]] = []
    for item in final_merged:
        criterion_type = item["type"]
        criterion_payload = {
            key: value for key, value in item.items() if key != "id"
        }
        criteria.append(
            {
                "criterionId": f"criterion-{len(criteria) + 1}",
                **criterion_payload,
                "description": DEFAULT_DESCRIPTION_TEMPLATES[
                    criterion_type
                ].format(name=item["name"]),
                "suggestedWeight": 0,
                "evidenceRule": DEFAULT_EVIDENCE_RULES[criterion_type],
            }
        )
    assign_default_weights(criteria)
    unique_ignored = {
        item["sourceText"].casefold(): item for item in ignored_texts
    }
    return {
        "softCriteria": criteria,
        "ignoredTexts": list(unique_ignored.values()),
        "needsConsolidation": unresolved_consolidation,
        "consolidationAttempted": consolidation_attempted,
        "consolidationSucceeded": consolidation_succeeded,
        "consolidationMethod": consolidation_method,
        "criteriaCountBeforeConsolidation": criteria_count_before,
        "criteriaCountAfterConsolidation": len(criteria),
        "criteriaReducedByConsolidation": criteria_count_before - len(criteria),
        "fallbackRecoveries": fallback_recoveries,
        "domainKnowledgeFallbackRecoveryCount": sum(
            item["type"] == "domain_knowledge" for item in fallback_recoveries
        ),
        "preferredCertificationFallbackRecoveryCount": sum(
            item["type"] == "preferred_certification"
            for item in fallback_recoveries
        ),
        "relevantExperienceFallbackRecoveryCount": sum(
            item["type"] == "relevant_experience"
            for item in fallback_recoveries
        ),
        "consolidationRawModelOutput": consolidation_diagnostics[
            "consolidationRawModelOutput"
        ],
        "consolidationParseError": consolidation_diagnostics[
            "consolidationParseError"
        ],
        "consolidationValidationErrors": consolidation_diagnostics[
            "consolidationValidationErrors"
        ],
        "consolidationWarnings": consolidation_diagnostics[
            "consolidationWarnings"
        ],
        "inputCriteriaWithIds": consolidation_diagnostics[
            "inputCriteriaWithIds"
        ],
        "parsedConsolidationGroups": consolidation_diagnostics[
            "parsedConsolidationGroups"
        ],
        "consolidationFailureCategories": consolidation_diagnostics[
            "consolidationFailureCategories"
        ],
        "typesBeforeConsolidation": consolidation_diagnostics[
            "typesBeforeConsolidation"
        ],
        "typesAfterConsolidation": consolidation_diagnostics[
            "typesAfterConsolidation"
        ],
        "lostTypesDuringConsolidation": consolidation_diagnostics[
            "lostTypesDuringConsolidation"
        ],
        "addedTypesDuringConsolidation": consolidation_diagnostics[
            "addedTypesDuringConsolidation"
        ],
        "criterionIdsBeforeConsolidation": consolidation_diagnostics[
            "criterionIdsBeforeConsolidation"
        ],
        "criterionIdsAfterConsolidation": consolidation_diagnostics[
            "criterionIdsAfterConsolidation"
        ],
        "mergedFromIds": consolidation_diagnostics["mergedFromIds"],
        "finalCriteriaLimitValid": True,
        "finalCriteriaCountValidation": consolidation_diagnostics[
            "finalCriteriaCountValidation"
        ],
        "consolidationDiagnostics": consolidation_diagnostics,
    }

def generate_model_output(messages: list[dict[str, str]]) -> str:
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=6144,
    )
    model_device = next(model.parameters()).device
    encoded = {key: value.to(model_device) for key, value in encoded.items()}
    generated = model.generate(
        **encoded,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    prompt_length = encoded["input_ids"].shape[1]
    return tokenizer.decode(
        generated[0, prompt_length:],
        skip_special_tokens=True,
    )

def generate_section_raw_output(
    jd_input: dict[str, Any],
    section_name: str,
    section_texts: list[str],
) -> str:
    if not section_texts:
        return '{"criteria": []}'
    return generate_model_output(
        build_section_messages(jd_input, section_name, section_texts)
    )

def generate_json_retry_output(
    jd_input: dict[str, Any],
    section_name: str,
    section_texts: list[str],
    previous_raw_output: str,
) -> str:
    retry_instruction = """Your previous response was not valid JSON.

Repeat the extraction for the same JD section.

Return valid JSON only.
Do not include markdown, comments, explanations or trailing text.

Required structure:

{
  "criteria": [
    {
      "type": "allowed_type_id",
      "name": "Concise HR-facing criterion name",
      "sourceText": "Grounded evidence from the supplied JD section"
    }
  ]
}

Use only the six allowed criterion types.
Use only evidence from the supplied JD section.
"""
    user_prompt = (
        retry_instruction
        + "\n\nAllowed type IDs:\n"
        + json.dumps(sorted(ALLOWED_SOFT_CRITERIA_TYPES), indent=2)
        + f"\n\nSection: {section_name}\n"
        + "Section texts:\n"
        + json.dumps(section_texts, indent=2)
        + "\n\nPrevious malformed response:\n"
        + previous_raw_output
    )
    return generate_model_output(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

def generate_consolidation_raw_output(
    criteria_with_ids: list[dict[str, str]],
) -> str:
    return generate_model_output(
        build_consolidation_messages(criteria_with_ids)
    )

@torch.inference_mode()
def extract_soft_criteria_llm(
    jd_inputs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outputs: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for jd_input in jd_inputs:
        responsibilities, ignored_responsibilities = filter_generic_duties(
            jd_input.get("responsibilities", [])
        )
        requirements, ignored_requirements = filter_generic_duties(
            jd_input.get("requirements", [])
        )

        section_inputs = {
            "responsibilities": responsibilities,
            "requirements": requirements,
        }
        combined_criteria: list[dict[str, str]] = []
        section_diagnostics: dict[str, dict[str, Any]] = {}

        for section_name, section_texts in section_inputs.items():
            original_raw_output = generate_section_raw_output(
                jd_input,
                section_name,
                section_texts,
            )
            retry_attempted = False
            retry_succeeded = False
            retry_raw_output: str | None = None
            final_raw_output = original_raw_output
            retry_reason = section_output_retry_reason(original_raw_output)
            if retry_reason is not None:
                retry_attempted = True
                retry_raw_output = generate_json_retry_output(
                    jd_input,
                    section_name,
                    section_texts,
                    original_raw_output,
                )
                final_raw_output = retry_raw_output
                retry_succeeded = (
                    section_output_retry_reason(retry_raw_output) is None
                )
            criteria, item_diagnostics = validate_section_output(
                final_raw_output,
                section_texts,
                source_id_prefix=section_name,
            )
            if retry_attempted and not retry_succeeded:
                retry_failure = section_output_retry_reason(final_raw_output)
                item_diagnostics["fatalErrors"].append(
                    "JSON retry failed: " + str(retry_failure)
                )
                item_diagnostics["invalidOutput"] = True
                item_diagnostics["issues"] = (
                    item_diagnostics["fatalErrors"]
                    + item_diagnostics["warnings"]
                )
                criteria = []
            item_diagnostics.update(
                {
                    "retryAttempted": retry_attempted,
                    "retrySucceeded": retry_succeeded,
                    "originalRawModelOutput": original_raw_output,
                    "retryRawModelOutput": retry_raw_output,
                    "finalRawModelOutput": final_raw_output,
                }
            )
            combined_criteria.extend(criteria)
            section_diagnostics[section_name] = item_diagnostics

        output = finalise_extraction(
            combined_criteria,
            ignored_responsibilities + ignored_requirements,
            requirements,
            consolidation_generator=generate_consolidation_raw_output,
        )
        fatal_errors = [
            f"{section_name}: {error}"
            for section_name, item in section_diagnostics.items()
            for error in item["fatalErrors"]
        ]
        warnings = [
            f"{section_name}: {warning}"
            for section_name, item in section_diagnostics.items()
            for warning in item["warnings"]
        ]
        if output["needsConsolidation"]:
            warnings.append(
                "Potential same-capability overlap remains for HR review."
            )
        if output["consolidationAttempted"] and not output["consolidationSucceeded"]:
            if output["consolidationParseError"]:
                warnings.append(
                    "consolidation: " + output["consolidationParseError"]
                )
            warnings.extend(
                "consolidation: " + error
                for error in output["consolidationValidationErrors"]
            )
        warnings.extend(
            "consolidation: " + warning
            for warning in output["consolidationWarnings"]
        )
        issues = fatal_errors + warnings
        outputs.append(output)
        diagnostics.append(
            {
                "invalidOutput": bool(fatal_errors),
                "fatalErrors": fatal_errors,
                "warnings": warnings,
                "issues": issues,
                "sectionDiagnostics": section_diagnostics,
                "sectionInputs": section_inputs,
                "finalWeightTotalValid": weights_are_valid(
                    output["softCriteria"]
                ),
                "retryAttempted": any(
                    item["retryAttempted"] for item in section_diagnostics.values()
                ),
                "retrySucceeded": any(
                    item["retrySucceeded"] for item in section_diagnostics.values()
                ),
                "consolidationAttempted": output["consolidationAttempted"],
                "consolidationSucceeded": output["consolidationSucceeded"],
                "consolidationMethod": output["consolidationMethod"],
                "criteriaCountBeforeConsolidation": output[
                    "criteriaCountBeforeConsolidation"
                ],
                "criteriaCountAfterConsolidation": output[
                    "criteriaCountAfterConsolidation"
                ],
                "fallbackRecoveries": output["fallbackRecoveries"],
                "domainKnowledgeFallbackRecoveryCount": output[
                    "domainKnowledgeFallbackRecoveryCount"
                ],
                "preferredCertificationFallbackRecoveryCount": output[
                    "preferredCertificationFallbackRecoveryCount"
                ],
                "relevantExperienceFallbackRecoveryCount": output[
                    "relevantExperienceFallbackRecoveryCount"
                ],
                "consolidationRawModelOutput": output[
                    "consolidationRawModelOutput"
                ],
                "consolidationParseError": output[
                    "consolidationParseError"
                ],
                "consolidationValidationErrors": output[
                    "consolidationValidationErrors"
                ],
                "consolidationWarnings": output[
                    "consolidationWarnings"
                ],
                "inputCriteriaWithIds": output["inputCriteriaWithIds"],
                "parsedConsolidationGroups": output[
                    "parsedConsolidationGroups"
                ],
                "rawModelOutput": {
                    section_name: {
                        "original": item["originalRawModelOutput"],
                        "retry": item["retryRawModelOutput"],
                        "final": item["finalRawModelOutput"],
                    }
                    for section_name, item in section_diagnostics.items()
                },
            }
        )
    return outputs, diagnostics
