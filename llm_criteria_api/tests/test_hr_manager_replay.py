from __future__ import annotations

import json
from types import SimpleNamespace

from app.pipeline import CriteriaPipeline


RESPONSIBILITIES = [
    "Recruitment, training, employee relations, payroll, foreign workers, security, safety and health, canteen and 5S.",
    "Foreign worker: recruitment, manpower sourcing, permits, immigration matters, hostel, facilities, transportation and departure arrangements.",
    "Employee relations: grievances, counselling, motivation and disciplinary matters.",
    "Security management: security guards, security processes, access systems and CCTV.",
    "Administration and operations: company vehicles, parking, canteen, cleanliness, housekeeping and 5S.",
    "Compliance: ISO 9001, ISO 14001, ISO 13485, OHSAS, company policies, safety and environmental requirements.",
]

REQUIREMENTS = [
    "STPM, Diploma or Degree.",
    "Minimum 5 years of experience in the HR field.",
    "Detail-oriented, able to work independently, able to multi-task.",
    "Excellent verbal and written communication skills; able to communicate with staff at all levels.",
    "Familiarity with Malaysian labour laws.",
]


class HRManagerCachedLoader:
    def __init__(self) -> None:
        self.config = SimpleNamespace(mock_llm=False, max_new_tokens=900)
        self.loaded = True
        self.model = None
        self.tokenizer = None
        self._section_outputs = iter(
            [
                json.dumps(
                    {
                        "criteria": [
                            {
                                "type": "relevant_skill",
                                "name": "HR Process Management",
                                "sourceText": RESPONSIBILITIES[0],
                            },
                            {
                                "type": "relevant_skill",
                                "name": "Foreign Worker Facilities Management Oversight",
                                "sourceText": RESPONSIBILITIES[1],
                            },
                            {
                                "type": "relevant_skill",
                                "name": "Employee Relations Management",
                                "sourceText": RESPONSIBILITIES[2],
                            },
                            {
                                "type": "relevant_skill",
                                "name": "Security Management",
                                "sourceText": RESPONSIBILITIES[3],
                            },
                            {
                                "type": "relevant_skill",
                                "name": "Administration and 5S Operations",
                                "sourceText": RESPONSIBILITIES[4],
                            },
                            {
                                "type": "domain_knowledge",
                                "name": "ISO and Safety Compliance",
                                "sourceText": RESPONSIBILITIES[5],
                            },
                        ]
                    }
                ),
                json.dumps(
                    {
                        "criteria": [
                            {
                                "type": "education_relevance",
                                "name": "Relevant Education Field",
                                "sourceText": REQUIREMENTS[0],
                            },
                            {
                                "type": "relevant_experience",
                                "name": "HR Field Experience",
                                "sourceText": REQUIREMENTS[1],
                            },
                            {
                                "type": "relevant_skill",
                                "name": "Communication Skills",
                                "sourceText": REQUIREMENTS[3],
                            },
                            {
                                "type": "domain_knowledge",
                                "name": "Malaysian Labour Law",
                                "sourceText": REQUIREMENTS[4],
                            },
                        ]
                    }
                ),
            ]
        )

    def raw_output_generator(self, messages: list[dict[str, str]]) -> str:
        content = messages[-1]["content"]
        if "criteriaByType" not in content:
            return next(self._section_outputs)
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


def test_hr_manager_retains_foreign_worker_capability_in_final_output():
    result = CriteriaPipeline(HRManagerCachedLoader()).generate(
        {
            "jobTitle": "Manager",
            "department": "Human Resource",
            "responsibilities": RESPONSIBILITIES,
            "requirements": REQUIREMENTS,
        }
    )

    foreign_worker = next(
        item
        for item in result["criteria"]
        if item["name"] == "Foreign Worker Management"
    )
    # The broad Main HR Scope sentence is context, not evidence for every
    # capability. Only the specific foreign-worker scope remains grounded.
    assert foreign_worker["sourceText"].count(" | ") == 0
    assert "foreign worker" in foreign_worker["sourceText"].casefold()
    assert "manpower sourcing" in foreign_worker["sourceText"].casefold()
    assert "immigration" in foreign_worker["sourceText"].casefold()
    assert "canteen" not in foreign_worker["sourceText"].casefold()
    assert "parking" not in foreign_worker["sourceText"].casefold()
    assert "Facilities Management" not in foreign_worker["name"]
    assert sum(item["suggestedWeight"] for item in result["criteria"]) == 100

    experience = next(
        item
        for item in result["criteria"]
        if item["type"] == "relevant_experience"
    )
    core_weights = [
        item["suggestedWeight"]
        for item in result["criteria"]
        if item["type"] == "relevant_skill"
        and item["name"] != "Communication Skills"
    ]
    assert core_weights
    assert experience["suggestedWeight"] < max(core_weights)


def test_hr_manager_is_not_over_fragmented_after_safe_consolidation():
    result = CriteriaPipeline(HRManagerCachedLoader()).generate(
        {
            "jobTitle": "Manager",
            "department": "Human Resource",
            "responsibilities": RESPONSIBILITIES,
            "requirements": REQUIREMENTS,
        }
    )

    # The broad HR scope is retained as one additional grounded core
    # capability; the framework does not impose a maximum criterion count.
    # Explicit formal standards may add a separate domain_knowledge criterion;
    # the framework does not impose a maximum criterion count.
    assert 8 <= len(result["criteria"]) <= 10
    assert result["weightTotal"] == 100
    administration = next(
        item
        for item in result["criteria"]
        if item["name"] == "Administration and 5S Operations"
    )
    compliance = next(
        item
        for item in result["criteria"]
        if "iso 9001" in item["sourceText"].casefold()
    )
    assert "company vehicles" in administration["sourceText"].casefold()
    assert "iso 9001" not in administration["sourceText"].casefold()
    assert administration["sourceIds"] == ["responsibilities-5"]
    assert administration["groundingScores"] == [1.0]
    assert "company vehicles" not in compliance["sourceText"].casefold()
    assert compliance["sourceIds"] == ["responsibilities-6"]
    assert compliance["groundingScores"] == [1.0]

    security = next(
        item for item in result["criteria"] if item["name"] == "Security Management"
    )
    assert "canteen" not in security["sourceText"].casefold()
    assert "vehicles" not in security["sourceText"].casefold()
    assert "5s" not in security["sourceText"].casefold()

    foreign = next(
        item
        for item in result["criteria"]
        if item["name"] == "Foreign Worker Management"
    )
    assert "employee relations" not in foreign["sourceText"].casefold()
    assert "security management" not in foreign["sourceText"].casefold()

    labour_law = next(
        item
        for item in result["criteria"]
        if item["name"] == "Malaysian Labour Law"
    )
    assert labour_law["type"] == "domain_knowledge"
