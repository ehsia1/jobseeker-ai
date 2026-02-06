"""Business logic services."""

from backend.services.ingestion_service import IngestionService
from backend.services.matching_service import MatchingService
from backend.services.application_service import ApplicationTrackingService
from backend.services.feedback_service import FeedbackCollectionService
from backend.services.recommendation_engine import RecommendationEngine
from backend.services.template_service import TemplateService
from backend.services.email_service import EmailService, get_email_service
from backend.services.digest_service import DigestService

__all__ = [
    "IngestionService",
    "MatchingService",
    "ApplicationTrackingService",
    "FeedbackCollectionService",
    "RecommendationEngine",
    "TemplateService",
    "EmailService",
    "get_email_service",
    "DigestService",
]