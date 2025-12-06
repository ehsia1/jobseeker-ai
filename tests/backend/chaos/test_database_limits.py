"""
Chaos test for Supabase database size limits (500MB free tier)
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.job import Job
from backend.services.cleanup_service import DatabaseCleanupService
import random
import string


class TestDatabaseSizeLimits:
    """Test system behavior when approaching Supabase 500MB limit"""
    
    @pytest.mark.asyncio
    async def test_database_size_monitoring(self, db_session: AsyncSession):
        """Test database size monitoring and alerts"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Get current database size
        size_mb = await cleanup_service.get_database_size_mb()
        
        assert size_mb >= 0
        assert size_mb <= 500  # Should never exceed free tier
        
        # Check alert thresholds
        alerts = cleanup_service.check_size_alerts()
        
        if size_mb > 400:  # 80% threshold
            assert "WARNING" in alerts
            assert "80%" in alerts
        
        if size_mb > 475:  # 95% threshold
            assert "CRITICAL" in alerts
            assert "95%" in alerts
    
    @pytest.mark.asyncio
    async def test_automatic_cleanup_at_80_percent(self, db_session: AsyncSession):
        """Test automatic cleanup triggers at 80% capacity"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Simulate database at 80% capacity
        cleanup_service.get_database_size_mb = lambda: 400
        
        # Should trigger cleanup
        cleaned = await cleanup_service.auto_cleanup()
        
        assert cleaned > 0
        assert cleanup_service.last_cleanup_timestamp is not None
        
        # Verify old jobs were deleted (>30 days)
        old_jobs = await db_session.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_at < NOW() - INTERVAL '30 days'"
        )
        assert old_jobs.scalar() == 0
    
    @pytest.mark.asyncio
    async def test_emergency_cleanup_at_95_percent(self, db_session: AsyncSession):
        """Test emergency cleanup at 95% capacity"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Simulate database at 95% capacity
        cleanup_service.get_database_size_mb = lambda: 475
        
        # Should trigger emergency cleanup
        cleaned = await cleanup_service.emergency_cleanup()
        
        assert cleaned > 0
        
        # Verify aggressive cleanup (>7 days)
        recent_jobs = await db_session.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_at < NOW() - INTERVAL '7 days'"
        )
        assert recent_jobs.scalar() == 0
    
    @pytest.mark.asyncio
    async def test_fill_database_simulation(self, db_session: AsyncSession):
        """Simulate filling database to test cleanup triggers"""
        cleanup_service = DatabaseCleanupService(db_session)
        initial_size = await cleanup_service.get_database_size_mb()
        
        jobs_added = 0
        target_size = min(initial_size + 50, 450)  # Don't exceed 450MB in tests
        
        while await cleanup_service.get_database_size_mb() < target_size:
            # Create batch of large jobs
            jobs = []
            for _ in range(100):
                job = Job(
                    title=f"Test Job {random.randint(1, 10000)}",
                    company=f"Company {random.randint(1, 1000)}",
                    description="x" * 10000,  # 10KB description
                    skills=["python"] * 20,  # Large skill array
                    requirements={"text": "x" * 5000},  # 5KB requirements
                    raw_data={"data": "x" * 5000}  # 5KB raw data
                )
                jobs.append(job)
            
            db_session.add_all(jobs)
            await db_session.commit()
            jobs_added += 100
            
            # Check if cleanup triggered
            current_size = await cleanup_service.get_database_size_mb()
            if current_size > 400:
                cleanup_triggered = await cleanup_service.check_and_cleanup()
                assert cleanup_triggered is True
                break
        
        # Verify system is still functional
        assert await cleanup_service.get_database_size_mb() < 450
    
    @pytest.mark.asyncio
    async def test_read_only_mode_at_capacity(self, db_session: AsyncSession):
        """Test read-only mode when database is at capacity"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Simulate database at 99% capacity
        cleanup_service.get_database_size_mb = lambda: 495
        
        # Should enable read-only mode
        read_only = cleanup_service.check_read_only_mode()
        assert read_only is True
        
        # Verify writes are blocked
        with pytest.raises(Exception) as exc:
            job = Job(title="New Job", company="Company")
            db_session.add(job)
            await db_session.commit()
        
        assert "read-only" in str(exc.value).lower()
    
    @pytest.mark.asyncio
    async def test_storage_optimization_strategies(self, db_session: AsyncSession):
        """Test various storage optimization strategies"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Test 1: Compress large text fields
        compressed = await cleanup_service.compress_job_descriptions()
        assert compressed >= 0  # Number of compressed jobs
        
        # Test 2: Remove duplicate jobs
        deduped = await cleanup_service.remove_duplicate_jobs()
        assert deduped >= 0  # Number of removed duplicates
        
        # Test 3: Archive old matches
        archived = await cleanup_service.archive_old_matches()
        assert archived >= 0  # Number of archived matches
        
        # Test 4: Truncate large fields
        truncated = await cleanup_service.truncate_large_fields()
        assert truncated >= 0  # Number of truncated fields


class TestDatabaseCleanupService:
    """Test the cleanup service implementation"""
    
    @pytest.mark.asyncio
    async def test_cleanup_schedule(self):
        """Test cleanup runs on schedule"""
        from datetime import datetime, timedelta
        
        cleanup_service = DatabaseCleanupService(None)
        
        # Set last cleanup to 25 hours ago
        cleanup_service.last_cleanup_timestamp = datetime.now() - timedelta(hours=25)
        
        # Should need cleanup (runs daily)
        assert cleanup_service.needs_cleanup() is True
        
        # Set last cleanup to 1 hour ago
        cleanup_service.last_cleanup_timestamp = datetime.now() - timedelta(hours=1)
        
        # Should not need cleanup yet
        assert cleanup_service.needs_cleanup() is False
    
    @pytest.mark.asyncio
    async def test_cleanup_metrics(self, db_session: AsyncSession):
        """Test cleanup metrics and reporting"""
        cleanup_service = DatabaseCleanupService(db_session)
        
        # Run cleanup
        metrics = await cleanup_service.run_cleanup_with_metrics()
        
        assert "jobs_deleted" in metrics
        assert "space_freed_mb" in metrics
        assert "duration_seconds" in metrics
        assert "final_size_mb" in metrics
        assert metrics["final_size_mb"] <= 500