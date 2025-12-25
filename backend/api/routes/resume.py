"""Resume routes for uploading, parsing, and managing resumes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.services.resume_service import ResumeService
from backend.api.schemas.resume import (
    ResumeResponse,
    ResumeTextRequest,
    ResumeUploadResponse,
    ResumeSummary,
    WorkExperienceResponse,
    EducationEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/plain": "txt",
}

# Optional OAuth2 scheme for demo mode compatibility
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user_or_demo(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user, or create/get demo user in demo mode."""
    # Demo mode: use demo user
    if settings.demo_mode and token is None:
        from uuid import UUID

        # Get or create demo user
        result = await db.execute(
            select(User).where(User.email == "demo@localhost")
        )
        user = result.scalar_one_or_none()

        if not user:
            from uuid import uuid4

            user = User(
                id=uuid4(),
                email="demo@localhost",
                username="demo",
                password_hash="demo_not_used",
                is_active=True,
                is_premium=True,
            )
            db.add(user)
            await db.flush()

        return user

    # No token provided in non-demo mode
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    try:
        from jose import JWTError, jwt

        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Get user from database
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def _resume_to_response(resume) -> ResumeResponse:
    """Convert Resume model to response schema."""
    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        full_name=resume.full_name,
        email=resume.email,
        phone=resume.phone,
        location=resume.location,
        linkedin_url=resume.linkedin_url,
        github_url=resume.github_url,
        portfolio_url=resume.portfolio_url,
        summary=resume.summary,
        skills=resume.skills or [],
        education=[EducationEntry(**e) for e in (resume.education or [])],
        certifications=resume.certifications or [],
        languages=resume.languages or [],
        file_name=resume.file_name,
        file_type=resume.file_type,
        file_size=resume.file_size,
        parsed_at=resume.parsed_at,
        parse_quality_score=resume.parse_quality_score,
        total_experience_years=resume.total_experience_years,
        work_experiences=[
            WorkExperienceResponse(
                id=exp.id,
                company=exp.company,
                title=exp.title,
                location=exp.location,
                employment_type=exp.employment_type,
                is_remote=exp.is_remote,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                description=exp.description,
                achievements=exp.achievements or [],
                skills_used=exp.skills_used or [],
                metrics=exp.metrics or {},
                duration_months=exp.duration_months,
                duration_text=exp.duration_text,
            )
            for exp in (resume.work_experiences or [])
        ],
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume file.

    Supported formats: PDF, DOCX, DOC, TXT.
    Maximum file size: 10MB.

    The resume will be parsed using AI to extract:
    - Contact information (name, email, phone, location)
    - Professional summary
    - Skills and technologies
    - Work experience with achievements
    - Education and certifications
    """
    # Validate file type
    content_type = file.content_type
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{content_type}' not supported. Use PDF, DOCX, or TXT.",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
        )

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB.",
        )

    # Validate file not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    try:
        service = ResumeService(db)
        resume = await service.upload_and_parse(
            user_id=current_user.id,
            file_content=content,
            file_name=file.filename or "resume",
            file_type=ALLOWED_TYPES[content_type],
        )

        await db.commit()

        # Trigger background tasks: sync profile, recalculate matches, find new matches
        try:
            from backend.workers.agent_tasks import on_resume_updated
            on_resume_updated(str(current_user.id))
            logger.info(f"Triggered resume update workflow for user {current_user.id}")
        except Exception as e:
            # Don't fail the request if background tasks fail to queue
            logger.warning(f"Failed to trigger resume update workflow: {e}")

        return ResumeUploadResponse(
            message="Resume uploaded and parsed successfully",
            resume=_resume_to_response(resume),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume. Please try again or paste the text directly.",
        )


@router.post("/text", response_model=ResumeUploadResponse)
async def parse_resume_text(
    request: ResumeTextRequest,
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Parse resume from pasted text.

    Paste your resume content directly instead of uploading a file.
    Useful when you want to update specific sections or don't have the file handy.
    """
    try:
        service = ResumeService(db)
        resume = await service.parse_text(
            user_id=current_user.id,
            text=request.text,
        )

        await db.commit()

        # Trigger background tasks: sync profile, recalculate matches, find new matches
        try:
            from backend.workers.agent_tasks import on_resume_updated
            on_resume_updated(str(current_user.id))
            logger.info(f"Triggered resume update workflow for user {current_user.id}")
        except Exception as e:
            # Don't fail the request if background tasks fail to queue
            logger.warning(f"Failed to trigger resume update workflow: {e}")

        return ResumeUploadResponse(
            message="Resume parsed successfully",
            resume=_resume_to_response(resume),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Resume text parsing failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume text. Please try again.",
        )


@router.get("", response_model=Optional[ResumeResponse])
async def get_resume(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's resume.

    Returns the parsed resume data including:
    - All extracted contact and professional information
    - Skills and certifications
    - Work experience history with achievements
    - Education background

    Returns null if no resume has been uploaded.
    """
    service = ResumeService(db)
    resume = await service.get_resume(current_user.id)

    if resume is None:
        return None

    return _resume_to_response(resume)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Delete the current user's resume.

    This permanently removes the resume and all associated work experience data.
    You can upload a new resume at any time after deletion.
    """
    service = ResumeService(db)
    deleted = await service.delete_resume(current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found to delete",
        )

    await db.commit()
    return None


@router.post("/reparse", response_model=ResumeUploadResponse)
async def reparse_resume(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Re-parse the current user's resume using updated parsing logic.

    This re-processes the stored resume text without requiring a new upload.
    Useful when parsing logic has been improved to get better extraction results.
    """
    service = ResumeService(db)
    resume = await service.get_resume(current_user.id)

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found to re-parse",
        )

    if not resume.raw_text or len(resume.raw_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has no stored text content to re-parse. Please upload again.",
        )

    try:
        # Re-parse the stored text
        reparsed = await service.parse_text(
            user_id=current_user.id,
            text=resume.raw_text,
        )

        # Restore file metadata that parse_text clears
        reparsed.file_name = resume.file_name
        reparsed.file_type = resume.file_type if resume.file_type != "text" else reparsed.file_type
        reparsed.file_size = resume.file_size

        await db.commit()
        await db.refresh(reparsed)

        # Trigger background tasks: sync profile, recalculate matches, find new matches
        try:
            from backend.workers.agent_tasks import on_resume_updated
            on_resume_updated(str(current_user.id))
            logger.info(f"Triggered resume update workflow for user {current_user.id}")
        except Exception as e:
            # Don't fail the request if background tasks fail to queue
            logger.warning(f"Failed to trigger resume update workflow: {e}")

        return ResumeUploadResponse(
            message="Resume re-parsed successfully with updated logic",
            resume=_resume_to_response(reparsed),
        )

    except Exception as e:
        logger.error(f"Resume reparse failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-parse resume. Please try uploading again.",
        )


@router.get("/summary", response_model=Optional[ResumeSummary])
async def get_resume_summary(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get a brief summary of the user's resume.

    Lightweight endpoint for checking if a resume exists and basic stats.
    Returns null if no resume has been uploaded.
    """
    service = ResumeService(db)
    resume = await service.get_resume(current_user.id)

    if resume is None:
        return None

    return ResumeSummary(
        id=resume.id,
        full_name=resume.full_name,
        file_name=resume.file_name,
        file_type=resume.file_type,
        skills_count=len(resume.skills or []),
        experience_count=len(resume.work_experiences or []),
        total_experience_years=resume.total_experience_years,
        parse_quality_score=resume.parse_quality_score,
        parsed_at=resume.parsed_at,
        updated_at=resume.updated_at,
    )


@router.get("/debug/raw-text")
async def get_raw_text(
    current_user: User = Depends(get_current_user_or_demo),
    db: AsyncSession = Depends(get_db),
):
    """Get the raw extracted text from the resume for debugging.

    This shows exactly what text was extracted from your PDF/DOCX file.
    If this text doesn't match your resume, the file extraction failed.
    """
    service = ResumeService(db)
    resume = await service.get_resume(current_user.id)

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found",
        )

    raw_text = resume.raw_text or ""

    return {
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "file_size": resume.file_size,
        "raw_text_length": len(raw_text),
        "raw_text_preview": raw_text[:2000] if raw_text else None,
        "raw_text_full": raw_text,
        "parsed_at": resume.parsed_at.isoformat() if resume.parsed_at else None,
        "parse_quality_score": resume.parse_quality_score,
        "extracted_full_name": resume.full_name,
        "extracted_skills_count": len(resume.skills or []),
        "extracted_work_exp_count": len(resume.work_experiences or []),
    }


@router.get("/health")
async def resume_health():
    """Check if the resume service is operational."""
    from backend.services.llm_service import get_llm_service

    llm = get_llm_service()
    is_available = llm.is_available()

    # Check if parsing libraries are available
    pdf_available = True
    docx_available = True

    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        pdf_available = False

    try:
        from docx import Document  # noqa: F401
    except ImportError:
        docx_available = False

    return {
        "status": "healthy" if (is_available and pdf_available and docx_available) else "degraded",
        "llm_provider": llm.provider,
        "llm_model": llm.model,
        "llm_available": is_available,
        "pdf_parsing": pdf_available,
        "docx_parsing": docx_available,
        "demo_mode": settings.demo_mode,
        "max_file_size_mb": MAX_FILE_SIZE // 1024 // 1024,
        "allowed_types": list(ALLOWED_TYPES.values()),
    }
