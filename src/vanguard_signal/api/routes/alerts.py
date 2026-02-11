"""
alerts.py — CRUD and lifecycle management for alerts.

Endpoints:
  GET    /api/alerts            — List alerts with filtering & pagination
  GET    /api/alerts/{id}       — Get a single alert with evidence + analogs
  PATCH  /api/alerts/{id}       — Update severity or status
  GET    /api/alerts/{id}/full  — Full detail: alert + evidence + feedback + postmortem
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.schema.enums import AlertStatus, Severity
from vanguard_signal.schema.models.alert import (
    Alert,
    AlertEscalation,
    AlertSilence,
    AlertTemplate,
    AnalystFeedback,
    EvidenceChain,
    HistoricalAnalog,
    PostMortem,
)
from vanguard_signal.schema.validators import AlertRead, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ── List Alerts ──────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_alerts(
    status: AlertStatus | None = Query(None, description="Filter by status"),
    severity: Severity | None = Query(None, description="Filter by severity"),
    entity: str | None = Query(None, description="Filter by primary_entity (substring)"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    sort_by: str = Query("created_at", pattern="^(created_at|confidence_score|severity)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List alerts with filtering, sorting, and pagination."""

    stmt = select(Alert)

    # Filters
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if entity:
        stmt = stmt.where(Alert.primary_entity.ilike(f"%{entity}%"))
    if min_confidence is not None:
        stmt = stmt.where(Alert.confidence_score >= min_confidence)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sort
    sort_col = getattr(Alert, sort_by)
    stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [AlertRead.model_validate(a) for a in alerts],
    }


# ── Get Single Alert ─────────────────────────────────────────────────────

@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertRead:
    """Get a single alert by ID."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertRead.model_validate(alert)


# ── Get Full Alert Detail ────────────────────────────────────────────────

@router.get("/{alert_id}/full", response_model=dict)
async def get_alert_full(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Full alert view: alert + evidence chains + feedback + postmortem +
    historical analogs.  This powers the "Evidence Chain" visualization.
    """
    stmt = (
        select(Alert)
        .where(Alert.id == alert_id)
        .options(
            selectinload(Alert.evidence_chains),
            selectinload(Alert.feedbacks),
            selectinload(Alert.postmortem),
            selectinload(Alert.historical_analogs),
        )
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "alert": AlertRead.model_validate(alert),
        "evidence_chains": [
            {
                "id": str(e.id),
                "raw_ids": e.raw_ids,
                "normalized_event_ids": e.normalized_event_ids,
                "series_ids": e.series_ids,
                "anomaly_ids": e.anomaly_ids,
                "explainability_text": e.explainability_text,
                "evidence_metadata": e.evidence_metadata,
            }
            for e in alert.evidence_chains
        ],
        "feedback": [
            {
                "id": str(f.id),
                "user_id": f.user_id,
                "verdict": f.verdict.value,
                "confidence": f.confidence,
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f in alert.feedbacks
        ],
        "postmortem": (
            {
                "event_outcome": alert.postmortem.event_outcome.value,
                "impact_domain": (
                    alert.postmortem.impact_domain.value
                    if alert.postmortem.impact_domain
                    else None
                ),
                "notes": alert.postmortem.notes,
                "lead_time_hours": alert.postmortem.lead_time_hours,
            }
            if alert.postmortem
            else None
        ),
        "historical_analogs": [
            {
                "matched_alert_id": str(a.matched_alert_id),
                "similarity_score": a.similarity_score,
                "similarity_method": a.similarity_method,
                "analog_summary": a.analog_summary,
                "reference_period_start": a.reference_period_start.isoformat(),
                "reference_period_end": a.reference_period_end.isoformat(),
            }
            for a in alert.historical_analogs
        ],
    }


# ── Update Alert ─────────────────────────────────────────────────────────

@router.patch("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: UUID,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> AlertRead:
    """Update alert severity or status (analyst workflow)."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if body.severity is not None:
        alert.severity = body.severity
    if body.status is not None:
        alert.status = body.status

    alert.updated_by = user_id
    await db.flush()

    return AlertRead.model_validate(alert)


# ── Acknowledge Alert ────────────────────────────────────────────────────

@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(
    alert_id: UUID,
    comment: str | None = Query(None, description="Optional acknowledgment comment"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> AlertRead:
    """Acknowledge an alert (mark as acknowledged by analyst)."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(
            status_code=400,
            detail="Cannot acknowledge a resolved alert"
        )

    # Update status to acknowledged (keeping it active for monitoring)
    alert.status = AlertStatus.ACTIVE  # Keep active but mark as acknowledged
    alert.updated_by = user_id

    # Add analyst feedback for acknowledgment
    feedback = AnalystFeedback(
        alert_id=alert_id,
        user_id=user_id,
        verdict="confirm",  # Acknowledgment implies confirmation of validity
        confidence=0.8,    # Default confidence for acknowledgment
        comment=f"Alert acknowledged{f': {comment}' if comment else ''}",
    )
    db.add(feedback)

    await db.flush()

    return AlertRead.model_validate(alert)


# ── Resolve Alert ────────────────────────────────────────────────────────

@router.post("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: UUID,
    resolution: str = Query(..., description="Resolution explanation"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> AlertRead:
    """Resolve an alert (mark as resolved with explanation)."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update status to resolved
    alert.status = AlertStatus.RESOLVED
    alert.updated_by = user_id

    # Add analyst feedback for resolution
    feedback = AnalystFeedback(
        alert_id=alert_id,
        user_id=user_id,
        verdict="confirm",  # Resolution implies the alert was valid
        confidence=1.0,    # Full confidence for resolution
        comment=f"Alert resolved: {resolution}",
    )
    db.add(feedback)

    await db.flush()

    return AlertRead.model_validate(alert)


# ── Get Alert History ─────────────────────────────────────────────────────

@router.get("/{alert_id}/history", response_model=dict)
async def get_alert_history(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get complete history of an alert including escalations, feedback, and status changes."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Get escalations
    escalation_stmt = select(AlertEscalation).where(AlertEscalation.alert_id == alert_id).order_by(AlertEscalation.escalated_at)
    escalation_result = await db.execute(escalation_stmt)
    escalations = escalation_result.scalars().all()

    # Get feedback
    feedback_stmt = select(AnalystFeedback).where(AnalystFeedback.alert_id == alert_id).order_by(AnalystFeedback.created_at)
    feedback_result = await db.execute(feedback_stmt)
    feedbacks = feedback_result.scalars().all()

    # Build history timeline
    history_events = []

    # Initial creation event
    history_events.append({
        "timestamp": alert.created_at.isoformat(),
        "event_type": "created",
        "description": f"Alert created with severity {alert.severity.value}",
        "user_id": alert.created_by,
        "details": {
            "initial_severity": alert.severity.value,
            "primary_entity": alert.primary_entity,
            "confidence_score": alert.confidence_score,
        }
    })

    # Add escalation events
    for esc in escalations:
        history_events.append({
            "timestamp": esc.escalated_at.isoformat(),
            "event_type": "escalation",
            "description": f"Severity escalated from {esc.previous_severity} to {esc.new_severity}",
            "details": {
                "trigger": esc.escalation_trigger,
                "reason": esc.escalation_reason,
                "metadata": esc.escalation_metadata,
            }
        })

    # Add feedback events
    for fb in feedbacks:
        history_events.append({
            "timestamp": fb.created_at.isoformat(),
            "event_type": "feedback",
            "description": f"Analyst feedback: {fb.verdict.value}",
            "user_id": fb.user_id,
            "details": {
                "verdict": fb.verdict.value,
                "confidence": fb.confidence,
                "comment": fb.comment,
            }
        })

    # Add status change events (if we had audit logging)
    if alert.status == AlertStatus.RESOLVED:
        # Find the resolution feedback
        resolution_fb = next((fb for fb in feedbacks if "resolved" in (fb.comment or "").lower()), None)
        if resolution_fb:
            history_events.append({
                "timestamp": resolution_fb.created_at.isoformat(),
                "event_type": "resolved",
                "description": "Alert marked as resolved",
                "user_id": resolution_fb.user_id,
                "details": {
                    "resolution_comment": resolution_fb.comment,
                }
            })

    # Sort events by timestamp
    history_events.sort(key=lambda x: x["timestamp"])

    return {
        "alert_id": str(alert_id),
        "current_status": alert.status.value,
        "current_severity": alert.severity.value,
        "history": history_events,
    }


# ── Alert Silence Management ───────────────────────────────────────────

@router.post("/{alert_id}/silence", response_model=dict)
async def silence_alert(
    alert_id: UUID,
    duration_minutes: int | None = Query(None, description="Silence duration in minutes (null = indefinite)"),
    reason: str | None = Query(None, description="Reason for silencing"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> dict:
    """Silence notifications for a specific alert."""
    from vanguard_signal.detection.silence import get_silence_service
    service = get_silence_service()

    silence_id = await service.silence_alert(
        alert_id=str(alert_id),
        duration_minutes=duration_minutes,
        reason=reason,
        silenced_by=user_id,
        silence_type="alert",
        session=db,
    )

    return {
        "silence_id": silence_id,
        "message": f"Alert {alert_id} silenced for {duration_minutes or 'indefinite'} minutes",
    }


@router.post("/silence/entity", response_model=dict)
async def silence_entity(
    entity_pattern: str = Query(..., description="Regex pattern to match entity names"),
    duration_minutes: int | None = Query(None, description="Silence duration in minutes"),
    reason: str | None = Query(None, description="Reason for silencing"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> dict:
    """Silence notifications for alerts matching an entity pattern."""
    from vanguard_signal.detection.silence import get_silence_service
    service = get_silence_service()

    silence_id = await service.silence_alert(
        entity_pattern=entity_pattern,
        duration_minutes=duration_minutes,
        reason=reason,
        silenced_by=user_id,
        silence_type="entity",
        session=db,
    )

    return {
        "silence_id": silence_id,
        "message": f"Entity pattern '{entity_pattern}' silenced for {duration_minutes or 'indefinite'} minutes",
    }


@router.post("/silence/global", response_model=dict)
async def silence_global(
    duration_minutes: int | None = Query(None, description="Silence duration in minutes"),
    reason: str | None = Query(None, description="Reason for silencing"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> dict:
    """Silence all alert notifications globally."""
    from vanguard_signal.detection.silence import get_silence_service
    service = get_silence_service()

    silence_id = await service.silence_alert(
        duration_minutes=duration_minutes,
        reason=reason,
        silenced_by=user_id,
        silence_type="global",
        session=db,
    )

    return {
        "silence_id": silence_id,
        "message": f"Global alert silence activated for {duration_minutes or 'indefinite'} minutes",
    }


@router.delete("/silence/{silence_id}", response_model=dict)
async def unsilence(
    silence_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a silence rule."""
    from vanguard_signal.detection.silence import get_silence_service
    service = get_silence_service()

    success = await service.unsilence(str(silence_id), session=db)

    if success:
        return {"message": f"Silence rule {silence_id} deactivated"}
    else:
        raise HTTPException(status_code=404, detail="Silence rule not found or already inactive")


@router.get("/silence", response_model=list)
async def list_active_silences(
    db: AsyncSession = Depends(get_db),
) -> list:
    """List all active silence rules."""
    from vanguard_signal.detection.silence import get_silence_service
    service = get_silence_service()

    silences = await service.list_active_silences(session=db)
    return silences


# ═════════════════════════════════════════════════════════════════════════
# ALERT TEMPLATES
# ═════════════════════════════════════════════════════════════════════════

from vanguard_signal.schema.validators import (
    AlertTemplateCreate,
    AlertTemplateRead,
    AlertTemplateUpdate,
)


@router.post("/templates/", response_model=AlertTemplateRead)
async def create_alert_template(
    template: AlertTemplateCreate,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertTemplateRead:
    """Create a new alert template."""
    # If this is set as default, unset other defaults
    if template.is_default:
        await db.execute(
            select(AlertTemplate).where(AlertTemplate.is_default == True)
        )
        # Update all existing default templates to non-default
        await db.execute(
            "UPDATE alert.alert_template SET is_default = false WHERE is_default = true"
        )

    # Create the new template
    db_template = AlertTemplate(
        **template.model_dump(),
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    return AlertTemplateRead.model_validate(db_template)


@router.get("/templates/", response_model=list[AlertTemplateRead])
async def list_alert_templates(
    enabled_only: bool = Query(True, description="Only return enabled templates"),
    db: AsyncSession = Depends(get_db),
) -> list[AlertTemplateRead]:
    """List all alert templates."""
    query = select(AlertTemplate)
    if enabled_only:
        query = query.where(AlertTemplate.enabled == True)

    result = await db.execute(query)
    templates = result.scalars().all()
    return [AlertTemplateRead.model_validate(template) for template in templates]


@router.get("/templates/{template_id}", response_model=AlertTemplateRead)
async def get_alert_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
) -> AlertTemplateRead:
    """Get a specific alert template."""
    result = await db.execute(
        select(AlertTemplate).where(AlertTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Alert template not found")
    return AlertTemplateRead.model_validate(template)


@router.patch("/templates/{template_id}", response_model=AlertTemplateRead)
async def update_alert_template(
    template_id: int,
    template_update: AlertTemplateUpdate,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertTemplateRead:
    """Update an alert template."""
    result = await db.execute(
        select(AlertTemplate).where(AlertTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Alert template not found")

    # Prevent updating system templates
    if template.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system templates")

    # If setting as default, unset other defaults
    if template_update.is_default:
        await db.execute(
            "UPDATE alert.alert_template SET is_default = false WHERE is_default = true AND id != %s",
            (template_id,)
        )

    # Update the template
    update_data = template_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = user_id

    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return AlertTemplateRead.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_alert_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete an alert template."""
    result = await db.execute(
        select(AlertTemplate).where(AlertTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Alert template not found")

    # Prevent deleting system templates
    if template.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system templates")

    await db.delete(template)
    await db.commit()
    return {"message": "Alert template deleted successfully"}


# ── Alert Rule Analytics ─────────────────────────────────────────────────

@router.get("/analytics/rules", response_model=dict)
async def get_alert_rule_analytics(
    rule_id: str | None = Query(None, description="Specific rule ID to get analytics for"),
    days: int = Query(30, ge=1, le=365, description="Number of days of analytics to retrieve"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get performance analytics for alert rules.

    Returns effectiveness metrics, false positive rates, and response times.
    """
    from vanguard_signal.detection.analytics import get_analytics_service
    analytics_service = get_analytics_service()

    if rule_id:
        # Get analytics for specific rule
        analytics = await analytics_service.get_rule_analytics(rule_id, days)
        return {
            "rule_id": rule_id,
            "analytics": [analytics.__dict__ for analytics in analytics]
        }
    else:
        # Get analytics for all rules
        all_analytics = await analytics_service.get_all_rules_analytics(days)
        return {
            "rules": {
                rule_id: [analytics.__dict__ for analytics in rule_analytics]
                for rule_id, rule_analytics in all_analytics.items()
            }
        }


@router.post("/analytics/cleanup")
async def cleanup_old_analytics(
    max_age_days: int = Query(90, ge=30, description="Delete analytics older than this many days"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """
    Clean up old analytics records to prevent database bloat.

    Returns the number of records deleted.
    """
    from vanguard_signal.detection.analytics import get_analytics_service
    analytics_service = get_analytics_service()

    deleted_count = await analytics_service.cleanup_old_analytics(max_age_days)
    return {"records_deleted": deleted_count}
