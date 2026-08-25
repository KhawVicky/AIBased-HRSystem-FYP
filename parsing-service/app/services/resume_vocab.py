"""Conservative vocabularies used only for explicit text matching."""

import re


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "React": ("react", "react.js", "reactjs"),
    "TypeScript": ("typescript",),
    "Node.js": ("node.js", "nodejs", "node js"),
    "JavaScript": ("javascript", "java script"),
    "Python": ("python",),
    "Java": ("java",),
    "C#": ("c#", "c sharp"),
    "C++": ("c++",),
    "PHP": ("php",),
    "SQL": ("sql",),
    "HTML": ("html",),
    "CSS": ("css",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "GCP": ("gcp", "google cloud platform"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Git": ("git", "github", "gitlab"),
    "Figma": ("figma",),
    "Excel": ("microsoft excel", "excel"),
    "Power BI": ("power bi", "powerbi"),
    "SAP": ("sap",),
    "Laravel": ("laravel",),
    "Django": ("django",),
    "FastAPI": ("fastapi",),
    "Spring Boot": ("spring boot",),
    "REST API": ("rest api", "restful api"),
    "GraphQL": ("graphql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb", "mongo db"),
    "Pandas": ("pandas",),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Selenium": ("selenium",),
    "Jira": ("jira",),
    "Agile": ("agile",),
    "Recruitment": ("recruitment", "recruiting"),
    "Talent Acquisition": ("talent acquisition",),
    "Employee Relations": ("employee relations",),
    "Payroll": ("payroll",),
    "Immigration Documentation": ("immigration documentation",),
    "Foreign Worker Management": ("foreign worker", "foreign workers"),
    "Performance Management": ("performance management",),
    "Onboarding": ("onboarding",),
    "Project Management": ("project management",),
    "Data Analysis": ("data analysis", "data analytics"),
}

GENERIC_SKILLS = {
    "hardworking",
    "responsible",
    "team player",
    "motivated",
    "willing to learn",
    "good attitude",
    "communication skills",
    "leadership skills",
}

DOMAIN_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("software development", ("software developer", "software development", "web developer", "programmer")),
    ("frontend engineering", ("frontend", "front-end", "ui developer", "react developer")),
    ("backend engineering", ("backend", "back-end", "api developer")),
    ("human resources", ("human resources", "hr executive", "hr manager", "recruitment", "employee relations")),
    ("finance and accounting", ("finance", "accounting", "accountant", "audit")),
    ("sales", ("sales", "business development", "account manager")),
    ("marketing", ("marketing", "digital marketing", "content marketing")),
    ("operations", ("operations", "supply chain", "logistics", "procurement")),
    ("data and analytics", ("data analyst", "data science", "analytics", "business intelligence")),
    ("education", ("teacher", "lecturer", "education", "academic")),
)

LANGUAGE_NAMES = (
    "Bahasa Malaysia",
    "Bahasa Melayu",
    "Mandarin",
    "English",
    "Malay",
    "Chinese",
    "Cantonese",
    "Tamil",
    "Hindi",
    "Arabic",
    "Japanese",
    "Korean",
    "French",
    "German",
    "Spanish",
    "Italian",
    "Indonesian",
    "Thai",
    "Vietnamese",
)


def normalise_skill_name(value: str) -> str:
    compact = re.sub(r"[^a-z0-9+#.]+", "", value.lower())
    for canonical, aliases in SKILL_ALIASES.items():
        if compact == re.sub(r"[^a-z0-9+#.]+", "", canonical.lower()):
            return canonical
        if any(compact == re.sub(r"[^a-z0-9+#.]+", "", alias.lower()) for alias in aliases):
            return canonical
    return re.sub(r"\s+", " ", value.strip())


def _pattern_for(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    if alias[0].isalnum() and alias[-1].isalnum():
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


SKILL_PATTERNS = {
    canonical: tuple(_pattern_for(alias) for alias in aliases)
    for canonical, aliases in SKILL_ALIASES.items()
}


def explicit_skills_in_text(text: str) -> list[str]:
    found: list[str] = []
    for canonical, patterns in SKILL_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            found.append(canonical)
    return found


def detect_domain(text: str) -> str | None:
    value = text.lower()
    for domain, patterns in DOMAIN_PATTERNS:
        if any(pattern in value for pattern in patterns):
            return domain
    return None

