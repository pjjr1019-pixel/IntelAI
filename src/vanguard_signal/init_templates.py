"""
Initialize system report templates.
Run this script to create default report templates in the database.
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.models import ReportTemplate


async def create_system_templates():
    """Create default system report templates."""
    templates_data = [
        {
            "name": "Daily Trends Report",
            "description": "Daily summary of trending topics and keywords",
            "template_type": "trends",
            "default_parameters": {"geo": "US", "days": 1},
            "email_subject_template": "Daily Trends Report - {date}",
            "email_body_template": "Attached is your daily trends report for {geo} covering the last {days} day(s).",
            "is_system": True,
        },
        {
            "name": "Weekly Trends Report",
            "description": "Weekly summary of trending topics and keywords",
            "template_type": "trends",
            "default_parameters": {"geo": "US", "days": 7},
            "email_subject_template": "Weekly Trends Report - Week of {date}",
            "email_body_template": "Attached is your weekly trends report for {geo} covering the last {days} days.",
            "is_system": True,
        },
        {
            "name": "Monthly Trends Report",
            "description": "Monthly summary of trending topics and keywords",
            "template_type": "trends",
            "default_parameters": {"geo": "US", "days": 30},
            "email_subject_template": "Monthly Trends Report - {month} {year}",
            "email_body_template": "Attached is your monthly trends report for {geo} covering the last {days} days.",
            "is_system": True,
        },
        {
            "name": "Daily Alerts Report",
            "description": "Daily summary of anomaly alerts",
            "template_type": "alerts",
            "default_parameters": {"geo": "US", "days": 1},
            "email_subject_template": "Daily Alerts Report - {date}",
            "email_body_template": "Attached is your daily alerts report covering the last {days} day(s).",
            "is_system": True,
        },
        {
            "name": "Weekly Alerts Report",
            "description": "Weekly summary of anomaly alerts",
            "template_type": "alerts",
            "default_parameters": {"geo": "US", "days": 7},
            "email_subject_template": "Weekly Alerts Report - Week of {date}",
            "email_body_template": "Attached is your weekly alerts report covering the last {days} days.",
            "is_system": True,
        },
    ]

    async with get_session() as db:
        for template_data in templates_data:
            # Check if template already exists
            result = await db.execute(
                ReportTemplate.__table__.select().where(
                    ReportTemplate.name == template_data["name"]
                )
            )
            existing = result.first()
            if existing:
                print(f"Template '{template_data['name']}' already exists, skipping...")
                continue

            template = ReportTemplate(**template_data)
            db.add(template)
            print(f"Created template: {template.name}")

        await db.commit()
        print("System templates initialization complete!")


if __name__ == "__main__":
    asyncio.run(create_system_templates())