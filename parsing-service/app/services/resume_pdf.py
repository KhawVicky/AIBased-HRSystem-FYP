"""Robust text-layer PDF extraction for resume documents."""

from dataclasses import dataclass, replace
from io import BytesIO
import re
from typing import Any

from pypdf import PdfReader

from app.services.resume_sections import (
    clean_line,
    detect_section_heading,
    normalize_resume_line,
)


class ResumePdfError(ValueError):
    """Raised when a PDF cannot provide a meaningful text layer."""


EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])")
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACED_LETTER_RUN_RE = re.compile(
    r"(?<![A-Za-z])(?:[A-Za-z](?:[ \t]+[A-Za-z]){2,})(?![A-Za-z])"
)


@dataclass(frozen=True)
class ExtractionQuality:
    score: float
    signals: tuple[str, ...]
    useful_text_count: int
    spaced_character_sequence_count: int
    control_character_count: int
    recognized_section_count: int
    email_detected: bool
    suspicious: bool


@dataclass(frozen=True)
class PdfExtractionResult:
    raw_text: str
    cleaned_text: str
    page_count: int
    method: str = "pypdf_text"
    quality: ExtractionQuality | None = None
    fallback_attempted: bool = False
    fallback_selected: bool = False

    @property
    def diagnostics(self) -> dict[str, Any]:
        quality = self.quality
        return {
            "extractionQualityScore": quality.score if quality else None,
            "extractionQualitySignals": list(quality.signals) if quality else [],
            "extractionUsefulTextCount": quality.useful_text_count if quality else None,
            "spacedCharacterSequenceCount": (
                quality.spaced_character_sequence_count if quality else 0
            ),
            "controlCharacterCount": quality.control_character_count if quality else 0,
            "recognizedSectionCount": quality.recognized_section_count if quality else 0,
            "emailDetected": quality.email_detected if quality else False,
            "extractionQualitySuspicious": quality.suspicious if quality else False,
            "fallbackAttempted": self.fallback_attempted,
            "fallbackSelected": self.fallback_selected,
        }


def _safe_raw_text(text: str) -> str:
    """Remove invalid controls while retaining readable line boundaries."""

    return "\n".join(normalize_resume_line(line) for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))


def clean_resume_text(text: str) -> str:
    """Normalize layout noise while retaining line and section boundaries."""

    cleaned_lines: list[str] = []
    previous_blank = False
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = clean_line(raw_line)
        if not line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue
        cleaned_lines.append(line)
        previous_blank = False

    return "\n".join(cleaned_lines).strip()


def _recognized_section_count(text: str) -> int:
    sections = {
        heading[0]
        for line in text.splitlines()
        if (heading := detect_section_heading(line)) is not None
    }
    return len(sections)


def assess_extraction_quality(text: str) -> ExtractionQuality:
    """Score deterministic signals that indicate corrupted PDF extraction."""

    control_count = len(_CONTROL_CHARACTER_RE.findall(text))
    spaced_count = len(_SPACED_LETTER_RUN_RE.findall(text))
    normalized = clean_resume_text(text)
    useful_text_count = len(re.sub(r"[^\w@.+-]", "", normalized, flags=re.UNICODE))
    words = re.findall(r"\b[\w@.+-]+\b", normalized, flags=re.UNICODE)
    single_letter_tokens = re.findall(r"(?<!\w)[A-Za-z](?!\w)", text)
    single_letter_ratio = len(single_letter_tokens) / max(len(words), 1)
    non_empty_lines = [line for line in normalized.splitlines() if line.strip()]
    fragmented_lines = sum(
        1 for line in non_empty_lines if len(re.findall(r"[A-Za-z0-9]", line)) <= 2
    )
    section_count = _recognized_section_count(normalized)
    email_detected = bool(EMAIL_RE.search(normalized))

    score = 100.0
    signals: list[str] = []
    if spaced_count:
        score -= min(45.0, 10.0 + spaced_count * 0.35)
        signals.append("character_spacing_corruption")
    if useful_text_count < 80:
        score -= 30.0
        signals.append("very_low_useful_text")
    elif useful_text_count < 180:
        score -= 15.0
        signals.append("low_useful_text")
    if control_count:
        score -= min(15.0, control_count * 2.0)
        signals.append("control_characters")
    if single_letter_ratio > 0.35:
        score -= 20.0
        signals.append("fragmented_word_tokens")
    if useful_text_count > 300 and section_count < 2:
        score -= 20.0
        signals.append("section_headings_not_recognized")
    if "@" in normalized and not email_detected:
        score -= 15.0
        signals.append("email_not_recoverable")
    if len(non_empty_lines) >= 20 and fragmented_lines / len(non_empty_lines) > 0.35:
        score -= 10.0
        signals.append("excessive_fragmented_lines")

    suspicious = (
        score < 78.0
        or spaced_count >= 3
        or control_count >= 5
        or (useful_text_count > 300 and section_count < 2)
    )
    return ExtractionQuality(
        score=max(0.0, round(score, 1)),
        signals=tuple(dict.fromkeys(signals)),
        useful_text_count=useful_text_count,
        spaced_character_sequence_count=spaced_count,
        control_character_count=control_count,
        recognized_section_count=section_count,
        email_detected=email_detected,
        suspicious=suspicious,
    )


def _extract_pypdf(content: bytes) -> tuple[str, int]:
    reader = PdfReader(BytesIO(content))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages)


def _block_text(block: tuple[Any, ...]) -> str:
    return str(block[4] or "").strip() if len(block) > 4 else ""


def _is_text_block(block: tuple[Any, ...]) -> bool:
    return bool(_block_text(block)) and (len(block) < 7 or int(block[6]) == 0)


def _first_heading_y(blocks: list[tuple[Any, ...]]) -> float | None:
    positions = [
        float(block[1])
        for block in blocks
        if any(detect_section_heading(line) for line in _block_text(block).splitlines())
    ]
    return min(positions) if positions else None


def _layout_page_text(page: Any) -> str:
    blocks = [tuple(block) for block in page.get_text("blocks", sort=False) if _is_text_block(tuple(block))]
    if not blocks:
        return ""

    first_heading_y = _first_heading_y(blocks)
    header_indices = {
        index
        for index, block in enumerate(blocks)
        if first_heading_y is not None and float(block[1]) < first_heading_y - 0.5
    }
    body_indices = [index for index in range(len(blocks)) if index not in header_indices]
    page_width = float(page.rect.width)
    column_threshold = page_width * 0.36
    left_indices = [
        index for index in body_indices if float(blocks[index][2]) <= column_threshold
    ]
    right_indices = [
        index for index in body_indices if float(blocks[index][0]) >= column_threshold
    ]
    has_two_columns = (
        len(left_indices) >= 2
        and len(right_indices) >= 2
        and min(float(blocks[index][0]) for index in right_indices)
        - max(float(blocks[index][2]) for index in left_indices)
        >= page_width * 0.04
    )

    def sort_indices(indices: list[int]) -> list[int]:
        return sorted(indices, key=lambda index: (float(blocks[index][1]), float(blocks[index][0])))

    if has_two_columns:
        assigned = set(left_indices) | set(right_indices) | header_indices
        other_indices = [index for index in body_indices if index not in assigned]
        ordered = (
            sort_indices(list(header_indices))
            + sort_indices(left_indices)
            + sort_indices(other_indices)
            + sort_indices(right_indices)
        )
    else:
        ordered = sort_indices(list(range(len(blocks))))

    return "\n".join(_block_text(blocks[index]) for index in ordered)


def _extract_pymupdf(content: bytes) -> tuple[str, int]:
    try:
        import pymupdf
    except ImportError as error:  # pragma: no cover - packaging failure path
        raise ResumePdfError("PyMuPDF layout extraction is not installed") from error

    try:
        document = pymupdf.open(stream=content, filetype="pdf")
        page_texts = [_layout_page_text(page) for page in document]
        return "\n\n".join(page_texts), len(document)
    except Exception as error:  # PyMuPDF exposes several parser-specific errors.
        raise ResumePdfError("The PDF layout extractor could not read the document") from error


def _build_result(raw_text: str, page_count: int, method: str) -> PdfExtractionResult:
    quality = assess_extraction_quality(raw_text)
    safe_raw = _safe_raw_text(raw_text)
    cleaned = clean_resume_text(safe_raw)
    meaningful_text = re.sub(r"[^\w@.+-]", "", cleaned, flags=re.UNICODE)
    if len(meaningful_text) < 20:
        raise ResumePdfError(
            "The PDF does not contain a meaningful text layer; OCR is not enabled for resume-parsing-v1"
        )
    return PdfExtractionResult(
        raw_text=safe_raw,
        cleaned_text=cleaned,
        page_count=page_count,
        method=method,
        quality=quality,
    )


def _quality_rank(result: PdfExtractionResult) -> tuple[float, int, int, int]:
    quality = result.quality
    if quality is None:
        return (0.0, 0, 0, 0)
    return (
        quality.score,
        quality.useful_text_count,
        quality.recognized_section_count,
        -quality.spaced_character_sequence_count,
    )


def extract_pdf_text(content: bytes) -> PdfExtractionResult:
    """Select pypdf or a layout-aware PyMuPDF extraction deterministically."""

    if not content:
        raise ResumePdfError("The uploaded PDF is empty")

    try:
        primary_raw, page_count = _extract_pypdf(content)
        primary = _build_result(primary_raw, page_count, "pypdf_text")
    except ResumePdfError:
        raise
    except Exception as error:  # pypdf exposes several parser-specific errors.
        raise ResumePdfError("The uploaded PDF could not be read") from error

    if not primary.quality or not primary.quality.suspicious:
        return primary

    try:
        fallback_raw, fallback_page_count = _extract_pymupdf(content)
        fallback = _build_result(fallback_raw, fallback_page_count, "pymupdf_layout")
    except ResumePdfError:
        return replace(primary, fallback_attempted=True)

    if _quality_rank(fallback) > _quality_rank(primary):
        return replace(fallback, fallback_attempted=True, fallback_selected=True)
    return replace(primary, fallback_attempted=True)
