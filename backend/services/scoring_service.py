"""Advanced scoring service for job matching."""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.models.job import Job
from backend.models.user import UserProfile
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a job match score."""
    
    total_score: float  # 0-100
    semantic_similarity: float  # 0-100
    skill_match: float  # 0-100
    experience_match: float  # 0-100
    compensation_match: float  # 0-100
    location_match: float  # 0-100
    freshness_score: float  # 0-100
    preference_match: float  # 0-100
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'total_score': self.total_score,
            'semantic_similarity': self.semantic_similarity,
            'skill_match': self.skill_match,
            'experience_match': self.experience_match,
            'compensation_match': self.compensation_match,
            'location_match': self.location_match,
            'freshness_score': self.freshness_score,
            'preference_match': self.preference_match
        }


class ScoringService:
    """Service for scoring job-profile matches."""
    
    # Weights for different scoring components
    DEFAULT_WEIGHTS = {
        'semantic_similarity': 0.25,  # 25% - How well the job description matches profile
        'skill_match': 0.25,          # 25% - Direct skill overlap
        'experience_match': 0.15,     # 15% - Experience level alignment
        'compensation_match': 0.15,   # 15% - Salary/rate expectations
        'location_match': 0.10,       # 10% - Location preferences
        'freshness_score': 0.05,      # 5%  - How recent the job posting is
        'preference_match': 0.05      # 5%  - Other preferences (remote, industry, etc.)
    }
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize scoring service.
        
        Args:
            embedding_service: Optional embedding service instance
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.weights = self.DEFAULT_WEIGHTS.copy()
    
    def score_job(self, job: Job, profile: UserProfile) -> ScoreBreakdown:
        """
        Calculate comprehensive score for a job-profile match.
        
        Args:
            job: Job to score
            profile: User profile to match against
            
        Returns:
            ScoreBreakdown with detailed scoring
        """
        scores = {}
        
        # 1. Semantic Similarity (if embeddings available)
        scores['semantic_similarity'] = self._calculate_semantic_similarity(job, profile)
        
        # 2. Skill Match
        scores['skill_match'] = self._calculate_skill_match(job, profile)
        
        # 3. Experience Match
        scores['experience_match'] = self._calculate_experience_match(job, profile)
        
        # 4. Compensation Match
        scores['compensation_match'] = self._calculate_compensation_match(job, profile)
        
        # 5. Location Match
        scores['location_match'] = self._calculate_location_match(job, profile)
        
        # 6. Freshness Score
        scores['freshness_score'] = self._calculate_freshness_score(job)
        
        # 7. Preference Match
        scores['preference_match'] = self._calculate_preference_match(job, profile)
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * self.weights[key] 
            for key in scores.keys()
        )
        
        return ScoreBreakdown(
            total_score=min(100, total_score),
            **scores
        )
    
    def _calculate_semantic_similarity(self, job: Job, profile: UserProfile) -> float:
        """Calculate semantic similarity using embeddings."""
        try:
            # Check if both have embeddings
            if not job.embedding or not profile.profile_embedding:
                # Fall back to basic text similarity
                return self._calculate_text_similarity(job, profile)
            
            # Convert stored embeddings to numpy arrays
            job_embedding = np.array(job.embedding)
            profile_embedding = np.array(profile.profile_embedding)
            
            # Calculate cosine similarity
            similarity = self.embedding_service.calculate_similarity(
                job_embedding, 
                profile_embedding
            )
            
            # Convert to 0-100 scale
            return similarity * 100
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 50.0  # Default middle score
    
    def _calculate_text_similarity(self, job: Job, profile: UserProfile) -> float:
        """Basic text similarity when embeddings not available."""
        # Generate embeddings on the fly
        try:
            job_dict = {
                'title': job.title,
                'description': job.description,
                'skills': job.skills,
                'company': job.company,
                'location': job.location,
                'remote': job.remote
            }
            job_embedding = self.embedding_service.generate_job_embedding(job_dict)
            profile_embedding = self.embedding_service.generate_profile_embedding(profile)
            
            similarity = self.embedding_service.calculate_similarity(
                job_embedding,
                profile_embedding
            )
            return similarity * 100
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return 50.0
    
    def _calculate_skill_match(self, job: Job, profile: UserProfile) -> float:
        """Calculate skill overlap between job and profile."""
        if not job.skills or not profile.skills:
            return 0.0
        
        job_skills = set(s.lower() for s in job.skills)
        profile_skills = set(s.lower() for s in profile.skills)
        
        if not job_skills:
            return 100.0  # No specific skills required
        
        # Calculate what percentage of required skills the user has
        matched_skills = job_skills & profile_skills
        match_percentage = (len(matched_skills) / len(job_skills)) * 100
        
        # Bonus for having additional relevant skills
        extra_skills = profile_skills - job_skills
        if extra_skills:
            bonus = min(10, len(extra_skills) * 2)  # Up to 10% bonus
            match_percentage = min(100, match_percentage + bonus)
        
        return match_percentage
    
    def _calculate_experience_match(self, job: Job, profile: UserProfile) -> float:
        """Calculate experience level match."""
        # Extract experience requirements from job
        job_exp_years = self._extract_experience_years(job)
        profile_exp_years = profile.experience_years or 0
        
        if job_exp_years is None:
            return 75.0  # No specific requirement, good match
        
        # Perfect match if within range
        if isinstance(job_exp_years, tuple):
            min_years, max_years = job_exp_years
            if min_years <= profile_exp_years <= max_years:
                return 100.0
            elif profile_exp_years < min_years:
                # Under-qualified: reduce score based on gap
                gap = min_years - profile_exp_years
                return max(0, 100 - (gap * 20))  # -20% per year gap
            else:
                # Over-qualified: small penalty
                gap = profile_exp_years - max_years
                return max(70, 100 - (gap * 5))  # -5% per year over
        else:
            # Single value requirement
            if profile_exp_years >= job_exp_years:
                return 100.0
            else:
                gap = job_exp_years - profile_exp_years
                return max(0, 100 - (gap * 20))
    
    def _extract_experience_years(self, job: Job) -> Optional[Union[int, Tuple[int, int]]]:
        """Extract experience requirements from job."""
        # Look in requirements field
        if job.requirements:
            req_text = str(job.requirements).lower()
            # Look for patterns like "3+ years", "3-5 years", etc.
            import re
            
            # Pattern for range (e.g., "3-5 years")
            range_pattern = r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)'
            match = re.search(range_pattern, req_text)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            
            # Pattern for minimum (e.g., "3+ years", "minimum 3 years")
            min_pattern = r'(?:(?:minimum|at least|min\.?)\s*)?(\d+)\+?\s*(?:years?|yrs?)'
            match = re.search(min_pattern, req_text)
            if match:
                return int(match.group(1))
        
        # Check job title for senior/junior indicators
        title_lower = job.title.lower()
        if any(word in title_lower for word in ['senior', 'sr.', 'lead', 'principal']):
            return 5  # Senior positions typically need 5+ years
        elif any(word in title_lower for word in ['junior', 'jr.', 'entry']):
            return 0  # Entry level
        elif 'mid' in title_lower:
            return 3  # Mid-level
        
        return None  # No specific requirement found
    
    def _calculate_compensation_match(self, job: Job, profile: UserProfile) -> float:
        """Calculate compensation alignment."""
        # Check if we have compensation data
        if not (job.rate_min or job.rate_max):
            return 75.0  # No data, neutral score
        
        if not profile.min_rate_usd:
            return 75.0  # User has no preference
        
        # Convert to comparable values (annual)
        job_min_annual = self._to_annual_rate(job.rate_min, job.rate_type) if job.rate_min else 0
        job_max_annual = self._to_annual_rate(job.rate_max, job.rate_type) if job.rate_max else job_min_annual * 1.2
        profile_min_annual = float(profile.min_rate_usd) if profile.min_rate_usd else 0
        
        # Perfect match if profile minimum is within job range
        if job_min_annual <= profile_min_annual <= job_max_annual:
            return 100.0
        
        # Calculate how far off we are
        if profile_min_annual < job_min_annual:
            # Job pays more than expected - great!
            return 100.0
        else:
            # Job pays less than expected
            gap_percentage = ((profile_min_annual - job_max_annual) / profile_min_annual) * 100
            return max(0, 100 - gap_percentage)
    
    def _to_annual_rate(self, rate: float, rate_type: str) -> float:
        """Convert rate to annual salary."""
        if not rate:
            return 0
        
        rate_type_lower = (rate_type or 'annual').lower()
        
        if 'hour' in rate_type_lower:
            return rate * 2080  # 40 hours/week * 52 weeks
        elif 'day' in rate_type_lower:
            return rate * 260  # 5 days/week * 52 weeks
        elif 'week' in rate_type_lower:
            return rate * 52
        elif 'month' in rate_type_lower:
            return rate * 12
        else:  # Assume annual
            return rate
    
    def _calculate_location_match(self, job: Job, profile: UserProfile) -> float:
        """Calculate location preference match."""
        # Remote work preference
        if profile.preferences and profile.preferences.get('remote_only'):
            if job.remote:
                return 100.0
            else:
                return 25.0  # Heavy penalty for non-remote when remote required
        
        # If job is remote, it's always a good match
        if job.remote:
            return 100.0
        
        # Check location match
        if not job.location or not profile.location:
            return 50.0  # No location data
        
        job_location_lower = job.location.lower()
        profile_location_lower = profile.location.lower()
        
        # Exact match
        if profile_location_lower in job_location_lower or job_location_lower in profile_location_lower:
            return 100.0
        
        # Same city/state (basic matching)
        job_parts = set(job_location_lower.split(','))
        profile_parts = set(profile_location_lower.split(','))
        
        if job_parts & profile_parts:
            return 75.0  # Some overlap
        
        return 50.0  # Different locations
    
    def _calculate_freshness_score(self, job: Job) -> float:
        """Calculate how fresh/recent the job posting is."""
        if not job.posted_at:
            return 50.0  # Unknown posting date
        
        # Calculate age in days
        now = datetime.utcnow()
        if job.posted_at.tzinfo:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age_days = (now - job.posted_at).days
        
        # Scoring based on age
        if age_days <= 1:
            return 100.0  # Posted today/yesterday
        elif age_days <= 3:
            return 90.0
        elif age_days <= 7:
            return 75.0
        elif age_days <= 14:
            return 60.0
        elif age_days <= 30:
            return 40.0
        else:
            return max(0, 40 - age_days)  # Older than 30 days
    
    def _calculate_preference_match(self, job: Job, profile: UserProfile) -> float:
        """Calculate match for other preferences."""
        if not profile.preferences:
            return 75.0  # No specific preferences
        
        score = 75.0  # Base score
        matches = 0
        checks = 0
        
        # Industry preference
        if profile.preferences.get('industries'):
            checks += 1
            preferred_industries = [i.lower() for i in profile.preferences['industries']]
            job_text = f"{job.title} {job.company} {job.description or ''}".lower()
            
            if any(industry in job_text for industry in preferred_industries):
                matches += 1
        
        # Job type preference
        if profile.preferences.get('job_types'):
            checks += 1
            preferred_types = [t.lower() for t in profile.preferences['job_types']]
            job_type = job.employment_type.lower() if job.employment_type else 'full-time'
            
            if job_type in preferred_types:
                matches += 1
        
        # Avoid keywords
        if profile.preferences.get('avoid_keywords'):
            checks += 1
            avoid_keywords = [k.lower() for k in profile.preferences['avoid_keywords']]
            job_text = f"{job.title} {job.description or ''}".lower()
            
            if not any(keyword in job_text for keyword in avoid_keywords):
                matches += 1
        
        # Calculate final score
        if checks > 0:
            score = (matches / checks) * 100
        
        return score
    
    def generate_explanation(self, job: Job, profile: UserProfile, score_breakdown: ScoreBreakdown) -> str:
        """
        Generate human-readable explanation of the score.
        
        Args:
            job: Job being scored
            profile: User profile
            score_breakdown: Detailed score breakdown
            
        Returns:
            Explanation text
        """
        explanations = []
        
        # Overall assessment
        if score_breakdown.total_score >= 80:
            explanations.append("⭐ Excellent match! This job aligns very well with your profile.")
        elif score_breakdown.total_score >= 60:
            explanations.append("✅ Good match. This job has strong alignment with your skills.")
        elif score_breakdown.total_score >= 40:
            explanations.append("🔄 Moderate match. Some aspects align well, others may need consideration.")
        else:
            explanations.append("⚠️ Weak match. This job may not align well with your profile.")
        
        # Skill match explanation
        if score_breakdown.skill_match >= 80:
            explanations.append(f"• Skills: Strong match ({score_breakdown.skill_match:.0f}%) - You have most required skills")
        elif score_breakdown.skill_match >= 50:
            explanations.append(f"• Skills: Partial match ({score_breakdown.skill_match:.0f}%) - You have some required skills")
        else:
            explanations.append(f"• Skills: Low match ({score_breakdown.skill_match:.0f}%) - Missing several key skills")
        
        # Experience explanation
        if score_breakdown.experience_match >= 80:
            explanations.append(f"• Experience: Well aligned ({score_breakdown.experience_match:.0f}%)")
        elif score_breakdown.experience_match < 50:
            explanations.append(f"• Experience: May need more experience ({score_breakdown.experience_match:.0f}%)")
        
        # Compensation explanation
        if score_breakdown.compensation_match >= 80:
            explanations.append(f"• Compensation: Meets expectations ({score_breakdown.compensation_match:.0f}%)")
        elif score_breakdown.compensation_match < 50:
            explanations.append(f"• Compensation: Below expectations ({score_breakdown.compensation_match:.0f}%)")
        
        # Location explanation
        if job.remote:
            explanations.append("• Location: Remote position ✓")
        elif score_breakdown.location_match >= 80:
            explanations.append(f"• Location: Good match ({score_breakdown.location_match:.0f}%)")
        elif score_breakdown.location_match < 50:
            explanations.append(f"• Location: May require relocation ({score_breakdown.location_match:.0f}%)")
        
        # Freshness
        if score_breakdown.freshness_score >= 90:
            explanations.append("• Posting: Very recent (apply soon!)")
        elif score_breakdown.freshness_score < 50:
            explanations.append("• Posting: Older listing (may be filled)")
        
        return "\n".join(explanations)
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update scoring weights.
        
        Args:
            new_weights: Dictionary of component weights
        """
        # Validate weights sum to 1.0
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.weights.update(new_weights)
        logger.info(f"Updated scoring weights: {self.weights}")