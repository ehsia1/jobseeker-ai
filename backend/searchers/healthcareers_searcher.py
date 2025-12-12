"""Healthcare job board searcher for medical professionals."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class HealthCareersSearcher(BaseJobSearcher):
    """Searcher for healthcare/medical jobs from multiple sources."""

    # Health eCareers API endpoint (simplified)
    BASE_URL = "https://www.healthecareers.com/api/jobs"

    HEALTHCARE_SKILLS = [
        "nursing", "patient care", "ehr", "epic", "cerner", "meditech",
        "medical terminology", "hipaa", "clinical", "phlebotomy", "iv therapy",
        "wound care", "medication administration", "vital signs", "cpr",
        "bls", "acls", "pals", "telemetry", "icu", "er", "or", "labor delivery",
        "pediatrics", "geriatrics", "oncology", "cardiology", "orthopedics",
        "physical therapy", "occupational therapy", "speech therapy",
        "medical coding", "icd-10", "cpt", "billing", "medical records",
        "radiology", "ultrasound", "mri", "ct scan", "x-ray",
        "pharmacy", "pharmacology", "medication management",
        "mental health", "behavioral health", "psychiatry",
        "case management", "discharge planning", "care coordination"
    ]

    def __init__(self):
        super().__init__("healthcareers")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for healthcare jobs."""
        results = []

        try:
            # Map general keywords to healthcare terms
            keywords = self._map_healthcare_keywords(query.keywords or [])

            params = {
                "q": " ".join(keywords) or "nurse",
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
                        logger.warning(f"HealthCareers API returned {response.status}")
                        # Fallback to mock data for demo
                        return self._get_mock_results(query)

                    data = await response.json()
                    jobs = data.get("jobs", data.get("results", []))

                    for job in jobs:
                        try:
                            result = self._parse_job(job)
                            if result:
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"Error parsing healthcare job: {e}")

        except Exception as e:
            logger.error(f"HealthCareers search error: {e}")
            return self._get_mock_results(query)

        return results

    def _map_healthcare_keywords(self, keywords: List[str]) -> List[str]:
        """Map general keywords to healthcare-specific terms."""
        keyword_map = {
            "healthcare": ["nursing", "medical", "clinical"],
            "nurse": ["RN", "registered nurse", "nursing"],
            "doctor": ["physician", "MD", "medical doctor"],
            "therapist": ["physical therapist", "occupational therapist"],
            "medical": ["healthcare", "clinical", "hospital"],
        }

        mapped = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in keyword_map:
                mapped.extend(keyword_map[kw_lower])
            else:
                mapped.append(kw)

        return mapped or ["healthcare"]

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a healthcare job listing."""
        title = job.get("title", job.get("jobTitle", ""))
        if not title:
            return None

        company = job.get("company", job.get("employer", job.get("organization", "")))
        if isinstance(company, dict):
            company = company.get("name", "")

        location = job.get("location", job.get("city", ""))
        if isinstance(location, dict):
            city = location.get("city", "")
            state = location.get("state", "")
            location = f"{city}, {state}".strip(", ")

        description = job.get("description", job.get("summary", ""))

        salary_min, salary_max, salary_type = None, None, None
        salary = job.get("salary", job.get("compensation", ""))
        if salary:
            salary_min, salary_max, salary_type = self.parse_salary(str(salary))

        job_url = job.get("url", job.get("applyUrl", ""))

        return SearchResult(
            source="healthcareers",
            source_id=job.get("id", job.get("jobId")),
            title=title,
            company=company,
            description=description,
            url=job_url,
            location=location,
            remote=job.get("remote", False),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_type=salary_type,
            skills=self._extract_healthcare_skills(description),
            posted_date=self._parse_date(job.get("postedDate")),
            job_type=job.get("employmentType", job.get("jobType")),
            raw_data=job,
        )

    def _extract_healthcare_skills(self, text: str) -> List[str]:
        """Extract healthcare-specific skills."""
        text_lower = text.lower()
        found = []

        for skill in self.HEALTHCARE_SKILLS:
            if skill in text_lower:
                found.append(skill.upper() if len(skill) <= 4 else skill.title())

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
                source="healthcareers",
                source_id="mock-1",
                title="Registered Nurse - ICU",
                company="City General Hospital",
                description="Seeking experienced ICU RN with BLS/ACLS certification. Epic EHR experience preferred.",
                url="https://healthecareers.com/jobs/mock-1",
                location="Boston, MA",
                remote=False,
                salary_min=75000,
                salary_max=95000,
                salary_type="annual",
                skills=["ICU", "BLS", "ACLS", "Epic", "Patient Care"],
                job_type="full-time",
            ),
            SearchResult(
                source="healthcareers",
                source_id="mock-2",
                title="Telehealth Nurse Practitioner",
                company="Virtual Care Services",
                description="Remote NP position providing telehealth consultations. Must be licensed in multiple states.",
                url="https://healthecareers.com/jobs/mock-2",
                location="Remote",
                remote=True,
                salary_min=110000,
                salary_max=140000,
                salary_type="annual",
                skills=["Telehealth", "NP", "Patient Assessment", "Clinical"],
                job_type="full-time",
            ),
        ]
