"""AngelList/Wellfound searcher - startup jobs for various roles."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime
import json

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class AngelListSearcher(BaseJobSearcher):
    """Searcher for AngelList/Wellfound startup jobs."""
    
    def __init__(self):
        super().__init__()
        self.source_name = "AngelList"
        # Wellfound (formerly AngelList Talent) API
        self.base_url = "https://wellfound.com/api/v1"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search AngelList/Wellfound for startup jobs."""
        try:
            # Public API endpoint for job search
            # Note: May require API key for production use
            search_url = f"{self.base_url}/jobs"
            
            params = {
                "page": 1,
                "per_page": query.limit or 20,
            }
            
            # Add role filters based on keywords
            if query.keywords:
                roles = self._map_keywords_to_roles(query.keywords)
                if roles:
                    params["roles"] = ",".join(roles)
            
            # Add location filter
            if query.location:
                params["location"] = query.location
            elif query.remote_only:
                params["remote"] = "true"
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_angellist_jobs(data, query)
                else:
                    logger.warning(f"AngelList API returned {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching AngelList: {e}")
            return []
    
    def _map_keywords_to_roles(self, keywords: List[str]) -> List[str]:
        """Map keywords to AngelList role categories."""
        role_mapping = {
            "engineering": ["engineering", "developer", "software", "backend", "frontend", "fullstack"],
            "design": ["design", "ux", "ui", "product design", "graphic"],
            "sales": ["sales", "business development", "bd", "account executive"],
            "marketing": ["marketing", "growth", "content", "seo", "sem"],
            "product": ["product manager", "pm", "product"],
            "operations": ["operations", "ops", "coo"],
            "finance": ["finance", "cfo", "accounting", "controller"],
            "hr": ["hr", "human resources", "recruiting", "people ops"],
            "data": ["data", "analytics", "data science", "ml", "ai"],
        }
        
        roles = set()
        keywords_lower = [k.lower() for k in keywords]
        
        for role, role_keywords in role_mapping.items():
            if any(rk in " ".join(keywords_lower) for rk in role_keywords):
                roles.add(role)
        
        return list(roles)
    
    def _parse_angellist_jobs(self, data: dict, query: SearchQuery) -> List[SearchResult]:
        """Parse AngelList job response."""
        results = []
        
        jobs = data.get("jobs", [])
        for job in jobs[:query.limit]:
            try:
                # Extract skills from requirements
                skills = self._extract_skills(job.get("description", ""))
                
                # Parse salary if available
                salary_min, salary_max = None, None
                if job.get("salary_min"):
                    salary_min = float(job["salary_min"])
                if job.get("salary_max"):
                    salary_max = float(job["salary_max"])
                
                result = SearchResult(
                    source=self.source_name,
                    external_id=str(job.get("id", "")),
                    title=job.get("title", ""),
                    company=job.get("company", {}).get("name", ""),
                    description=job.get("description", ""),
                    url=job.get("url", ""),
                    location=job.get("location", ""),
                    remote=job.get("remote", False),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_type="annual",
                    skills=skills,
                    posted_at=datetime.fromisoformat(job["created_at"]) if job.get("created_at") else None,
                    application_url=job.get("apply_url", ""),
                    company_url=job.get("company", {}).get("url", ""),
                    experience_level=job.get("experience_level", ""),
                    job_type=job.get("job_type", "full-time"),
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error parsing AngelList job: {e}")
                continue
        
        logger.info(f"Found {len(results)} jobs on AngelList")
        return results