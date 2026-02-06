"""A/B Testing service for proposal variants."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.proposal import (
    ProposalVariant,
    ABTest,
    ABTestStatus,
)
from backend.models.job import JobMatch

logger = logging.getLogger(__name__)


class ABTestService:
    """Service for managing A/B tests and proposal variants."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============= A/B Test Management =============

    async def create_ab_test(
        self,
        user_id: UUID,
        name: str,
        test_type: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        target_sample_size: int = 10,
    ) -> ABTest:
        """Create a new A/B test."""
        ab_test = ABTest(
            user_id=user_id,
            name=name,
            description=description,
            test_type=test_type,
            status=ABTestStatus.DRAFT.value,
            parameters=parameters or {},
            target_sample_size=target_sample_size,
        )
        self.db.add(ab_test)
        await self.db.commit()
        await self.db.refresh(ab_test)

        logger.info(f"Created A/B test '{name}' for user {user_id}")
        return ab_test

    async def get_ab_test(
        self,
        test_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[ABTest]:
        """Get an A/B test by ID."""
        query = select(ABTest).options(
            selectinload(ABTest.variants)
        ).where(ABTest.id == test_id)

        if user_id:
            query = query.where(ABTest.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_ab_tests(
        self,
        user_id: UUID,
        status: Optional[str] = None,
    ) -> List[ABTest]:
        """Get all A/B tests for a user."""
        query = select(ABTest).options(
            selectinload(ABTest.variants)
        ).where(ABTest.user_id == user_id).order_by(ABTest.created_at.desc())

        if status:
            query = query.where(ABTest.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def start_ab_test(self, test_id: UUID, user_id: UUID) -> ABTest:
        """Start an A/B test."""
        ab_test = await self.get_ab_test(test_id, user_id)
        if not ab_test:
            raise ValueError("A/B test not found")

        if ab_test.status != ABTestStatus.DRAFT.value:
            raise ValueError(f"Cannot start test with status '{ab_test.status}'")

        ab_test.status = ABTestStatus.ACTIVE.value
        ab_test.started_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(ab_test)

        logger.info(f"Started A/B test {test_id}")
        return ab_test

    async def pause_ab_test(self, test_id: UUID, user_id: UUID) -> ABTest:
        """Pause an active A/B test."""
        ab_test = await self.get_ab_test(test_id, user_id)
        if not ab_test:
            raise ValueError("A/B test not found")

        if ab_test.status != ABTestStatus.ACTIVE.value:
            raise ValueError("Can only pause active tests")

        ab_test.status = ABTestStatus.PAUSED.value
        await self.db.commit()
        await self.db.refresh(ab_test)

        logger.info(f"Paused A/B test {test_id}")
        return ab_test

    async def complete_ab_test(
        self,
        test_id: UUID,
        user_id: UUID,
    ) -> ABTest:
        """Complete an A/B test and calculate results."""
        ab_test = await self.get_ab_test(test_id, user_id)
        if not ab_test:
            raise ValueError("A/B test not found")

        # Calculate results
        metrics_a = ab_test.variant_a_metrics
        metrics_b = ab_test.variant_b_metrics

        # Determine winner based on response rate
        winner = None
        if metrics_a.get("sent", 0) > 0 and metrics_b.get("sent", 0) > 0:
            rate_a = metrics_a.get("response_rate", 0)
            rate_b = metrics_b.get("response_rate", 0)

            if rate_a > rate_b:
                winner = "A"
            elif rate_b > rate_a:
                winner = "B"
            # else: inconclusive

        ab_test.status = ABTestStatus.COMPLETED.value
        ab_test.ended_at = datetime.utcnow()
        ab_test.winner_variant = winner
        ab_test.results = {
            "variant_a": metrics_a,
            "variant_b": metrics_b,
            "winner": winner,
            "completed_at": datetime.utcnow().isoformat(),
        }

        await self.db.commit()
        await self.db.refresh(ab_test)

        logger.info(f"Completed A/B test {test_id}, winner: {winner}")
        return ab_test

    async def delete_ab_test(self, test_id: UUID, user_id: UUID) -> bool:
        """Delete an A/B test."""
        ab_test = await self.get_ab_test(test_id, user_id)
        if not ab_test:
            return False

        await self.db.delete(ab_test)
        await self.db.commit()

        logger.info(f"Deleted A/B test {test_id}")
        return True

    # ============= Variant Management =============

    async def create_variant(
        self,
        user_id: UUID,
        content: str,
        job_match_id: Optional[UUID] = None,
        ab_test_id: Optional[UUID] = None,
        variant_name: Optional[str] = None,
        variant_label: Optional[str] = None,  # "A" or "B"
        tone: Optional[str] = None,
        style: Optional[str] = None,
        length: Optional[str] = None,
        generation_method: Optional[str] = None,
        model_used: Optional[str] = None,
        keywords_used: Optional[List[str]] = None,
        ats_score: Optional[int] = None,
        is_control: bool = False,
    ) -> ProposalVariant:
        """Create a new proposal variant."""
        word_count = len(content.split())

        variant = ProposalVariant(
            user_id=user_id,
            job_match_id=job_match_id,
            ab_test_id=ab_test_id,
            content=content,
            variant_name=variant_name,
            variant_label=variant_label,
            tone=tone,
            style=style,
            length=length,
            generation_method=generation_method,
            model_used=model_used,
            word_count=word_count,
            keywords_used=keywords_used or [],
            ats_score=ats_score,
            is_control=is_control,
        )
        self.db.add(variant)
        await self.db.commit()
        await self.db.refresh(variant)

        # Update A/B test sample counts if applicable
        if ab_test_id and variant_label:
            await self._update_test_sample_counts(ab_test_id)

        logger.info(f"Created proposal variant for user {user_id}")
        return variant

    async def get_variant(
        self,
        variant_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[ProposalVariant]:
        """Get a variant by ID."""
        query = select(ProposalVariant).where(ProposalVariant.id == variant_id)

        if user_id:
            query = query.where(ProposalVariant.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_variants_for_job(
        self,
        job_match_id: UUID,
        user_id: UUID,
    ) -> List[ProposalVariant]:
        """Get all variants for a specific job match."""
        query = select(ProposalVariant).where(
            and_(
                ProposalVariant.job_match_id == job_match_id,
                ProposalVariant.user_id == user_id,
            )
        ).order_by(ProposalVariant.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_variants_for_test(
        self,
        ab_test_id: UUID,
        variant_label: Optional[str] = None,
    ) -> List[ProposalVariant]:
        """Get all variants in an A/B test."""
        query = select(ProposalVariant).where(
            ProposalVariant.ab_test_id == ab_test_id
        )

        if variant_label:
            query = query.where(ProposalVariant.variant_label == variant_label)

        query = query.order_by(ProposalVariant.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def select_variant(
        self,
        variant_id: UUID,
        user_id: UUID,
    ) -> ProposalVariant:
        """Mark a variant as selected (to be used/sent)."""
        variant = await self.get_variant(variant_id, user_id)
        if not variant:
            raise ValueError("Variant not found")

        # Unselect any other variants for this job match
        if variant.job_match_id:
            await self.db.execute(
                select(ProposalVariant).where(
                    and_(
                        ProposalVariant.job_match_id == variant.job_match_id,
                        ProposalVariant.id != variant_id,
                    )
                )
            )
            # Update using raw SQL for efficiency
            from sqlalchemy import update
            await self.db.execute(
                update(ProposalVariant)
                .where(
                    and_(
                        ProposalVariant.job_match_id == variant.job_match_id,
                        ProposalVariant.id != variant_id,
                    )
                )
                .values(is_selected=False)
            )

        variant.is_selected = True
        await self.db.commit()
        await self.db.refresh(variant)

        logger.info(f"Selected variant {variant_id}")
        return variant

    async def mark_variant_sent(
        self,
        variant_id: UUID,
        user_id: UUID,
    ) -> ProposalVariant:
        """Mark a variant as sent."""
        variant = await self.get_variant(variant_id, user_id)
        if not variant:
            raise ValueError("Variant not found")

        variant.was_sent = True
        variant.sent_at = datetime.utcnow()
        variant.is_selected = True

        await self.db.commit()
        await self.db.refresh(variant)

        logger.info(f"Marked variant {variant_id} as sent")
        return variant

    async def record_outcome(
        self,
        variant_id: UUID,
        user_id: UUID,
        outcome_type: str,  # "response", "interview", "offer"
    ) -> ProposalVariant:
        """Record an outcome for a variant."""
        variant = await self.get_variant(variant_id, user_id)
        if not variant:
            raise ValueError("Variant not found")

        now = datetime.utcnow()

        if outcome_type == "response":
            variant.got_response = True
            variant.response_at = now
        elif outcome_type == "interview":
            variant.got_interview = True
            variant.interview_at = now
        elif outcome_type == "offer":
            variant.got_offer = True
            variant.offer_at = now
        else:
            raise ValueError(f"Invalid outcome type: {outcome_type}")

        await self.db.commit()
        await self.db.refresh(variant)

        logger.info(f"Recorded {outcome_type} for variant {variant_id}")
        return variant

    async def delete_variant(
        self,
        variant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a variant."""
        variant = await self.get_variant(variant_id, user_id)
        if not variant:
            return False

        ab_test_id = variant.ab_test_id

        await self.db.delete(variant)
        await self.db.commit()

        # Update A/B test sample counts if applicable
        if ab_test_id:
            await self._update_test_sample_counts(ab_test_id)

        logger.info(f"Deleted variant {variant_id}")
        return True

    # ============= Analytics =============

    async def get_user_variant_stats(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Get aggregated variant statistics for a user."""
        # Total variants
        total_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                ProposalVariant.user_id == user_id
            )
        )
        total_variants = total_result.scalar() or 0

        # Sent variants
        sent_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.user_id == user_id,
                    ProposalVariant.was_sent == True,
                )
            )
        )
        sent_count = sent_result.scalar() or 0

        # Response rate
        response_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.user_id == user_id,
                    ProposalVariant.got_response == True,
                )
            )
        )
        response_count = response_result.scalar() or 0

        # Interview rate
        interview_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.user_id == user_id,
                    ProposalVariant.got_interview == True,
                )
            )
        )
        interview_count = interview_result.scalar() or 0

        # Offer rate
        offer_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.user_id == user_id,
                    ProposalVariant.got_offer == True,
                )
            )
        )
        offer_count = offer_result.scalar() or 0

        # Performance by tone
        tone_stats = await self._get_stats_by_field(user_id, "tone")
        style_stats = await self._get_stats_by_field(user_id, "style")

        return {
            "total_variants": total_variants,
            "sent_count": sent_count,
            "response_count": response_count,
            "interview_count": interview_count,
            "offer_count": offer_count,
            "response_rate": (response_count / sent_count * 100) if sent_count > 0 else 0,
            "interview_rate": (interview_count / sent_count * 100) if sent_count > 0 else 0,
            "offer_rate": (offer_count / sent_count * 100) if sent_count > 0 else 0,
            "by_tone": tone_stats,
            "by_style": style_stats,
        }

    async def _get_stats_by_field(
        self,
        user_id: UUID,
        field_name: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance stats grouped by a field (tone, style, etc.)."""
        field = getattr(ProposalVariant, field_name)

        result = await self.db.execute(
            select(
                field,
                func.count(ProposalVariant.id).label("total"),
                func.sum(
                    func.cast(ProposalVariant.was_sent, Integer)
                ).label("sent"),
                func.sum(
                    func.cast(ProposalVariant.got_response, Integer)
                ).label("responses"),
                func.sum(
                    func.cast(ProposalVariant.got_interview, Integer)
                ).label("interviews"),
                func.sum(
                    func.cast(ProposalVariant.got_offer, Integer)
                ).label("offers"),
            )
            .where(
                and_(
                    ProposalVariant.user_id == user_id,
                    field.isnot(None),
                )
            )
            .group_by(field)
        )

        stats = {}
        for row in result:
            value, total, sent, responses, interviews, offers = row
            sent = sent or 0
            responses = responses or 0
            interviews = interviews or 0
            offers = offers or 0

            stats[value] = {
                "total": total,
                "sent": sent,
                "responses": responses,
                "interviews": interviews,
                "offers": offers,
                "response_rate": (responses / sent * 100) if sent > 0 else 0,
                "interview_rate": (interviews / sent * 100) if sent > 0 else 0,
            }

        return stats

    async def _update_test_sample_counts(self, ab_test_id: UUID) -> None:
        """Update sample counts for an A/B test."""
        # Count variant A
        count_a_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.ab_test_id == ab_test_id,
                    ProposalVariant.variant_label == "A",
                )
            )
        )
        count_a = count_a_result.scalar() or 0

        # Count variant B
        count_b_result = await self.db.execute(
            select(func.count(ProposalVariant.id)).where(
                and_(
                    ProposalVariant.ab_test_id == ab_test_id,
                    ProposalVariant.variant_label == "B",
                )
            )
        )
        count_b = count_b_result.scalar() or 0

        # Update the test
        from sqlalchemy import update
        await self.db.execute(
            update(ABTest)
            .where(ABTest.id == ab_test_id)
            .values(
                current_sample_size_a=count_a,
                current_sample_size_b=count_b,
            )
        )


# Singleton-style accessor
def get_ab_test_service(db: AsyncSession) -> ABTestService:
    """Get an ABTestService instance."""
    return ABTestService(db)
