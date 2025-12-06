"""Base class for job board searchers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Search query parameters."""
    keywords: List[str] = None  # Skills/keywords to search for
    location: Optional[str] = None  # Location preference
    remote_only: bool = True  # Remote jobs only
    min_rate: Optional[float] = None  # Minimum hourly/annual rate
    max_rate: Optional[float] = None  # Maximum rate
    job_type: Optional[str] = None  # full-time, part-time, contract, etc.
    experience_level: Optional[str] = None  # junior, mid, senior, etc.
    limit: int = 50  # Max results to return


@dataclass
class SearchResult:
    """Job search result."""
    source: str
    source_id: Optional[str]
    title: str
    company: Optional[str]
    description: str
    url: str
    location: Optional[str] = None
    remote: bool = False
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_type: Optional[str] = None  # hourly, annual, etc.
    skills: List[str] = None
    posted_date: Optional[datetime] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    raw_data: Dict[str, Any] = None


class BaseJobSearcher(ABC):
    """Base class for job board searchers."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = None
    
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search for jobs based on query parameters.
        
        Args:
            query: Search parameters
            
        Returns:
            List of job search results
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Initialize connection/session if needed."""
        pass
    
    async def disconnect(self):
        """Close connection/session if needed."""
        if self.session:
            await self.session.close()
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract skills from job description.
        
        Args:
            text: Job description text
            
        Returns:
            List of identified skills
        """
        # Common tech skills to look for
        skills_keywords = [
            # Languages
            'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'rust',
            'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'julia',
            
            # Web
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
            'fastapi', 'rails', 'spring', 'asp.net', 'laravel', 'nextjs', 'nuxt',
            
            # Databases
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
            'dynamodb', 'firestore', 'sqlite', 'oracle', 'sql server',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
            'jenkins', 'gitlab', 'github actions', 'circleci', 'linux', 'nginx',
            
            # AI/ML
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'nlp', 'computer vision', 'pandas', 'numpy', 'jupyter', 'transformers',
            
            # Mobile
            'ios', 'android', 'react native', 'flutter', 'xamarin', 'swiftui',
            
            # Other
            'git', 'agile', 'scrum', 'rest api', 'graphql', 'microservices',
            'blockchain', 'solidity', 'web3', 'devops', 'ci/cd', 'testing'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skills_keywords:
            if skill in text_lower:
                # Normalize skill name
                skill_normalized = skill.replace('.js', 'js').replace('.net', 'net')
                skill_normalized = skill_normalized.title().replace('Sql', 'SQL').replace('Api', 'API')
                skill_normalized = skill_normalized.replace('Nlp', 'NLP').replace('Aws', 'AWS')
                skill_normalized = skill_normalized.replace('Gcp', 'GCP').replace('Ci/Cd', 'CI/CD')
                
                if skill_normalized not in found_skills:
                    found_skills.append(skill_normalized)
        
        return found_skills[:20]  # Limit to 20 skills
    
    def parse_salary(self, salary_text: str) -> tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Parse salary information from text.
        
        Args:
            salary_text: Salary text to parse
            
        Returns:
            Tuple of (min_salary, max_salary, salary_type)
        """
        import re
        
        if not salary_text:
            return None, None, None
        
        salary_text = salary_text.lower()
        
        # Check for hourly rate
        hourly_pattern = r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:-|to)\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:per\s*)?(?:hour|hr|hourly)'
        hourly_match = re.search(hourly_pattern, salary_text)
        if hourly_match:
            min_rate = float(hourly_match.group(1).replace(',', ''))
            max_rate = float(hourly_match.group(2).replace(',', ''))
            return min_rate, max_rate, 'hourly'
        
        # Check for annual salary
        annual_pattern = r'\$?(\d+(?:,\d{3})*)[kK]?\s*(?:-|to)\s*\$?(\d+(?:,\d{3})*)[kK]?'
        annual_match = re.search(annual_pattern, salary_text)
        if annual_match:
            min_sal = annual_match.group(1).replace(',', '')
            max_sal = annual_match.group(2).replace(',', '')
            
            # Handle 'k' notation (e.g., 120k)
            if 'k' in salary_text.lower():
                min_sal = float(min_sal) * 1000 if float(min_sal) < 1000 else float(min_sal)
                max_sal = float(max_sal) * 1000 if float(max_sal) < 1000 else float(max_sal)
            else:
                min_sal = float(min_sal)
                max_sal = float(max_sal)
            
            return min_sal, max_sal, 'annual'
        
        return None, None, None