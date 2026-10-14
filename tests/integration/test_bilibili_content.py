"""Shared Content authority from deterministic public network fixtures."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.providers.bilibili import BilibiliAdapter, BilibiliError
from youtube_intel.source_authority import verify_source
from youtube_intel.state import SQLiteStateRepository

BV = "BV1xx411c7mD"
NOW = datetime(2026, 10, 4, tzinfo=UTC)


class PublicFixture:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.caption = True
        self.title = "Public Bilibili source"
        self.text = "公共字幕支持统一证据。"
        self.offline = False

    def fetch(self, url: str, maximum: int) -> bytes:
        self.calls.append(url)
        if self.offline:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        if "/view?" in url:
            body = {"code": 0, "data": {"bvid": BV, "cid": 12345,
                "title": self.title, "owner": {"mid": 123, "name": "Public uploader"},
                "pubdate": 1470000000, "duration": 60, "state": 0, "rights": {"pay": 0}}}
        elif "/v2?" in url:
            body = {"code": 0, "data": {"subtitle": {"subtitles": [] if not self.caption else [
                {"id": 678, "lan": "zh-CN", "lan_doc": "中文", "subtitle_url": "//aisubtitle.hdslb.com/bfs/subtitle/fixture.json"}]}}}
        else:
            body = {"body": [{"from": 0, "to": 3, "content": self.text},
                {"from": 4, "to": 8, "content": "Stored captions remain readable offline."}]}
        return json.dumps(body, ensure_ascii=False).encode()


def setup(tmp_path: Path) -> tuple[SQLiteStateRepository, BilibiliContentProvider, PublicFixture]:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=NOW)
    fixture = PublicFixture()
    provider = BilibiliContentProvider(repo, tmp_path / "data", adapter=BilibiliAdapter(fetch=fixture.fetch), now=lambda: NOW)
    return repo, provider, fixture


def test_content_caption_summary_evidence_restart_offline(tmp_path: Path) -> None:
    repo, provider, fixture = setup(tmp_path)
    result = provider.import_input(BV)
    assert result.status == "READY"
    assert repo.schema_version().version == 39  # type: ignore[union-attr]
    content = repo.get_video(result.content_id)
    assert content is not None and content.provider == "BILIBILI"
    assert content.default_language == "zh-CN"
    following = repo.list_source_subscriptions()[0]
    assert following.provider == "BILIBILI"
    assert following.channel_id is None and following.video_id == result.content_id
    timed = repo.get_verified_timed_transcript(video_id=result.content_id)
    assert timed is not None and timed.cues[0].text == fixture.text
    ids = repo.list_evidence_for_presentation(result.content_id)
    assert ids and all(repo.get_evidence(e).locator_type == "TIMED_MEDIA" for e in ids)  # type: ignore[union-attr]
    assert all(repo.resolve_verified_evidence_text(e) is not None for e in ids)
    pointer = repo.current_local_summary_pointer(result.content_id)
    assert pointer is not None
    summary = ExtractiveSummaryService(repo, tmp_path / "data").read(result.content_id, pointer.artifact_id)
    assert summary.result.evidence
    fixture.offline = True
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite")
    restarted.bind_source_storage(tmp_path / "data")
    assert restarted.get_verified_timed_transcript(video_id=result.content_id) == timed
    assert ExtractiveSummaryService(restarted, tmp_path / "data").read(result.content_id, pointer.artifact_id) == summary
    calls = len(fixture.calls)
    duplicate = provider.import_input(f"https://m.bilibili.com/video/{BV}?share=changed")
    assert duplicate.reused and duplicate.content_id == result.content_id
    assert len(fixture.calls) == calls and len(repo.list_videos()) == 1


def test_no_caption_and_explicit_retry(tmp_path: Path) -> None:
    repo, provider, fixture = setup(tmp_path)
    fixture.caption = False
    result = provider.import_input(BV)
    assert result.status == "CAPTION_UNAVAILABLE"
    assert repo.list_evidence_for_presentation(result.content_id) == ()
    assert repo.current_local_summary_pointer(result.content_id) is None
    fixture.caption = True
    retry = provider.retry(result.content_id)
    assert retry.status == "READY"
    assert repo.list_source_subscriptions()[0].last_error_code is None
    assert len(repo.list_videos()) == 1


def test_ready_caption_never_overwritten_by_remote_change(tmp_path: Path) -> None:
    repo, provider, fixture = setup(tmp_path)
    result = provider.import_input(BV)
    evidence = repo.list_evidence_for_presentation(result.content_id)
    before = tuple(repo.resolve_verified_evidence_text(e) for e in evidence)
    fixture.title = "Changed title"
    fixture.text = "Changed caption"
    calls = len(fixture.calls)
    assert provider.retry(result.content_id).status == "READY"
    assert len(fixture.calls) == calls
    assert tuple(repo.resolve_verified_evidence_text(e) for e in evidence) == before
    assert repo.get_video(result.content_id).title == "Public Bilibili source"  # type: ignore[union-attr]


def test_corrupt_caption_artifact_rejected(tmp_path: Path) -> None:
    repo, provider, fixture = setup(tmp_path)
    result = provider.import_input(BV)
    ids = repo.list_evidence_for_presentation(result.content_id)
    with repo._connect() as connection:
        source = verify_source(repo, connection, result.content_id)
        assert source is not None
        artifact = connection.execute("SELECT relative_path FROM artifacts WHERE artifact_id=?", (source["canonical_artifact_id"],)).fetchone()
    (tmp_path / "data" / artifact[0]).write_text("corrupt")
    assert repo.get_verified_timed_transcript(video_id=result.content_id) is None
    assert all(repo.resolve_verified_evidence_text(e) is None for e in ids)


def test_offline_new_import_admits_nothing(tmp_path: Path) -> None:
    repo, provider, fixture = setup(tmp_path)
    fixture.offline = True
    with pytest.raises(BilibiliError, match="NETWORK_UNAVAILABLE"):
        provider.import_input(BV)
    assert not repo.list_videos() and not repo.list_source_subscriptions()


def test_shared_api_projects_caption_source_and_failure(tmp_path: Path) -> None:
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repo, provider, fixture = setup(tmp_path)
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=tmp_path / "data",
        bilibili_adapter=provider.adapter, now=lambda: NOW)
    status, result = app.handle("POST", "/api/v1/bilibili/imports", json.dumps({"input": BV}).encode())
    assert status == 201
    content_id = result["import"]["content_id"]
    status, detail = app.handle("GET", "/api/v1/videos/" + content_id)
    assert status == 200
    assert detail["video"]["provider"] == "BILIBILI"
    assert detail["video"]["source_url"] == f"https://www.bilibili.com/video/{BV}/"
    assert detail["video"]["channel_name"] == "Public uploader"
    assert detail["transcript"]["timed_segments"][0]["text"] == fixture.text
    assert detail["note"]["v2"]["timestamped_key_points"]
    with pytest.raises(ApiError) as rejected:
        app.handle("POST", "/api/v1/bilibili/imports", b'{"input":"https://localhost/a"}')
    assert rejected.value.status == 422 and rejected.value.code == "BILIBILI_UNSUPPORTED_URL"
    assert len(repo.list_videos()) == 1
    assert ProductOrchestrationService(repo).check_source("bilibili-video-" + BV).status.value == "BLOCKED"


def test_crash_before_content_admission_can_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, provider, fixture = setup(tmp_path)
    original = provider._artifact_write
    def failure(*args, **kwargs):
        raise OSError("staging unavailable")
    monkeypatch.setattr(provider, "_artifact_write", failure)
    with pytest.raises(OSError):
        provider.import_input(BV)
    assert not repo.list_videos()
    monkeypatch.setattr(provider, "_artifact_write", original)
    assert provider.import_input(BV).status == "READY"
    assert len(repo.list_source_subscriptions()) == 1


def test_no_media_or_unqualified_executor_route(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from youtube_intel import local_content
    from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
    from youtube_intel.runtime_composition import _deep_analysis_production_capability
    def forbidden(*args, **kwargs):
        raise AssertionError("unqualified media/ASR route was reached")
    monkeypatch.setattr(local_content, "probe_media", forbidden)
    monkeypatch.setattr(LocalTranscriptionJobs, "start", forbidden)
    repo, provider, fixture = setup(tmp_path)
    fixture.caption = False
    result = provider.import_input(BV)
    assert result.status == "CAPTION_UNAVAILABLE"
    fixture.caption = True
    assert provider.retry(result.content_id).status == "READY"
    with repo._connect() as connection:
        assert not connection.execute("SELECT * FROM artifacts WHERE video_id=? AND kind='audio'", (result.content_id,)).fetchall()
    assert _deep_analysis_production_capability().execution_route() is None


def test_bilibili_evidence_cannot_bind_another_content(tmp_path: Path) -> None:
    from youtube_intel.local_content import LocalContentProvider
    from youtube_intel.state import (
        EvidenceAvailability,
        EvidenceLineageKind,
        EvidenceRole,
        EvidenceTextBindingWrite,
        EvidenceWrite,
        IntegrityConflict,
        build_evidence_id,
    )
    repo, provider, _ = setup(tmp_path)
    imported = provider.import_input(BV)
    timed = repo.get_verified_timed_transcript(video_id=imported.content_id)
    assert timed is not None
    other = LocalContentProvider(repo, tmp_path / 'data', now=lambda: NOW).import_bytes(
        'other.txt', b'Different Content authority.')
    evidence = EvidenceWrite(
        evidence_id=build_evidence_id(video_id=other.content_id,
            artifact_id=timed.canonical_artifact_id, start_ms=0, end_ms=3000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL),
        video_id=other.content_id, artifact_id=timed.canonical_artifact_id,
        start_ms=0, end_ms=3000, lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL, language='zh-CN', availability=EvidenceAvailability.AVAILABLE)
    binding = EvidenceTextBindingWrite.from_timed_transcript(evidence=evidence,
        timed_transcript_id=timed.timed_transcript_id, start_cue_index=0, end_cue_index=1,
        excerpt=timed.cues[0].text)
    with pytest.raises((IntegrityConflict, ValueError)):
        repo.create_evidence_with_text_binding(evidence, binding, now=NOW)
    assert repo.get_evidence(evidence.evidence_id) is None


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_code"),
    [
        ("RISK_CONTROLLED", 429, "BILIBILI_RISK_CONTROLLED"),
        ("RATE_LIMITED", 429, "BILIBILI_RATE_LIMITED"),
        ("ACCESS_DENIED", 403, "BILIBILI_ACCESS_DENIED"),
        ("NOT_FOUND", 404, "BILIBILI_NOT_FOUND"),
        ("NETWORK_UNAVAILABLE", 503, "BILIBILI_NETWORK_UNAVAILABLE"),
        ("INVALID_INPUT", 422, "BILIBILI_INVALID_INPUT"),
    ],
)
def test_public_refusal_is_reported_as_its_true_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_status: int,
    expected_code: str,
) -> None:
    """A provider refusal must not be laundered into a generic client error.

    Phase 11R measured the real provider refusing public requests with
    ``-412 request was banned``. Telling the user "access denied" describes a
    different problem and invites the wrong next action, so each code keeps its
    own truthful HTTP status.
    """
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repo, provider, fixture = setup(tmp_path)
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=tmp_path / "data",
        bilibili_adapter=provider.adapter,
        now=lambda: NOW,
    )

    def refuse(url: str, maximum: int) -> bytes:
        raise BilibiliError(failure)

    monkeypatch.setattr(provider.adapter, "fetch", refuse)
    with pytest.raises(ApiError) as rejected:
        app.handle("POST", "/api/v1/bilibili/imports", json.dumps({"input": BV}).encode())
    assert rejected.value.status == expected_status
    assert rejected.value.code == expected_code
    assert not repo.list_videos(), "a refusal must not admit Content"
