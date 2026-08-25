"""Section detection and small text helpers for varied resume layouts."""

from collections import OrderedDict
import re


SECTION_DISPLAY_NAMES = {
    "header": "Header",
    "contact": "Contact",
    "profile": "Profile",
    "education": "Education",
    "experience": "Work Experience",
    "skills": "Skills",
    "certifications": "Certifications",
    "languages": "Languages",
    "projects": "Projects",
    "achievements": "Achievements",
}

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "contact": (
        "contact",
        "contact information",
        "personal information",
        "personal details",
    ),
    "profile": (
        "profile",
        "summary",
        "career summary",
        "professional summary",
        "objective",
        "career objective",
        "professional profile",
        "about me",
    ),
    "education": (
        "education",
        "academic background",
        "academic record",
        "academics",
        "qualification",
        "qualifications",
        "educational background",
    ),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "employment history",
        "career history",
        "professional experience",
        "professional background",
        "work history",
        "employment record",
    ),
    "skills": (
        "skills",
        "tech skills",
        "technical skills",
        "core skills",
        "key skills",
        "competencies",
        "technical competencies",
        "areas of expertise",
    ),
    "certifications": (
        "certifications",
        "certificates",
        "professional certifications",
        "credentials",
        "licenses and certifications",
    ),
    "languages": (
        "languages",
        "language skills",
        "spoken languages",
    ),
    "projects": (
        "project",
        "projects",
        "selected projects",
        "academic projects",
        "project experience",
    ),
    "achievements": (
        "achievements",
        "awards",
        "awards and achievements",
        "honors and awards",
        "accomplishments",
    ),
}

_ALIASES_BY_NORMALISED = {
    re.sub(r"\s+", " ", alias.strip().lower()): canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}
_SORTED_ALIASES = sorted(_ALIASES_BY_NORMALISED, key=len, reverse=True)

_PROGRAMMING_LANGUAGE_NAMES = {
    "c", "c#", "c++", "css", "dart", "go", "html", "java", "javascript",
    "kotlin", "php", "python", "ruby", "rust", "sql", "swift", "typescript",
}
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACED_LETTER_RUN_RE = re.compile(
    r"(?<![A-Za-z])(?:[A-Za-z](?:[ \t]+[A-Za-z]){2,})(?![A-Za-z])"
)
_SPACED_DIGIT_RUN_RE = re.compile(r"(?<!\d)(?:\d[ \t]+){3,}\d(?!\d)")


def collapse_spaced_characters(value: str) -> str:
    """Collapse character-level PDF spacing without removing normal word spaces."""

    def replace(match: re.Match[str]) -> str:
        parts = re.split(r"[ \t]{2,}", match.group(0).strip())
        collapsed: list[str] = []
        for part in parts:
            tokens = part.split()
            if len(tokens) >= 3 and all(len(token) == 1 and token.isalpha() for token in tokens):
                collapsed.append("".join(tokens))
            else:
                collapsed.append(part)
        return " ".join(collapsed)

    return _SPACED_LETTER_RUN_RE.sub(replace, value)


def collapse_spaced_digits(value: str) -> str:
    """Recover phone/date digit runs split by a text extractor."""

    return _SPACED_DIGIT_RUN_RE.sub(
        lambda match: re.sub(r"[ \t]+", "", match.group(0)),
        value,
    )


def normalize_resume_line(line: str) -> str:
    """Apply conservative, reusable normalization to one extracted line."""

    value = collapse_spaced_characters(line)
    value = collapse_spaced_digits(value)
    value = re.sub(r"(?<=\+)\s+(?=\d)", "", value)
    value = re.sub(r"\s+([@.])", r"\1", value)
    value = re.sub(r"([@.])\s+", r"\1", value)
    value = _CONTROL_CHARACTER_RE.sub(" ", value)
    value = value.replace("\u00a0", " ").replace("\u00ad", "")
    value = re.sub(r"[ \t]+", " ", value).strip()
    if value and value[0] in {"\u2022", "\u25aa", "\u25e6", "\u2023", "\u00b7"}:
        value = "- " + value[1:].lstrip()
    return value


def clean_line(line: str) -> str:
    return normalize_resume_line(line)


def strip_bullet(line: str) -> str:
    value = clean_line(line)
    return re.sub(r"^(?:[-*+•▪◦‣]|\(?\d+[.)]|[a-zA-Z][.)])\s+", "", value).strip()


def _normalise_heading(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[|:]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -–—")


def detect_section_heading(line: str) -> tuple[str, str] | None:
    """Return a canonical section and optional inline content."""

    value = clean_line(line)
    if not value or value.startswith(("-", "*", "•", "▪")):
        return None

    normalised = _normalise_heading(value)
    exact = _ALIASES_BY_NORMALISED.get(normalised)
    if exact:
        return exact, ""

    # Support Skills: Python, SQL and similar compact resume headings.
    for alias in _SORTED_ALIASES:
        match = re.match(rf"^{re.escape(alias)}\s*(?::|\||-|–|—)\s*(.+)$", normalised)
        if match:
            return _ALIASES_BY_NORMALISED[alias], match.group(1).strip()

    # A heading may carry a small suffix such as WORK EXPERIENCE / 2019-2024.
    for alias in _SORTED_ALIASES:
        if normalised.startswith(alias + " "):
            remainder = normalised[len(alias) :].strip(" -–—:/")
            if remainder and len(remainder) <= 40 and not re.search(r"[.!?]", remainder):
                return _ALIASES_BY_NORMALISED[alias], remainder
    return None


def segment_resume_sections(text: str) -> OrderedDict[str, str]:
    """Segment text into canonical sections while preserving their content."""

    sections: OrderedDict[str, list[str]] = OrderedDict()
    current = "header"
    sections[current] = []
    for raw_line in text.splitlines():
        heading = detect_section_heading(raw_line)
        if heading:
            current, inline_content = heading
            sections.setdefault(current, [])
            if inline_content:
                sections[current].append(inline_content)
            continue
        sections.setdefault(current, []).append(clean_line(raw_line))

    return OrderedDict(
        (section, "\n".join(lines).strip())
        for section, lines in sections.items()
        if "\n".join(lines).strip()
    )


def non_empty_lines(text: str) -> list[str]:
    return [clean_line(line) for line in text.splitlines() if clean_line(line)]


def is_generic_soft_skill(value: str) -> bool:
    normalised = re.sub(r"[^a-z ]", "", value.lower())
    generic = {
        "hardworking",
        "hard working",
        "responsible",
        "team player",
        "motivated",
        "willing to learn",
        "good attitude",
        "able to work under pressure",
        "fast learner",
        "positive attitude",
        "excellent communication",
        "communication skills",
        "leadership skills",
    }
    return normalised.strip() in generic


def meaningful_tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9+#.]+", value.lower())
    stopwords = {
        "and",
        "the",
        "with",
        "for",
        "from",
        "using",
        "this",
        "that",
        "role",
        "work",
        "experience",
        "responsible",
        "managed",
        "manage",
    }
    return {token for token in tokens if token not in stopwords and len(token) > 2}


def stem_token(token: str) -> str:
    value = token.lower()
    for suffix in ("ing", "ed", "es", "s"):
        if value.endswith(suffix) and len(value) - len(suffix) >= 4:
            return value[: -len(suffix)]
    return value


# The definitions below intentionally sit after the legacy helpers so the
# parser uses the safer normalization/context rules while older imports keep
# their names and signatures compatible.
def strip_bullet(line: str) -> str:
    value = clean_line(line)
    return re.sub(
        r"^(?:[-*+\u2022\u25aa\u25e6\u2023\u00b7]|\(?\d+[.)]|[a-zA-Z][.)])\s+",
        "",
        value,
    ).strip()


def _normalise_heading(value: str) -> str:
    value = collapse_spaced_characters(value).strip().lower()
    value = re.sub(r"^\s*\d+\s*[.)-]\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -\u2013\u2014")


def detect_section_heading(
    line: str,
    *,
    current_section: str | None = None,
) -> tuple[str, str] | None:
    """Return a canonical section and optional inline content."""

    value = clean_line(line)
    if not value or value.startswith(("-", "*")):
        return None

    normalised = _normalise_heading(value)
    exact_key = re.sub(r"[|:]+", " ", normalised)
    exact_key = re.sub(r"\s+", " ", exact_key).strip(" -\u2013\u2014")
    exact = _ALIASES_BY_NORMALISED.get(exact_key)
    if exact:
        return exact, ""

    for alias in _SORTED_ALIASES:
        match = re.match(
            rf"^{re.escape(alias)}\s*(?::|\||-|\u2013|\u2014)\s*(.+)$",
            normalised,
        )
        if not match:
            continue
        canonical = _ALIASES_BY_NORMALISED[alias]
        inline = match.group(1).strip()
        inline_tokens = {
            token.casefold()
            for token in re.findall(r"[A-Za-z][A-Za-z+#]*", inline)
        }
        if canonical == "languages" and (
            current_section == "skills"
            or bool(inline_tokens & _PROGRAMMING_LANGUAGE_NAMES)
        ):
            return None
        return canonical, inline

    for alias in _SORTED_ALIASES:
        if normalised.startswith(alias + " "):
            remainder = normalised[len(alias) :].strip(" -\u2013\u2014:/")
            if remainder and len(remainder) <= 40 and not re.search(r"[.!?]", remainder):
                return _ALIASES_BY_NORMALISED[alias], remainder
    return None


def segment_resume_sections(text: str) -> OrderedDict[str, str]:
    """Segment normalized text while respecting contextual inline headings."""

    sections: OrderedDict[str, list[str]] = OrderedDict()
    current = "header"
    sections[current] = []
    for raw_line in text.splitlines():
        heading = detect_section_heading(raw_line, current_section=current)
        if heading:
            current, inline_content = heading
            sections.setdefault(current, [])
            if inline_content:
                sections[current].append(inline_content)
            continue
        sections.setdefault(current, []).append(clean_line(raw_line))

    return OrderedDict(
        (section, "\n".join(lines).strip())
        for section, lines in sections.items()
        if "\n".join(lines).strip()
    )
