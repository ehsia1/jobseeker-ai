"""Main job scoring implementation."""

from typing import Dict, Any, List, Optional, Set
import numpy as np
from decimal import Decimal
import re

from backend.scorers.base import BaseScorer, ScoringResult
from backend.scorers.embedding_service import EmbeddingService


class JobScorer(BaseScorer):
    """Comprehensive job scoring system combining multiple factors."""
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        super().__init__("comprehensive_scorer")
        self.embedding_service = embedding_service or EmbeddingService(model_type="local")
        
        # Scoring weights (configurable)
        self.weights = {
            "semantic_similarity": 0.35,  # AI embedding similarity
            "skill_match": 0.25,          # Direct skill matching
            "compensation_fit": 0.15,     # Rate/salary alignment
            "requirements_match": 0.15,   # Years of experience, etc.
            "preferences_match": 0.10,    # Remote, industry, etc.
        }
    
    async def score(
        self,
        job: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ScoringResult:
        """
        Score a job for a user profile using multiple factors.
        
        Args:
            job: Job data dictionary
            profile: User profile data dictionary
            context: Optional context (previous feedback, etc.)
            
        Returns:
            ScoringResult with comprehensive scoring
        """
        
        scores = {}
        
        # 1. Semantic Similarity (AI embeddings)
        if job.get('job_embedding') and profile.get('profile_embedding'):
            # Use existing embeddings if available
            semantic_score = self.embedding_service.calculate_similarity(
                np.array(job['job_embedding']),
                np.array(profile['profile_embedding'])
            )
        else:
            # Generate embeddings on the fly
            job_embedding = await self.embedding_service.generate_job_embedding(job)
            profile_embedding = await self.embedding_service.generate_profile_embedding(profile)
            semantic_score = self.embedding_service.calculate_similarity(
                job_embedding,
                profile_embedding
            )
        
        scores["semantic_similarity"] = self.normalize_score(semantic_score)
        
        # 2. Skill Matching
        skill_score = self._calculate_skill_match(job, profile)
        scores["skill_match"] = skill_score
        
        # 3. Compensation Fit
        comp_score = self._calculate_compensation_fit(job, profile)
        scores["compensation_fit"] = comp_score
        
        # 4. Requirements Match
        req_score = self._calculate_requirements_match(job, profile)
        scores["requirements_match"] = req_score
        
        # 5. Preferences Match
        pref_score = self._calculate_preferences_match(job, profile)
        scores["preferences_match"] = pref_score
        
        # Calculate total weighted score
        total_score = self.calculate_weighted_score(scores, self.weights)
        
        # Apply context adjustments (if user has provided feedback)
        if context:
            total_score = self._apply_context_adjustments(total_score, job, context)
        
        # Generate explanation
        explanation = self._generate_explanation(scores, job, profile)
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(job, profile)
        
        return ScoringResult(
            total_score=total_score,
            breakdown=scores,
            explanation=explanation,
            confidence=confidence
        )
    
    def _calculate_skill_match(self, job: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate skill matching score."""
        
        job_skills = set(skill.lower() for skill in job.get('skills', []))
        profile_skills = set(skill.lower() for skill in profile.get('skills', []))
        
        if not job_skills:
            return 50.0  # Neutral score if no skills specified
        
        if not profile_skills:
            return 0.0  # No match if user has no skills listed
        
        # Find matching skills
        matching_skills = job_skills.intersection(profile_skills)
        
        # Calculate match percentage
        match_percentage = len(matching_skills) / len(job_skills)
        
        # Bonus for matching critical skills
        critical_skills = self._identify_critical_skills(job)
        critical_matches = matching_skills.intersection(critical_skills)
        
        if critical_matches:
            match_percentage += 0.2 * (len(critical_matches) / max(1, len(critical_skills)))
        
        return self.normalize_score(min(1.0, match_percentage))
    
    def _identify_critical_skills(self, job: Dict[str, Any]) -> Set[str]:
        """Identify critical skills from job requirements."""
        
        critical = set()
        
        # Look for keywords indicating importance
        description = (job.get('description', '') + ' ' + ' '.join(job.get('requirements', []))).lower()
        
        critical_patterns = [
            r'must have[:\s]+([^.,]+)',
            r'required[:\s]+([^.,]+)',
            r'essential[:\s]+([^.,]+)',
            r'mandatory[:\s]+([^.,]+)',
        ]
        
        for pattern in critical_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                # Extract skills from the match
                words = match.lower().split()
                for skill in job.get('skills', []):
                    if skill.lower() in words:
                        critical.add(skill.lower())
        
        # If no explicit critical skills, assume first 3 are most important
        if not critical and job.get('skills'):
            critical = set(skill.lower() for skill in job['skills'][:3])
        
        return critical
    
    def _calculate_compensation_fit(self, job: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate compensation alignment score."""
        
        # Get job compensation
        job_min = job.get('rate_min')
        job_max = job.get('rate_max')
        job_type = job.get('rate_type', 'hourly')
        
        # Get user expectations
        user_min = profile.get('min_rate_usd')
        
        # No compensation info - neutral score
        if not job_min and not job_max:
            return 50.0
        
        # User has no rate preference - good match
        if not user_min:
            return 75.0
        
        # Convert to comparable rates (assume hourly)
        if job_type == 'annual':
            # Convert annual to hourly (assume 2080 hours/year)
            if job_min:
                job_min = job_min / 2080
            if job_max:
                job_max = job_max / 2080
        elif job_type == 'fixed':
            # For fixed price, we can't directly compare - neutral score
            return 50.0
        
        # Convert Decimal to float for comparison
        if isinstance(job_min, Decimal):
            job_min = float(job_min)
        if isinstance(job_max, Decimal):
            job_max = float(job_max)
        if isinstance(user_min, Decimal):
            user_min = float(user_min)
        
        # Calculate score based on how well job meets user minimum
        if job_max and job_max >= user_min:
            if job_min and job_min >= user_min:
                # Exceeds expectations
                score = 1.0
            else:
                # Partially meets (max is good, min is below)
                score = 0.7
        elif job_min and job_min >= user_min * 0.9:
            # Close to expectations (within 10%)
            score = 0.8
        elif job_min and job_min >= user_min * 0.75:
            # Somewhat below expectations (within 25%)
            score = 0.5
        else:
            # Significantly below expectations
            score = 0.2
        
        return self.normalize_score(score)
    
    def _calculate_requirements_match(self, job: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate requirements matching score."""
        
        score_components = []
        
        # Experience years matching
        job_requirements = ' '.join(job.get('requirements', [])).lower()
        
        # Extract required years of experience
        exp_pattern = r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)'
        exp_matches = re.findall(exp_pattern, job_requirements)
        
        if exp_matches:
            required_years = int(exp_matches[0])
            user_years = profile.get('experience_years', 0)
            
            if user_years >= required_years:
                exp_score = 1.0
            elif user_years >= required_years * 0.75:
                exp_score = 0.7
            else:
                exp_score = max(0.2, user_years / required_years)
            
            score_components.append(exp_score)
        
        # Certification matching
        job_certs = self._extract_certifications(job)
        user_certs = set(cert.lower() for cert in profile.get('certifications', []))
        
        if job_certs:
            matching_certs = job_certs.intersection(user_certs)
            cert_score = len(matching_certs) / len(job_certs)
            score_components.append(cert_score)
        
        # Education requirements
        if any(degree in job_requirements for degree in ['bachelor', 'master', 'phd', 'degree']):
            # Simple check - assume user meets if they have experience
            if profile.get('experience_years', 0) >= 3:
                score_components.append(0.8)
            else:
                score_components.append(0.4)
        
        if not score_components:
            return 75.0  # Good score if no specific requirements
        
        avg_score = sum(score_components) / len(score_components)
        return self.normalize_score(avg_score)
    
    def _extract_certifications(self, job: Dict[str, Any]) -> Set[str]:
        """Extract certification requirements from job."""
        
        cert_patterns = [
            'aws', 'azure', 'gcp', 'cissp', 'pmp', 'scrum master',
            'ccna', 'ccnp', 'kubernetes', 'docker', 'terraform'
        ]
        
        text = (job.get('description', '') + ' ' + ' '.join(job.get('requirements', []))).lower()
        
        found_certs = set()
        for cert in cert_patterns:
            if cert in text:
                found_certs.add(cert)
        
        return found_certs
    
    def _calculate_preferences_match(self, job: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate preferences alignment score."""
        
        preferences = profile.get('preferences', {})
        score_components = []
        
        # Remote work preference
        if preferences.get('remote_only'):
            if job.get('remote'):
                score_components.append(1.0)
            else:
                score_components.append(0.0)  # Deal breaker
                return 0.0  # If remote_only and job isn't remote, very low score
        elif job.get('remote'):
            score_components.append(1.0)  # Remote is a bonus
        
        # Industry preference
        preferred_industries = preferences.get('industries', [])
        if preferred_industries:
            # Check if company/description mentions preferred industries
            job_text = (job.get('company', '') + ' ' + job.get('description', '')).lower()
            
            industry_match = any(
                industry.lower() in job_text 
                for industry in preferred_industries
            )
            
            score_components.append(1.0 if industry_match else 0.5)
        
        # Work hours preference
        max_hours = profile.get('max_hours_per_week')
        job_hours = job.get('hours_per_week')
        
        if max_hours and job_hours:
            if job_hours <= max_hours:
                score_components.append(1.0)
            else:
                score_components.append(max(0.2, max_hours / job_hours))
        
        # Avoid keywords
        avoid_keywords = preferences.get('avoid_keywords', [])
        if avoid_keywords:
            job_text = (
                job.get('title', '') + ' ' + 
                job.get('description', '') + ' ' +
                ' '.join(job.get('skills', []))
            ).lower()
            
            has_avoided = any(
                keyword.lower() in job_text 
                for keyword in avoid_keywords
            )
            
            if has_avoided:
                return 0.0  # Strong negative signal
        
        if not score_components:
            return 75.0  # Neutral-good score if no specific preferences
        
        avg_score = sum(score_components) / len(score_components)
        return self.normalize_score(avg_score)
    
    def _apply_context_adjustments(
        self, 
        base_score: float, 
        job: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> float:
        """Apply adjustments based on user feedback and history."""
        
        adjusted_score = base_score
        
        # Boost score for similar jobs that user applied to
        if context.get('applied_jobs'):
            similarity_boost = 0
            for applied_job in context['applied_jobs'][-10:]:  # Last 10 applications
                if self._jobs_similar(job, applied_job):
                    similarity_boost += 5
            
            adjusted_score = min(100, adjusted_score + similarity_boost)
        
        # Reduce score for similar jobs that user rejected
        if context.get('rejected_jobs'):
            similarity_penalty = 0
            for rejected_job in context['rejected_jobs'][-10:]:
                if self._jobs_similar(job, rejected_job):
                    similarity_penalty += 10
            
            adjusted_score = max(0, adjusted_score - similarity_penalty)
        
        # ML model adjustment (if available)
        if context.get('ml_adjustment'):
            ml_factor = context['ml_adjustment']
            adjusted_score = adjusted_score * (1 + ml_factor)
            adjusted_score = max(0, min(100, adjusted_score))
        
        return adjusted_score
    
    def _jobs_similar(self, job1: Dict[str, Any], job2: Dict[str, Any]) -> bool:
        """Check if two jobs are similar."""
        
        # Similar if same company
        if job1.get('company') and job1['company'] == job2.get('company'):
            return True
        
        # Similar if >50% skill overlap
        skills1 = set(job1.get('skills', []))
        skills2 = set(job2.get('skills', []))
        
        if skills1 and skills2:
            overlap = len(skills1.intersection(skills2))
            if overlap >= len(skills1) * 0.5:
                return True
        
        return False
    
    def _generate_explanation(
        self, 
        scores: Dict[str, float], 
        job: Dict[str, Any], 
        profile: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of the score."""
        
        explanations = []
        
        # Semantic similarity
        sem_score = scores.get('semantic_similarity', 0)
        if sem_score >= 80:
            explanations.append("Excellent conceptual match")
        elif sem_score >= 60:
            explanations.append("Good overall alignment")
        
        # Skill match
        skill_score = scores.get('skill_match', 0)
        if skill_score >= 80:
            explanations.append("Strong skill match")
        elif skill_score >= 60:
            explanations.append("Good skill overlap")
        elif skill_score < 40:
            explanations.append("Limited skill match")
        
        # Compensation
        comp_score = scores.get('compensation_fit', 0)
        if comp_score >= 80:
            explanations.append("Meets/exceeds rate expectations")
        elif comp_score < 40:
            explanations.append("Below desired compensation")
        
        # Requirements
        req_score = scores.get('requirements_match', 0)
        if req_score >= 80:
            explanations.append("Meets all requirements")
        elif req_score < 40:
            explanations.append("May not meet all requirements")
        
        # Preferences
        pref_score = scores.get('preferences_match', 0)
        if job.get('remote') and profile.get('preferences', {}).get('remote_only'):
            explanations.append("Remote position ✓")
        
        # Join with proper formatting
        if explanations:
            return " • ".join(explanations)
        else:
            return "Moderate match based on available information"
    
    def _calculate_confidence(self, job: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate confidence in the scoring based on data completeness."""
        
        confidence_factors = []
        
        # Job data completeness
        job_fields = ['title', 'description', 'skills', 'requirements', 'rate_min', 'rate_max']
        job_completeness = sum(1 for field in job_fields if job.get(field)) / len(job_fields)
        confidence_factors.append(job_completeness)
        
        # Profile data completeness
        profile_fields = ['skills', 'experience_years', 'min_rate_usd', 'preferences']
        profile_completeness = sum(1 for field in profile_fields if profile.get(field)) / len(profile_fields)
        confidence_factors.append(profile_completeness)
        
        # Average confidence
        return sum(confidence_factors) / len(confidence_factors)