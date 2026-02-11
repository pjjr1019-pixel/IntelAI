"""
Report models for scheduled report generation and delivery.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship

from ..base import Base


class ScheduledReport(Base):
    """
    Scheduled report configuration for automated report generation and delivery.
    """
    __tablename__ = "scheduled_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Schedule configuration
    schedule_type = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'
    schedule_time = Column(String(50), nullable=False)  # '09:00' for daily, 'monday' for weekly, '1' for monthly
    timezone = Column(String(50), nullable=False, default='UTC')

    # Report configuration
    report_type = Column(String(50), nullable=False)  # 'trends', 'alerts', 'correlation'
    geo = Column(String(5), nullable=False, default='US')
    parameters = Column(JSON, nullable=True)  # Additional parameters like days, format, etc.

    # Delivery configuration
    email_recipients = Column(JSON, nullable=False)  # List of email addresses
    email_subject = Column(String(255), nullable=True)
    email_body = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Execution tracking
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(50), nullable=True)  # 'success', 'failed'
    last_run_error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ScheduledReport(id={self.id}, name='{self.name}', schedule_type='{self.schedule_type}')>"


class ReportTemplate(Base):
    """
    Predefined report templates with customizable parameters.
    """
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)  # 'trends', 'alerts', 'correlation'

    # Template configuration
    default_parameters = Column(JSON, nullable=True)
    email_subject_template = Column(String(255), nullable=True)
    email_body_template = Column(Text, nullable=True)

    # Metadata
    is_system = Column(Boolean, nullable=False, default=False)  # System templates vs user-created
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, name='{self.name}', template_type='{self.template_type}')>"