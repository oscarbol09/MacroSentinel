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


@pytest.mark.asyncio
async def test_treasury_client_fallback():
    """Verify Treasury client returns structured datapoints even when offline."""
    from macro_sentinel.extractors.treasury_client import TreasuryClient

    client = TreasuryClient()
    rates = await client.fetch_avg_interest_rates()
    assert rates.dataset == "avg_interest_rates"
    assert rates.latest_value > 0.0

    debt = await client.fetch_debt_to_penny()
    assert debt.dataset == "debt_to_penny"
    assert debt.latest_value > 1e12

    all_series = await client.fetch_all_registered_series()
    assert len(all_series) == 2
    assert all_series[0].meta.series_id == "TREASURY_AVG_RATE"
    assert all_series[1].meta.series_id == "TREASURY_DEBT"


@pytest.mark.asyncio
async def test_bls_client_fallback():
    """Verify BLS client returns structured observations for registered series."""
    from macro_sentinel.extractors.bls_client import BLSClient

    client = BLSClient()
    series_list = await client.fetch_series(["CUSR0000SA0", "CES0000000001"])
    assert len(series_list) == 2
    assert series_list[0].series_id == "CUSR0000SA0"
    assert series_list[0].latest_value > 0.0

    all_series = await client.fetch_all_registered_series()
    assert len(all_series) == 3
    sids = [s.meta.series_id for s in all_series]
    assert "CUSR0000SA0" in sids
    assert "CES0000000001" in sids


@pytest.mark.asyncio
async def test_cftc_client_fallback():
    """Verify CFTC client returns parsed leveraged money positioning."""
    from macro_sentinel.extractors.cftc_client import CFTCClient

    client = CFTCClient()
    positions = await client.fetch_positioning()
    assert len(positions) > 0
    assert positions[0].net_positioning is not None

    all_series = await client.fetch_all_registered_series()
    assert len(all_series) >= 2
    sids = [s.meta.series_id for s in all_series]
    assert "CFTC_UST_NET" in sids
    assert "CFTC_ES_NET" in sids


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

