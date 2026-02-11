"""
Narrative Saturation API endpoints.

Provides endpoints for:
- Detecting saturated narratives in news coverage
- Getting narrative clusters and saturation scores
- Narrative lifecycle tracking and alerts
"""

from datetime import datetime, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_user_id
from ...narrative.detector import NarrativeSaturationDetector
from ...schema.models.narrative import NarrativeCluster, NarrativeSaturation, NarrativeAlert
from ...schema.models.ingestion import NewsArticle

router = APIRouter(prefix="/api/narrative", tags=["narrative"])
logger = logging.getLogger(__name__)

# Global detector instance
detector = NarrativeSaturationDetector()

@router.get("/saturation")
async def get_saturated_narratives(
    time_window_hours: int = Query(24, ge=1, le=168, description="Analysis time window in hours"),
    min_saturation_score: float = Query(0.7, ge=0.0, le=1.0, description="Minimum saturation score threshold"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Get currently saturated/overhyped narratives.

    Returns narratives that exceed the saturation threshold, indicating
    potential echo chambers or oversaturated coverage.
    """
    try:
        # Get recent news articles
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        stmt = select(NewsArticle).where(NewsArticle.published_at >= cutoff_time)
        result = await db.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            return {
                "saturated_narratives": [],
                "total_analyzed": 0,
                "time_window_hours": time_window_hours,
                "saturation_threshold": min_saturation_score
            }

        # Detect saturated narratives
        saturated_narratives = detector.get_saturated_narratives(articles, time_window_hours)

        # Filter by minimum saturation score
        filtered_narratives = [
            n for n in saturated_narratives
            if n['saturation_score'] >= min_saturation_score
        ][:limit]

        logger.info(f"Found {len(filtered_narratives)} saturated narratives from {len(articles)} articles")

        return {
            "saturated_narratives": filtered_narratives,
            "total_analyzed": len(articles),
            "time_window_hours": time_window_hours,
            "saturation_threshold": min_saturation_score,
            "returned_count": len(filtered_narratives)
        }

    except Exception as e:
        logger.error(f"Error getting saturated narratives: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze narratives: {str(e)}")

@router.get("/clusters")
async def get_narrative_clusters(
    time_window_hours: int = Query(24, ge=1, le=168, description="Analysis time window in hours"),
    min_cluster_size: int = Query(3, ge=2, le=50, description="Minimum articles per cluster"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of clusters"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Get all narrative clusters detected in the time window.

    Returns both saturated and non-saturated narrative clusters
    for comprehensive analysis.
    """
    try:
        # Get recent news articles
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        stmt = select(NewsArticle).where(NewsArticle.published_at >= cutoff_time)
        result = await db.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            return {
                "clusters": [],
                "total_articles": 0,
                "time_window_hours": time_window_hours
            }

        # Detect narrative clusters
        clusters = detector.detect_narratives(articles, time_window_hours)

        # Filter by minimum cluster size
        filtered_clusters = [
            c for c in clusters
            if len(c.articles) >= min_cluster_size
        ][:limit]

        # Convert to API response format
        cluster_data = []
        for cluster in filtered_clusters:
            cluster_dict = {
                "id": cluster.id,
                "representative_title": cluster.representative_title,
                "article_count": len(cluster.articles),
                "source_count": len(cluster.source_distribution),
                "average_tone": cluster.average_tone,
                "coverage_intensity": cluster.coverage_intensity,
                "time_span_hours": cluster.time_span_hours,
                "source_distribution": cluster.source_distribution,
                "created_at": cluster.created_at.isoformat(),
                "articles": [
                    {
                        "title": a.title,
                        "source": a.source,
                        "published_at": a.published_at.isoformat(),
                        "tone": a.tone,
                        "url": a.url
                    }
                    for a in cluster.articles[:10]  # Top 10 articles
                ]
            }
            cluster_data.append(cluster_dict)

        logger.info(f"Found {len(cluster_data)} narrative clusters from {len(articles)} articles")

        return {
            "clusters": cluster_data,
            "total_articles": len(articles),
            "time_window_hours": time_window_hours,
            "min_cluster_size": min_cluster_size
        }

    except Exception as e:
        logger.error(f"Error getting narrative clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get clusters: {str(e)}")

@router.get("/saturation/{cluster_id}")
async def get_cluster_saturation(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Get detailed saturation analysis for a specific narrative cluster.
    """
    try:
        # Get cluster from database
        stmt = select(NarrativeCluster).where(NarrativeCluster.id == cluster_id)
        result = await db.execute(stmt)
        cluster = result.scalar_one_or_none()

        if not cluster:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

        # Get latest saturation score
        stmt = select(NarrativeSaturation).where(
            NarrativeSaturation.cluster_id == cluster_id
        ).order_by(desc(NarrativeSaturation.calculated_at)).limit(1)
        result = await db.execute(stmt)
        saturation = result.scalar_one_or_none()

        if not saturation:
            # Calculate saturation on-demand
            saturation_scores = detector.calculate_saturation_scores([cluster])
            saturation = saturation_scores[0] if saturation_scores else None

        if not saturation:
            raise HTTPException(status_code=404, detail=f"No saturation data for cluster {cluster_id}")

        return {
            "cluster_id": cluster.id,
            "representative_title": cluster.representative_title,
            "saturation_score": saturation.saturation_score,
            "lifecycle_stage": saturation.lifecycle_stage,
            "coverage_volume": saturation.coverage_volume,
            "source_concentration": saturation.source_concentration,
            "repetition_score": saturation.repetition_score,
            "temporal_distribution": saturation.temporal_distribution,
            "is_saturated": saturation.is_saturated,
            "calculated_at": saturation.calculated_at.isoformat(),
            "source_distribution": cluster.source_distribution,
            "average_tone": cluster.average_tone,
            "coverage_intensity": cluster.coverage_intensity,
            "time_span_hours": cluster.time_span_hours
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster saturation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get saturation data: {str(e)}")

@router.get("/alerts")
async def get_narrative_alerts(
    active_only: bool = Query(True, description="Return only active alerts"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Get narrative-based alerts for saturated or problematic coverage.
    """
    try:
        stmt = select(NarrativeAlert).order_by(desc(NarrativeAlert.created_at))

        if active_only:
            stmt = stmt.where(NarrativeAlert.is_active == True)

        if severity_filter:
            stmt = stmt.where(NarrativeAlert.severity == severity_filter)

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        alert_data = []
        for alert in alerts:
            alert_dict = {
                "id": alert.id,
                "cluster_id": alert.cluster_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "saturation_score": alert.saturation_score,
                "article_count": alert.article_count,
                "source_count": alert.source_count,
                "is_active": alert.is_active,
                "created_at": alert.created_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            alert_data.append(alert_dict)

        return {
            "alerts": alert_data,
            "total_count": len(alert_data),
            "active_only": active_only,
            "severity_filter": severity_filter
        }

    except Exception as e:
        logger.error(f"Error getting narrative alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

@router.post("/analyze")
async def analyze_narratives(
    time_window_hours: int = Query(24, ge=1, le=168, description="Analysis time window in hours"),
    save_results: bool = Query(False, description="Save analysis results to database"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Perform comprehensive narrative analysis and optionally save results.

    This endpoint runs the full narrative saturation detection pipeline
    and can persist the results for historical tracking.
    """
    try:
        # Get recent news articles
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        stmt = select(NewsArticle).where(NewsArticle.published_at >= cutoff_time)
        result = await db.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            return {
                "message": "No articles found in time window",
                "time_window_hours": time_window_hours,
                "articles_analyzed": 0
            }

        # Detect narrative clusters
        clusters = detector.detect_narratives(articles, time_window_hours)

        # Calculate saturation scores
        saturation_scores = detector.calculate_saturation_scores(clusters)

        # Save results if requested
        if save_results:
            await _save_analysis_results(db, clusters, saturation_scores)

        # Generate alerts for saturated narratives
        saturated_scores = [s for s in saturation_scores if s.is_saturated]
        alerts_generated = await _generate_narrative_alerts(db, saturated_scores)

        # Prepare response
        analysis_results = {
            "clusters_detected": len(clusters),
            "saturated_narratives": len(saturated_scores),
            "alerts_generated": alerts_generated,
            "articles_analyzed": len(articles),
            "time_window_hours": time_window_hours,
            "results_saved": save_results,
            "top_saturated": [
                {
                    "cluster_id": s.cluster_id,
                    "saturation_score": s.saturation_score,
                    "lifecycle_stage": s.lifecycle_stage,
                    "coverage_volume": s.coverage_volume
                }
                for s in saturated_scores[:5]  # Top 5
            ]
        }

        logger.info(f"Narrative analysis completed: {analysis_results}")
        return analysis_results

    except Exception as e:
        logger.error(f"Error in narrative analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def _save_analysis_results(db: AsyncSession, clusters: List[NarrativeCluster],
                               saturation_scores: List[NarrativeSaturation]):
    """Save analysis results to database."""
    try:
        # Save clusters
        for cluster in clusters:
            db.add(cluster)

        # Save saturation scores
        for saturation in saturation_scores:
            db.add(saturation)

        await db.commit()
        logger.info(f"Saved {len(clusters)} clusters and {len(saturation_scores)} saturation scores")

    except Exception as e:
        logger.error(f"Error saving analysis results: {e}")
        await db.rollback()
        raise

async def _generate_narrative_alerts(db: AsyncSession, saturated_scores: List[NarrativeSaturation]) -> int:
    """Generate alerts for saturated narratives."""
    alerts_created = 0

    try:
        for saturation in saturated_scores:
            # Check if alert already exists for this cluster
            stmt = select(NarrativeAlert).where(
                NarrativeAlert.cluster_id == saturation.cluster_id,
                NarrativeAlert.is_active == True
            )
            result = await db.execute(stmt)
            existing_alert = result.scalar_one_or_none()

            if existing_alert:
                continue  # Alert already exists

            # Create new alert
            alert_type = "saturation_warning" if saturation.saturation_score >= 0.8 else "moderate_saturation"
            severity = "high" if saturation.saturation_score >= 0.9 else "medium"

            # Get cluster info for alert message
            stmt = select(NarrativeCluster).where(NarrativeCluster.id == saturation.cluster_id)
            result = await db.execute(stmt)
            cluster = result.scalar_one_or_none()

            if cluster:
                alert = NarrativeAlert(
                    cluster_id=saturation.cluster_id,
                    alert_type=alert_type,
                    severity=severity,
                    title=f"Narrative Saturation Alert: {cluster.representative_title[:50]}...",
                    message=f"Narrative cluster '{cluster.representative_title}' has reached saturation score of {saturation.saturation_score:.2f} with {saturation.coverage_volume} articles from {len(cluster.source_distribution)} sources.",
                    saturation_score=saturation.saturation_score,
                    article_count=saturation.coverage_volume,
                    source_count=len(cluster.source_distribution)
                )

                db.add(alert)
                alerts_created += 1

        if alerts_created > 0:
            await db.commit()
            logger.info(f"Generated {alerts_created} narrative alerts")

        return alerts_created

    except Exception as e:
        logger.error(f"Error generating narrative alerts: {e}")
        await db.rollback()
        return 0