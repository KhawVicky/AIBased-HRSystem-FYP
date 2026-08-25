"""Extraction prompt exports for live and frozen API callers."""

from .extraction_prompt import (  # noqa: F401
    ALLOWED_CRITERION_TYPES,
    SYSTEM_PROMPT as LIVE_SYSTEM_PROMPT,
    build_extraction_messages,
    build_extraction_retry_messages,
)

from .frozen_pipeline import (  # noqa: F401
    SYSTEM_PROMPT as FROZEN_SYSTEM_PROMPT,
    build_consolidation_messages,
    build_section_messages,
    generate_json_retry_output,
    generate_section_raw_output,
)

# Keep the historical import name available for legacy callers. The live
# CriteriaPipeline imports LIVE_SYSTEM_PROMPT/build_extraction_messages
# explicitly and never changes frozen parity behaviour.
SYSTEM_PROMPT = FROZEN_SYSTEM_PROMPT
