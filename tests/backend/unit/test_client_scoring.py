"""
Unit tests for client-side job scoring
"""
import pytest
from backend.services.matching_service import MatchingService
from backend.models.job import Job
from backend.models.user import UserProfile


class TestClientSideScoring:
    """Test client-side scoring accuracy and performance"""
    
    @pytest.fixture
    def sample_job(self):
        """Create a sample job for testing"""
        return Job(
            title="Senior Python Developer",
            company="TechCorp",
            description="Looking for Python expert with 5+ years experience",
            skills=["python", "django", "postgresql", "redis"],
            rate_min=120,
            rate_max=150,
            rate_type="hourly",
            location="Remote",
            remote=True,
            posted_at="2025-09-01T00:00:00Z"
        )
    
    @pytest.fixture
    def sample_profile(self):
        """Create a sample user profile"""
        return UserProfile(
            skills=["python", "django", "fastapi", "postgresql"],
            experience_years=6,
            min_rate_usd=100,
            location="USA",
            preferences={
                "remote_only": True,
                "job_types": ["full-time", "contract"]
            }
        )
    
    def test_scoring_accuracy_within_margin(self, sample_job, sample_profile):
        """Verify client scoring matches server within 5% margin"""
        # Server-side scoring
        server_scorer = MatchingService(None)
        server_score = server_scorer.calculate_match_score(sample_job, sample_profile)
        
        # Simulate client-side scoring (same algorithm)
        client_score = self._simulate_client_scoring(sample_job, sample_profile)
        
        # Check within 5% margin
        difference = abs(server_score - client_score)
        assert difference <= 5, f"Score difference {difference} exceeds 5% margin"
    
    def test_scoring_performance_for_large_dataset(self, sample_profile):
        """Test scoring 1000 jobs completes in under 100ms"""
        import time
        
        # Create 1000 jobs
        jobs = []
        for i in range(1000):
            job = Job(
                title=f"Job {i}",
                company=f"Company {i}",
                skills=["python", "django"] if i % 2 == 0 else ["javascript", "react"],
                rate_min=80 + (i % 50),
                rate_max=150 + (i % 50),
                remote=i % 3 == 0
            )
            jobs.append(job)
        
        # Time the scoring
        start_time = time.time()
        
        for job in jobs:
            self._simulate_client_scoring(job, sample_profile)
        
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        assert duration < 100, f"Scoring took {duration}ms, exceeds 100ms limit"
    
    def test_skill_match_calculation(self, sample_job, sample_profile):
        """Test skill matching algorithm"""
        score = self._calculate_skill_match(sample_job, sample_profile)
        
        # 3 out of 4 job skills match = 75%, plus bonus for extra skills
        assert score >= 75
        assert score <= 100
    
    def test_compensation_match_calculation(self, sample_job, sample_profile):
        """Test compensation matching"""
        score = self._calculate_compensation_match(sample_job, sample_profile)
        
        # Job pays 120-150, user wants 100 minimum = perfect match
        assert score == 100
    
    def test_location_remote_preference(self, sample_job, sample_profile):
        """Test remote job matching for remote-only preference"""
        score = self._calculate_location_match(sample_job, sample_profile)
        
        # Remote job + remote preference = perfect match
        assert score == 100
    
    def test_freshness_scoring(self, sample_job):
        """Test job freshness scoring"""
        from datetime import datetime, timedelta
        
        # Fresh job (posted today)
        sample_job.posted_at = datetime.now()
        score = self._calculate_freshness(sample_job)
        assert score == 100
        
        # Week old job
        sample_job.posted_at = datetime.now() - timedelta(days=7)
        score = self._calculate_freshness(sample_job)
        assert score == 75
        
        # Month old job
        sample_job.posted_at = datetime.now() - timedelta(days=30)
        score = self._calculate_freshness(sample_job)
        assert score == 40
    
    def _simulate_client_scoring(self, job, profile):
        """Simulate client-side scoring algorithm"""
        weights = {
            'skill_match': 0.30,
            'experience_match': 0.20,
            'compensation_match': 0.20,
            'location_match': 0.15,
            'freshness_score': 0.10,
            'preference_match': 0.05,
        }
        
        scores = {
            'skill_match': self._calculate_skill_match(job, profile),
            'experience_match': self._calculate_experience_match(job, profile),
            'compensation_match': self._calculate_compensation_match(job, profile),
            'location_match': self._calculate_location_match(job, profile),
            'freshness_score': self._calculate_freshness(job),
            'preference_match': self._calculate_preference_match(job, profile),
        }
        
        total = sum(score * weights[key] for key, score in scores.items())
        return min(100, max(0, total))
    
    def _calculate_skill_match(self, job, profile):
        """Calculate skill match score"""
        if not job.skills or not profile.skills:
            return 50
        
        job_skills = set(s.lower() for s in job.skills)
        user_skills = set(s.lower() for s in profile.skills)
        
        matches = len(job_skills & user_skills)
        total_required = len(job_skills)
        
        if total_required == 0:
            return 75
        
        match_ratio = matches / total_required
        bonus = 10 if len(user_skills) > len(job_skills) else 0
        
        return min(100, match_ratio * 100 + bonus)
    
    def _calculate_experience_match(self, job, profile):
        """Calculate experience match"""
        if not profile.experience_years:
            return 50
        
        # Simple heuristic: assume 5 years required for "Senior"
        required = 5 if "senior" in job.title.lower() else 3
        
        if profile.experience_years >= required:
            return min(100, 80 + (profile.experience_years - required) * 2)
        else:
            ratio = profile.experience_years / required
            return max(0, ratio * 80)
    
    def _calculate_compensation_match(self, job, profile):
        """Calculate compensation match"""
        if not profile.min_rate_usd:
            return 75
        
        job_max = job.rate_max or job.rate_min or 0
        
        if job_max >= profile.min_rate_usd:
            return 100
        
        if job_max == 0:
            return 50
        
        gap = profile.min_rate_usd - job_max
        percentage_gap = (gap / profile.min_rate_usd) * 100
        
        return max(0, 100 - percentage_gap)
    
    def _calculate_location_match(self, job, profile):
        """Calculate location match"""
        if job.remote:
            return 100
        
        if profile.preferences and profile.preferences.get('remote_only'):
            return 20 if not job.remote else 100
        
        return 50
    
    def _calculate_freshness(self, job):
        """Calculate job freshness score"""
        from datetime import datetime
        
        if isinstance(job.posted_at, str):
            posted = datetime.fromisoformat(job.posted_at.replace('Z', '+00:00'))
        else:
            posted = job.posted_at
        
        now = datetime.now(posted.tzinfo) if posted.tzinfo else datetime.now()
        days_old = (now - posted).days
        
        if days_old <= 1:
            return 100
        elif days_old <= 3:
            return 90
        elif days_old <= 7:
            return 75
        elif days_old <= 14:
            return 60
        elif days_old <= 30:
            return 40
        else:
            return 20
    
    def _calculate_preference_match(self, job, profile):
        """Calculate preference match"""
        if not profile.preferences:
            return 50
        
        score = 50
        prefs = profile.preferences
        
        # Job type preference
        if prefs.get('job_types') and hasattr(job, 'employment_type'):
            if job.employment_type in prefs['job_types']:
                score += 25
        
        return min(100, score)