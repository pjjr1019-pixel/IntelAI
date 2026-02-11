"""
replay.py — API endpoints for Replay Mode functionality.

Routes
------
POST   /api/replay/sessions        — Create a new replay session
GET    /api/replay/sessions        — List replay sessions
GET    /api/replay/sessions/{id}   — Get replay session details
POST   /api/replay/sessions/{id}/run — Run a replay session
GET    /api/replay/sessions/{id}/results — Get replay results
DELETE /api/replay/sessions/{id}   — Delete a replay session
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
import logging

from vanguard_signal.api.deps import get_db, get_user_id
from vanguard_signal.schema.models.alert import (
    ReplayDecision,
    ReplaySession,
    ReplaySignal,
    ReplaySnapshot,
)
from vanguard_signal.schema.models.signal import SignalTimeSeries, AnomalyResult
from vanguard_signal.detection.ensemble import EnsembleDetector
from vanguard_signal.schema.enums import Severity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/replay", tags=["replay"])


# ── Request/Response Models ──────────────────────────────────────────────

class ReplaySessionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    parameters: Dict[str, Any]


class ReplaySessionResponse(BaseModel):
    id: UUID
    user_id: str
    name: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    parameters: Dict[str, Any]
    status: str
    progress_percentage: Optional[float]
    alerts_generated: int
    trades_simulated: int
    key_insights: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ReplaySnapshotResponse(BaseModel):
    id: UUID
    session_id: UUID
    snapshot_time: datetime
    sequence_number: int
    active_signals: List[Dict[str, Any]]
    system_parameters: Dict[str, Any]
    market_conditions: Optional[Dict[str, Any]]
    portfolio_state: Optional[Dict[str, Any]]


class ReplayDecisionResponse(BaseModel):
    id: UUID
    session_id: UUID
    decision_time: datetime
    decision_type: str
    sequence_number: int
    decision_data: Dict[str, Any]
    confidence_score: Optional[float]
    original_alert_id: Optional[UUID]
    original_trade_id: Optional[UUID]
    would_have_occurred: Optional[bool]
    impact_analysis: Optional[Dict[str, Any]]


class ReplaySignalResponse(BaseModel):
    id: UUID
    session_id: UUID
    entity_value: str
    signal_time: datetime
    original_scores: Dict[str, Any]
    adjusted_scores: Dict[str, Any]
    would_trigger_alert: bool
    confidence_level: float
    signal_metadata: Optional[Dict[str, Any]]
    parameter_sensitivity: Optional[Dict[str, Any]]


# ── API Endpoints ───────────────────────────────────────────────────────

@router.post("/sessions", response_model=ReplaySessionResponse)
async def create_replay_session(
    request: ReplaySessionCreateRequest,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReplaySessionResponse:
    """
    Create a new replay session.

    This initializes a replay session with the specified parameters and time range.
    The session will be in 'created' status until run.
    """
    # Validate time range
    if request.start_time >= request.end_time:
        raise HTTPException(
            status_code=400,
            detail="Start time must be before end time"
        )

    # Create the session
    session = ReplaySession(
        user_id=user_id,
        name=request.name,
        description=request.description,
        start_time=request.start_time,
        end_time=request.end_time,
        parameters=request.parameters,
        status="created",
        alerts_generated=0,
        trades_simulated=0,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ReplaySessionResponse(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        description=session.description,
        start_time=session.start_time,
        end_time=session.end_time,
        parameters=session.parameters,
        status=session.status,
        progress_percentage=session.progress_percentage,
        alerts_generated=session.alerts_generated,
        trades_simulated=session.trades_simulated,
        key_insights=session.key_insights,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=List[ReplaySessionResponse])
async def list_replay_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[ReplaySessionResponse]:
    """
    List replay sessions for the current user.

    Supports filtering by status and pagination.
    """
    query = select(ReplaySession).where(ReplaySession.user_id == user_id)

    if status:
        query = query.where(ReplaySession.status == status)

    query = query.offset(skip).limit(limit).order_by(ReplaySession.created_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [
        ReplaySessionResponse(
            id=session.id,
            user_id=session.user_id,
            name=session.name,
            description=session.description,
            start_time=session.start_time,
            end_time=session.end_time,
            parameters=session.parameters,
            status=session.status,
            progress_percentage=session.progress_percentage,
            alerts_generated=session.alerts_generated,
            trades_simulated=session.trades_simulated,
            key_insights=session.key_insights,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ReplaySessionResponse)
async def get_replay_session(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReplaySessionResponse:
    """
    Get details of a specific replay session.
    """
    query = select(ReplaySession).where(
        ReplaySession.id == session_id,
        ReplaySession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")

    return ReplaySessionResponse(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        description=session.description,
        start_time=session.start_time,
        end_time=session.end_time,
        parameters=session.parameters,
        status=session.status,
        progress_percentage=session.progress_percentage,
        alerts_generated=session.alerts_generated,
        trades_simulated=session.trades_simulated,
        key_insights=session.key_insights,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/run")
async def run_replay_session(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run a replay session.

    This will execute the replay logic, processing historical data with
    the session's parameters and generating snapshots, decisions, and signals.
    """
    # Get the session
    query = select(ReplaySession).where(
        ReplaySession.id == session_id,
        ReplaySession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")

    if session.status not in ["created", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Session is already {session.status}"
        )

    # Update session status to running
    session.status = "running"
    session.progress_percentage = 0.0
    await db.commit()

    try:
        # Run the replay in background task
        asyncio.create_task(_execute_replay_session(session_id, db))

        return {
            "message": "Replay session started",
            "session_id": session_id,
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Failed to start replay session {session_id}: {e}")
        session.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to start replay session")


async def _execute_replay_session(session_id: UUID, db: AsyncSession):
    """
    Execute the replay session logic in the background.
    """
    try:
        # Get session
        session = await db.get(ReplaySession, session_id)
        if not session:
            logger.error(f"Replay session {session_id} not found")
            return

        # Get replay parameters
        params = session.parameters or {}
        detector_weights = params.get("detector_weights", {
            "stl": 0.30,
            "iforest": 0.25,
            "cusum": 0.25,
            "velocity": 0.20
        })
        ensemble_threshold = params.get("ensemble_threshold", 0.6)
        alert_threshold = params.get("alert_threshold", 0.7)

        # Fetch historical time series data for the replay period
        time_series_query = select(SignalTimeSeries).where(
            and_(
                SignalTimeSeries.bucket_start >= session.start_time,
                SignalTimeSeries.bucket_start < session.end_time
            )
        ).order_by(SignalTimeSeries.bucket_start)

        result = await db.execute(time_series_query)
        time_series_data = result.scalars().all()

        if not time_series_data:
            logger.warning(f"No time series data found for replay session {session_id}")
            session.status = "completed"
            session.progress_percentage = 100.0
            await db.commit()
            return

        # Group data by entity
        entity_data = {}
        for ts in time_series_data:
            entity = ts.entity_value
            if entity not in entity_data:
                entity_data[entity] = []
            entity_data[entity].append(ts)

        # Sort each entity's data by time
        for entity in entity_data:
            entity_data[entity].sort(key=lambda x: x.bucket_start)

        total_entities = len(entity_data)
        processed_entities = 0
        alerts_generated = 0
        signals_created = 0

        # Process each entity
        for entity, series in entity_data.items():
            try:
                # Extract values and timestamps
                values = [ts.value for ts in series]
                timestamps = [ts.bucket_start for ts in series]

                if len(values) < 5:  # Minimum for meaningful detection
                    continue

                # Create ensemble detector with session parameters
                detector = EnsembleDetector(
                    weight_stl=detector_weights.get("stl", 0.30),
                    weight_iforest=detector_weights.get("iforest", 0.25),
                    weight_cusum=detector_weights.get("cusum", 0.25),
                    weight_velocity=detector_weights.get("velocity", 0.20),
                    ensemble_threshold=ensemble_threshold
                )

                # Run detection on the historical data
                detection_result = detector.detect(values)

                # Create replay signal record
                original_scores = {
                    "stl": detection_result.stl.score,
                    "iforest": detection_result.iforest.score,
                    "cusum": detection_result.cusum.score,
                    "velocity": detection_result.velocity.score,
                    "ensemble": detection_result.ensemble_score
                }

                # Apply parameter modifications for "what-if" analysis
                adjusted_scores = _apply_parameter_adjustments(original_scores, params)

                # Determine if this would trigger an alert
                would_trigger = adjusted_scores["ensemble"] >= alert_threshold

                signal = ReplaySignal(
                    session_id=session_id,
                    entity_value=entity,
                    signal_time=series[-1].bucket_start,  # Latest timestamp
                    original_scores=original_scores,
                    adjusted_scores=adjusted_scores,
                    would_trigger_alert=would_trigger,
                    confidence_level=adjusted_scores["ensemble"],
                    signal_metadata={
                        "data_points": len(values),
                        "time_range": {
                            "start": timestamps[0].isoformat(),
                            "end": timestamps[-1].isoformat()
                        },
                        "source_coverage": sum(ts.coverage_score for ts in series) / len(series)
                    },
                    parameter_sensitivity=_calculate_sensitivity(original_scores, params)
                )

                db.add(signal)
                signals_created += 1

                # If it would trigger an alert, create a replay decision
                if would_trigger:
                    # Determine severity based on confidence
                    confidence = adjusted_scores["ensemble"]
                    if confidence >= 0.9:
                        severity = Severity.CRITICAL
                    elif confidence >= 0.8:
                        severity = Severity.HIGH
                    elif confidence >= 0.7:
                        severity = Severity.MEDIUM
                    else:
                        severity = Severity.LOW

                    decision = ReplayDecision(
                        session_id=session_id,
                        decision_time=series[-1].bucket_start,
                        decision_type="alert_generation",
                        sequence_number=alerts_generated + 1,
                        decision_data={
                            "entity": entity,
                            "severity": severity.value,
                            "confidence": confidence,
                            "scores": adjusted_scores,
                            "reasoning": f"Anomaly detected with ensemble score {confidence:.3f}"
                        },
                        confidence_score=confidence,
                        would_have_occurred=True,
                        impact_analysis={
                            "potential_trading_opportunity": confidence >= 0.8,
                            "requires_immediate_attention": severity in [Severity.HIGH, Severity.CRITICAL]
                        }
                    )

                    db.add(decision)
                    alerts_generated += 1

                # Create periodic snapshots (every 10 signals or at key points)
                if signals_created % 10 == 0 or processed_entities == total_entities - 1:
                    snapshot = ReplaySnapshot(
                        session_id=session_id,
                        snapshot_time=series[-1].bucket_start,
                        sequence_number=signals_created // 10 + 1,
                        active_signals=[
                            {
                                "entity": entity,
                                "score": adjusted_scores["ensemble"],
                                "would_trigger": would_trigger
                            }
                        ],
                        system_parameters={
                            "detector_weights": detector_weights,
                            "ensemble_threshold": ensemble_threshold,
                            "alert_threshold": alert_threshold
                        },
                        market_conditions={
                            "replay_mode": True,
                            "historical_data": True
                        }
                    )
                    db.add(snapshot)

                await db.commit()  # Commit periodically

            except Exception as e:
                logger.error(f"Error processing entity {entity} in replay session {session_id}: {e}")
                continue

            processed_entities += 1
            session.progress_percentage = (processed_entities / total_entities) * 100.0
            await db.commit()

        # Update session with final results
        session.status = "completed"
        session.alerts_generated = alerts_generated
        session.trades_simulated = 0  # For now, just alerts; trading simulation can be added later
        session.key_insights = {
            "total_entities_processed": total_entities,
            "signals_analyzed": signals_created,
            "alerts_would_have_triggered": alerts_generated,
            "parameter_sensitivity": params.get("sensitivity_analysis", {}),
            "detection_effectiveness": {
                "alert_rate": alerts_generated / max(signals_created, 1),
                "high_confidence_alerts": sum(1 for s in [] if s.confidence_level >= 0.8)  # Would need to query
            }
        }

        await db.commit()
        logger.info(f"Replay session {session_id} completed successfully")

    except Exception as e:
        logger.error(f"Replay session {session_id} failed: {e}")
        session = await db.get(ReplaySession, session_id)
        if session:
            session.status = "failed"
            await db.commit()


def _apply_parameter_adjustments(original_scores: Dict[str, float], params: Dict[str, Any]) -> Dict[str, float]:
    """
    Apply parameter adjustments for what-if analysis.
    """
    adjusted = original_scores.copy()

    # Apply sensitivity adjustments if specified
    sensitivity = params.get("sensitivity", {})
    for detector, multiplier in sensitivity.items():
        if detector in adjusted:
            adjusted[detector] *= multiplier

    # Recalculate ensemble score with potentially different weights
    weights = params.get("detector_weights", {
        "stl": 0.30, "iforest": 0.25, "cusum": 0.25, "velocity": 0.20
    })

    adjusted["ensemble"] = sum(
        weights.get(detector, 0.0) * score
        for detector, score in adjusted.items()
        if detector != "ensemble"
    )

    return adjusted


def _calculate_sensitivity(original_scores: Dict[str, float], params: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate parameter sensitivity for the signal.
    """
    sensitivity = {}
    base_ensemble = original_scores["ensemble"]

    # Test small changes in each detector weight
    for detector in ["stl", "iforest", "cusum", "velocity"]:
        if detector in original_scores:
            # Increase weight by 10%
            test_weights = params.get("detector_weights", {
                "stl": 0.30, "iforest": 0.25, "cusum": 0.25, "velocity": 0.20
            }).copy()
            test_weights[detector] *= 1.1

            # Normalize weights
            total = sum(test_weights.values())
            test_weights = {k: v/total for k, v in test_weights.items()}

            test_ensemble = sum(
                test_weights.get(d, 0.0) * original_scores.get(d, 0.0)
                for d in ["stl", "iforest", "cusum", "velocity"]
            )

            sensitivity[detector] = (test_ensemble - base_ensemble) / base_ensemble if base_ensemble > 0 else 0

    return sensitivity


@router.get("/sessions/{session_id}/results")
async def get_replay_results(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the results of a completed replay session.

    Returns snapshots, decisions, signals, and analysis.
    """
    # Get the session
    query = select(ReplaySession).where(
        ReplaySession.id == session_id,
        ReplaySession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")

    if session.status not in ["completed", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.status}, no results available"
        )

    # Get snapshots
    snapshot_query = select(ReplaySnapshot).where(
        ReplaySnapshot.session_id == session_id
    ).order_by(ReplaySnapshot.sequence_number)
    snapshot_result = await db.execute(snapshot_query)
    snapshots = snapshot_result.scalars().all()

    # Get decisions
    decision_query = select(ReplayDecision).where(
        ReplayDecision.session_id == session_id
    ).order_by(ReplayDecision.sequence_number)
    decision_result = await db.execute(decision_query)
    decisions = decision_result.scalars().all()

    # Get signals
    signal_query = select(ReplaySignal).where(
        ReplaySignal.session_id == session_id
    ).order_by(ReplaySignal.signal_time)
    signal_result = await db.execute(signal_query)
    signals = signal_result.scalars().all()

    return {
        "session": ReplaySessionResponse(
            id=session.id,
            user_id=session.user_id,
            name=session.name,
            description=session.description,
            start_time=session.start_time,
            end_time=session.end_time,
            parameters=session.parameters,
            status=session.status,
            progress_percentage=session.progress_percentage,
            alerts_generated=session.alerts_generated,
            trades_simulated=session.trades_simulated,
            key_insights=session.key_insights,
            created_at=session.created_at,
            updated_at=session.updated_at,
        ),
        "snapshots": [
            ReplaySnapshotResponse(
                id=snapshot.id,
                session_id=snapshot.session_id,
                snapshot_time=snapshot.snapshot_time,
                sequence_number=snapshot.sequence_number,
                active_signals=snapshot.active_signals,
                system_parameters=snapshot.system_parameters,
                market_conditions=snapshot.market_conditions,
                portfolio_state=snapshot.portfolio_state,
            )
            for snapshot in snapshots
        ],
        "decisions": [
            ReplayDecisionResponse(
                id=decision.id,
                session_id=decision.session_id,
                decision_time=decision.decision_time,
                decision_type=decision.decision_type,
                sequence_number=decision.sequence_number,
                decision_data=decision.decision_data,
                confidence_score=decision.confidence_score,
                original_alert_id=decision.original_alert_id,
                original_trade_id=decision.original_trade_id,
                would_have_occurred=decision.would_have_occurred,
                impact_analysis=decision.impact_analysis,
            )
            for decision in decisions
        ],
        "signals": [
            ReplaySignalResponse(
                id=signal.id,
                session_id=signal.session_id,
                entity_value=signal.entity_value,
                signal_time=signal.signal_time,
                original_scores=signal.original_scores,
                adjusted_scores=signal.adjusted_scores,
                would_trigger_alert=signal.would_trigger_alert,
                confidence_level=signal.confidence_level,
                signal_metadata=signal.signal_metadata,
                parameter_sensitivity=signal.parameter_sensitivity,
            )
            for signal in signals
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_replay_session(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Delete a replay session and all its associated data.
    """
    # Get the session
    query = select(ReplaySession).where(
        ReplaySession.id == session_id,
        ReplaySession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")

    # Delete the session (cascade will handle related records)
    await db.delete(session)
    await db.commit()

    return {"message": "Replay session deleted successfully"}