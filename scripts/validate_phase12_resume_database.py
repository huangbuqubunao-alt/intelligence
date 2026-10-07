"""Offline integrity and exact portable-authority drill on an isolated fixture DB."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.following_tracking import verify_tracking
from youtube_intel.state import SQLiteStateRepository


def snapshot(root):
    repo = SQLiteStateRepository(root / "state.sqlite")
    repo.bind_source_storage(root / "data")
    with repo._connect() as connection:
        health = {name: [list(row) for row in connection.execute("PRAGMA " + name)] for name in ("quick_check", "integrity_check", "foreign_key_check")}
        assert health == {"quick_check": [["ok"]], "integrity_check": [["ok"]], "foreign_key_check": []}
        checks = {
            "duplicate_sources": "SELECT provider,canonical_url FROM source_subscriptions GROUP BY provider,canonical_url HAVING COUNT(*)>1",
            "duplicate_content": "SELECT provider,video_id FROM videos GROUP BY provider,video_id HAVING COUNT(*)>1",
            "orphan_links": "SELECT l.source_id FROM source_video_links l LEFT JOIN source_subscriptions s USING(source_id) LEFT JOIN videos v USING(video_id) WHERE s.source_id IS NULL OR v.video_id IS NULL",
            "orphan_checks": "SELECT c.check_id FROM source_checks c LEFT JOIN source_subscriptions s USING(source_id) WHERE s.source_id IS NULL",
            "orphan_runs": "SELECT r.run_id FROM source_runs r LEFT JOIN source_subscriptions s USING(source_id) WHERE s.source_id IS NULL",
            "false_baseline_success": "SELECT s.source_id FROM source_subscriptions s JOIN source_tracking_state t USING(source_id) WHERE (t.verified_at IS NOT NULL OR s.last_success_at IS NOT NULL) AND t.baseline_at IS NULL",
            "active_checks": "SELECT check_id FROM source_checks WHERE status='RUNNING'",
            "active_runs": "SELECT run_id FROM source_runs WHERE state IN ('QUEUED','RUNNING','WAITING','PARTIAL')",
        }
        issues = {key: [list(row) for row in connection.execute(sql)] for key, sql in checks.items()}
        assert all(not value for value in issues.values()), issues
        tracked = [row[0] for row in connection.execute("SELECT source_id FROM source_tracking_state")]
        for source_id in tracked:
            verify_tracking(connection, source_id, repository=repo)
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        digests = {}
        counts = {}
        for table in tables:
            # Names originate from our schema, not provider/user input.
            assert table.replace('_', '').isalnum()
            rows = sorted(tuple(row) for row in connection.execute('SELECT * FROM "' + table + '"')) if table == "schema_migrations" else sorted(repr(tuple(row)) for row in connection.execute('SELECT * FROM "' + table + '"'))
            digests[table] = hashlib.sha256(repr(rows).encode()).hexdigest()
            counts[table] = len(rows)
        return {"schema": connection.execute("PRAGMA user_version").fetchone()[0], "pragmas": health, "issues": issues, "tracked_sources": tracked, "source_states": [dict(row) for row in connection.execute("SELECT s.source_id,s.provider,s.enabled,t.baseline_at,t.verified_at,t.health FROM source_subscriptions s JOIN source_tracking_state t USING(source_id) ORDER BY s.source_id")], "table_sha256": digests, "table_counts": counts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[1] / ".var/phase12")
    before = snapshot(root)
    output = {"kind": "FIXTURE/REPLAY", "before": before, "provider_network_used": False}
    if args.restore:
        service = BackupRestoreService(database=root / "state.sqlite", data_root=root / "data")
        assert service.readiness()["ready"]
        created = service.create_backup()
        archive, _ = service.backup_download(created.backup_id)
        staged = service.stage_restore(archive.read_bytes())
        service.confirm_restore(staged.restore_id)
        service.recover_and_apply_pending_restore()
        after = snapshot(root)
        assert before == after
        output.update({"after": after, "all_authority_tables_exactly_restored": True, "backup_id": created.backup_id})
    migrations = []
    for path in sorted(Path('src/youtube_intel/migrations').glob('*.sql')):
        data = path.read_bytes()
        for baseline in ('4d0cb5e5', '8ebdf282'):
            assert data == subprocess.check_output(['git', 'show', baseline + ':' + str(path)])
        migrations.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
    output["unchanged_historical_migrations"] = migrations
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
