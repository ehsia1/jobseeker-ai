"""Industry-specific configurations for job searching and templates."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Industry(str, Enum):
    """Supported industries."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    LEGAL = "legal"
    CREATIVE = "creative"
    MARKETING = "marketing"
    EDUCATION = "education"
    ENGINEERING = "engineering"
    SALES = "sales"
    OPERATIONS = "operations"
    GENERAL = "general"


@dataclass
class IndustryConfig:
    """Configuration for a specific industry."""
    name: str
    display_name: str
    description: str
    job_boards: List[str]
    core_skills: List[str]
    certifications: List[str]
    keywords: List[str]
    salary_range: Dict[str, tuple]  # role -> (min, max)
    resume_sections: List[str]
    cover_letter_tone: str
    interview_types: List[str]


# Industry configurations
INDUSTRY_CONFIGS: Dict[str, IndustryConfig] = {
    Industry.TECHNOLOGY: IndustryConfig(
        name="technology",
        display_name="Technology & Software",
        description="Software engineering, data science, DevOps, and IT roles",
        job_boards=[
            "dice", "remoteok", "hackernews", "github_jobs",
            "angellist", "indeed", "linkedin"
        ],
        core_skills=[
            "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust",
            "React", "Node.js", "AWS", "Docker", "Kubernetes", "PostgreSQL",
            "MongoDB", "Redis", "Git", "CI/CD", "Agile", "REST API", "GraphQL",
            "Machine Learning", "TensorFlow", "PyTorch"
        ],
        certifications=[
            "AWS Certified Solutions Architect", "AWS Certified Developer",
            "Google Cloud Professional", "Azure Administrator",
            "Kubernetes Administrator (CKA)", "Terraform Associate",
            "PMP", "Scrum Master (CSM)", "CISSP"
        ],
        keywords=[
            "software engineer", "developer", "full stack", "backend", "frontend",
            "devops", "sre", "data engineer", "ml engineer", "platform engineer"
        ],
        salary_range={
            "junior": (70000, 100000),
            "mid": (100000, 150000),
            "senior": (150000, 220000),
            "staff": (200000, 300000),
            "principal": (250000, 400000),
        },
        resume_sections=[
            "Technical Skills", "Projects", "Experience", "Education",
            "Certifications", "Open Source Contributions"
        ],
        cover_letter_tone="technical_professional",
        interview_types=["technical", "system_design", "behavioral", "coding"],
    ),

    Industry.HEALTHCARE: IndustryConfig(
        name="healthcare",
        display_name="Healthcare & Medical",
        description="Nursing, clinical, medical administration, and healthcare IT roles",
        job_boards=[
            "healthcareers", "indeed", "linkedin", "flexjobs"
        ],
        core_skills=[
            "Patient Care", "EHR/EMR", "Epic", "Cerner", "HIPAA Compliance",
            "Clinical Documentation", "Medication Administration", "Vital Signs",
            "IV Therapy", "Wound Care", "BLS", "ACLS", "PALS",
            "Care Coordination", "Patient Education", "Telehealth"
        ],
        certifications=[
            "RN License", "NP License", "BLS Certification", "ACLS Certification",
            "PALS Certification", "CNA Certification", "Medical Coding (CPC)",
            "CPHIMS", "RHIA", "Epic Certification"
        ],
        keywords=[
            "nurse", "rn", "lpn", "np", "physician", "medical assistant",
            "clinical", "patient care", "healthcare administrator"
        ],
        salary_range={
            "cna": (30000, 45000),
            "lpn": (45000, 60000),
            "rn": (65000, 95000),
            "np": (100000, 140000),
            "manager": (80000, 120000),
        },
        resume_sections=[
            "Licenses & Certifications", "Clinical Experience", "Skills",
            "Education", "Continuing Education", "Specializations"
        ],
        cover_letter_tone="compassionate_professional",
        interview_types=["behavioral", "situational", "competency", "clinical"],
    ),

    Industry.FINANCE: IndustryConfig(
        name="finance",
        display_name="Finance & Banking",
        description="Investment banking, asset management, financial analysis, and fintech roles",
        job_boards=[
            "efinancialcareers", "indeed", "linkedin", "angellist"
        ],
        core_skills=[
            "Financial Modeling", "Excel", "VBA", "Python", "SQL", "Bloomberg",
            "Valuation", "DCF", "LBO", "M&A", "Equity Research", "Fixed Income",
            "Risk Management", "Derivatives", "Portfolio Management",
            "Financial Analysis", "Budgeting", "Forecasting", "FP&A"
        ],
        certifications=[
            "CFA Level I/II/III", "CPA", "FRM", "CAIA", "Series 7",
            "Series 63", "Series 66", "CFP", "Bloomberg Market Concepts"
        ],
        keywords=[
            "analyst", "associate", "investment banking", "private equity",
            "hedge fund", "asset management", "trading", "quantitative"
        ],
        salary_range={
            "analyst": (85000, 150000),
            "associate": (150000, 250000),
            "vp": (250000, 400000),
            "director": (350000, 600000),
            "md": (500000, 1500000),
        },
        resume_sections=[
            "Experience", "Education", "Certifications", "Technical Skills",
            "Deal Experience", "Languages"
        ],
        cover_letter_tone="formal_quantitative",
        interview_types=["technical", "case_study", "behavioral", "fit"],
    ),

    Industry.LEGAL: IndustryConfig(
        name="legal",
        display_name="Legal & Law",
        description="Attorneys, paralegals, legal operations, and compliance roles",
        job_boards=[
            "lawjobs", "indeed", "linkedin", "flexjobs"
        ],
        core_skills=[
            "Legal Research", "Westlaw", "LexisNexis", "Contract Drafting",
            "Litigation", "Corporate Law", "Due Diligence", "Document Review",
            "E-Discovery", "Legal Writing", "Client Counseling",
            "Negotiation", "Compliance", "Regulatory Affairs"
        ],
        certifications=[
            "Bar Admission", "Paralegal Certificate", "eDiscovery Specialist",
            "Compliance Certification", "Contract Management (CCCM)"
        ],
        keywords=[
            "attorney", "lawyer", "counsel", "paralegal", "legal assistant",
            "compliance", "contract manager", "legal operations"
        ],
        salary_range={
            "paralegal": (50000, 85000),
            "associate_1y": (160000, 215000),
            "associate_5y": (250000, 350000),
            "counsel": (200000, 350000),
            "partner": (400000, 2000000),
        },
        resume_sections=[
            "Bar Admissions", "Experience", "Education", "Practice Areas",
            "Publications", "Pro Bono Work", "Professional Affiliations"
        ],
        cover_letter_tone="formal_precise",
        interview_types=["behavioral", "case_study", "writing_sample", "fit"],
    ),

    Industry.CREATIVE: IndustryConfig(
        name="creative",
        display_name="Creative & Design",
        description="UX/UI design, graphic design, content creation, and creative direction roles",
        job_boards=[
            "dribbble", "behance", "angellist", "remoteok",
            "flexjobs", "upwork", "indeed"
        ],
        core_skills=[
            "Figma", "Sketch", "Adobe XD", "Photoshop", "Illustrator",
            "After Effects", "UI Design", "UX Design", "User Research",
            "Prototyping", "Wireframing", "Design Systems", "Typography",
            "Motion Design", "Branding", "Illustration"
        ],
        certifications=[
            "Google UX Design Certificate", "Adobe Certified Expert",
            "Interaction Design Foundation", "Nielsen Norman UX Certification"
        ],
        keywords=[
            "designer", "ux", "ui", "graphic designer", "product designer",
            "creative director", "art director", "visual designer"
        ],
        salary_range={
            "junior": (55000, 75000),
            "mid": (75000, 110000),
            "senior": (110000, 160000),
            "lead": (140000, 200000),
            "director": (180000, 280000),
        },
        resume_sections=[
            "Portfolio Link", "Experience", "Skills & Tools", "Education",
            "Awards & Recognition", "Side Projects"
        ],
        cover_letter_tone="creative_professional",
        interview_types=["portfolio_review", "design_challenge", "behavioral", "whiteboard"],
    ),

    Industry.MARKETING: IndustryConfig(
        name="marketing",
        display_name="Marketing & Growth",
        description="Digital marketing, content marketing, growth, and brand management roles",
        job_boards=[
            "angellist", "remoteok", "indeed", "linkedin", "flexjobs"
        ],
        core_skills=[
            "SEO", "SEM", "Google Analytics", "Google Ads", "Facebook Ads",
            "Content Marketing", "Email Marketing", "Social Media Marketing",
            "Marketing Automation", "HubSpot", "Salesforce", "A/B Testing",
            "Conversion Optimization", "Brand Strategy", "Market Research",
            "Copywriting", "Data Analysis"
        ],
        certifications=[
            "Google Analytics Certification", "Google Ads Certification",
            "HubSpot Inbound Marketing", "Facebook Blueprint",
            "Hootsuite Social Marketing"
        ],
        keywords=[
            "marketing manager", "growth", "digital marketing", "content",
            "brand manager", "seo specialist", "performance marketing"
        ],
        salary_range={
            "coordinator": (45000, 60000),
            "specialist": (55000, 80000),
            "manager": (75000, 120000),
            "director": (120000, 180000),
            "vp": (180000, 300000),
        },
        resume_sections=[
            "Experience", "Key Achievements", "Skills & Tools", "Education",
            "Certifications", "Campaign Highlights"
        ],
        cover_letter_tone="results_driven",
        interview_types=["behavioral", "case_study", "portfolio_review", "analytical"],
    ),

    Industry.EDUCATION: IndustryConfig(
        name="education",
        display_name="Education & Training",
        description="Teaching, instructional design, academic administration, and corporate training roles",
        job_boards=[
            "indeed", "linkedin", "flexjobs", "higheredjobs"
        ],
        core_skills=[
            "Curriculum Development", "Instructional Design", "Lesson Planning",
            "Classroom Management", "Assessment", "Differentiated Instruction",
            "Educational Technology", "LMS Administration", "Canvas", "Blackboard",
            "Student Engagement", "Special Education", "ESL/ELL",
            "Adult Learning", "Corporate Training", "E-Learning Development"
        ],
        certifications=[
            "Teaching License/Certification", "TESOL/TEFL",
            "Instructional Design Certificate", "Google Certified Educator",
            "Apple Teacher", "Microsoft Innovative Educator"
        ],
        keywords=[
            "teacher", "instructor", "professor", "trainer", "instructional designer",
            "curriculum developer", "education coordinator"
        ],
        salary_range={
            "teacher": (45000, 75000),
            "specialist": (55000, 85000),
            "coordinator": (60000, 90000),
            "administrator": (80000, 130000),
            "director": (100000, 160000),
        },
        resume_sections=[
            "Certifications & Licenses", "Teaching Experience", "Education",
            "Professional Development", "Curriculum Projects", "Technology Skills"
        ],
        cover_letter_tone="educational_professional",
        interview_types=["behavioral", "teaching_demo", "situational", "competency"],
    ),

    Industry.SALES: IndustryConfig(
        name="sales",
        display_name="Sales & Business Development",
        description="Sales, account management, business development, and revenue roles",
        job_boards=[
            "angellist", "indeed", "linkedin", "remoteok"
        ],
        core_skills=[
            "Salesforce", "HubSpot CRM", "Lead Generation", "Pipeline Management",
            "Negotiation", "Cold Calling", "Solution Selling", "SPIN Selling",
            "Account Management", "Territory Planning", "Forecasting",
            "Contract Negotiation", "Presentation Skills", "Demo Skills",
            "Objection Handling", "Closing"
        ],
        certifications=[
            "Salesforce Administrator", "HubSpot Sales Certification",
            "Challenger Sale Certification", "SPIN Selling Certification"
        ],
        keywords=[
            "sales", "account executive", "sdr", "bdr", "account manager",
            "sales manager", "business development", "enterprise sales"
        ],
        salary_range={
            "sdr": (50000, 70000),
            "ae": (80000, 150000),
            "senior_ae": (120000, 200000),
            "manager": (130000, 200000),
            "director": (180000, 300000),
        },
        resume_sections=[
            "Sales Achievements", "Experience", "Skills", "Education",
            "Certifications", "Quota Attainment History"
        ],
        cover_letter_tone="persuasive_results",
        interview_types=["behavioral", "role_play", "presentation", "case_study"],
    ),

    Industry.GENERAL: IndustryConfig(
        name="general",
        display_name="General / Other",
        description="General roles across various industries",
        job_boards=[
            "indeed", "linkedin", "flexjobs", "remoteok"
        ],
        core_skills=[
            "Communication", "Problem Solving", "Project Management",
            "Microsoft Office", "Google Workspace", "Time Management",
            "Team Collaboration", "Data Entry", "Customer Service",
            "Administrative Support"
        ],
        certifications=[
            "PMP", "Google Workspace Certification", "Microsoft Office Specialist"
        ],
        keywords=[
            "coordinator", "assistant", "administrator", "analyst", "specialist"
        ],
        salary_range={
            "entry": (35000, 50000),
            "mid": (50000, 75000),
            "senior": (75000, 100000),
            "manager": (80000, 120000),
        },
        resume_sections=[
            "Experience", "Skills", "Education", "Certifications"
        ],
        cover_letter_tone="professional",
        interview_types=["behavioral", "situational", "competency"],
    ),
}


def get_industry_config(industry: str) -> IndustryConfig:
    """Get configuration for a specific industry."""
    industry_lower = industry.lower().replace(" ", "_")

    # Try direct match
    if industry_lower in INDUSTRY_CONFIGS:
        return INDUSTRY_CONFIGS[industry_lower]

    # Try to match by keywords
    for ind, config in INDUSTRY_CONFIGS.items():
        if any(kw in industry_lower for kw in config.keywords):
            return config

    return INDUSTRY_CONFIGS[Industry.GENERAL]


def suggest_industry(keywords: List[str], profession: str = None) -> str:
    """Suggest an industry based on keywords and profession."""
    text = " ".join(keywords).lower()
    if profession:
        text += " " + profession.lower()

    best_match = Industry.GENERAL
    best_score = 0

    for industry, config in INDUSTRY_CONFIGS.items():
        score = sum(1 for kw in config.keywords if kw in text)
        # Bonus for skill matches
        score += sum(0.5 for skill in config.core_skills if skill.lower() in text)

        if score > best_score:
            best_score = score
            best_match = industry

    return best_match


def get_industry_job_boards(industry: str) -> List[str]:
    """Get recommended job boards for an industry."""
    config = get_industry_config(industry)
    return config.job_boards


def get_all_industries() -> List[Dict[str, Any]]:
    """Get list of all supported industries."""
    return [
        {
            "id": config.name,
            "name": config.display_name,
            "description": config.description,
        }
        for config in INDUSTRY_CONFIGS.values()
    ]


# Mapping of professions to industries
PROFESSION_INDUSTRY_MAP = {
    # Technology
    "software_engineer": Industry.TECHNOLOGY,
    "software_developer": Industry.TECHNOLOGY,
    "data_scientist": Industry.TECHNOLOGY,
    "data_analyst": Industry.TECHNOLOGY,
    "devops_engineer": Industry.TECHNOLOGY,
    "frontend_developer": Industry.TECHNOLOGY,
    "backend_developer": Industry.TECHNOLOGY,
    "fullstack_developer": Industry.TECHNOLOGY,
    "mobile_developer": Industry.TECHNOLOGY,
    "machine_learning_engineer": Industry.TECHNOLOGY,
    "product_manager": Industry.TECHNOLOGY,
    "ux_designer": Industry.TECHNOLOGY,
    "qa_engineer": Industry.TECHNOLOGY,
    "security_engineer": Industry.TECHNOLOGY,
    "cloud_architect": Industry.TECHNOLOGY,

    # Healthcare
    "nurse": Industry.HEALTHCARE,
    "registered_nurse": Industry.HEALTHCARE,
    "physician": Industry.HEALTHCARE,
    "doctor": Industry.HEALTHCARE,
    "medical_assistant": Industry.HEALTHCARE,
    "pharmacist": Industry.HEALTHCARE,
    "physical_therapist": Industry.HEALTHCARE,
    "occupational_therapist": Industry.HEALTHCARE,
    "healthcare_administrator": Industry.HEALTHCARE,
    "medical_technologist": Industry.HEALTHCARE,
    "dental_hygienist": Industry.HEALTHCARE,

    # Finance
    "financial_analyst": Industry.FINANCE,
    "accountant": Industry.FINANCE,
    "investment_banker": Industry.FINANCE,
    "portfolio_manager": Industry.FINANCE,
    "risk_analyst": Industry.FINANCE,
    "tax_accountant": Industry.FINANCE,
    "auditor": Industry.FINANCE,
    "controller": Industry.FINANCE,
    "cfo": Industry.FINANCE,
    "treasury_analyst": Industry.FINANCE,

    # Legal
    "attorney": Industry.LEGAL,
    "lawyer": Industry.LEGAL,
    "paralegal": Industry.LEGAL,
    "legal_assistant": Industry.LEGAL,
    "corporate_counsel": Industry.LEGAL,
    "litigation_attorney": Industry.LEGAL,
    "contract_attorney": Industry.LEGAL,
    "compliance_officer": Industry.LEGAL,

    # Marketing/Creative
    "marketing_manager": Industry.MARKETING,
    "brand_manager": Industry.MARKETING,
    "content_strategist": Industry.MARKETING,
    "social_media_manager": Industry.MARKETING,
    "digital_marketer": Industry.MARKETING,
    "copywriter": Industry.MARKETING,
    "graphic_designer": Industry.CREATIVE,
    "art_director": Industry.CREATIVE,
    "creative_director": Industry.CREATIVE,
    "video_producer": Industry.CREATIVE,
    "animator": Industry.CREATIVE,

    # Education
    "teacher": Industry.EDUCATION,
    "professor": Industry.EDUCATION,
    "principal": Industry.EDUCATION,
    "curriculum_developer": Industry.EDUCATION,
    "instructional_designer": Industry.EDUCATION,
    "school_counselor": Industry.EDUCATION,

    # Sales
    "sales_representative": Industry.SALES,
    "account_executive": Industry.SALES,
    "sales_manager": Industry.SALES,
    "business_development": Industry.SALES,
    "sales_director": Industry.SALES,

    # Engineering
    "mechanical_engineer": Industry.ENGINEERING,
    "civil_engineer": Industry.ENGINEERING,
    "electrical_engineer": Industry.ENGINEERING,
    "chemical_engineer": Industry.ENGINEERING,
    "aerospace_engineer": Industry.ENGINEERING,
    "manufacturing_engineer": Industry.ENGINEERING,

    # Operations / General
    "program_manager": Industry.OPERATIONS,
    "operations_manager": Industry.OPERATIONS,
    "project_manager": Industry.OPERATIONS,
    "supply_chain_manager": Industry.OPERATIONS,
    "logistics_coordinator": Industry.OPERATIONS,
}


def get_industry_for_profession(profession: str) -> Optional[Industry]:
    """Get the industry for a given profession.

    Args:
        profession: The profession name (e.g., 'software_engineer', 'nurse')

    Returns:
        Industry enum value if found, None otherwise
    """
    # Normalize the profession string
    normalized = profession.lower().replace(" ", "_").replace("-", "_")

    # Direct lookup
    if normalized in PROFESSION_INDUSTRY_MAP:
        return PROFESSION_INDUSTRY_MAP[normalized]

    # Fuzzy matching - check if profession contains any key
    for prof_key, industry in PROFESSION_INDUSTRY_MAP.items():
        if prof_key in normalized or normalized in prof_key:
            return industry

    # Keyword-based matching as fallback
    keywords = normalized.split("_")
    return Industry(suggest_industry(keywords, normalized))
