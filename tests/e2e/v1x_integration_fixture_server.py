"""Disposable integrated HTTP fixture; no model, credentials or real vault."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel import deep_analysis_activation  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.runtime_composition import (
    _deep_analysis_production_capability,  # noqa: E402
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    args.root = args.root.resolve()
    if not (str(args.root).startswith("/tmp/v1x-phase2-integration-") or args.root.resolve().is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "phase6")):
        raise ValueError("use a disposable integration fixture root")
    args.root.mkdir(parents=True, exist_ok=True)
    if any(args.root.iterdir()):
        raise ValueError("fixture root must start empty")
    authority = _load_module("test_v1x_phase1b_authority")
    delta = _load_module("test_v1x_knowledge_delta")
    repository = authority.seed(args.root)
    authority.activation._seed_content(repository, "integration-no-result")
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET title=? WHERE video_id=?", ("Phase 2 disposable fixture " + "Long title " * 20, authority.VIDEO))
        connection.execute("UPDATE videos SET title='Integration no result' WHERE video_id='integration-no-result'")
    service = authority.service(repository)
    result = service.run(content_id=authority.VIDEO)
    delta.content(repository, "integration-recent", delta.NOW)
    # Restrict candidate discovery too; reviewed production records remain real.
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    service._capability = _deep_analysis_production_capability()
    assert service._capability.execution_route() is None
    vault = args.root / "external-vault"
    (vault / "Knowledge").mkdir(parents=True)
    application = LocalApiApplication(
        repository, ProductOrchestrationService(repository),
        data_root=args.root / "data", vault_root=vault / "Knowledge",
        deep_analysis_service=service, now=lambda: delta.NOW,
    )
    server = serve_loopback(application, port=0)
    info = {"port": server.server_port, "root": str(args.root), "content_id": authority.VIDEO, "result_identity": result.result_identity}
    (args.root / "browser-fixture.json").write_text(json.dumps(info))
    print(json.dumps(info), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
