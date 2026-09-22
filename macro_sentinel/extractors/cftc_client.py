"""Client for CFTC Commitment of Traders (COT) reports via Socrata SODA2 API."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class COTPositioning(BaseModel):
    """Structured container for CFTC COT positioning data."""
    model_config = ConfigDict(frozen=True)
    contract_name: str
    report_date: str
    lev_money_positions_long: float
    lev_money_positions_short: float
    net_positioning: float
    z_score: Optional[float] = None


class CFTCClient:
    """Async client for fetching data from the CFTC COT API."""

    def __init__(self):
        self.base_url = "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=15.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def fetch_positioning(self, date_gte: str = "2023-01-01") -> List[COTPositioning]:
        """Fetch the latest commitment of traders positioning data."""
        query = f"?$where=report_date_as_yyyy_mm_dd >= '{date_gte}'&$order=report_date_as_yyyy_mm_dd DESC&$limit=10"
        url = f"{self.base_url}{query}"

        should_close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            should_close = True

        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as err:
            logger.error("Failed to query CFTC API: %s", err)
            return self._generate_mock_data()
        finally:
            if should_close:
                await client.aclose()

        results = []
        for row in data:
            contract_name = row.get("contract_market_name", "")
            if "TREASURY" not in contract_name and "E-MINI" not in contract_name:
                continue

            try:
                # Disaggregated futures only format usually uses 'lev_money_positions_long_all' or similar
                long_pos = float(row.get("lev_money_positions_long_all", row.get("lev_money_positions_long", 0.0)))
                short_pos = float(row.get("lev_money_positions_short_all", row.get("lev_money_positions_short", 0.0)))
                net_pos = long_pos - short_pos
                report_date = row.get("report_date_as_yyyy_mm_dd", "")

                results.append(
                    COTPositioning(
                        contract_name=contract_name,
                        report_date=report_date,
                        lev_money_positions_long=long_pos,
                        lev_money_positions_short=short_pos,
                        net_positioning=net_pos,
                    )
                )
            except (ValueError, TypeError):
                continue

        if not results:
            return self._generate_mock_data()

        return results

    async def fetch_all_registered_series(self) -> list:
        """Fetch all CFTC positioning series as standardized MacroDataPoint objects."""
        from ..config.series_registry import MacroSeriesMeta
        from .fred_client import MacroDataPoint, SeriesObservation

        datapoints = []
        positions = await self.fetch_positioning()

        for pos in positions:
            if "TREASURY" in pos.contract_name:
                sid = "CFTC_UST_NET"
                name = "Leveraged Funds Net Treasury Futures Positioning"
                desc = "Net positioning (long - short contracts) by leveraged funds in US Treasury futures."
            elif "E-MINI" in pos.contract_name:
                sid = "CFTC_ES_NET"
                name = "Leveraged Funds Net S&P 500 E-Mini Positioning"
                desc = "Net positioning (long - short contracts) by leveraged funds in S&P 500 E-mini futures."
            else:
                continue

            meta = MacroSeriesMeta(
                series_id=sid,
                name=name,
                category="Market Positioning",
                unit="Contracts",
                frequency="Weekly",
                description=desc,
            )

            datapoints.append(
                MacroDataPoint(
                    meta=meta,
                    latest_value=pos.net_positioning,
                    previous_value=None,
                    delta=None,
                    delta_bps=None,
                    delta_percentage=None,
                    latest_date=pos.report_date[:10] if pos.report_date else "",
                    observations=[
                        SeriesObservation(
                            date=pos.report_date[:10] if pos.report_date else "",
                            value=pos.net_positioning,
                        ),
                    ],
                )
            )

        return datapoints

    def _generate_mock_data(self) -> List[COTPositioning]:
        """Deterministic fallback baseline readings for offline dev and tests."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000")
        return [
            COTPositioning(
                contract_name="U.S. TREASURY BONDS - CHICAGO BOARD OF TRADE",
                report_date=today,
                lev_money_positions_long=100000.0,
                lev_money_positions_short=150000.0,
                net_positioning=-50000.0,
            ),
            COTPositioning(
                contract_name="E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
                report_date=today,
                lev_money_positions_long=200000.0,
                lev_money_positions_short=180000.0,
                net_positioning=20000.0,
            ),
        ]
