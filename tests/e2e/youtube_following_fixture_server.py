"""Real loopback API/SQLite/Source Run fixture for mixed-provider Following."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module  # noqa: E402

from youtube_intel.backup_restore import BackupRestoreService  # noqa: E402
from youtube_intel.bilibili_content import BilibiliContentProvider  # noqa: E402
from youtube_intel.config import load_app_config  # noqa: E402
from youtube_intel.extractive_summary import ExtractiveSummaryService  # noqa: E402
from youtube_intel.following_tracking import FollowingTrackingService  # noqa: E402
from youtube_intel.local_api import LocalApiApplication, serve_loopback  # noqa: E402
from youtube_intel.local_content import LocalContentProvider  # noqa: E402
from youtube_intel.orchestration import ProcessingPolicy  # noqa: E402
from youtube_intel.orchestration_service import (
    ProductOrchestrationService,  # noqa: E402
)
from youtube_intel.providers.bilibili import (  # noqa: E402
    BilibiliAdapter,
    BilibiliError,
)
from youtube_intel.providers.youtube_channel import (  # noqa: E402
    TrackingError,
    YouTubeFollowingProvider,
    canonical_channel,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations  # noqa: E402
from youtube_intel.runtime_composition import (
    DurableSourceRunWorker,
    RuntimeSourceRunIngestion,
)  # noqa: E402
from youtube_intel.state import SQLiteStateRepository  # noqa: E402
from youtube_intel.transcripts import SubtitleTrackListing  # noqa: E402

support = _load_module("test_runtime_composition")
youtube = _load_module("test_youtube_following")
creator = _load_module("test_creator_following")
runs = _load_module("test_task024_processing_orchestration")
authority = _load_module("test_v1x_phase1b_authority")


class Fixture:
    def __init__(self, root, offline):
        self.root = root
        self.offline = offline
        path = root / "provider-state.json"
        self.state = (
            json.loads(path.read_text())
            if path.exists()
            else {
                "now": youtube.NOW.isoformat(),
                "published": [],
                "publication_times": {},
            }
        )
        self.channels = []
        self.requests = []
        for index in range(8):
            fixture = youtube.YouTubeFixture()
            fixture.name = "YouTube channel " + str(index)
            fixture.metadata_channel = "UC" + str(index).zfill(22)
            fixture.items = [
                ("oldyt" + str(index).zfill(6), youtube.NOW - timedelta(days=10))
            ]
            if index in self.state["published"]:
                fixture.items = [
                    (
                        "ytcpt" + str(index).zfill(6),
                        datetime.fromisoformat(
                            self.state["publication_times"][str(index)]
                        )
                        + timedelta(seconds=1),
                    ),
                    (
                        "ytnoo" + str(index).zfill(6),
                        datetime.fromisoformat(
                            self.state["publication_times"][str(index)]
                        )
                        + timedelta(seconds=2),
                    ),
                ] + fixture.items
            self.channels.append(fixture)
        self.bili = creator.CreatorFixture()
        if self.state["published"]:
            self.bili.items.insert(0, (creator.NEW, youtube.NOW + timedelta(seconds=1)))

    def now(self):
        return datetime.fromisoformat(self.state["now"])

    def save(self):
        (self.root / "provider-state.json").write_text(json.dumps(self.state))

    def denied(self):
        raise AssertionError("No model, cloud or acoustic provider may be used")

    def fetch(self, video_id):
        self.requests.append("metadata:" + video_id)
        if self.offline:
            raise TrackingError("NETWORK_UNAVAILABLE")
        return next(
            channel.fetch(video_id)
            for channel in self.channels
            if video_id in dict(channel.items)
        )

    def feed(self, channel_id):
        self.requests.append("feed:" + channel_id)
        if self.offline or channel_id in self.state.get("failed_feeds", []):
            raise TrackingError("NETWORK_UNAVAILABLE")
        return next(
            channel.feed(channel_id)
            for channel in self.channels
            if channel.metadata_channel == channel_id
        )

    def resolve(self, alias):
        if self.offline:
            raise TrackingError("NETWORK_UNAVAILABLE")
        channel = (
            self.channels[int(alias[7:])]
            if alias.startswith("@public")
            else next(
                channel
                for channel in self.channels
                if channel.metadata_channel == alias
            )
        )
        return canonical_channel(channel.metadata_channel, channel.name)

    def bili_fetch(self, url, maximum):
        self.requests.append("bilibili:" + url)
        self.bili.now = self.now()
        if self.offline:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        return self.bili.fetch(url, maximum)

    def subtitle(self):
        adapter = support._TimedSubtitleAdapter()
        original = adapter.enumerate_tracks

        def enumerate_tracks(video_id):
            self.requests.append("captions:" + video_id)
            if self.offline:
                raise TrackingError("NETWORK_UNAVAILABLE")
            listing = original(support.VIDEO_ID)
            return (
                SubtitleTrackListing(tracks=(), call=listing.call)
                if video_id.startswith("ytnoo")
                else listing
            )

        adapter.enumerate_tracks = enumerate_tracks
        return adapter


class App(LocalApiApplication):
    def handle(self, method, path, body=b""):
        if method == "POST" and path == "/api/v1/fixture/failure":
            data = json.loads(body)
            channel_id = self.fixture.channels[data["index"]].metadata_channel
            failed = set(self.fixture.state.get("failed_feeds", []))
            if data["offline"]:
                failed.add(channel_id)
            else:
                failed.discard(channel_id)
            self.fixture.state["failed_feeds"] = sorted(failed)
            self.fixture.save()
            return 200, {"failed_feeds": sorted(failed)}
        if method == "POST" and path == "/api/v1/fixture/advance":
            data = json.loads(body)
            self.fixture.state["now"] = (
                self.fixture.now() + timedelta(minutes=20)
            ).isoformat()
            if data.get("publish"):
                index = data["index"]
                if index not in self.fixture.state["published"]:
                    self.fixture.state["published"].append(index)
                    published_at = self.fixture.now() - timedelta(minutes=1)
                    self.fixture.state["publication_times"][str(index)] = (
                        published_at.isoformat()
                    )
                    channel = self.fixture.channels[index]
                    channel.items = [
                        (
                            "ytcpt" + str(index).zfill(6),
                            published_at + timedelta(seconds=1),
                        ),
                        (
                            "ytnoo" + str(index).zfill(6),
                            published_at + timedelta(seconds=2),
                        ),
                    ] + channel.items
                    if len(self.fixture.state["published"]) == 1:
                        self.fixture.bili.items.insert(
                            0, (creator.NEW, youtube.NOW + timedelta(seconds=1))
                        )
            self.fixture.save()
            return 200, {"now": self.fixture.state["now"]}
        return super().handle(method, path, body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[2] / ".var/phase12"):
        raise ValueError("Use an isolated Phase 12 root")
    root.mkdir(parents=True, exist_ok=True)
    fixture = Fixture(root, args.offline)
    if not (root / "config/channels.yaml").exists():
        support._project(root)
    config = load_app_config(
        root / "config/channels.yaml", root / "config/settings.yaml"
    )
    backup = BackupRestoreService(
        database=root / "state.sqlite", data_root=root / "data"
    )
    backup.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(root / "state.sqlite")
    runtime = RuntimeOperations(
        config=config,
        project_root=root,
        repository=repo,
        dependencies=RuntimeDependencies(
            discovery_source=support._DiscoverySource(),
            metadata_provider=fixture,
            subtitle_adapter_factory=fixture.subtitle,
            scoring_provider_factory=fixture.denied,
            analysis_provider_factory=fixture.denied,
            quality_judge_provider_factory=fixture.denied,
        ),
    )
    import youtube_intel.providers.youtube_channel as provider_module
    import youtube_intel.runtime as runtime_module

    runtime_module._utcnow = fixture.now
    provider_module.public_operation = lambda operation: operation()
    provider = YouTubeFollowingProvider(
        enroll_video=runtime.enroll_followed_youtube_video
    )
    provider._fetch = fixture.feed
    provider._resolve = fixture.resolve
    tracker = FollowingTrackingService(
        repo,
        BilibiliContentProvider(
            repo,
            runtime._data_root,
            adapter=BilibiliAdapter(fetch=fixture.bili_fetch),
            now=fixture.now,
        ),
        youtube=provider,
        now=fixture.now,
    )
    # Seed retained Phase 11 authority with a historical fixture only. Runtime
    # capability stays withdrawn; the browser cannot create/check a creator.
    if repo.get_source_subscription("bilibili-creator-123") is None:
        tracker.providers["BILIBILI"].available = True
        fixture.bili.items.insert(0, (creator.NEW, youtube.NOW - timedelta(days=1)))
        tracker.follow("123")
        tracker.publisher.import_input(creator.NEW)
        tracker.providers["BILIBILI"].available = False
    # Existing manual YouTube import, using the accepted ordinary ingestion path.
    info = root / "fixture.json"
    if not info.exists():
        product = ProductOrchestrationService(repo, now=fixture.now)
        for channel in fixture.channels:
            id = channel.items[0][0]
            source = product.add_source(
                url="https://www.youtube.com/watch?v=" + id,
                processing_policy=ProcessingPolicy.DISCOVER_ONLY,
            )
            runtime.ingest_source_to_transcript(source.source_id, limit=1)
            ExtractiveSummaryService(repo, runtime._data_root).create(
                id, now=fixture.now()
            )
        local = LocalContentProvider(
            repo, runtime._data_root, now=fixture.now
        ).import_bytes(
            "Public local.md",
            b"This public source supports independent local evidence.\n",
        )
        info.write_text(
            json.dumps(
                {
                    "local_id": local.content_id,
                    "channels": [
                        channel.metadata_channel for channel in fixture.channels
                    ],
                }
            )
        )
    transport = runs._Transport(available=False)
    orchestrator = runs._orchestrator(repo, transport)
    orchestrator._now = fixture.now
    orchestrator._ingestion = RuntimeSourceRunIngestion(
        runtime, orchestrator._source_policy, tracker
    )
    worker = DurableSourceRunWorker(orchestrator)
    from youtube_intel.runtime_composition import _deep_analysis_production_capability

    da = authority.service(repo)
    da._capability = _deep_analysis_production_capability()
    assert da._capability.execution_route() is None
    app = App(
        repo,
        ProductOrchestrationService(
            repo,
            source_run_submitter=orchestrator,
            source_tracking=tracker,
            now=fixture.now,
        ),
        data_root=runtime._data_root,
        source_tracking=tracker,
        processing_orchestrator=orchestrator,
        source_run_wakeup=worker.notify,
        now=fixture.now,
        backup_restore_service=backup,
        deep_analysis_service=da,
        bilibili_adapter=tracker.publisher.adapter,
    )
    app.fixture = fixture
    server = serve_loopback(app, port=5712)
    worker.start()
    print(json.dumps({"port": 5712, "offline": args.offline}), flush=True)
    try:
        server.serve_forever()
    finally:
        worker.stop()
        fixture.save()
        assert transport.calls == 0
        (
            root / ("offline-requests.json" if args.offline else "requests.json")
        ).write_text(json.dumps(fixture.requests, indent=2))
        server.server_close()


if __name__ == "__main__":
    main()
