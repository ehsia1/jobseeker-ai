"""eFinancialCareers job board searcher for finance professionals."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class EFinancialCareersSearcher(BaseJobSearcher):
    """Searcher for eFinancialCareers - finance/banking jobs."""

    BASE_URL = "https://www.efinancialcareers.com/api/jobs"

    FINANCE_SKILLS = [
        "financial modeling", "excel", "vba", "python", "sql", "bloomberg",
        "financial analysis", "valuation", "dcf", "lbo", "m&a", "ipo",
        "equity research", "fixed income", "derivatives", "options",
        "risk management", "var", "credit risk", "market risk",
        "portfolio management", "asset allocation", "quantitative analysis",
        "algorithmic trading", "high frequency trading", "fintech",
        "regulatory compliance", "aml", "kyc", "basel", "dodd-frank",
        "accounting", "gaap", "ifrs", "audit", "tax", "cpa", "cfa",
        "investment banking", "private equity", "venture capital",
        "hedge fund", "wealth management", "financial planning",
        "budgeting", "forecasting", "fp&a", "treasury", "capital markets",
        "structured products", "securitization", "credit analysis",
        "underwriting", "due diligence", "pitch books", "deal execution"
    ]

    def __init__(self):
        super().__init__("efinancialcareers")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for finance jobs."""
        results = []

        try:
            keywords = query.keywords or ["finance", "analyst"]

            params = {
                "q": " ".join(keywords),
                "page": "1",
                "limit": str(min(query.limit, 50)),
            }

            if query.location:
                params["location"] = query.location

            if query.remote_only:
                params["remote"] = "true"

            headers = {
                "User-Agent": "JobSeeker-AI/1.0",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL, params=params, headers=headers
                ) as response:
                    if response.status != 200:
                        logger.warning(f"eFinancialCareers API returned {response.status}")
                        return self._get_mock_results(query)

                    data = await response.json()
                    jobs = data.get("jobs", data.get("results", []))

                    for job in jobs:
                        try:
                            result = self._parse_job(job)
                            if result:
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"Error parsing finance job: {e}")

        except Exception as e:
            logger.error(f"eFinancialCareers search error: {e}")
            return self._get_mock_results(query)

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a finance job listing."""
        title = job.get("title", "")
        if not title:
            return None

        company = job.get("company", job.get("employer", ""))
        if isinstance(company, dict):
            company = company.get("name", "")

        location = job.get("location", "")
        if isinstance(location, dict):
            city = location.get("city", "")
            state = location.get("state", "")
            country = location.get("country", "")
            location = ", ".join(filter(None, [city, state, country]))

        description = job.get("description", job.get("summary", ""))

        salary_min, salary_max, salary_type = None, None, None
        salary = job.get("salary", job.get("compensation", ""))
        if salary:
            salary_min, salary_max, salary_type = self.parse_salary(str(salary))

        return SearchResult(
            source="efinancialcareers",
            source_id=job.get("id"),
            title=title,
            company=company,
            description=description,
            url=job.get("url", ""),
            location=location,
            remote=job.get("remote", False),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_type=salary_type,
            skills=self._extract_finance_skills(description),
            posted_date=self._parse_date(job.get("postedDate")),
            job_type=job.get("employmentType"),
            experience_level=job.get("experienceLevel"),
            raw_data=job,
        )

    def _extract_finance_skills(self, text: str) -> List[str]:
        """Extract finance-specific skills."""
        text_lower = text.lower()
        found = []

        for skill in self.FINANCE_SKILLS:
            if skill in text_lower:
                # Normalize skill names
                skill_name = skill.upper() if len(skill) <= 4 else skill.title()
                skill_name = skill_name.replace("&", "&").replace("Fp&A", "FP&A")
                found.append(skill_name)

        return list(set(found))[:15]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def _get_mock_results(self, query: SearchQuery) -> List[SearchResult]:
        """Return mock results for demo purposes."""
        return [
            SearchResult(
                source="efinancialcareers",
                source_id="mock-fin-1",
                title="Investment Banking Analyst",
                company="Morgan Stanley",
                description="Analyst position in Technology M&A group. Strong financial modeling and valuation skills required.",
                url="https://efinancialcareers.com/jobs/mock-fin-1",
                location="New York, NY",
                remote=False,
                salary_min=100000,
                salary_max=150000,
                salary_type="annual",
                skills=["Financial Modeling", "M&A", "Valuation", "DCF", "Excel", "Pitch Books"],
                job_type="full-time",
                experience_level="entry",
            ),
            SearchResult(
                source="efinancialcareers",
                source_id="mock-fin-2",
                title="Quantitative Analyst - Risk",
                company="Goldman Sachs",
                description="Quantitative analyst for market risk team. Python, VaR modeling, derivatives pricing experience required.",
                url="https://efinancialcareers.com/jobs/mock-fin-2",
                location="New York, NY",
                remote=False,
                salary_min=150000,
                salary_max=250000,
                salary_type="annual",
                skills=["Python", "Quantitative Analysis", "VAR", "Risk Management", "Derivatives"],
                job_type="full-time",
                experience_level="mid",
            ),
            SearchResult(
                source="efinancialcareers",
                source_id="mock-fin-3",
                title="Remote FP&A Manager",
                company="Tech Startup (Series C)",
                description="Lead FP&A function for fast-growing fintech. Build financial models, budgets, and investor reporting.",
                url="https://efinancialcareers.com/jobs/mock-fin-3",
                location="Remote",
                remote=True,
                salary_min=130000,
                salary_max=170000,
                salary_type="annual",
                skills=["FP&A", "Financial Modeling", "Budgeting", "Forecasting", "Excel"],
                job_type="full-time",
                experience_level="senior",
            ),
        ]
