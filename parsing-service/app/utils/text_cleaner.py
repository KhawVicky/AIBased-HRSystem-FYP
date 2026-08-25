"""Cleans text read from Excel cells."""

import re
from typing import Any


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def strip_value_prefix(value: str) -> str:
    return re.sub(r"^[\s:\-]+", "", clean_text(value)).strip()


def strip_section_number(value: str) -> str:
    return re.sub(r"^\s*\d+\s*[.)-]\s*", "", clean_text(value)).strip()


def normalized_heading(value: str) -> str:
    return re.sub(r"\s+", " ", strip_section_number(value).lower()).strip(" :.-")
