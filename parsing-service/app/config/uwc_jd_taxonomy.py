"""UWC job-domain taxonomy used only for JD classification and grouping."""

from typing import TypedDict


PatternRule = tuple[str, str]


class CapabilityConfig(TypedDict):
    label: str
    keywords: tuple[str, ...]
    phrases: tuple[str, ...]
    patterns: tuple[PatternRule, ...]


class DomainConfig(TypedDict):
    name: str
    keywords: tuple[str, ...]
    phrases: tuple[str, ...]
    patterns: tuple[str, ...]
    capabilities: dict[str, CapabilityConfig]


# Domain rules support grouping but do not create final criteria.
UWC_JOB_TAXONOMY: dict[str, DomainConfig] = {
    "software_it": {
        "name": "Software and IT",
        "keywords": ("software", "application", "programming", "database", "network", "cloud", "api"),
        "phrases": ("software development", "information technology", "technical support", "quality assurance"),
        "patterns": (r"\b(?:sdlc|stlc|ci\s*/?\s*cd)\b", r"\b(?:java|python|javascript|typescript|c#|c\+\+)\b"),
        "capabilities": {
            "software_development": {
                "label": "Software Development",
                "keywords": ("coding", "programming", "api"),
                "phrases": ("application development", "code review"),
                "patterns": (
                    ("Software and Application Development", r"\b(?:software|application|web|system) development\b|\bdevelop(?:ing|s|ed)? (?:software|applications?|systems?|apis?)\b"),
                    ("Code Development and Review", r"\b(?:write|develop|review|maintain)\w* code\b|\bcoding\b"),
                    ("API Development", r"\b(?:develop|design|integrate|maintain)\w* apis?\b"),
                ),
            },
            "software_testing": {
                "label": "Software Quality and Testing",
                "keywords": ("testing", "defect", "bug"),
                "phrases": ("test case", "quality assurance"),
                "patterns": (
                    (
                        "Test Case Design",
                        r"\b(?:design|create|prepare|write)\w* "
                        r"(?:software )?test (?:cases?|plans?|scripts?|scenarios?)\b",
                    ),
                    ("Software Testing", r"\b(?:software|manual|functional|regression|integration|unit|system|acceptance) testing\b"),
                    ("Defect Management", r"\b(?:identify|track|report|manage|resolve)\w* (?:defects?|bugs?|issues?)\b"),
                ),
            },
            "test_automation": {
                "label": "Test Automation",
                "keywords": ("automation", "selenium", "cypress", "pytest"),
                "phrases": ("test automation", "automated testing", "automation framework"),
                "patterns": (
                    ("Test Automation", r"\b(?:test automation|automated testing|automation testing|automat(?:e|ing) tests?)\b"),
                    ("Automation Framework Development", r"\b(?:build|develop|maintain|create)\w* (?:test )?automation (?:frameworks?|scripts?|suites?)\b"),
                ),
            },
            "it_infrastructure_support": {
                "label": "IT Infrastructure and Support",
                "keywords": ("network", "server", "infrastructure", "helpdesk"),
                "phrases": ("technical support", "system administration", "incident resolution"),
                "patterns": (
                    ("IT Infrastructure Administration", r"\b(?:administer|maintain|manage|monitor)\w* (?:servers?|networks?|infrastructure|cloud systems?)\b"),
                    ("Technical Support and Incident Resolution", r"\b(?:provide|deliver|handle)\w* technical support\b|\bresolve\w* (?:it |system |user )?incidents?\b"),
                ),
            },
        },
    },
    "procurement_sourcing": {
        "name": "Procurement and Sourcing",
        "keywords": ("procurement", "purchasing", "supplier", "vendor", "quotation"),
        "phrases": ("supplier sourcing", "price negotiation", "purchase order", "vendor management"),
        "patterns": (r"\b(?:rfq|rfi|tender)\b", r"\b(?:procure|purchase|source)\w* (?:materials?|components?|services?)\b"),
        "capabilities": {
            "procurement": {
                "label": "Supplier Sourcing and Commercial Negotiation",
                "keywords": ("supplier", "vendor", "sourcing", "negotiation"),
                "phrases": ("supplier sourcing", "price negotiation", "contract negotiation"),
                "patterns": (
                    ("Supplier Sourcing", r"\b(?:supplier|vendor) sourc(?:ing|e)\b|\bsourc(?:ing|e) (?:new )?(?:suppliers?|vendors?)\b|\b(?:identify|evaluate|select)\w* (?:new )?(?:suppliers?|vendors?)\b"),
                    ("Price Negotiation", r"\b(?:price|cost|contract|commercial) negotiations?\b|\bnegotiat(?:e|ing) (?:prices?|costs?|contracts?|terms?)\b"),
                ),
            },
            "purchasing_operations": {
                "label": "Purchasing Operations",
                "keywords": ("purchase", "quotation", "requisition"),
                "phrases": ("purchase order", "purchase requisition", "quotation comparison"),
                "patterns": (
                    ("Purchase Order Management", r"\b(?:prepare|issue|process|manage)\w* purchase orders?\b|\bpurchase requisitions?\b"),
                    ("Quotation and Tender Evaluation", r"\b(?:compare|evaluate|review)\w* (?:supplier |vendor )?(?:quotations?|tenders?|commercial proposals?)\b"),
                ),
            },
            "supplier_management": {
                "label": "Supplier Performance Management",
                "keywords": ("supplier", "vendor", "performance"),
                "phrases": ("supplier performance", "vendor evaluation", "supplier relationship"),
                "patterns": (
                    ("Supplier Performance Management", r"\b(?:supplier|vendor) (?:performance|evaluation|assessment|development)\b"),
                    ("Supplier Relationship Management", r"\b(?:manage|maintain|develop)\w* (?:supplier|vendor) relationships?\b"),
                ),
            },
        },
    },
    "production_planning": {
        "name": "Production Planning",
        "keywords": ("production", "planning", "schedule", "capacity", "material"),
        "phrases": ("production planning", "production schedule", "capacity planning", "material planning"),
        "patterns": (r"\b(?:mrp|master production schedule|production plan)\b",),
        "capabilities": {
            "production_scheduling": {
                "label": "Production Scheduling",
                "keywords": ("schedule", "planning", "output"),
                "phrases": ("production schedule", "daily production plan"),
                "patterns": (
                    ("Production Planning and Scheduling", r"\b(?:plan|prepare|develop|maintain|adjust)\w* (?:daily |weekly |monthly )?production (?:plans?|schedules?)\b"),
                    ("Production Output Coordination", r"\b(?:coordinate|monitor|track)\w* production (?:output|progress|status)\b"),
                ),
            },
            "materials_capacity_planning": {
                "label": "Materials and Capacity Planning",
                "keywords": ("capacity", "material", "manpower"),
                "phrases": ("capacity planning", "material requirements planning", "resource planning"),
                "patterns": (
                    ("Capacity and Resource Planning", r"\b(?:capacity|resource|manpower) planning\b"),
                    ("Material Requirements Planning", r"\b(?:material requirements planning|mrp|plan\w* material requirements?)\b"),
                ),
            },
        },
    },
    "manufacturing": {
        "name": "Manufacturing",
        "keywords": ("manufacturing", "production", "assembly", "machining", "process"),
        "phrases": ("production line", "manufacturing process", "shop floor", "work instruction"),
        "patterns": (r"\b(?:cnc|lean manufacturing|oee|cycle time)\b",),
        "capabilities": {
            "manufacturing_operations": {
                "label": "Manufacturing Operations",
                "keywords": ("production", "assembly", "machining"),
                "phrases": ("production line", "manufacturing operations"),
                "patterns": (
                    ("Manufacturing Operations", r"\b(?:manage|oversee|operate|coordinate|support)\w* (?:manufacturing|production|assembly|machining) (?:operations?|lines?|processes?)\b"),
                    ("Production Process Control", r"\b(?:monitor|control|improve)\w* production processes?\b"),
                ),
            },
            "manufacturing_improvement": {
                "label": "Manufacturing Process Improvement",
                "keywords": ("lean", "productivity", "efficiency", "waste"),
                "phrases": ("continuous improvement", "cycle time reduction", "process optimisation"),
                "patterns": (
                    ("Continuous Improvement", r"\b(?:continuous improvement|lean manufacturing|kaizen)\b"),
                    ("Productivity and Waste Reduction", r"\b(?:improve|increase|optimi[sz]e|reduce)\w* (?:productivity|efficiency|cycle time|waste|scrap)\b"),
                ),
            },
        },
    },
    "engineering": {
        "name": "Engineering",
        "keywords": ("engineering", "design", "drawing", "specification", "technical"),
        "phrases": ("technical drawing", "engineering design", "design verification", "technical specification"),
        "patterns": (r"\b(?:autocad|solidworks|cad|gd&t)\b",),
        "capabilities": {
            "engineering_design": {
                "label": "Engineering Design and Development",
                "keywords": ("design", "drawing", "specification"),
                "phrases": ("engineering design", "technical drawing", "design review"),
                "patterns": (
                    ("Engineering Design", r"\b(?:design|develop|modify|review)\w* (?:products?|components?|fixtures?|systems?)\b"),
                    ("Technical Drawings and Specifications", r"\b(?:prepare|create|review|interpret)\w* (?:technical |engineering )?(?:drawings?|specifications?)\b"),
                ),
            },
            "engineering_projects": {
                "label": "Engineering Project Delivery",
                "keywords": ("project", "prototype", "validation"),
                "phrases": ("engineering project", "design validation", "product development"),
                "patterns": (
                    ("Engineering Project Delivery", r"\b(?:lead|manage|coordinate|deliver)\w* engineering projects?\b"),
                    ("Prototype and Design Validation", r"\b(?:prototype|design validation|engineering validation|verification testing)\b"),
                ),
            },
        },
    },
    "quality_assurance": {
        "name": "Quality Assurance",
        "keywords": ("quality", "inspection", "audit", "defect", "compliance"),
        "phrases": ("quality assurance", "quality control", "root cause analysis", "corrective action"),
        "patterns": (r"\b(?:iso\s*9001|iatf\s*16949|8d|fmea|spc)\b",),
        "capabilities": {
            "quality_management": {
                "label": "Quality Assurance and Control",
                "keywords": ("quality", "inspection", "audit"),
                "phrases": ("quality assurance", "quality inspection", "quality audit"),
                "patterns": (
                    ("Quality Inspection and Control", r"\b(?:quality control|quality inspection|inspect(?:ing)? products?|product quality)\b"),
                    ("Quality Assurance", r"\bquality assurance\b|\bqa processes?\b"),
                    ("Quality Auditing", r"\b(?:conduct|perform|support)\w* (?:quality |internal |supplier )?audits?\b"),
                ),
            },
            "corrective_preventive_action": {
                "label": "Corrective and Preventive Action",
                "keywords": ("corrective", "preventive", "defect", "root cause"),
                "phrases": ("corrective action", "preventive action", "root cause analysis"),
                "patterns": (
                    ("Root Cause Analysis", r"\broot cause analys(?:is|es)\b"),
                    ("Corrective and Preventive Action", r"\b(?:corrective|preventive) actions?\b|\bcapa\b"),
                    ("Defect Reduction", r"\b(?:reduce|resolve|investigate)\w* (?:defects?|non-conformities|quality issues?)\b"),
                ),
            },
        },
    },
    "sales_marketing": {
        "name": "Sales and Marketing",
        "keywords": ("sales", "marketing", "customer", "market", "revenue"),
        "phrases": ("business development", "sales target", "marketing campaign", "key account"),
        "patterns": (r"\b(?:lead generation|customer acquisition|market research)\b",),
        "capabilities": {
            "customer_account_management": {
                "label": "Customer Relationship and Account Management",
                "keywords": ("account", "customer", "client", "enquiry", "payment"),
                "phrases": ("customer relationship", "customer account", "order follow-up", "payment follow-up"),
                "patterns": (
                    ("Customer Relationship Management", r"\b(?:build|maintain|develop|manage)\w* (?:customer|client) relationships?\b"),
                    ("Customer Enquiry Follow-up", r"\b(?:follow up|respond to|handle)\w* (?:customer |client )?(?:enquiries|inquiries|queries)\b"),
                    ("Customer Account Management", r"\b(?:key account management|manage\w* (?:customer|client) accounts?)\b"),
                    ("Order and Payment Follow-up", r"\b(?:follow up|track|monitor)\w* (?:customer )?(?:orders?|payment status|payments?)\b"),
                ),
            },
            "quotation_proposal_management": {
                "label": "Quotation and Proposal Management",
                "keywords": ("quotation", "proposal", "presentation"),
                "phrases": ("sales quotation", "sales proposal", "sales presentation"),
                "patterns": (
                    ("Quotation Preparation", r"\b(?:prepare|create|issue|follow up)\w* (?:sales )?quotations?\b"),
                    (
                        "Sales Proposal Preparation",
                        r"\b(?:prepare|develop|create)\w* "
                        r"(?:quotations? and )?(?:sales |commercial )?proposals?\b",
                    ),
                    ("Sales Presentation Preparation", r"\b(?:prepare|develop|deliver)\w* (?:sales |customer )?presentations?\b"),
                ),
            },
            "sales_performance": {
                "label": "Sales Target Achievement and Performance",
                "keywords": ("sales", "target", "revenue", "performance"),
                "phrases": ("sales target", "monthly sales target", "annual sales target"),
                "patterns": (
                    ("Sales Target Achievement", r"\b(?:achieve|meet|deliver|grow)\w* (?:(?:monthly|annual)(?: and annual)? )?(?:sales|revenue) targets?\b"),
                    ("Sales Performance Management", r"\b(?:monthly |annual )?sales performance\b|\btrack\w* sales results?\b"),
                ),
            },
            "market_analysis": {
                "label": "Market Research and Competitor Analysis",
                "keywords": ("market", "competitor", "trend", "information"),
                "phrases": ("market research", "competitor analysis", "market information"),
                "patterns": (
                    ("Market Information Collection", r"\b(?:collect|gather|analyse|review)\w* market (?:information|data|trends?)\b|\bmarket research\b"),
                    ("Competitor Analysis", r"\b(?:competitor|competition) (?:analysis|updates?|information|activities)\b"),
                ),
            },
            "business_development": {
                "label": "Business Development and Lead Generation",
                "keywords": ("business", "lead", "prospect", "opportunity"),
                "phrases": ("business development", "lead generation", "new business"),
                "patterns": (
                    ("Business Development", r"\bbusiness development\b|\bdevelop(?:ing)? new business\b"),
                    ("Lead Generation", r"\blead generation\b|\bgenerate\w* (?:sales )?leads?\b"),
                ),
            },
            "marketing_execution": {
                "label": "Marketing Campaign Planning and Execution",
                "keywords": ("marketing", "campaign", "brand"),
                "phrases": ("marketing campaign", "digital marketing", "brand promotion"),
                "patterns": (
                    ("Marketing Campaign Execution", r"\b(?:plan|develop|execute|manage)\w* marketing campaigns?\b"),
                ),
            },
        },
    },
    "warehouse_logistics": {
        "name": "Warehouse and Logistics",
        "keywords": ("warehouse", "inventory", "stock", "logistics", "shipment"),
        "phrases": ("inventory control", "warehouse operations", "stock accuracy", "delivery planning"),
        "patterns": (r"\b(?:fifo|wms|cycle count|goods receipt|dispatch)\b",),
        "capabilities": {
            "inventory_control": {
                "label": "Inventory Control",
                "keywords": ("inventory", "stock", "count"),
                "phrases": ("inventory control", "stock accuracy", "cycle count"),
                "patterns": (
                    ("Inventory Accuracy and Control", r"\b(?:manage|monitor|maintain|ensure)\w* (?:inventory|stock) (?:accuracy|levels?|records?|control)\b"),
                    ("Stock Counting and Reconciliation", r"\b(?:cycle counts?|stock counts?|inventory reconciliation)\b"),
                ),
            },
            "warehouse_operations": {
                "label": "Warehouse Operations",
                "keywords": ("warehouse", "receiving", "picking", "packing"),
                "phrases": ("warehouse operations", "goods receiving", "order picking"),
                "patterns": (
                    ("Warehouse Operations", r"\b(?:manage|coordinate|perform|oversee)\w* warehouse operations?\b"),
                    ("Receiving, Picking and Dispatch", r"\b(?:goods receiving|order picking|packing|dispatch(?:ing)?|loading|unloading)\b"),
                ),
            },
            "logistics_distribution": {
                "label": "Logistics and Distribution",
                "keywords": ("logistics", "shipment", "delivery", "transport"),
                "phrases": ("delivery planning", "shipment coordination", "transport management"),
                "patterns": (
                    ("Shipment and Delivery Coordination", r"\b(?:coordinate|plan|track|manage)\w* (?:shipments?|deliveries?|transportation)\b"),
                    ("Logistics Planning", r"\b(?:logistics|distribution|transport) planning\b"),
                ),
            },
        },
    },
    "finance_costing": {
        "name": "Finance and Costing",
        "keywords": ("finance", "accounting", "costing", "budget", "invoice"),
        "phrases": ("financial reporting", "cost analysis", "budget control", "general ledger"),
        "patterns": (r"\b(?:accounts? payable|accounts? receivable|variance analysis|standard costing)\b",),
        "capabilities": {
            "financial_management": {
                "label": "Financial Reporting and Accounting",
                "keywords": ("financial", "accounting", "ledger", "reconciliation"),
                "phrases": ("financial reporting", "general ledger", "account reconciliation"),
                "patterns": (
                    ("Financial Reporting", r"\b(?:prepare|review|analy[sz]e)\w* financial (?:reports?|statements?|results)\b"),
                    ("Accounting Operations", r"\b(?:accounts? payable|accounts? receivable|general ledger|reconciliation|invoicing)\b"),
                ),
            },
            "costing_budget_control": {
                "label": "Costing and Budget Control",
                "keywords": ("costing", "budget", "variance", "margin"),
                "phrases": ("cost analysis", "budget control", "variance analysis", "standard costing"),
                "patterns": (
                    ("Cost Analysis and Control", r"\b(?:cost analysis|cost control|product costing|standard costing)\b"),
                    ("Budget and Variance Management", r"\b(?:budgeting|budget management|budget control|variance analysis)\b"),
                ),
            },
        },
    },
    "maintenance_facilities": {
        "name": "Maintenance and Facilities",
        "keywords": ("maintenance", "facility", "equipment", "repair", "breakdown"),
        "phrases": ("preventive maintenance", "corrective maintenance", "facility management", "equipment reliability"),
        "patterns": (r"\b(?:cmms|mtbf|mttr|machine downtime)\b",),
        "capabilities": {
            "maintenance_engineering": {
                "label": "Equipment Maintenance and Reliability",
                "keywords": ("maintenance", "repair", "equipment", "breakdown"),
                "phrases": ("preventive maintenance", "corrective maintenance", "equipment reliability"),
                "patterns": (
                    ("Equipment Maintenance", r"\b(?:maintain|repair|service|inspect)\w* (?:equipment|machinery|machines?|systems?)\b"),
                    ("Preventive and Corrective Maintenance", r"\b(?:preventive|corrective|planned) maintenance\b"),
                    ("Technical Troubleshooting", r"\b(?:troubleshoot|diagnose|resolve)\w* (?:technical |equipment |system )?(?:issues?|faults?|problems?|breakdowns?)\b"),
                ),
            },
            "facilities_management": {
                "label": "Facilities and Utilities Management",
                "keywords": ("facility", "utilities", "building", "contractor"),
                "phrases": ("facility management", "building maintenance", "utilities management"),
                "patterns": (
                    ("Facilities Maintenance", r"\b(?:manage|maintain|inspect|coordinate)\w* (?:facilities|buildings?|premises)\b"),
                    ("Utilities and Contractor Coordination", r"\b(?:manage|monitor|coordinate)\w* (?:utilities|maintenance contractors?|service providers?)\b"),
                ),
            },
        },
    },
    "human_resources": {
        "name": "Human Resources",
        "keywords": ("recruitment", "employee", "payroll", "hris", "training"),
        "phrases": ("talent acquisition", "employee relations", "performance management", "compensation and benefits"),
        "patterns": (r"\b(?:human resources?|hr operations?|labou?r law)\b",),
        "capabilities": {
            "talent_acquisition": {
                "label": "Talent Acquisition",
                "keywords": ("recruitment", "candidate", "interview", "onboarding"),
                "phrases": ("candidate sourcing", "candidate screening", "interview coordination", "talent acquisition"),
                "patterns": (
                    ("Candidate Sourcing", r"\b(?:candidate sourcing|sourc(?:e|ing) candidates?)\b"),
                    ("Candidate Screening and Shortlisting", r"\b(?:screen(?:ing)?|shortlist(?:ing)?)\s+(?:of\s+)?candidates?\b|\bresume screening\b"),
                    ("Interview Coordination", r"\b(?:conduct|coordinate|arrange|schedule|manage)\w*\s+(?:candidate\s+)?interviews?\b"),
                    ("Candidate Onboarding", r"\b(?:candidate|employee|new hire)?\s*onboarding\b"),
                    ("End-to-End Recruitment", r"\b(?:end-to-end|full[- ]cycle) recruitment\b|\brecruitment (?:process|cycle)\b|\b(?:manage|coordinate|handle)\w* recruitment\b"),
                ),
            },
            "employee_relations": {
                "label": "Employee Relations",
                "keywords": ("employee", "grievance", "disciplinary", "engagement"),
                "phrases": ("employee relations", "disciplinary action", "employee engagement"),
                "patterns": (
                    ("Employee Relations and Engagement", r"\b(?:manage|handle|support)\w* employee relations\b|\bemployee engagement\b"),
                    ("Grievance and Disciplinary Management", r"\b(?:employee grievances?|disciplinary actions?|misconduct cases?)\b"),
                ),
            },
            "hr_operations": {
                "label": "HR Operations",
                "keywords": ("payroll", "hris", "benefits", "attendance"),
                "phrases": ("payroll processing", "hr administration", "compensation and benefits"),
                "patterns": (
                    ("Payroll and HR Administration", r"\b(?:process|manage|administer|support)\w* payroll\b|\bhr administration\b"),
                    ("HRIS and Employee Records", r"\b(?:maintain|manage|update)\w* (?:hris|employee records?)\b"),
                    ("Compensation and Benefits", r"\bcompensation and benefits\b|\bemployee benefits?\b"),
                ),
            },
            "learning_performance": {
                "label": "Learning and Performance Management",
                "keywords": ("training", "learning", "performance", "development"),
                "phrases": ("training needs", "performance appraisal", "employee development"),
                "patterns": (
                    ("Learning and Development", r"\b(?:training needs?|learning and development|employee development)\b"),
                    ("Performance Management", r"\b(?:performance management|performance appraisals?|employee performance reviews?)\b"),
                ),
            },
        },
    },
}


# Generic rules are used when no UWC domain is clear.
GENERIC_CAPABILITY_TAXONOMY: dict[str, CapabilityConfig] = {
    "data_analysis_reporting": {
        "label": "Data Analysis and Performance Reporting",
        "keywords": ("data", "reporting", "dashboard", "insight"),
        "phrases": ("data analysis", "performance reporting", "dashboard development"),
        "patterns": (
            ("Data Analysis", r"\b(?:data|statistical|business) analys(?:is|tics)\b|\banaly[sz](?:e|ing) data\b"),
            (
                "Performance Reporting",
                r"\b(?:prepare|create|develop|produce|maintain)\w* "
                r"(?:[a-z-]+\s+){0,3}reports?\b",
            ),
            (
                "Dashboard Development",
                r"\b(?:prepare|create|develop|produce|maintain)\w* "
                r"(?:[a-z-]+\s+){0,3}dashboards?\b",
            ),
            ("Performance Insights", r"\b(?:present|interpret|communicate)\w* (?:findings|insights|trends|results)\b"),
        ),
    },
    "operations_planning": {
        "label": "Operational Planning and Coordination",
        "keywords": ("operations", "schedule", "resource", "workflow"),
        "phrases": ("operational planning", "resource coordination", "process improvement"),
        "patterns": (
            (
                "Operational Planning",
                r"\bplan\w* (?:daily |business |site |production )?operations?\b",
            ),
            (
                "Operational Coordination",
                r"\bcoordinate\w* (?:daily |business |site |production )?operations?\b",
            ),
            (
                "Operations Management",
                r"\b(?:manage|oversee)\w* (?:daily |business |site |production )?operations?\b",
            ),
            ("Scheduling and Resource Coordination", r"\b(?:schedule|coordinate|allocate)\w* (?:resources?|activities|work|staff|production)\b"),
            ("Process Improvement", r"\b(?:improve|optimi[sz]e|streamline)\w* (?:processes?|workflows?|operations?)\b"),
        ),
    },
    "project_delivery": {
        "label": "Project Planning and Delivery",
        "keywords": ("project", "timeline", "milestone", "deliverable"),
        "phrases": ("project delivery", "project schedule", "risk mitigation"),
        "patterns": (
            ("Project Planning and Delivery", r"\b(?:plan|manage|coordinate|deliver|lead)\w* projects?\b"),
            ("Timeline and Deliverable Management", r"\b(?:timelines?|milestones?|deliverables?|project schedules?)\b"),
            ("Risk and Issue Management", r"\b(?:project risks?|project issues?|risk mitigation)\b"),
        ),
    },
    "customer_service": {
        "label": "Customer Service and Issue Resolution",
        "keywords": ("customer", "service", "complaint", "support"),
        "phrases": ("customer service", "customer support", "issue resolution"),
        "patterns": (
            ("Customer Service and Support", r"\b(?:assist|support|serve|respond to)\w* customers?\b|\bcustomer service\b"),
            ("Customer Issue Resolution", r"\b(?:resolve|handle|manage)\w* (?:customer )?(?:complaints?|queries|issues?)\b"),
            ("Customer Relationship Management", r"\b(?:customer|client) relationship management\b"),
        ),
    },
    "people_management": {
        "label": "Team Leadership and People Management",
        "keywords": ("team", "staff", "employee", "leadership"),
        "phrases": ("team leadership", "performance management", "training and coaching"),
        "patterns": (
            ("Team Leadership and Supervision", r"\b(?:lead|manage|supervise|oversee)\w* (?:a |the )?(?:team|staff|employees?)\b"),
            ("Training and Coaching", r"\b(?:train|coach|mentor|develop)\w* (?:staff|employees?|team members?)\b"),
            ("Performance Management", r"\b(?:manage|review|monitor)\w* (?:staff |employee |team )?performance\b"),
        ),
    },
    "stakeholder_coordination": {
        "label": "Stakeholder Communication and Coordination",
        "keywords": ("stakeholder", "collaboration", "coordination", "liaison"),
        "phrases": ("stakeholder coordination", "cross-functional collaboration", "vendor coordination"),
        "patterns": (
            ("Stakeholder Coordination", r"\b(?:coordinate|liaise|collaborate|communicate|work)\w* with (?:internal |external )?stakeholders?\b"),
            ("Cross-functional Collaboration", r"\bcross-functional (?:collaboration|coordination|teams?)\b"),
            ("Client and Vendor Coordination", r"\b(?:coordinate|liaise|communicate)\w* with (?:clients?|customers?|vendors?|suppliers?)\b"),
        ),
    },
    "documentation_records": {
        "label": "Documentation and Record Management",
        "keywords": ("documentation", "record", "manual", "file"),
        "phrases": ("record management", "technical documentation", "procedure documentation"),
        "patterns": (
            ("Documentation and Record Management", r"\b(?:prepare|create|maintain|update|archive|document|manage)\w* (?:[a-z-]+\s+){0,3}(?:documents?|documentation|records?|manuals?|files?)\b"),
            ("Procedure and Report Documentation", r"\b(?:document|record|maintain)\w* (?:procedures?|findings|results|activities)\b"),
        ),
    },
    "compliance_safety": {
        "label": "Regulatory Compliance and Safety Management",
        "keywords": ("regulatory", "compliance", "safety", "risk"),
        "phrases": ("regulatory compliance", "safety management", "access control"),
        "patterns": (
            ("Regulatory Compliance", r"\b(?:ensure|maintain|monitor|manage)\w* (?:regulatory|legal) compliance\b"),
            ("Safety Management", r"\b(?:manage|ensure|monitor|enforce)\w* (?:workplace |occupational )?safety\b"),
            ("Risk and Access Control", r"\b(?:risk controls?|access control|emergency response)\b"),
        ),
    },
}


SUPPORTING_CAPABILITY_LABELS: dict[str, str] = {
    "tools_systems": "Digital Tools and Systems Proficiency",
    "communication": "Professional Communication and Coordination",
    "compliance": "Regulatory and Standards Knowledge",
    "work_attitude": "Professional Work Attitude",
    "certification": "Relevant Professional Certification",
    "education": "Relevant Academic Background",
    "language": "Professional Language Proficiency",
    "availability": "Work Location Availability",
}
