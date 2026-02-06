"""HackerNews Who's Hiring thread searcher."""

import aiohttp
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class HackerNewsSearcher(BaseJobSearcher):
    """Searcher for HackerNews Who's Hiring threads."""
    
    def __init__(self):
        super().__init__("HackerNews")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.algolia_url = "https://hn.algolia.com/api/v1/search"
    
    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search HackerNews Who's Hiring threads.

        Strategy:
        1. Find the latest "Who is hiring?" thread
        2. Get all comments (job postings)
        3. Parse and filter based on query
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Find the latest Who's Hiring thread
                thread_id = await self._find_latest_hiring_thread(session)
                if not thread_id:
                    logger.warning("Could not find HackerNews hiring thread")
                    return []

                # Get all job postings from the thread
                jobs = await self._get_thread_jobs(thread_id, session)
            
            # Filter and parse jobs
            results = []
            for job_text in jobs:
                if not self._matches_query(job_text, query):
                    continue
                
                result = self._parse_job_posting(job_text)
                if result:
                    results.append(result)
                
                if len(results) >= query.limit:
                    break
            
            logger.info(f"Found {len(results)} jobs on HackerNews")
            return results
            
        except Exception as e:
            logger.error(f"Error searching HackerNews: {e}")
            return []
    
    async def _find_latest_hiring_thread(self, session: aiohttp.ClientSession) -> Optional[int]:
        """Find the most recent 'Who is hiring?' thread."""
        try:
            # Search for recent "Who is hiring?" posts by whoishiring user
            params = {
                "query": "Who is hiring?",
                "tags": "story,author_whoishiring",
                "hitsPerPage": 5
            }

            async with session.get(self.algolia_url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                hits = data.get('hits', [])
                
                # Get the most recent one
                for hit in hits:
                    if "Who is hiring?" in hit.get('title', ''):
                        return hit.get('objectID')  # This is the thread ID
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding hiring thread: {e}")
            return None
    
    async def _get_thread_jobs(self, thread_id: int, session: aiohttp.ClientSession) -> List[str]:
        """Get all job postings from a thread."""
        jobs = []

        try:
            # Get the thread item
            async with session.get(f"{self.base_url}/item/{thread_id}.json") as response:
                if response.status != 200:
                    return jobs
                
                thread_data = await response.json()
                kid_ids = thread_data.get('kids', [])

                # Fetch each comment (job posting)
                for kid_id in kid_ids[:100]:  # Limit to first 100 to avoid too many requests
                    async with session.get(f"{self.base_url}/item/{kid_id}.json") as resp:
                        if resp.status == 200:
                            comment = await resp.json()
                            if comment and not comment.get('deleted') and not comment.get('dead'):
                                text = comment.get('text', '')
                                if text:
                                    jobs.append(text)
                
                return jobs
                
        except Exception as e:
            logger.error(f"Error getting thread jobs: {e}")
            return jobs
    
    def _matches_query(self, job_text: str, query: SearchQuery) -> bool:
        """Check if job text matches search query."""
        job_text_lower = job_text.lower()
        
        # Check keywords
        if query.keywords:
            keyword_match = any(
                keyword.lower() in job_text_lower 
                for keyword in query.keywords
            )
            if not keyword_match:
                return False
        
        # Check for remote
        if query.remote_only:
            remote_keywords = ['remote', 'distributed', 'work from home', 'wfh', 'anywhere']
            if not any(kw in job_text_lower for kw in remote_keywords):
                # Check if explicitly says no remote
                if 'no remote' in job_text_lower or 'onsite only' in job_text_lower:
                    return False
        
        return True
    
    def _parse_job_posting(self, text: str) -> Optional[SearchResult]:
        """Parse a HackerNews job posting."""
        try:
            # Clean HTML entities
            import html
            text = html.unescape(text)
            text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
            
            # Extract company name (usually at the beginning)
            lines = text.split('\n')
            first_line = lines[0] if lines else ''
            
            # Common patterns: "Company | Location | ..."
            company_match = re.match(r'^([^|]+)', first_line)
            company = company_match.group(1).strip() if company_match else None
            
            # Extract location
            location = None
            location_match = re.search(r'\|\s*([^|]+)\s*\|', first_line)
            if location_match:
                location = location_match.group(1).strip()
            
            # Check if remote
            remote = any(kw in text.lower() for kw in ['remote', 'distributed', 'wfh', 'anywhere'])
            
            # Extract URL
            url_match = re.search(r'https?://[^\s<>"]+', text)
            url = url_match.group(0) if url_match else f"https://news.ycombinator.com/item?id={id(text)}"
            
            # Extract salary if mentioned
            salary_min, salary_max, salary_type = self.parse_salary(text)
            
            # Extract skills
            skills = self.extract_skills(text)
            
            # Create a title from the first line or company name
            title_parts = []
            
            # Look for role keywords
            role_keywords = ['engineer', 'developer', 'designer', 'manager', 'scientist', 
                           'analyst', 'architect', 'lead', 'senior', 'junior', 'intern']
            
            for keyword in role_keywords:
                if keyword in text.lower():
                    # Find the context around the keyword
                    pattern = rf'\b([\w\s]+{keyword}[\w\s]*)\b'
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        title_parts.append(match.group(1).strip())
                        break
            
            title = title_parts[0] if title_parts else f"Position at {company}" if company else "Software Engineer"

            # Truncate fields to fit database VARCHAR(255) limits
            title = title[:200] if title else "Software Engineer"
            company = company[:200] if company else None
            url = url[:250] if url else None
            location = location[:200] if location else None

            return SearchResult(
                source=self.source_name,
                source_id=None,
                title=title,
                company=company,
                description=text[:2000],  # Limit description
                url=url,
                location=location,
                remote=remote,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills,
                posted_date=datetime.utcnow(),  # Approximate
                job_type=None,
                experience_level=None,
                raw_data={"text": text}
            )
            
        except Exception as e:
            logger.error(f"Error parsing HackerNews job: {e}")
            return None