"""Industry-specific cover letter templates and guidance."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class CoverLetterTone(str, Enum):
    """Tone styles for cover letters."""
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    ENTHUSIASTIC = "enthusiastic"


class CoverLetterFormat(str, Enum):
    """Format styles for cover letters."""
    TRADITIONAL = "traditional"
    MODERN = "modern"
    STORYTELLING = "storytelling"
    PROBLEM_SOLUTION = "problem_solution"
    ACHIEVEMENT_FOCUSED = "achievement_focused"


@dataclass
class CoverLetterSection:
    """Represents a section in a cover letter template."""
    name: str
    display_name: str
    description: str
    word_count_range: tuple = (50, 100)
    tips: List[str] = field(default_factory=list)
    example: str = ""
    required: bool = True


@dataclass
class CoverLetterTemplate:
    """Complete cover letter template for an industry/role."""
    id: str
    name: str
    industry: str
    role_type: str
    tone: CoverLetterTone
    format: CoverLetterFormat
    sections: List[CoverLetterSection]
    opening_hooks: List[str]
    closing_statements: List[str]
    keywords_to_include: List[str]
    phrases_to_avoid: List[str]
    formatting_tips: List[str]
    length_guidance: str
    personalization_tips: List[str]


# Define cover letter templates by industry

TECH_SOFTWARE_ENGINEER_COVER_LETTER = CoverLetterTemplate(
    id="tech_software_engineer",
    name="Software Engineer Cover Letter",
    industry="technology",
    role_type="software_engineer",
    tone=CoverLetterTone.PROFESSIONAL,
    format=CoverLetterFormat.ACHIEVEMENT_FOCUSED,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information and date",
            word_count_range=(0, 0),
            tips=[
                "Include email, phone, LinkedIn, and GitHub",
                "Match header style with your resume",
            ],
            example="John Smith | john@email.com | (555) 123-4567 | github.com/johnsmith",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Paragraph",
            description="Introduce yourself and state the position",
            word_count_range=(40, 80),
            tips=[
                "Mention the specific role and company name",
                "Include a compelling hook about your experience",
                "Reference how you found the position if relevant",
            ],
            example="As a full-stack engineer with 5 years of experience building scalable web applications, I'm excited to apply for the Senior Software Engineer position at [Company]. Your recent work on [specific project/technology] aligns perfectly with my expertise in distributed systems.",
        ),
        CoverLetterSection(
            name="technical_fit",
            display_name="Technical Fit",
            description="Highlight relevant technical skills and projects",
            word_count_range=(80, 150),
            tips=[
                "Match your skills to job requirements",
                "Quantify achievements (performance improvements, scale)",
                "Mention specific technologies from the job posting",
                "Reference 1-2 relevant projects with measurable outcomes",
            ],
            example="In my current role at [Company], I led the migration of our monolithic application to microservices, reducing deployment time by 60% and improving system reliability to 99.9% uptime. I've built production systems using Python, Go, and TypeScript, and have hands-on experience with AWS, Kubernetes, and the CI/CD practices you're looking for.",
        ),
        CoverLetterSection(
            name="culture_fit",
            display_name="Culture & Team Fit",
            description="Show alignment with company values and team",
            word_count_range=(50, 100),
            tips=[
                "Research company values and mission",
                "Mention collaboration and teamwork examples",
                "Show enthusiasm for the company's products/mission",
            ],
            example="I'm particularly drawn to [Company]'s commitment to [specific value/mission]. In my experience mentoring junior developers and contributing to open-source projects, I've found that collaborative environments bring out the best engineering solutions.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Call to action and thank you",
            word_count_range=(30, 60),
            tips=[
                "Express enthusiasm for next steps",
                "Include availability for interviews",
                "Thank them for their consideration",
            ],
            example="I'd love the opportunity to discuss how my experience can contribute to your team's goals. I'm available for a conversation at your convenience. Thank you for considering my application.",
        ),
    ],
    opening_hooks=[
        "As a [X]-year veteran of building scalable systems...",
        "Having contributed to open-source projects with [X]+ stars...",
        "After leading the development of [specific achievement]...",
        "Your recent blog post about [topic] resonated with my experience in...",
    ],
    closing_statements=[
        "I'm excited about the possibility of contributing to [Company]'s engineering team.",
        "I look forward to discussing how my skills align with your team's goals.",
        "I'd welcome the chance to explore how I can help [Company] achieve [specific goal].",
    ],
    keywords_to_include=[
        "scalable", "production", "collaborative", "agile",
        "test-driven", "code review", "mentorship", "architecture",
    ],
    phrases_to_avoid=[
        "I think I would be good at this job",
        "I need a job",
        "I'm a hard worker",
        "I'm a team player",
        "Dear Sir/Madam",
        "To Whom It May Concern",
    ],
    formatting_tips=[
        "Keep to one page (300-400 words)",
        "Use the same font as your resume",
        "Include hyperlinks to portfolio/GitHub",
        "PDF format preserves formatting",
    ],
    length_guidance="300-400 words, one page maximum",
    personalization_tips=[
        "Reference specific products or projects the company has built",
        "Mention technologies from the job posting",
        "Connect your experience to their tech stack",
        "Research the hiring manager if known",
    ],
)

HEALTHCARE_NURSE_COVER_LETTER = CoverLetterTemplate(
    id="healthcare_nurse",
    name="Registered Nurse Cover Letter",
    industry="healthcare",
    role_type="nurse",
    tone=CoverLetterTone.PROFESSIONAL,
    format=CoverLetterFormat.TRADITIONAL,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information and credentials",
            word_count_range=(0, 0),
            tips=[
                "Include RN license number and state",
                "List relevant certifications (BLS, ACLS, etc.)",
            ],
            example="Jane Doe, RN, BSN | jane.doe@email.com | (555) 123-4567 | License #RN12345",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Paragraph",
            description="State your qualifications and interest",
            word_count_range=(40, 80),
            tips=[
                "Mention your nursing credentials and specialty",
                "State the specific position and unit",
                "Express genuine interest in the facility",
            ],
            example="As a Registered Nurse with 6 years of ICU experience and current ACLS/PALS certifications, I am writing to express my interest in the Critical Care Nurse position at [Hospital]. Your facility's Magnet designation and commitment to patient-centered care align with my professional values.",
        ),
        CoverLetterSection(
            name="clinical_experience",
            display_name="Clinical Experience",
            description="Highlight relevant nursing experience",
            word_count_range=(80, 150),
            tips=[
                "Describe patient populations you've worked with",
                "Mention EHR systems you're proficient in (Epic, Cerner)",
                "Include specific clinical skills and procedures",
                "Quantify when possible (patient ratios, outcomes)",
            ],
            example="In my current role at [Hospital], I provide comprehensive care for critically ill patients with complex conditions including sepsis, respiratory failure, and post-surgical complications. I've maintained a 95% patient satisfaction score while managing 4:1 patient ratios. My proficiency with Epic EHR has streamlined documentation, allowing more time for direct patient care.",
        ),
        CoverLetterSection(
            name="soft_skills",
            display_name="Communication & Collaboration",
            description="Demonstrate teamwork and patient communication",
            word_count_range=(50, 100),
            tips=[
                "Highlight interdisciplinary collaboration",
                "Mention patient/family communication skills",
                "Include any leadership or preceptor experience",
            ],
            example="I believe nursing excellence extends beyond clinical skills. I've served as a charge nurse and preceptor for new graduates, and I regularly collaborate with physicians, therapists, and case managers to ensure seamless patient care. Families consistently note my ability to explain complex medical situations in understandable terms.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Express enthusiasm and availability",
            word_count_range=(30, 60),
            tips=[
                "Mention shift flexibility if applicable",
                "Express commitment to the facility's mission",
                "Thank them for the opportunity",
            ],
            example="I would welcome the opportunity to contribute to [Hospital]'s exceptional care team. I am available for all shifts and can start within two weeks. Thank you for considering my application.",
        ),
    ],
    opening_hooks=[
        "With [X] years of dedicated experience in [specialty] nursing...",
        "As a Magnet-trained nurse passionate about [specialty] care...",
        "Having earned recognition for [specific achievement]...",
        "Your hospital's reputation for [specific quality] inspired me to apply...",
    ],
    closing_statements=[
        "I am committed to upholding [Hospital]'s standards of excellence.",
        "I look forward to the opportunity to serve your patient community.",
        "I would be honored to contribute to your care team's mission.",
    ],
    keywords_to_include=[
        "patient-centered", "evidence-based", "interdisciplinary",
        "compassionate", "clinical excellence", "quality improvement",
        "patient safety", "advocacy",
    ],
    phrases_to_avoid=[
        "I need a change of scenery",
        "I'm burned out at my current job",
        "I want better hours",
        "I don't like my current manager",
    ],
    formatting_tips=[
        "Include license number in header or opening",
        "List relevant certifications prominently",
        "Keep to one page",
        "Use professional, easy-to-read font",
    ],
    length_guidance="250-350 words, one page",
    personalization_tips=[
        "Research the unit/department you're applying to",
        "Mention any awards or recognitions the facility has received",
        "Reference specific programs or initiatives they offer",
        "Connect your specialty experience to their patient population",
    ],
)

FINANCE_ANALYST_COVER_LETTER = CoverLetterTemplate(
    id="finance_analyst",
    name="Financial Analyst Cover Letter",
    industry="finance",
    role_type="analyst",
    tone=CoverLetterTone.FORMAL,
    format=CoverLetterFormat.ACHIEVEMENT_FOCUSED,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information",
            word_count_range=(0, 0),
            tips=[
                "Use professional email address",
                "Include LinkedIn profile",
            ],
            example="Michael Chen | michael.chen@email.com | (555) 123-4567 | linkedin.com/in/michaelchen",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Paragraph",
            description="State position and key qualification",
            word_count_range=(40, 80),
            tips=[
                "Mention the specific role and firm name",
                "Lead with your strongest credential (CFA, MBA, etc.)",
                "Reference a referral if applicable",
            ],
            example="As a CFA charterholder with 4 years of equity research experience, I am applying for the Senior Financial Analyst position at [Firm]. My background in technology sector coverage and financial modeling aligns directly with your team's focus.",
        ),
        CoverLetterSection(
            name="quantitative_achievements",
            display_name="Quantitative Achievements",
            description="Highlight measurable accomplishments",
            word_count_range=(80, 150),
            tips=[
                "Lead with numbers and results",
                "Mention deals, AUM, or coverage universe size",
                "Include modeling and technical skills",
                "Reference specific transactions if possible",
            ],
            example="At [Current Firm], I cover a $15B technology sector portfolio and have delivered stock recommendations with 23% average outperformance versus benchmark. I built the DCF and LBO models for our team's analysis of a $2.4B acquisition, which informed our buy recommendation 3 months before the announcement. My financial modeling skills in Excel and Python have reduced report generation time by 40%.",
        ),
        CoverLetterSection(
            name="industry_knowledge",
            display_name="Industry Knowledge",
            description="Demonstrate market understanding",
            word_count_range=(50, 100),
            tips=[
                "Show knowledge of their specific market/sector",
                "Mention relevant trends or insights",
                "Demonstrate analytical thinking",
            ],
            example="I've closely followed [Firm]'s research on emerging market fintech, and I believe my experience analyzing SaaS business models and recurring revenue metrics would complement your coverage expansion. The sector's transition to embedded finance presents significant alpha generation opportunities.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Professional close and call to action",
            word_count_range=(30, 60),
            tips=[
                "Maintain formal tone",
                "Express interest in discussing further",
                "Thank them professionally",
            ],
            example="I would welcome the opportunity to discuss how my analytical skills and sector expertise can contribute to [Firm]'s research excellence. Thank you for your consideration.",
        ),
    ],
    opening_hooks=[
        "As a CFA charterholder with [X] years in [specialty]...",
        "Having analyzed [X]+ companies across [sector]...",
        "[Referral name] suggested I reach out regarding...",
        "Your firm's recent research on [topic] demonstrated the analytical rigor I seek...",
    ],
    closing_statements=[
        "I look forward to discussing how I can contribute to your team's success.",
        "I am eager to bring my analytical expertise to [Firm].",
        "I would welcome the opportunity to discuss my qualifications further.",
    ],
    keywords_to_include=[
        "quantitative analysis", "financial modeling", "due diligence",
        "risk assessment", "portfolio management", "valuation",
        "Bloomberg", "capital markets",
    ],
    phrases_to_avoid=[
        "I am passionate about finance",
        "I want to make a lot of money",
        "I love working with numbers",
        "I'm a detail-oriented person",
    ],
    formatting_tips=[
        "Conservative formatting - no creative elements",
        "One page maximum",
        "Standard business letter format",
        "PDF format only",
    ],
    length_guidance="250-350 words, strict one page limit",
    personalization_tips=[
        "Reference specific research the firm has published",
        "Mention relevant deals or transactions they've worked on",
        "Show knowledge of their portfolio companies or coverage",
        "Research the hiring manager's background",
    ],
)

LEGAL_ATTORNEY_COVER_LETTER = CoverLetterTemplate(
    id="legal_attorney",
    name="Attorney Cover Letter",
    industry="legal",
    role_type="attorney",
    tone=CoverLetterTone.FORMAL,
    format=CoverLetterFormat.TRADITIONAL,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information and bar admissions",
            word_count_range=(0, 0),
            tips=[
                "Include bar admission states",
                "List law school and class year",
            ],
            example="Sarah Johnson, Esq. | sarah.johnson@email.com | (555) 123-4567 | Bar: NY, CA",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Paragraph",
            description="State position and qualifications",
            word_count_range=(40, 80),
            tips=[
                "Mention the specific position and firm",
                "Include years of experience and practice area",
                "Reference a connection if you have one",
            ],
            example="I am writing to express my interest in the Senior Associate position in the Corporate Practice Group at [Firm]. As a fifth-year corporate attorney with extensive M&A experience at a leading Am Law 100 firm, I am drawn to [Firm]'s reputation for sophisticated transactions and collaborative culture.",
        ),
        CoverLetterSection(
            name="legal_experience",
            display_name="Legal Experience",
            description="Detail relevant legal work and matters",
            word_count_range=(80, 150),
            tips=[
                "Describe types of matters and deal sizes",
                "Mention notable clients or industries (without breaching confidentiality)",
                "Highlight specific legal skills and areas of expertise",
                "Reference substantive legal work, not just hours billed",
            ],
            example="At [Current Firm], I have represented private equity sponsors and strategic acquirers in over 30 M&A transactions totaling $4.5B in aggregate deal value. My experience spans due diligence, negotiating purchase agreements, and managing cross-border regulatory filings. I recently served as lead associate on a $600M carve-out acquisition, coordinating a team of 8 attorneys across multiple jurisdictions.",
        ),
        CoverLetterSection(
            name="firm_fit",
            display_name="Firm Fit",
            description="Explain why this specific firm",
            word_count_range=(50, 100),
            tips=[
                "Research the firm's recent matters and clients",
                "Mention practice group strengths",
                "Show genuine interest in their specific work",
            ],
            example="I am particularly attracted to [Firm]'s healthcare and technology sector focus, which aligns with my experience advising digital health companies. Your firm's recent representation of [public transaction or client type] exemplifies the complex, high-stakes work I find most engaging.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Formal close",
            word_count_range=(30, 50),
            tips=[
                "Maintain formal tone throughout",
                "Express genuine interest in the opportunity",
                "Thank them appropriately",
            ],
            example="I would welcome the opportunity to discuss how my experience can contribute to [Firm]'s Corporate Practice Group. Thank you for your consideration.",
        ),
    ],
    opening_hooks=[
        "As a [X]-year [practice area] attorney with experience at [firm type]...",
        "[Partner name] suggested I contact you regarding...",
        "Having worked on [type of matters] totaling $[X] in deal value...",
        "Your firm's representation of [matter] demonstrates the practice I seek...",
    ],
    closing_statements=[
        "I would welcome the opportunity to discuss this position further.",
        "I look forward to the possibility of contributing to [Firm].",
        "Thank you for considering my application.",
    ],
    keywords_to_include=[
        "transaction", "due diligence", "negotiation", "client relationship",
        "matter management", "legal analysis", "risk assessment",
    ],
    phrases_to_avoid=[
        "I am passionate about the law",
        "I want to help people",
        "I love arguing",
        "I watch a lot of legal dramas",
    ],
    formatting_tips=[
        "Traditional business letter format",
        "Conservative, professional appearance",
        "One page only",
        "Standard fonts (Times New Roman, Garamond)",
    ],
    length_guidance="300-400 words, one page",
    personalization_tips=[
        "Research recent matters and deals",
        "Know the partners in the practice group",
        "Reference specific practice group strengths",
        "Understand their client base and industries",
    ],
)

CREATIVE_DESIGNER_COVER_LETTER = CoverLetterTemplate(
    id="creative_designer",
    name="UX/Product Designer Cover Letter",
    industry="creative",
    role_type="designer",
    tone=CoverLetterTone.CREATIVE,
    format=CoverLetterFormat.STORYTELLING,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information with portfolio link",
            word_count_range=(0, 0),
            tips=[
                "Include portfolio URL prominently",
                "Add Dribbble/Behance if relevant",
                "Match style with your portfolio branding",
            ],
            example="Alex Rivera | alex@design.co | portfolio.design/alex | dribbble.com/alexrivera",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Hook",
            description="Engaging introduction that shows personality",
            word_count_range=(40, 80),
            tips=[
                "Start with a story or observation",
                "Show your design thinking from the start",
                "Reference something specific about the company's product",
            ],
            example="The first time I used [Company]'s app, I spent 10 minutes just exploring the micro-interactions in the onboarding flow. That attention to detail—the kind that delights users without them knowing why—is exactly the craft I bring to my work as a product designer with 4 years of experience in consumer apps.",
        ),
        CoverLetterSection(
            name="design_philosophy",
            display_name="Design Process & Philosophy",
            description="Showcase your approach to design",
            word_count_range=(80, 150),
            tips=[
                "Describe your design process",
                "Show user-centered thinking",
                "Include a specific project example",
                "Mention research methods you use",
            ],
            example="I believe great design emerges from deep user empathy. At [Current Company], I redesigned the checkout experience after conducting 40 user interviews that revealed unexpected friction points. By simplifying the flow from 7 steps to 3 and adding progress indicators, we increased conversion by 34%. This project reinforced my conviction that the best solutions come from questioning assumptions and letting user behavior guide decisions.",
        ),
        CoverLetterSection(
            name="skills_and_impact",
            display_name="Skills & Impact",
            description="Highlight technical skills and measurable outcomes",
            word_count_range=(50, 100),
            tips=[
                "Mention specific tools (Figma, Principle, etc.)",
                "Include collaboration with engineers/PMs",
                "Quantify impact where possible",
            ],
            example="I'm fluent in Figma, Principle, and have enough front-end knowledge to prototype in code when needed. I've built and maintained design systems used by 3 product teams, and I love the collaborative handoff process—some of my best work has come from pairing sessions with engineers.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Enthusiastic but professional close",
            word_count_range=(30, 60),
            tips=[
                "Express genuine enthusiasm",
                "Reference your portfolio",
                "Make it easy for them to take action",
            ],
            example="I'd love to bring this approach to [Company] and help craft experiences that make users smile. My portfolio at [URL] has more examples of my work. Looking forward to the conversation!",
        ),
    ],
    opening_hooks=[
        "The moment I [used/saw/experienced] [Company's product], I noticed...",
        "Great design is invisible—until you experience bad design. At [Company]...",
        "I've spent [X] years obsessing over the details that make products feel magical...",
        "Your recent redesign of [feature] solved a problem I've been thinking about...",
    ],
    closing_statements=[
        "I'd love to bring this design passion to [Company].",
        "Let's chat about how I can help [Company] delight more users.",
        "I'm excited about the possibility of crafting experiences with your team.",
    ],
    keywords_to_include=[
        "user-centered", "iteration", "empathy", "research",
        "prototyping", "collaboration", "accessibility", "design systems",
    ],
    phrases_to_avoid=[
        "I make things pretty",
        "I've always been creative",
        "I have an eye for design",
        "I'm a perfectionist",
    ],
    formatting_tips=[
        "Design your cover letter like a mini-portfolio piece",
        "Show personality through formatting choices",
        "Make portfolio link impossible to miss",
        "Consider visual hierarchy",
    ],
    length_guidance="250-350 words, focus on quality over length",
    personalization_tips=[
        "Use their product and reference specific experiences",
        "Research the design team and their work",
        "Understand their design principles and values",
        "Reference their design blog or case studies if available",
    ],
)

MARKETING_MANAGER_COVER_LETTER = CoverLetterTemplate(
    id="marketing_manager",
    name="Marketing Manager Cover Letter",
    industry="marketing",
    role_type="marketing_manager",
    tone=CoverLetterTone.ENTHUSIASTIC,
    format=CoverLetterFormat.ACHIEVEMENT_FOCUSED,
    sections=[
        CoverLetterSection(
            name="header",
            display_name="Header",
            description="Contact information",
            word_count_range=(0, 0),
            tips=[
                "Include LinkedIn profile",
                "Add portfolio or blog if relevant",
            ],
            example="Chris Martinez | chris@email.com | (555) 123-4567 | linkedin.com/in/chrismartinez",
        ),
        CoverLetterSection(
            name="opening",
            display_name="Opening Paragraph",
            description="Hook with relevant achievement or insight",
            word_count_range=(40, 80),
            tips=[
                "Lead with a compelling metric or achievement",
                "Show you understand their market or audience",
                "Reference something specific about their marketing",
            ],
            example="When I helped grow [Previous Company]'s customer base from 10K to 150K users in 18 months, I learned that the best marketing doesn't feel like marketing—it feels like value. I'm excited to apply for the Marketing Manager role at [Company] because your customer-first approach to content resonates with how I build campaigns.",
        ),
        CoverLetterSection(
            name="marketing_achievements",
            display_name="Marketing Achievements",
            description="Quantified marketing results",
            word_count_range=(80, 150),
            tips=[
                "Lead with numbers: CAC, conversion rates, growth",
                "Show full-funnel understanding",
                "Mention specific channels and strategies",
                "Include both B2B and B2C experience if relevant",
            ],
            example="At [Current Company], I own a $500K annual marketing budget across paid, organic, and email channels. Key wins include: reducing CAC by 35% through attribution optimization, growing organic traffic 180% YoY through SEO and content strategy, and launching a referral program that now drives 25% of new signups. I've managed teams of 4 and regularly partner with Sales, Product, and Creative to align on messaging.",
        ),
        CoverLetterSection(
            name="strategic_thinking",
            display_name="Strategic Thinking",
            description="Show marketing strategy and business acumen",
            word_count_range=(50, 100),
            tips=[
                "Demonstrate understanding of business goals",
                "Show data-driven decision making",
                "Mention tools and platforms you use",
            ],
            example="I'm deeply analytical—I live in HubSpot, GA4, and Mixpanel—but I never lose sight of the brand story. I believe the best marketing strategies connect quantitative insights with qualitative customer understanding. Your recent campaign around [specific campaign] struck that balance beautifully.",
        ),
        CoverLetterSection(
            name="closing",
            display_name="Closing",
            description="Enthusiastic close with clear next step",
            word_count_range=(30, 60),
            tips=[
                "Show enthusiasm for their specific brand/mission",
                "Offer a clear next step",
                "Keep it professional but warm",
            ],
            example="I'd love to bring this growth mindset to [Company] and help scale your marketing impact. I have some ideas about [specific opportunity] that I'd be excited to discuss. Looking forward to connecting!",
        ),
    ],
    opening_hooks=[
        "Growing [metric] by [X]% taught me that...",
        "Your recent campaign for [product/initiative] caught my attention because...",
        "I've spent [X] years turning marketing budgets into growth engines...",
        "The best marketers are part analyst, part storyteller. Here's my story...",
    ],
    closing_statements=[
        "I'm excited about the opportunity to drive growth at [Company].",
        "Let's discuss how I can help [Company] reach its next milestone.",
        "I'd love to share more ideas about [specific opportunity].",
    ],
    keywords_to_include=[
        "growth", "conversion", "attribution", "brand", "strategy",
        "data-driven", "customer acquisition", "retention", "full-funnel",
    ],
    phrases_to_avoid=[
        "I'm a creative thinker",
        "I think outside the box",
        "I'm results-oriented",
        "I have a passion for marketing",
    ],
    formatting_tips=[
        "Clean, modern formatting",
        "Make metrics easy to scan",
        "One page maximum",
        "Consider a brief 'highlights' callout box",
    ],
    length_guidance="300-400 words, one page",
    personalization_tips=[
        "Reference specific campaigns or content they've created",
        "Understand their target audience",
        "Research their marketing team structure",
        "Know their competitors and market position",
    ],
)

# Registry of all cover letter templates
COVER_LETTER_TEMPLATES: Dict[str, CoverLetterTemplate] = {
    "tech_software_engineer": TECH_SOFTWARE_ENGINEER_COVER_LETTER,
    "healthcare_nurse": HEALTHCARE_NURSE_COVER_LETTER,
    "finance_analyst": FINANCE_ANALYST_COVER_LETTER,
    "legal_attorney": LEGAL_ATTORNEY_COVER_LETTER,
    "creative_designer": CREATIVE_DESIGNER_COVER_LETTER,
    "marketing_manager": MARKETING_MANAGER_COVER_LETTER,
}

# Mapping from industry to template IDs
INDUSTRY_TEMPLATES: Dict[str, List[str]] = {
    "technology": ["tech_software_engineer"],
    "healthcare": ["healthcare_nurse"],
    "finance": ["finance_analyst"],
    "legal": ["legal_attorney"],
    "creative": ["creative_designer"],
    "marketing": ["marketing_manager"],
}


def get_cover_letter_template(template_id: str) -> Optional[CoverLetterTemplate]:
    """Get a specific cover letter template by ID.

    Args:
        template_id: The unique identifier of the template.

    Returns:
        The CoverLetterTemplate if found, None otherwise.
    """
    return COVER_LETTER_TEMPLATES.get(template_id)


def get_cover_letter_templates_for_industry(industry: str) -> List[CoverLetterTemplate]:
    """Get all cover letter templates for a specific industry.

    Args:
        industry: The industry name (e.g., 'technology', 'healthcare').

    Returns:
        List of CoverLetterTemplate objects for the industry.
    """
    template_ids = INDUSTRY_TEMPLATES.get(industry.lower(), [])
    templates = []

    for template_id in template_ids:
        template = COVER_LETTER_TEMPLATES.get(template_id)
        if template:
            templates.append(template)

    # If no specific templates found, return a default template
    if not templates:
        # Return the marketing template as a reasonable default
        default = COVER_LETTER_TEMPLATES.get("marketing_manager")
        if default:
            templates.append(default)

    return templates


def get_all_cover_letter_templates() -> List[CoverLetterTemplate]:
    """Get all available cover letter templates.

    Returns:
        List of all CoverLetterTemplate objects.
    """
    return list(COVER_LETTER_TEMPLATES.values())
