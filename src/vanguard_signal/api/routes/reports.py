"""
Reports API endpoints for scheduled report management.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api import deps
from vanguard_signal.schema.models import ScheduledReport, ReportTemplate

router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = logging.getLogger(__name__)


# Pydantic schemas for API
from pydantic import BaseModel


class ScheduledReportCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schedule_type: str  # 'daily', 'weekly', 'monthly'
    schedule_time: str  # '09:00' for daily, 'monday' for weekly, '1' for monthly
    timezone: str = 'UTC'
    report_type: str  # 'trends', 'alerts', 'correlation'
    geo: str = 'US'
    parameters: Optional[dict] = None
    email_recipients: List[str]
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class ScheduledReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    timezone: Optional[str] = None
    report_type: Optional[str] = None
    geo: Optional[str] = None
    parameters: Optional[dict] = None
    email_recipients: Optional[List[str]] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    is_active: Optional[bool] = None


class ReportTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: str  # 'trends', 'alerts', 'correlation'
    default_parameters: Optional[dict] = None
    email_subject_template: Optional[str] = None
    email_body_template: Optional[str] = None


class ReportTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[str] = None
    default_parameters: Optional[dict] = None
    email_subject_template: Optional[str] = None
    email_body_template: Optional[str] = None


class ReportTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    template_type: str
    default_parameters: Optional[dict]
    email_subject_template: Optional[str]
    email_body_template: Optional[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportShareRequest(BaseModel):
    template_id: int
    email_recipients: List[str]
    custom_parameters: Optional[dict] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class ScheduledReportResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    schedule_type: str
    schedule_time: str
    timezone: str
    report_type: str
    geo: str
    parameters: Optional[dict]
    email_recipients: List[str]
    email_subject: Optional[str]
    email_body: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_error: Optional[str]

    class Config:
        from_attributes = True


@router.post("/", response_model=ScheduledReportResponse)
async def create_scheduled_report(
    report: ScheduledReportCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Create a new scheduled report."""
    db_report = ScheduledReport(**report.model_dump())
    db.add(db_report)
    await db.flush()
    return db_report


@router.get("/", response_model=List[ScheduledReportResponse])
async def list_scheduled_reports(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """List all scheduled reports."""
    result = await db.execute(
        select(ScheduledReport).offset(skip).limit(limit)
    )
    reports = result.scalars().all()
    return reports


@router.get("/{report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    report_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Get a specific scheduled report."""
    report = await db.get(ScheduledReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.put("/{report_id}", response_model=ScheduledReportResponse)
async def update_scheduled_report(
    report_id: int,
    report_update: ScheduledReportUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Update a scheduled report."""
    report = await db.get(ScheduledReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    update_data = report_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)

    await db.flush()
    return report


@router.delete("/{report_id}")
async def delete_scheduled_report(
    report_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Delete a scheduled report."""
    report = await db.get(ScheduledReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)
    await db.flush()
    return {"message": "Report deleted successfully"}


@router.post("/{report_id}/run")
async def run_scheduled_report(
    report_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Manually trigger a scheduled report."""
    report = db.query(ScheduledReport).filter(ScheduledReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # TODO: Implement report generation logic
    # For now, just update the last_run_at
    report.last_run_at = datetime.now(timezone.utc)
    report.last_run_status = "success"
    db.commit()

    return {"message": "Report run triggered successfully"}


# Report Template Endpoints

@router.post("/templates/", response_model=ReportTemplateResponse)
async def create_report_template(
    template: ReportTemplateCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Create a new report template."""
    db_template = ReportTemplate(**template.model_dump())
    db.add(db_template)
    await db.flush()
    return db_template


@router.get("/templates/", response_model=List[ReportTemplateResponse])
async def list_report_templates(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """List all report templates."""
    result = await db.execute(
        select(ReportTemplate).offset(skip).limit(limit)
    )
    templates = result.scalars().all()
    return templates


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    template_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Get a specific report template."""
    template = await db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: int,
    template_update: ReportTemplateUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Update a report template."""
    template = await db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()
    return template


@router.delete("/templates/{template_id}")
async def delete_report_template(
    template_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Delete a report template."""
    template = await db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")

    await db.delete(template)
    await db.flush()
    return {"message": "Template deleted successfully"}


@router.post("/share")
async def share_report(
    share_request: ReportShareRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: str = Depends(deps.get_user_id),
):
    """Generate and share a report using a template via email."""
    # Get the template
    template = await db.get(ReportTemplate, share_request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Merge default parameters with custom ones
    parameters = template.default_parameters or {}
    if share_request.custom_parameters:
        parameters.update(share_request.custom_parameters)

    # Generate the report content based on template type
    try:
        content = await generate_report_content(db, template.template_type, parameters)
    except Exception as e:
        logger.error(f"Failed to generate report content: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    # For testing/development, skip actual email sending
    # TODO: Re-enable email sending when SMTP is configured
    logger.info(f"Report generated for template {template.name}, would send to {share_request.email_recipients}")

    # Uncomment when email is configured:
    # # Send email
    # from vanguard_signal.notifications.email import send_email
    #
    # await send_email(
    #     to_emails=share_request.email_recipients,
    #     subject=subject,
    #     body=body,
    #     attachments=[(f"{template.name.lower().replace(' ', '_')}_report.csv", content)]
    # )

    return {"message": "Report generated successfully (email sending disabled for testing)"}


async def generate_report_content(db: AsyncSession, report_type: str, parameters: dict) -> str:
    """Generate report content based on type and parameters."""
    import pandas as pd

    geo = parameters.get('geo', 'US')
    days = parameters.get('days', 7)

    if report_type == 'trends':
        from vanguard_signal.schema.models import TrendKeyword
        result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.geo == geo,
                TrendKeyword.total_appearances >= 1
            ).order_by(TrendKeyword.avg_rank).limit(100)
        )
        keywords = result.scalars().all()

        export_data = []
        for keyword in keywords:
            export_data.append({
                "Keyword": keyword.keyword,
                "Geo": keyword.geo,
                "First_Seen": keyword.first_seen.isoformat(),
                "Last_Seen": keyword.last_seen.isoformat(),
                "Total_Appearances": keyword.total_appearances,
                "Peak_Rank": keyword.peak_rank,
                "Average_Rank": keyword.avg_rank,
                "Current_Rank": keyword.current_rank,
            })

        df = pd.DataFrame(export_data)
        return df.to_csv(index=False)

    elif report_type == 'alerts':
        from vanguard_signal.schema.models import Alert
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(Alert).where(
                Alert.created_at >= cutoff_date
            ).order_by(Alert.created_at.desc())
        )
        alerts = result.scalars().all()

        export_data = []
        for alert in alerts:
            export_data.append({
                "ID": alert.id,
                "Primary_Entity": alert.primary_entity,
                "Severity": alert.severity.value if alert.severity else "",
                "Status": alert.status.value if alert.status else "",
                "Confidence_Score": alert.confidence_score,
                "Summary_Text": alert.summary_text,
                "Created_At": alert.created_at.isoformat(),
            })

        df = pd.DataFrame(export_data)
        return df.to_csv(index=False)

    elif report_type == 'correlation':
        # Placeholder for correlation report
        return "Correlation report not implemented yet"

    else:
        raise ValueError(f"Unknown report type: {report_type}")


async def check_and_run_scheduled_reports():
    """Background task to check for due scheduled reports and execute them."""
    while True:
        try:
            # Get database session
            from vanguard_signal.schema.database import get_session
            async with get_session() as db:
                now = datetime.now(timezone.utc)
                
                # Find reports that are due
                result = await db.execute(
                    select(ScheduledReport).where(
                        ScheduledReport.is_active == True,
                        ScheduledReport.next_run_at <= now
                    )
                )
                due_reports = result.scalars().all()
                
                for report in due_reports:
                    try:
                        await generate_and_send_report(db, report)
                        # Update next run time
                        report.last_run_at = now
                        report.last_run_status = "success"
                        report.next_run_at = calculate_next_run_time(report)
                        await db.commit()
                    except Exception as e:
                        report.last_run_at = now
                        report.last_run_status = "failed"
                        report.last_run_error = str(e)
                        await db.commit()
                        
        except Exception as e:
            # Log error but continue
            pass
        
        # Check every minute
        await asyncio.sleep(60)


def calculate_next_run_time(report: ScheduledReport) -> datetime:
    """Calculate the next run time based on schedule."""
    # Simple implementation - in a real system, use a proper scheduler
    now = datetime.now(timezone.utc)
    
    if report.schedule_type == 'daily':
        # Assume schedule_time is like '09:00'
        hour, minute = map(int, report.schedule_time.split(':'))
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_time <= now:
            next_time = next_time.replace(day=next_time.day + 1)
    elif report.schedule_type == 'weekly':
        # Assume schedule_time is day name like 'monday'
        # Simplified - just add 7 days
        next_time = now + timedelta(days=7)
    else:  # monthly
        # Assume schedule_time is day of month
        day = int(report.schedule_time)
        next_time = now.replace(day=day)
        if next_time <= now:
            if now.month == 12:
                next_time = next_time.replace(year=next_time.year + 1, month=1)
            else:
                next_time = next_time.replace(month=next_time.month + 1)
    
    return next_time


async def generate_and_send_report(db: AsyncSession, report: ScheduledReport):
    """Generate the report and send it via email."""
    import pandas as pd
    from io import BytesIO
    
    if report.report_type == 'trends':
        # Generate trends report
        from vanguard_signal.schema.models import TrendKeyword
        result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.geo == report.geo,
                TrendKeyword.total_appearances >= 1
            ).order_by(TrendKeyword.avg_rank).limit(100)
        )
        keywords = result.scalars().all()
        
        export_data = []
        for keyword in keywords:
            base_record = {
                "Keyword": keyword.keyword,
                "Geo": keyword.geo,
                "First_Seen": keyword.first_seen.isoformat(),
                "Last_Seen": keyword.last_seen.isoformat(),
                "Total_Appearances": keyword.total_appearances,
                "Peak_Rank": keyword.peak_rank,
                "Average_Rank": keyword.avg_rank,
                "Current_Rank": keyword.current_rank,
            }
            export_data.append(base_record)
        
        df = pd.DataFrame(export_data)
        content = df.to_csv(index=False)
        
    elif report.report_type == 'alerts':
        # Generate alerts report
        from vanguard_signal.schema.models import Alert
        result = await db.execute(
            select(Alert).where(
                Alert.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
            )
        )
        alerts = result.scalars().all()
        
        export_data = []
        for alert in alerts:
            export_data.append({
                "ID": alert.id,
                "Title": alert.title,
                "Severity": alert.severity,
                "Status": alert.status,
                "Created_At": alert.created_at.isoformat(),
                "Entity": alert.entity,
                "Value": alert.value,
                "Threshold": alert.threshold,
            })
        
        df = pd.DataFrame(export_data)
        content = df.to_csv(index=False)
        
    elif report.report_type == 'correlation':
        # Generate correlation report - simplified
        content = "Correlation report not implemented yet"
    else:
        raise ValueError(f"Unknown report type: {report.report_type}")
    
    # Send email
    from vanguard_signal.notifications.email import send_email
    
    subject = report.email_subject or f"{report.name} Report"
    body = report.email_body or f"Attached is your scheduled {report.report_type} report."
    
    await send_email(
        to_emails=report.email_recipients,
        subject=subject,
        body=body,
        attachments=[("report.csv", content)]
    )
