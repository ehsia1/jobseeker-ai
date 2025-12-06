"""Job ingestion management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models.user import User
from backend.models.job import Job
from backend.api.routes.auth import get_current_user
from backend.services.ingestion_service import IngestionService

try:
    from backend.workers.job_ingestion import ingest_jobs_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    ingest_jobs_task = None

router = APIRouter()


@router.post("/trigger")
async def trigger_ingestion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger job ingestion from all sources."""
    
    if not current_user.is_premium:  # Only premium users can trigger manual ingestion
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for manual ingestion"
        )
    
    # Trigger background task
    task_result = ingest_jobs_task.delay()
    
    return {
        "message": "Job ingestion triggered",
        "task_id": task_result.id,
        "status": "processing"
    }


@router.get("/status")
async def ingestion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ingestion status and recent job counts."""
    
    # Get job counts by source
    result = await db.execute(
        select(Job.source, func.count(Job.id).label('count'))
        .group_by(Job.source)
    )
    source_counts = {row.source: row.count for row in result.all()}
    
    # Get recent jobs (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    recent_result = await db.execute(
        select(func.count(Job.id))
        .where(Job.created_at >= yesterday)
    )
    recent_count = recent_result.scalar() or 0
    
    return {
        "total_jobs": sum(source_counts.values()),
        "jobs_by_source": source_counts,
        "recent_jobs_24h": recent_count,
        "last_updated": datetime.utcnow().isoformat()
    }


@router.post("/test")
async def test_ingestion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test ingestion parsers without storing data."""
    
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for ingestion testing"
        )
    
    ingestion_service = IngestionService(db)
    
    try:
        test_results = await ingestion_service.test_parsers()
        return test_results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion test failed: {str(e)}"
        )


@router.get("/sources")
async def list_ingestion_sources(
    current_user: User = Depends(get_current_user)
):
    """List all configured ingestion sources."""
    
    sources = {
        "email_sources": [
            {
                "name": "upwork",
                "type": "email",
                "description": "Upwork job alert emails",
                "status": "active"
            }
        ],
        "rss_sources": [
            {
                "name": "remote_ok", 
                "type": "rss",
                "description": "Remote OK job feed",
                "url": "https://remoteok.io/remote-jobs.rss",
                "status": "active"
            }
        ]
    }
    
    return sources