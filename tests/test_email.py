"""Tests for Email digest dispatcher."""

import pytest
from jinja2 import Template

from macro_sentinel.analyzer.schemas import (
    DialecticalArgument,
    HawkishDovishTone,
    MacroAnomalyFlag,
    MacroPulseReportData,
    PolicyStance,
    RegimeClassification,
)
from macro_sentinel.dispatchers.email import EMAIL_TEMPLATE, EmailDispatcher


@pytest.mark.asyncio
async def test_email_dispatcher_unconfigured_noop():
    """Verify EmailDispatcher safely no-ops when credentials are not configured."""
    dispatcher = EmailDispatcher()
    report = MacroPulseReportData(
        report_id="MP-20260922-001",
        generated_at="2026-09-22T12:00:00Z",
        executive_summary="Macro summary text.",
        primary_regime="Late-Cycle Disinflation",
        regime_classification=RegimeClassification.DISINFLATION,
        tone_assessment=HawkishDovishTone(
            score=0.15,
            stance=PolicyStance.HAWKISH,
            confidence=0.85,
            rationale="Rationale text.",
        ),
        dialectical_debate=[
            DialecticalArgument(
                stance="Hawkish",
                key_evidence=["Sticky services"],
                conclusion="Maintain restrictive rate",
            )
        ],
        anomalies=[
            MacroAnomalyFlag(
                indicator="T10Y2Y",
                severity="HIGH",
                title="Yield Curve Un-inversion",
                description="Late-cycle signal",
                data_source="FRED",
            )
        ],
    )

    # Should complete without error when unconfigured
    await dispatcher.send_macro_digest(report)


def test_email_template_rendering():
    """Verify Jinja2 email template renders all components cleanly."""
    report = MacroPulseReportData(
        report_id="MP-TEST-123",
        generated_at="2026-09-22T15:30:00Z",
        executive_summary="Strong labor market with sticky inflation pressures.",
        primary_regime="Late-Cycle Restrictive Stance",
        regime_classification=RegimeClassification.STAGFLATION,
        tone_assessment=HawkishDovishTone(
            score=0.45,
            stance=PolicyStance.HAWKISH,
            confidence=0.92,
            rationale="Persistent inflation mandates prolonged restrictive rates.",
        ),
        anomalies=[
            MacroAnomalyFlag(
                indicator="UNRATE",
                severity="HIGH",
                title="Sahm Rule Warning",
                description="Unemployment ticked up to 4.3%",
                data_source="FRED",
                historical_precedent="Historical trigger for recessionary cycle.",
            )
        ],
        cross_asset_implications=["Equities under pressure", "Yield steepener attractive"],
        actionable_watchpoints=["Upcoming Core PCE print"],
    )

    template = Template(EMAIL_TEMPLATE)
    html = template.render(report=report)

    assert "MacroSentinel: Intelligence Digest" in html
    assert "MP-TEST-123" in html
    assert "Late-Cycle Restrictive Stance" in html
    assert "Sahm Rule Warning" in html
    assert "Equities under pressure" in html
    assert "Upcoming Core PCE print" in html
