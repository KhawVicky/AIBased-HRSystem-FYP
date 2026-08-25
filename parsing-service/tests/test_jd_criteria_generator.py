import pytest

from app.config.uwc_jd_taxonomy import UWC_JOB_TAXONOMY
from app.schemas.jd_criteria import CriteriaGenerationResponse, JDCriteriaRequest
from app.services.jd_criteria_generator import (
    _detect_uwc_taxonomy_domain,
    _responsibility_fact,
    generate_jd_criteria,
)


EXPECTED_UWC_DOMAINS = {
    "software_it",
    "procurement_sourcing",
    "production_planning",
    "manufacturing",
    "engineering",
    "quality_assurance",
    "sales_marketing",
    "warehouse_logistics",
    "finance_costing",
    "maintenance_facilities",
    "human_resources",
}


def test_uwc_taxonomy_has_expandable_domain_and_capability_configuration() -> None:
    assert set(UWC_JOB_TAXONOMY) == EXPECTED_UWC_DOMAINS
    for domain in UWC_JOB_TAXONOMY.values():
        assert domain["name"]
        assert domain["keywords"]
        assert domain["phrases"]
        assert domain["patterns"]
        assert domain["capabilities"]
        for capability in domain["capabilities"].values():
            assert capability["label"]
            assert capability["keywords"]
            assert capability["phrases"]
            assert capability["patterns"]


@pytest.mark.parametrize(
    ("responsibility", "expected_domain"),
    [
        ("Develop web applications and maintain APIs.", "software_it"),
        ("Source suppliers and negotiate material prices.", "procurement_sourcing"),
        ("Prepare weekly production schedules and capacity plans.", "production_planning"),
        ("Oversee manufacturing operations on the production line.", "manufacturing"),
        ("Prepare technical drawings and design machine components.", "engineering"),
        ("Conduct quality inspections and root cause analysis.", "quality_assurance"),
        ("Achieve sales targets through business development.", "sales_marketing"),
        ("Manage warehouse operations and inventory control.", "warehouse_logistics"),
        ("Prepare financial reports and perform cost analysis.", "finance_costing"),
        ("Perform preventive maintenance and repair machinery.", "maintenance_facilities"),
        ("Source candidates and coordinate interviews.", "human_resources"),
    ],
)
def test_detects_uwc_domain_from_current_jd_content(
    responsibility: str, expected_domain: str
) -> None:
    request = JDCriteriaRequest(responsibilities=[responsibility])
    assert _detect_uwc_taxonomy_domain(request) == expected_domain


def test_jd_content_overrides_conflicting_title_and_department_context() -> None:
    request = JDCriteriaRequest(
        jobTitle="Software Engineer",
        department="Information Technology",
        responsibilities=[
            "Source suppliers and negotiate material prices for production."
        ],
    )

    assert _detect_uwc_taxonomy_domain(request) == "procurement_sourcing"
    criteria = generate_jd_criteria(request)["data"]["criteria"]
    assert criteria[0]["category"] == "job_function_procurement"


def test_taxonomy_classifies_but_current_content_decides_the_criteria() -> None:
    sourcing_request = JDCriteriaRequest(
        jobTitle="Executive",
        responsibilities=[
            "Source new suppliers and negotiate contract terms."
        ],
    )
    purchasing_request = JDCriteriaRequest(
        jobTitle="Executive",
        responsibilities=[
            "Process purchase orders and evaluate supplier quotations."
        ],
    )

    assert _detect_uwc_taxonomy_domain(sourcing_request) == (
        "procurement_sourcing"
    )
    assert _detect_uwc_taxonomy_domain(purchasing_request) == (
        "procurement_sourcing"
    )
    sourcing_name = generate_jd_criteria(sourcing_request)["data"]["criteria"][0][
        "name"
    ]
    purchasing_name = generate_jd_criteria(purchasing_request)["data"]["criteria"][
        0
    ]["name"]
    assert sourcing_name == "Supplier Sourcing and Commercial Negotiation"
    assert purchasing_name == "Purchasing Operations"


def test_title_and_department_alone_do_not_select_a_taxonomy_domain() -> None:
    request = JDCriteriaRequest(
        jobTitle="Software Engineer",
        department="Information Technology",
        responsibilities=["Organise community event registrations."],
    )

    assert _detect_uwc_taxonomy_domain(request) is None


def test_generic_fallback_groups_content_when_taxonomy_has_no_match() -> None:
    request = JDCriteriaRequest(
        responsibilities=[
            "Prepare community event records.",
            "Archive event files after each session.",
        ]
    )

    assert _detect_uwc_taxonomy_domain(request) is None
    criteria = generate_jd_criteria(request)["data"]["criteria"]
    assert criteria[0]["category"] == "job_function_documentation_records"


def test_generates_grouped_criteria_and_eligibility_suggestions() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Data Analyst",
            department="Information Technology",
            description="This position is based in Batu Kawan, Penang.",
            qualifications=[
                "Bachelor Degree with minimum CGPA 3.0.",
                "At least 3-5 years of relevant experience.",
                "Fluent in English and professional certification preferred.",
            ],
            responsibilities=[
                "Use SQL, Python, Power BI and Excel to prepare reports.",
                "Perform data analysis and present findings.",
            ],
            requirements=["Strong communication skills."],
        )
    )

    data = result["data"]
    CriteriaGenerationResponse(**result)
    criteria = data["criteria"]
    assert [item["type"] for item in criteria] == [
        "relevant_skill",
        "relevant_experience",
        "preferred_certification",
        "job_related_language",
    ]
    assert sum(item["weight"] for item in criteria) == 100
    assert {item["type"]: item["weight"] for item in criteria} == {
        "relevant_skill": 43,
        "relevant_experience": 36,
        "preferred_certification": 11,
        "job_related_language": 10,
    }
    assert not any(item["type"] == "education_relevance" for item in criteria)
    assert not any(item["category"] == "availability" for item in criteria)
    assert all(item["isAutoDetected"] for item in criteria)
    assert all(item["jdEvidence"] for item in criteria)
    assert all(item["resumeEvidenceToCheck"] for item in criteria)
    assert all(
        item["explanation"].startswith("The job description requires")
        for item in criteria
    )
    assert all(". The resume should show " in item["explanation"] for item in criteria)
    assert not any(
        wording in item["explanation"]
        for item in criteria
        for wording in (
            "Grouped responsibility",
            "Mapped capability",
            "Detected taxonomy",
            "Generated from rule",
        )
    )
    assert len({item["explanation"] for item in criteria}) == len(criteria)
    skill_evidence = next(
        item["jdEvidence"]
        for item in criteria
        if item["type"] == "relevant_skill"
    )
    assert set(request for request in skill_evidence) >= {
        "Use SQL, Python, Power BI and Excel to prepare reports.",
        "Perform data analysis and present findings.",
        "Strong communication skills.",
    }

    suggestions = data["eligibilitySuggestions"]
    assert suggestions["minExperience"] == "3 years"
    assert suggestions["educationLevel"] == "Bachelor Degree"
    assert suggestions["minCGPA"] == 3.0
    assert suggestions["requiredLanguage"] == "English"
    assert suggestions["requiredLocation"] == "Penang"
    assert suggestions["enabledFilters"] == [
        "minExperience",
        "educationLevel",
        "minCGPA",
        "requiredLanguage",
        "requiredLocation",
    ]


def test_responsibility_function_takes_priority_over_supporting_skill() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="HR Executive",
            responsibilities=["Manage recruitment and payroll activities."],
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["name"] for item in criteria] == ["End-to-End Recruitment"]
    assert sum(item["weight"] for item in criteria) == 100


def test_generates_separate_recruitment_business_criteria() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Recruitment Executive",
            department="Human Resource",
            qualifications=[
                "Diploma or Degree, or past working experience in recruitment.",
                "At least 2 years in recruitment or worked in recruitment firms.",
                "Good written and verbal communication skills.",
                "Proficient in Microsoft Office, JobStreet and LinkedIn Recruiter.",
                "Proactive, detail-oriented and a team player.",
            ],
            responsibilities=[
                "Source candidates, screen candidates and shortlist suitable applicants.",
                "Arrange interviews and coordinate candidate onboarding.",
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["type"] for item in criteria] == [
        "relevant_skill",
        "relevant_experience",
    ]
    assert [item["weight"] for item in criteria] == [55, 45]
    assert all(
        evidence in criteria[0]["jdEvidence"]
        for evidence in (
            "Source candidates, screen candidates and shortlist suitable applicants.",
            "Arrange interviews and coordinate candidate onboarding.",
            "Good written and verbal communication skills.",
            "Proficient in Microsoft Office, JobStreet and LinkedIn Recruiter.",
            "Proactive, detail-oriented and a team player.",
        )
    )
    suggestions = result["data"]["eligibilitySuggestions"]
    assert suggestions["minExperience"] == "2 years"
    assert "educationLevel" not in suggestions
    assert "educationLevel" not in suggestions["enabledFilters"]


@pytest.mark.parametrize(
    ("experience_text", "expected_filter"),
    [
        ("At least 2 years", "2 years"),
        ("At least 6 years of experience", "5+ years"),
    ],
)
def test_qualification_only_experience_stays_an_eligibility_requirement(
    experience_text: str,
    expected_filter: str,
) -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Recruitment Executive",
            qualifications=[experience_text],
        )
    )

    assert result["data"]["criteria"] == []
    assert result["data"]["eligibilitySuggestions"]["minExperience"] == (
        expected_filter
    )


def test_job_title_and_department_do_not_force_a_domain() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Recruitment Manager",
            department="Human Resource",
            qualifications=["At least 3 years of relevant experience."],
            responsibilities=["Coordinate daily operations and prepare reports."],
        )
    )

    names = [item["name"] for item in result["data"]["criteria"]]
    assert names == [
        "Operational Coordination",
        "Experience in Operational Coordination",
    ]
    assert all("Recruitment" not in name for name in names)


def test_detects_compliance_as_a_general_category_with_domain_label() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Supervisor",
            qualifications=["Past working experience in security operations."],
            responsibilities=[
                "Manage access control and emergency response procedures.",
                "Ensure regulatory compliance and follow company policies.",
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["type"] for item in criteria] == [
        "relevant_skill",
        "relevant_experience",
        "domain_knowledge",
    ]
    assert [item["weight"] for item in criteria] == [40, 33, 27]
    assert criteria[0]["name"] == (
        "Regulatory Compliance and Safety Management"
    )
    assert "Manage access control and emergency response procedures." in (
        criteria[0]["jdEvidence"]
    )
    assert "Ensure regulatory compliance and follow company policies." in (
        criteria[2]["jdEvidence"]
    )
    assert sum(item["weight"] for item in result["data"]["criteria"]) == 100


def test_detects_separate_technical_criteria_from_jd_content() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Software Test Engineer",
            department="Information Technology",
            qualifications=[
                "Experience coding in Java, Python, C# and C++.",
                "Knowledge of SDLC, STLC and Agile practices.",
                "Familiar with Git, Jira and Docker.",
            ],
            responsibilities=[
                "Design software test cases and perform regression and integration testing.",
                "Build test automation using Selenium, Cypress and pytest.",
                "Develop applications and maintain CI/CD pipelines with Jenkins.",
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["type"] for item in criteria] == [
        "relevant_skill",
        "relevant_experience",
        "domain_knowledge",
    ]
    assert [item["weight"] for item in criteria] == [40, 33, 27]
    assert sum(item["weight"] for item in criteria) == 100

    skill = criteria[0]
    assert all(
        responsibility in skill["jdEvidence"]
        for responsibility in (
            "Design software test cases and perform regression and integration testing.",
            "Build test automation using Selenium, Cypress and pytest.",
            "Develop applications and maintain CI/CD pipelines with Jenkins.",
        )
    )
    assert criteria[2]["jdEvidence"] == [
        "Knowledge of SDLC, STLC and Agile practices."
    ]


def test_generic_company_policies_do_not_create_compliance_criterion() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Software Developer",
            qualifications=["Proficient in Python and Git."],
            responsibilities=[
                "Write code and follow company policies and procedures."
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert "compliance" not in [item["category"] for item in criteria]


def test_generic_policy_duties_never_create_a_criterion() -> None:
    ignored = generate_jd_criteria(
        JDCriteriaRequest(
            responsibilities=[
                "Prepare weekly operational reports.",
                "Follow company policies and procedures.",
            ]
        )
    )
    assert not any(
        item["category"] == "job_function_policy_governance"
        for item in ignored["data"]["criteria"]
    )

    major = generate_jd_criteria(
        JDCriteriaRequest(
            responsibilities=[
                "Follow company policies and procedures.",
                "Adhere to internal policies and guidelines.",
                "Prepare weekly operational reports.",
            ]
        )
    )
    assert not any(
        item["category"] == "job_function_policy_governance"
        for item in major["data"]["criteria"]
    )


def test_ignores_generic_duties_and_keeps_only_clear_capability_evidence() -> None:
    meaningful_responsibility = (
        "Conduct root cause analysis and corrective actions for product defects."
    )
    result = generate_jd_criteria(
        JDCriteriaRequest(
            responsibilities=[
                "Perform other duties assigned.",
                "Support management when required.",
                "Follow company policies.",
                "Complete other tasks as instructed.",
                meaningful_responsibility,
            ]
        )
    )

    criteria = result["data"]["criteria"]
    assert len(criteria) == 1
    assert criteria[0]["name"] == "Corrective and Preventive Action"
    assert criteria[0]["jdEvidence"] == [meaningful_responsibility]
    assert criteria[0]["weight"] == 100


def test_does_not_force_unmatched_responsibilities_into_vague_criteria() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            responsibilities=[
                "Assist the team as needed.",
                "Coordinate assigned activities.",
            ]
        )
    )

    assert result["data"]["criteria"] == []
    assert result["warnings"]


def test_merges_overlapping_core_and_supporting_criteria() -> None:
    responsibility = (
        "Coordinate with internal stakeholders on project deliverables."
    )
    qualification = "Strong written and verbal communication skills."
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=[qualification],
            responsibilities=[responsibility],
        )
    )

    criteria = result["data"]["criteria"]
    assert len(criteria) == 1
    assert criteria[0]["name"] == "Stakeholder Coordination"
    assert criteria[0]["category"] == "job_function_stakeholder_coordination"
    assert criteria[0]["jdEvidence"] == [responsibility, qualification]
    assert criteria[0]["weight"] == 100
    assert criteria[0]["explanation"]
    assert criteria[0]["resumeEvidenceToCheck"]


def test_education_is_suggested_and_kept_as_a_low_weight_fit_criterion() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Developer",
            qualifications=[
                "Bachelor Degree in Computer Science with minimum CGPA 3.2."
            ],
            responsibilities=["Develop applications using Java."],
        )
    )

    data = result["data"]
    education = next(
        item for item in data["criteria"] if item["category"] == "education"
    )
    assert education["name"] == "Relevant Academic Background"
    assert education["type"] == "education_relevance"
    assert education["weight"] == 25
    assert data["eligibilitySuggestions"]["educationLevel"] == "Bachelor Degree"
    assert data["eligibilitySuggestions"]["minCGPA"] == 3.2


def test_groups_excel_and_erp_into_a_professional_tool_criterion() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=["Proficient in Microsoft Excel and ERP systems."],
            responsibilities=[
                "Prepare weekly operational reports."
            ]
        )
    )

    criteria = result["data"]["criteria"]
    assert len(criteria) == 1
    assert criteria[0]["type"] == "relevant_skill"
    assert criteria[0]["weight"] == 100
    assert criteria[0]["jdEvidence"] == [
        "Prepare weekly operational reports.",
        "Proficient in Microsoft Excel and ERP systems.",
    ]
    assert "Digital Tools and Systems Proficiency" in criteria[0]["explanation"]


def test_groups_programming_languages_into_one_technical_criterion() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            responsibilities=[
                "Write and review code using JavaScript, TypeScript and C#."
            ]
        )
    )

    technical = next(
        item
        for item in result["data"]["criteria"]
        if item["category"] == "job_function_software_development"
    )
    assert technical["name"] == "Code Development and Review"


def test_groups_procurement_responsibilities_and_academic_field() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=[
                "Minimum Diploma in Supply Chain or Business Administration."
            ],
            responsibilities=["Handle supplier sourcing and price negotiation."],
        )
    )

    criteria = result["data"]["criteria"]
    job_skills = next(
        item for item in criteria if item["category"] == "job_function_procurement"
    )
    education = next(item for item in criteria if item["category"] == "education")
    assert job_skills["name"] == "Supplier Sourcing and Commercial Negotiation"
    assert education["name"] == "Relevant Academic Background"
    assert job_skills["weight"] == 75
    assert education["weight"] == 25
    assert sum(item["weight"] for item in criteria) == 100


def test_extracts_the_main_action_and_object_from_a_responsibility() -> None:
    fact = _responsibility_fact(
        "Manage supplier sourcing and contract negotiations using the ERP system."
    )

    assert fact is not None
    assert fact.action == "Manage"
    assert fact.object == "supplier sourcing and contract negotiations"


def test_groups_similar_responsibilities_into_one_functional_criterion() -> None:
    responsibilities = [
        "Source new suppliers for production materials.",
        "Evaluate vendors based on quality, capacity and delivery performance.",
        "Negotiate prices and contract terms with selected suppliers.",
    ]
    result = generate_jd_criteria(
        JDCriteriaRequest(responsibilities=responsibilities)
    )

    functional = [
        item
        for item in result["data"]["criteria"]
        if item["category"] == "job_function_procurement"
    ]
    assert len(functional) == 1
    assert functional[0]["name"] == "Supplier Sourcing and Commercial Negotiation"
    assert functional[0]["jdEvidence"] == responsibilities


def test_groups_documentation_sentences_into_one_capability_area() -> None:
    responsibilities = [
        "Prepare technical documentation for completed work.",
        "Maintain project records and supporting files.",
        "Archive operational manuals for future reference.",
    ]
    result = generate_jd_criteria(
        JDCriteriaRequest(responsibilities=responsibilities)
    )

    functional = [
        item
        for item in result["data"]["criteria"]
        if item["category"] == "job_function_documentation_records"
    ]
    assert len(functional) == 1
    assert functional[0]["name"] == "Documentation and Record Management"
    assert functional[0]["jdEvidence"] == responsibilities


def test_maps_each_sales_responsibility_to_one_taxonomy_capability() -> None:
    responsibilities = [
        "Maintain customer relationships and follow up customer enquiries.",
        "Prepare quotations and sales proposals for customers.",
        "Achieve monthly and annual sales targets.",
        "Collect market information and competitor updates.",
    ]
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=[
                "Proficient in Microsoft Excel.",
                "Bachelor Degree in Business Administration.",
            ],
            responsibilities=responsibilities,
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["type"] for item in criteria] == [
        "relevant_skill",
        "education_relevance",
    ]
    assert [item["weight"] for item in criteria] == [75, 25]
    assert all(
        sentence in criteria[0]["jdEvidence"]
        for sentence in responsibilities
    )
    assert "Proficient in Microsoft Excel." in criteria[0]["jdEvidence"]
    assert all(
        capability in criteria[0]["explanation"]
        for capability in (
            "Customer Relationship and Account Management",
            "Quotation and Proposal Management",
            "Sales Target Achievement",
            "Market Research and Competitor Analysis",
        )
    )
    assert all(item["explanation"] for item in criteria)
    assert all(item["resumeEvidenceToCheck"] for item in criteria)
    assert len({item["explanation"] for item in criteria}) == len(criteria)


def test_reporting_is_lower_priority_than_a_measurable_core_function() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=["Proficient in Microsoft Excel."],
            responsibilities=[
                "Achieve monthly sales targets.",
                "Prepare weekly sales reports.",
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert len(criteria) == 1
    assert criteria[0]["type"] == "relevant_skill"
    assert criteria[0]["weight"] == 100
    assert all(
        capability in criteria[0]["explanation"]
        for capability in (
            "Sales Target Achievement",
            "Performance Reporting",
            "Digital Tools and Systems Proficiency",
        )
    )


def test_does_not_overweight_an_eligibility_only_jd() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="Trainee",
            qualifications=[
                "Bachelor Degree with minimum CGPA 3.0 and professional certification."
            ],
        )
    )

    criteria = result["data"]["criteria"]
    assert criteria == []
    assert result["data"]["eligibilitySuggestions"]["educationLevel"] == (
        "Bachelor Degree"
    )


def test_does_not_invent_a_generic_criterion_without_responsibility_evidence() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            jobTitle="General Assistant",
            description="Support the team with assigned daily duties.",
        )
    )

    criteria = result["data"]["criteria"]
    assert criteria == []
    assert result["data"]["eligibilitySuggestions"]["enabledFilters"] == []
    assert result["warnings"]


def test_maps_experience_to_existing_filter_options() -> None:
    cases = [
        ("6 years of relevant experience", "5+ years"),
        ("8 years of relevant experience", "8+ years"),
        ("Minimum 10 years of experience", "10+ years"),
    ]

    for qualification, expected in cases:
        result = generate_jd_criteria(
            JDCriteriaRequest(
                jobTitle="Manager",
                qualifications=[qualification],
            )
        )
        assert (
            result["data"]["eligibilitySuggestions"]["minExperience"]
            == expected
        )


def test_all_six_soft_types_use_the_default_base_weights() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=[
                "Bachelor Degree in Human Resources.",
                "At least 3 years of relevant experience.",
                "Knowledge of employment laws and statutory regulations.",
                "SHRM certification would be an added advantage.",
                "Fluent in English.",
            ],
            responsibilities=[
                "Manage recruitment and candidate screening."
            ],
        )
    )

    assert {
        item["type"]: item["weight"]
        for item in result["data"]["criteria"]
    } == {
        "relevant_skill": 30,
        "relevant_experience": 25,
        "domain_knowledge": 20,
        "education_relevance": 10,
        "preferred_certification": 8,
        "job_related_language": 7,
    }


def test_enabled_soft_types_are_normalised_to_one_hundred() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=[
                "Bachelor Degree in Human Resources.",
                "At least 3 years of relevant experience.",
                "Knowledge of employment laws and statutory regulations.",
            ],
            responsibilities=[
                "Manage recruitment and candidate screening."
            ],
        )
    )

    assert {
        item["type"]: item["weight"]
        for item in result["data"]["criteria"]
    } == {
        "relevant_skill": 35,
        "relevant_experience": 29,
        "domain_knowledge": 24,
        "education_relevance": 12,
    }


def test_language_and_certification_are_not_forced() -> None:
    result = generate_jd_criteria(
        JDCriteriaRequest(
            qualifications=["PMP certification is mandatory."],
            responsibilities=["Plan and coordinate project delivery."],
        )
    )

    criteria = result["data"]["criteria"]
    assert [item["type"] for item in criteria] == ["relevant_skill"]
    assert criteria[0]["weight"] == 100
