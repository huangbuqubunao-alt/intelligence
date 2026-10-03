"""Isolated real-authority Diff fixture, restart and staged restore support."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel import deep_analysis_activation  # noqa: E402
from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.research_contract import ResearchRequest  # noqa: E402
from youtube_intel.research_lite import ResearchLiteService  # noqa: E402
from youtube_intel.runtime_composition import (
    _deep_analysis_production_capability,  # noqa: E402
)
from youtube_intel.state import SQLiteStateRepository  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5418)
    args = parser.parse_args()
    root = args.root.resolve()
    worktree = Path(__file__).resolve().parents[2]
    if not root.is_relative_to(worktree / ".var" / "phase6"):
        raise ValueError("fixture must remain inside Phase 6 worktree")
    root.mkdir(parents=True, exist_ok=True)
    support = _load_module("test_research_adversarial")
    if not (root / "state.sqlite3").exists():
        if any(root.iterdir()):
            raise ValueError("new fixture must be empty")
        fixture, repo, first, _ = support.admitted_packet(root)
        # The unit authority fixture supplies DB bindings; HTTP backup additionally
        # requires the exact referenced DATA bytes.
        (root / "data").mkdir()
        with repo._connect() as db:
            for row in db.execute("SELECT artifact_id,relative_path FROM artifacts WHERE storage_root='DATA'").fetchall():
                path = root / "data" / row["relative_path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Fixture canonical evidence.")
                db.execute("UPDATE artifacts SET content_hash=? WHERE artifact_id=?", (hashlib.sha256(path.read_bytes()).hexdigest(), row["artifact_id"]))
        helper = _load_module("test_research_diff")
        empty = helper.append_snapshot(repo, first, evidence=[], intelligence=[])
        current = helper.append_snapshot(repo, first)
        single = ResearchLiteService(repo, now=lambda: fixture.NOW).assemble(
            ResearchRequest(question="One canonical revision", content_ids=[c.content_id for c in first.packet.scope]), output_language="en")
        info = {"research_id": first.packet.research_id, "base": first.result_identity,
                "middle": empty.result_identity, "target": current.result_identity,
                "single": single.packet.research_id, "port": args.port}
        (root / "diff-fixture.json").write_text(json.dumps(info, indent=2))
    backup = BackupRestoreService(database=root / "state.sqlite3", data_root=root / "data")
    backup.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    authority = _load_module("test_v1x_phase1b_authority")
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    deep_analysis = authority.service(repo)
    deep_analysis._capability = _deep_analysis_production_capability()
    assert deep_analysis._capability.execution_route() is None
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=root / "data", backup_restore_service=backup, deep_analysis_service=deep_analysis)
    server = serve_loopback(app, port=args.port)
    print(json.dumps({"port": server.server_port, "root": str(root)}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
