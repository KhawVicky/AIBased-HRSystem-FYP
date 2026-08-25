"""Regression tests for evidence isolation and conservative same-type merges."""

from __future__ import annotations

import json
from types import SimpleNamespace

from app import frozen_pipeline
from app.evidence_safety import (
    apply_semantic_consolidation_plan,
    consolidate_adjacent_supply_operations,
    consolidate_grounded_workflow_relations,
    decompose_incoherent_multisource_criteria,
    final_evidence_safety_pass,
    is_generic_duty_safe,
    safe_merge_duplicate_criteria,
    same_capability_with_object_alignment,
)
from app.pipeline import CriteriaPipeline


class CachedLoader:
    def __init__(self, outputs: list[str]) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._outputs = iter(outputs)

    def raw_output_generator(self, _messages: list[dict[str, str]]) -> str:
        return next(self._outputs)


def section_output(*criteria: dict[str, str]) -> str:
    return json.dumps({"criteria": list(criteria)})


def run_case(responsibilities: list[str], output: str) -> dict:
    return CriteriaPipeline(CachedLoader([output, '{"criteria": []}'])).generate(
        {
            "jobTitle": "Manager",
            "department": "Human Resource",
            "responsibilities": responsibilities,
            "requirements": [],
        }
    )


def test_cctv_evidence_excludes_unrelated_operations() -> None:
    security = "Security management: security guards, security processes, access systems and CCTV."
    administration = "Administration and operations: company vehicles, parking, canteen, cleanliness, housekeeping and 5S."
    compliance = "Compliance: ISO 9001, company policies, safety and environmental requirements."
    result = run_case(
        [security, administration, compliance],
        section_output(
            {
                "type": "relevant_skill",
                "name": "CCTV Monitoring and Maintenance",
                "sourceText": " | ".join([security, administration, compliance]),
            }
        ),
    )
    criterion = next(item for item in result["criteria"] if "cctv" in item["sourceText"].casefold())
    evidence = criterion["sourceText"].casefold()
    assert "cctv" in evidence
    assert "canteen" not in evidence
    assert "vehicles" not in evidence
    assert "5s" not in evidence
    assert "company policies" not in evidence
    assert len(criterion["sourceIds"]) == len(criterion["groundingScores"])


def test_foreign_worker_evidence_excludes_minor_and_generic_sources() -> None:
    foreign = "Foreign worker: recruitment, manpower sourcing, permits, immigration matters, hostel, facilities, transportation and departure arrangements."
    presentation = "Prepare management presentations."
    parking = "Administration and operations: company vehicles, parking, canteen and 5S."
    generic = "Any other responsibility which may be assigned by the Management."
    result = run_case(
        [foreign, presentation, parking, generic],
        section_output(
            {
                "type": "relevant_skill",
                "name": "Foreign Worker Management",
                "sourceText": " | ".join([foreign, presentation, parking, generic]),
            }
        ),
    )
    criterion = next(item for item in result["criteria"] if item["name"] == "Foreign Worker Management")
    evidence = criterion["sourceText"].casefold()
    assert "foreign worker" in evidence
    assert "immigration" in evidence
    assert "presentation" not in evidence
    assert "parking" not in evidence
    assert "any other responsibility" not in evidence
    assert len(criterion["sourceIds"]) == len(criterion["groundingScores"])


def test_generic_duty_is_excluded_through_final_output() -> None:
    generic = "Any other responsibility which may be assigned by the Management."
    result = run_case(
        [generic],
        section_output(
            {
                "type": "relevant_skill",
                "name": "General Work Performance",
                "sourceText": generic,
            }
        ),
    )
    assert not result["criteria"]
    assert any(
        item.get("sourceText") == generic
        and "generic" in item.get("reason", "").casefold()
        for item in result["ignoredTexts"]
    )


def test_shared_monitor_verb_does_not_merge_different_domains() -> None:
    cctv = {"type": "relevant_skill", "name": "CCTV Monitoring", "sourceText": "Monitor CCTV systems."}
    attendance = {"type": "relevant_skill", "name": "Employee Attendance Monitoring", "sourceText": "Monitor employee attendance records."}
    same = lambda left, right: same_capability_with_object_alignment(
        lambda _left, _right: True, left, right
    )
    assert not same(cctv, attendance)
    merged = safe_merge_duplicate_criteria(
        [cctv, attendance], frozen_pipeline, same
    )
    assert len(merged) == 2


def test_shared_domain_words_do_not_merge_distinct_methods() -> None:
    system = {
        "type": "relevant_skill",
        "name": "Inventory Management System",
        "sourceText": "Maintain the inventory management system.",
    }
    analysis = {
        "type": "relevant_skill",
        "name": "Inventory Level Monitoring",
        "sourceText": "Monitor inventory levels using ABC analysis.",
    }
    same = lambda left, right: same_capability_with_object_alignment(
        lambda _left, _right: True, left, right
    )

    assert not same(system, analysis)
    assert len(
        safe_merge_duplicate_criteria(
            [system, analysis], frozen_pipeline, same
        )
    ) == 2


def test_low_confidence_fallback_preserves_separate_criteria_and_evidence() -> None:
    first = {"type": "relevant_skill", "name": "CCTV Monitoring", "sourceText": "Monitor CCTV systems.", "sourceIds": ["responsibilities-1"]}
    second = {"type": "relevant_skill", "name": "Canteen Operations", "sourceText": "Maintain canteen operations.", "sourceIds": ["responsibilities-2"]}
    same = lambda left, right: same_capability_with_object_alignment(
        lambda _left, _right: True, left, right
    )
    result = safe_merge_duplicate_criteria([first, second], frozen_pipeline, same)
    assert len(result) == 2
    assert {item["sourceText"] for item in result} == {
        first["sourceText"],
        second["sourceText"],
    }


def test_generic_duty_variants_are_removed_by_final_safety() -> None:
    variants = [
        "Any other responsibility which may be assigned form time to time by top management.",
        "Any other ad hoc tasks assigned by the Management.",
        "Follow company policies and procedures.",
        "Collaborate with team members on other assigned activities.",
    ]
    for text in variants:
        assert is_generic_duty_safe(text, frozen_pipeline)

    security = "Security management: security guards, security processes, access systems and CCTV."
    criterion = {
        "type": "relevant_skill",
        "name": "CCTV Monitoring and Maintenance",
        "sourceText": " | ".join([security, variants[0], "Administration and operations: company cars, canteen, 5S and housekeeping."]),
        "sourceIds": ["responsibilities-1", "responsibilities-2", "responsibilities-3"],
        "groundingScores": [1.0, 1.0, 1.0],
    }
    cleaned, warnings, rejected, audit = final_evidence_safety_pass(
        [criterion], frozen_pipeline
    )
    assert not rejected
    assert cleaned[0]["sourceText"] == security
    assert cleaned[0]["sourceIds"] == ["responsibilities-1"]
    assert cleaned[0]["groundingScores"] == [1.0]
    assert len(audit["removedSourceText"]) == 2
    assert warnings


def test_routine_recurring_meeting_is_safeguarded_but_meeting_ownership_is_not() -> None:
    assert is_generic_duty_safe(
        "Participate in monthly departmental meeting.", frozen_pipeline
    )
    assert not is_generic_duty_safe(
        "Facilitate monthly departmental meeting and present workforce metrics.",
        frozen_pipeline,
    )


def test_multisource_decomposition_releases_name_misaligned_evidence() -> None:
    sourcing = (
        "Source candidates through job portals, professional networks, "
        "employee referrals and targeted outreach."
    )
    screening = (
        "Screen applications and conduct structured phone interviews against "
        "the approved job requirements."
    )
    criterion = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Candidate Screening",
        "sourceText": f"{sourcing} | {screening}",
        "sourceIds": ["responsibilities-2", "responsibilities-3"],
        "groundingScores": [1.0, 1.0],
    }

    decomposed, warnings, audit = decompose_incoherent_multisource_criteria(
        [criterion]
    )

    assert decomposed[0]["sourceText"] == screening
    assert decomposed[0]["sourceIds"] == ["responsibilities-3"]
    assert any("released 1 source" in warning for warning in warnings)
    assert audit[0]["releasedSourceIds"] == ["responsibilities-2"]


def test_multisource_decomposition_splits_independent_name_conjuncts() -> None:
    interview = (
        "Schedule interviews, coordinate interview panels and keep candidates "
        "informed throughout the selection process."
    )
    offer = (
        "Prepare offer documents and coordinate reference checks and other "
        "pre-employment checks."
    )
    joining = (
        "Provide complete candidate and joining information to the onboarding "
        "team after offer acceptance."
    )
    criterion = {
        "criterionId": "criterion-2",
        "type": "relevant_skill",
        "name": "Interview Coordination and Offer Preparation",
        "sourceText": " | ".join([interview, offer, joining]),
        "sourceIds": [
            "responsibilities-4",
            "responsibilities-5",
            "responsibilities-8",
        ],
        "groundingScores": [1.0, 1.0, 1.0],
    }

    decomposed, warnings, audit = decompose_incoherent_multisource_criteria(
        [criterion]
    )

    assert [item["name"] for item in decomposed] == [
        "Interview Coordination",
        "Offer Preparation",
    ]
    assert [item["sourceIds"] for item in decomposed] == [
        ["responsibilities-4"],
        ["responsibilities-5"],
    ]
    assert any("decomposed" in warning for warning in warnings)
    assert audit[-1]["releasedSourceIds"] == ["responsibilities-8"]


def test_multisource_decomposition_preserves_shared_object_capability() -> None:
    account = "Manage existing customer accounts and maintain long-term business relationships."
    proposal = "Understand customer requirements and prepare suitable quotations and sales proposals."
    criterion = {
        "criterionId": "criterion-3",
        "type": "relevant_skill",
        "name": "Customer Relationship Management",
        "sourceText": f"{account} | {proposal}",
        "sourceIds": ["responsibilities-3", "responsibilities-4"],
        "groundingScores": [1.0, 1.0],
    }

    decomposed, warnings, audit = decompose_incoherent_multisource_criteria(
        [criterion]
    )

    assert decomposed == [criterion]
    assert not warnings
    assert not audit


def test_multisource_education_drops_nonacademic_evidence_even_when_trusted() -> None:
    education = "Diploma in Logistics or Supply Chain Management."
    experience = "Minimum 2 years of warehouse operations experience."
    criterion = {
        "criterionId": "criterion-1",
        "type": "education_relevance",
        "name": "Logistics Education",
        "sourceText": f"{experience} | {education}",
        "sourceIds": ["requirements-1", "qualifications-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [1.0, 1.0],
    }

    cleaned, warnings, rejected, audit = final_evidence_safety_pass(
        [criterion],
        frozen_pipeline,
        {"responsibilities-criterion-1": {experience, education}},
    )

    assert not rejected
    assert cleaned[0]["sourceText"] == education
    assert cleaned[0]["sourceIds"] == ["qualifications-1"]
    assert cleaned[0]["groundingScores"] == [1.0]
    assert audit["removedSourceText"] == [
        {"criterion": "Logistics Education", "sourceText": experience}
    ]
    assert warnings


def test_model_group_requires_shared_type_and_grounded_name() -> None:
    first = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Contract Request Review",
        "sourceText": "Review contract requests and verify approvals.",
        "sourceIds": ["responsibilities-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [1.0],
    }
    second = {
        "criterionId": "criterion-2",
        "type": "relevant_skill",
        "name": "Contract Approval Tracking",
        "sourceText": "Track contract approvals and unresolved requests.",
        "sourceIds": ["responsibilities-2"],
        "sourceCriterionIds": ["responsibilities-criterion-2"],
        "groundingScores": [0.98],
    }

    raw_plan = json.dumps(
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
    merged, warnings, audit, errors = apply_semantic_consolidation_plan(
        [first, second],
        raw_plan,
        frozen_pipeline,
    )

    assert len(merged) == 1
    assert merged[0]["name"] == "Contract Approval Workflow"
    assert merged[0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    assert merged[0]["mergedFromIds"] == ["criterion-1", "criterion-2"]
    assert warnings
    assert "contract" in audit[0]["sharedObjectRoots"]
    assert not errors


def test_model_group_may_keep_shared_context_implicit_in_grounded_name() -> None:
    suppliers = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Supplier Coordination",
        "sourceText": (
            "Coordinate office suppliers, service vendors, maintenance "
            "requests and facility-related matters."
        ),
        "sourceIds": ["responsibilities-5"],
        "sourceCriterionIds": ["responsibilities-criterion-5"],
        "groundingScores": [1.0],
    }
    stock = {
        "criterionId": "criterion-2",
        "type": "relevant_skill",
        "name": "Stock Level Monitoring",
        "sourceText": (
            "Monitor office supplies and arrange purchases when stock reaches "
            "the required level."
        ),
        "sourceIds": ["responsibilities-6"],
        "sourceCriterionIds": ["responsibilities-criterion-6"],
        "groundingScores": [1.0],
    }
    raw_plan = json.dumps(
        {
            "groups": [
                {
                    "type": "relevant_skill",
                    "name": "Supplier and Stock Management",
                    "memberIds": ["criterion-1", "criterion-2"],
                }
            ],
            "renames": [],
        }
    )

    merged, _, audit, errors = apply_semantic_consolidation_plan(
        [suppliers, stock], raw_plan, frozen_pipeline
    )

    assert len(merged) == 1
    assert merged[0]["name"] == "Supplier and Stock Management"
    assert merged[0]["sourceIds"] == [
        "responsibilities-5",
        "responsibilities-6",
    ]
    assert audit[0]["sharedObjectRoots"] == ["office"]
    assert not errors


def test_model_rename_adds_only_grounded_objects_to_singleton_name() -> None:
    criterion = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Quotation Preparation",
        "sourceText": (
            "Prepare quotations, invoices, purchase orders and delivery orders."
        ),
        "sourceIds": ["responsibilities-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [1.0],
    }
    raw_plan = json.dumps(
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

    renamed, warnings, audit, errors = apply_semantic_consolidation_plan(
        [criterion], raw_plan, frozen_pipeline
    )

    assert renamed[0]["name"] == "Quotation and Order Documentation"
    assert renamed[0]["sourceText"] == criterion["sourceText"]
    assert warnings
    assert audit[0]["kind"] == "rename"
    assert audit[0]["addedObjectRoots"] == ["order"]
    assert not errors


def test_model_rename_rejects_an_invented_object() -> None:
    criterion = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Quotation Preparation",
        "sourceText": "Prepare quotations and purchase orders.",
        "sourceIds": ["responsibilities-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [1.0],
    }
    raw_plan = json.dumps(
        {
            "groups": [],
            "renames": [
                {
                    "id": "criterion-1",
                    "name": "Quotation and Revenue Documentation",
                }
            ],
        }
    )

    unchanged, warnings, audit, errors = apply_semantic_consolidation_plan(
        [criterion], raw_plan, frozen_pipeline
    )

    assert unchanged[0]["name"] == "Quotation Preparation"
    assert not warnings
    assert not audit
    assert any("does not add grounded source objects" in error for error in errors)


def test_adjacent_supply_operations_merge_with_shared_physical_context() -> None:
    suppliers = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Supplier Coordination",
        "sourceText": (
            "Coordinate office suppliers, service vendors, maintenance "
            "requests and facility-related matters."
        ),
        "sourceIds": ["responsibilities-5"],
        "sourceCriterionIds": ["responsibilities-criterion-5"],
        "groundingScores": [1.0],
        "importance": "high",
    }
    stock = {
        "criterionId": "criterion-2",
        "type": "relevant_skill",
        "name": "Stock Level Monitoring",
        "sourceText": (
            "Monitor office supplies and arrange purchases when stock reaches "
            "the required level."
        ),
        "sourceIds": ["responsibilities-6"],
        "sourceCriterionIds": ["responsibilities-criterion-6"],
        "groundingScores": [0.98],
        "importance": "medium",
    }

    merged, warnings, audit = consolidate_adjacent_supply_operations(
        [suppliers, stock]
    )

    assert len(merged) == 1
    assert merged[0]["name"] == "Office Supplier and Stock Coordination"
    assert merged[0]["sourceIds"] == [
        "responsibilities-5",
        "responsibilities-6",
    ]
    assert merged[0]["groundingScores"] == [1.0, 0.98]
    assert merged[0]["mergedFromIds"] == ["criterion-1", "criterion-2"]
    assert warnings
    assert audit[0]["sharedContext"] == "office"


def test_supply_rule_does_not_merge_supplier_reconciliation_with_payments() -> None:
    reconciliation = {
        "criterionId": "criterion-1",
        "type": "relevant_skill",
        "name": "Supplier Statement Reconciliation",
        "sourceText": "Reconcile supplier statements and investigate differences.",
        "sourceIds": ["responsibilities-4"],
        "sourceCriterionIds": ["responsibilities-criterion-4"],
        "groundingScores": [1.0],
    }
    payment = {
        "criterionId": "criterion-2",
        "type": "relevant_skill",
        "name": "Payment Runs",
        "sourceText": "Prepare payment runs and supporting payment files.",
        "sourceIds": ["responsibilities-5"],
        "sourceCriterionIds": ["responsibilities-criterion-5"],
        "groundingScores": [1.0],
    }

    unchanged, warnings, audit = consolidate_adjacent_supply_operations(
        [reconciliation, payment]
    )

    assert unchanged == [reconciliation, payment]
    assert not warnings
    assert not audit


def _workflow_skill(
    criterion_id: str,
    name: str,
    source_text: str,
    source_id: str,
    *,
    importance: str = "medium",
) -> dict[str, object]:
    section, position = source_id.rsplit("-", 1)
    return {
        "criterionId": criterion_id,
        "type": "relevant_skill",
        "name": name,
        "sourceText": source_text,
        "sourceIds": [source_id],
        "sourceCriterionIds": [f"{section}-criterion-{position}"],
        "groundingScores": [1.0],
        "importance": importance,
    }


def test_grounded_invoice_verification_and_matching_are_consolidated() -> None:
    verification = _workflow_skill(
        "criterion-1",
        "Supplier Invoicing and Document Verification",
        "Process supplier invoices and verify supporting documents.",
        "responsibilities-1",
        importance="high",
    )
    matching = _workflow_skill(
        "criterion-2",
        "Three-Way Matching",
        "Perform three-way matching between orders, receipts and supplier invoices.",
        "responsibilities-2",
        importance="medium",
    )

    merged, warnings, audit = consolidate_grounded_workflow_relations(
        [verification, matching]
    )

    assert len(merged) == 1
    assert merged[0]["name"] == "Invoice Verification and Matching"
    assert merged[0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]
    assert merged[0]["groundingScores"] == [1.0, 1.0]
    assert merged[0]["mergedFromIds"] == ["criterion-1", "criterion-2"]
    assert merged[0]["importance"] == "high"
    assert warnings
    assert audit[0]["relation"] == "invoice_verification_matching"


def test_sales_pipeline_and_follow_up_use_source_order_not_list_order() -> None:
    pipeline = _workflow_skill(
        "criterion-pipeline",
        "Sales Pipeline Monitoring",
        "Monitor the sales pipeline and prepare regular forecasts.",
        "responsibilities-7",
    )
    unrelated = _workflow_skill(
        "criterion-presentation",
        "Sales Presentation",
        "Prepare and deliver sales presentations to customers.",
        "responsibilities-3",
    )
    follow_up = _workflow_skill(
        "criterion-follow-up",
        "Sales Follow-Up Activities",
        "Maintain sales opportunities and follow-up actions in the CRM system.",
        "responsibilities-6",
        importance="high",
    )

    merged, warnings, audit = consolidate_grounded_workflow_relations(
        [pipeline, unrelated, follow_up]
    )

    assert [item["name"] for item in merged] == [
        "Sales Pipeline and Follow-Up Management",
        "Sales Presentation",
    ]
    assert merged[0]["sourceIds"] == [
        "responsibilities-6",
        "responsibilities-7",
    ]
    assert merged[0]["sourceCriterionIds"] == [
        "responsibilities-criterion-6",
        "responsibilities-criterion-7",
    ]
    assert merged[0]["mergedFromIds"] == [
        "criterion-follow-up",
        "criterion-pipeline",
    ]
    assert merged[0]["importance"] == "high"
    assert warnings
    assert audit[0]["relation"] == "commercial_pipeline_follow_up"


def test_workflow_relations_reject_near_misses_and_nonconsecutive_sources() -> None:
    cases = [
        [
            _workflow_skill(
                "criterion-1",
                "Invoice Verification",
                "Verify supplier invoices and supporting documents.",
                "responsibilities-1",
            ),
            _workflow_skill(
                "criterion-2",
                "Supplier Payments",
                "Prepare approved supplier invoice payments.",
                "responsibilities-2",
            ),
        ],
        [
            _workflow_skill(
                "criterion-1",
                "Lead Pipeline Monitoring",
                "Monitor the lead pipeline and forecast opportunities.",
                "responsibilities-1",
            ),
            _workflow_skill(
                "criterion-2",
                "Prospect Follow-Up",
                "Complete follow-up actions with prospective clients.",
                "responsibilities-2",
            ),
        ],
        [
            _workflow_skill(
                "criterion-1",
                "Sales Presentation",
                "Deliver sales presentations to prospective customers.",
                "responsibilities-1",
            ),
            _workflow_skill(
                "criterion-2",
                "Sales Follow-Up",
                "Complete sales follow-up actions with prospective customers.",
                "responsibilities-2",
            ),
        ],
        [
            _workflow_skill(
                "criterion-1",
                "Customer Relationship Management",
                "Maintain customer relationships and account records.",
                "responsibilities-1",
            ),
            _workflow_skill(
                "criterion-2",
                "Sales Pipeline Monitoring",
                "Monitor the sales pipeline and forecast opportunities.",
                "responsibilities-2",
            ),
        ],
        [
            _workflow_skill(
                "criterion-1",
                "Invoice Verification",
                "Verify supplier invoices and supporting documents.",
                "responsibilities-1",
            ),
            _workflow_skill(
                "criterion-2",
                "Invoice Matching",
                "Match supplier invoices against purchase orders.",
                "responsibilities-3",
            ),
        ],
    ]

    for criteria in cases:
        unchanged, warnings, audit = consolidate_grounded_workflow_relations(
            criteria
        )
        assert unchanged == criteria
        assert not warnings
        assert not audit


def test_hr_process_and_foreign_worker_are_not_same_capability() -> None:
    hr_process = {
        "type": "relevant_skill",
        "name": "HR Process Management",
        "sourceText": "Manage recruitment, training, payroll and employee relations.",
    }
    foreign_worker = {
        "type": "relevant_skill",
        "name": "Foreign Worker Management",
        "sourceText": "Manage foreign workers, permits, immigration and hostel arrangements.",
    }
    assert not same_capability_with_object_alignment(
        lambda _left, _right: True, hr_process, foreign_worker
    )


def test_foreign_worker_stages_merge_only_with_each_other() -> None:
    recruitment = {
        "type": "relevant_skill",
        "name": "Recruitment Administration",
        "sourceText": "Manage recruitment and administration of foreign workers.",
        "sourceIds": ["responsibilities-1"],
        "groundingScores": [1.0],
    }
    permits = {
        "type": "relevant_skill",
        "name": "Foreign Worker Coordination",
        "sourceText": "Coordinate foreign-worker permits and immigration documentation.",
        "sourceIds": ["responsibilities-2"],
        "groundingScores": [1.0],
    }
    same = lambda left, right: same_capability_with_object_alignment(
        lambda _left, _right: False, left, right
    )

    merged = safe_merge_duplicate_criteria(
        [recruitment, permits], frozen_pipeline, same
    )

    assert len(merged) == 1
    assert merged[0]["name"] == "Foreign Worker Management"
    assert merged[0]["sourceIds"] == [
        "responsibilities-1",
        "responsibilities-2",
    ]


def test_malaysian_labour_law_remains_domain_knowledge_after_safety() -> None:
    source = "Familiarity with Malaysian labour laws."
    criterion = {
        "type": "domain_knowledge",
        "name": "Malaysian Labour Law",
        "sourceText": source,
        "sourceIds": ["requirements-5"],
        "groundingScores": [1.0],
    }
    cleaned, _, rejected, _ = final_evidence_safety_pass(
        [criterion], frozen_pipeline
    )
    assert not rejected
    assert cleaned[0]["type"] == "domain_knowledge"
    assert cleaned[0]["sourceText"] == source
    assert cleaned[0]["sourceIds"] == ["requirements-5"]


def test_level_only_education_survives_as_neutral_education_relevance() -> None:
    source = "Minimum Diploma or Degree."
    criterion = {
        "type": "education_relevance",
        "name": "Relevant Education Field",
        "sourceText": source,
        "sourceIds": ["requirements-1"],
        "groundingScores": [1.0],
    }

    cleaned, warnings, rejected, _ = final_evidence_safety_pass(
        [criterion], frozen_pipeline
    )

    assert not rejected
    assert cleaned[0]["type"] == "education_relevance"
    assert cleaned[0]["name"] == "Education"
    assert cleaned[0]["sourceText"] == source
    assert not any("evidence removed" in warning for warning in warnings)


def test_named_education_field_remains_valid_education_relevance() -> None:
    source = "Degree in Human Resources, Business Administration or related field."
    criterion = {
        "type": "education_relevance",
        "name": "Human Resources Education",
        "sourceText": source,
        "sourceIds": ["requirements-1"],
        "groundingScores": [1.0],
    }

    cleaned, _, rejected, _ = final_evidence_safety_pass(
        [criterion], frozen_pipeline
    )

    assert not rejected
    assert cleaned == [criterion]


def test_distinct_hr_capability_domains_remain_separate() -> None:
    employee = {
        "type": "relevant_skill",
        "name": "Employee Relations Management",
        "sourceText": "Employee relations: grievances and disciplinary matters.",
        "sourceIds": ["responsibilities-1"],
        "sourceCriterionIds": ["responsibilities-criterion-1"],
        "groundingScores": [1.0],
    }
    hr_process = {
        "type": "relevant_skill",
        "name": "HR Process Management",
        "sourceText": "Manage recruitment, training and payroll processes.",
        "sourceIds": ["responsibilities-2"],
        "sourceCriterionIds": ["responsibilities-criterion-2"],
        "groundingScores": [0.98],
    }
    merged = safe_merge_duplicate_criteria(
        [employee, hr_process],
        frozen_pipeline,
        lambda left, right: same_capability_with_object_alignment(
            lambda _left, _right: False, left, right
        ),
    )
    assert len(merged) == 2
    assert {item["name"] for item in merged} == {
        "Employee Relations Management",
        "HR Process Management",
    }
    assert [item["sourceIds"] for item in merged] == [
        ["responsibilities-1"],
        ["responsibilities-2"],
    ]
