"""Tests for LLMReasoner and ReportGenerator."""

import pytest
from macro_sentinel.analyzer.llm_reasoner import LLMReasoner
from macro_sentinel.analyzer.schemas import PolicyStance
from macro_sentinel.config.series_registry import FRED_SERIES
from macro_sentinel.extractors.central_banks import CentralBankRelease
from macro_sentinel.extractors.fred_client import MacroDataPoint, SeriesObservation
from macro_sentinel.reports.generator import ReportGenerator


@pytest.mark.asyncio
async def test_analyzer_inverted_curve_anomaly():
    """Verify reasoning flags high severity anomaly when yield curve is inverted."""
    reasoner = LLMReasoner(model_name="mock-model")

    mock_datapoint = MacroDataPoint(
        meta=FRED_SERIES["T10Y2Y"],
        latest_value=-0.25,
        previous_value=-0.15,
        delta=-0.10,
        delta_bps=-10.0,
        latest_date="2026-09-22",
        observations=[SeriesObservation(date="2026-09-22", value=-0.25)],
    )

    mock_release = CentralBankRelease(
        source_code="FED_FOMC",
        institution="Federal Reserve",
        title="FOMC Statement",
        link="https://federalreserve.gov",
        published_date="2026-09-22",
        summary="Inflation remains elevated. Committee keeps rates restrictive.",
    )

    report_data = await reasoner.analyze_and_synthesize([mock_datapoint], [mock_release])

    assert report_data.report_id.startswith("MP-")
    assert report_data.tone_assessment.stance == PolicyStance.HAWKISH
    assert -1.0 <= report_data.tone_assessment.score <= 1.0

    # Yield curve inversion should be flagged
    inversion_flag = next((a for a in report_data.anomalies if a.indicator == "T10Y2Y"), None)
    assert inversion_flag is not None
    assert inversion_flag.severity == "HIGH"
    assert "Inverted" in inversion_flag.title

    # Test report generator with basis points
    generator = ReportGenerator()
    report_path = generator.generate_markdown_report(report_data, [mock_datapoint])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "MacroSentinel" in content
    assert "bps" in content
