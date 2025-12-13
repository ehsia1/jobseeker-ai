"""Application Tracker Agent - AI-powered application portfolio intelligence."""

import logging
from datetime import datetime, timedelta
from typing import TypedDict, Optional, Any
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.job import JobMatch, Job
from backend.models.application import (
    ApplicationStatus,
    ApplicationTimeline,
    ApplicationReminder,
    ReminderType,
)
from backend.services.application_service import ApplicationTrackingService

logger = logging.getLogger(__name__)


class BriefingType(str, Enum):
    """Type of briefing to generate."""
    DAILY = "daily"
    WEEKLY = "weekly"
    FULL = "full"


class ApplicationTrackerState(TypedDict):
    """State for the Application Tracker Agent workflow."""
    # Input
    user_id: str
    briefing_type: str  # daily, weekly, full

    # Database session
    db: Any

    # Loaded data
    applications: list[dict]
    reminders: list[dict]
    timeline_events: list[dict]
    stats: dict

    # Analysis results
    portfolio_analysis: dict
    stale_applications: list[dict]
    recommendations: list[dict]
    action_items: list[dict]

    # Output
    briefing: str
    error: Optional[str]


class ApplicationTrackerAgent:
    """
    AI-powered Application Tracker Agent.

    Provides intelligent analysis of job application portfolio including:
    - Portfolio health analysis
    - Stale application detection
    - Smart follow-up recommendations
    - Automated action item generation
    - Daily/weekly briefings
    """

    # Thresholds for stale application detection (in days)
    STALE_THRESHOLDS = {
        ApplicationStatus.APPLIED: 7,      # No response after 7 days
        ApplicationStatus.SCREENING: 5,    # Screening taking too long
        ApplicationStatus.INTERVIEWING: 3,  # Interview process stalled
        ApplicationStatus.OFFER_RECEIVED: 2,  # Need to respond to offer
    }

    def __init__(self, db: AsyncSession):
        """Initialize the Application Tracker Agent."""
        self.db = db
        self.llm = self._init_llm()
        self.workflow = self._build_workflow()
        self.tracking_service = ApplicationTrackingService(db)

    def _init_llm(self) -> ChatOpenAI:
        """Initialize the LLM for analysis and recommendations."""
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key,
        )

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for application tracking."""
        workflow = StateGraph(ApplicationTrackerState)

        # Add nodes
        workflow.add_node("load_applications", self._load_applications)
        workflow.add_node("analyze_portfolio", self._analyze_portfolio)
        workflow.add_node("detect_stale", self._detect_stale_applications)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("create_briefing", self._create_briefing)

        # Define edges
        workflow.set_entry_point("load_applications")
        workflow.add_edge("load_applications", "analyze_portfolio")
        workflow.add_edge("analyze_portfolio", "detect_stale")
        workflow.add_edge("detect_stale", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "create_briefing")
        workflow.add_edge("create_briefing", END)

        return workflow.compile()

    async def _load_applications(self, state: ApplicationTrackerState) -> dict:
        """Load user's applications with timelines and reminders."""
        try:
            user_id = state["user_id"]

            # Load all job matches (applications) for the user
            query = (
                select(JobMatch)
                .options(
                    selectinload(JobMatch.job),
                    selectinload(JobMatch.timeline_entries),
                    selectinload(JobMatch.reminders),
                )
                .where(JobMatch.user_id == user_id)
                .order_by(JobMatch.updated_at.desc())
            )

            result = await self.db.execute(query)
            matches = result.scalars().all()

            # Convert to dictionaries for state
            applications = []
            all_reminders = []
            all_timeline_events = []

            for match in matches:
                app_data = {
                    "id": str(match.id),
                    "job_id": str(match.job_id),
                    "job_title": match.job.title if match.job else "Unknown",
                    "company": match.job.company if match.job else "Unknown",
                    "status": match.status.value if match.status else "new",
                    "match_score": match.score,
                    "created_at": match.created_at.isoformat() if match.created_at else None,
                    "updated_at": match.updated_at.isoformat() if match.updated_at else None,
                    "days_since_update": (datetime.utcnow() - match.updated_at).days if match.updated_at else 0,
                }
                applications.append(app_data)

                # Collect timeline events
                for event in match.timeline_entries:
                    all_timeline_events.append({
                        "application_id": str(match.id),
                        "from_status": event.from_status.value if event.from_status else None,
                        "to_status": event.to_status.value if event.to_status else None,
                        "notes": event.notes,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    })

                # Collect reminders
                for reminder in match.reminders:
                    if not reminder.is_dismissed:
                        all_reminders.append({
                            "id": str(reminder.id),
                            "application_id": str(match.id),
                            "job_title": app_data["job_title"],
                            "company": app_data["company"],
                            "type": reminder.reminder_type.value if reminder.reminder_type else "custom",
                            "title": reminder.title,
                            "description": reminder.description,
                            "scheduled_for": reminder.scheduled_for.isoformat() if reminder.scheduled_for else None,
                            "is_completed": reminder.is_completed,
                            "is_overdue": reminder.scheduled_for < datetime.utcnow() if reminder.scheduled_for else False,
                        })

            # Get overall stats
            stats = await self.tracking_service.get_application_stats(user_id)

            # Calculate response rate: (interviews + offers) / total
            total = stats.total_applications or 1  # Avoid division by zero
            response_rate = ((stats.interviews_scheduled + stats.offers_received) / total) * 100

            stats_dict = {
                "total_applications": stats.total_applications,
                "active_applications": stats.active_applications,
                "interviews_scheduled": stats.interviews_scheduled,
                "offers_received": stats.offers_received,
                "response_rate": round(response_rate, 1),
                "by_status": stats.applications_by_status,
                "recent_activity_count": stats.recent_activity_count,
            }

            return {
                "applications": applications,
                "reminders": all_reminders,
                "timeline_events": all_timeline_events,
                "stats": stats_dict,
            }

        except Exception as e:
            logger.error(f"Error loading applications: {e}")
            return {"error": str(e)}

    async def _analyze_portfolio(self, state: ApplicationTrackerState) -> dict:
        """Analyze the health and distribution of the application portfolio."""
        if state.get("error"):
            return {}

        applications = state["applications"]
        stats = state["stats"]

        if not applications:
            return {
                "portfolio_analysis": {
                    "health_score": 0,
                    "total_count": 0,
                    "insights": ["No applications found. Start applying to jobs!"],
                    "status_distribution": {},
                    "activity_trend": "none",
                }
            }

        # Calculate portfolio health metrics
        total = len(applications)
        active_statuses = [
            ApplicationStatus.APPLIED.value,
            ApplicationStatus.SCREENING.value,
            ApplicationStatus.INTERVIEWING.value,
            ApplicationStatus.OFFER_RECEIVED.value,
        ]

        active_count = sum(1 for app in applications if app["status"] in active_statuses)
        interview_count = sum(1 for app in applications if app["status"] == ApplicationStatus.INTERVIEWING.value)
        offer_count = sum(1 for app in applications if app["status"] == ApplicationStatus.OFFER_RECEIVED.value)
        rejected_count = sum(1 for app in applications if app["status"] == ApplicationStatus.REJECTED.value)

        # Calculate health score (0-100)
        health_score = 50  # Base score

        # Bonus for active applications
        if active_count > 0:
            health_score += min(20, active_count * 4)

        # Bonus for interviews
        if interview_count > 0:
            health_score += min(15, interview_count * 5)

        # Bonus for offers
        if offer_count > 0:
            health_score += 15

        # Penalty for high rejection rate
        if total > 5:
            rejection_rate = rejected_count / total
            if rejection_rate > 0.7:
                health_score -= 20
            elif rejection_rate > 0.5:
                health_score -= 10

        health_score = max(0, min(100, health_score))

        # Determine activity trend
        recent_apps = [app for app in applications if app.get("days_since_update", 999) <= 7]
        if len(recent_apps) >= 5:
            activity_trend = "high"
        elif len(recent_apps) >= 2:
            activity_trend = "moderate"
        elif len(recent_apps) >= 1:
            activity_trend = "low"
        else:
            activity_trend = "stagnant"

        # Generate insights
        insights = []

        if active_count == 0:
            insights.append("You have no active applications. Consider applying to more positions.")
        elif active_count < 5:
            insights.append(f"You have {active_count} active application(s). Aim for 10-15 active applications for best results.")

        if interview_count > 0:
            insights.append(f"Great progress! You have {interview_count} application(s) in the interview stage.")

        if offer_count > 0:
            insights.append(f"Congratulations! You have {offer_count} offer(s) to consider.")

        response_rate = stats.get("response_rate", 0)
        if response_rate < 20 and total >= 10:
            insights.append("Your response rate is below average. Consider tailoring your resume for each application.")
        elif response_rate >= 40:
            insights.append("Your response rate is excellent! Keep up the targeted applications.")

        return {
            "portfolio_analysis": {
                "health_score": health_score,
                "total_count": total,
                "active_count": active_count,
                "interview_count": interview_count,
                "offer_count": offer_count,
                "insights": insights,
                "status_distribution": stats.get("by_status", {}),
                "activity_trend": activity_trend,
                "response_rate": response_rate,
            }
        }

    async def _detect_stale_applications(self, state: ApplicationTrackerState) -> dict:
        """Detect applications that need attention based on time thresholds."""
        if state.get("error"):
            return {}

        applications = state["applications"]
        stale_applications = []

        for app in applications:
            status = app["status"]
            days_since_update = app.get("days_since_update", 0)

            # Check against thresholds
            threshold = self.STALE_THRESHOLDS.get(ApplicationStatus(status))

            if threshold and days_since_update >= threshold:
                urgency = "high" if days_since_update >= threshold * 2 else "medium"

                stale_applications.append({
                    "application_id": app["id"],
                    "job_title": app["job_title"],
                    "company": app["company"],
                    "status": status,
                    "days_stale": days_since_update,
                    "threshold": threshold,
                    "urgency": urgency,
                    "reason": self._get_stale_reason(status, days_since_update),
                })

        # Sort by urgency and days stale
        stale_applications.sort(
            key=lambda x: (0 if x["urgency"] == "high" else 1, -x["days_stale"])
        )

        return {"stale_applications": stale_applications}

    def _get_stale_reason(self, status: str, days: int) -> str:
        """Get human-readable reason for stale application."""
        reasons = {
            ApplicationStatus.APPLIED.value: f"No response received after {days} days. Consider following up.",
            ApplicationStatus.SCREENING.value: f"Screening process has been ongoing for {days} days. Check for updates.",
            ApplicationStatus.INTERVIEWING.value: f"Interview process stalled for {days} days. Follow up on next steps.",
            ApplicationStatus.OFFER_RECEIVED.value: f"Offer pending response for {days} days. Don't keep them waiting!",
        }
        return reasons.get(status, f"No activity for {days} days.")

    async def _generate_recommendations(self, state: ApplicationTrackerState) -> dict:
        """Generate smart recommendations and action items."""
        if state.get("error"):
            return {}

        applications = state["applications"]
        stale_applications = state.get("stale_applications", [])
        reminders = state["reminders"]
        portfolio_analysis = state.get("portfolio_analysis", {})

        recommendations = []
        action_items = []

        # Handle stale applications
        for stale in stale_applications[:5]:  # Top 5 most urgent
            action_items.append({
                "type": "follow_up",
                "priority": "high" if stale["urgency"] == "high" else "medium",
                "title": f"Follow up on {stale['job_title']} at {stale['company']}",
                "description": stale["reason"],
                "application_id": stale["application_id"],
            })

        # Handle overdue reminders
        overdue_reminders = [r for r in reminders if r.get("is_overdue") and not r.get("is_completed")]
        for reminder in overdue_reminders[:3]:
            action_items.append({
                "type": "reminder",
                "priority": "high",
                "title": reminder["title"],
                "description": f"Overdue reminder for {reminder['job_title']} at {reminder['company']}",
                "reminder_id": reminder["id"],
                "application_id": reminder["application_id"],
            })

        # Handle upcoming reminders (next 24 hours)
        upcoming = [
            r for r in reminders
            if not r.get("is_overdue") and not r.get("is_completed") and r.get("scheduled_for")
        ]
        for reminder in upcoming[:3]:
            scheduled = datetime.fromisoformat(reminder["scheduled_for"])
            if scheduled <= datetime.utcnow() + timedelta(hours=24):
                action_items.append({
                    "type": "upcoming",
                    "priority": "medium",
                    "title": reminder["title"],
                    "description": f"Coming up: {reminder['job_title']} at {reminder['company']}",
                    "reminder_id": reminder["id"],
                    "application_id": reminder["application_id"],
                })

        # Generate strategic recommendations based on portfolio analysis
        health_score = portfolio_analysis.get("health_score", 50)
        active_count = portfolio_analysis.get("active_count", 0)
        activity_trend = portfolio_analysis.get("activity_trend", "moderate")

        if active_count < 5:
            recommendations.append({
                "type": "strategy",
                "title": "Increase Application Volume",
                "description": "You have fewer than 5 active applications. Aim to maintain 10-15 active applications for optimal job search momentum.",
                "priority": "high",
            })

        if activity_trend in ["low", "stagnant"]:
            recommendations.append({
                "type": "strategy",
                "title": "Maintain Consistent Activity",
                "description": "Your application activity has slowed down. Try to apply to 3-5 new positions per week.",
                "priority": "medium",
            })

        if len(stale_applications) > 3:
            recommendations.append({
                "type": "strategy",
                "title": "Clear Application Backlog",
                "description": f"You have {len(stale_applications)} applications needing attention. Dedicate time to follow up or close out stale applications.",
                "priority": "high",
            })

        # Interview prep recommendation
        interviewing_apps = [a for a in applications if a["status"] == ApplicationStatus.INTERVIEWING.value]
        if interviewing_apps:
            recommendations.append({
                "type": "preparation",
                "title": "Prepare for Interviews",
                "description": f"You have {len(interviewing_apps)} active interview process(es). Make sure you're prepared with company research and practice questions.",
                "priority": "high",
            })

        return {
            "recommendations": recommendations,
            "action_items": action_items,
        }

    async def _create_briefing(self, state: ApplicationTrackerState) -> dict:
        """Create a natural language briefing using the LLM."""
        if state.get("error"):
            return {"briefing": f"Error generating briefing: {state['error']}"}

        briefing_type = state.get("briefing_type", "daily")
        portfolio_analysis = state.get("portfolio_analysis", {})
        stale_applications = state.get("stale_applications", [])
        recommendations = state.get("recommendations", [])
        action_items = state.get("action_items", [])
        stats = state.get("stats", {})

        # Prepare context for LLM
        context = {
            "briefing_type": briefing_type,
            "date": datetime.utcnow().strftime("%B %d, %Y"),
            "portfolio": {
                "health_score": portfolio_analysis.get("health_score", 0),
                "total_applications": portfolio_analysis.get("total_count", 0),
                "active_applications": portfolio_analysis.get("active_count", 0),
                "interviews_in_progress": portfolio_analysis.get("interview_count", 0),
                "offers_pending": portfolio_analysis.get("offer_count", 0),
                "response_rate": portfolio_analysis.get("response_rate", 0),
                "activity_trend": portfolio_analysis.get("activity_trend", "moderate"),
            },
            "attention_needed": len(stale_applications),
            "top_stale": stale_applications[:3],
            "recommendations": recommendations[:3],
            "action_items": action_items[:5],
            "insights": portfolio_analysis.get("insights", []),
        }

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful job search assistant providing application portfolio briefings.
Generate a concise, actionable briefing based on the provided data. Be encouraging but realistic.
Keep the tone professional yet supportive. Focus on the most important items.

For daily briefings: Focus on immediate action items and urgent matters.
For weekly briefings: Include progress summary and strategic recommendations.
For full briefings: Provide comprehensive analysis with all details."""),
            ("human", """Generate a {briefing_type} briefing for {date}.

Portfolio Overview:
- Health Score: {health_score}/100
- Total Applications: {total_apps}
- Active Applications: {active_apps}
- Interviews in Progress: {interviews}
- Pending Offers: {offers}
- Response Rate: {response_rate}%
- Activity Trend: {activity_trend}

Applications Needing Attention: {attention_count}
{stale_details}

Key Insights:
{insights}

Recommendations:
{recommendations}

Action Items:
{action_items}

Generate a well-structured, personalized briefing.""")
        ])

        # Format the details
        stale_details = "\n".join([
            f"- {s['job_title']} at {s['company']}: {s['reason']}"
            for s in context["top_stale"]
        ]) if context["top_stale"] else "None currently."

        insights_text = "\n".join([f"- {i}" for i in context["insights"]]) if context["insights"] else "No specific insights."

        recommendations_text = "\n".join([
            f"- {r['title']}: {r['description']}"
            for r in context["recommendations"]
        ]) if context["recommendations"] else "No recommendations at this time."

        action_items_text = "\n".join([
            f"- [{a['priority'].upper()}] {a['title']}"
            for a in context["action_items"]
        ]) if context["action_items"] else "No immediate action items."

        try:
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    briefing_type=briefing_type,
                    date=context["date"],
                    health_score=context["portfolio"]["health_score"],
                    total_apps=context["portfolio"]["total_applications"],
                    active_apps=context["portfolio"]["active_applications"],
                    interviews=context["portfolio"]["interviews_in_progress"],
                    offers=context["portfolio"]["offers_pending"],
                    response_rate=context["portfolio"]["response_rate"],
                    activity_trend=context["portfolio"]["activity_trend"],
                    attention_count=context["attention_needed"],
                    stale_details=stale_details,
                    insights=insights_text,
                    recommendations=recommendations_text,
                    action_items=action_items_text,
                )
            )

            return {"briefing": response.content}

        except Exception as e:
            logger.error(f"Error generating briefing with LLM: {e}")
            # Fallback to simple briefing
            return {
                "briefing": self._generate_fallback_briefing(context)
            }

    def _generate_fallback_briefing(self, context: dict) -> str:
        """Generate a simple briefing without LLM."""
        portfolio = context["portfolio"]
        briefing_type = context["briefing_type"].title()

        lines = [
            f"📊 {briefing_type} Application Briefing - {context['date']}",
            "",
            f"Portfolio Health: {portfolio['health_score']}/100",
            f"Active Applications: {portfolio['active_applications']} of {portfolio['total_applications']} total",
            f"Interviews: {portfolio['interviews_in_progress']} | Offers: {portfolio['offers_pending']}",
            "",
        ]

        if context["attention_needed"] > 0:
            lines.append(f"⚠️ {context['attention_needed']} application(s) need your attention")

        if context["action_items"]:
            lines.append("")
            lines.append("📋 Action Items:")
            for item in context["action_items"][:3]:
                lines.append(f"  • {item['title']}")

        if context["insights"]:
            lines.append("")
            lines.append("💡 Insights:")
            for insight in context["insights"][:2]:
                lines.append(f"  • {insight}")

        return "\n".join(lines)

    async def run(
        self,
        user_id: str,
        briefing_type: str = "daily",
    ) -> dict:
        """
        Run the Application Tracker Agent.

        Args:
            user_id: User ID to track applications for
            briefing_type: Type of briefing (daily, weekly, full)

        Returns:
            Dictionary containing briefing, analysis, and action items
        """
        initial_state: ApplicationTrackerState = {
            "user_id": user_id,
            "briefing_type": briefing_type,
            "db": self.db,
            "applications": [],
            "reminders": [],
            "timeline_events": [],
            "stats": {},
            "portfolio_analysis": {},
            "stale_applications": [],
            "recommendations": [],
            "action_items": [],
            "briefing": "",
            "error": None,
        }

        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)

            return {
                "success": True,
                "briefing": final_state.get("briefing", ""),
                "portfolio_analysis": final_state.get("portfolio_analysis", {}),
                "stale_applications": final_state.get("stale_applications", []),
                "recommendations": final_state.get("recommendations", []),
                "action_items": final_state.get("action_items", []),
                "stats": final_state.get("stats", {}),
            }

        except Exception as e:
            logger.error(f"Error running Application Tracker Agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "briefing": "",
                "portfolio_analysis": {},
                "stale_applications": [],
                "recommendations": [],
                "action_items": [],
                "stats": {},
            }

    async def get_quick_stats(self, user_id: str) -> dict:
        """
        Get quick stats without full analysis (for dashboard).

        Args:
            user_id: User ID

        Returns:
            Quick statistics dictionary
        """
        try:
            stats = await self.tracking_service.get_application_stats(user_id)
            upcoming = await self.tracking_service.get_upcoming_reminders(user_id, hours_ahead=24*7)
            overdue = await self.tracking_service.get_overdue_reminders(user_id)

            # Calculate response rate: (interviews + offers) / total
            total = stats.total_applications or 1  # Avoid division by zero
            response_rate = ((stats.interviews_scheduled + stats.offers_received) / total) * 100

            return {
                "success": True,
                "total_applications": stats.total_applications,
                "active_applications": stats.active_applications,
                "response_rate": round(response_rate, 1),
                "upcoming_reminders": len(upcoming),
                "overdue_reminders": len(overdue),
                "by_status": stats.applications_by_status,
            }
        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return {
                "success": False,
                "error": str(e),
            }
