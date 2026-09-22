"""Tests for ChartEngine and headless matplotlib figure generation."""

from macro_sentinel.config.series_registry import FRED_SERIES
from macro_sentinel.extractors.fred_client import MacroDataPoint, SeriesObservation
from macro_sentinel.reports.charts import ChartEngine


def test_yield_curve_chart_generation(tmp_path):
    """Verify ChartEngine renders yield curve PNG with observations."""
    engine = ChartEngine(figures_dir=tmp_path)

    obs = [
        SeriesObservation(date="2026-01-01", value=-0.35),
        SeriesObservation(date="2026-03-01", value=-0.15),
        SeriesObservation(date="2026-06-01", value=0.05),
        SeriesObservation(date="2026-09-22", value=0.18),
    ]

    dp = MacroDataPoint(
        meta=FRED_SERIES["T10Y2Y"],
        latest_value=0.18,
        previous_value=0.05,
        delta=0.13,
        delta_bps=13.0,
        latest_date="2026-09-22",
        observations=obs,
    )

    chart_path = engine.generate_yield_curve_chart(dp, report_id="test_001")
    assert chart_path is not None
    assert chart_path.exists()
    assert chart_path.stat().st_size > 1000  # Valid non-empty PNG
