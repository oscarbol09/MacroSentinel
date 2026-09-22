"""SQLite cache and persistence layer with WAL mode for MacroSentinel."""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..analyzer.schemas import MacroPulseReportData
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SQLiteCache:
    """Manages local SQLite database for feed deduplication and historical report indexing."""

    def __init__(self, db_path: Optional[Path] = None):
        settings = get_settings()
        self.db_path = db_path or (settings.data_storage_dir / "macrosentinel.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL mode and foreign key constraints enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema if not already present."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS processed_releases (
                    url TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    institution TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_date TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS report_history (
                    report_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    primary_regime TEXT NOT NULL,
                    tone_score REAL NOT NULL,
                    stance TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    report_path TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_releases_hash ON processed_releases (content_hash);
                CREATE INDEX IF NOT EXISTS idx_reports_generated ON report_history (generated_at DESC);
                """
            )

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Compute SHA-256 digest of clean statement text for deduplication."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def is_release_processed(self, url: str, content_hash: Optional[str] = None) -> bool:
        """Check if a central bank release has already been analyzed."""
        with self._get_connection() as conn:
            if url:
                row = conn.execute(
                    "SELECT 1 FROM processed_releases WHERE url = ?", (url,)
                ).fetchone()
                if row:
                    return True
            if content_hash:
                row = conn.execute(
                    "SELECT 1 FROM processed_releases WHERE content_hash = ?", (content_hash,)
                ).fetchone()
                if row:
                    return True
            return False

    def mark_release_processed(
        self,
        url: str,
        content_hash: str,
        institution: str,
        title: str,
        published_date: str,
    ) -> None:
        """Record release as processed in the database."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_releases 
                (url, content_hash, institution, title, published_date, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (url, content_hash, institution, title, published_date, now_iso),
            )

    def save_report(self, report_data: MacroPulseReportData, report_path: Path) -> None:
        """Store generated report metadata and raw structured JSON."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO report_history
                (report_id, generated_at, primary_regime, tone_score, stance, confidence, report_path, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_data.report_id,
                    report_data.generated_at,
                    report_data.primary_regime,
                    report_data.tone_assessment.score,
                    report_data.tone_assessment.stance.value,
                    report_data.tone_assessment.confidence,
                    str(report_path),
                    json.dumps(report_data.model_dump(), ensure_ascii=False),
                ),
            )

    def get_latest_tone_score(self) -> Optional[float]:
        """Fetch the most recent tone score for delta calculation."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT tone_score FROM report_history ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
            return row["tone_score"] if row else None

    def get_recent_reports(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent report records from storage."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT report_id, generated_at, primary_regime, tone_score, stance, confidence, report_path
                FROM report_history 
                ORDER BY generated_at DESC 
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
