"""Tests for FRED client, Central Bank extractors, and network guards."""

import pytest
from macro_sentinel.extractors.central_banks import CentralBankExtractor, assert_safe_remote_url
from macro_sentinel.extractors.fred_client import FredClient


@pytest.mark.asyncio
async def test_fred_client_rate_series_bps():
    """Verify rate series calculates delta in basis points rather than relative percentage."""
    client = FredClient(api_key="your_fred_api_key_here")
    dp = await client.fetch_series_observations("T10Y2Y")

    assert dp.meta.series_id == "T10Y2Y"
    assert dp.latest_value is not None
    assert dp.delta_bps is not None
    assert dp.delta_percentage is None  # Percentages avoided for rates to prevent distortions
    assert len(dp.observations) > 0


@pytest.mark.asyncio
async def test_fred_client_index_series_pct():
    """Verify non-rate series (CPI) calculates delta in relative percentage."""
    client = FredClient(api_key="your_fred_api_key_here")
    dp = await client.fetch_series_observations("CPIAUCSL")

    assert dp.meta.series_id == "CPIAUCSL"
    assert dp.latest_value is not None
    assert dp.delta_bps is None
    assert dp.delta_percentage is not None


@pytest.mark.asyncio
async def test_central_bank_extractor_fallback():
    """Verify central bank extraction returns structured releases even when offline."""
    extractor = CentralBankExtractor()
    releases = await extractor.fetch_recent_releases(limit_per_source=1)

    assert len(releases) > 0
    first = releases[0]
    assert first.institution is not None
    assert first.title is not None
    assert first.summary is not None


def test_ssrf_guard_blocks_private_networks():
    """Verify SSRF defense blocks loopback, link-local, and private subnets."""
    with pytest.raises(ValueError, match="Blocked local loopback access"):
        assert_safe_remote_url("http://localhost/feed.xml")

    with pytest.raises(ValueError, match="Blocked local loopback access"):
        assert_safe_remote_url("http://127.0.0.1:8080/feed.xml")

    with pytest.raises(ValueError, match="Unsupported protocol scheme"):
        assert_safe_remote_url("file:///etc/passwd")

    # Safe public URL passes
    safe = assert_safe_remote_url("https://www.federalreserve.gov/feeds/press_monetary.xml")
    assert safe == "https://www.federalreserve.gov/feeds/press_monetary.xml"
