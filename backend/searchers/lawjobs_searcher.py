"""Legal job board searcher for law professionals."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class LawJobsSearcher(BaseJobSearcher):
    """Searcher for legal/law jobs."""

    BASE_URL = "https://www.lawjobs.com/api/jobs"

    LEGAL_SKILLS = [
        "legal research", "westlaw", "lexisnexis", "contract drafting",
        "litigation", "corporate law", "intellectual property", "patent",
        "trademark", "mergers acquisitions", "real estate law", "family law",
        "criminal law", "immigration law", "employment law", "tax law",
        "bankruptcy", "securities", "compliance", "regulatory",
        "legal writing", "discovery", "e-discovery", "deposition",
        "trial preparation", "mediation", "arbitration", "negotiation",
        "client counseling", "case management", "document review",
        "due diligence", "transactional", "estate planning", "probate",
        "environmental law", "healthcare law", "privacy law", "gdpr",
        "contract management", "billing", "timekeeping", "clio",
        "practice management", "legal technology", "jd", "bar admission"
    ]

    PRACTICE_AREAS = [
        "corporate", "litigation", "real estate", "intellectual property",
        "employment", "tax", "healthcare", "environmental", "criminal",
        "family", "immigration", "bankruptcy", "securities", "privacy"
    ]

    def __init__(self):
        super().__init__("lawjobs")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for legal jobs."""
        results = []

        try:
            keywords = query.keywords or ["attorney", "lawyer"]

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
                        logger.warning(f"LawJobs API returned {response.status}")
                        return self._get_mock_results(query)

                    data = await response.json()
                    jobs = data.get("jobs", data.get("results", []))

                    for job in jobs:
                        try:
                            result = self._parse_job(job)
                            if result:
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"Error parsing law job: {e}")

        except Exception as e:
            logger.error(f"LawJobs search error: {e}")
            return self._get_mock_results(query)

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a legal job listing."""
        title = job.get("title", "")
        if not title:
            return None

        company = job.get("company", job.get("firm", job.get("employer", "")))
        if isinstance(company, dict):
            company = company.get("name", "")

        location = job.get("location", "")
        if isinstance(location, dict):
            city = location.get("city", "")
            state = location.get("state", "")
            location = f"{city}, {state}".strip(", ")

        description = job.get("description", job.get("summary", ""))

        salary_min, salary_max, salary_type = None, None, None
        salary = job.get("salary", job.get("compensation", ""))
        if salary:
            salary_min, salary_max, salary_type = self.parse_salary(str(salary))

        practice_areas = self._extract_practice_areas(description + " " + title)

        return SearchResult(
            source="lawjobs",
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
            skills=self._extract_legal_skills(description) + practice_areas,
            posted_date=self._parse_date(job.get("postedDate")),
            job_type=job.get("employmentType"),
            experience_level=job.get("experienceLevel"),
            raw_data=job,
        )

    def _extract_legal_skills(self, text: str) -> List[str]:
        """Extract legal-specific skills."""
        text_lower = text.lower()
        found = []

        for skill in self.LEGAL_SKILLS:
            if skill in text_lower:
                found.append(skill.title())

        return list(set(found))[:12]

    def _extract_practice_areas(self, text: str) -> List[str]:
        """Extract practice areas from text."""
        text_lower = text.lower()
        found = []

        for area in self.PRACTICE_AREAS:
            if area in text_lower:
                found.append(f"{area.title()} Law")

        return found[:5]

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
                source="lawjobs",
                source_id="mock-law-1",
                title="Associate Attorney - Corporate M&A",
                company="Smith & Williams LLP",
                description="Mid-level associate for busy corporate M&A practice. 3-5 years experience required. Westlaw/LexisNexis proficiency.",
                url="https://lawjobs.com/jobs/mock-law-1",
                location="New York, NY",
                remote=False,
                salary_min=180000,
                salary_max=220000,
                salary_type="annual",
                skills=["Corporate Law", "M&A", "Due Diligence", "Westlaw", "Contract Drafting"],
                job_type="full-time",
                experience_level="mid",
            ),
            SearchResult(
                source="lawjobs",
                source_id="mock-law-2",
                title="Remote Contract Attorney - Document Review",
                company="Legal Staffing Solutions",
                description="Remote document review for large litigation matter. JD required, bar admission preferred.",
                url="https://lawjobs.com/jobs/mock-law-2",
                location="Remote",
                remote=True,
                salary_min=35,
                salary_max=50,
                salary_type="hourly",
                skills=["Document Review", "E-Discovery", "Litigation", "Legal Research"],
                job_type="contract",
            ),
            SearchResult(
                source="lawjobs",
                source_id="mock-law-3",
                title="Paralegal - Intellectual Property",
                company="Tech Law Group",
                description="IP paralegal to support patent and trademark prosecution. Experience with USPTO filings required.",
                url="https://lawjobs.com/jobs/mock-law-3",
                location="San Francisco, CA",
                remote=False,
                salary_min=70000,
                salary_max=90000,
                salary_type="annual",
                skills=["Intellectual Property", "Patent", "Trademark", "USPTO", "Legal Research"],
                job_type="full-time",
            ),
        ]
