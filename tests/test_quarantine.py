"""Tests for Quarantine storage and dead letter queue."""

from macro_sentinel.storage.quarantine import QuarantineStore


def test_quarantine_store_lifecycle(tmp_path):
    """Verify storing, retrieving, and replaying quarantined extraction failures."""
    db_file = tmp_path / "test_quarantine.db"
    store = QuarantineStore(db_path=db_file)

    # Initially empty
    assert len(store.get_quarantined_items()) == 0

    # Record a failure
    store.quarantine_failure(
        source="FRED",
        error_msg="HTTP 503 Service Unavailable",
        traceback_str="Traceback (most recent call last)...",
        payload='{"series_id": "T10Y2Y"}',
    )

    items = store.get_quarantined_items()
    assert len(items) == 1
    assert items[0]["source"] == "FRED"
    assert "503" in items[0]["error_message"]

    # Filter by source
    assert len(store.get_quarantined_items(source="Treasury")) == 0
    assert len(store.get_quarantined_items(source="FRED")) == 1

    # Replay and clear
    item_id = items[0]["id"]
    store.replay_and_clear(item_id)
    assert len(store.get_quarantined_items()) == 0
