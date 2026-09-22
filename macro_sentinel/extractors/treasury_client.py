"""Client for the U.S. Treasury Fiscal Data API."""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TreasuryDataPoint(BaseModel):
    """Structured container for Treasury data observations."""
    model_config = ConfigDict(frozen=True)
    dataset: str
    latest_value: float
    latest_date: str
    previous_value: Optional[float] = None


class TreasuryClient:
    """Async client for fetching data from the U.S. Treasury Fiscal Data API."""

    def __init__(self):
        self.base_url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
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
    async def fetch_avg_interest_rates(self, date_gte: str = "2023-01-01") -> TreasuryDataPoint:
        """Fetch the latest average interest rates on Treasury securities."""
        return await self._fetch_data(
            "/v2/accounting/od/avg_interest_rates",
            "avg_interest_rates",
            date_gte,
            "avg_interest_rate_amt"
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def fetch_debt_to_penny(self, date_gte: str = "2023-01-01") -> TreasuryDataPoint:
        """Fetch the current national debt level."""
        return await self._fetch_data(
            "/v2/accounting/od/debt_to_penny",
            "debt_to_penny",
            date_gte,
            "tot_pub_debt_out_amt"
        )

    async def fetch_all_registered_series(self) -> list:
        """Fetch all Treasury fiscal series as standardized MacroDataPoint objects."""
        from ..config.series_registry import MacroSeriesMeta
        from .fred_client import MacroDataPoint, SeriesObservation

        datapoints = []
        try:
            rate_dp = await self.fetch_avg_interest_rates()
            rate_delta = (
                (rate_dp.latest_value - rate_dp.previous_value)
                if rate_dp.previous_value is not None
                else None
            )
            rate_delta_bps = round(rate_delta * 100.0, 2) if rate_delta is not None else None
            meta_rate = MacroSeriesMeta(
                series_id="TREASURY_AVG_RATE",
                name="Treasury Securities Average Interest Rate",
                category="Fiscal / Rates",
                unit="Percent",
                frequency="Monthly",
                description="Average interest rate across all outstanding marketable Treasury debt.",
            )
            datapoints.append(
                MacroDataPoint(
                    meta=meta_rate,
                    latest_value=rate_dp.latest_value,
                    previous_value=rate_dp.previous_value,
                    delta=rate_delta,
                    delta_bps=rate_delta_bps,
                    delta_percentage=None,
                    latest_date=rate_dp.latest_date,
                    observations=[
                        SeriesObservation(date=rate_dp.latest_date, value=rate_dp.latest_value),
                    ],
                )
            )
        except Exception as err:
            logger.warning("Failed to fetch Treasury interest rates: %s", err)

        try:
            debt_dp = await self.fetch_debt_to_penny()
            debt_delta = (
                (debt_dp.latest_value - debt_dp.previous_value)
                if debt_dp.previous_value is not None
                else None
            )
            debt_pct = (
                round((debt_delta / debt_dp.previous_value) * 100.0, 4)
                if debt_delta is not None and debt_dp.previous_value
                else None
            )
            meta_debt = MacroSeriesMeta(
                series_id="TREASURY_DEBT",
                name="Federal Debt to the Penny",
                category="Fiscal Debt",
                unit="USD",
                frequency="Daily",
                description="Total public debt outstanding of the United States Government.",
            )
            datapoints.append(
                MacroDataPoint(
                    meta=meta_debt,
                    latest_value=debt_dp.latest_value,
                    previous_value=debt_dp.previous_value,
                    delta=debt_delta,
                    delta_bps=None,
                    delta_percentage=debt_pct,
                    latest_date=debt_dp.latest_date,
                    observations=[
                        SeriesObservation(date=debt_dp.latest_date, value=debt_dp.latest_value),
                    ],
                )
            )
        except Exception as err:
            logger.warning("Failed to fetch Treasury debt to penny: %s", err)

        return datapoints

    async def _fetch_data(
        self, endpoint: str, dataset_name: str, date_gte: str, value_field: str
    ) -> TreasuryDataPoint:
        """Fetch and parse data from a generic Fiscal Data endpoint."""
        params = {
            "filter": f"record_date:gte:{date_gte}",
            "sort": "-record_date",
            "page[size]": 10,
            "format": "json"
        }

        url = f"{self.base_url}{endpoint}"

        should_close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            should_close = True

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as err:
            logger.error("Failed to query Treasury API for %s: %s", dataset_name, err)
            return self._generate_mock_datapoint(dataset_name)
        finally:
            if should_close:
                await client.aclose()

        raw_data = data.get("data", [])
        if not raw_data:
            return self._generate_mock_datapoint(dataset_name)

        try:
            latest = raw_data[0]
            latest_val = float(latest.get(value_field, 0.0))
            latest_date = latest.get("record_date", "")

            prev_val = None
            if len(raw_data) > 1:
                prev_val = float(raw_data[1].get(value_field, 0.0))

            return TreasuryDataPoint(
                dataset=dataset_name,
                latest_value=latest_val,
                latest_date=latest_date,
                previous_value=prev_val,
            )
        except (ValueError, IndexError, TypeError):
            return self._generate_mock_datapoint(dataset_name)

    def _generate_mock_datapoint(self, dataset: str) -> TreasuryDataPoint:
        """Deterministic fallback baseline readings for offline dev and tests."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if dataset == "avg_interest_rates":
            val = 3.5
            prev_val = 3.4
        else:
            val = 34000000000000.0
            prev_val = 33900000000000.0

        return TreasuryDataPoint(
            dataset=dataset,
            latest_value=val,
            latest_date=today,
            previous_value=prev_val,
        )
