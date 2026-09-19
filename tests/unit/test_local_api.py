import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from youtube_intel.domain import Availability, JobStatus, LiveStatus, VideoMetadata
from youtube_intel.local_api import _LOCAL_ORIGIN, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    ReportStatus,
    ReportWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)


def _app(tmp_path: Path) -> LocalApiApplication:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 9, 1, tzinfo=UTC))
    service = ProductOrchestrationService(
        repository, now=lambda: datetime(2026, 9, 1, tzinfo=UTC)
    )
    return LocalApiApplication(
        repository,
        service,
        data_root=tmp_path / "data",
        vault_root=tmp_path / "vault",
        now=lambda: datetime(2026, 9, 1, tzinfo=UTC),
    )


def _record_video(app: LocalApiApplication, video_id: str) -> None:
    app._repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC1234567890123456789012",
            channel_name="Fixture channel",
            title=f"Video {video_id}",
            description="Fixture only.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=datetime(2026, 9, 1, tzinfo=UTC),
    )


def test_safe_source_write_and_read_do_not_start_check(tmp_path: Path) -> None:
    app = _app(tmp_path)
    status, payload = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtu.be/abcdefghijk",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    assert status == 201
    assert payload["source"]["last_checked_at"] is None
    assert (
        app.handle("GET", "/api/v1/sources")[1]["sources"][0]["video_id"]
        == "abcdefghijk"
    )


def test_system_backup_projection_is_truthful_and_non_actionable(tmp_path: Path) -> None:
    status, payload = _app(tmp_path).handle("GET", "/api/v1/system")

    assert status == 200
    assert payload["backup"] == {
        "status": "NOT_RUN",
        "backup_available": False,
        "restore_available": False,
        "reason": "No production backup/restore service is wired.",
    }


def test_safe_provider_projection_has_no_secret_or_active_model(tmp_path: Path) -> None:
    status, payload = _app(tmp_path).handle("GET", "/api/v1/settings")
    assert status == 200
    assert payload["model_preference"]["active_production_default"] is None
    assert payload["providers"][1]["reason"] == "1/2; SCHEMA_INVALID"


def test_output_language_uses_bootstrap_default_then_persists_user_choice(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    status, before = app.handle("GET", "/api/v1/settings")
    assert status == 200
    assert before["general"]["output_language"] == "zh-CN"
    assert before["general"]["output_language_source"] == "BOOTSTRAP_DEFAULT"

    status, saved = app.handle(
        "PUT",
        "/api/v1/settings/output-language",
        json.dumps({"output_language": "en"}).encode(),
    )
    assert status == 200
    assert saved["output_language"] == "en"
    assert saved["source"] == "USER_PREFERENCE"

    _, after = app.handle("GET", "/api/v1/settings")
    assert after["general"]["output_language"] == "en"
    assert after["general"]["output_language_source"] == "USER_PREFERENCE"

    repository = app._repository
    reloaded = LocalApiApplication(
        repository,
        ProductOrchestrationService(
            repository, now=lambda: datetime(2026, 9, 1, tzinfo=UTC)
        ),
        output_language_default="zh-CN",
        now=lambda: datetime(2026, 9, 1, tzinfo=UTC),
    )
    _, restarted = reloaded.handle("GET", "/api/v1/settings")
    assert restarted["general"]["output_language"] == "en"


def test_output_language_rejects_unsupported_values(tmp_path: Path) -> None:
    app = _app(tmp_path)

    status, payload = app.handle(
        "PUT",
        "/api/v1/settings/output-language",
        json.dumps({"output_language": "fr"}).encode(),
    )

    assert status == 422
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert app.handle("GET", "/api/v1/settings")[1]["general"]["output_language"] == "zh-CN"


def test_manual_check_is_explicitly_blocked_by_runtime_guard(tmp_path: Path) -> None:
    app = _app(tmp_path)
    _, created = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtube.com/channel/UC1234567890123456789012",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    status, checked = app.handle(
        "POST", f"/api/v1/sources/{created['source']['source_id']}/check"
    )
    assert status == 200
    assert checked["status"] == "BLOCKED"


def test_schedule_time_and_weekday_are_persisted_and_projected_for_future_only(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _, created = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtu.be/abcdefghijk",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    source_id = created["source"]["source_id"]
    status, daily = app.handle(
        "POST",
        "/api/v1/automation",
        json.dumps(
            {
                "target_type": "SOURCE_CHECK",
                "target_id": source_id,
                "frequency": "DAILY",
                "weekday": None,
                "local_time": "08:30",
                "enabled": True,
            }
        ).encode(),
    )
    assert status == 201
    assert daily["schedule"]["next_run"] == "2026-09-01T00:30:00Z"
    assert daily["schedule"]["timezone"] == "Asia/Shanghai"
    status, weekly = app.handle(
        "POST",
        "/api/v1/automation",
        json.dumps(
            {
                "schedule_id": daily["schedule"]["schedule_id"],
                "target_type": "SOURCE_CHECK",
                "target_id": source_id,
                "frequency": "WEEKLY",
                "weekday": 6,
                "local_time": "20:00",
                "enabled": True,
            }
        ).encode(),
    )
    assert status == 201
    assert weekly["schedule"]["next_run"] == "2026-09-06T12:00:00Z"
    assert app.handle("GET", "/api/v1/activity")[1]["runs"] == []


def test_loopback_origin_rule_accepts_only_local_ui_origins() -> None:
    assert _LOCAL_ORIGIN.fullmatch("http://127.0.0.1:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("http://localhost:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("https://example.test") is None


def test_verified_scoring_projection_only_exposes_safe_verified_fields(
    tmp_path: Path,
) -> None:
    class Reader:
        def read(self, video_id: str) -> object:
            assert video_id == "abcdefghijk"
            return SimpleNamespace(
                scoring_outcome=SimpleNamespace(
                    result=SimpleNamespace(
                        score=8.5,
                        reason="Clear product evidence.",
                        topics=("product", "strategy"),
                        provider="local",
                        model="fixture-model",
                        prompt_version="v1",
                    ),
                    decision=SimpleNamespace(final_should_summarize=True),
                    call=SimpleNamespace(finished_at=datetime(2026, 9, 1, tzinfo=UTC)),
                ),
                scoring_success_provenance="VERIFIED_LINEAGE",
            )

    app = _app(tmp_path)
    app._scoring_reader = cast(AuthoritativeScoringReader, Reader())
    projection = app._scoring_projection("abcdefghijk")
    assert projection == {
        "status": "AVAILABLE",
        "score": 8.5,
        "reason": "Clear product evidence.",
        "topics": ["product", "strategy"],
        "should_summarize": True,
        "trusted": True,
        "completed_at": "2026-09-01T00:00:00Z",
        "provenance": {
            "provider": "local",
            "model": "fixture-model",
            "prompt_version": "v1",
            "success_provenance": "VERIFIED_LINEAGE",
        },
    }
    assert "request_hash" not in projection


def test_reader_rejection_fails_closed_without_unverified_content(
    tmp_path: Path,
) -> None:
    class RejectingReader:
        def read(self, video_id: str) -> object:
            raise ValueError("forged raw result")

    app = _app(tmp_path)
    app._scoring_reader = cast(AuthoritativeScoringReader, RejectingReader())
    projection = app._scoring_projection("abcdefghijk")
    assert projection["status"] == "NOT_AVAILABLE"
    assert "forged" not in str(projection)


def test_content_projection_defaults_to_truthful_unavailable_states(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    assert app._transcript_projection("abcdefghijk") == {
        "status": "NOT_PROCESSED",
        "reason": "No canonical transcript has been recorded for this video.",
    }
    assert app._note_projection("abcdefghijk") == {
        "v1": {"status": "UNAVAILABLE", "code": "NOTE_REF_NOT_PERSISTED"},
        "v2": {"status": "UNAVAILABLE", "code": "CONTENT_NOT_FOUND"},
    }


def test_note_projection_exposes_bounded_verified_summary_content(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    summary_section = SimpleNamespace(
        kind=SimpleNamespace(value="SUMMARY"),
        entries=(SimpleNamespace(text="One sentence.", evidence_ids=("e1",)),),
    )
    points_section = SimpleNamespace(
        kind=SimpleNamespace(value="CORE_POINTS"),
        entries=(
            SimpleNamespace(text="Point one.", evidence_ids=("e1",)),
            SimpleNamespace(text="Point two.", evidence_ids=("e2",)),
        ),
    )
    references = (
        SimpleNamespace(
            evidence_id="e1",
            source="transcript",
            excerpt="Evidence one.",
            start_seconds=12.0,
            end_seconds=18.0,
        ),
        SimpleNamespace(
            evidence_id="e2",
            source="transcript",
            excerpt="Evidence two.",
            start_seconds=30.0,
            end_seconds=35.0,
        ),
    )
    app._content_summary_reader.read_current = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        result_identity="a" * 64,
        note=SimpleNamespace(
            identity="note-identity",
            language="zh-CN",
            sections=(summary_section, points_section),
            evidence_references=references,
        ),
    )

    projection = app._note_projection("abcdefghijk")

    assert projection["v2"] == {
        "status": "AVAILABLE",
        "note_identity": "note-identity",
        "result_identity": "a" * 64,
        "language": "zh-CN",
        "summary": "One sentence.",
        "core_points": ["Point one.", "Point two."],
        "timestamped_key_points": [
            {
                "text": "Point one.",
                "start_seconds": 12.0,
                "end_seconds": 18.0,
                "evidence_ids": ["e1"],
            },
            {
                "text": "Point two.",
                "start_seconds": 30.0,
                "end_seconds": 35.0,
                "evidence_ids": ["e2"],
            },
        ],
        "evidence_references": [
            {
                "evidence_id": "e1",
                "source": "transcript",
                "excerpt": "Evidence one.",
                "start_seconds": 12.0,
                "end_seconds": 18.0,
            },
            {
                "evidence_id": "e2",
                "source": "transcript",
                "excerpt": "Evidence two.",
                "start_seconds": 30.0,
                "end_seconds": 35.0,
            },
        ],
    }


def test_note_projection_never_invents_timestamped_key_points(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    summary_section = SimpleNamespace(
        kind=SimpleNamespace(value="SUMMARY"),
        entries=(SimpleNamespace(text="One sentence.", evidence_ids=("e1",)),),
    )
    points_section = SimpleNamespace(
        kind=SimpleNamespace(value="CORE_POINTS"),
        entries=(SimpleNamespace(text="Untimed point.", evidence_ids=("e1",)),),
    )
    references = (
        SimpleNamespace(
            evidence_id="e1",
            source="description",
            excerpt="Untimed evidence.",
            start_seconds=None,
            end_seconds=None,
        ),
    )
    app._content_summary_reader.read_current = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        result_identity="b" * 64,
        note=SimpleNamespace(
            identity="note-untimed",
            language="en",
            sections=(summary_section, points_section),
            evidence_references=references,
        ),
    )

    projection = app._note_projection("abcdefghijk")

    assert projection["v2"]["timestamped_key_points"] == []


def test_intelligence_projection_exposes_excerpt_stance_and_persisted_provenance(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    verified = SimpleNamespace(
        intelligence_id="intel-1",
        revision_id="revision-1",
        claim_kind=SimpleNamespace(value="FACT"),
        state=SimpleNamespace(value="CONFIRMED"),
        evidence_ids=("evidence-1",),
        is_confirmed=True,
    )
    app._intelligence_reader.read_current = lambda _intelligence_id: verified  # type: ignore[method-assign]
    app._intelligence_reader.read_current_card = lambda _intelligence_id: SimpleNamespace(  # type: ignore[method-assign]
        verified=verified,
        core_conclusion="Trusted conclusion.",
        user_relevant_information=("Relevant.",),
        important_new_information=(),
        meaningful_details=(),
        filtered_noise=(),
        source_id="source-1",
        video_id="abcdefghijk",
        preference_ids=(),
        source_policy_revision_id=None,
    )
    app._repository.get_video = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        source_url="https://www.youtube.com/watch?v=abcdefghijk"
    )
    app._repository.list_intelligence_revision_evidence_relations = lambda _revision_id: (  # type: ignore[method-assign]
        SimpleNamespace(
            revision_id="revision-1",
            evidence_id="evidence-1",
            stance=SimpleNamespace(value="contradicting"),
        ),
    )
    app._repository.get_evidence = lambda _evidence_id: SimpleNamespace(  # type: ignore[method-assign]
        evidence_id="evidence-1",
        artifact_id="transcript-artifact-1",
        start_ms=1000,
        end_ms=2000,
        language="en",
        lineage_kind=SimpleNamespace(value="ORIGINAL_TRANSCRIPT"),
        role=SimpleNamespace(value="PRIMARY_ORIGINAL"),
        source_excerpt="The source directly disputes the claim.",
    )

    projection = app._intelligence_projection("intel-1")

    assert projection["card"]["evidence_links"] == [
        {
            "evidence_id": "evidence-1",
            "artifact_id": "transcript-artifact-1",
            "start_ms": 1000,
            "end_ms": 2000,
            "language": "en",
            "lineage_kind": "ORIGINAL_TRANSCRIPT",
            "role": "PRIMARY_ORIGINAL",
            "original_excerpt": "The source directly disputes the claim.",
            "translated_excerpt": None,
            "translated_language": None,
            "stance": "contradicting",
        }
    ]


def test_intelligence_projection_keeps_legacy_excerpt_and_stance_truthfully_unavailable(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    verified = SimpleNamespace(
        intelligence_id="intel-legacy",
        revision_id="revision-legacy",
        claim_kind=SimpleNamespace(value="FACT"),
        state=SimpleNamespace(value="CONFIRMED"),
        evidence_ids=("evidence-legacy",),
        is_confirmed=True,
    )
    app._intelligence_reader.read_current = lambda _intelligence_id: verified  # type: ignore[method-assign]
    app._intelligence_reader.read_current_card = lambda _intelligence_id: SimpleNamespace(  # type: ignore[method-assign]
        verified=verified,
        core_conclusion="Legacy conclusion.",
        user_relevant_information=(),
        important_new_information=(),
        meaningful_details=(),
        filtered_noise=(),
        source_id="source-1",
        video_id="abcdefghijk",
        preference_ids=(),
        source_policy_revision_id=None,
    )
    app._repository.get_video = lambda _video_id: SimpleNamespace(source_url=None)  # type: ignore[method-assign]
    app._repository.list_intelligence_revision_evidence_relations = lambda _revision_id: (  # type: ignore[method-assign]
        SimpleNamespace(
            revision_id="revision-legacy",
            evidence_id="evidence-legacy",
            stance=None,
        ),
    )
    app._repository.get_evidence = lambda _evidence_id: SimpleNamespace(  # type: ignore[method-assign]
        evidence_id="evidence-legacy",
        artifact_id="artifact-legacy",
        start_ms=1000,
        end_ms=2000,
        language="en",
        lineage_kind=SimpleNamespace(value="ORIGINAL_TRANSCRIPT"),
        role=SimpleNamespace(value="PRIMARY_ORIGINAL"),
        source_excerpt=None,
    )

    projection = app._intelligence_projection("intel-legacy")

    link = projection["card"]["evidence_links"][0]
    assert link["original_excerpt"] is None
    assert link["stance"] is None
    assert link["translated_excerpt"] is None


def test_intelligence_feed_rechecks_each_identity_and_never_emits_raw_content(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    app._repository.list_current_intelligence_ids = lambda *, limit: ("missing",)  # type: ignore[method-assign]

    status, payload = app.handle("GET", "/api/v1/intelligence")

    assert status == 200
    item = payload["intelligence"][0]
    assert item["status"] == "UNAVAILABLE"
    assert item["trusted"] is False
    assert "card" not in item


def test_source_video_projection_has_a_scoped_repository_reader(tmp_path: Path) -> None:
    app = _app(tmp_path)
    assert app._repository.list_source_videos("missing-source", limit=10) == ()


def test_transcript_projection_reads_only_hash_bound_canonical_content(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _record_video(app, "abcdefghijk")
    body = b"Safe canonical transcript."
    path = tmp_path / "data" / "transcripts" / "abcdefghijk.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    app._repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="transcript-artifact",
            artifact_key="transcript/abcdefghijk",
            video_id="abcdefghijk",
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="transcripts/abcdefghijk.txt",
            content_hash=sha256(body).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=datetime(2026, 9, 1, tzinfo=UTC),
    )

    projection = app._transcript_projection("abcdefghijk")
    assert projection["status"] == "AVAILABLE"
    assert projection["text"] == body.decode()
    assert str(tmp_path) not in str(projection)
    assert "relative_path" not in projection


def test_transcript_projection_fails_closed_when_artifact_hash_is_invalid(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _record_video(app, "abcdefghijk")
    path = tmp_path / "data" / "transcripts" / "abcdefghijk.txt"
    path.parent.mkdir(parents=True)
    path.write_text("tampered", encoding="utf-8")
    app._repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="transcript-artifact",
            artifact_key="transcript/abcdefghijk",
            video_id="abcdefghijk",
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="transcripts/abcdefghijk.txt",
            content_hash=sha256(b"original").hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert app._transcript_projection("abcdefghijk") == {
        "status": "UNAVAILABLE",
        "code": "TRANSCRIPT_UNAVAILABLE",
        "reason": "The recorded canonical transcript cannot be safely read.",
    }


def test_transcript_failed_state_uses_only_the_safe_failure_code(
    tmp_path: Path, monkeypatch: object
) -> None:
    app = _app(tmp_path)
    failed = SimpleNamespace(
        status=JobStatus.FAILED_FINAL,
        last_error_code="LOCAL_RESOURCE",
    )
    monkeypatch.setattr(app._repository, "latest_video_job", lambda *_args, **_kwargs: failed)  # type: ignore[union-attr]
    projection = app._transcript_projection("abcdefghijk")
    assert projection == {
        "status": "FAILED",
        "code": "LOCAL_RESOURCE",
        "reason": "Transcript processing ended without a canonical transcript.",
    }


def test_history_preserves_ambiguous_and_weekly_keeps_unknown_version(
    tmp_path: Path, monkeypatch: object
) -> None:
    app = _app(tmp_path)
    ambiguous = SimpleNamespace(
        job_id="job-1",
        target_stage=SimpleNamespace(value="ANALYSIS"),
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 1, tzinfo=UTC),
        finished_at=datetime(2026, 9, 1, tzinfo=UTC),
        status=JobStatus.FAILED_FINAL,
        last_error_code="AMBIGUOUS",
    )
    monkeypatch.setattr(app._repository, "list_video_jobs", lambda *_args, **_kwargs: (ambiguous,))  # type: ignore[union-attr]
    monkeypatch.setattr(app._repository, "list_job_attempts", lambda *_args: ())  # type: ignore[union-attr]
    history = app._history_projection("abcdefghijk")
    ambiguous_event = next(item for item in history if item["status"] == "AMBIGUOUS")
    assert "will not automatically retry" in str(ambiguous_event["summary"])

    app._repository.upsert_report(
        ReportWrite(
            report_id="weekly-1",
            timezone="Asia/Shanghai",
            iso_year=2026,
            iso_week=36,
            relative_path=None,
            content_hash=None,
            status=ReportStatus.WRITTEN,
        ),
        now=datetime(2026, 9, 1, tzinfo=UTC),
    )
    weekly = app.handle("GET", "/api/v1/weekly")[1]["weekly"]
    assert weekly[0]["version"] == "UNKNOWN"
    assert weekly[0]["linkage"]["status"] == "UNAVAILABLE_IN_CURRENT_AUTHORITY"


def test_source_recent_videos_are_joined_only_through_persisted_links(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _, created = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps({"url": "https://youtu.be/abcdefghijk", "processing_policy": "DISCOVER_ONLY"}).encode(),
    )
    source_id = created["source"]["source_id"]
    _record_video(app, "abcdefghijk")
    _record_video(app, "zzzzzzzzzzz")
    app._repository.link_source_video(source_id, "abcdefghijk", discovered_at=datetime(2026, 9, 1, tzinfo=UTC))

    detail = app.handle("GET", f"/api/v1/sources/{source_id}")[1]
    assert [item["video_id"] for item in detail["recent_videos"]] == ["abcdefghijk"]
