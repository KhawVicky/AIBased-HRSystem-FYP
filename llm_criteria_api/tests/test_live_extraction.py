import json
import re
from types import SimpleNamespace

from app.extraction_prompt import (
    build_extraction_messages,
    build_extraction_retry_messages,
    build_responsibility_recovery_messages,
    build_semantic_consolidation_messages,
)
from app.extraction_schema import normalise_extraction_output
from app.pipeline import CriteriaPipeline


def test_live_prompt_contains_complete_jd_and_forbids_model_weights():
    job = {
        "jobTitle": "Software Engineer",
        "department": "Information Technology",
        "responsibilities": ["Develop service integrations."],
        "requirements": ["Three years of API experience is preferred."],
        "qualifications": ["A degree in Computer Science is preferred."],
    }

    messages = build_extraction_messages(job)
    system = messages[0]["content"]
    user = messages[1]["content"]

    assert "candidateCriteria" in user
    assert '"importance": "<high, medium, or low>"' in user
    assert '"sourceRef": "R1"' in user
    assert '"text": "Develop service integrations."' in user
    assert '"sourceRef": "Q1"' in user
    assert '"text": "Three years of API experience is preferred."' in user
    assert '"sourceRef": "Q2"' in user
    assert "Develop service integrations." in user
    assert "A degree in Computer Science is preferred." in user
    assert "Do not calculate percentage weights." in system
    assert "do not return suggestedweight" in user.casefold()
    assert "eligibility filters" in user
    assert "Complete JD evidence" in user
    assert "valid for a supplied source to remain unmapped" in user
    assert "CORE" not in system
    assert "SUPPORTING" not in system
    assert "IGNORE" not in system


def test_live_prompt_uses_generic_source_accounting_without_examples():
    messages = build_extraction_messages(
        {
            "jobTitle": "Planner",
            "department": "Operations",
            "responsibilities": ["Coordinate production schedules."],
            "requirements": ["Diploma or Degree."],
        }
    )
    system = messages[0]["content"]

    assert "few-shot" not in system.casefold()
    assert "Capability-formation process" in system
    assert "source set is the complete responsibilities" in system
    normalised_system = " ".join(system.casefold().split())
    assert "shared verbs, departments or broad themes never justify a merge" in normalised_system
    assert "one normal resume example would ordinarily demonstrate it" in normalised_system
    assert "supported by every referenced sentence" in normalised_system
    assert "bare generic name" in system
    assert "HR remains the final decision maker" in system
    assert "generic assigned-duty boilerplate" in messages[1]["content"]

    for forbidden_title in (
        "HR Manager",
        "Software Engineer",
        "Accounts Payable Executive",
        "Sales Executive",
        "QA Engineer",
        "Administrative Executive",
    ):
        assert forbidden_title not in system

    assert '"candidateCriteria"' in messages[1]["content"]
    assert '"sourceRefs"' in messages[1]["content"]
    assert '"ignoredSourceRefs"' not in messages[1]["content"]
    assert "capabilityGroup" not in messages[1]["content"]
    assert '"sourceRefs": [\n      "R1"' not in messages[1]["content"]
    assert 'Available source-reference checklist:\n["R1", "Q1"]' in messages[1]["content"]
    assert "Never copy placeholder text" in messages[1]["content"]


def test_semantic_consolidation_prompt_is_isolated_and_conservative():
    messages = build_semantic_consolidation_messages(
        [
            {
                "criterionId": "criterion-1",
                "type": "relevant_skill",
                "name": "Contract Review",
                "sourceIds": ["responsibilities-1"],
                "sourceText": "Review contract requests.",
            },
            {
                "criterionId": "criterion-2",
                "type": "relevant_skill",
                "name": "Contract Approval",
                "sourceIds": ["responsibilities-2"],
                "sourceText": "Verify contract approvals.",
            },
        ]
    )

    assert "conservative consolidation review" in messages[0]["content"].casefold()
    assert "exactly two supplied criterion IDs" in messages[0]["content"]
    assert "criterion-1" in messages[1]["content"]
    assert '"groups"' in messages[1]["content"]
    assert '"renames"' in messages[1]["content"]


def test_retry_prompt_focuses_missing_refs_and_preserves_valid_work():
    job = {
        "jobTitle": "Service Lead",
        "department": "Operations",
        "responsibilities": [
            "Investigate service failures.",
            "Resolve confirmed service failures.",
        ],
        "requirements": [],
    }

    messages = build_extraction_retry_messages(
        job,
        '{"candidateCriteria": [], "ignoredSourceRefs": []}',
        {"R2"},
    )
    user = messages[1]["content"]

    assert 'unaccounted for:\n["R2"]' in user
    assert "Preserve its valid criteria and source-reference decisions" in user
    assert "complete corrected JSON response, not a patch" in user


def test_retry_prompt_identifies_refs_attached_only_to_unsupported_names():
    job = {
        "jobTitle": "Service Lead",
        "department": "Operations",
        "responsibilities": [
            "Identify new enterprise customers.",
            "Develop new service opportunities.",
        ],
        "requirements": [],
    }

    messages = build_extraction_retry_messages(
        job,
        '{"candidateCriteria": [], "ignoredSourceRefs": []}',
        set(),
        {"R1"},
    )
    user = messages[1]["content"]

    assert 'supported by that sentence:\n["R1"]' in user
    assert "move it to a correctly named criterion" in user


def test_responsibility_recovery_prompt_is_bounded_to_uncovered_sources():
    messages = build_responsibility_recovery_messages(
        {
            "jobTitle": "Service Lead",
            "department": "Operations",
        },
        {
            "R2": "Resolve confirmed service failures.",
            "R3": "Report recurring failure trends.",
        },
        [
            {
                "type": "relevant_skill",
                "name": "Service Failure Investigation",
                "sourceIds": ["responsibilities-1"],
            }
        ],
    )

    system = messages[0]["content"]
    user = messages[1]["content"]
    normalised_system = " ".join(system.split())
    assert "bounded grounding repair" in normalised_system
    assert "not an importance or HR decision" in normalised_system
    assert "one normal resume example" in normalised_system
    assert '"ref": "R2"' in user
    assert '"ref": "R3"' in user
    assert "Service Failure Investigation" in user
    assert "Use only supplied refs" in user
    assert "HR Manager" not in system


def test_extraction_schema_normalises_importance_and_ignores_model_weight():
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "API Integration",
                    "sourceText": "Develop service integrations.",
                    "importance": "HIGH",
                    "suggestedWeight": 99,
                },
                {
                    "type": "relevant_skill",
                    "name": "Documentation",
                    "sourceText": "Maintain service documentation.",
                },
            ],
            "ignoredTexts": [],
        }
    )

    result = normalise_extraction_output(raw, debug=True)

    assert json.loads(result.legacy_json)["criteria"][0]["name"] == "API Integration"
    assert result.importance_by_index == {1: "high", 2: "medium"}
    assert any("weight was ignored" in warning for warning in result.warnings)
    assert any("missing importance" in warning for warning in result.warnings)


def test_extraction_schema_joins_exact_grouped_source_texts():
    source_texts = [
        "Investigate recurring service failures.",
        "Implement corrective actions for confirmed causes.",
    ]
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Failure Investigation",
                    "sourceTexts": source_texts,
                    "importance": "high",
                }
            ],
            "ignoredTexts": [],
        }
    )

    result = normalise_extraction_output(raw)
    criterion = json.loads(result.legacy_json)["criteria"][0]

    assert criterion["sourceText"] == " | ".join(source_texts)
    assert result.importance_by_index == {1: "high"}


def test_extraction_schema_resolves_compact_refs_to_exact_grouped_sources():
    source_lookup = {
        "R1": "Investigate recurring service failures.",
        "R2": "Implement corrective actions for confirmed causes.",
    }
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Failure Resolution",
                    "sourceRefs": ["r1", "R2"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = normalise_extraction_output(raw, source_lookup=source_lookup)
    criterion = json.loads(result.legacy_json)["criteria"][0]

    assert criterion["sourceText"] == " | ".join(source_lookup.values())
    assert result.importance_by_index == {1: "high"}


def test_extraction_schema_rejects_unknown_refs_without_inventing_evidence():
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Unsupported Capability",
                    "sourceRefs": ["R99"],
                    "importance": "medium",
                }
            ],
            "ignoredSourceRefs": ["Q99"],
        }
    )

    result = normalise_extraction_output(
        raw,
        source_lookup={"R1": "Maintain supported operations."},
    )
    criterion = json.loads(result.legacy_json)["criteria"][0]

    assert criterion["sourceText"] == ""
    assert result.ignored_texts == []
    assert result.parse_error is not None
    assert "unknown source references" in result.parse_error
    assert "unaccounted source references" not in result.parse_error
    assert result.missing_source_refs == set()
    assert result.unknown_source_refs == {"Q99", "R99"}
    assert any("unknown sourceRef 'R99'" in warning for warning in result.warnings)
    assert any("Ignored sourceRef 'Q99' is unknown" in warning for warning in result.warnings)


def test_extraction_schema_does_not_require_generic_duty_refs():
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Supported Operations",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = normalise_extraction_output(
        raw,
        source_lookup={
            "R1": "Maintain supported operations.",
            "R2": "Perform other duties assigned by management.",
        },
        required_source_refs={"R1"},
    )

    assert result.parse_error is None


def test_extraction_schema_accepts_explicit_unmapped_refs_as_a_valid_outcome():
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Supported Operations",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "unmappedSourceRefs": ["R2"],
        }
    )

    result = normalise_extraction_output(
        raw,
        source_lookup={
            "R1": "Maintain supported operations.",
            "R2": "Participate in a routine meeting.",
        },
        required_source_refs={"R1", "R2"},
    )

    assert result.parse_error is None
    assert result.unmapped_source_refs == {"R2"}


class EnhancedCachedLoader:
    def __init__(self, raw_output: str):
        self.model = None
        self.tokenizer = None
        self.loaded = True
        self.config = SimpleNamespace(
            mock_llm=False,
            max_new_tokens=900,
            debug_mode=True,
        )
        self.raw_output = raw_output
        self.calls = []
        self.triage_calls = []

    def triage_raw_output_generator(self, messages):
        self.triage_calls.append(messages)
        refs = list(
            dict.fromkeys(
                re.findall(
                    r'"sourceRef"\s*:\s*"([RQ]\d+)"',
                    messages[1]["content"],
                )
            )
        )
        return json.dumps(
            {
                "sourceDispositions": [
                    {
                        "sourceRef": source_ref,
                        "disposition": "CORE" if source_ref.startswith("R") else "SUPPORTING",
                        "resumeAssessable": True,
                        "importance": "high" if source_ref.startswith("R") else "medium",
                        "criterionUse": "STANDALONE_ELIGIBLE",
                        "reason": "Material resume-assessable role evidence.",
                    }
                    for source_ref in refs
                ]
            }
        )

    def enhanced_raw_output_generator(self, messages):
        self.calls.append(messages)
        return self.raw_output


class EnhancedSequenceLoader(EnhancedCachedLoader):
    def __init__(self, raw_outputs: list[str]):
        super().__init__(raw_outputs[0])
        self.raw_outputs = iter(raw_outputs)

    def enhanced_raw_output_generator(self, messages):
        self.calls.append(messages)
        return next(self.raw_outputs)


class SemanticConsolidationLoader(EnhancedCachedLoader):
    def __init__(self, raw_output: str, semantic_plan: str):
        super().__init__(raw_output)
        self.semantic_plan = semantic_plan
        self.semantic_calls = []

    def semantic_consolidation_raw_output_generator(self, messages):
        self.semantic_calls.append(messages)
        return self.semantic_plan


def test_live_pipeline_consolidates_grounded_model_capability_groups():
    responsibilities = [
        "Review contract requests and verify approval records.",
        "Track contract approvals and report unresolved requests.",
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Contract Request Review",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Contract Approval Tracking",
                    "sourceRefs": ["R2"],
                    "importance": "medium",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    semantic_plan = json.dumps(
        {
            "groups": [
                {
                    "type": "relevant_skill",
                    "name": "Contract Approval Workflow",
                    "memberIds": ["criterion-1", "criterion-2"],
                }
            ]
        }
    )

    loader = SemanticConsolidationLoader(raw_output, semantic_plan)
    result = CriteriaPipeline(loader).generate(
        {
            "jobTitle": "Contract Operations Lead",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "capability-group-consolidation",
    )

    assert len(result["criteria"]) == 1
    criterion = result["criteria"][0]
    assert criterion["name"] == "Contract Approval Workflow"
    assert criterion["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    assert criterion["sourceText"] == " | ".join(responsibilities)
    assert len(criterion["mergedFromIds"]) == 2
    assert len(loader.semantic_calls) == 1
    stage = next(
        item
        for item in result["audit"]["debugTrace"]
        if item["stage"] == "semantic_consolidation_review"
    )
    assert stage["acceptedGroupCount"] == 1
    assert stage["acceptedRenameCount"] == 0


def test_live_pipeline_expands_an_under_specified_singleton_name():
    responsibilities = [
        "Prepare quotations, invoices, purchase orders and delivery orders.",
        "Maintain accurate electronic and physical records.",
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Quotation Preparation",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Electronic Record Maintenance",
                    "sourceRefs": ["R2"],
                    "importance": "high",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    semantic_plan = json.dumps(
        {
            "groups": [],
            "renames": [
                {
                    "id": "criterion-1",
                    "name": "Quotation and Order Documentation",
                }
            ],
        }
    )

    result = CriteriaPipeline(
        SemanticConsolidationLoader(raw_output, semantic_plan)
    ).generate(
        {
            "jobTitle": "Operations Coordinator",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "grounded-singleton-rename",
    )

    assert [item["name"] for item in result["criteria"]] == [
        "Quotation and Order Documentation",
        "Electronic Record Maintenance",
    ]
    stage = next(
        item
        for item in result["audit"]["debugTrace"]
        if item["stage"] == "semantic_consolidation_review"
    )
    assert stage["acceptedGroupCount"] == 0
    assert stage["acceptedRenameCount"] == 1


def test_live_pipeline_consolidates_adjacent_supply_operations_when_review_is_empty():
    responsibilities = [
        (
            "Coordinate office suppliers, service vendors, maintenance "
            "requests and facility-related matters."
        ),
        (
            "Monitor office supplies and arrange purchases when stock reaches "
            "the required level."
        ),
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Supplier Coordination",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Stock Level Monitoring",
                    "sourceRefs": ["R2"],
                    "importance": "medium",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = SemanticConsolidationLoader(
        raw_output,
        json.dumps({"groups": [], "renames": []}),
    )

    result = CriteriaPipeline(loader).generate(
        {
            "jobTitle": "Operations Coordinator",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "adjacent-supply-operations",
    )

    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["name"] == (
        "Office Supplier and Stock Coordination"
    )
    assert result["criteria"][0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    stage = next(
        item
        for item in result["audit"]["debugTrace"]
        if item["stage"] == "supply_operations_consolidation"
    )
    assert len(stage["groups"]) == 1


def test_live_pipeline_consolidates_grounded_invoice_workflow_when_review_is_empty():
    responsibilities = [
        "Process supplier invoices and verify supporting documents.",
        (
            "Perform three-way matching between purchase orders, goods received "
            "notes and supplier invoices."
        ),
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Supplier Invoicing and Document Verification",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Three-Way Matching",
                    "sourceRefs": ["R2"],
                    "importance": "high",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = SemanticConsolidationLoader(
        raw_output,
        json.dumps({"groups": [], "renames": []}),
    )

    result = CriteriaPipeline(loader).generate(
        {
            "jobTitle": "Finance Operations Specialist",
            "department": "Finance",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "grounded-invoice-workflow",
    )

    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["name"] == (
        "Invoice Verification and Matching"
    )
    assert result["criteria"][0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    stage = next(
        item
        for item in result["audit"]["debugTrace"]
        if item["stage"] == "workflow_relation_consolidation"
    )
    assert len(stage["groups"]) == 1


def test_live_pipeline_rejects_group_name_not_supported_by_every_source():
    responsibilities = [
        "Review contract requests and verify approval records.",
        "Monitor warehouse temperature sensors.",
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Contract Request Review",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Warehouse Temperature Monitoring",
                    "sourceRefs": ["R2"],
                    "importance": "medium",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    semantic_plan = json.dumps(
        {
            "groups": [
                {
                    "type": "relevant_skill",
                    "name": "Contract Approval Workflow",
                    "memberIds": ["criterion-1", "criterion-2"],
                }
            ]
        }
    )

    result = CriteriaPipeline(
        SemanticConsolidationLoader(raw_output, semantic_plan)
    ).generate(
        {
            "jobTitle": "Operations Lead",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "unsafe-capability-group",
    )

    assert len(result["criteria"]) == 2
    assert {item["name"] for item in result["criteria"]} == {
        "Contract Request Review",
        "Warehouse Temperature Monitoring",
    }


def test_live_pipeline_retries_refs_attached_only_to_unsupported_names():
    responsibilities = [
        "Identify new enterprise customers.",
        "Develop new service opportunities.",
    ]
    misaligned = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Opportunity Development",
                    "sourceRefs": ["R1", "R2"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    repaired = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Enterprise Customer and Service Opportunity Development",
                    "sourceRefs": ["R1", "R2"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(
        EnhancedSequenceLoader([misaligned, repaired])
    ).generate(
        {
            "jobTitle": "Service Lead",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "misaligned-source-retry",
    )

    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    assert any(
        "assigned only to criteria whose names" in warning
        for warning in result["warnings"]
    )


def test_live_development_name_is_grounded_across_develop_source_forms():
    responsibilities = [
        "Identify new service customers.",
        "Develop new service opportunities.",
    ]
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Opportunity Development",
                    "sourceRefs": ["R1", "R2"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw_output)).generate(
        {
            "jobTitle": "Service Lead",
            "department": "Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "develop-development-grounding",
    )

    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]


def test_live_pipeline_keeps_unmapped_source_without_forced_recovery():
    responsibilities = [
        "Investigate recurring service failures.",
        "Resolve confirmed service failures and document the outcome.",
    ]
    job = {
        "jobTitle": "Service Reliability Lead",
        "department": "Operations",
        "responsibilities": responsibilities,
        "requirements": [],
    }
    incomplete = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Failure Investigation",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedSequenceLoader([incomplete])

    result = CriteriaPipeline(loader).generate(job, "source-accounting-retry")

    assert len(loader.calls) == 1
    assert len(result["criteria"]) == 1
    criterion = result["criteria"][0]
    assert criterion["sourceText"] == responsibilities[0]
    assert criterion["sourceIds"] == ["responsibilities-1"]
    assert not any(
        item["stage"] == "qwen_retry:complete_jd"
        for item in result["audit"]["debugTrace"]
    )
    accounting = {
        item["sourceRef"]: item
        for item in result["audit"]["sourceAccounting"]["sources"]
    }
    assert accounting["R2"]["processingOutcome"] == "not_mapped_after_validation"
    assert accounting["R2"]["generatedCriterionIds"] == []


def test_live_pipeline_does_not_recover_unmapped_responsibility():
    responsibilities = [
        "Investigate recurring service failures.",
        "Resolve confirmed service failures and document the outcome.",
    ]
    job = {
        "jobTitle": "Service Reliability Lead",
        "department": "Operations",
        "responsibilities": responsibilities,
        "requirements": [],
    }
    incomplete = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Failure Investigation",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedSequenceLoader([incomplete])

    result = CriteriaPipeline(loader).generate(job, "accounting-warning-fallback")

    assert len(loader.calls) == 1
    assert len(result["criteria"]) == 1
    assert not any(
        item["stage"] == "core_disposition_recovery"
        for item in result["audit"]["debugTrace"]
    )
    accounting = {
        item["sourceRef"]: item
        for item in result["audit"]["sourceAccounting"]["sources"]
    }
    assert accounting["R2"]["processingOutcome"] == "not_mapped_after_validation"


def test_live_pipeline_preserves_unmapped_plural_source_for_audit():
    responsibilities = [
        "Gather and validate operational data.",
        (
            "Write SQL queries and build reusable analytical datasets for "
            "reporting and investigation."
        ),
    ]
    job = {
        "jobTitle": "Reporting Specialist",
        "department": "Business Intelligence",
        "responsibilities": responsibilities,
        "requirements": [],
    }
    incomplete = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Operational Data Validation",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedSequenceLoader([incomplete])

    result = CriteriaPipeline(loader).generate(job, "plural-name-recovery")

    assert len(loader.calls) == 1
    assert not any(
        item.get("sourceIds") == ["responsibilities-2"]
        for item in result["criteria"]
    )
    accounting = {
        item["sourceRef"]: item
        for item in result["audit"]["sourceAccounting"]["sources"]
    }
    assert accounting["R2"]["processingOutcome"] == "not_mapped_after_validation"


def test_live_pipeline_decomposes_umbrellas_without_recovery():
    responsibilities = [
        "Clarify vacancy requirements and prepare recruitment plans.",
        "Source candidates through job portals and professional networks.",
        "Screen applications and conduct structured phone interviews.",
        "Schedule interviews and coordinate interview panels.",
        "Prepare offer documents and coordinate reference checks.",
        "Maintain applicant tracking records and produce pipeline reports.",
        "Support employer-branding and career-fair campaigns.",
        "Provide joining information to the onboarding team after acceptance.",
    ]
    umbrella = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Vacancy Recruitment Planning",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Candidate Sourcing and Screening",
                    "sourceRefs": ["R2", "R3"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Interview Coordination and Offer Preparation",
                    "sourceRefs": ["R4", "R5", "R6", "R8"],
                    "importance": "high",
                },
            ],
            "ignoredSourceRefs": ["R7"],
        }
    )
    loader = EnhancedSequenceLoader([umbrella, umbrella])

    result = CriteriaPipeline(loader).generate(
        {
            "jobTitle": "Talent Coordinator",
            "department": "People Operations",
            "responsibilities": responsibilities,
            "requirements": [],
        },
        "decompose-and-recover",
    )

    by_source = {
        tuple(item["sourceIds"]): item["name"] for item in result["criteria"]
    }
    assert by_source[("responsibilities-2",)] == "Candidate Sourcing"
    assert by_source[("responsibilities-3",)] == "Candidate Screening"
    assert by_source[("responsibilities-4",)] == "Interview Coordination"
    assert by_source[("responsibilities-5",)] == "Offer Preparation"
    assert ("responsibilities-6",) not in by_source
    assert ("responsibilities-7",) not in by_source
    assert ("responsibilities-8",) not in by_source
    assert result["weightTotal"] == 100
    decomposition = next(
        item
        for item in result["audit"]["debugTrace"]
        if item["stage"] == "multisource_capability_decomposition"
    )
    assert decomposition["changeCount"] >= 2
    assert not any(
        item["stage"] == "core_disposition_recovery"
        for item in result["audit"]["debugTrace"]
    )
    accounting = {
        item["sourceRef"]: item
        for item in result["audit"]["sourceAccounting"]["sources"]
    }
    assert accounting["R7"]["processingOutcome"] == "not_mapped_after_model_review"


def test_live_pipeline_keeps_first_output_when_only_q_refs_are_missing():
    job = {
        "jobTitle": "Operations Lead",
        "department": "Operations",
        "responsibilities": ["Prepare weekly workforce reports."],
        "requirements": [
            "Minimum 5 years of experience in workforce operations.",
            "Experience working in a manufacturing environment is preferred.",
        ],
    }
    first_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_experience",
                    "name": "Workforce Report Preparation",
                    "sourceRefs": ["R1"],
                    "importance": "medium",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedSequenceLoader([first_output])

    result = CriteriaPipeline(loader).generate(job, "q-gap-first-output")

    assert len(loader.calls) == 1
    assert not any(
        item["stage"] == "qwen_retry:complete_jd"
        for item in result["audit"]["debugTrace"]
    )
    report = next(
        item for item in result["criteria"]
        if item["sourceIds"] == ["responsibilities-1"]
    )
    assert report["type"] == "relevant_skill"
    experience = {
        item["name"]: item
        for item in result["criteria"]
        if item["type"] == "relevant_experience"
    }
    assert set(experience) == {
        "Workforce Operations Experience",
        "Manufacturing Environment Experience",
    }
    assert {
        tuple(item["sourceIds"])
        for item in experience.values()
    } == {("requirements-1",), ("requirements-2",)}
    assert result["weightTotal"] == 100
    assert not any(
        "unaccounted source references: Q1, Q2" in warning
        for warning in result["warnings"]
    )


def test_live_pipeline_recovers_explicit_qualification_field():
    job = {
        "jobTitle": "Integration Developer",
        "department": "Technology",
        "responsibilities": ["Develop service integrations."],
        "requirements": [],
        "qualifications": [
            "A degree in Computer Science or Software Engineering is required."
        ],
    }
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Integration Development",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedSequenceLoader([raw_output])

    result = CriteriaPipeline(loader).generate(job, "qualification-recovery")

    assert len(loader.calls) == 1
    education = next(
        item for item in result["criteria"]
        if item["type"] == "education_relevance"
    )
    assert education["name"] == "Computing Education"
    assert education["sourceIds"] == ["qualifications-1"]


def test_live_pipeline_creates_neutral_education_for_level_only_and_exposes_hard_filter():
    job = {
        "jobTitle": "Operations Coordinator",
        "department": "Operations",
        "responsibilities": ["Coordinate daily operating schedules."],
        "requirements": ["Minimum Diploma or Degree."],
    }
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Operating Schedule Coordination",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw_output)).generate(
        job,
        "level-only-education",
    )

    education = [
        item for item in result["criteria"] if item["type"] == "education_relevance"
    ]
    assert len(education) == 1
    assert education[0]["name"] == "Education"
    assert education[0]["sourceIds"] == ["requirements-1"]
    assert "field of study" not in education[0]["sourceText"].casefold()
    assert result["eligibilitySuggestions"]["educationLevel"] == "Diploma"
    assert result["eligibilitySuggestions"]["enabledFilters"] == ["educationLevel"]
    assert result["weightTotal"] == 100


def test_live_pipeline_separates_hr_experience_scope_from_level_only_education():
    job = {
        "jobTitle": "People Manager",
        "department": "People",
        "responsibilities": ["Lead employee relations cases."],
        "requirements": [
            "Min. STPM/Diploma or Degree with min. 5 years experience in HR field."
        ],
    }
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Employee Relations Cases",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw_output)).generate(
        job,
        "education-experience-grammar",
    )

    by_type = {item["type"]: item for item in result["criteria"]}
    assert by_type["education_relevance"]["name"] == "Education"
    assert by_type["education_relevance"]["sourceIds"] == ["requirements-1"]
    assert by_type["relevant_experience"]["name"] == "HR Field Experience"
    assert by_type["relevant_experience"]["sourceIds"] == ["requirements-1"]
    assert not any(
        "HR Field Education" == item["name"] for item in result["criteria"]
    )
    assert result["eligibilitySuggestions"] == {
        "minCGPA": None,
        "minExperience": "5+ years",
        "educationLevel": "STPM / Foundation / Matriculation",
        "requiredLanguage": None,
        "requiredLocation": None,
        "enabledFilters": ["minExperience", "educationLevel"],
    }
    assert result["weightTotal"] == 100


def test_live_pipeline_does_not_force_education_or_experience_without_evidence():
    job = {
        "jobTitle": "Operations Coordinator",
        "department": "Operations",
        "responsibilities": ["Coordinate daily operating schedules."],
        "requirements": ["Strong written communication skills."],
    }
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Operating Schedule Coordination",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw_output)).generate(
        job,
        "conditional-soft-dimensions",
    )

    assert not any(
        item["type"] in {"education_relevance", "relevant_experience"}
        for item in result["criteria"]
    )
    assert result["eligibilitySuggestions"]["educationLevel"] is None
    assert result["eligibilitySuggestions"]["minExperience"] is None
    assert result["eligibilitySuggestions"]["enabledFilters"] == []


def test_live_pipeline_keeps_non_numeric_experience_as_soft_evidence_only():
    job = {
        "jobTitle": "Operations Lead",
        "department": "Operations",
        "responsibilities": ["Improve production workflows."],
        "requirements": ["Experience in a manufacturing environment is preferred."],
    }
    raw_output = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Production Workflow Improvement",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw_output)).generate(
        job,
        "non-numeric-experience",
    )

    experience = [
        item for item in result["criteria"] if item["type"] == "relevant_experience"
    ]
    assert len(experience) == 1
    assert experience[0]["name"] == "Manufacturing Environment Experience"
    assert result["eligibilitySuggestions"]["minExperience"] is None
    assert result["eligibilitySuggestions"]["enabledFilters"] == []


def test_live_pipeline_uses_one_complete_extraction_and_preserves_sections():
    job = {
        "jobTitle": "Process Engineer",
        "department": "Engineering",
        "responsibilities": [
            "Analyse process data to identify yield losses.",
            "Plan and conduct controlled process trials.",
            "Any other duties assigned by management.",
        ],
        "requirements": [
            "A degree in Chemical Engineering or a related field is required.",
            "Knowledge of statistical process control is required.",
        ],
    }
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Process Data Analysis",
                    "sourceRefs": ["R1"],
                    "importance": "high",
                },
                {
                    "type": "relevant_skill",
                    "name": "Process Trials",
                    "sourceRefs": ["R2"],
                    "importance": "high",
                },
                {
                    "type": "education_relevance",
                    "name": "Chemical Engineering Education",
                    "sourceRefs": ["Q1"],
                    "importance": "low",
                },
                {
                    "type": "domain_knowledge",
                    "name": "Statistical Process Control",
                    "sourceRefs": ["Q2"],
                    "importance": "medium",
                },
            ],
            "ignoredSourceRefs": [],
        }
    )
    loader = EnhancedCachedLoader(raw)

    result = CriteriaPipeline(loader).generate(job, "live-test")

    assert len(loader.calls) == 1
    prompt = loader.calls[0][1]["content"]
    assert "Analyse process data to identify yield losses." in prompt
    assert "Knowledge of statistical process control is required." in prompt
    assert result["weightTotal"] == 100
    assert result["criteria"]
    assert len(result["criteria"]) == 4
    assert {item["type"] for item in result["criteria"]} == {
        "relevant_skill",
        "education_relevance",
        "domain_knowledge",
    }

    by_name = {item["name"]: item for item in result["criteria"]}
    assert by_name["Process Data Analysis"]["sourceIds"] == ["responsibilities-1"]
    assert by_name["Process Trials"]["sourceIds"] == ["responsibilities-2"]
    assert by_name["Chemical Engineering Education"]["sourceIds"] == ["requirements-1"]
    assert by_name["Statistical Process Control"]["sourceIds"] == ["requirements-2"]
    assert by_name["Process Data Analysis"]["importance"] == "high"
    assert by_name["Chemical Engineering Education"]["importance"] == "low"
    assert all(item["mergedFromIds"] == [item["criterionId"]] for item in result["criteria"])
    assert all("Any other duties" not in item["sourceText"] for item in result["criteria"])
    assert any(item["sourceText"] == job["responsibilities"][2] for item in result["ignoredTexts"])
    assert all(item["description"].startswith("Evaluates") for item in result["criteria"])


def test_live_pipeline_does_not_use_model_weight_for_final_weighting():
    job = {
        "jobTitle": "Planner",
        "department": "Operations",
        "responsibilities": ["Manage production planning."],
        "requirements": ["A diploma in Supply Chain is required."],
    }
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Production Planning",
                    "sourceText": "Manage production planning.",
                    "importance": "high",
                    "weight": 1,
                },
                {
                    "type": "education_relevance",
                    "name": "Supply Chain Education",
                    "sourceText": "A diploma in Supply Chain is required.",
                    "importance": "low",
                    "suggestedWeight": 99,
                },
            ],
            "ignoredTexts": [],
        }
    )
    loader = EnhancedCachedLoader(raw)

    result = CriteriaPipeline(loader).generate(job, "weight-test")

    assert result["weightTotal"] == 100
    weights = {item["name"]: item["suggestedWeight"] for item in result["criteria"]}
    assert weights["Production Planning"] > weights["Supply Chain Education"]
    assert any("weight was ignored" in warning for warning in result["warnings"])


def test_live_pipeline_preserves_grouped_source_metadata_and_lineage():
    responsibilities = [
        "Investigate recurring service failures.",
        "Resolve confirmed service failures and document the outcome.",
    ]
    job = {
        "jobTitle": "Service Reliability Lead",
        "department": "Operations",
        "responsibilities": responsibilities,
        "requirements": [],
    }
    raw = json.dumps(
        {
            "candidateCriteria": [
                {
                    "type": "relevant_skill",
                    "name": "Service Failure Investigation",
                    "sourceRefs": ["R1", "R2"],
                    "importance": "high",
                }
            ],
            "ignoredSourceRefs": [],
        }
    )

    result = CriteriaPipeline(EnhancedCachedLoader(raw)).generate(job, "grouped-test")

    assert len(result["criteria"]) == 1
    criterion = result["criteria"][0]
    assert criterion["sourceText"] == " | ".join(responsibilities)
    assert criterion["sourceIds"] == ["responsibilities-1", "responsibilities-2"]
    assert criterion["groundingScores"] == [1.0, 1.0]
    assert criterion["mergedFromIds"] == [criterion["criterionId"]]
    stages = [item["stage"] for item in result["audit"]["debugTrace"]]
    assert "lineage_restoration" in stages
