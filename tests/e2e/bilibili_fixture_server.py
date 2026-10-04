"""Isolated HTTP/SQLite fixture for Phase 10B, never a live provider claim."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.extractive_summary import ExtractiveSummaryService  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.local_content import LocalContentProvider  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.providers.bilibili import (  # noqa: E402
    BilibiliAdapter,
    BilibiliError,
    validate_request_url,
)
from youtube_intel.runtime_composition import (
    _deep_analysis_production_capability,  # noqa: E402
)
from youtube_intel.state import SQLiteStateRepository  # noqa: E402

CAPTION_BV = "BV1xx411c7mD"
NO_CAPTION_BV = "BV1Q541167Qg"
NOW = datetime(2026, 10, 4, tzinfo=UTC)


class PublicFixture:
    def __init__(self, offline: bool = False):
        self.offline = offline
        self.requests = []

    def fetch(self, url: str, maximum: int) -> bytes:
        validate_request_url(url)
        self.requests.append(url)
        if self.offline:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        parts = urlsplit(url)
        bvid = parse_qs(parts.query).get("bvid", [CAPTION_BV])[0]
        if parts.path.endswith("/view"):
            if bvid not in {CAPTION_BV, NO_CAPTION_BV}:
                raise BilibiliError("NOT_FOUND")
            body = {"code": 0, "data": {"bvid": bvid, "cid": 101 if bvid == CAPTION_BV else 102,
                "title": "Sentence1 Bilibili trusted captions <script>alert('unsafe')</script>" if bvid == CAPTION_BV else "Bilibili metadata only",
                "owner": {"mid": 123, "name": "Public fixture uploader"}, "pubdate": 1791020000,
                "duration": 60, "state": 0, "rights": {"pay": 0}}}
        elif parts.path.endswith("/v2"):
            body = {"code": 0, "data": {"subtitle": {"subtitles": [] if bvid == NO_CAPTION_BV else [
                {"id": 456, "lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//aisubtitle.hdslb.com/bfs/subtitle/phase10b.json"}]}}}
        else:
            body = {"body": [{"from": 0.25, "to": 3, "content": "Sentence1 哔哩哔哩原始字幕支持统一证据。"},
                {"from": 4, "to": 8, "content": "Stored captions stay readable offline. <script>never execute</script>"}]}
        return json.dumps(body, ensure_ascii=False).encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5610)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "phase10b"):
        raise ValueError("Phase 10B fixture must remain isolated")
    root.mkdir(parents=True, exist_ok=True)
    authority = _load_module("test_v1x_phase1b_authority")
    if not (root / "state.sqlite3").exists():
        repo = authority.seed(root)
        local = LocalContentProvider(repo, root / "data", now=lambda: NOW)
        local_id = local.import_bytes("Sentence1 local research.md", b"Sentence1 local authority is independent of remote providers.\n").content_id
        ExtractiveSummaryService(repo, root / "data").create(authority.VIDEO, now=NOW)
        (root / "fixture.json").write_text(json.dumps({"youtube_id": authority.VIDEO, "local_id": local_id,
            "caption_bv": CAPTION_BV, "no_caption_bv": NO_CAPTION_BV}))
    backup = BackupRestoreService(database=root / "state.sqlite3", data_root=root / "data")
    backup.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=NOW)
    da = authority.service(repo)
    da._capability = _deep_analysis_production_capability()
    assert da._capability.execution_route() is None
    fixture = PublicFixture(args.offline)
    app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: NOW), data_root=root / "data",
        deep_analysis_service=da, backup_restore_service=backup, bilibili_adapter=BilibiliAdapter(fetch=fixture.fetch), now=lambda: NOW)
    server = serve_loopback(app, port=args.port)
    print(json.dumps({"port": server.server_port, "root": str(root), "provider": "DETERMINISTIC_PUBLIC_FIXTURE", "offline": args.offline}), flush=True)
    try:
        server.serve_forever()
    finally:
        (root / ("offline-requests.json" if args.offline else "fixture-requests.json")).write_text(json.dumps(fixture.requests, indent=2))
        server.server_close()


if __name__ == "__main__":
    main()
