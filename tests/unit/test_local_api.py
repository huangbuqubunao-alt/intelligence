import json
from datetime import UTC, datetime
from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisResult,
    Availability,
    JobStatus,
    LiveStatus,
    ProviderCallMetadata,
    VideoMetadata,
)
from youtube_intel.local_api import _LOCAL_ORIGIN, ApiError, LocalApiApplication
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


def test_video_detail_distinguishes_not_processed_admitted_and_no_new(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _record_video(app, "video-result")

    status, not_processed = app.handle("GET", "/api/v1/videos/video-result")
    assert status == 200
    assert not_processed["intelligence_result"] == {
        "status": "NOT_PROCESSED",
        "execution_id": None,
        "has_new_intelligence": None,
        "intelligence_id": None,
        "revision_id": None,
        "updated_at": None,
    }

    app._repository.latest_distillation_execution_for_video = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        execution_id="exec-admitted",
        status="SUCCEEDED",
        output_language="zh-CN",
        intelligence_id="intel-1",
        revision_id="revision-1",
        updated_at=datetime(2026, 9, 1, 1, tzinfo=UTC),
    )
    admitted = app.handle("GET", "/api/v1/videos/video-result")[1]
    assert admitted["intelligence_result"]["has_new_intelligence"] is True

    app._repository.latest_distillation_execution_for_video = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        execution_id="exec-zero",
        status="SUCCEEDED_NO_NEW_INTELLIGENCE",
        output_language="zh-CN",
        intelligence_id=None,
        revision_id=None,
        updated_at=datetime(2026, 9, 1, 2, tzinfo=UTC),
    )
    no_new = app.handle("GET", "/api/v1/videos/video-result")[1]
    assert no_new["intelligence_result"] == {
        "status": "SUCCEEDED_NO_NEW_INTELLIGENCE",
        "execution_id": "exec-zero",
        "output_language": "zh-CN",
        "has_new_intelligence": False,
        "intelligence_id": None,
        "revision_id": None,
        "updated_at": "2026-09-01T02:00:00Z",
    }


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


@pytest.mark.parametrize(
    ("transcript_status", "error_code", "expected_status", "retry_allowed"),
    [
        (JobStatus.RETRY_PENDING, "RATE_LIMITED", "RETRY_REQUIRED", True),
        (JobStatus.PENDING, None, "READING_CAPTIONS", True),
        (JobStatus.PENDING, "RATE_LIMITED", "RETRY_REQUIRED", True),
        (JobStatus.RUNNING, None, "READING_CAPTIONS", True),
        (JobStatus.FAILED_FINAL, "CAPABILITY_UNAVAILABLE", "FAILED", False),
    ],
)
def test_metadata_completion_does_not_hide_unfinished_caption_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    transcript_status: JobStatus, error_code: str | None,
    expected_status: str, retry_allowed: bool,
) -> None:
    from youtube_intel.domain import ProcessingStage

    app = _app(tmp_path)
    _record_video(app, "abcdefghijk")
    app.handle("POST", "/api/v1/sources", json.dumps({
        "url": "https://youtu.be/abcdefghijk", "processing_policy": "DISCOVER_ONLY",
    }).encode())
    available_at = datetime(2026, 9, 1, 1, tzinfo=UTC)
    metadata = SimpleNamespace(status=JobStatus.SUCCEEDED,
        target_stage=ProcessingStage.METADATA, available_at=available_at,
        last_error_code=None)
    transcript = SimpleNamespace(status=transcript_status,
        target_stage=ProcessingStage.TRANSCRIPT, available_at=available_at,
        last_error_code=error_code)
    monkeypatch.setattr(app._repository, "latest_video_job",
        lambda _id, *, target_stage=None: transcript
        if target_stage is ProcessingStage.TRANSCRIPT else metadata)

    status, detail = app.handle("GET", "/api/v1/videos/abcdefghijk")
    assert status == 200
    assert detail["video"]["processing_status"] == expected_status
    assert detail["video"]["processing_job"]["stage"] == "TRANSCRIPT"
    assert detail["video"]["processing_job"]["error_code"] == error_code
    assert detail["video"]["retry_allowed"] is retry_allowed
    assert detail["video"]["source_id"]


def test_safe_provider_projection_reports_bounded_local_authority(tmp_path: Path) -> None:
    status, payload = _app(tmp_path).handle("GET", "/api/v1/settings")
    assert status == 200
    assert payload["model_preference"]["active_production_default"] is None
    local = payload["providers"][0]
    assert local["provider"] == "Local"
    assert local["model"] == "qwen3:8b"
    assert local["credential_status"] == "NOT_REQUIRED"
    assert local["qualification_status"] == "INTELLIGENCE_UNQUALIFIED"
    assert local["authorized"] is False
    assert local["production_eligible"] is False
    assert local["scope"] == "SCORING_SUMMARY_ONLY"
    nim = next(item for item in payload["providers"] if item["provider"] == "NVIDIA NIM")
    assert nim["provider"] == "NVIDIA NIM"
    assert nim["qualification_status"] == "M12_REQUALIFICATION_REQUIRED"
    assert nim["authorized"] is False
    assert nim["production_eligible"] is False
    assert "secret" not in str(payload).lower()


def test_completed_plain_caption_import_needs_attention_instead_of_polling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from youtube_intel.domain import PipelineStatus, ProcessingStage

    app = _app(tmp_path)
    _record_video(app, "abcdefghijk")
    record = app._repository.get_video("abcdefghijk")
    assert record is not None
    monkeypatch.setattr(app._repository, "get_video", lambda _id: replace(record, pipeline_status=PipelineStatus.TRANSCRIPT_READY))
    monkeypatch.setattr(app._repository, "latest_content_job", lambda _id: SimpleNamespace(
        status=JobStatus.SUCCEEDED, target_stage=ProcessingStage.TRANSCRIPT,
        available_at=datetime(2026, 9, 1, tzinfo=UTC), last_error_code=None,
    ))
    status, detail = app.handle("GET", "/api/v1/videos/abcdefghijk")
    assert status == 200
    assert detail["video"]["processing_status"] == "NEEDS_ATTENTION"
    assert detail["video"]["caption_timing_status"] == "UNAVAILABLE"


def test_qualified_moonshot_projection_keeps_consent_per_execution() -> None:
    from youtube_intel.orchestration import provider_model_statuses

    ready = next(
        item for item in provider_model_statuses(
            None, None, moonshot_qualified=True, moonshot_credential_available=True
        ) if item.provider == "moonshot"
    )
    assert ready.model == "kimi-k2.6"
    assert ready.production_eligible is True
    assert ready.authorized is False
    assert ready.credential_status == "AVAILABLE"
    missing_credential = next(
        item for item in provider_model_statuses(
            None, None, moonshot_qualified=True, moonshot_credential_available=False
        ) if item.provider == "moonshot"
    )
    assert missing_credential.production_eligible is False


def test_intelligence_card_projects_readable_persisted_provenance(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    verified = SimpleNamespace(
        intelligence_id="intel-1",
        revision_id="revision-1",
        claim_kind=SimpleNamespace(value="EVIDENCE_BACKED_STATEMENT"),
        state=SimpleNamespace(value="UPDATED"),
        evidence_ids=("evidence-1",),
        is_confirmed=True,
    )
    card = SimpleNamespace(
        verified=verified,
        core_conclusion="Transformer attention weighs relevant context.",
        user_relevant_information=("This helps explain current LLM behavior.",),
        important_new_information=("Context is weighted per token.",),
        meaningful_details=("The mechanism repeats across layers.",),
        filtered_noise=(),
        source_id="source-1",
        video_id="wjZofJX0v4M",
        preference_ids=(),
        source_policy_revision_id="policy-1",
    )
    app._intelligence_reader = SimpleNamespace(  # type: ignore[assignment]
        read_current=lambda intelligence_id: verified,
        read_current_card=lambda intelligence_id: card,
    )
    app._repository.get_source_subscription = lambda source_id: SimpleNamespace(  # type: ignore[method-assign]
        display_name=None,
        canonical_url="https://www.youtube.com/channel/3blue1brown",
        channel_id="UCYO_jab_esuFRV4b17AJtAw",
        video_id=None,
    )
    app._repository.get_video = lambda video_id: SimpleNamespace(  # type: ignore[method-assign]
        title="Transformers, the tech behind LLMs | Deep Learning Chapter 5",
        channel_name="3Blue1Brown",
        source_url="https://www.youtube.com/watch?v=wjZofJX0v4M",
    )
    app._repository.resolve_verified_evidence_text = lambda evidence_id: (
        SimpleNamespace(  # type: ignore[method-assign]
            evidence_id=evidence_id,
            video_id="wjZofJX0v4M",
            locator_type="TIMED_MEDIA",
            start_ms=18_000,
            end_ms=42_000,
            excerpt="Attention lets each token weigh relevant context from other tokens.",
        )
    )
    app._repository.list_intelligence_revision_evidence_relations = lambda revision_id: (  # type: ignore[method-assign]
        SimpleNamespace(
            revision_id=revision_id,
            evidence_id="evidence-1",
            stance=SimpleNamespace(value="supporting"),
        ),
    )
    app._repository.get_evidence = lambda evidence_id: SimpleNamespace(  # type: ignore[method-assign]
        evidence_id=evidence_id,
        video_id="wjZofJX0v4M",
        artifact_id="transcript-artifact-1",
        start_ms=18_000,
        end_ms=42_000,
        language="en",
        lineage_kind=SimpleNamespace(value="ORIGINAL_TRANSCRIPT"),
        role=SimpleNamespace(value="PRIMARY_ORIGINAL"),
        source_excerpt=None,
    )

    projection = app._intelligence_projection("intel-1")

    assert projection["trusted"] is True
    projected_card = cast(dict[str, object], projection["card"])
    assert projected_card["source_display_name"] == "3Blue1Brown"
    assert projected_card["source_url"] == "https://www.youtube.com/channel/3blue1brown"
    assert projected_card["video_title"] == (
        "Transformers, the tech behind LLMs | Deep Learning Chapter 5"
    )
    assert cast(list[dict[str, object]], projected_card["evidence_links"])[0] == {
        "evidence_id": "evidence-1",
        "artifact_id": "transcript-artifact-1",
        "start_ms": 18_000,
        "end_ms": 42_000,
        "language": "en",
        "lineage_kind": "ORIGINAL_TRANSCRIPT",
        "role": "PRIMARY_ORIGINAL",
        "original_excerpt": "Attention lets each token weigh relevant context from other tokens.",
        "translated_excerpt": None,
        "translated_language": None,
        "translation_target_language": "zh-CN",
        "stance": "supporting",
    }


@pytest.mark.parametrize(
    "forged_field", ("qualified", "authorized", "production_eligible")
)
def test_frontend_cannot_submit_provider_authority(
    tmp_path: Path, forged_field: str
) -> None:
    app = _app(tmp_path)

    with pytest.raises(ApiError) as captured:
        app.handle(
            "PUT",
            "/api/v1/settings/model-preference",
            json.dumps(
                {
                    "provider": "Kimi",
                    "model": "moonshotai/kimi-k3",
                    forged_field: True,
                }
            ).encode(),
        )

    assert captured.value.status == 422


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

    with pytest.raises(ApiError) as rejected:
        app.handle(
            "PUT",
            "/api/v1/settings/output-language",
            json.dumps({"output_language": "fr"}).encode(),
        )

    assert rejected.value.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rejected.value.code == "VALIDATION_ERROR"
    assert app.handle("GET", "/api/v1/settings")[1]["general"]["output_language"] == "zh-CN"


def test_manual_check_is_explicitly_blocked_by_runtime_guard(tmp_path: Path) -> None:
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


def test_local_summary_reads_only_explicit_artifact_and_sealed_language(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    result = AnalysisResult.model_validate({
        "one_sentence_summary": "忠实摘要。",
        "core_points": [{"text": "有证据的要点。", "kind": "fact", "evidence_ids": ["e1"]}],
        "keywords": ["主题"],
        "evidence": [{"evidence_id": "e1", "source": "title", "excerpt": "English title"}],
        "provider": "ollama", "model": "qwen3:8b",
        "prompt_version": "analysis-prompt-v4", "request_hash": "a" * 64,
    })
    outcome = AnalysisCompleted(
        result=result,
        call=ProviderCallMetadata(
            provider="ollama", model="qwen3:8b",
            started_at=datetime(2026, 9, 1, tzinfo=UTC),
            finished_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
    )
    app._repository.current_local_summary_pointer = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        artifact_id="selected-artifact", output_language="zh-CN"
    )
    requested: list[tuple[str, str]] = []

    def read_selected(video_id: str, artifact_id: str) -> AnalysisCompleted:
        requested.append((video_id, artifact_id))
        return outcome

    app._analysis_reader = read_selected
    projection = app._note_projection("abcdefghijk")
    assert requested == [("abcdefghijk", "selected-artifact")]
    assert projection["v2"]["language"] == "zh-CN"
    assert projection["v2"]["summary"] == "忠实摘要。"
    assert projection["v2"]["evidence_references"][0]["excerpt"] == "English title"

    app._analysis_reader = lambda _video_id, _artifact_id: (_ for _ in ()).throw(  # type: ignore[assignment]
        ValueError("selected artifact failed verification")
    )
    assert app._note_projection("abcdefghijk")["v2"]["status"] == "UNAVAILABLE"


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
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        channel_name="Fixture channel",
        title="Fixture video",
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
        video_id="abcdefghijk",
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
            "translation_target_language": "zh-CN",
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
    app._repository.get_video = lambda _video_id: SimpleNamespace(  # type: ignore[method-assign]
        source_url=None,
        channel_name="Fixture channel",
        title="Fixture video",
    )
    app._repository.list_intelligence_revision_evidence_relations = lambda _revision_id: (  # type: ignore[method-assign]
        SimpleNamespace(
            revision_id="revision-legacy",
            evidence_id="evidence-legacy",
            stance=None,
        ),
    )
    app._repository.get_evidence = lambda _evidence_id: SimpleNamespace(  # type: ignore[method-assign]
        evidence_id="evidence-legacy",
        video_id="abcdefghijk",
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
    monkeypatch.setattr(
        app._repository, "latest_video_job", lambda *_args, **_kwargs: failed
    )  # type: ignore[union-attr]
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
    monkeypatch.setattr(
        app._repository, "list_video_jobs", lambda *_args, **_kwargs: (ambiguous,)
    )  # type: ignore[union-attr]
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
        json.dumps(
            {
                "url": "https://youtu.be/abcdefghijk",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    source_id = created["source"]["source_id"]
    _record_video(app, "abcdefghijk")
    _record_video(app, "zzzzzzzzzzz")
    app._repository.link_source_video(
        source_id, "abcdefghijk", discovered_at=datetime(2026, 9, 1, tzinfo=UTC)
    )

    detail = app.handle("GET", f"/api/v1/sources/{source_id}")[1]
    assert [item["video_id"] for item in detail["recent_videos"]] == ["abcdefghijk"]
