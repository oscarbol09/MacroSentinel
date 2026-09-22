"""Tests for FRED client and Central Bank extractors."""

import pytest
from macro_sentinel.config.series_registry import FRED_SERIES
from macro_sentinel.extractors.central_banks import CentralBankExtractor
from macro_sentinel.extractors.fred_client import FredClient


@pytest.mark.asyncio
async def test_fred_client_mock_mode():
    """Verify FredClient fallback works cleanly when no API key is set."""
    client = FredClient(api_key="your_fred_api_key_here")
    dp = await client.fetch_series_observations("T10Y2Y")

    assert dp.meta.series_id == "T10Y2Y"
    assert dp.latest_value is not None
    assert len(dp.observations) > 0


@pytest.mark.asyncio
async def test_central_bank_extractor():
    """Verify central bank extraction returns structured releases."""
    extractor = CentralBankExtractor()
    releases = await extractor.fetch_recent_releases(limit_per_source=1)

    assert len(releases) > 0
    first = releases[0]
    assert first.institution is not None
    assert first.title is not None
    assert first.summary is not None
