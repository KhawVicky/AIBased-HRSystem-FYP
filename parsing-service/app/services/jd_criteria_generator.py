"""Builds rule-based criteria and eligibility suggestions."""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.config.uwc_jd_taxonomy import (
    GENERIC_CAPABILITY_TAXONOMY,
    SUPPORTING_CAPABILITY_LABELS,
    UWC_JOB_TAXONOMY,
    DomainConfig,
    PatternRule,
)
from app.schemas.jd_criteria import JDCriteriaRequest


GENERIC_SKILL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SQL", r"\bsql\b"),
    ("Python", r"\bpython\b"),
    ("R programming", r"\b(?:r programming|rstudio|using r)\b"),
    ("Power BI", r"\bpower\s*bi\b"),
    ("Tableau", r"\btableau\b"),
    ("ERP Systems", r"\berp(?: systems?| software)?\b"),
    ("AutoCAD", r"\bautocad\b"),
    ("SolidWorks", r"\bsolidworks?\b"),
    ("CNC", r"\bcnc\b"),
    ("data analysis", r"\bdata analys(?:is|tics)\b"),
    ("machine learning", r"\bmachine learning\b"),
    ("project management", r"\bproject management\b"),
    ("payroll", r"\bpayroll\b"),
    ("leadership", r"\b(?:leadership|team lead(?:ing)?)\b"),
    ("problem solving", r"\bproblem[ -]solving\b"),
)

COMMUNICATION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "written and verbal communication",
        r"\b(?:written|verbal|oral) communication(?: skills?)?\b"
        r"|\bcommunication skills?\b",
    ),
    ("interpersonal skills", r"\binterpersonal skills?\b"),
    ("negotiation", r"\bnegotiation skills?\b"),
    ("presentation", r"\bpresentation skills?\b"),
    (
        "stakeholder communication",
        r"\b(?:communicat(?:e|ion) with|liaise with)\s+(?:internal\s+)?stakeholders?\b",
    ),
)

DIGITAL_TOOL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Microsoft Office", r"\b(?:microsoft|ms) office\b"),
    ("Microsoft Excel", r"\b(?:microsoft\s+)?excel\b"),
    ("Microsoft Word", r"\b(?:microsoft\s+)?word\b"),
    ("Microsoft PowerPoint", r"\b(?:microsoft\s+)?powerpoint\b"),
    ("ATS", r"\b(?:ats|applicant tracking system)\b"),
    ("HRIS", r"\bhris\b"),
    ("JobStreet", r"\bjobstreet\b"),
    ("LinkedIn Recruiter", r"\blinkedin(?: recruiter)?\b"),
    ("social media", r"\bsocial media\b"),
    (
        "digital recruitment platforms",
        r"\b(?:online job portals?|digital recruitment platforms?|recruitment software)\b",
    ),
    ("SAP", r"\bsap\b"),
)

WORK_ATTITUDE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("proactive", r"\bproactive\b"),
    ("self-motivated", r"\bself[- ]motivated\b"),
    ("independent", r"\b(?:work|working) independently\b|\bindependent worker\b"),
    ("team player", r"\bteam player\b|\bteamwork\b"),
    ("detail-oriented", r"\b(?:detail[- ]oriented|attention to detail)\b"),
    ("responsible", r"\b(?:responsible attitude|sense of responsibility)\b"),
    ("positive attitude", r"\bpositive attitude\b"),
    ("willing to learn", r"\b(?:willingness|willing) to learn\b"),
    ("adaptable", r"\b(?:adaptable|adaptability|flexible attitude)\b"),
    ("able to multitask", r"\b(?:multi[- ]task|manage multiple priorities)\b"),
    ("integrity", r"\bintegrity\b"),
)

SKILL_PATTERNS = (
    GENERIC_SKILL_PATTERNS
    + DIGITAL_TOOL_PATTERNS
)

PROGRAMMING_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Python", r"\bpython\b"),
    ("Java", r"\bjava\b"),
    ("JavaScript", r"\bjavascript\b"),
    ("TypeScript", r"\btypescript\b"),
    ("C#", r"(?<!\w)c#(?!\w)|\bc sharp\b"),
    ("C++", r"(?<!\w)c\+\+(?!\w)"),
    ("PHP", r"\bphp\b"),
    ("Ruby", r"\bruby\b"),
    ("Go", r"\b(?:golang|go programming)\b"),
    ("Kotlin", r"\bkotlin\b"),
    ("Swift", r"\bswift\b"),
    ("SQL", r"\bsql\b"),
    (
        "coding and software development",
        r"\b(?:coding|software development|application development|develop(?:ing)? applications?)\b",
    ),
)

TESTING_PATTERNS: tuple[tuple[str, str], ...] = (
    ("software testing", r"\bsoftware testing\b|\bquality assurance\b|\bqa testing\b"),
    ("test cases", r"\btest (?:cases?|plans?|scripts?|scenarios?)\b"),
    ("manual testing", r"\bmanual testing\b"),
    ("functional testing", r"\bfunctional testing\b"),
    (
        "regression testing",
        r"\bregression(?:\s+and\s+[a-z-]+)?\s+testing\b",
    ),
    ("integration testing", r"\bintegration testing\b"),
    ("unit testing", r"\bunit testing\b"),
    ("system testing", r"\bsystem testing\b"),
    ("UAT", r"\b(?:uat|user acceptance testing)\b"),
    ("defect tracking", r"\b(?:defect|bug) (?:tracking|management|reporting)\b"),
)

AUTOMATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("test automation", r"\b(?:test automation|automated testing|automation testing)\b"),
    ("Selenium", r"\bselenium\b"),
    ("Cypress", r"\bcypress\b"),
    ("Playwright", r"\bplaywright\b"),
    ("Appium", r"\bappium\b"),
    ("Robot Framework", r"\brobot framework\b"),
    ("pytest", r"\bpytest\b"),
    ("JUnit", r"\bjunit\b"),
    ("TestNG", r"\btestng\b"),
    ("Cucumber", r"\bcucumber\b"),
)

LIFECYCLE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SDLC", r"\bsdlc\b|\bsoftware development life ?cycle\b"),
    ("STLC", r"\bstlc\b|\bsoftware testing life ?cycle\b"),
    ("Agile", r"\bagile\b"),
    ("Scrum", r"\bscrum\b"),
    ("Waterfall", r"\bwaterfall\b"),
)

DEVELOPMENT_TOOL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Git", r"\bgit\b"),
    ("GitHub", r"\bgithub\b"),
    ("GitLab", r"\bgitlab\b"),
    ("Bitbucket", r"\bbitbucket\b"),
    ("Jira", r"\bjira\b"),
    ("Jenkins", r"\bjenkins\b"),
    ("Docker", r"\bdocker\b"),
    ("Kubernetes", r"\bkubernetes\b"),
    ("CI/CD", r"\bci\s*/?\s*cd\b|\bcontinuous integration\b"),
    ("Postman", r"\bpostman\b"),
    ("Visual Studio", r"\bvisual studio\b"),
    ("VS Code", r"\bvs code\b|\bvisual studio code\b"),
    ("Azure DevOps", r"\bazure devops\b"),
)

COMPLIANCE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("regulatory compliance", r"\b(?:regulatory|legal) compliance\b"),
    ("employment law", r"\b(?:employment|labou?r) laws?\b"),
    ("data privacy", r"\b(?:data privacy|data protection|pdpa|gdpr)\b"),
    ("safety procedures", r"\b(?:workplace|occupational)?\s*safety procedures?\b"),
    ("quality standards", r"\b(?:quality standards?|quality compliance)\b"),
    ("audit requirements", r"\b(?:audit|auditing) requirements?\b"),
    ("risk controls", r"\b(?:risk controls?|risk management)\b"),
    ("access control", r"\baccess control(?: procedures?)?\b"),
)

GENERIC_FALLBACK_FUNCTION_GROUP_RULES: dict[str, tuple[PatternRule, ...]] = {
    key: capability["patterns"]
    for key, capability in GENERIC_CAPABILITY_TAXONOMY.items()
}
GENERIC_CAPABILITY_LABELS = {
    key: capability["label"]
    for key, capability in GENERIC_CAPABILITY_TAXONOMY.items()
}

ACTION_PATTERN = re.compile(
    r"\b(manag(?:e|es|ing)|lead(?:s|ing)?|oversee(?:s|ing)?|coordinate(?:s|d|ing)?|"
    r"develop(?:s|ed|ing)?|design(?:s|ed|ing)?|create(?:s|d|ing)?|prepare(?:s|d|ing)?|"
    r"analy[sz](?:e|es|ed|ing)|maintain(?:s|ed|ing)?|implement(?:s|ed|ing)?|"
    r"monitor(?:s|ed|ing)?|perform(?:s|ed|ing)?|conduct(?:s|ed|ing)?|execute(?:s|d|ing)?|"
    r"support(?:s|ed|ing)?|handle(?:s|d|ing)?|ensure(?:s|d|ing)?|review(?:s|ed|ing)?|"
    r"source(?:s|d|ing)?|screen(?:s|ed|ing)?|negotiate(?:s|d|ing)?|"
    r"test(?:s|ed|ing)?|automat(?:e|es|ed|ing)|troubleshoot(?:s|ed|ing)?|"
    r"repair(?:s|ed|ing)?|inspect(?:s|ed|ing)?|train(?:s|ed|ing)?|"
    r"build(?:s|ing)?|built|"
    r"communicate(?:s|d|ing)?|collaborate(?:s|d|ing)?|deliver(?:s|ed|ing)?|"
    r"plan(?:s|ned|ning)?|process(?:es|ed|ing)?|use(?:s|d|ing)?|write(?:s|written|ing)?)\b",
    flags=re.IGNORECASE,
)

ACTION_BASES = {
    "manag": "Manage",
    "lead": "Lead",
    "oversee": "Oversee",
    "coordinate": "Coordinate",
    "develop": "Develop",
    "design": "Design",
    "create": "Create",
    "prepare": "Prepare",
    "analy": "Analyse",
    "maintain": "Maintain",
    "implement": "Implement",
    "monitor": "Monitor",
    "perform": "Perform",
    "conduct": "Conduct",
    "execute": "Execute",
    "support": "Support",
    "handle": "Handle",
    "ensure": "Ensure",
    "review": "Review",
    "source": "Source",
    "screen": "Screen",
    "negotiate": "Negotiate",
    "test": "Test",
    "automat": "Automate",
    "troubleshoot": "Troubleshoot",
    "repair": "Repair",
    "inspect": "Inspect",
    "train": "Train",
    "build": "Build",
    "built": "Build",
    "communicate": "Communicate",
    "collaborate": "Collaborate",
    "deliver": "Deliver",
    "plan": "Plan",
    "process": "Process",
    "use": "Use",
    "write": "Write",
}

@dataclass
class ResponsibilityFact:
    sentence: str
    action: str
    object: str


@dataclass
class FunctionalGroup:
    key: str
    capability_label: str
    facts: list[ResponsibilityFact] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

BUSINESS_TOOL_LABELS = {
    "Power BI",
    "Tableau",
    "ERP Systems",
    "AutoCAD",
    "SolidWorks",
    "CNC",
    *(label for label, _ in DIGITAL_TOOL_PATTERNS),
}

CERTIFICATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SHRM", r"\bshrm(?:-cp|-scp)?\b"),
    ("CIPD", r"\bcipd\b"),
    ("MIHRM", r"\bmihrm\b"),
    ("ACCA", r"\bacca\b"),
    ("CPA", r"\bcpa\b"),
    ("CFA", r"\bcfa\b"),
    ("PMP", r"\bpmp\b"),
    ("Six Sigma", r"\bsix sigma\b"),
    ("NIOSH", r"\bniosh\b"),
    ("DOSH", r"\bdosh\b"),
    ("OSHA", r"\bosha\b"),
    ("ISO", r"\biso(?:\s*\d{4,5})?\b"),
    ("First Aid", r"\bfirst aid\b"),
    (
        "Professional certification",
        r"\b(?:professional|required) certification\b|\bcertified in\b",
    ),
)

EDUCATION_RULES: tuple[tuple[str, str], ...] = (
    ("PhD", r"\b(?:ph\.?d\.?|doctorate|doctoral degree)\b"),
    ("Master Degree", r"\b(?:master'?s?(?: degree)?|mba)\b"),
    (
        "Bachelor Degree",
        r"\b(?:bachelor'?s?(?: degree)?|degree holder|degree(?:\s+in|\s+from)?)\b",
    ),
    ("Diploma", r"\bdiploma\b"),
    (
        "STPM / Foundation / Matriculation",
        r"\b(?:stpm|foundation|matriculation|a[ -]?levels?)\b",
    ),
    ("SPM", r"\b(?:spm|pmr)\b"),
)

LANGUAGE_RULES: tuple[tuple[str, str], ...] = (
    ("English", r"\benglish\b"),
    ("Bahasa Malaysia", r"\b(?:bahasa malaysia|bahasa melayu|malay)\b"),
    ("Mandarin", r"\b(?:mandarin|chinese)\b"),
    ("Tamil", r"\btamil\b"),
    ("Japanese", r"\bjapanese\b"),
    ("Korean", r"\bkorean\b"),
)

LOCATION_RULES: tuple[tuple[str, str], ...] = (
    ("Penang", r"\b(?:penang|batu kawan|bukit minyak|perai|prai)\b"),
    ("Kuala Lumpur", r"\b(?:kuala lumpur|kl)\b"),
    ("Selangor", r"\bselangor\b"),
    ("Johor", r"\b(?:johor|johor bahru|jb)\b"),
    ("Perak", r"\bperak\b"),
)

EXPERIENCE_SIGNAL_PATTERN = re.compile(
    r"\bexperience (?:working )?(?:in|with|as|coding|developing|testing|using)\b"
    r"|\b(?:relevant|professional|industry|working) experience\b"
    r"|\b(?:past|previous|prior) working experience\b"
    r"|\bworked (?:in|with|for|as)\b"
    r"|\b(?:experienced|experience) (?:is )?(?:required|preferred|essential)\b",
    flags=re.IGNORECASE,
)

EXPERIENCE_REQUIREMENT_PATTERN = re.compile(
    EXPERIENCE_SIGNAL_PATTERN.pattern
    + r"|\b(?:at least|minimum|min\.?)\s*\d+(?:\.\d+)?"
    r"(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*(?:\+|plus)?\s*years?\b",
    flags=re.IGNORECASE,
)

DOMAIN_KNOWLEDGE_SIGNAL_PATTERN = re.compile(
    r"\b(?:laws?|regulations?|regulatory|statutory|standards?|"
    r"compliance frameworks?|professional principles?|technical concepts?|"
    r"sdlc|stlc|gaap|accounting principles?|incident response procedures?|"
    r"employment act|labou?r act|epf|socso|eis|lhdn|pcb|fomema|"
    r"immigration requirements?|iso(?:\s*\d{4,5})?)\b",
    flags=re.IGNORECASE,
)

PREFERRED_CERTIFICATION_PATTERN = re.compile(
    r"\b(?:preferred|preferably|desirable|beneficial|"
    r"added advantage|an advantage|would be beneficial)\b",
    flags=re.IGNORECASE,
)

SOFT_CRITERION_BASE_WEIGHTS = {
    "relevant_skill": 30,
    "relevant_experience": 25,
    "domain_knowledge": 20,
    "education_relevance": 10,
    "preferred_certification": 8,
    "job_related_language": 7,
}

SOFT_CRITERION_LABELS = {
    "relevant_skill": "Relevant Skill",
    "relevant_experience": "Relevant Experience",
    "domain_knowledge": "Domain Knowledge",
    "education_relevance": "Education Relevance",
    "preferred_certification": "Preferred Certification",
    "job_related_language": "Job-Related Language",
}

EDUCATION_ALTERNATIVE_PATTERNS: tuple[str, ...] = (
    r"\b(?:degree|diploma|academic qualification|qualification)\b.{0,80}"
    r"\b(?:or|and/or)\b.{0,80}\b(?:past working |relevant |equivalent )?experience\b",
    r"\bexperience\b.{0,80}\b(?:or|in lieu of|instead of)\b.{0,80}"
    r"\b(?:degree|diploma|qualification)\b",
    r"\bequivalent combination of (?:education|qualification) and experience\b",
    r"\b(?:degree|diploma) or equivalent experience\b",
)


def _joined_source(request: JDCriteriaRequest) -> str:
    values: Iterable[str] = (
        request.description,
        *request.qualifications,
        *request.responsibilities,
        *request.requirements,
    )
    return "\n".join(value.strip() for value in values if value and value.strip())


def _detect_labels(source: str, rules: tuple[tuple[str, str], ...]) -> list[str]:
    return [
        label
        for label, pattern in rules
        if re.search(pattern, source, flags=re.IGNORECASE)
    ]


def _literal_pattern(value: str) -> str:
    return r"\b" + re.escape(value).replace(r"\ ", r"\s+") + r"\b"


def _domain_patterns(config: DomainConfig, include_capabilities: bool) -> list[str]:
    patterns = [
        *(_literal_pattern(value) for value in config["keywords"]),
        *(_literal_pattern(value) for value in config["phrases"]),
        *config["patterns"],
    ]
    if include_capabilities:
        for capability in config["capabilities"].values():
            patterns.extend(
                _literal_pattern(value) for value in capability["keywords"]
            )
            patterns.extend(
                _literal_pattern(value) for value in capability["phrases"]
            )
            patterns.extend(pattern for _, pattern in capability["patterns"])
    return list(dict.fromkeys(patterns))


def _pattern_match_score(source: str, patterns: Iterable[str]) -> int:
    return sum(
        1 for pattern in patterns if re.search(pattern, source, flags=re.IGNORECASE)
    )


def _domain_content_score(source: str, config: DomainConfig) -> int:
    score = _pattern_match_score(
        source, (_literal_pattern(value) for value in config["keywords"])
    )
    score += _pattern_match_score(
        source, (_literal_pattern(value) for value in config["phrases"])
    ) * 2
    score += _pattern_match_score(source, config["patterns"]) * 3
    for capability in config["capabilities"].values():
        score += _pattern_match_score(
            source,
            (_literal_pattern(value) for value in capability["keywords"]),
        )
        score += _pattern_match_score(
            source,
            (_literal_pattern(value) for value in capability["phrases"]),
        ) * 2
        score += _pattern_match_score(
            source, (pattern for _, pattern in capability["patterns"])
        ) * 4
    return score


def _detect_uwc_taxonomy_domain(request: JDCriteriaRequest) -> str | None:
    # Responsibilities carry more weight than qualifications and context.
    responsibility_source = "\n".join(request.responsibilities)
    supporting_source = "\n".join(
        [*request.qualifications, *request.requirements]
    )
    context_source = "\n".join([request.jobTitle, request.department])
    ranked: list[tuple[int, int, str]] = []
    for domain_key, config in UWC_JOB_TAXONOMY.items():
        content_score = (
            _domain_content_score(responsibility_source, config) * 3
            + _domain_content_score(supporting_source, config)
        )
        if content_score == 0:
            continue
        context_score = _pattern_match_score(
            context_source,
            _domain_patterns(config, include_capabilities=False),
        )
        ranked.append((content_score, context_score, domain_key))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][2]


def _taxonomy_capability_rules(
    domain_key: str | None,
) -> dict[str, tuple[PatternRule, ...]]:
    if not domain_key:
        return {}
    return {
        capability_key: capability["patterns"]
        for capability_key, capability in UWC_JOB_TAXONOMY[domain_key][
            "capabilities"
        ].items()
    }


def _taxonomy_capability_labels(domain_key: str | None) -> dict[str, str]:
    if not domain_key:
        return {}
    return {
        capability_key: capability["label"]
        for capability_key, capability in UWC_JOB_TAXONOMY[domain_key][
            "capabilities"
        ].items()
    }


def _detect_experience(source: str) -> tuple[float | None, str]:
    normalized_source = source.replace("\u2013", "-").replace("\u2014", "-")
    patterns = (
        r"(?:minimum|min\.?|at least)?\s*(\d+(?:\.\d+)?)\s*[-]\s*"
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        r"(?:minimum|min\.?|at least)\s+(?:of\s+)?(\d+(?:\.\d+)?)"
        r"\s*\+?\s*(?:years?|yrs?)(?:\s+(?:of|in|with))?"
        r"(?:\s+[a-z-]+){0,6}\s*(?:experience|recruitment|working)?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)"
        r"(?:\s+(?:of|in|with))?(?:\s+[a-z-]+){0,6}"
        r"\s*(?:experience|recruitment)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized_source, flags=re.IGNORECASE)
        if not match:
            continue
        minimum = float(match.group(1))
        maximum = match.group(2) if match.lastindex and match.lastindex > 1 else None
        display_minimum = f"{minimum:g}"
        evidence = (
            f"{display_minimum}-{float(maximum):g} years of experience"
            if maximum
            else f"at least {display_minimum} years of experience"
        )
        return minimum, evidence
    return None, ""


def _experience_option(years: float) -> str:
    if years <= 0:
        return "0 year"
    if years < 1:
        return "Internship"
    rounded_years = math.floor(years)
    if rounded_years <= 4:
        return f"{rounded_years} year" + ("s" if rounded_years != 1 else "")
    if rounded_years < 8:
        return "5+ years"
    if rounded_years < 10:
        return "8+ years"
    return "10+ years"


def _detect_cgpa(source: str) -> float | None:
    match = re.search(
        r"\b(?:cgpa|gpa)\s*(?:of|at least|minimum|min\.?|[:>=-])*\s*"
        r"([0-4](?:\.\d{1,2})?)",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 < value <= 4 else None


def _education_allows_experience(source: str) -> bool:
    return any(
        re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL)
        for pattern in EDUCATION_ALTERNATIVE_PATTERNS
    )


def _display_label(label: str) -> str:
    if any(character.isupper() for character in label[1:]):
        return label
    words = label.title().split()
    connectors = {"A", "An", "And", "For", "In", "Of", "Or", "The", "To", "With"}
    displayed = " ".join(
        word.lower() if word in connectors else word for word in words
    )
    return displayed.replace("-To-", "-to-")


def _human_join(labels: list[str]) -> str:
    displayed = [_display_label(label) for label in labels]
    if len(displayed) <= 1:
        return "".join(displayed)
    if len(displayed) == 2:
        return " and ".join(displayed)
    return ", ".join(displayed[:-1]) + f" and {displayed[-1]}"


def _plain_join(values: list[str]) -> str:
    if len(values) <= 1:
        return "".join(values)
    if len(values) == 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _main_action(action_text: str) -> str:
    lowered = action_text.lower()
    for stem, display in ACTION_BASES.items():
        if lowered.startswith(stem):
            return display
    return _display_label(action_text)


def _responsibility_fact(sentence: str) -> ResponsibilityFact | None:
    # Keep a short action and object for grouping, not for the final name.
    cleaned = re.sub(r"^[\s\d.)-]+", "", sentence).strip()
    if not cleaned:
        return None
    action_match = ACTION_PATTERN.search(cleaned)
    if action_match:
        action = _main_action(action_match.group(1))
        object_text = cleaned[action_match.end() :]
    else:
        words = cleaned.split(maxsplit=1)
        action = _display_label(words[0])
        object_text = words[1] if len(words) > 1 else ""

    object_text = re.split(
        r"\b(?:using|through|by|in accordance with|according to|to ensure)\b",
        object_text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    object_text = re.sub(r"\s+", " ", object_text).strip(" .,:;-()").strip()
    object_words = object_text.split()
    if len(object_words) > 14:
        object_text = " ".join(object_words[:14])

    return ResponsibilityFact(cleaned, action, object_text)


def _is_generic_responsibility(sentence: str) -> bool:
    # Generic duties do not show a useful candidate capability.
    generic_patterns = (
        r"perform (?:any )?other duties? (?:as |when )?(?:assigned|required)",
        r"support (?:the )?management(?: team)? (?:as |when )?(?:required|needed)",
        r"(?:follow|adhere to|comply with) (?:all )?(?:company|internal) "
        r"(?:policies|procedures|rules|guidelines)",
        r"(?:complete|perform|carry out|handle) (?:any )?other "
        r"(?:tasks?|duties|assignments?) (?:as |when )?"
        r"(?:instructed|assigned|required)",
        r"(?:other|additional|ad[ -]?hoc) duties? (?:as |when )?"
        r"(?:assigned|required|instructed)",
    )
    normalized = sentence.strip().strip(" .;:")
    return any(
        re.fullmatch(pattern, normalized, flags=re.IGNORECASE)
        for pattern in generic_patterns
    )


def _responsibility_groups(
    responsibilities: list[str],
    taxonomy_rules: dict[str, tuple[PatternRule, ...]] | None = None,
    taxonomy_labels: dict[str, str] | None = None,
) -> list[FunctionalGroup]:
    # Each sentence is mapped to at most one clear capability group.
    groups: list[FunctionalGroup] = []
    active_rules = {
        **(taxonomy_rules or {}),
        **GENERIC_FALLBACK_FUNCTION_GROUP_RULES,
    }
    active_labels = {
        **GENERIC_CAPABILITY_LABELS,
        **(taxonomy_labels or {}),
    }
    for sentence in responsibilities:
        if _is_generic_responsibility(sentence):
            continue
        fact = _responsibility_fact(sentence)
        if not fact:
            continue

        ranked_matches: list[tuple[int, int, str, list[str]]] = []
        for key, rules in active_rules.items():
            labels = _detect_labels(fact.sentence, rules)
            if labels:
                first_position = min(
                    match.start()
                    for _, pattern in rules
                    if (match := re.search(pattern, fact.sentence, flags=re.IGNORECASE))
                )
                ranked_matches.append(
                    (len(labels), -first_position, key, labels)
                )

        if ranked_matches:
            _, _, key, labels = max(
                ranked_matches, key=lambda item: (item[0], item[1])
            )
            group = next((item for item in groups if item.key == key), None)
            if group is None:
                group = FunctionalGroup(key, active_labels[key])
                groups.append(group)
            group.facts.append(fact)
            group.labels = list(dict.fromkeys([*group.labels, *labels]))

    return groups


def _functional_group_name(group: FunctionalGroup) -> str:
    if len(group.labels) == 1:
        return _display_label(group.labels[0])
    return group.capability_label


CORE_IMPACT_PATTERN = re.compile(
    r"\b(?:achieve|increase|reduce|improve|optimi[sz]e|save|deliver|meet)\w*\b"
    r"|\b(?:targets?|revenue|costs?|savings?|quality|defects?|output|"
    r"productivity|efficiency|deadlines?|kpis?|results?)\b",
    flags=re.IGNORECASE,
)
CORE_OWNERSHIP_PATTERN = re.compile(
    r"\b(?:lead|manage|oversee|own|develop|design|negotiate|resolve)\w*\b",
    flags=re.IGNORECASE,
)


def _core_criterion_importance(group: FunctionalGroup, position: int) -> int:
    importance = 40 - position * 4
    importance += min(max(len(group.facts) - 1, 0) * 6, 12)
    importance += min(len(group.labels), 3)
    if any(CORE_IMPACT_PATTERN.search(fact.sentence) for fact in group.facts):
        importance += 14
    if any(CORE_OWNERSHIP_PATTERN.search(fact.sentence) for fact in group.facts):
        importance += 5
    if group.key == "documentation_records":
        importance -= 12
    if group.key == "data_analysis_reporting" and not any(
        label in {"Data Analysis", "Performance Insights"}
        for label in group.labels
    ):
        importance -= 10
    return max(importance, 12)


def _hr_explanation(requirement: str, resume_evidence: str) -> str:
    return (
        f"The job description requires {requirement.strip().rstrip('.')}."
        f" The resume should show {resume_evidence.strip().rstrip('.')}."
    )


def _matching_evidence(
    values: Iterable[str], rules: tuple[tuple[str, str], ...]
) -> list[str]:
    return [
        value.strip()
        for value in values
        if value.strip()
        and any(
            re.search(pattern, value, flags=re.IGNORECASE)
            for _, pattern in rules
        )
    ]


def _matching_experience_evidence(values: Iterable[str]) -> list[str]:
    return [
        value.strip()
        for value in values
        if value.strip() and EXPERIENCE_REQUIREMENT_PATTERN.search(value)
    ]


def _matching_preferred_certification_evidence(
    values: Iterable[str],
) -> list[str]:
    return [
        value.strip()
        for value in values
        if value.strip()
        and PREFERRED_CERTIFICATION_PATTERN.search(value)
        and any(
            re.search(pattern, value, flags=re.IGNORECASE)
            for _, pattern in CERTIFICATION_PATTERNS
        )
    ]


def _criterion_soft_type(criterion: dict) -> str:
    category = criterion["category"]
    if category in SOFT_CRITERION_BASE_WEIGHTS:
        return category
    if category == "experience":
        return "relevant_experience"
    if category == "education":
        return "education_relevance"
    if category == "certification":
        return "preferred_certification"
    if category == "language":
        return "job_related_language"
    if category == "compliance":
        return "domain_knowledge"
    return "relevant_skill"


def _consolidate_soft_criteria(criteria: list[dict]) -> list[dict]:
    # The six soft types are optional, but each enabled type is shown once.
    grouped: dict[str, list[dict]] = {}
    for criterion in criteria:
        criterion_type = _criterion_soft_type(criterion)
        grouped.setdefault(criterion_type, []).append(criterion)

    consolidated: list[dict] = []
    for criterion_type in SOFT_CRITERION_BASE_WEIGHTS:
        members = grouped.get(criterion_type, [])
        if not members:
            continue

        evidence = list(
            dict.fromkeys(
                source
                for member in members
                for source in member["jdEvidence"]
            )
        )
        if len(members) == 1:
            explanation = members[0]["explanation"]
            resume_evidence = members[0]["resumeEvidenceToCheck"]
        else:
            capability_names = _plain_join(
                [member["name"] for member in members]
            )
            explanation = _hr_explanation(
                f"practical capability across {capability_names}",
                "direct examples of performing these functions, including "
                "responsibility scope, tools used, achievements, and measurable "
                "results",
            )
            resume_evidence = (
                "Direct examples covering the identified capabilities, including "
                "responsibility scope, tools used, achievements, and measurable "
                "results."
            )

        consolidated.append(
            {
                "id": f"generated-{criterion_type.replace('_', '-')}",
                "category": (
                    members[0]["category"]
                    if len(members) == 1
                    else criterion_type
                ),
                "type": criterion_type,
                "name": (
                    members[0]["name"]
                    if len(members) == 1
                    else SOFT_CRITERION_LABELS[criterion_type]
                ),
                "_importance": max(
                    member["_importance"] for member in members
                ),
                "status": "active",
                "jdEvidence": evidence,
                "explanation": explanation,
                "resumeEvidenceToCheck": resume_evidence,
                "isAutoDetected": True,
            }
        )
    return consolidated


def _detect_academic_field(source: str) -> str:
    match = re.search(
        r"\b(?:ph\.?d\.?|doctorate|master'?s?(?: degree)?|mba|"
        r"bachelor'?s?(?: degree)?|degree|diploma)\s+(?:in|of)\s+"
        r"([^\n,.;]{2,80}?)(?=\s+with\b|\s+(?:and\s+)?(?:minimum|at least)\b|"
        r"[\n,.;]|$)",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    phrase = re.sub(r"\s+", " ", match.group(1)).strip(" -/")
    words = phrase.title().split()
    connectors = {"And", "Or", "Of", "In", "For"}
    return " ".join(word.lower() if word in connectors else word for word in words)


def _supporting_category_evidence(
    request: JDCriteriaRequest,
    rules: tuple[tuple[str, str], ...],
    base_importance: int,
) -> tuple[list[str], int]:
    supporting_source = "\n".join(
        [request.description, *request.qualifications, *request.requirements]
    )
    labels = _detect_labels(supporting_source, rules)
    importance = base_importance + len(labels)
    return labels, importance


CRITERION_NAME_STOP_WORDS = {
    "and",
    "for",
    "in",
    "of",
    "the",
    "with",
    "professional",
    "relevant",
}


def _criterion_name_tokens(name: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z][a-z-]{2,}", name.lower())
        if token not in CRITERION_NAME_STOP_WORDS
    }


def _criteria_are_overlapping(first: dict, second: dict) -> bool:
    distinct_soft_categories = {
        "experience",
        "education",
        "compliance",
        "certification",
        "language",
    }
    if (
        first["category"] != second["category"]
        and (
            first["category"] in distinct_soft_categories
            or second["category"] in distinct_soft_categories
        )
    ):
        return False
    if first["name"].casefold() == second["name"].casefold():
        return True
    category_pair = {first["category"], second["category"]}
    if (
        "communication" in category_pair
        and any(
            category.endswith("stakeholder_coordination")
            for category in category_pair
        )
    ):
        return True
    first_tokens = _criterion_name_tokens(first["name"])
    second_tokens = _criterion_name_tokens(second["name"])
    shared = first_tokens & second_tokens
    combined = first_tokens | second_tokens
    return (
        len(shared) >= 2
        and bool(combined)
        and len(shared) / len(combined) >= 0.5
    )


def _merge_overlapping_criteria(criteria: list[dict]) -> list[dict]:
    # Merge only close criteria and keep all JD evidence.
    merged: list[dict] = []
    for candidate in criteria:
        match_index = next(
            (
                index
                for index, existing in enumerate(merged)
                if _criteria_are_overlapping(existing, candidate)
            ),
            None,
        )
        if match_index is None:
            merged.append(candidate)
            continue

        existing = merged[match_index]
        existing_is_core = existing["category"].startswith("job_function_")
        candidate_is_core = candidate["category"].startswith("job_function_")
        if candidate_is_core and not existing_is_core:
            primary, secondary = candidate, existing
        elif existing_is_core and not candidate_is_core:
            primary, secondary = existing, candidate
        elif candidate["_importance"] > existing["_importance"]:
            primary, secondary = candidate, existing
        else:
            primary, secondary = existing, candidate

        primary["jdEvidence"] = list(
            dict.fromkeys([*primary["jdEvidence"], *secondary["jdEvidence"]])
        )
        primary["_importance"] = max(
            primary["_importance"], secondary["_importance"]
        )
        if not primary["category"].startswith("job_function_"):
            maxima = [
                value
                for value in (
                    primary.get("_maximum"),
                    secondary.get("_maximum"),
                )
                if value is not None
            ]
            if maxima:
                primary["_maximum"] = min(maxima)
        else:
            primary.pop("_maximum", None)
        merged[match_index] = primary
    return merged


def _assign_evidence_weights(criteria: list[dict]) -> tuple[list[dict], int]:
    # Preserve every enabled soft type, then normalise its base share to 100.
    if not criteria:
        return [], 0

    for criterion in criteria:
        criterion["type"] = _criterion_soft_type(criterion)

    original_count = len(criteria)
    selected: list[dict] = []
    selected_ids: set[int] = set()

    for criterion_type in SOFT_CRITERION_BASE_WEIGHTS:
        matching = [
            item for item in criteria if item["type"] == criterion_type
        ]
        if not matching:
            continue
        representative = max(matching, key=lambda item: item["_importance"])
        selected.append(representative)
        selected_ids.add(id(representative))

    for item in sorted(
        criteria, key=lambda criterion: criterion["_importance"], reverse=True
    ):
        if len(selected) >= 6:
            break
        if id(item) not in selected_ids:
            selected.append(item)
            selected_ids.add(id(item))

    selected.sort(key=criteria.index)
    enabled_types = [
        criterion_type
        for criterion_type in SOFT_CRITERION_BASE_WEIGHTS
        if any(item["type"] == criterion_type for item in selected)
    ]
    enabled_base_total = sum(
        SOFT_CRITERION_BASE_WEIGHTS[criterion_type]
        for criterion_type in enabled_types
    )
    raw_type_weights = {
        criterion_type: (
            SOFT_CRITERION_BASE_WEIGHTS[criterion_type]
            * 100
            / enabled_base_total
        )
        for criterion_type in enabled_types
    }
    type_weights = {
        criterion_type: math.floor(raw_type_weights[criterion_type])
        for criterion_type in enabled_types
    }
    remainder = 100 - sum(type_weights.values())
    remainder_order = sorted(
        enabled_types,
        key=lambda criterion_type: (
            raw_type_weights[criterion_type] - type_weights[criterion_type],
            -list(SOFT_CRITERION_BASE_WEIGHTS).index(criterion_type),
        ),
        reverse=True,
    )
    for criterion_type in remainder_order[:remainder]:
        type_weights[criterion_type] += 1

    for criterion_type, type_weight in type_weights.items():
        matching = [
            item for item in selected if item["type"] == criterion_type
        ]
        if len(matching) == 1:
            matching[0]["weight"] = type_weight
            continue

        minimum_weight = 1
        distributable = type_weight - minimum_weight * len(matching)
        priority_scores = [item["_importance"] ** 2 for item in matching]
        total_priority = sum(priority_scores)
        raw_shares = [
            score * distributable / total_priority
            for score in priority_scores
        ]
        allocated = [math.floor(share) for share in raw_shares]
        item_remainder = distributable - sum(allocated)
        item_order = sorted(
            range(len(matching)),
            key=lambda index: (
                raw_shares[index] - allocated[index],
                -index,
            ),
            reverse=True,
        )
        for index in item_order[:item_remainder]:
            allocated[index] += 1
        for item, extra_weight in zip(matching, allocated, strict=True):
            item["weight"] = minimum_weight + extra_weight

    output = []
    for item in selected:
        item.pop("_importance")
        item.pop("_maximum", None)
        output.append(item)
    return output, original_count - len(output)


def generate_jd_criteria(request: JDCriteriaRequest) -> dict:
    """Convert JD evidence into editable criteria, eligibility suggestions, and total weight 100."""

    # Detect, group, support, merge, and weight in a fixed order.
    detected_domain = _detect_uwc_taxonomy_domain(request)
    taxonomy_rules = _taxonomy_capability_rules(detected_domain)
    taxonomy_labels = _taxonomy_capability_labels(detected_domain)
    active_group_rules = {
        **taxonomy_rules,
        **GENERIC_FALLBACK_FUNCTION_GROUP_RULES,
    }
    responsibility_groups = _responsibility_groups(
        request.responsibilities, taxonomy_rules, taxonomy_labels
    )
    supporting_evidence_values = [
        *request.qualifications,
        *request.requirements,
        request.description,
    ]
    supporting_source = "\n".join(supporting_evidence_values)
    automation, automation_importance = _supporting_category_evidence(
        request, AUTOMATION_PATTERNS, 6
    )
    development_tools, development_tools_importance = _supporting_category_evidence(
        request, DEVELOPMENT_TOOL_PATTERNS, 4
    )
    business_tool_rules = DIGITAL_TOOL_PATTERNS + tuple(
        rule
        for rule in GENERIC_SKILL_PATTERNS
        if rule[0] in BUSINESS_TOOL_LABELS
    )
    business_tools, business_tools_importance = _supporting_category_evidence(
        request, business_tool_rules, 5
    )
    automation_tools = [item for item in automation if item != "test automation"]
    combined_tools = list(
        dict.fromkeys([*business_tools, *development_tools, *automation_tools])
    )
    combined_tool_importance = max(
        business_tools_importance,
        development_tools_importance,
        automation_importance,
    )
    communication_skills, communication_importance = _supporting_category_evidence(
        request, COMMUNICATION_PATTERNS, 4
    )
    _, compliance_importance = _supporting_category_evidence(
        request, COMPLIANCE_PATTERNS, 5
    )
    work_attitudes, attitude_importance = _supporting_category_evidence(
        request, WORK_ATTITUDE_PATTERNS, 3
    )
    preferred_certification_evidence = (
        _matching_preferred_certification_evidence(
            supporting_evidence_values
        )
    )
    certifications = _detect_labels(
        "\n".join(preferred_certification_evidence),
        CERTIFICATION_PATTERNS,
    )
    certification_importance = 3 + len(certifications)
    spoken_languages = _detect_labels(supporting_source, LANGUAGE_RULES)
    locations = _detect_labels(supporting_source, LOCATION_RULES)
    education = next(
        (
            label
            for label, pattern in EDUCATION_RULES
            if re.search(pattern, supporting_source, flags=re.IGNORECASE)
        ),
        "",
    )
    education_is_alternative = bool(education) and _education_allows_experience(
        supporting_source
    )
    academic_field = _detect_academic_field(supporting_source)
    experience_years, _ = _detect_experience(supporting_source)
    experience_evidence = _matching_experience_evidence(
        [*request.qualifications, *request.requirements]
    )
    cgpa = _detect_cgpa(supporting_source)

    criteria: list[dict] = []

    def add_criterion(
        key: str,
        category: str,
        name: str,
        importance: int,
        explanation: str,
        maximum: int | None = None,
        evidence: list[str] | None = None,
        resume_evidence_to_check: str = (
            "Demonstrated experience, proficiency, scope, and results."
        ),
    ) -> None:
        criterion_evidence = list(
            dict.fromkeys(item.strip() for item in (evidence or []) if item.strip())
        )
        if not criterion_evidence:
            return
        criterion = {
            "id": f"generated-{key}",
            "category": category,
            "name": name,
            "_importance": importance,
            "status": "active",
            "jdEvidence": criterion_evidence,
            "explanation": explanation.strip(),
            "resumeEvidenceToCheck": resume_evidence_to_check.strip(),
            "isAutoDetected": True,
        }
        if maximum is not None:
            criterion["_maximum"] = maximum
        criteria.append(criterion)

    for index, group in enumerate(responsibility_groups):
        group_rules = active_group_rules.get(group.key, ())
        evidence = [fact.sentence for fact in group.facts]
        if group_rules:
            evidence.extend(
                _matching_evidence(
                    [*request.qualifications, *request.requirements], group_rules
                )
            )
        criterion_name = _functional_group_name(group)
        responsibility_actions = list(
            dict.fromkeys(
                f"{fact.action.lower()} {fact.object}".strip()
                for fact in group.facts
                if fact.action or fact.object
            )
        )
        responsibility_meaning = _plain_join(responsibility_actions)
        matched_capabilities = _plain_join(
            [label.lower() for label in group.labels]
        )
        resume_evidence = (
            f"direct experience in {matched_capabilities}, including the scope of "
            "responsibility, relevant projects, achievements, and measurable results"
        )
        add_criterion(
            group.key,
            f"job_function_{group.key}",
            criterion_name,
            _core_criterion_importance(group, index),
            _hr_explanation(
                f"the candidate to {responsibility_meaning}",
                resume_evidence,
            ),
            evidence=evidence,
            resume_evidence_to_check=(
                resume_evidence[0].upper() + resume_evidence[1:] + "."
            ),
        )

    if experience_evidence and criteria:
        primary_capability = criteria[0]["name"]
        add_criterion(
            "relevant-experience",
            "experience",
            f"Experience in {primary_capability}",
            24,
            _hr_explanation(
                f"experience related to {primary_capability.lower()}",
                "the relevance and depth of the candidate's work, responsibility "
                "scope, industry or operating environment, achievements, and "
                "measurable results beyond the minimum years required",
            ),
            evidence=experience_evidence,
            resume_evidence_to_check=(
                "Experience relevance, depth, responsibility scope, industry or "
                "operating environment, achievements, and measurable results beyond "
                "the minimum eligibility threshold."
            ),
        )

    if combined_tools and criteria:
        combined_tool_rules = (
            business_tool_rules
            + DEVELOPMENT_TOOL_PATTERNS
            + AUTOMATION_PATTERNS
        )
        add_criterion(
            "tools-systems",
            "tools_systems",
            SUPPORTING_CAPABILITY_LABELS["tools_systems"],
            combined_tool_importance,
            _hr_explanation(
                "practical use of " + _human_join(combined_tools),
                "where the candidate used these tools, the level of proficiency, "
                "the complexity of the work, and results achieved",
            ),
            maximum=15,
            evidence=_matching_evidence(
                supporting_evidence_values, combined_tool_rules
            ),
            resume_evidence_to_check=(
                "Proficiency level, work complexity, and results achieved with "
                + _human_join(combined_tools)
                + "."
            ),
        )
    if communication_skills and criteria:
        communication_context = ""
        if responsibility_groups:
            primary_group = responsibility_groups[0]
            context_items = primary_group.labels[:2]
            if not context_items:
                context_items = [
                    fact.object
                    for fact in primary_group.facts
                    if fact.object
                ][:2]
            communication_context = _human_join(context_items)
        add_criterion(
            "communication-skills",
            "communication",
            SUPPORTING_CAPABILITY_LABELS["communication"],
            communication_importance,
            _hr_explanation(
                _human_join(communication_skills).lower()
                + (
                    " when working with " + communication_context.lower()
                    if communication_context
                    else ""
                ),
                "examples of communication with comparable stakeholders, the purpose "
                "of the communication, and the outcome achieved",
            ),
            maximum=12,
            evidence=_matching_evidence(
                supporting_evidence_values, COMMUNICATION_PATTERNS
            ),
            resume_evidence_to_check=(
                "Communication with comparable audiences and stakeholders, including "
                "coordination outcomes and business context."
            ),
        )
    domain_knowledge_evidence = [
        evidence.strip()
        for evidence in [
            *request.responsibilities,
            *supporting_evidence_values,
        ]
        if DOMAIN_KNOWLEDGE_SIGNAL_PATTERN.search(evidence)
    ]
    domain_knowledge_labels = _detect_labels(
        "\n".join(domain_knowledge_evidence),
        COMPLIANCE_PATTERNS,
    )
    if domain_knowledge_evidence and criteria:
        add_criterion(
            "compliance",
            "compliance",
            SUPPORTING_CAPABILITY_LABELS["compliance"],
            compliance_importance,
            _hr_explanation(
                "applied knowledge of "
                + (
                    _human_join(domain_knowledge_labels)
                    if domain_knowledge_labels
                    else "the stated laws, regulations, standards, or formal requirements"
                ),
                "experience applying the named regulations, controls, audits, or "
                "standards in a comparable work environment",
            ),
            maximum=12,
            evidence=domain_knowledge_evidence,
            resume_evidence_to_check=(
                "Use of the named regulations, controls, audits, or standards in a "
                "comparable work environment."
            ),
        )
    if work_attitudes and criteria:
        add_criterion(
            "work-attitude",
            "work_attitude",
            SUPPORTING_CAPABILITY_LABELS["work_attitude"],
            attitude_importance,
            _hr_explanation(
                "work behaviours such as " + _human_join(work_attitudes),
                "examples that demonstrate these behaviours through ownership, "
                "collaboration, and completed work",
            ),
            maximum=8,
            evidence=_matching_evidence(
                supporting_evidence_values, WORK_ATTITUDE_PATTERNS
            ),
            resume_evidence_to_check=(
                "Examples showing these behaviours through ownership, collaboration, "
                "and completed work."
            ),
        )
    if certifications and criteria:
        named_certifications = [
            certification
            for certification in certifications
            if certification != "Professional certification"
        ]
        certification_requirement = (
            "professional certification in " + _human_join(named_certifications)
            if named_certifications
            else "a relevant professional certification"
        )
        add_criterion(
            "certification-match",
            "certification",
            SUPPORTING_CAPABILITY_LABELS["certification"],
            certification_importance,
            _hr_explanation(
                certification_requirement,
                "the certification title, issuing body, validity, and evidence of "
                "practical application",
            ),
            maximum=8,
            evidence=preferred_certification_evidence,
            resume_evidence_to_check=(
                "Certification relevance, validity, level, and evidence of practical "
                "application."
            ),
        )

    if education and academic_field and criteria:
        add_criterion(
            "education",
            "education",
            SUPPORTING_CAPABILITY_LABELS["education"],
            1,
            _hr_explanation(
                f"an academic background in {academic_field}",
                "a relevant field of study, coursework, academic projects, or "
                "specialised training connected to the role",
            ),
            maximum=8,
            evidence=[
                item.strip()
                for item in supporting_evidence_values
                if any(
                    re.search(pattern, item, flags=re.IGNORECASE)
                    for _, pattern in EDUCATION_RULES
                )
            ],
            resume_evidence_to_check=(
                "Field-of-study relevance, coursework, academic projects, and "
                "specialised training connected to the role."
            ),
        )

    if spoken_languages and criteria:
        add_criterion(
            "language",
            "language",
            SUPPORTING_CAPABILITY_LABELS["language"],
            1,
            _hr_explanation(
                "professional use of " + _human_join(spoken_languages),
                "written or verbal use of the required language in relevant work, "
                "customer, or stakeholder situations",
            ),
            maximum=6,
            evidence=_matching_evidence(supporting_evidence_values, LANGUAGE_RULES),
            resume_evidence_to_check=(
                "Professional use beyond minimum fluency, including relevant written "
                "and verbal contexts."
            ),
        )

    criteria = _consolidate_soft_criteria(
        _merge_overlapping_criteria(criteria)
    )
    criteria, omitted_count = _assign_evidence_weights(criteria)

    suggestions: dict = {"enabledFilters": []}

    def suggest(key: str, value: object) -> None:
        suggestions[key] = value
        suggestions["enabledFilters"].append(key)

    if experience_years is not None:
        suggest("minExperience", _experience_option(experience_years))
    if education and not education_is_alternative:
        suggest("educationLevel", education)
    if cgpa is not None and not education_is_alternative:
        suggest("minCGPA", cgpa)
    if spoken_languages:
        suggest("requiredLanguage", spoken_languages[0])
    if locations:
        suggest("requiredLocation", locations[0])

    warnings = []
    if omitted_count:
        warnings.append(
            f"{omitted_count} lower-priority criterion suggestion(s) were omitted to keep the review focused."
        )
    if len(criteria) < 4:
        warnings.append(
            "The JD contains evidence for fewer than four non-overlapping criteria. Review the JD or add a custom criterion."
        )

    return {
        "success": True,
        "data": {
            "criteria": criteria,
            "eligibilitySuggestions": suggestions,
        },
        "warnings": warnings,
    }
