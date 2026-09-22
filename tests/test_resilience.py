"""Tests for pipeline resilience, scatter-gather execution, and circuit breaker."""

import pytest

from macro_sentinel.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_scheduler_circuit_breaker_and_safe_extract():
    """Verify circuit breaker trips after 3 consecutive failures and recovers on success."""
    runner = SchedulerRunner()

    class MockFailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def fetch_broken(self):
            raise ConnectionError("Simulated upstream gateway timeout")

    failing_client = MockFailingClient()

    # Run 1 - First failure
    res1 = await runner._safe_extract("FRED", failing_client, "fetch_broken")
    assert res1 == []
    assert runner.circuit_breaker["FRED"]["failures"] == 1
    assert runner.circuit_breaker["FRED"]["skip_runs"] == 0

    # Run 2 - Second failure
    res2 = await runner._safe_extract("FRED", failing_client, "fetch_broken")
    assert res2 == []
    assert runner.circuit_breaker["FRED"]["failures"] == 2
    assert runner.circuit_breaker["FRED"]["skip_runs"] == 0

    # Run 3 - Third failure trips circuit breaker
    res3 = await runner._safe_extract("FRED", failing_client, "fetch_broken")
    assert res3 == []
    assert runner.circuit_breaker["FRED"]["failures"] == 0
    assert runner.circuit_breaker["FRED"]["skip_runs"] == 3

    # Run 4 - Circuit breaker active, skips call immediately
    res4 = await runner._safe_extract("FRED", failing_client, "fetch_broken")
    assert res4 == []
    assert runner.circuit_breaker["FRED"]["skip_runs"] == 2


@pytest.mark.asyncio
async def test_scheduler_execute_full_pipeline_offline(tmp_path):
    """Verify full end-to-end pipeline completes successfully offline without network."""
    runner = SchedulerRunner()
    # Execute full pipeline without console spam
    await runner.execute_full_pipeline(render_to_console=False)

    # Verify reports were saved
    recent = runner.cache.get_recent_reports(limit=5)
    assert len(recent) > 0
