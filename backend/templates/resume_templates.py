"""Industry-specific resume templates."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ResumeStyle(str, Enum):
    """Resume formatting styles."""
    TRADITIONAL = "traditional"
    MODERN = "modern"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    ACADEMIC = "academic"


@dataclass
class ResumeSection:
    """A section of a resume template."""
    name: str
    display_name: str
    description: str
    required: bool = True
    order: int = 0
    tips: List[str] = field(default_factory=list)
    example: str = ""


@dataclass
class ResumeTemplate:
    """Industry-specific resume template."""
    id: str
    name: str
    industry: str
    style: ResumeStyle
    description: str
    sections: List[ResumeSection]
    formatting_tips: List[str]
    keywords_to_include: List[str]
    common_mistakes: List[str]
    ats_optimization_tips: List[str]


# Resume templates by industry
RESUME_TEMPLATES: Dict[str, ResumeTemplate] = {
    "tech_software_engineer": ResumeTemplate(
        id="tech_software_engineer",
        name="Software Engineer Resume",
        industry="technology",
        style=ResumeStyle.TECHNICAL,
        description="Technical resume optimized for software engineering roles at tech companies",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact Information",
                description="Name, email, phone, location, LinkedIn, GitHub",
                required=True,
                order=1,
                tips=[
                    "Include GitHub profile link",
                    "Add LinkedIn URL",
                    "City/State only for location (no full address)",
                    "Use professional email address"
                ],
                example="John Smith | john@email.com | (555) 123-4567 | San Francisco, CA | github.com/johnsmith | linkedin.com/in/johnsmith"
            ),
            ResumeSection(
                name="summary",
                display_name="Professional Summary",
                description="2-3 sentence overview highlighting key skills and experience",
                required=False,
                order=2,
                tips=[
                    "Lead with years of experience",
                    "Mention 2-3 key technologies",
                    "Include a notable achievement",
                    "Keep under 50 words"
                ],
                example="Senior Software Engineer with 7+ years building scalable web applications. Expert in Python, TypeScript, and cloud architecture. Led teams delivering products used by 2M+ users."
            ),
            ResumeSection(
                name="skills",
                display_name="Technical Skills",
                description="Categorized list of programming languages, frameworks, tools",
                required=True,
                order=3,
                tips=[
                    "Group by category (Languages, Frameworks, Tools, Cloud)",
                    "List most relevant skills first",
                    "Include version numbers for major frameworks (React 18, Python 3.11)",
                    "Avoid rating skills (no bars or percentages)"
                ],
                example="Languages: Python, TypeScript, Go, SQL | Frameworks: React, FastAPI, Django | Cloud: AWS (EC2, Lambda, RDS), Docker, Kubernetes | Tools: Git, CI/CD, PostgreSQL, Redis"
            ),
            ResumeSection(
                name="experience",
                display_name="Professional Experience",
                description="Work history with quantified achievements",
                required=True,
                order=4,
                tips=[
                    "Start each bullet with strong action verb",
                    "Include metrics: users impacted, performance improvements, cost savings",
                    "Focus on outcomes, not just responsibilities",
                    "Use STAR format for achievements"
                ],
                example="Senior Software Engineer | TechCorp | 2020-Present\n• Architected microservices handling 10M+ daily requests, reducing latency by 40%\n• Led team of 5 engineers building real-time analytics platform\n• Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes"
            ),
            ResumeSection(
                name="projects",
                display_name="Projects",
                description="Notable personal or open-source projects",
                required=False,
                order=5,
                tips=[
                    "Include links to live demos or GitHub repos",
                    "Describe the problem solved and technologies used",
                    "Mention metrics if available (stars, downloads, users)"
                ],
                example="Open Source CLI Tool | github.com/user/project\n• Built command-line tool for API testing with 2K+ GitHub stars\n• Technologies: Go, gRPC, Docker"
            ),
            ResumeSection(
                name="education",
                display_name="Education",
                description="Degrees, bootcamps, relevant certifications",
                required=True,
                order=6,
                tips=[
                    "Include GPA only if 3.5+ and recent graduate",
                    "List relevant coursework for entry-level roles",
                    "Bootcamps and online courses are valid"
                ],
                example="B.S. Computer Science | Stanford University | 2018"
            ),
            ResumeSection(
                name="certifications",
                display_name="Certifications",
                description="Professional certifications",
                required=False,
                order=7,
                tips=["Include cloud certifications (AWS, GCP, Azure)", "Add expiration dates if applicable"],
                example="AWS Solutions Architect Professional | Kubernetes Administrator (CKA)"
            ),
        ],
        formatting_tips=[
            "Keep to 1 page for <10 years experience, 2 pages max",
            "Use consistent formatting and bullet points",
            "Avoid graphics, tables, or columns for ATS compatibility",
            "Use standard fonts: Arial, Calibri, or Georgia",
            "Save as PDF to preserve formatting"
        ],
        keywords_to_include=[
            "Python", "JavaScript", "TypeScript", "React", "Node.js",
            "AWS", "Docker", "Kubernetes", "CI/CD", "Agile", "REST API",
            "microservices", "scalable", "distributed systems"
        ],
        common_mistakes=[
            "Listing every technology ever used instead of relevant ones",
            "No quantified achievements or metrics",
            "Too much focus on responsibilities vs. impact",
            "Outdated technologies listed prominently",
            "Missing GitHub or portfolio link"
        ],
        ats_optimization_tips=[
            "Match keywords from job description",
            "Avoid abbreviations on first use",
            "Use standard section headings",
            "No headers/footers with important info",
            "Plain text formatting, no images"
        ]
    ),

    "healthcare_nurse": ResumeTemplate(
        id="healthcare_nurse",
        name="Registered Nurse Resume",
        industry="healthcare",
        style=ResumeStyle.TRADITIONAL,
        description="Clinical resume for nursing professionals",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact Information",
                description="Name, credentials, contact details",
                required=True,
                order=1,
                tips=["Include nursing credentials after name (RN, BSN, MSN)", "Add state license number"],
                example="Jane Doe, RN, BSN | jane.doe@email.com | (555) 234-5678 | Boston, MA | License: RN123456"
            ),
            ResumeSection(
                name="licenses",
                display_name="Licenses & Certifications",
                description="Active nursing licenses and certifications",
                required=True,
                order=2,
                tips=[
                    "List all active state licenses",
                    "Include BLS, ACLS, PALS certifications with expiration dates",
                    "Add specialty certifications (CCRN, CEN, etc.)"
                ],
                example="RN License: Massachusetts (Active through 2025)\nCertifications: BLS, ACLS, PALS, CCRN"
            ),
            ResumeSection(
                name="summary",
                display_name="Professional Summary",
                description="Overview of nursing experience and specializations",
                required=True,
                order=3,
                tips=[
                    "Lead with years of experience and specialty",
                    "Mention patient population expertise",
                    "Include key clinical skills"
                ],
                example="Dedicated ICU Registered Nurse with 8+ years of critical care experience. Expertise in ventilator management, hemodynamic monitoring, and rapid response. Proven track record of excellent patient outcomes and family-centered care."
            ),
            ResumeSection(
                name="clinical_experience",
                display_name="Clinical Experience",
                description="Nursing work history with patient care details",
                required=True,
                order=4,
                tips=[
                    "Include unit type and bed count",
                    "Describe patient acuity and population",
                    "Quantify: patient ratios, procedures performed",
                    "Highlight leadership and precepting roles"
                ],
                example="Staff Nurse, ICU | Mass General Hospital | 2018-Present\n• Provide comprehensive care for 12-bed Medical ICU, typical ratio 1:2\n• Manage complex patients on ventilators, vasopressors, and CRRT\n• Precept new graduate nurses and nursing students\n• Member of Code Blue and Rapid Response teams"
            ),
            ResumeSection(
                name="skills",
                display_name="Clinical Skills",
                description="Nursing skills and competencies",
                required=True,
                order=5,
                tips=["Include EHR systems (Epic, Cerner)", "List technical skills and equipment"],
                example="EHR: Epic Certified | Skills: IV insertion, Phlebotomy, Foley catheter, NG tube, Wound care, Central line care, Ventilator management, Medication administration"
            ),
            ResumeSection(
                name="education",
                display_name="Education",
                description="Nursing degrees and academic achievements",
                required=True,
                order=6,
                tips=["List highest degree first", "Include honors if applicable"],
                example="Bachelor of Science in Nursing (BSN) | Boston College | 2016\nMagna Cum Laude"
            ),
            ResumeSection(
                name="professional_development",
                display_name="Professional Development",
                description="Continuing education and training",
                required=False,
                order=7,
                tips=["Include CEUs and specialized training", "Add conference presentations"],
                example="NIHSS Stroke Certification | Trauma Nursing Core Course (TNCC)"
            ),
        ],
        formatting_tips=[
            "Keep to 1-2 pages",
            "Use clear section headings",
            "List certifications prominently",
            "Chronological format works best"
        ],
        keywords_to_include=[
            "Patient care", "Assessment", "Documentation", "Medication administration",
            "Care planning", "Patient education", "Team collaboration",
            "Critical thinking", "Emergency response", "HIPAA compliance"
        ],
        common_mistakes=[
            "Not listing license numbers and states",
            "Missing certification expiration dates",
            "Generic descriptions without unit specifics",
            "Not mentioning EHR proficiency",
            "Overlooking leadership experiences"
        ],
        ats_optimization_tips=[
            "Include full certification names, not just acronyms",
            "List specific EHR systems by name",
            "Use standard nursing terminology",
            "Match specialty keywords from job posting"
        ]
    ),

    "finance_analyst": ResumeTemplate(
        id="finance_analyst",
        name="Financial Analyst Resume",
        industry="finance",
        style=ResumeStyle.EXECUTIVE,
        description="Professional resume for finance and banking roles",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact Information",
                description="Professional contact details",
                required=True,
                order=1,
                tips=["Use professional email", "LinkedIn is essential for finance"],
                example="Michael Chen | michael.chen@email.com | (555) 345-6789 | New York, NY | linkedin.com/in/michaelchen"
            ),
            ResumeSection(
                name="summary",
                display_name="Professional Summary",
                description="Career overview highlighting financial expertise",
                required=True,
                order=2,
                tips=[
                    "Quantify deal experience and AUM",
                    "Mention industry focus areas",
                    "Include CFA progress if applicable"
                ],
                example="Investment Banking Associate with 5+ years in Technology M&A. Executed $2B+ in transactions including IPOs, mergers, and debt financings. CFA Level III Candidate. Strong financial modeling and client management skills."
            ),
            ResumeSection(
                name="experience",
                display_name="Professional Experience",
                description="Work history with transaction details",
                required=True,
                order=3,
                tips=[
                    "List notable deals with values",
                    "Describe your specific role and contribution",
                    "Quantify: deal sizes, returns, cost savings",
                    "Use finance-specific terminology"
                ],
                example="Associate | Goldman Sachs, Technology M&A | 2020-Present\n• Executed 8 M&A transactions totaling $1.5B in enterprise value\n• Built complex LBO and DCF models for PE clients\n• Led due diligence workstreams for $500M software acquisition\n• Managed analyst team of 3 on live engagements"
            ),
            ResumeSection(
                name="deal_experience",
                display_name="Select Transaction Experience",
                description="Notable deals worked on",
                required=False,
                order=4,
                tips=["Include deal name, size, your role", "Focus on closed/announced transactions"],
                example="• TechCo acquisition by PE Fund ($500M) - Lead associate, financial modeling\n• SaaS Corp IPO ($200M) - Valuation analysis and investor presentation"
            ),
            ResumeSection(
                name="education",
                display_name="Education",
                description="Degrees with honors and relevant activities",
                required=True,
                order=5,
                tips=["Include GPA if strong (3.5+)", "List finance clubs and competitions"],
                example="MBA | Wharton School | 2020 | GPA: 3.8\nB.S. Finance | NYU Stern | 2016 | GPA: 3.7, Dean's List"
            ),
            ResumeSection(
                name="certifications",
                display_name="Certifications & Licenses",
                description="Professional certifications",
                required=True,
                order=6,
                tips=["CFA status is critical", "Include Series licenses"],
                example="CFA Level III Candidate | Series 7, 63 Licensed"
            ),
            ResumeSection(
                name="skills",
                display_name="Skills",
                description="Technical and analytical skills",
                required=True,
                order=7,
                tips=["Excel proficiency is assumed, mention advanced skills", "Include financial software"],
                example="Financial Modeling: DCF, LBO, M&A | Tools: Bloomberg, Capital IQ, FactSet | Excel: VBA, Power Query | Languages: Python (pandas), SQL"
            ),
        ],
        formatting_tips=[
            "1 page for <5 years experience, 2 pages max",
            "Clean, professional formatting",
            "Use tables for deal lists if needed",
            "Conservative fonts and colors"
        ],
        keywords_to_include=[
            "Financial modeling", "Valuation", "M&A", "Due diligence",
            "DCF", "LBO", "IPO", "Pitch books", "Client management",
            "Bloomberg", "Excel", "Financial analysis"
        ],
        common_mistakes=[
            "Not quantifying deal experience",
            "Missing CFA or licensing status",
            "Vague descriptions without deal specifics",
            "Not tailoring to specific finance sub-sector"
        ],
        ats_optimization_tips=[
            "Spell out abbreviations first time",
            "Include both technical and soft skills",
            "Match terminology from job description",
            "Use standard financial terms"
        ]
    ),

    "legal_attorney": ResumeTemplate(
        id="legal_attorney",
        name="Attorney Resume",
        industry="legal",
        style=ResumeStyle.TRADITIONAL,
        description="Professional resume for attorneys and legal professionals",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact Information",
                description="Professional contact details",
                required=True,
                order=1,
                tips=["Include bar admission states"],
                example="Sarah Johnson, Esq. | sarah.johnson@firm.com | (555) 456-7890 | New York, NY"
            ),
            ResumeSection(
                name="bar_admissions",
                display_name="Bar Admissions",
                description="State bar admissions and court admissions",
                required=True,
                order=2,
                tips=["List all active jurisdictions", "Include federal court admissions"],
                example="Bar Admissions: New York (2018), California (2020)\nCourt Admissions: U.S. District Court, Southern District of New York"
            ),
            ResumeSection(
                name="experience",
                display_name="Legal Experience",
                description="Law firm and legal work history",
                required=True,
                order=3,
                tips=[
                    "Describe practice areas and case types",
                    "Highlight significant matters",
                    "Quantify: case values, team sizes",
                    "Include pro bono work"
                ],
                example="Associate | Kirkland & Ellis LLP | 2018-Present\n• Handle complex commercial litigation matters in federal and state courts\n• First-chaired 5 depositions and argued 3 discovery motions\n• Led document review team of 10 attorneys for $50M breach of contract case\n• Drafted successful motion to dismiss in securities fraud matter"
            ),
            ResumeSection(
                name="education",
                display_name="Education",
                description="Law school and undergraduate education",
                required=True,
                order=4,
                tips=[
                    "Include law review/journal membership",
                    "List moot court and honors",
                    "GPA if strong"
                ],
                example="J.D. | Columbia Law School | 2018\n• Columbia Law Review, Senior Editor\n• Stone Scholar (top 10%)\nB.A. Political Science | Yale University | 2015 | Magna Cum Laude"
            ),
            ResumeSection(
                name="publications",
                display_name="Publications & Speaking",
                description="Legal publications and presentations",
                required=False,
                order=5,
                tips=["Include law review articles", "Add CLE presentations"],
                example="'Recent Developments in Securities Litigation,' Columbia Law Review, 2018"
            ),
            ResumeSection(
                name="skills",
                display_name="Skills",
                description="Legal research tools and languages",
                required=True,
                order=6,
                tips=["Include Westlaw/LexisNexis", "List e-discovery platforms"],
                example="Research: Westlaw, LexisNexis | E-Discovery: Relativity, Concordance | Languages: Spanish (fluent)"
            ),
        ],
        formatting_tips=[
            "1-2 pages maximum",
            "Conservative, traditional format",
            "Use legal-standard fonts (Times New Roman, Garamond)",
            "Clear hierarchy of information"
        ],
        keywords_to_include=[
            "Litigation", "Legal research", "Brief writing", "Depositions",
            "Motion practice", "Discovery", "Due diligence", "Contract drafting",
            "Client counseling", "Westlaw", "LexisNexis"
        ],
        common_mistakes=[
            "Not listing bar admissions prominently",
            "Missing law school honors/activities",
            "Vague practice area descriptions",
            "Not highlighting significant matters"
        ],
        ats_optimization_tips=[
            "Use standard legal terminology",
            "Include practice area keywords",
            "Spell out court names fully",
            "Match firm's practice area naming"
        ]
    ),

    "creative_designer": ResumeTemplate(
        id="creative_designer",
        name="UX/Product Designer Resume",
        industry="creative",
        style=ResumeStyle.CREATIVE,
        description="Design-focused resume for UX, UI, and product designers",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact & Portfolio",
                description="Contact info with portfolio link",
                required=True,
                order=1,
                tips=[
                    "Portfolio link is essential",
                    "Include Dribbble/Behance if active",
                    "Personal website preferred"
                ],
                example="Alex Rivera | alex@design.com | (555) 567-8901 | San Francisco, CA\nPortfolio: alexrivera.design | Dribbble: dribbble.com/alexrivera"
            ),
            ResumeSection(
                name="summary",
                display_name="Design Summary",
                description="Brief overview of design philosophy and experience",
                required=True,
                order=2,
                tips=[
                    "Mention design specialties",
                    "Include notable companies/products",
                    "Keep it authentic to your voice"
                ],
                example="Product Designer with 6+ years crafting intuitive digital experiences. Passionate about user-centered design and design systems. Led design for products reaching 5M+ users at Airbnb and Stripe."
            ),
            ResumeSection(
                name="experience",
                display_name="Design Experience",
                description="Work history with project highlights",
                required=True,
                order=3,
                tips=[
                    "Focus on impact and outcomes",
                    "Describe the problem you solved",
                    "Include metrics where possible",
                    "Reference portfolio for visuals"
                ],
                example="Senior Product Designer | Airbnb | 2020-Present\n• Redesigned host onboarding flow, increasing completion rate by 35%\n• Established design system components used across 15+ product teams\n• Led user research initiatives with 100+ participant studies\n• Mentored 3 junior designers"
            ),
            ResumeSection(
                name="skills",
                display_name="Design Skills & Tools",
                description="Design tools and methodologies",
                required=True,
                order=4,
                tips=[
                    "Organize by category",
                    "Include both tools and methods",
                    "Mention collaboration tools"
                ],
                example="Design: Figma, Sketch, Adobe CC, Framer | Prototyping: Principle, ProtoPie, Origami | Research: UserTesting, Maze, Dovetail | Methods: Design Thinking, Jobs-to-be-Done, Design Sprints"
            ),
            ResumeSection(
                name="projects",
                display_name="Select Projects",
                description="Notable design projects with links",
                required=False,
                order=5,
                tips=[
                    "Include case study links",
                    "Describe your role and impact",
                    "Choose diverse project types"
                ],
                example="Mobile Banking Redesign | Case Study: portfolio.com/banking\n• Led end-to-end redesign increasing mobile deposits by 50%\n• Created comprehensive design system with 200+ components"
            ),
            ResumeSection(
                name="education",
                display_name="Education",
                description="Design education and certifications",
                required=True,
                order=6,
                tips=["Include design bootcamps", "List relevant courses"],
                example="B.F.A. Interaction Design | RISD | 2016\nGoogle UX Design Certificate | 2020"
            ),
        ],
        formatting_tips=[
            "Clean, modern layout that showcases design sensibility",
            "Consistent use of typography and spacing",
            "Subtle use of color is acceptable",
            "Ensure ATS compatibility if applying through job boards",
            "Have both designed PDF and plain-text versions"
        ],
        keywords_to_include=[
            "UX design", "UI design", "User research", "Prototyping",
            "Design systems", "Figma", "User testing", "Wireframing",
            "Information architecture", "Interaction design"
        ],
        common_mistakes=[
            "Missing portfolio link",
            "Over-designed resume that's not ATS-friendly",
            "Not quantifying design impact",
            "Listing tools without showing expertise",
            "No mention of research/validation"
        ],
        ats_optimization_tips=[
            "Include plain-text version for ATS",
            "Use standard headings alongside creative ones",
            "Include skills in text, not just icons",
            "Avoid putting important info in graphics"
        ]
    ),

    "marketing_manager": ResumeTemplate(
        id="marketing_manager",
        name="Marketing Manager Resume",
        industry="marketing",
        style=ResumeStyle.MODERN,
        description="Results-driven resume for marketing professionals",
        sections=[
            ResumeSection(
                name="contact",
                display_name="Contact Information",
                description="Professional contact with LinkedIn",
                required=True,
                order=1,
                tips=["LinkedIn is essential", "Include portfolio if applicable"],
                example="Jennifer Lee | jennifer.lee@email.com | (555) 678-9012 | Austin, TX | linkedin.com/in/jenniferlee"
            ),
            ResumeSection(
                name="summary",
                display_name="Professional Summary",
                description="Marketing expertise and achievements overview",
                required=True,
                order=2,
                tips=[
                    "Lead with quantified results",
                    "Mention key channels/specialties",
                    "Include industry focus"
                ],
                example="Data-driven Marketing Manager with 8+ years driving growth for B2B SaaS companies. Generated $15M+ pipeline through integrated campaigns. Expert in demand generation, content marketing, and marketing automation."
            ),
            ResumeSection(
                name="experience",
                display_name="Professional Experience",
                description="Marketing roles with campaign results",
                required=True,
                order=3,
                tips=[
                    "Quantify everything: leads, revenue, ROI, growth",
                    "Describe campaigns and their outcomes",
                    "Include team size if managing",
                    "Show progression"
                ],
                example="Senior Marketing Manager | HubSpot | 2019-Present\n• Manage $2M annual budget across paid, content, and events channels\n• Increased MQL volume by 150% YoY through multi-channel campaigns\n• Built and led team of 4 marketing specialists\n• Achieved 4.5x ROI on paid acquisition programs"
            ),
            ResumeSection(
                name="skills",
                display_name="Marketing Skills",
                description="Tools, platforms, and competencies",
                required=True,
                order=4,
                tips=["Include marketing tech stack", "Show analytics capabilities"],
                example="Platforms: HubSpot, Salesforce, Google Analytics, Tableau | Channels: SEO/SEM, Paid Social, Content, Email, Events | Skills: Marketing Automation, A/B Testing, Attribution Modeling, Budget Management"
            ),
            ResumeSection(
                name="achievements",
                display_name="Key Achievements",
                description="Notable campaign wins and recognitions",
                required=False,
                order=5,
                tips=["Highlight award-winning campaigns", "Include internal recognitions"],
                example="• 'Best B2B Campaign' - Content Marketing Awards 2022\n• Promoted twice in 3 years for exceeding pipeline targets"
            ),
            ResumeSection(
                name="education",
                display_name="Education & Certifications",
                description="Marketing education and certifications",
                required=True,
                order=6,
                tips=["Include marketing certifications", "List relevant coursework"],
                example="MBA, Marketing | UT Austin | 2016\nCertifications: Google Analytics, HubSpot Inbound, Facebook Blueprint"
            ),
        ],
        formatting_tips=[
            "1-2 pages with strong metrics",
            "Use data and numbers prominently",
            "Clean, modern formatting",
            "Easy to scan for key achievements"
        ],
        keywords_to_include=[
            "Demand generation", "Lead generation", "Marketing automation",
            "Content marketing", "SEO", "SEM", "Paid media", "ROI",
            "Pipeline", "Conversion rate", "A/B testing", "Analytics"
        ],
        common_mistakes=[
            "Not quantifying marketing impact",
            "Vague campaign descriptions",
            "Missing marketing tech proficiency",
            "Not showing business impact (revenue, leads)"
        ],
        ats_optimization_tips=[
            "Include both abbreviations and full terms (SEO, Search Engine Optimization)",
            "Use industry-standard metric terms",
            "Match job description keywords",
            "Include tool names explicitly"
        ]
    ),
}


def get_resume_template(template_id: str) -> Optional[ResumeTemplate]:
    """Get a specific resume template by ID."""
    return RESUME_TEMPLATES.get(template_id)


def get_resume_templates_for_industry(industry: str) -> List[ResumeTemplate]:
    """Get all resume templates for a specific industry."""
    industry_lower = industry.lower()
    return [
        template for template in RESUME_TEMPLATES.values()
        if industry_lower in template.industry.lower()
    ]


def get_all_resume_templates() -> List[ResumeTemplate]:
    """Get all available resume templates."""
    return list(RESUME_TEMPLATES.values())
