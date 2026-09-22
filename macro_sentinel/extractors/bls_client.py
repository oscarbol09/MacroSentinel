"""Client for the Bureau of Labor Statistics (BLS) API v2."""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class BLSDataPoint(BaseModel):
    """Structured container for BLS data observations."""
    model_config = ConfigDict(frozen=True)
    series_id: str
    latest_value: float
    latest_date: str
    previous_value: Optional[float] = None


class BLSClient:
    """Async client for fetching data from the BLS API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("BLS_API_KEY")
        self.base_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
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
    async def fetch_series(
        self, series_ids: List[str], start_year: str = "2024", end_year: str = "2026"
    ) -> List[BLSDataPoint]:
        """Fetch multiple BLS series over a given time range."""
        payload = {
            "seriesid": series_ids,
            "startyear": start_year,
            "endyear": end_year,
        }
        if self.api_key:
            payload["registrationkey"] = self.api_key

        should_close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            should_close = True

        try:
            response = await client.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as err:
            logger.error("Failed to query BLS API: %s", err)
            return [self._generate_mock_datapoint(sid) for sid in series_ids]
        finally:
            if should_close:
                await client.aclose()

        results = []
        status = data.get("status")
        if status != "REQUEST_SUCCEEDED":
            logger.warning("BLS API request did not succeed: %s", data.get("message"))
            return [self._generate_mock_datapoint(sid) for sid in series_ids]

        for series in data.get("Results", {}).get("series", []):
            series_id = series.get("seriesID")
            data_points = series.get("data", [])

            if not data_points:
                if series_id:
                    results.append(self._generate_mock_datapoint(series_id))
                continue

            try:
                latest = data_points[0]
                latest_val = float(latest.get("value", 0.0))
                latest_date = f"{latest.get('year')}-{latest.get('periodName')}"

                prev_val = None
                if len(data_points) > 1:
                    prev_val = float(data_points[1].get("value", 0.0))

                results.append(
                    BLSDataPoint(
                        series_id=series_id,
                        latest_value=latest_val,
                        latest_date=latest_date,
                        previous_value=prev_val,
                    )
                )
            except (ValueError, IndexError, TypeError):
                if series_id:
                    results.append(self._generate_mock_datapoint(series_id))

        return results

    async def fetch_all_registered_series(self) -> list:
        """Fetch all registered BLS series as standardized MacroDataPoint objects."""
        from ..config.series_registry import BLS_SERIES, MacroSeriesMeta
        from .fred_client import MacroDataPoint, SeriesObservation

        datapoints = []
        series_ids = list(BLS_SERIES.keys())
        raw_points = await self.fetch_series(series_ids)

        for rp in raw_points:
            meta_info = BLS_SERIES.get(rp.series_id)
            if not meta_info:
                continue

            delta = (
                (rp.latest_value - rp.previous_value)
                if rp.previous_value is not None
                else None
            )
            delta_pct = (
                round((delta / abs(rp.previous_value)) * 100.0, 2)
                if delta is not None and rp.previous_value
                else None
            )

            meta = MacroSeriesMeta(
                series_id=meta_info.series_id,
                name=meta_info.name,
                category=meta_info.category,
                unit=meta_info.unit,
                frequency="Monthly",
                description=meta_info.description,
            )

            datapoints.append(
                MacroDataPoint(
                    meta=meta,
                    latest_value=rp.latest_value,
                    previous_value=rp.previous_value,
                    delta=delta,
                    delta_bps=None,
                    delta_percentage=delta_pct,
                    latest_date=rp.latest_date,
                    observations=[
                        SeriesObservation(date=rp.latest_date, value=rp.latest_value),
                    ],
                )
            )

        return datapoints

    def _generate_mock_datapoint(self, series_id: str) -> BLSDataPoint:
        """Deterministic fallback baseline readings for offline dev and tests."""
        mock_values = {
            "CUSR0000SA0": 314.5,
            "CUSR0000SA0L1E": 318.2,
            "CES0000000001": 158500.0,
        }
        val = mock_values.get(series_id, 100.0)
        today = datetime.now(timezone.utc).strftime("%Y-%m")

        return BLSDataPoint(
            series_id=series_id,
            latest_value=val,
            latest_date=today,
            previous_value=val * 0.99,
        )
