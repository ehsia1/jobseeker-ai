"""Job board searchers for active job discovery."""

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

# Core searchers
from backend.searchers.remoteok_searcher import RemoteOKSearcher
from backend.searchers.github_jobs_searcher import GitHubJobsSearcher
from backend.searchers.hackernews_searcher import HackerNewsSearcher
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
from backend.searchers.remotive_searcher import RemotiveSearcher

# Job aggregators (Indeed alternatives)
from backend.searchers.adzuna_searcher import AdzunaSearcher

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

# Registry
from backend.searchers.searcher_registry import SearcherRegistry

__all__ = [
    # Base classes
    "BaseJobSearcher",
    "SearchQuery",
    "SearchResult",

    # Core searchers
    "RemoteOKSearcher",
    "GitHubJobsSearcher",
    "HackerNewsSearcher",
    "IndeedSearcher",
    "LinkedInSearcher",
    "AngelListSearcher",
    "FlexJobsSearcher",
    "UpworkSearcher",

    # Industry-specific
    "DiceSearcher",
    "DribbbleSearcher",
    "HealthCareersSearcher",
    "LawJobsSearcher",
    "EFinancialCareersSearcher",

    # General job boards
    "GlassdoorSearcher",
    "ZipRecruiterSearcher",
    "MonsterSearcher",
    "SimplyHiredSearcher",

    # Remote-focused
    "WeWorkRemotelySearcher",
    "RemoteCoSearcher",
    "WorkingNomadsSearcher",
    "JobspressoSearcher",
    "RemotiveSearcher",

    # Job aggregators (Indeed alternatives)
    "AdzunaSearcher",

    # Industry-specific additional
    "HigherEdJobsSearcher",
    "USAJobsSearcher",
    "IdealistSearcher",
    "MediabistroSearcher",
    "BehanceSearcher",

    # Freelance platforms
    "FiverrSearcher",
    "FreelancerSearcher",
    "ToptalSearcher",

    # Registry
    "SearcherRegistry",
]
