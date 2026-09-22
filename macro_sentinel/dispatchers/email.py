"""Email digest dispatcher for Macro Pulse alerts."""

import logging
from typing import Optional

from jinja2 import Template

from ..analyzer.schemas import MacroPulseReportData
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Basic HTML template using inline CSS suitable for email clients
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #0056b3; padding-bottom: 10px; margin-bottom: 20px; }
        .title { color: #0056b3; margin: 0; }
        .timestamp { color: #666666; font-size: 0.9em; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em; margin-bottom: 10px; }
        .badge-regime { background-color: #e0f2fe; color: #0284c7; }
        .tone-indicator { margin: 15px 0; padding: 10px; border-radius: 4px; background-color: #f8f9fa; border-left: 4px solid #0056b3; }
        .card { background-color: #fff3f3; border: 1px solid #ffcdd2; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
        .card-high { border-left: 4px solid #d32f2f; }
        .card-med { border-left: 4px solid #f57c00; background-color: #fff8e1; border-color: #ffe082; }
        h3 { color: #2c3e50; margin-top: 25px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        ul { padding-left: 20px; }
        li { margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">MacroSentinel: Intelligence Digest</h1>
        <div class="timestamp">Generated: {{ report.generated_at }} | ID: {{ report.report_id }}</div>
    </div>

    <div>
        <span class="badge badge-regime">Regime: {{ report.primary_regime }}</span>
    </div>

    <div class="tone-indicator">
        <strong>Central Bank Stance:</strong> {{ report.tone_assessment.stance.value }}
        (Score: {{ "%.2f"|format(report.tone_assessment.score) }}, Confidence: {{ "%.0f"|format(report.tone_assessment.confidence * 100) }}%)
        <br>
        <small>{{ report.tone_assessment.rationale }}</small>
    </div>

    <h3>Executive Summary</h3>
    <p>{{ report.executive_summary }}</p>

    {% if report.anomalies %}
    <h3>Anomalies & Risks</h3>
    {% for anomaly in report.anomalies %}
        <div class="card {% if anomaly.severity in ['HIGH', 'CRITICAL'] %}card-high{% else %}card-med{% endif %}">
            <strong>{{ anomaly.title }}</strong> ({{ anomaly.indicator }})
            <p style="margin: 5px 0;">{{ anomaly.description }}</p>
            {% if anomaly.historical_precedent %}
            <small><em>Precedent: {{ anomaly.historical_precedent }}</em></small>
            {% endif %}
        </div>
    {% endfor %}
    {% endif %}

    {% if report.cross_asset_implications %}
    <h3>Cross-Asset Implications</h3>
    <ul>
    {% for item in report.cross_asset_implications %}
        <li>{{ item }}</li>
    {% endfor %}
    </ul>
    {% endif %}

    {% if report.actionable_watchpoints %}
    <h3>Watchpoints</h3>
    <ul>
    {% for item in report.actionable_watchpoints %}
        <li>{{ item }}</li>
    {% endfor %}
    </ul>
    {% endif %}
</body>
</html>
"""

class EmailDispatcher:
    """Dispatches executive summaries via email using the Resend API."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.resend_api_key
        self.recipient = self.settings.alert_email_recipient

    async def send_macro_digest(self, report: MacroPulseReportData, macro_data: Optional[list] = None) -> None:
        """Send a formatted HTML email digest containing the report data."""
        if not self.api_key or not self.recipient:
            logger.info("Email dispatcher not configured (missing resend api key or recipient). Skipping.")
            return

        try:
            import resend

            resend.api_key = self.api_key
            template = Template(EMAIL_TEMPLATE)
            html_content = template.render(report=report)

            subject = f"🦅 MacroSentinel Alert: {report.primary_regime} Regime Detected"

            params = {
                "from": "MacroSentinel <onboarding@resend.dev>",
                "to": [self.recipient],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)
            logger.info("Email digest successfully dispatched. ID: %s", response.get("id"))

        except Exception as e:
            logger.error("Failed to send email digest: %s", e, exc_info=True)
