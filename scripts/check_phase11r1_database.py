"""Task-local database verification for Phase 11R.1.

Creates a fresh database through the normal migration path and reports the
three PRAGMA checks plus the schema version.  Nothing here changes the schema:
the point is to prove schema 34 is intact and no migration was introduced.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from youtube_intel.backup_restore import LATEST_SCHEMA_VERSION  # noqa: E402
from youtube_intel.state import SQLiteStateRepository  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        repository = SQLiteStateRepository(root / "state.db")
        version = repository.initialize(now=datetime(2026, 10, 6, tzinfo=timezone.utc))
        connection = sqlite3.connect(root / "state.db")
        try:
            report = {
                "schema_version_reported": int(version.version),
                "schema_version_expected": LATEST_SCHEMA_VERSION,
                "quick_check": [row[0] for row in connection.execute("PRAGMA quick_check")],
                "integrity_check": [row[0] for row in connection.execute("PRAGMA integrity_check")],
                "foreign_key_check": [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")],
                "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
                "applied_migrations": connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
            }
        finally:
            connection.close()
    report["schema_matches"] = report["schema_version_reported"] == LATEST_SCHEMA_VERSION
    report["ok"] = (
        report["schema_matches"]
        and report["quick_check"] == ["ok"]
        and report["integrity_check"] == ["ok"]
        and report["foreign_key_check"] == []
        and report["user_version"] == LATEST_SCHEMA_VERSION
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())