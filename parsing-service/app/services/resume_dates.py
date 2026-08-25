"""Deterministic date and employment-duration helpers."""

from dataclasses import dataclass
from datetime import date
import re


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

DATE_TOKEN_PATTERN = (
    r"(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s*[,.]?\s*\d{4}"
    r"|(?:0?[1-9]|1[0-2])\s*[/.-]\s*\d{4}"
    r"|\d{4}"
    r")"
)
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{DATE_TOKEN_PATTERN})\s*(?:-|–|—|to|until)\s*"
    rf"(?P<end>{DATE_TOKEN_PATTERN}|Present|Current|Now)",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(
    rf"(?P<value>{DATE_TOKEN_PATTERN}|Present|Current|Now)", re.IGNORECASE
)


@dataclass(frozen=True)
class DatePoint:
    year: int
    month: int | None
    precision: str


@dataclass(frozen=True)
class DateRange:
    start: DatePoint
    end: DatePoint | None
    is_current: bool


def _normalise_token(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().replace(",", " "))


def parse_date_token(token: str) -> DatePoint | None:
    """Parse supported tokens without fabricating month precision."""

    value = _normalise_token(token).lower()
    if value in {"present", "current", "now"}:
        return None

    year_match = re.search(r"(19|20)\d{2}", value)
    if not year_match:
        return None
    year = int(year_match.group(0))

    month_match = re.match(r"([a-z]+)\s+(?:\d{1,2}\s+)?\d{4}$", value)
    if month_match and month_match.group(1) in MONTHS:
        return DatePoint(year=year, month=MONTHS[month_match.group(1)], precision="month")

    numeric_match = re.match(r"(\d{1,2})\s*[/.-]\s*(\d{4})$", value)
    if numeric_match:
        month = int(numeric_match.group(1))
        if 1 <= month <= 12:
            return DatePoint(year=year, month=month, precision="month")

    return DatePoint(year=year, month=None, precision="year")


def parse_date_range(text: str) -> DateRange | None:
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None

    start = parse_date_token(match.group("start"))
    if start is None:
        return None
    end_text = match.group("end")
    is_current = end_text.lower() in {"present", "current", "now"}
    end = None if is_current else parse_date_token(end_text)
    if not is_current and end is None:
        return None
    return DateRange(start=start, end=end, is_current=is_current)


def normalise_date(point: DatePoint | None) -> str | None:
    if point is None:
        return None
    if point.month is None:
        return f"{point.year:04d}"
    return f"{point.year:04d}-{point.month:02d}"


def _month_index(point: DatePoint, *, start_boundary: bool) -> int:
    month = point.month if point.month is not None else (1 if start_boundary else 12)
    return point.year * 12 + month - 1


def duration_months(date_range: DateRange | None, as_of: date | None = None) -> int | None:
    if date_range is None:
        return None
    as_of = as_of or date.today()
    start_index = _month_index(date_range.start, start_boundary=True)
    if date_range.is_current:
        end_index = as_of.year * 12 + as_of.month - 1
    elif date_range.end is not None:
        end_index = _month_index(date_range.end, start_boundary=False)
    else:
        return None
    if end_index < start_index:
        return None
    return end_index - start_index + 1


def duration_confidence(date_range: DateRange | None) -> str:
    if date_range is None:
        return "unresolved"
    if date_range.start.precision == "month" and (
        date_range.is_current or (date_range.end and date_range.end.precision == "month")
    ):
        return "month"
    return "year"


def range_month_interval(
    date_range: DateRange | None, as_of: date | None = None
) -> tuple[int, int] | None:
    """Return an inclusive month interval for unique covered-time calculation."""

    if date_range is None:
        return None
    as_of = as_of or date.today()
    start_index = _month_index(date_range.start, start_boundary=True)
    if date_range.is_current:
        end_index = as_of.year * 12 + as_of.month - 1
    elif date_range.end is not None:
        end_index = _month_index(date_range.end, start_boundary=False)
    else:
        return None
    return (start_index, end_index) if end_index >= start_index else None


def unique_covered_months(ranges: list[DateRange], as_of: date | None = None) -> int:
    intervals = [range_month_interval(item, as_of) for item in ranges]
    intervals = [item for item in intervals if item is not None]
    if not intervals:
        return 0

    intervals.sort()
    total = 0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
            continue
        total += current_end - current_start + 1
        current_start, current_end = start, end
    return total + current_end - current_start + 1

