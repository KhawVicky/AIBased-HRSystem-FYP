# Frozen Notebook Parity Audit

## Migration status

`app/frozen_pipeline.py` is a static export from the active Kaggle runtime cells that produced the five frozen fixture records. [kaggle_frozen_pipeline_manifest.json](kaggle_frozen_pipeline_manifest.json) records the 50 exported functions, their source hashes, referenced globals, constants, package versions, generation settings, and the Kaggle runtime self-parity result. The API never reads or executes a notebook at runtime.

| Notebook stage | Frozen notebook function/cell | API location | Status | Difference |
|---|---|---|---|---|
| Generic-duty filtering | `filter_generic_duties` / cell 11 | `frozen_pipeline.filter_generic_duties` | exact | None |
| Responsibilities and requirements extraction | `extract_soft_criteria_llm` / cell 13 | `frozen_pipeline.extract_soft_criteria_llm` | exact | None |
| Prompt and section guidance | `SYSTEM_PROMPT`, `build_section_messages` / cells 9, 5 | `frozen_pipeline` | exact | None |
| JSON parsing, repair and retry prompt | `extract_json_object`, `section_output_retry_reason`, `generate_json_retry_output` / cells 11, 13 | `frozen_pipeline` | exact | None |
| Grounding | `find_grounded_source`, `source_grounding_score` / cell 11 | `frozen_pipeline` | exact | None |
| Name correction and morphology | final `validate_section_output` overrides / cell 12 | `frozen_pipeline.validate_section_output` | exact | None |
| Safe type remapping | `_safe_recover_type` / cell 12 | `frozen_pipeline._safe_recover_type` | exact | None |
| Language and certification boundaries | `validate_section_output` / cells 11, 12 | `frozen_pipeline` | exact | None |
| Education and narrow fallbacks | `add_*_fallback` / cell 11 | `frozen_pipeline` | exact | None |
| Deduplication and consolidation | `merge_duplicate_criteria`, `apply_consolidation`, `finalise_extraction` / cell 11 | `frozen_pipeline` | exact | The frozen count validation already has `limitEnabled: False`; no count trigger is enabled. |
| Criterion/source metadata | `assign_stable_criterion_ids`, `finalise_extraction` / cell 11 | `frozen_pipeline` | exact | None |
| Descriptions, evidence rules, warnings and weights | `DEFAULT_*`, `assign_default_weights`, `finalise_extraction` / cell 11 | `frozen_pipeline` | exact | None |
| FastAPI model startup and response adaptation | N/A | `model_loader.py`, `main.py`, `pipeline.py` | intentional adapter | Startup dependency injection and HTTP serialization only. |

## Exact-output fixtures

`tests/fixtures/frozen_cached_outputs.json` contains the five real cached raw-output records exported from the same Kaggle runtime. The Kaggle self-check reached `5/5`, and the local `test_frozen_cached_output_parity` fixture test reached `5/5`.

When populated, the test requires exact equality for the final criteria, source metadata, warnings, weights, fallback recoveries, rejection diagnostics, and grounding scores.
