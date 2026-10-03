"""Disposable real SQLite Research fixture; startup/restart never calls a model."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel import deep_analysis_activation  # noqa: E402
from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.runtime_composition import (
    _deep_analysis_production_capability,  # noqa: E402
)
from youtube_intel.state import SQLiteStateRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    worktree = Path(__file__).resolve().parents[2]
    root = args.root.resolve()
    if not root.is_relative_to(worktree / ".var" / "phase4"):
        raise ValueError("fixture root must be isolated inside Phase 4 worktree")
    root.mkdir(parents=True, exist_ok=True)
    support = _load_module("test_task022_personalized_distillation")
    authority = _load_module("test_v1x_phase1b_authority")
    database = root / "state.sqlite3"
    data = root / "data"
    if not database.exists():
        if any(root.iterdir()):
            raise ValueError("new fixture root must start empty")
        repo = authority.seed(root)
        source, video = support._source_and_video(repo)
        evidence = support._evidence(repo, video)
        artifact = repo.get_artifact(f"artifact-{video}-1000-1500")
        assert artifact is not None
        file = data / artifact.relative_path
        file.write_text("Fixture canonical evidence.")
        with repo._connect() as db:
            db.execute("UPDATE artifacts SET content_hash=? WHERE artifact_id=?", (hashlib.sha256(file.read_bytes()).hexdigest(), artifact.artifact_id))
        admitted = support._service(repo, support._FakeTransport(support._raw(evidence))).distill(support._command(source, video, evidence))
        assert admitted.intelligence_id is not None
        authority.activation._seed_content(repo, "no-material")
        with repo._connect() as db:
            db.execute("UPDATE videos SET title=? WHERE video_id='no-material'", ("No authoritative material " + "长标题 " * 30,))
    repo = SQLiteStateRepository(database)
    repo.initialize(now=authority.NOW)
    service = ProductOrchestrationService(repo, now=lambda: authority.NOW)
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    deep_analysis = authority.service(repo)
    deep_analysis._capability = _deep_analysis_production_capability()
    assert deep_analysis._capability.execution_route() is None
    app = LocalApiApplication(
        repo, service, data_root=data, now=lambda: authority.NOW,
        deep_analysis_service=deep_analysis,
        backup_restore_service=BackupRestoreService(database=database, data_root=data),
    )
    server = serve_loopback(app, port=args.port)
    info = {"port": server.server_port, "root": str(root)}
    (root / "browser-fixture.json").write_text(json.dumps(info))
    print(json.dumps(info), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
