"""SQLite-based quarantine storage for failed data extractions."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class QuarantineStore:
    """Manages a local SQLite dead letter queue for failed pipeline extractions."""

    def __init__(self, db_path: Optional[Path] = None):
        settings = get_settings()
        self.db_path = db_path or (settings.data_storage_dir / "macrosentinel.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize quarantine table if not already present."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pipeline_quarantine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    error_traceback TEXT,
                    payload TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                """
            )

    def quarantine_failure(
        self,
        source: str,
        error_msg: str,
        traceback_str: str,
        payload: Optional[str] = None
    ) -> None:
        """Insert a failed extraction record into the quarantine table."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_quarantine
                (source, error_message, error_traceback, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source, error_msg, traceback_str, payload, now_iso),
            )
        logger.info(f"Quarantined failure for source: {source}")

    def get_quarantined_items(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve quarantined items, optionally filtered by source."""
        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "SELECT * FROM pipeline_quarantine WHERE source = ? AND resolved_at IS NULL ORDER BY created_at ASC",
                    (source,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM pipeline_quarantine WHERE resolved_at IS NULL ORDER BY created_at ASC"
                )
            return [dict(row) for row in cursor.fetchall()]

    def replay_and_clear(self, item_id: int) -> None:
        """Delete a successfully replayed item from the quarantine."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM pipeline_quarantine WHERE id = ?", (item_id,))
        logger.info(f"Cleared quarantined item id: {item_id}")
