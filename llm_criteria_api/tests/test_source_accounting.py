from types import SimpleNamespace

from app.source_accounting import build_source_accounting, build_source_records


def _hard(*items):
    return SimpleNamespace(requirements=list(items), is_hard_only=lambda ref: ref == "Q1")


def test_source_records_preserve_sections_and_deduplicate_duplicate_qualifications():
    records = build_source_records(
        {
            "responsibilities": ["Investigate incidents."],
            "requirements": ["Diploma or Degree.", "Diploma or Degree."],
            "qualifications": ["Degree in Safety."],
        }
    )

    assert [(item.source_ref, item.source_id, item.section) for item in records] == [
        ("R1", "responsibilities-1", "responsibilities"),
        ("Q1", "requirements-1", "requirements"),
        ("Q2", "qualifications-1", "qualifications"),
    ]
    assert all(item.source_hash for item in records)


def test_source_accounting_preserves_multiple_identical_responsibility_sources():
    records = build_source_records(
        {"responsibilities": ["Prepare weekly reports.", "Prepare weekly reports."]}
    )
    audit = build_source_accounting(
        records,
        [
            {
                "criterionId": "criterion-1",
                "sourceText": "Prepare weekly reports.",
                "sourceIds": ["responsibilities-1", "responsibilities-2"],
            }
        ],
        _hard(),
    )

    assert [item["generatedCriterionIds"] for item in audit["sources"]] == [
        ["criterion-1"],
        ["criterion-1"],
    ]
    assert audit["valid"] is True


def test_source_accounting_accepts_compact_source_refs_as_lineage_inputs():
    records = build_source_records({"responsibilities": ["Review incident reports."]})
    audit = build_source_accounting(
        records,
        [{"criterionId": "criterion-1", "sourceRefs": ["R1"]}],
        _hard(),
    )

    assert audit["sources"][0]["generatedCriterionIds"] == ["criterion-1"]


def test_source_accounting_has_explicit_hard_and_grounding_outcomes():
    records = build_source_records(
        {
            "responsibilities": ["Perform other duties assigned by management."],
            "requirements": ["Minimum Diploma or Degree."],
        }
    )
    audit = build_source_accounting(
        records,
        [],
        _hard(SimpleNamespace(source_ref="Q1", kind="education_level")),
        generic_duty_detector=lambda text: "other duties" in text.casefold(),
    )

    by_ref = {item["sourceRef"]: item for item in audit["sources"]}
    assert by_ref["R1"]["processingOutcome"] == "not_mapped_grounding_safeguard"
    assert by_ref["Q1"]["processingOutcome"] == "hard_requirement_processing"
    assert audit["valid"] is True
