"""Base scorer interface for job matching."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Result of job scoring."""
    
    total_score: float  # 0-100
    breakdown: Dict[str, float]  # Component scores
    explanation: str  # Human-readable explanation
    confidence: float  # 0-1 confidence in the score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_score": self.total_score,
            "breakdown": self.breakdown,
            "explanation": self.explanation,
            "confidence": self.confidence
        }


class BaseScorer(ABC):
    """Abstract base class for job scoring algorithms."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def score(
        self, 
        job: Dict[str, Any], 
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ScoringResult:
        """
        Score a job for a user profile.
        
        Args:
            job: Job data dictionary
            profile: User profile data dictionary
            context: Optional context (previous matches, feedback, etc.)
            
        Returns:
            ScoringResult with score and breakdown
        """
        pass
    
    def normalize_score(self, score: float, min_val: float = 0, max_val: float = 1) -> float:
        """
        Normalize score to 0-100 range.
        
        Args:
            score: Raw score
            min_val: Minimum possible value
            max_val: Maximum possible value
            
        Returns:
            Normalized score (0-100)
        """
        if max_val == min_val:
            return 50.0
        
        normalized = (score - min_val) / (max_val - min_val)
        return max(0, min(100, normalized * 100))
    
    def calculate_weighted_score(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """
        Calculate weighted average of multiple scores.
        
        Args:
            scores: Dictionary of component scores
            weights: Dictionary of weights for each component
            
        Returns:
            Weighted average score
        """
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(
            scores.get(component, 0) * weight 
            for component, weight in weights.items()
        )
        
        return weighted_sum / total_weight