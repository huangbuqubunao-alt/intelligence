"""Real local HTTP/SQLite/worker fixture. No live provider/model qualification."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.bilibili_content import BilibiliContentProvider  # noqa: E402
from youtube_intel.extractive_summary import ExtractiveSummaryService  # noqa: E402
from youtube_intel.following_tracking import FollowingTrackingService  # noqa: E402
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
from youtube_intel.runtime_composition import (  # noqa: E402
    DurableSourceRunWorker,
    RuntimeSourceRunIngestion,
    _deep_analysis_production_capability,
)

creator = _load_module("test_creator_following")
source_runs = _load_module("test_task024_processing_orchestration")
authority = _load_module("test_v1x_phase1b_authority")


class Fixture:
    def __init__(self, root: Path, *, offline: bool) -> None:
        self.path = root / "provider-state.json"
        self.offline = offline
        self.requests: list[str] = []
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "now": "2026-10-04T00:00:00+00:00", "published": {}}

    def now(self) -> datetime:
        return datetime.fromisoformat(self.state["now"])

    def save(self) -> None:
        self.path.write_text(json.dumps(self.state))

    def ids(self, mid: int) -> tuple[str, str, str]:
        return tuple(creator.bvid(mid * 10 + index) for index in range(3))

    def fetch(self, url: str, maximum: int) -> bytes:
        validate_request_url(url)
        self.requests.append(url)
        if self.offline:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        query = parse_qs(urlsplit(url).query)
        if "/card?" in url:
            mid = query["mid"][0]
            data = {"card": {"mid": mid, "name": "公开 UP 主 " + mid}}
        elif "/search?" in url:
            mid = int(query["mid"][0])
            page = int(query["pn"][0])
            ids = self.ids(mid)
            timestamp = self.state["published"].get(str(mid))
            entries = [{"bvid": ids[0], "mid": mid, "created": 1700000000}]
            if timestamp is not None:
                entries = [{"bvid": bv, "mid": mid, "created": timestamp} for bv in ids[1:]] + entries
            data = {"list": {"vlist": entries if page == 1 else []}, "page": {"pn": page, "ps": 30, "count": len(entries)}}
        elif "/view?" in url:
            bv = query["bvid"][0]
            match = next((mid for mid in range(1000, 1010) if bv in self.ids(mid)), None)
            if match is None:
                raise BilibiliError("NOT_FOUND")
            old, _, _ = self.ids(match)
            data = {"bvid": bv, "cid": 12345, "title": "Sentence1 Bilibili " + bv + " <script>never execute</script>",
                "owner": {"mid": match, "name": "公开 UP 主 " + str(match)}, "pubdate": 1700000000 if bv == old else self.state["published"][str(match)],
                "duration": 60, "state": 0, "rights": {"pay": 0}}
        elif "/v2?" in url:
            bv = query["bvid"][0]
            captionless = any(bv == self.ids(mid)[2] for mid in range(1000, 1010))
            data = {"subtitle": {"subtitles": [] if captionless else [{"id": 678, "lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//aisubtitle.hdslb.com/bfs/subtitle/phase11.json"}]}}
        else:
            return json.dumps({"body": [{"from": 0.25, "to": 3, "content": "Sentence1 公开字幕支持可信的来源证据。"},
                {"from": 4, "to": 8, "content": "Stored captions stay readable offline."}]}).encode()
        return json.dumps({"code": 0, "data": data}).encode()


class FixtureApplication(LocalApiApplication):
    fixture: Fixture

    def handle(self, method: str, path: str, body: bytes = b"") -> tuple[int, dict[str, object]]:
        if method == "POST" and path == "/api/v1/fixture/advance":
            data = json.loads(body)
            self.fixture.state["now"] = (self.fixture.now() + timedelta(minutes=20)).isoformat()
            if data.get("publish"):
                self.fixture.state["published"][str(data["mid"])] = int(self.fixture.now().timestamp())
            self.fixture.save()
            return 200, {"now": self.fixture.state["now"]}
        return super().handle(method, path, body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5612)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "phase11"):
        raise ValueError("Use an isolated Phase 11 fixture root")
    root.mkdir(parents=True, exist_ok=True)
    fixture = Fixture(root, offline=args.offline)
    if not (root / "state.sqlite3").exists():
        repo = authority.seed(root)
        local_id = LocalContentProvider(repo, root / "data", now=fixture.now).import_bytes(
            "Sentence1 local research.md", b"Sentence1 independent local authority.\n").content_id
        ExtractiveSummaryService(repo, root / "data").create(authority.VIDEO, now=fixture.now())
        (root / "fixture.json").write_text(json.dumps({"youtube_id": authority.VIDEO, "local_id": local_id,
            "creators": {str(mid): fixture.ids(mid) for mid in range(1000, 1010)}}))
    backup = BackupRestoreService(database=root / "state.sqlite3", data_root=root / "data")
    backup.recover_and_apply_pending_restore()
    repo = authority.SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=fixture.now())
    tracker = FollowingTrackingService(repo, BilibiliContentProvider(repo, root / "data", adapter=BilibiliAdapter(fetch=fixture.fetch), now=fixture.now), now=fixture.now)
    transport = source_runs._Transport(available=False)
    orchestrator = source_runs._orchestrator(repo, transport)
    orchestrator._now = fixture.now
    orchestrator._ingestion = RuntimeSourceRunIngestion(SimpleNamespace(_repository=repo), orchestrator._source_policy, tracker)
    worker = DurableSourceRunWorker(orchestrator)
    product = ProductOrchestrationService(repo, source_run_submitter=orchestrator, source_tracking=tracker, now=fixture.now)
    da = authority.service(repo)
    da._capability = _deep_analysis_production_capability()
    assert da._capability.execution_route() is None
    app = FixtureApplication(repo, product, data_root=root / "data", source_tracking=tracker,
        bilibili_adapter=tracker.publisher.adapter,
        processing_orchestrator=orchestrator, source_run_wakeup=worker.notify, now=fixture.now,
        deep_analysis_service=da, backup_restore_service=backup)
    app.fixture = fixture
    server = serve_loopback(app, port=args.port)
    worker.start()
    print(json.dumps({"port": server.server_port, "root": str(root), "offline": args.offline}), flush=True)
    try:
        server.serve_forever()
    finally:
        worker.stop()
        fixture.save()
        assert transport.calls == 0
        (root / ("offline-requests.json" if args.offline else "requests.json")).write_text(json.dumps(fixture.requests, indent=2))
        server.server_close()


if __name__ == "__main__":
    main()
