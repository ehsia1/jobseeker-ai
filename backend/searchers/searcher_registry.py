"""Registry for selecting appropriate job searchers based on profession and industry."""

from typing import List, Dict, Type
import logging

from backend.searchers.base import BaseJobSearcher
from backend.searchers.remoteok_searcher import RemoteOKSearcher
from backend.searchers.hackernews_searcher import HackerNewsSearcher
from backend.searchers.github_jobs_searcher import GitHubJobsSearcher
from backend.searchers.indeed_searcher import IndeedSearcher
from backend.searchers.linkedin_searcher import LinkedInSearcher
from backend.searchers.angellist_searcher import AngelListSearcher
from backend.searchers.flexjobs_searcher import FlexJobsSearcher
from backend.searchers.upwork_searcher import UpworkSearcher

# Industry-specific searchers
from backend.searchers.dice_searcher import DiceSearcher
from backend.searchers.dribbble_searcher import DribbbleSearcher
from backend.searchers.healthcareers_searcher import HealthCareersSearcher
from backend.searchers.lawjobs_searcher import LawJobsSearcher
from backend.searchers.efinancialcareers_searcher import EFinancialCareersSearcher

logger = logging.getLogger(__name__)


class SearcherRegistry:
    """Registry for profession-specific job searchers."""
    
    # Map professions to relevant job boards
    PROFESSION_SEARCHERS: Dict[str, List[Type[BaseJobSearcher]]] = {
        # Technology roles
        "software_engineer": [
            DiceSearcher,  # Tech-focused job board
            RemoteOKSearcher,
            HackerNewsSearcher,
            GitHubJobsSearcher,
            AngelListSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "data_scientist": [
            DiceSearcher,
            RemoteOKSearcher,
            HackerNewsSearcher,
            AngelListSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "devops": [
            DiceSearcher,
            RemoteOKSearcher,
            HackerNewsSearcher,
            GitHubJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "product_manager": [
            AngelListSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        
        # Creative roles
        "designer": [
            DribbbleSearcher,  # Design-focused job board
            AngelListSearcher,
            RemoteOKSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "writer": [
            FlexJobsSearcher,
            UpworkSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "content_creator": [
            FlexJobsSearcher,
            UpworkSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
        ],
        
        # Business roles
        "sales": [
            AngelListSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "marketing": [
            AngelListSearcher,
            RemoteOKSearcher,
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "business_analyst": [
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
            FlexJobsSearcher,
        ],
        
        # Operations & Admin
        "operations": [
            AngelListSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "admin": [
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            UpworkSearcher,
        ],
        "project_manager": [
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
        ],
        
        # Finance & Accounting
        "accountant": [
            EFinancialCareersSearcher,  # Finance-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
        ],
        "finance": [
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
        ],
        "investment_banking": [
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "quantitative_analyst": [
            EFinancialCareersSearcher,
            DiceSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        
        # Healthcare
        "healthcare": [
            HealthCareersSearcher,  # Healthcare-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "nurse": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "physician": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "medical_technician": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        
        # Education
        "teacher": [
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "trainer": [
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            UpworkSearcher,
        ],
        
        # Customer Service
        "customer_service": [
            FlexJobsSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "support": [
            RemoteOKSearcher,
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        
        # Legal
        "legal": [
            LawJobsSearcher,  # Legal-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
        ],
        "attorney": [
            LawJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "paralegal": [
            LawJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "compliance": [
            LawJobsSearcher,
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        
        # Freelance/Consultant (any field)
        "freelancer": [
            UpworkSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
        ],
        "consultant": [
            UpworkSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        
        # Default/General
        "general": [
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
        ],
    }
    
    @classmethod
    def get_searchers_for_profession(cls, profession: str) -> List[BaseJobSearcher]:
        """Get appropriate searchers for a given profession."""
        profession_lower = profession.lower().replace(" ", "_")
        
        # Try exact match first
        if profession_lower in cls.PROFESSION_SEARCHERS:
            searcher_classes = cls.PROFESSION_SEARCHERS[profession_lower]
        else:
            # Try to find partial matches
            matched_classes = set()
            for key, searchers in cls.PROFESSION_SEARCHERS.items():
                if key in profession_lower or profession_lower in key:
                    matched_classes.update(searchers)
            
            if matched_classes:
                searcher_classes = list(matched_classes)
            else:
                # Default to general searchers
                logger.info(f"No specific searchers for '{profession}', using general searchers")
                searcher_classes = cls.PROFESSION_SEARCHERS["general"]
        
        # Instantiate searchers
        searchers = []
        for searcher_class in searcher_classes:
            try:
                searchers.append(searcher_class())
            except Exception as e:
                logger.error(f"Error instantiating {searcher_class.__name__}: {e}")
        
        logger.info(f"Selected {len(searchers)} searchers for profession '{profession}'")
        return searchers
    
    @classmethod
    def get_all_professions(cls) -> List[str]:
        """Get list of all supported professions."""
        return list(cls.PROFESSION_SEARCHERS.keys())
    
    @classmethod
    def suggest_profession(cls, keywords: List[str]) -> str:
        """Suggest a profession based on keywords."""
        keyword_text = " ".join(k.lower() for k in keywords)
        
        # Profession keyword mapping
        profession_keywords = {
            "software_engineer": ["software", "developer", "programmer", "coding", "backend", "frontend", "fullstack"],
            "data_scientist": ["data", "machine learning", "ml", "ai", "analytics", "data science"],
            "designer": ["design", "ux", "ui", "graphic", "visual", "creative"],
            "sales": ["sales", "business development", "account executive", "revenue"],
            "marketing": ["marketing", "growth", "seo", "content", "brand", "digital marketing"],
            "product_manager": ["product manager", "pm", "product owner", "product"],
            "writer": ["writer", "writing", "content", "copywriter", "author", "journalist"],
            "teacher": ["teacher", "teaching", "education", "instructor", "professor"],
            "nurse": ["nurse", "nursing", "rn", "healthcare", "medical"],
            "accountant": ["accountant", "accounting", "bookkeeper", "cpa", "finance"],
            "customer_service": ["customer service", "support", "help desk", "customer success"],
        }
        
        best_match = "general"
        best_score = 0
        
        for profession, prof_keywords in profession_keywords.items():
            score = sum(1 for kw in prof_keywords if kw in keyword_text)
            if score > best_score:
                best_score = score
                best_match = profession
        
        return best_match