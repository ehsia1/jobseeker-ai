"""Client Risk Assessment Service - Analyzes job postings for potential red flags."""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.config import settings
from backend.models.job import Job
from backend.models.client_risk import (
    ClientRiskAssessment,
    CompanyRiskProfile,
    RiskLevel,
    RiskCategory,
)

logger = logging.getLogger(__name__)


# Red flag patterns for rule-based detection
RED_FLAG_PATTERNS = {
    RiskCategory.PAYMENT: [
        (r"unpaid|no pay|for exposure|for experience|volunteer", "Unpaid or experience-only compensation", "high", 0.9),
        (r"payment upon success|pay after|equity only", "Delayed or contingent payment", "high", 0.85),
        (r"negotiate.*rate|flexible.*budget", "Vague payment terms", "low", 0.6),
        (r"low budget|tight budget|limited budget", "Limited budget mentioned", "medium", 0.7),
    ],
    RiskCategory.EXPECTATIONS: [
        (r"asap|urgent|immediately|yesterday", "Unrealistic timeline pressure", "medium", 0.75),
        (r"guru|rockstar|ninja|wizard|unicorn", "Unrealistic skill expectations", "medium", 0.7),
        (r"everything|full.?stack.*expert|all.?in.?one", "Expects too many skills", "medium", 0.7),
        (r"24.?7|always available|any time", "Excessive availability expectations", "high", 0.85),
    ],
    RiskCategory.SCOPE: [
        (r"simple|easy|quick|just need", "Minimizing complexity", "low", 0.65),
        (r"ongoing|long.?term|unlimited", "Open-ended scope", "low", 0.5),
        (r"and more|etc\.?$|various tasks", "Vague or expandable scope", "medium", 0.7),
        (r"change.*requirements|flexible.*requirements", "Unstable requirements", "medium", 0.75),
    ],
    RiskCategory.COMMUNICATION: [
        (r"no questions|just do|don't ask", "Discourages communication", "high", 0.85),
        (r"test.*project|prove.*yourself|unpaid.*trial", "Unpaid trial work requested", "high", 0.9),
    ],
    RiskCategory.LEGAL: [
        (r"copyright|intellectual property|ip transfer", "IP concerns", "low", 0.5),  # Not necessarily bad, just note
        (r"nda|confidential|secret", "Confidentiality requirements", "low", 0.4),  # Normal, just note
        (r"no contract|without contract", "No contract mentioned", "high", 0.85),
    ],
    RiskCategory.COMPANY: [
        (r"new company|startup|just started", "New/unestablished company", "low", 0.5),
        (r"stealth|confidential client|anonymous", "Hidden company identity", "medium", 0.7),
    ],
}

# Green flag patterns
GREEN_FLAG_PATTERNS = [
    (r"\$\d+.*(?:per|\/)\s*(?:hour|hr)", "Clear hourly rate specified", RiskCategory.PAYMENT, 0.8),
    (r"milestone|escrow|upfront", "Secure payment terms", RiskCategory.PAYMENT, 0.85),
    (r"verified|established|years in business", "Established company", RiskCategory.COMPANY, 0.7),
    (r"detailed.*requirements|specifications|scope", "Clear requirements", RiskCategory.SCOPE, 0.75),
    (r"contract|agreement|terms", "Formal agreement mentioned", RiskCategory.LEGAL, 0.7),
    (r"review|feedback|communication", "Good communication practices", RiskCategory.COMMUNICATION, 0.6),
]


class ClientRiskService:
    """Service for analyzing client/job risk."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = self._init_llm()

    def _init_llm(self):
        """Initialize LLM for advanced analysis."""
        provider = settings.llm_provider

        if provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.3,  # Lower temperature for more consistent analysis
                    api_key=settings.openai_api_key
                )
            except ImportError:
                logger.warning("langchain-openai not installed")
                return None

        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=0.3,
                    api_key=settings.anthropic_api_key
                )
            except ImportError:
                logger.warning("langchain-anthropic not installed")
                return None

        return None

    async def analyze_job(
        self,
        job_id: UUID,
        force_refresh: bool = False
    ) -> ClientRiskAssessment:
        """Analyze a job posting for client risk factors."""

        # Check for existing non-expired assessment
        if not force_refresh:
            existing = await self._get_existing_assessment(job_id)
            if existing and not existing.is_expired:
                return existing

        # Fetch the job
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Run analysis
        red_flags, green_flags = self._analyze_patterns(job)
        risk_breakdown = self._calculate_breakdown(red_flags)

        # Get LLM analysis if available
        llm_analysis = None
        if self.llm:
            llm_analysis = await self._llm_analysis(job)
            if llm_analysis:
                # Merge LLM findings
                red_flags.extend(llm_analysis.get("red_flags", []))
                green_flags.extend(llm_analysis.get("green_flags", []))
                # Recalculate breakdown with LLM findings
                risk_breakdown = self._calculate_breakdown(red_flags)

        # Calculate overall score
        risk_score = self._calculate_overall_score(risk_breakdown, len(green_flags))
        risk_level = ClientRiskAssessment.calculate_risk_level(risk_score)

        # Generate summary and recommendations
        summary = self._generate_summary(job, risk_score, red_flags, green_flags)
        recommendations = self._generate_recommendations(red_flags, risk_level)

        # Create or update assessment
        assessment = await self._save_assessment(
            job_id=job_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_breakdown=risk_breakdown,
            red_flags=red_flags,
            green_flags=green_flags,
            summary=summary,
            recommendations=recommendations,
            company_name=job.company,
            analysis_method="hybrid" if self.llm else "rules",
            model_used=getattr(self.llm, "model_name", None) if self.llm else None,
        )

        # Update company risk profile
        if job.company:
            await self._update_company_profile(job.company)

        return assessment

    def _analyze_patterns(self, job: Job) -> Tuple[List[Dict], List[Dict]]:
        """Analyze job text for red and green flag patterns."""
        red_flags = []
        green_flags = []

        # Combine all text for analysis
        text = " ".join(filter(None, [
            job.title,
            job.description,
            job.company or "",
            " ".join(job.requirements) if job.requirements else "",
        ])).lower()

        # Check red flag patterns
        for category, patterns in RED_FLAG_PATTERNS.items():
            for pattern, description, severity, confidence in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    red_flags.append({
                        "category": category.value,
                        "flag": description,
                        "severity": severity,
                        "confidence": confidence,
                        "source": "pattern"
                    })

        # Check green flag patterns
        for pattern, description, category, confidence in GREEN_FLAG_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                green_flags.append({
                    "category": category.value,
                    "flag": description,
                    "confidence": confidence,
                    "source": "pattern"
                })

        # Check job-specific fields
        if job.rate_min and job.rate_max:
            green_flags.append({
                "category": RiskCategory.PAYMENT.value,
                "flag": "Clear budget range provided",
                "confidence": 0.9,
                "source": "field"
            })
        elif not job.rate_min and not job.rate_max:
            red_flags.append({
                "category": RiskCategory.PAYMENT.value,
                "flag": "No budget information provided",
                "severity": "medium",
                "confidence": 0.8,
                "source": "field"
            })

        return red_flags, green_flags

    def _calculate_breakdown(self, red_flags: List[Dict]) -> Dict[str, Dict]:
        """Calculate risk breakdown by category."""
        breakdown = {}
        severity_weights = {"low": 10, "medium": 25, "high": 50, "critical": 100}

        for flag in red_flags:
            category = flag.get("category", "unknown")
            if category not in breakdown:
                breakdown[category] = {"score": 0, "factors": []}

            severity = flag.get("severity", "low")
            confidence = flag.get("confidence", 0.5)
            weight = severity_weights.get(severity, 10)

            # Add weighted score
            breakdown[category]["score"] += int(weight * confidence)
            breakdown[category]["factors"].append(flag["flag"])

        # Cap category scores at 100
        for category in breakdown:
            breakdown[category]["score"] = min(100, breakdown[category]["score"])

        return breakdown

    def _calculate_overall_score(
        self,
        breakdown: Dict[str, Dict],
        green_flag_count: int
    ) -> int:
        """Calculate overall risk score from breakdown."""
        if not breakdown:
            return 0

        # Weight categories
        category_weights = {
            RiskCategory.PAYMENT.value: 0.25,
            RiskCategory.EXPECTATIONS.value: 0.20,
            RiskCategory.SCOPE.value: 0.15,
            RiskCategory.COMMUNICATION.value: 0.15,
            RiskCategory.COMPANY.value: 0.10,
            RiskCategory.LEGAL.value: 0.10,
            RiskCategory.REPUTATION.value: 0.05,
        }

        weighted_sum = 0
        total_weight = 0

        for category, data in breakdown.items():
            weight = category_weights.get(category, 0.1)
            weighted_sum += data["score"] * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        base_score = int(weighted_sum / total_weight)

        # Reduce score for green flags (each green flag reduces by ~5 points)
        green_flag_reduction = min(25, green_flag_count * 5)
        final_score = max(0, base_score - green_flag_reduction)

        return min(100, final_score)

    async def _llm_analysis(self, job: Job) -> Optional[Dict]:
        """Use LLM for advanced risk analysis."""
        if not self.llm:
            return None

        try:
            prompt = f"""Analyze this job posting for potential red flags and risks.

Job Title: {job.title}
Company: {job.company or "Not specified"}
Description: {job.description[:2000] if job.description else "No description"}
Requirements: {', '.join(job.requirements[:10]) if job.requirements else "None listed"}
Rate: {job.rate_range_text}
Location: {job.location or "Not specified"}
Remote: {"Yes" if job.remote else "No"}

Identify:
1. Red flags (concerning signals) - each with category (payment/expectations/scope/communication/company/legal), severity (low/medium/high/critical), and confidence (0-1)
2. Green flags (positive signals) - each with category and confidence

Respond in JSON format:
{{
    "red_flags": [
        {{"category": "payment", "flag": "description", "severity": "medium", "confidence": 0.8}}
    ],
    "green_flags": [
        {{"category": "company", "flag": "description", "confidence": 0.9}}
    ],
    "overall_assessment": "brief assessment"
}}

Only include genuinely concerning red flags, not normal job posting elements."""

            response = await self.llm.ainvoke(prompt)
            content = response.content

            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis = json.loads(json_match.group())
                # Add source marker
                for flag in analysis.get("red_flags", []):
                    flag["source"] = "llm"
                for flag in analysis.get("green_flags", []):
                    flag["source"] = "llm"
                return analysis

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        return None

    def _generate_summary(
        self,
        job: Job,
        risk_score: int,
        red_flags: List[Dict],
        green_flags: List[Dict]
    ) -> str:
        """Generate a human-readable risk summary."""
        risk_level = ClientRiskAssessment.calculate_risk_level(risk_score)

        if risk_level == RiskLevel.CRITICAL.value:
            prefix = "High caution advised."
        elif risk_level == RiskLevel.HIGH.value:
            prefix = "Several concerns identified."
        elif risk_level == RiskLevel.MEDIUM.value:
            prefix = "Some areas to clarify."
        else:
            prefix = "Looks promising overall."

        parts = [prefix]

        if red_flags:
            top_concerns = [f["flag"] for f in red_flags[:3]]
            parts.append(f"Key concerns: {'; '.join(top_concerns)}.")

        if green_flags:
            top_positives = [f["flag"] for f in green_flags[:2]]
            parts.append(f"Positives: {'; '.join(top_positives)}.")

        return " ".join(parts)

    def _generate_recommendations(
        self,
        red_flags: List[Dict],
        risk_level: str
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []

        # Category-specific recommendations
        categories_found = set(f.get("category") for f in red_flags)

        if RiskCategory.PAYMENT.value in categories_found:
            recommendations.append("Clarify payment terms, amounts, and schedule before starting")
            recommendations.append("Consider using escrow or milestone payments for protection")

        if RiskCategory.EXPECTATIONS.value in categories_found:
            recommendations.append("Discuss realistic timelines and expectations upfront")
            recommendations.append("Get specific deliverables agreed in writing")

        if RiskCategory.SCOPE.value in categories_found:
            recommendations.append("Request a detailed scope document or specification")
            recommendations.append("Agree on a change request process for scope modifications")

        if RiskCategory.COMMUNICATION.value in categories_found:
            recommendations.append("Establish clear communication channels and expectations")

        if RiskCategory.COMPANY.value in categories_found:
            recommendations.append("Research the company before proceeding")
            recommendations.append("Ask for references from previous contractors/employees")

        if RiskCategory.LEGAL.value in categories_found:
            recommendations.append("Ensure a proper contract is in place before starting")

        # General recommendations based on risk level
        if risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
            recommendations.append("Consider requesting an initial paid discovery phase")
            recommendations.append("Document all communications and agreements")

        return recommendations[:5]  # Limit to top 5

    async def _get_existing_assessment(self, job_id: UUID) -> Optional[ClientRiskAssessment]:
        """Get existing assessment if available."""
        result = await self.db.execute(
            select(ClientRiskAssessment).where(
                ClientRiskAssessment.job_id == job_id
            )
        )
        return result.scalar_one_or_none()

    async def _save_assessment(
        self,
        job_id: UUID,
        risk_score: int,
        risk_level: str,
        risk_breakdown: Dict,
        red_flags: List[Dict],
        green_flags: List[Dict],
        summary: str,
        recommendations: List[str],
        company_name: Optional[str],
        analysis_method: str,
        model_used: Optional[str],
    ) -> ClientRiskAssessment:
        """Save or update risk assessment."""
        existing = await self._get_existing_assessment(job_id)

        if existing:
            existing.risk_score = risk_score
            existing.risk_level = risk_level
            existing.risk_breakdown = risk_breakdown
            existing.red_flags = red_flags
            existing.green_flags = green_flags
            existing.summary = summary
            existing.recommendations = recommendations
            existing.company_name = company_name
            existing.analysis_method = analysis_method
            existing.model_used = model_used
            existing.analyzed_at = datetime.now(timezone.utc)
            existing.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        assessment = ClientRiskAssessment(
            job_id=job_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_breakdown=risk_breakdown,
            red_flags=red_flags,
            green_flags=green_flags,
            summary=summary,
            recommendations=recommendations,
            company_name=company_name,
            analysis_method=analysis_method,
            model_used=model_used,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment

    async def _update_company_profile(self, company_name: str) -> None:
        """Update aggregated company risk profile."""
        if not company_name:
            return

        normalized = CompanyRiskProfile.normalize_company_name(company_name)

        # Get or create profile
        result = await self.db.execute(
            select(CompanyRiskProfile).where(
                CompanyRiskProfile.company_name_normalized == normalized
            )
        )
        profile = result.scalar_one_or_none()

        # Get all assessments for this company
        assessments_result = await self.db.execute(
            select(ClientRiskAssessment).where(
                func.lower(ClientRiskAssessment.company_name) == normalized
            )
        )
        assessments = assessments_result.scalars().all()

        if not assessments:
            return

        # Calculate aggregates
        avg_score = sum(a.risk_score for a in assessments) / len(assessments)
        total_jobs = len(assessments)

        # Aggregate red flags
        flag_counts: Dict[str, int] = {}
        for assessment in assessments:
            for flag in (assessment.red_flags or []):
                flag_text = flag.get("flag", "Unknown")
                flag_counts[flag_text] = flag_counts.get(flag_text, 0) + 1

        common_flags = [
            {"flag": flag, "count": count, "percentage": round(count / total_jobs * 100)}
            for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1])[:5]
        ]

        if profile:
            profile.average_risk_score = int(avg_score)
            profile.risk_level = ClientRiskAssessment.calculate_risk_level(int(avg_score))
            profile.total_jobs_analyzed = total_jobs
            profile.common_red_flags = common_flags
        else:
            profile = CompanyRiskProfile(
                company_name=company_name,
                company_name_normalized=normalized,
                average_risk_score=int(avg_score),
                risk_level=ClientRiskAssessment.calculate_risk_level(int(avg_score)),
                total_jobs_analyzed=total_jobs,
                common_red_flags=common_flags,
            )
            self.db.add(profile)

        await self.db.commit()

    async def get_job_risk(self, job_id: UUID) -> Optional[ClientRiskAssessment]:
        """Get risk assessment for a job."""
        return await self._get_existing_assessment(job_id)

    async def get_company_profile(self, company_name: str) -> Optional[CompanyRiskProfile]:
        """Get company risk profile."""
        normalized = CompanyRiskProfile.normalize_company_name(company_name)
        result = await self.db.execute(
            select(CompanyRiskProfile).where(
                CompanyRiskProfile.company_name_normalized == normalized
            )
        )
        return result.scalar_one_or_none()

    async def batch_analyze(self, job_ids: List[UUID]) -> List[ClientRiskAssessment]:
        """Analyze multiple jobs in batch."""
        results = []
        for job_id in job_ids:
            try:
                assessment = await self.analyze_job(job_id)
                results.append(assessment)
            except Exception as e:
                logger.error(f"Failed to analyze job {job_id}: {e}")
        return results


def get_client_risk_service(db: AsyncSession) -> ClientRiskService:
    """Get an instance of the client risk service."""
    return ClientRiskService(db)
