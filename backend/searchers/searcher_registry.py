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

# General job boards
from backend.searchers.glassdoor_searcher import GlassdoorSearcher
from backend.searchers.ziprecruiter_searcher import ZipRecruiterSearcher
from backend.searchers.monster_searcher import MonsterSearcher
from backend.searchers.simplyhired_searcher import SimplyHiredSearcher

# Remote-focused job boards
from backend.searchers.weworkremotely_searcher import WeWorkRemotelySearcher
from backend.searchers.remoteco_searcher import RemoteCoSearcher
from backend.searchers.workingnomads_searcher import WorkingNomadsSearcher
from backend.searchers.jobspresso_searcher import JobspressoSearcher

# Industry-specific additional searchers
from backend.searchers.higheredjobs_searcher import HigherEdJobsSearcher
from backend.searchers.usajobs_searcher import USAJobsSearcher
from backend.searchers.idealist_searcher import IdealistSearcher
from backend.searchers.mediabistro_searcher import MediabistroSearcher
from backend.searchers.behance_searcher import BehanceSearcher

# Freelance platforms
from backend.searchers.fiverr_searcher import FiverrSearcher
from backend.searchers.freelancer_searcher import FreelancerSearcher
from backend.searchers.toptal_searcher import ToptalSearcher

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
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            WeWorkRemotelySearcher,
            WorkingNomadsSearcher,
            ToptalSearcher,
        ],
        "data_scientist": [
            DiceSearcher,
            RemoteOKSearcher,
            HackerNewsSearcher,
            AngelListSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
            WeWorkRemotelySearcher,
            ToptalSearcher,
        ],
        "devops": [
            DiceSearcher,
            RemoteOKSearcher,
            HackerNewsSearcher,
            GitHubJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
            WeWorkRemotelySearcher,
            WorkingNomadsSearcher,
            ToptalSearcher,
        ],
        "product_manager": [
            AngelListSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            WeWorkRemotelySearcher,
            ToptalSearcher,
        ],

        # Creative roles
        "designer": [
            DribbbleSearcher,  # Design-focused job board
            BehanceSearcher,  # Adobe creative network
            AngelListSearcher,
            RemoteOKSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            WeWorkRemotelySearcher,
            FiverrSearcher,
            ToptalSearcher,
        ],
        "writer": [
            FlexJobsSearcher,
            UpworkSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            MediabistroSearcher,
            RemoteCoSearcher,
            JobspressoSearcher,
            FiverrSearcher,
            FreelancerSearcher,
        ],
        "content_creator": [
            FlexJobsSearcher,
            UpworkSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            MediabistroSearcher,
            FiverrSearcher,
            FreelancerSearcher,
        ],

        # Business roles
        "sales": [
            AngelListSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
            WeWorkRemotelySearcher,
        ],
        "marketing": [
            AngelListSearcher,
            RemoteOKSearcher,
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            MediabistroSearcher,
            GlassdoorSearcher,
            WeWorkRemotelySearcher,
            JobspressoSearcher,
        ],
        "business_analyst": [
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
            FlexJobsSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
        ],

        # Operations & Admin
        "operations": [
            AngelListSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
        ],
        "admin": [
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            UpworkSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
            SimplyHiredSearcher,
            RemoteCoSearcher,
        ],
        "project_manager": [
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
            GlassdoorSearcher,
            ToptalSearcher,
        ],

        # Finance & Accounting
        "accountant": [
            EFinancialCareersSearcher,  # Finance-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
        ],
        "finance": [
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            AngelListSearcher,
            GlassdoorSearcher,
            ToptalSearcher,
        ],
        "investment_banking": [
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],
        "quantitative_analyst": [
            EFinancialCareersSearcher,
            DiceSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            ToptalSearcher,
        ],

        # Healthcare
        "healthcare": [
            HealthCareersSearcher,  # Healthcare-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
        ],
        "nurse": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
        ],
        "physician": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],
        "medical_technician": [
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            ZipRecruiterSearcher,
        ],

        # Education
        "teacher": [
            HigherEdJobsSearcher,  # Higher education jobs
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            IdealistSearcher,  # Non-profit education
            ZipRecruiterSearcher,
        ],
        "professor": [
            HigherEdJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],
        "trainer": [
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            UpworkSearcher,
            RemoteCoSearcher,
        ],

        # Customer Service
        "customer_service": [
            FlexJobsSearcher,
            RemoteOKSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            ZipRecruiterSearcher,
            RemoteCoSearcher,
            WeWorkRemotelySearcher,
        ],
        "support": [
            RemoteOKSearcher,
            FlexJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            WeWorkRemotelySearcher,
            WorkingNomadsSearcher,
        ],

        # Legal
        "legal": [
            LawJobsSearcher,  # Legal-focused job board
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            UpworkSearcher,
            GlassdoorSearcher,
        ],
        "attorney": [
            LawJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],
        "paralegal": [
            LawJobsSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            ZipRecruiterSearcher,
        ],
        "compliance": [
            LawJobsSearcher,
            EFinancialCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],

        # Government
        "government": [
            USAJobsSearcher,  # Federal government jobs
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],
        "public_service": [
            USAJobsSearcher,
            IdealistSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],

        # Non-profit / Social Impact
        "nonprofit": [
            IdealistSearcher,  # Non-profit focused
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "social_worker": [
            IdealistSearcher,
            HealthCareersSearcher,
            IndeedSearcher,
            LinkedInSearcher,
        ],

        # Media & Communications
        "journalist": [
            MediabistroSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
        ],
        "public_relations": [
            MediabistroSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            GlassdoorSearcher,
        ],

        # Freelance/Consultant (any field)
        "freelancer": [
            UpworkSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
            FiverrSearcher,
            FreelancerSearcher,
            ToptalSearcher,
            WeWorkRemotelySearcher,
            JobspressoSearcher,
        ],
        "consultant": [
            UpworkSearcher,
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            ToptalSearcher,
            FreelancerSearcher,
        ],

        # Default/General
        "general": [
            IndeedSearcher,
            LinkedInSearcher,
            FlexJobsSearcher,
            RemoteOKSearcher,
            GlassdoorSearcher,
            ZipRecruiterSearcher,
            MonsterSearcher,
            SimplyHiredSearcher,
            WeWorkRemotelySearcher,
            RemoteCoSearcher,
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
    def get_all_searchers(cls) -> List[BaseJobSearcher]:
        """Get one instance of each unique searcher type."""
        # Collect all unique searcher classes
        all_classes = set()
        for searcher_list in cls.PROFESSION_SEARCHERS.values():
            all_classes.update(searcher_list)

        # Instantiate each searcher once
        searchers = []
        for searcher_class in all_classes:
            try:
                searchers.append(searcher_class())
            except Exception as e:
                logger.error(f"Error instantiating {searcher_class.__name__}: {e}")

        logger.info(f"Loaded {len(searchers)} total unique searchers")
        return searchers
    
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