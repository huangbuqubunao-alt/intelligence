"""Disposable Phase 1B SQLite fixture; never contacts a model or real vault."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel.deep_analysis_service import DeepAnalysisCapability  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    if any(args.root.iterdir()):
        raise ValueError("fixture root must start empty")
    support = _load_module("test_v1x_phase1b_authority")
    repository = support.seed(args.root)
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET title=? WHERE video_id=?", ("Phase 2 disposable fixture " + "Long title " * 20, support.VIDEO))
    service = support.service(repository)
    result = service.run(content_id=support.VIDEO)
    service._capability = DeepAnalysisCapability()
    vault = args.root / "external-vault"
    (vault / "Knowledge").mkdir(parents=True)
    application = LocalApiApplication(
        repository, ProductOrchestrationService(repository),
        data_root=args.root / "data", vault_root=vault / "Knowledge",
        deep_analysis_service=service,
    )
    server = serve_loopback(application, port=0)
    info = {"port": server.server_port, "root": str(args.root), "content_id": support.VIDEO, "result_identity": result.result_identity}
    (args.root / "browser-fixture.json").write_text(json.dumps(info))
    print(json.dumps(info), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
