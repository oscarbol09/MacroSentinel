"""Tests for LLMReasoner and ReportGenerator."""

import pytest
from macro_sentinel.analyzer.llm_reasoner import LLMReasoner
from macro_sentinel.config.series_registry import FRED_SERIES
from macro_sentinel.extractors.central_banks import CentralBankRelease
from macro_sentinel.extractors.fred_client import MacroDataPoint, SeriesObservation
from macro_sentinel.reports.generator import ReportGenerator


@pytest.mark.asyncio
async def test_analyzer_and_report_generation(tmp_path, monkeypatch):
    """Verify end-to-end reasoning and markdown report generation."""
    reasoner = LLMReasoner(model_name="mock-model")

    mock_datapoint = MacroDataPoint(
        meta=FRED_SERIES["T10Y2Y"],
        latest_value=-0.12,
        previous_value=-0.18,
        delta=0.06,
        delta_percentage=33.3,
        latest_date="2026-09-22",
        observations=[SeriesObservation(date="2026-09-22", value=-0.12)],
    )

    mock_release = CentralBankRelease(
        source_code="FED_FOMC",
        institution="Federal Reserve",
        title="FOMC Statement",
        link="https://federalreserve.gov",
        published_date="2026-09-22",
        summary="Inflation remains elevated. Rates maintained.",
    )

    report_data = await reasoner.analyze_and_synthesize([mock_datapoint], [mock_release])

    assert report_data.report_id.startswith("MP-")
    assert report_data.tone_assessment is not None
    assert -1.0 <= report_data.tone_assessment.score <= 1.0

    # Test report file generator
    generator = ReportGenerator()
    report_path = generator.generate_markdown_report(report_data, [mock_datapoint])
    assert report_path.exists()
    assert "MacroSentinel" in report_path.read_text(encoding="utf-8")
