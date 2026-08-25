"""Transport-only normalisation for model responses.

The frozen parser remains responsible for JSON parsing and all downstream
validation. This helper only unwraps one complete outer Markdown code fence.
"""

from __future__ import annotations

import re


_OUTER_FENCE_PATTERN = re.compile(
    r"^```[ \t]*(?:(?P<language>json)[ \t]*)?\r?\n"
    r"(?P<body>.*?)"
    r"\r?\n```[ \t]*$",
    flags=re.IGNORECASE | re.DOTALL,
)


def normalise_model_output(raw_output: str) -> tuple[str, bool]:
    """Return ``raw_output`` with at most one complete outer fence removed.

    A fence is removed only when it wraps the entire trimmed response. Text
    before or after a fence therefore remains untouched and is still rejected
    by the frozen JSON parser when it is not valid JSON.
    """

    trimmed = raw_output.strip()
    match = _OUTER_FENCE_PATTERN.fullmatch(trimmed)
    if not match:
        return trimmed, False
    return match.group("body").strip(), True
