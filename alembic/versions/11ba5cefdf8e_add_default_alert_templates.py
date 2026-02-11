"""add_default_alert_templates

Revision ID: 11ba5cefdf8e
Revises: c9309228e88c
Create Date: 2026-02-09 09:25:09.024733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11ba5cefdf8e'
down_revision: Union[str, None] = 'c9309228e88c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert default alert templates
    op.execute("""
    INSERT INTO alert.alert_template (
        created_at, updated_at, created_by, updated_by,
        name, description, subject_template, html_template, text_template,
        severity_filter, category_filter, is_default, is_system, enabled, template_metadata
    ) VALUES
    (
        NOW(), NOW(), 'system', 'system',
        'Critical Alert Template',
        'Default template for critical severity alerts',
        '[Vanguard Signal] 🚨 CRITICAL ALERT: {{primary_entity}}',
        '<!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
                .content { padding: 20px; }
                .alert-details { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .actions { text-align: center; margin-top: 30px; }
                .btn { display: inline-block; padding: 12px 24px; margin: 0 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }
                .btn-primary { background: #007bff; color: white; }
                .btn-secondary { background: #6c757d; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 CRITICAL ALERT</h1>
                    <h2>{{primary_entity}}</h2>
                </div>
                <div class="content">
                    <div class="alert-details">
                        <h3>Alert Details</h3>
                        <p><strong>Severity:</strong> {{severity|upper}}</p>
                        <p><strong>Confidence:</strong> {{confidence}}%</p>
                        <p><strong>Anomaly Score:</strong> {{anomaly_score}}</p>
                        <p><strong>Reason:</strong> {{reason_code}}</p>
                        <p><strong>Detected:</strong> {{detected_at}}</p>
                    </div>
                    <p><strong>Summary:</strong> {{summary_text}}</p>
                    <div class="actions">
                        <a href="{{dashboard_url}}" class="btn btn-primary">View in Dashboard</a>
                        <a href="{{acknowledge_url}}" class="btn btn-secondary">Acknowledge</a>
                    </div>
                </div>
            </div>
        </body>
        </html>',
        'VANGUARD SIGNAL - CRITICAL ALERT

Entity: {{primary_entity}}
Severity: {{severity|upper}}
Confidence: {{confidence}}%
Anomaly Score: {{anomaly_score}}
Reason: {{reason_code}}
Detected: {{detected_at}}

Summary: {{summary_text}}

View Dashboard: {{dashboard_url}}
Acknowledge: {{acknowledge_url}}

This is an automated alert from Vanguard Signal.',
        '["critical"]', NULL, true, true, true, NULL
    ),
    (
        NOW(), NOW(), 'system', 'system',
        'High Alert Template',
        'Default template for high severity alerts',
        '[Vanguard Signal] ⚠️ HIGH ALERT: {{primary_entity}}',
        '<!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background: #fd7e14; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
                .content { padding: 20px; }
                .alert-details { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .actions { text-align: center; margin-top: 30px; }
                .btn { display: inline-block; padding: 12px 24px; margin: 0 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }
                .btn-primary { background: #007bff; color: white; }
                .btn-secondary { background: #6c757d; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ HIGH ALERT</h1>
                    <h2>{{primary_entity}}</h2>
                </div>
                <div class="content">
                    <div class="alert-details">
                        <h3>Alert Details</h3>
                        <p><strong>Severity:</strong> {{severity|upper}}</p>
                        <p><strong>Confidence:</strong> {{confidence}}%</p>
                        <p><strong>Anomaly Score:</strong> {{anomaly_score}}</p>
                        <p><strong>Reason:</strong> {{reason_code}}</p>
                        <p><strong>Detected:</strong> {{detected_at}}</p>
                    </div>
                    <p><strong>Summary:</strong> {{summary_text}}</p>
                    <div class="actions">
                        <a href="{{dashboard_url}}" class="btn btn-primary">View in Dashboard</a>
                        <a href="{{acknowledge_url}}" class="btn btn-secondary">Acknowledge</a>
                    </div>
                </div>
            </div>
        </body>
        </html>',
        'VANGUARD SIGNAL - HIGH ALERT

Entity: {{primary_entity}}
Severity: {{severity|upper}}
Confidence: {{confidence}}%
Anomaly Score: {{anomaly_score}}
Reason: {{reason_code}}
Detected: {{detected_at}}

Summary: {{summary_text}}

View Dashboard: {{dashboard_url}}
Acknowledge: {{acknowledge_url}}

This is an automated alert from Vanguard Signal.',
        '["high"]', NULL, false, true, true, NULL
    ),
    (
        NOW(), NOW(), 'system', 'system',
        'Standard Alert Template',
        'Default template for medium and low severity alerts',
        '[Vanguard Signal] 📊 Alert: {{primary_entity}}',
        '<!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background: #17a2b8; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
                .content { padding: 20px; }
                .alert-details { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .actions { text-align: center; margin-top: 30px; }
                .btn { display: inline-block; padding: 12px 24px; margin: 0 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }
                .btn-primary { background: #007bff; color: white; }
                .btn-secondary { background: #6c757d; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 ALERT</h1>
                    <h2>{{primary_entity}}</h2>
                </div>
                <div class="content">
                    <div class="alert-details">
                        <h3>Alert Details</h3>
                        <p><strong>Severity:</strong> {{severity|upper}}</p>
                        <p><strong>Confidence:</strong> {{confidence}}%</p>
                        <p><strong>Anomaly Score:</strong> {{anomaly_score}}</p>
                        <p><strong>Reason:</strong> {{reason_code}}</p>
                        <p><strong>Detected:</strong> {{detected_at}}</p>
                    </div>
                    <p><strong>Summary:</strong> {{summary_text}}</p>
                    <div class="actions">
                        <a href="{{dashboard_url}}" class="btn btn-primary">View in Dashboard</a>
                        <a href="{{acknowledge_url}}" class="btn btn-secondary">Acknowledge</a>
                    </div>
                </div>
            </div>
        </body>
        </html>',
        'VANGUARD SIGNAL - ALERT

Entity: {{primary_entity}}
Severity: {{severity|upper}}
Confidence: {{confidence}}%
Anomaly Score: {{anomaly_score}}
Reason: {{reason_code}}
Detected: {{detected_at}}

Summary: {{summary_text}}

View Dashboard: {{dashboard_url}}
Acknowledge: {{acknowledge_url}}

This is an automated alert from Vanguard Signal.',
        '["medium", "low"]', NULL, false, true, true, NULL
    );
    """)


def downgrade() -> None:
    # Remove default alert templates
    op.execute("DELETE FROM alert.alert_template WHERE is_system = true")
