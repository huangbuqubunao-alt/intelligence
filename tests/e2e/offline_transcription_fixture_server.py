"""Phase 8 isolated HTTP/SQLite product fixture, no production model claim."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module
from offline_executor_fixture import ProcessFixtureExecutor

from youtube_intel import deep_analysis_activation
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.runtime_composition import _deep_analysis_production_capability
from youtube_intel.state import SQLiteStateRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5588)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "phase8")
    root.mkdir(parents=True, exist_ok=True)
    authority = _load_module("test_v1x_phase1b_authority")
    if not (root / "state.sqlite3").exists():
        repo = authority.seed(root)
        (root / "fixture.json").write_text(json.dumps({"content_id": authority.VIDEO}))
    backup = BackupRestoreService(
        database=root / "state.sqlite3", data_root=root / "data"
    )
    backup.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=authority.NOW)
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    da = authority.service(repo)
    da._capability = _deep_analysis_production_capability()
    assert da._capability.execution_route() is None
    executor = ProcessFixtureExecutor(root / "executor")
    jobs = LocalTranscriptionJobs(repo, root / "data", executor=executor)
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=root / "data",
        deep_analysis_service=da,
        backup_restore_service=backup,
        transcription_jobs=jobs,
    )
    server = serve_loopback(app, port=args.port)
    print(json.dumps({"port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
