"""Cross-role regression checks for the frozen criteria API pipeline."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from app.pipeline import CriteriaPipeline


ALLOWED_TYPES = {
    "relevant_skill",
    "relevant_experience",
    "education_relevance",
    "domain_knowledge",
    "preferred_certification",
    "job_related_language",
}


ROLE_CASES: list[dict[str, Any]] = [
    {
        "jobTitle": "HR Manager",
        "department": "Human Resource",
        "responsibilities": [
            "Lead recruitment, training and employee onboarding activities.",
            "Manage employee relations, grievances and disciplinary matters.",
            "Process monthly payroll and HR records.",
            "Monitor office security procedures and access control.",
            "Any other duties assigned by management.",
        ],
        "requirements": [
            "Minimum 5 years of experience in human resources.",
            "STPM, Diploma or Degree.",
            "Familiarity with Malaysian labour laws.",
        ],
    },
    {
        "jobTitle": "Software Engineer",
        "department": "Information Technology",
        "responsibilities": [
            "Develop and test software applications using Python and REST APIs.",
            "Troubleshoot application defects and improve system performance.",
            "Maintain technical documentation for deployed services.",
            "Any other tasks assigned by the manager.",
        ],
        "requirements": [
            "Degree in Computer Science or Software Engineering.",
            "Minimum 3 years of experience in software development.",
            "Familiarity with secure coding principles.",
        ],
    },
    {
        "jobTitle": "Accounts Payable Executive",
        "department": "Finance and Accounting",
        "responsibilities": [
            "Process supplier invoices and reconcile payment records.",
            "Prepare monthly financial reports and investigate variances.",
            "Maintain accounts payable documentation.",
            "Perform other duties as assigned.",
        ],
        "requirements": [
            "Diploma or Degree.",
            "Minimum 2 years of experience.",
            "Knowledge of accounting controls and tax regulations.",
            "Professional accounting certification is an added advantage.",
        ],
    },
    {
        "jobTitle": "Sales Executive",
        "department": "Sales and Marketing",
        "responsibilities": [
            "Develop sales plans and manage key customer accounts.",
            "Conduct market research and prepare sales proposals.",
            "Follow up customer enquiries and negotiate commercial terms.",
            "Complete other tasks as instructed.",
        ],
        "requirements": [
            "Bachelor's Degree in Marketing, Business or a related field.",
            "Minimum 3 years of experience.",
            "Fluent in English and Bahasa Malaysia.",
            "Experience with CRM systems is an advantage.",
        ],
    },
]


SECTION_OUTPUTS: dict[str, list[dict[str, Any]]] = {
    "HR Manager": [
        {
            "type": "relevant_skill",
            "name": "Recruitment and Training Management",
            "sourceText": ROLE_CASES[0]["responsibilities"][0],
        },
        {
            "type": "relevant_skill",
            "name": "Employee Relations Management",
            "sourceText": ROLE_CASES[0]["responsibilities"][1],
        },
        {
            "type": "relevant_skill",
            "name": "Payroll Processing",
            "sourceText": ROLE_CASES[0]["responsibilities"][2],
        },
        {
            "type": "relevant_skill",
            "name": "Security Management",
            "sourceText": ROLE_CASES[0]["responsibilities"][3],
        },
        {
            "type": "relevant_experience",
            "name": "HR Field Experience",
            "sourceText": ROLE_CASES[0]["requirements"][0],
        },
        {
            "type": "domain_knowledge",
            "name": "Malaysian Labour Law",
            "sourceText": ROLE_CASES[0]["requirements"][2],
        },
    ],
    "Software Engineer": [
        {
            "type": "relevant_skill",
            "name": "Software Development and Testing",
            "sourceText": ROLE_CASES[1]["responsibilities"][0],
        },
        {
            "type": "relevant_skill",
            "name": "Application Troubleshooting",
            "sourceText": ROLE_CASES[1]["responsibilities"][1],
        },
        {
            "type": "relevant_skill",
            "name": "Technical Documentation",
            "sourceText": ROLE_CASES[1]["responsibilities"][2],
        },
        {
            "type": "relevant_experience",
            "name": "Software Development Experience",
            "sourceText": ROLE_CASES[1]["requirements"][1],
        },
        {
            "type": "education_relevance",
            "name": "Computer Science or Software Engineering Education",
            "sourceText": ROLE_CASES[1]["requirements"][0],
        },
        {
            "type": "domain_knowledge",
            "name": "Secure Coding Principles",
            "sourceText": ROLE_CASES[1]["requirements"][2],
        },
    ],
    "Accounts Payable Executive": [
        {
            "type": "relevant_skill",
            "name": "Invoice Processing and Reconciliation",
            "sourceText": ROLE_CASES[2]["responsibilities"][0],
        },
        {
            "type": "relevant_skill",
            "name": "Financial Reporting and Variance Investigation",
            "sourceText": ROLE_CASES[2]["responsibilities"][1],
        },
        {
            "type": "relevant_skill",
            "name": "Accounts Payable Documentation",
            "sourceText": ROLE_CASES[2]["responsibilities"][2],
        },
        {
            "type": "domain_knowledge",
            "name": "Accounting Controls and Tax Regulations",
            "sourceText": ROLE_CASES[2]["requirements"][2],
        },
        {
            "type": "preferred_certification",
            "name": "Professional Accounting Certification",
            "sourceText": ROLE_CASES[2]["requirements"][3],
        },
    ],
    "Sales Executive": [
        {
            "type": "relevant_skill",
            "name": "Sales Planning and Account Management",
            "sourceText": ROLE_CASES[3]["responsibilities"][0],
        },
        {
            "type": "relevant_skill",
            "name": "Market Research and Sales Proposals",
            "sourceText": ROLE_CASES[3]["responsibilities"][1],
        },
        {
            "type": "relevant_skill",
            "name": "Customer Enquiry and Commercial Negotiation",
            "sourceText": ROLE_CASES[3]["responsibilities"][2],
        },
        {
            "type": "education_relevance",
            "name": "Marketing or Business Education",
            "sourceText": ROLE_CASES[3]["requirements"][0],
        },
        {
            "type": "job_related_language",
            "name": "English and Bahasa Malaysia Proficiency",
            "sourceText": ROLE_CASES[3]["requirements"][2],
        },
        {
            "type": "relevant_skill",
            "name": "CRM Systems",
            "sourceText": ROLE_CASES[3]["requirements"][3],
        },
    ],
}


class CrossRoleCachedLoader:
    def __init__(self, job_title: str) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self.job_title = job_title
        self._section_outputs = iter(
            [
                json.dumps(
                    {"criteria": SECTION_OUTPUTS[job_title]}
                ),
                json.dumps({"criteria": []}),
            ]
        )

    def raw_output_generator(self, messages: list[dict[str, str]]) -> str:
        content = messages[-1]["content"]
        if "criteriaByType" in content and "Validated criteria" in content:
            start = content.index("{", content.index("criteriaByType") - 2)
            payload, _ = json.JSONDecoder().raw_decode(content[start:])
            groups = [
                {
                    "type": type_id,
                    "name": item["name"],
                    "memberIds": [item["id"]],
                }
                for type_id, items in payload["criteriaByType"].items()
                for item in items
            ]
            return json.dumps({"groups": groups})
        return next(self._section_outputs)


def run_case(job: dict[str, Any]) -> dict[str, Any]:
    return CriteriaPipeline(
        CrossRoleCachedLoader(job["jobTitle"])
    ).generate(job)


def _all_source_parts(criterion: dict[str, Any]) -> list[str]:
    return [
        part.strip()
        for part in criterion["sourceText"].split("|")
        if part.strip()
    ]


def _assert_common_contract(job: dict[str, Any], result: dict[str, Any]) -> None:
    source_texts = set(job["responsibilities"] + job["requirements"])
    assert result["weightTotal"] == 100
    assert result["audit"]["consolidation"]["finalCriteriaCountValidation"]["limitEnabled"] is False
    assert result["audit"]["consolidation"]["finalCriteriaLimitValid"] is True
    for criterion in result["criteria"]:
        assert criterion["type"] in ALLOWED_TYPES
        parts = _all_source_parts(criterion)
        assert parts
        assert set(parts).issubset(source_texts)
        assert len(criterion["sourceIds"]) == len(parts)
        assert len(criterion["groundingScores"]) == len(parts)
        assert all(0 <= score <= 1 for score in criterion["groundingScores"])
        assert criterion["name"].casefold() != job["jobTitle"].casefold()


def test_cross_role_regression_preserves_role_priority_and_grounding() -> None:
    results = {
        job["jobTitle"]: run_case(job)
        for job in ROLE_CASES
    }

    for job in ROLE_CASES:
        _assert_common_contract(job, results[job["jobTitle"]])

    hr = results["HR Manager"]
    hr_criteria = hr["criteria"]
    hr_evidence = " ".join(item["sourceText"] for item in hr_criteria).casefold()
    assert "recruitment" in hr_evidence
    assert "training" in hr_evidence
    assert "payroll" in hr_evidence
    security = next(item for item in hr_criteria if item["name"] == "Security Management")
    core_hr_weights = [
        item["suggestedWeight"]
        for item in hr_criteria
        if item is not security
        and any(
            token in item["sourceText"].casefold()
            for token in ("recruitment", "training", "payroll")
        )
    ]
    assert core_hr_weights
    assert security["suggestedWeight"] <= max(core_hr_weights)


def test_existing_hr_manager_fixture_keeps_main_hr_scope_evidence() -> None:
    from tests.test_hr_manager_replay import (
        HRManagerCachedLoader,
        REQUIREMENTS,
        RESPONSIBILITIES,
    )

    result = CriteriaPipeline(HRManagerCachedLoader()).generate(
        {
            "jobTitle": "Manager",
            "department": "Human Resource",
            "responsibilities": RESPONSIBILITIES,
            "requirements": REQUIREMENTS,
        }
    )
    final_evidence = " ".join(
        item["sourceText"] for item in result["criteria"]
    ).casefold()
    assert "recruitment" in final_evidence
    assert "training" in final_evidence
    assert "payroll" in final_evidence
    security = next(
        item for item in result["criteria"]
        if item["name"] == "Security Management"
    )
    assert security["suggestedWeight"] <= max(
        item["suggestedWeight"]
        for item in result["criteria"]
        if item["name"] != "Security Management"
        and item["type"] == "relevant_skill"
    )
    assert result["weightTotal"] == 100


def test_cross_role_education_and_experience_boundaries() -> None:
    hr = run_case(ROLE_CASES[0])
    finance = run_case(ROLE_CASES[2])
    software = run_case(ROLE_CASES[1])
    sales = run_case(ROLE_CASES[3])

    assert any(item["type"] == "education_relevance" for item in hr["criteria"])
    assert any(item["type"] == "education_relevance" for item in finance["criteria"])
    assert any(item["type"] == "education_relevance" for item in software["criteria"])
    assert any(item["type"] == "education_relevance" for item in sales["criteria"])

    for result in (hr, software, sales):
        experience = [
            item for item in result["criteria"]
            if item["type"] == "relevant_experience"
        ]
        if experience:
            assert max(item["suggestedWeight"] for item in experience) < max(
                item["suggestedWeight"]
                for item in result["criteria"]
                if item["type"] == "relevant_skill"
            )
    assert not any(
        item["type"] == "relevant_experience"
        for item in finance["criteria"]
    )


def test_cross_role_titles_do_not_create_unsupported_capabilities() -> None:
    for job in ROLE_CASES:
        result = run_case(job)
        source_text = " ".join(
            job["responsibilities"] + job["requirements"]
        ).casefold()
        for criterion in result["criteria"]:
            assert criterion["name"].casefold() != job["jobTitle"].casefold()
            meaningful_title_tokens = {
                token
                for token in job["jobTitle"].casefold().split()
                if len(token) > 3
            }
            unsupported_title_tokens = {
                token for token in meaningful_title_tokens
                if token not in source_text
            }
            assert not (
                unsupported_title_tokens
                and all(
                    token in criterion["name"].casefold()
                    for token in unsupported_title_tokens
                )
            )
