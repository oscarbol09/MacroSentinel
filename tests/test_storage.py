"""Tests for SQLite persistence, deduplication, and report history."""

from macro_sentinel.analyzer.schemas import HawkishDovishTone, MacroPulseReportData, PolicyStance
from macro_sentinel.storage.sqlite_cache import SQLiteCache


def test_sqlite_cache_deduplication(tmp_path):
    """Verify that releases are correctly hashed and recognized as processed."""
    db_file = tmp_path / "test_sentinel.db"
    cache = SQLiteCache(db_path=db_file)

    url = "https://www.federalreserve.gov/statement/2026-09-22.htm"
    summary = "The Federal Open Market Committee decided to hold rates steady."
    content_hash = SQLiteCache.compute_content_hash(summary)

    # Initially not processed
    assert not cache.is_release_processed(url=url, content_hash=content_hash)

    # Mark processed
    cache.mark_release_processed(
        url=url,
        content_hash=content_hash,
        institution="Federal Reserve",
        title="FOMC Decision",
        published_date="2026-09-22",
    )

    # Should now be recognized
    assert cache.is_release_processed(url=url)
    assert cache.is_release_processed(url="", content_hash=content_hash)


def test_sqlite_report_history(tmp_path):
    """Verify report history persistence and score retrieval."""
    db_file = tmp_path / "test_sentinel.db"
    cache = SQLiteCache(db_path=db_file)

    report = MacroPulseReportData(
        report_id="MP-20260922-120000",
        generated_at="2026-09-22T12:00:00Z",
        executive_summary="Macro overview.",
        primary_regime="Late-Cycle Restrictive Stance",
        tone_assessment=HawkishDovishTone(
            score=0.35,
            stance=PolicyStance.HAWKISH,
            confidence=0.90,
            rationale="Hawkish remarks.",
        ),
    )

    dummy_path = tmp_path / "report.md"
    dummy_path.write_text("dummy", encoding="utf-8")

    cache.save_report(report, dummy_path)

    latest_score = cache.get_latest_tone_score()
    assert latest_score == 0.35

    recent = cache.get_recent_reports(limit=5)
    assert len(recent) == 1
    assert recent[0]["report_id"] == "MP-20260922-120000"
    assert recent[0]["stance"] == "Hawkish"
