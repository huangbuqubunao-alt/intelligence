"""Bounded public-only Phase 12 smoke; no credentials, cookies or model calls."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.following_tracking import FollowingTrackingService
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.providers.youtube_channel import YouTubeFollowingProvider
from youtube_intel.state import SQLiteStateRepository


def main():
    with tempfile.TemporaryDirectory(prefix="intelligence-phase12-public-") as directory:
        root = Path(directory).resolve()
        repo = SQLiteStateRepository(root / "state.sqlite")
        repo.initialize(now=datetime.now(UTC))
        data_root = root / "data"
        data_root.mkdir()
        tracker = FollowingTrackingService(repo, BilibiliContentProvider(repo, data_root), youtube=YouTubeFollowingProvider())
        backup = BackupRestoreService(database=root / "state.sqlite", data_root=data_root)
        app = LocalApiApplication(repo, ProductOrchestrationService(repo, source_tracking=tracker), source_tracking=tracker, data_root=data_root, backup_restore_service=backup)
        attempts = []
        # Two nonpersonal public channels; no retry and no historical enrollment.
        for handle in ("@NASA", "@GoogleDevelopers"):
            started = datetime.now(UTC).isoformat()
            try:
                status, result = app.handle("POST", "/api/v1/sources/channels", json.dumps({"input": handle}).encode())
            except ApiError as error:
                status, result = error.status, {"error": {"code": error.code, "message": str(error)}}
            attempt = {"kind": "REAL", "input": handle, "started_at": started, "status": status, "result": result}
            if status == 200:
                source_id = result["source"]["source_id"]
                attempt["source_detail"] = app.handle("GET", "/api/v1/sources/" + source_id)[1]
                attempt["immediate_check"] = app.handle("POST", "/api/v1/sources/" + source_id + "/check", b'{"command_id":"real-immediate"}')[1]
                assert repo.list_videos() == ()
                reopened = SQLiteStateRepository(root / "state.sqlite")
                reopened.bind_source_storage(data_root)
                attempt["restart_source"] = reopened.get_source_subscription(source_id).source_id
            attempts.append(attempt)
            error = result.get("error", {}).get("code", "")
            if any(category in error for category in ("RATE_LIMITED", "RISK_CONTROLLED", "ACCESS_DENIED")):
                break
        with repo._connect() as connection:
            health = {name: [list(row) for row in connection.execute("PRAGMA " + name)] for name in ("quick_check", "integrity_check", "foreign_key_check")}
        bundle = backup.create_backup()
        output = {"attempts": attempts, "database_health": health, "backup_created": bool(bundle), "historical_content_count": len(repo.list_videos()), "cookies": False, "login": False, "models": False, "real_success_claimed": any(a["status"] == 200 and a["result"]["source"]["tracking"]["baseline_at"] is not None for a in attempts)}
        print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
