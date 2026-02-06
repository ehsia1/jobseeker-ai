"""RemoteOK job board searcher."""

import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class RemoteOKSearcher(BaseJobSearcher):
    """Searcher for RemoteOK job board."""
    
    def __init__(self):
        super().__init__("RemoteOK")
        self.base_url = "https://remoteok.io/api"
        self.headers = {
            "User-Agent": "JobSeeker AI Bot 1.0"
        }
    
    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search RemoteOK for jobs.

        RemoteOK provides a JSON API with all their jobs.
        We'll filter based on the query parameters.
        """
        try:
            # RemoteOK doesn't have search params, returns all jobs
            # We'll filter client-side
            async with aiohttp.ClientSession(headers=self.headers) as session:
              async with session.get(self.base_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"RemoteOK API returned status {response.status}")
                    return []
                
                data = await response.json()
                
                # First item is metadata, skip it
                if data and isinstance(data[0], dict) and 'legal' in data[0]:
                    jobs = data[1:]
                else:
                    jobs = data
                
                results = []
                
                for job in jobs[:query.limit * 2]:  # Get more to filter
                    # Filter based on query
                    if not self._matches_query(job, query):
                        continue
                    
                    result = self._parse_job(job)
                    if result:
                        results.append(result)
                    
                    if len(results) >= query.limit:
                        break
                
                logger.info(f"Found {len(results)} jobs on RemoteOK")
                return results
                
        except Exception as e:
            logger.error(f"Error searching RemoteOK: {e}")
            return []
    
    def _matches_query(self, job: Dict[str, Any], query: SearchQuery) -> bool:
        """Check if job matches search query."""
        # Check keywords
        if query.keywords:
            job_text = f"{job.get('position', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}"
            job_text_lower = job_text.lower()
            
            # Check if any keyword matches
            keyword_match = any(
                keyword.lower() in job_text_lower 
                for keyword in query.keywords
            )
            
            if not keyword_match:
                return False
        
        # Check salary range
        if query.min_rate:
            salary_min = job.get('salary_min', 0)
            if salary_min and salary_min < query.min_rate:
                return False
        
        if query.max_rate:
            salary_max = job.get('salary_max', float('inf'))
            if salary_max and salary_max > query.max_rate:
                return False
        
        return True
    
    def _parse_job(self, job: Dict[str, Any]) -> Optional[SearchResult]:
        """Parse RemoteOK job into SearchResult."""
        try:
            # Extract posted date
            posted_date = None
            if job.get('date'):
                try:
                    posted_date = datetime.fromisoformat(job['date'].replace('Z', '+00:00'))
                except:
                    pass
            elif job.get('epoch'):
                posted_date = datetime.fromtimestamp(job['epoch'])
            
            # Extract skills from tags and description
            skills = job.get('tags', [])
            if job.get('description'):
                extracted_skills = self.extract_skills(job['description'])
                skills.extend(extracted_skills)
            
            # Remove duplicates
            skills = list(set(skills))
            
            # Parse salary
            salary_min = job.get('salary_min')
            salary_max = job.get('salary_max')
            salary_type = 'annual' if salary_min or salary_max else None
            
            return SearchResult(
                source=self.source_name,
                source_id=job.get('id') or job.get('slug'),
                title=job.get('position', 'Unknown Position'),
                company=job.get('company'),
                description=job.get('description', ''),
                url=job.get('url') or job.get('apply_url', ''),
                location=job.get('location', 'Remote'),
                remote=True,  # RemoteOK is all remote jobs
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills[:20],  # Limit skills
                posted_date=posted_date,
                job_type=None,  # RemoteOK doesn't specify
                experience_level=None,  # Could parse from description
                raw_data=job
            )
            
        except Exception as e:
            logger.error(f"Error parsing RemoteOK job: {e}")
            return None