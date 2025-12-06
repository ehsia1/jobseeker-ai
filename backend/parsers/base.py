"""Base job parser interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedJob:
    """Standardized job data structure."""
    
    # Required fields
    source: str
    title: str
    
    # Optional basic info
    source_id: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    
    # Requirements and skills
    requirements: List[str] = None
    skills: List[str] = None
    
    # Compensation
    rate_min: Optional[Decimal] = None
    rate_max: Optional[Decimal] = None
    rate_type: Optional[str] = None  # "hourly", "fixed", "annual"
    
    # Work details
    hours_per_week: Optional[int] = None
    duration: Optional[str] = None
    
    # Timing
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.skills is None:
            self.skills = []
        if self.raw_data is None:
            self.raw_data = {}


class BaseJobParser(ABC):
    """Abstract base class for job parsers."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def parse(self, content: str, metadata: Dict[str, Any] = None) -> List[ParsedJob]:
        """
        Parse content and extract job listings.
        
        Args:
            content: Raw content (email HTML, RSS XML, JSON, etc.)
            metadata: Additional context (email headers, URLs, etc.)
            
        Returns:
            List of parsed jobs
        """
        pass
    
    @abstractmethod
    def can_parse(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Check if this parser can handle the given content.
        
        Args:
            content: Raw content to check
            metadata: Additional context
            
        Returns:
            True if parser can handle this content
        """
        pass
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract common tech skills from text."""
        
        # Common skills to look for (case insensitive)
        skill_keywords = {
            # Programming languages
            'python', 'javascript', 'java', 'c#', 'c++', 'go', 'rust', 'ruby', 'php',
            'typescript', 'kotlin', 'swift', 'scala', 'r', 'matlab',
            
            # Web technologies
            'react', 'vue', 'angular', 'html', 'css', 'node.js', 'nodejs', 'express',
            'django', 'flask', 'fastapi', 'spring', 'laravel', 'rails',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
            'jenkins', 'gitlab', 'github actions', 'circleci',
            
            # Databases
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb',
            'cassandra', 'oracle', 'sql server',
            
            # AI/ML
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'pandas', 'numpy', 'jupyter', 'llm', 'langchain',
            
            # Other
            'git', 'linux', 'agile', 'scrum', 'api', 'rest', 'graphql', 'microservices',
            'serverless', 'lambda', 'blockchain', 'web3'
        }
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in text_lower:
                # Handle variations
                if skill == 'node.js' and 'node.js' in text_lower:
                    found_skills.append('node.js')
                elif skill == 'nodejs' and 'nodejs' in text_lower and 'node.js' not in found_skills:
                    found_skills.append('node.js')
                elif skill not in ['node.js', 'nodejs']:
                    found_skills.append(skill)
        
        return list(set(found_skills))  # Remove duplicates
    
    def extract_rate(self, text: str) -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
        """
        Extract hourly/fixed rate from text.
        
        Returns:
            (min_rate, max_rate, rate_type)
        """
        import re
        
        text_lower = text.lower()
        
        # Hourly rates
        hourly_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*-?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)?/hr',
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*-?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)?/?hour',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*-?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)?\s*per hour',
        ]
        
        for pattern in hourly_patterns:
            match = re.search(pattern, text_lower)
            if match:
                min_rate = Decimal(match.group(1).replace(',', ''))
                max_rate = Decimal(match.group(2).replace(',', '')) if match.group(2) else None
                return min_rate, max_rate, "hourly"
        
        # Fixed price
        fixed_patterns = [
            r'fixed price:?\s*\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'budget:?\s*\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*fixed',
        ]
        
        for pattern in fixed_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = Decimal(match.group(1).replace(',', ''))
                return amount, amount, "fixed"
        
        # Annual salary
        annual_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*-?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)?/year',
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*-?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)?/?annually',
            r'salary:?\s*\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in annual_patterns:
            match = re.search(pattern, text_lower)
            if match:
                min_rate = Decimal(match.group(1).replace(',', ''))
                max_rate = Decimal(match.group(2).replace(',', '')) if match.group(2) else None
                return min_rate, max_rate, "annual"
        
        return None, None, None
    
    def is_remote(self, text: str) -> bool:
        """Check if job is remote based on text content."""
        
        remote_keywords = [
            'remote', 'work from home', 'wfh', 'distributed', 'anywhere',
            'home office', 'remote work', 'remote position', 'remote job',
            'work remotely', 'fully remote', '100% remote'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in remote_keywords)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra punctuation
        text = re.sub(r'[^\w\s\-.,!?$@()]', ' ', text)
        
        return text.strip()