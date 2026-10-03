"""One isolated product database with DA, Evidence and three Research revisions."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel import deep_analysis_activation  # noqa: E402
from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.model_settings import ModelSettingsService  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.runtime_composition import (
    _deep_analysis_production_capability,  # noqa: E402
)
from youtube_intel.state import SQLiteStateRepository  # noqa: E402


class FixtureCredentialStore:
    secret = None

    def get(self):
        return self.secret

    def save(self, secret):
        self.secret = secret

    def delete(self):
        self.secret = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5492)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "closure"):
        raise ValueError("closure fixture must remain isolated")
    root.mkdir(parents=True, exist_ok=True)
    authority = _load_module("test_v1x_phase1b_authority")
    research = _load_module("test_research_lite")
    delta = _load_module("test_v1x_knowledge_delta")
    if not (root / "state.sqlite3").exists():
        if any(root.iterdir()):
            raise ValueError("new fixture must start empty")
        repo = authority.seed(root)
        da = authority.service(repo).run(content_id=authority.VIDEO)
        revisions = [research.run(repo) for _ in range(3)]
        delta.content(repo, "closure-recent", delta.NOW)
        info = {"content_id": authority.VIDEO, "da": da.result_identity,
                "research_id": revisions[0].packet.research_id,
                "revisions": [r.result_identity for r in revisions]}
        (root / "fixture.json").write_text(json.dumps(info, indent=2))
    backup = BackupRestoreService(database=root / "state.sqlite3", data_root=root / "data")
    backup.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=authority.NOW)
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    da_service = authority.service(repo)
    da_service._capability = _deep_analysis_production_capability()
    assert da_service._capability.execution_route() is None
    vault = root / "external-vault" / "Knowledge"
    vault.mkdir(parents=True, exist_ok=True)
    models = ModelSettingsService(FixtureCredentialStore(), tags_fetch=lambda: {"models": [{"name": "closure-candidate:7b"}]})
    app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: delta.NOW),
                              data_root=root / "data", vault_root=vault,
                              deep_analysis_service=da_service, backup_restore_service=backup,
                              model_settings=models, now=lambda: delta.NOW)
    server = serve_loopback(app, port=args.port)
    print(json.dumps({"port": server.server_port, "root": str(root)}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
