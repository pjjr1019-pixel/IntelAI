"""
export.py — Data export endpoints (CSV, Excel, PDF download).

Endpoints:
  GET /api/export/alerts  — Download alerts as CSV
  GET /api/export/trends  — Download trends as CSV/Excel (in live_trending.py)
  GET /api/export/report  — Generate PDF report
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.schema.models.alert import Alert
from vanguard_signal.schema.models.trend import TrendKeyword, TrendTimeSeries

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger(__name__)

_ALERT_COLUMNS = [
    "id", "primary_entity", "severity", "status", "confidence_score",
    "ensemble_anomaly_score", "semantic_drift_score", "reason_code",
    "summary_text", "signal_start", "signal_end", "created_at",
]


@router.get("/alerts")
async def export_alerts_csv(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(10000, ge=1, le=100000),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export alerts as a CSV file download."""
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)

    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_ALERT_COLUMNS)

    for a in alerts:
        writer.writerow([
            str(a.id),
            a.primary_entity,
            a.severity.value if a.severity else "",
            a.status.value if a.status else "",
            round(a.confidence_score, 4) if a.confidence_score else "",
            round(a.ensemble_anomaly_score, 4) if a.ensemble_anomaly_score else "",
            round(a.semantic_drift_score, 4) if a.semantic_drift_score else "",
            a.reason_code or "",
            (a.summary_text or "")[:500],
            a.signal_start.isoformat() if a.signal_start else "",
            a.signal_end.isoformat() if a.signal_end else "",
            a.created_at.isoformat() if a.created_at else "",
        ])

    output.seek(0)
    logger.info("Exported %d alerts as CSV", len(alerts))

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vanguard_alerts.csv"},
    )


@router.get("/report")
async def generate_pdf_report(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    days: int = Query(7, ge=1, le=30, description="Number of days for the report"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Generate a comprehensive PDF report with trends, alerts, and analytics.
    """
    try:
        # Get report data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get trending data
        trends_result = await db.execute(
            select(TrendKeyword).filter(
                TrendKeyword.geo == geo,
                TrendKeyword.total_appearances >= 1
            ).order_by(TrendKeyword.avg_rank).limit(20)
        )
        trends = trends_result.scalars().all()

        # Get alerts
        alerts_result = await db.execute(
            select(Alert).filter(
                Alert.created_at >= cutoff_date
            ).order_by(Alert.created_at.desc()).limit(50)
        )
        alerts = alerts_result.scalars().all()

        # Get alert statistics
        alert_stats_result = await db.execute(
            select(
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.created_at >= cutoff_date
            ).group_by(Alert.severity)
        )
        alert_stats = alert_stats_result.all()

        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("Vanguard Signal Report", title_style))
        story.append(Spacer(1, 12))

        # Report metadata
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray
        )
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        story.append(Paragraph(f"Period: Last {days} days", meta_style))
        story.append(Paragraph(f"Region: {geo}", meta_style))
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Spacer(1, 12))

        summary_text = f"""
        This report covers anomaly detection and trending analysis for the {geo} region over the past {days} days.
        Key findings include {len(trends)} trending topics and {len(alerts)} alerts generated.
        """

        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))

        # Alert Statistics
        if alert_stats:
            story.append(Paragraph("Alert Statistics", styles['Heading3']))
            story.append(Spacer(1, 12))

            # Create statistics table
            stat_data = [['Severity', 'Count']]
            for stat in alert_stats:
                stat_data.append([stat.severity.value if stat.severity else 'Unknown', str(stat.count)])

            stat_table = Table(stat_data)
            stat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(stat_table)
            story.append(Spacer(1, 20))

        # Top Trends
        if trends:
            story.append(Paragraph("Top Trending Topics", styles['Heading3']))
            story.append(Spacer(1, 12))

            # Create trends table
            trend_data = [['Rank', 'Keyword', 'Category', 'Avg Rank', 'Appearances']]
            for i, trend in enumerate(trends[:10], 1):
                trend_data.append([
                    str(i),
                    trend.keyword[:50],  # Truncate long keywords
                    trend.category or 'N/A',
                    f"{trend.avg_rank:.1f}",
                    str(trend.total_appearances)
                ])

            trend_table = Table(trend_data)
            trend_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(trend_table)
            story.append(Spacer(1, 20))

        # Recent Alerts
        if alerts:
            story.append(Paragraph("Recent Alerts", styles['Heading3']))
            story.append(Spacer(1, 12))

            alert_data = [['Time', 'Entity', 'Severity', 'Status', 'Summary']]
            for alert in alerts[:10]:  # Show top 10 alerts
                alert_data.append([
                    alert.created_at.strftime('%m/%d %H:%M') if alert.created_at else 'N/A',
                    alert.primary_entity[:30] if alert.primary_entity else 'N/A',
                    alert.severity.value if alert.severity else 'N/A',
                    alert.status.value if alert.status else 'N/A',
                    (alert.summary_text or '')[:50] + '...' if alert.summary_text and len(alert.summary_text) > 50 else alert.summary_text or ''
                ])

            alert_table = Table(alert_data, colWidths=[60, 80, 60, 60, 200])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(alert_table)

        # Footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=1
        )
        story.append(Paragraph("Generated by Vanguard Signal - Pre-Event Anomaly Detection", footer_style))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        filename = f"vanguard_report_{geo}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
