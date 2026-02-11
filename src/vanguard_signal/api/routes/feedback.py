"""
feedback.py — Analyst feedback (Confirm / Dismiss) and Post-Mortem endpoints.

Endpoints:
  POST   /api/feedback                — Submit a verdict on an alert
  GET    /api/feedback/{alert_id}     — Get all feedback for an alert
  POST   /api/postmortem              — Create a post-mortem for an alert
  GET    /api/postmortem/{alert_id}   — Get the post-mortem for an alert
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db, get_user_id

logger = logging.getLogger(__name__)
from vanguard_signal.schema.enums import AlertStatus
from vanguard_signal.schema.models.alert import Alert, AnalystFeedback, PostMortem
from vanguard_signal.schema.validators import (
    AnalystFeedbackCreate,
    AnalystFeedbackRead,
    PostMortemCreate,
    PostMortemRead,
)

router = APIRouter(tags=["feedback"])


# ═════════════════════════════════════════════════════════════════════════
# ANALYST FEEDBACK
# ═════════════════════════════════════════════════════════════════════════

@router.post("/api/feedback", response_model=AnalystFeedbackRead, status_code=201)
async def submit_feedback(
    body: AnalystFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> AnalystFeedbackRead:
    """
    Submit a Confirm or Dismiss verdict for an alert.

    The user_id from the header overrides body.user_id to prevent spoofing.
    This feeds the RL layer that tunes ensemble weights over time.
    """
    # Validate alert exists
    alert = await db.get(Alert, body.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    feedback = AnalystFeedback(
        alert_id=body.alert_id,
        user_id=user_id,
        verdict=body.verdict,
        confidence=body.confidence,
        comment=body.comment,
    )
    db.add(feedback)

    # Auto-transition alert status based on verdict
    if body.verdict.value == "confirm" and alert.status == AlertStatus.ACTIVE:
        alert.status = AlertStatus.CONFIRMED
        alert.updated_by = user_id
    elif body.verdict.value == "dismiss" and alert.status == AlertStatus.ACTIVE:
        alert.status = AlertStatus.DISMISSED
        alert.updated_by = user_id

    await db.flush()

    # ── Record analytics for rule-based alerts ───────────────────────
    try:
        from vanguard_signal.detection.analytics import get_analytics_service
        analytics_service = get_analytics_service()

        # Calculate response time if alert was resolved
        response_time = None
        if alert.status in [AlertStatus.CONFIRMED, AlertStatus.DISMISSED]:
            response_time = (feedback.created_at - alert.created_at).total_seconds() / 60.0

        was_confirmed = body.verdict.value == "confirm"
        await analytics_service.record_alert_resolution(
            alert=alert,
            was_confirmed=was_confirmed,
            response_time_minutes=response_time
        )
    except Exception as analytics_exc:
        logger.debug("Analytics recording failed: %s", analytics_exc)

    # ── RL Feedback Loop: update ensemble weights ────────────────────
    try:
        from vanguard_signal.config import settings
        if settings.enable_rl_feedback:
            from vanguard_signal.detection.rl_feedback import process_feedback
            rl_result = await process_feedback(feedback, db)
            logger.info("RL feedback processed: %s", rl_result.get("status"))
    except Exception as rl_exc:
        logger.warning("RL feedback processing failed: %s", rl_exc)

    return AnalystFeedbackRead.model_validate(feedback)


@router.get("/api/feedback/{alert_id}", response_model=list[AnalystFeedbackRead])
async def get_feedback_for_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AnalystFeedbackRead]:
    """Return all analyst feedback for a given alert."""
    stmt = (
        select(AnalystFeedback)
        .where(AnalystFeedback.alert_id == alert_id)
        .order_by(AnalystFeedback.created_at.desc())
    )
    result = await db.execute(stmt)
    return [AnalystFeedbackRead.model_validate(f) for f in result.scalars().all()]


# ═════════════════════════════════════════════════════════════════════════
# POST-MORTEM
# ═════════════════════════════════════════════════════════════════════════

@router.post("/api/postmortem", response_model=PostMortemRead, status_code=201)
async def create_postmortem(
    body: PostMortemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> PostMortemRead:
    """
    Create a post-mortem for an alert.  Only one per alert.

    This records the ground truth: was it a true positive, false positive,
    or inconclusive?  The backtesting engine and RL loop learn from this.
    """
    # Check alert exists
    alert = await db.get(Alert, body.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check for existing post-mortem
    existing = await db.execute(
        select(PostMortem).where(PostMortem.alert_id == body.alert_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Post-mortem already exists for this alert")

    # Compute lead time if we have timestamps
    lead_time = None
    if body.event_actual_start:
        delta = body.event_actual_start - alert.created_at
        lead_time = delta.total_seconds() / 3600.0

    pm = PostMortem(
        alert_id=body.alert_id,
        event_outcome=body.event_outcome,
        impact_domain=body.impact_domain,
        impact_severity=body.impact_severity,
        notes=body.notes,
        external_references=body.external_references,
        event_actual_start=body.event_actual_start,
        event_actual_end=body.event_actual_end,
        lead_time_hours=lead_time or body.lead_time_hours,
        created_by=user_id,
    )
    db.add(pm)

    # Transition alert to RESOLVED
    alert.status = AlertStatus.RESOLVED
    alert.updated_by = user_id

    await db.flush()
    return PostMortemRead.model_validate(pm)


@router.get("/api/postmortem/{alert_id}", response_model=PostMortemRead)
async def get_postmortem(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PostMortemRead:
    """Get the post-mortem for a given alert."""
    stmt = select(PostMortem).where(PostMortem.alert_id == alert_id)
    result = await db.execute(stmt)
    pm = result.scalar_one_or_none()
    if not pm:
        raise HTTPException(status_code=404, detail="Post-mortem not found")
    return PostMortemRead.model_validate(pm)
