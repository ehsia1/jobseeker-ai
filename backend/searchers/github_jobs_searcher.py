"""GitHub Jobs searcher (searches GitHub Issues for job postings)."""

import aiohttp
from typing import List, Optional
from datetime import datetime
import logging

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class GitHubJobsSearcher(BaseJobSearcher):
    """
    Searcher for GitHub job postings.
    
    Since GitHub Jobs API is discontinued, this searches for job postings
    in GitHub Issues in repositories like:
    - remote-jobs/remote-jobs
    - remoteintech/remote-jobs
    """
    
    def __init__(self):
        super().__init__("GitHub")
        self.base_url = "https://api.github.com"
        # Repositories known to have job postings
        self.job_repos = [
            "remote-jobs/remote-jobs",
            "remoteintech/remote-jobs",  
        ]
    
    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "JobSeeker AI Bot"
            }
        )
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search GitHub for job postings."""
        results = []
        
        try:
            # Build search query for GitHub
            search_terms = []
            
            if query.keywords:
                search_terms.extend(query.keywords)
            
            if query.remote_only:
                search_terms.append("remote")
            
            search_query = " ".join(search_terms) if search_terms else "hiring"
            
            # Search in issues
            params = {
                "q": f"{search_query} is:issue is:open label:hiring,job,jobs,career in:title,body",
                "sort": "created",
                "order": "desc",
                "per_page": min(query.limit, 100)
            }
            
            async with self.session.get(f"{self.base_url}/search/issues", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    
                    for item in items:
                        result = self._parse_issue(item, query)
                        if result:
                            results.append(result)
                elif response.status == 403:
                    logger.warning("GitHub API rate limit reached")
                else:
                    logger.error(f"GitHub API returned status {response.status}")
            
            logger.info(f"Found {len(results)} jobs on GitHub")
            
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
        
        return results
    
    def _parse_issue(self, issue: dict, query: SearchQuery) -> Optional[SearchResult]:
        """Parse GitHub issue into SearchResult."""
        try:
            # Extract company from repository or title
            repo_parts = issue.get('repository_url', '').split('/')
            company = repo_parts[-1] if repo_parts else None
            
            # Parse title
            title = issue.get('title', 'Unknown Position')
            
            # Clean up common prefixes
            for prefix in ['[HIRING]', '[JOB]', '[REMOTE]', 'HIRING:', 'JOB:']:
                title = title.replace(prefix, '').strip()
            
            # Extract skills from body
            body = issue.get('body', '')
            skills = self.extract_skills(body)
            
            # Check if remote
            remote = 'remote' in (title + body).lower()
            
            # Parse salary if mentioned
            salary_min, salary_max, salary_type = self.parse_salary(body)
            
            # Get created date
            created_at = issue.get('created_at')
            posted_date = None
            if created_at:
                try:
                    posted_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    pass
            
            return SearchResult(
                source=self.source_name,
                source_id=str(issue.get('id')),
                title=title,
                company=company,
                description=body[:2000],  # Limit description
                url=issue.get('html_url', ''),
                location="Remote" if remote else None,
                remote=remote,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills,
                posted_date=posted_date,
                job_type=None,
                experience_level=None,
                raw_data=issue
            )
            
        except Exception as e:
            logger.error(f"Error parsing GitHub issue: {e}")
            return None