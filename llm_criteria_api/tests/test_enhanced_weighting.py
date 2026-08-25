from app.enhanced_weighting import apply_enhanced_weights
from app.role_context import build_role_context, criterion_context_signals


def test_core_responsibilities_outweigh_supporting_requirements():
    criteria = [
        {
            "type": "relevant_skill",
            "name": "Foreign Worker Management",
            "sourceText": "Handle foreign worker recruitment and manpower sourcing.",
            "sourceIds": ["responsibilities-1"],
        },
        {
            "type": "relevant_skill",
            "name": "Security Operations",
            "sourceText": "Manage security guards, access systems and CCTV.",
            "sourceIds": ["responsibilities-2"],
        },
        {
            "type": "relevant_experience",
            "name": "HR Field Experience",
            "sourceText": "Minimum 5 years of experience in the HR field.",
            "sourceIds": ["requirements-1"],
        },
        {
            "type": "domain_knowledge",
            "name": "Malaysian Labour Law",
            "sourceText": "Familiarity with Malaysian labour laws.",
            "sourceIds": ["requirements-2"],
        },
        {
            "type": "education_relevance",
            "name": "Relevant Education Field",
            "sourceText": "STPM, Diploma or Degree in Human Resources.",
            "sourceIds": ["requirements-3"],
        },
    ]

    weighted = apply_enhanced_weights(criteria)
    weights = [item["suggestedWeight"] for item in weighted]

    assert sum(weights) == 100
    assert weights[0] > weights[2]
    assert weights[1] > weights[2]
    assert weights[0] > weights[3]
    assert weights[1] > weights[3]
    assert weights[2] > weights[4]


def test_role_title_is_only_a_contextual_priority_signal():
    criteria = [
        {
            "type": "relevant_skill",
            "name": "Software Development",
            "sourceText": "Develop and test software applications.",
            "sourceIds": ["responsibilities-1"],
            "sourceCriterionIds": ["responsibilities-criterion-1"],
        },
        {
            "type": "relevant_skill",
            "name": "Office Administration",
            "sourceText": "Maintain office records and supplies.",
            "sourceIds": ["responsibilities-2"],
            "sourceCriterionIds": ["responsibilities-criterion-2"],
        },
    ]
    job = {
        "jobTitle": "Software Developer",
        "department": "Information Technology",
        "responsibilities": [
            "Develop and test software applications.",
            "Maintain office records and supplies.",
        ],
        "requirements": ["Experience with software development projects."],
    }
    context = build_role_context(job)
    signals = criterion_context_signals(criteria[0], context)
    assert signals["titleOverlap"] > 0
    assert signals["isResponsibility"] is True

    weighted = apply_enhanced_weights(criteria, job)
    assert weighted[0]["suggestedWeight"] > weighted[1]["suggestedWeight"]
    assert sum(item["suggestedWeight"] for item in weighted) == 100


def test_role_context_does_not_create_or_rename_criteria():
    criteria = [
        {
            "type": "relevant_skill",
            "name": "Inventory Reconciliation",
            "sourceText": "Reconcile inventory records.",
            "sourceIds": ["responsibilities-1"],
        }
    ]
    weighted = apply_enhanced_weights(
        criteria,
        {
            "jobTitle": "Warehouse Supervisor",
            "department": "Supply Chain",
            "responsibilities": ["Reconcile inventory records."],
            "requirements": [],
        },
    )
    assert len(weighted) == 1
    assert weighted[0]["name"] == "Inventory Reconciliation"


def test_source_breadth_does_not_allow_one_criterion_to_dominate():
    criteria = [
        {
            "type": "relevant_skill",
            "name": "Recruitment Operations",
            "sourceText": "Recruit candidates. | Screen applicants. | Coordinate interviews. | Prepare offers. | Track onboarding.",
            "sourceIds": [f"responsibilities-{index}" for index in range(1, 6)],
        },
        {
            "type": "relevant_skill",
            "name": "Employee Relations",
            "sourceText": "Handle employee grievances.",
            "sourceIds": ["responsibilities-6"],
        },
        {
            "type": "domain_knowledge",
            "name": "Labour Law",
            "sourceText": "Knowledge of labour law.",
            "sourceIds": ["requirements-1"],
        },
        {
            "type": "education_relevance",
            "name": "Education",
            "sourceText": "Minimum Diploma or Degree.",
            "sourceIds": ["requirements-2"],
        },
    ]

    weighted = apply_enhanced_weights(criteria)

    assert sum(item["suggestedWeight"] for item in weighted) == 100
    assert max(item["suggestedWeight"] for item in weighted) <= 35
    assert weighted[2]["suggestedWeight"] > 0
    assert weighted[3]["suggestedWeight"] > 0
