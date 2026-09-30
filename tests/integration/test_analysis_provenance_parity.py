"""Runtime <-> Weekly Analysis provenance parity.

Both trusted consumers of a persisted Summary artifact must reach the *same*
provenance conclusion for the same bytes, artifact row and ledger row.  Runtime
holds an already-parsed ``AnalysisResult``; Weekly must parse the bytes itself.
The interesting divergence is therefore any field where Weekly substitutes its
own raw-JSON reading for a value the domain contract defaults.

This module drives both real code paths -- ``RuntimeOperations``
``validate_persisted_analysis_pointer`` and ``WeeklyReportService``
``_verified_analysis`` -- over one shared fixture, and compares verdicts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.analysis_provenance import (
    ANALYSIS_PROVIDER_SET,
    ANALYSIS_RESULT_SCHEMA_VERSION,
)
from youtube_intel.config import AppConfig, load_app_config
from youtube_intel.domain import AnalysisResult, EvidenceSource
from youtube_intel.reporting import _verified_analysis, _WeeklySummaryNotTrusted
from youtube_intel.runtime import RuntimeOperations
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    JobType,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    RetentionClass,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
)
from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint
from youtube_intel.summary_evidence_authority import hydrate_summary_evidence
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry

NOW = datetime(2026, 9, 30, 18, 0, tzinfo=UTC)
PIPELINE_VERSION = "runtime-v1"
NORMALIZED = "b" * 64
PARITY_INPUT_IDENTITY = "c" * 64
VIDEO_ID = "ausLKMojXaY"
CANONICAL_ARTIFACT = "parity-canonical"
JOB_ID = "parity-analysis-job"
RAW_ARTIFACT = "parity-raw"
CUE_TEXTS = tuple(f"cue{index} source sentence" for index in range(4))


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Verdict:
    accepted: bool
    kind: str


def _runtime_verdict(operations, video_id: str, artifact_id: str) -> Verdict:
    from youtube_intel.summary_evidence_authority import (
        LegacySummaryNotCurrentAuthority,
        SummaryCitationNotDurable,
    )

    try:
        outcome = RuntimeOperations.validate_persisted_analysis_pointer(
            config=operations._config,
            repository=operations._repository,
            data_root=operations._data_root,
            video_id=video_id,
            artifact_id=artifact_id,
        )
    except LegacySummaryNotCurrentAuthority:
        return Verdict(False, "stale-legacy")
    except SummaryCitationNotDurable:
        return Verdict(False, "corrupt-citation")
    except Exception as error:  # noqa: BLE001 - parity compares classes, not strings
        return Verdict(False, type(error).__name__)
    return Verdict(True, "accepted" if isinstance(outcome, AnalysisResult) else "accepted")


def _weekly_verdict(operations, video_id: str, artifact_id: str) -> Verdict:
    try:
        result = _verified_analysis(
            operations._data_root,
            operations._repository.get_artifact(artifact_id),
            video_id,
            operations._repository,
        )
    except _WeeklySummaryNotTrusted:
        return Verdict(False, "candidate-local")
    except Exception as error:  # noqa: BLE001
        return Verdict(False, type(error).__name__)
    return Verdict(True, "accepted" if isinstance(result, AnalysisResult) else "accepted")


#: Semantic categories both readers must agree on.  Exception *classes* may
#: differ where the architecture forces it, but the verdict category may not.
_RUNTIME_CATEGORY = {"accepted": "accepted", "stale-legacy": "stale"}
_WEEKLY_CATEGORY = {
    "accepted": "accepted",
    "candidate-local": "local",
    "AnalysisProviderCallProvenanceError": "fatal",
}


def _runtime_category(verdict: Verdict) -> str:
    if not verdict.accepted and verdict.kind not in _RUNTIME_CATEGORY:
        return "fatal"
    return _RUNTIME_CATEGORY[verdict.kind]


def _weekly_category(verdict: Verdict) -> str:
    if not verdict.accepted and verdict.kind not in _WEEKLY_CATEGORY:
        return "fatal"
    return _WEEKLY_CATEGORY[verdict.kind]


def _same_outcome(left: Verdict, right: Verdict) -> bool:
    """Semantic parity: both accept, or both refuse.

    The concrete refusal class may differ where the architecture forces it --
    Runtime inspects an already-parsed object while Weekly must parse the bytes,
    so an unparseable payload is necessarily candidate-local for Weekly.  What
    must never differ is whether the artifact is trusted.
    """

    return left.accepted == right.accepted


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


def _project(workspace: Path) -> AppConfig:
    (workspace / "config").mkdir(parents=True, exist_ok=True)
    (workspace / "vault").mkdir(parents=True, exist_ok=True)
    (workspace / "templates").mkdir(parents=True, exist_ok=True)
    (workspace / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: UC_PARITY\n", encoding="utf-8"
    )
    (workspace / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{'1' * 64}
cloud:
  enabled: false
  model: gpt-4.1-mini
  api_key_env: OPENAI_API_KEY
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {workspace / 'vault'}
  vault_subdir: Vault
""",
        encoding="utf-8",
    )
    return load_app_config(
        workspace / "config" / "channels.yaml", workspace / "config" / "settings.yaml"
    )


def _build(workspace: Path):
    from youtube_intel.state import SQLiteStateRepository

    config = _project(workspace)
    data_root = (workspace / "data").resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteStateRepository(data_root / "state.sqlite3")
    repository.initialize(now=NOW)

    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC_PARITY",
            channel_name="Parity Channel",
            title="Parity Video",
            description="d",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version=PIPELINE_VERSION,
        now=NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=CANONICAL_ARTIFACT,
            artifact_key=f"transcript/{VIDEO_ID}",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{VIDEO_ID}/canonical.txt",
            content_hash=hashlib.sha256(b"parity").hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=VIDEO_ID,
            canonical_artifact_id=CANONICAL_ARTIFACT,
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000,
                    end_ms=(index + 1) * 1000,
                    text=text,
                )
                for index, text in enumerate(CUE_TEXTS)
            ),
        ),
        now=NOW,
    )
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
        (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED),
    ):
        repository.advance_pipeline(
            video_id=VIDEO_ID,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=NOW,
        )
    repository.create_job(
        job_id=JOB_ID,
        scope_key=f"video:{VIDEO_ID}:{ProcessingStage.ANALYSIS.value}",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(
        owner="parity-owner",
        lease_until=NOW + timedelta(minutes=5),
        now=NOW,
        video_id=VIDEO_ID,
    )
    durable = _promote_evidence(repository)

    operations = RuntimeOperations.__new__(RuntimeOperations)
    operations._config = config
    operations._repository = repository
    operations._data_root = data_root
    return operations, repository, durable


def _promote_evidence(repository) -> str:
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="Parity Video",
        channel_name="Parity Channel",
        description="d",
        input_identity="a" * 64,
    )
    ref = next(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    hydrated = hydrate_summary_evidence(
        SummaryDraft(
            one_sentence_summary="s",
            core_points=(
                SummaryDraftPoint(text="t", kind="fact", evidence_refs=(ref,)),
            ),
            keywords=("k",),
        ),
        registry,
        video_id=VIDEO_ID,
        canonical_artifact_id=CANONICAL_ARTIFACT,
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )
    promotion = hydrated.promotions[0]
    repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    return promotion.evidence_id


def _payload(durable: str, **overrides) -> dict:
    """Explicitly populated AnalysisResult fields; overrides drop a key when None."""
    payload = {
        "one_sentence_summary": "Parity summary.",
        "core_points": [
            {"text": "t", "kind": "fact", "evidence_ids": [durable]}
        ],
        "keywords": ["k"],
        "evidence": [
            {
                "evidence_id": durable,
                "source": "transcript_sample",
                "excerpt": "e",
            }
        ],
        "request_hash": NORMALIZED,
        "provider": "ollama",
        "model": "qwen3:8b",
        "prompt_version": "analysis-prompt-v6",
        "schema_version": "analysis-result-v1",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def _install(
    operations,
    repository,
    durable: str,
    *,
    payload: dict | bytes,
    ledger_prompt: str = "analysis-prompt-v6",
    ledger_schema: str = ANALYSIS_RESULT_SCHEMA_VERSION,
    ledger_operation: str = "local-analysis",
    ledger_provider: str = "ollama",
    ledger_model: str = "qwen3:8b",
) -> str:
    """Persist one Analysis artifact plus its ledger row through the public API.

    Only ``SQLiteStateRepository`` methods are used, exactly as the production
    runtime persists an Analysis result, so the parity matrix cannot drift into
    a hand-built database shape that the real code paths would never accept.
    """

    from youtube_intel.state import PipelineStatus, ProviderCallRequest

    request = ProviderCallRequest(
        operation=ledger_operation,
        normalized_input_hash=PARITY_INPUT_IDENTITY,
        provider=ledger_provider,
        model=ledger_model,
        prompt_version=ledger_prompt,
        schema_version=ledger_schema,
        deterministic_artifact_key=f"analysis/{NORMALIZED}/raw",
    )
    request_hash = request.request_hash
    data_root = operations._data_root
    if isinstance(payload, dict):
        body = json.dumps({**payload, "request_hash": request.request_hash}).encode("utf-8")
    else:
        body = payload
    raw_content = b'{"raw": "parity analysis response"}'

    raw_relative = f"analysis/{request_hash}/raw.json"
    structured_relative = f"analysis/{request_hash}/structured.json"
    (data_root / f"analysis/{request_hash}").mkdir(parents=True, exist_ok=True)
    (data_root / raw_relative).write_bytes(raw_content)
    (data_root / structured_relative).write_bytes(body)

    raw_id = f"analysis-raw-{hashlib.sha256(raw_relative.encode()).hexdigest()[:16]}"
    structured_id = f"analysis-structured-{hashlib.sha256(structured_relative.encode()).hexdigest()[:16]}"
    raw = ArtifactWrite(
            artifact_id=raw_id,
            artifact_key=f"analysis/{request_hash}/raw",
            video_id=VIDEO_ID,
            job_id=JOB_ID,
            kind=ArtifactKind.ANALYSIS_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=raw_relative,
            content_hash=hashlib.sha256(raw_content).hexdigest(),
            provider=ledger_provider,
            model=ledger_model,
            producer_version="analysis-raw-v1",
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=NOW + timedelta(days=30),
        )
    structured = ArtifactWrite(
            artifact_id=structured_id,
            artifact_key=f"analysis/{request_hash}/structured",
            video_id=VIDEO_ID,
            job_id=JOB_ID,
            kind=ArtifactKind.ANALYSIS_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=structured_relative,
            content_hash=hashlib.sha256(body).hexdigest(),
            provider=ledger_provider,
            model=ledger_model,
            producer_version="analysis-structured-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )
    repository.upsert_artifact(raw, now=NOW)
    repository.upsert_artifact(structured, now=NOW)
    repository.reserve_provider_call(
        request,
        owner="parity-owner",
        lease_until=NOW + timedelta(minutes=5),
        available_at=NOW,
        now=NOW,
    )
    repository.complete_provider_call(
        request_hash=request_hash,
        owner="parity-owner",
        response_artifact_id=raw_id,
        input_tokens=None,
        output_tokens=None,
        cost_microusd=None,
        now=NOW,
    )
    repository.complete_stage(
        job_id=JOB_ID,
        owner="parity-owner",
        video_id=VIDEO_ID,
        expected_status=PipelineStatus.SCORED,
        target_status=PipelineStatus.ANALYSIS_READY,
        pipeline_version=PIPELINE_VERSION,
        artifacts=(raw, structured),
        provider_call=None,
        now=NOW,
    )
    repository.promote_current_local_summary(
        video_id=VIDEO_ID, artifact_id=structured_id, output_language="zh-CN", now=NOW
    )
    return structured_id


# ---------------------------------------------------------------------------
# Parity matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "payload_kwargs", "ledger_kwargs", "expected_runtime", "expected_weekly"),
    [
        # (case, payload overrides, ledger overrides, runtime verdict, weekly verdict)
        #
        # ``stale`` and ``local`` are the same semantic outcome expressed through
        # each reader's own boundary: runtime raises a typed legacy exception, while
        # Weekly excludes the single candidate and keeps its valid siblings.  A
        # stale Summary must never be reported as a provenance forgery (``fatal``),
        # and a forged one must never be softened into merely ``stale``.
        ("explicit normal v6", {}, {}, "accepted", "accepted"),
        ("omitted schema_version", {"schema_version": None}, {}, "accepted", "accepted"),
        ("omitted prompt_version", {"prompt_version": None}, {}, "stale", "local"),
        ("genuine v5", {"prompt_version": "analysis-prompt-v5"},
         {"ledger_prompt": "analysis-prompt-v5"}, "stale", "local"),
        ("explicit wrong prompt", {"prompt_version": "analysis-prompt-v5"}, {},
         "stale", "local"),
        ("provider mismatch", {"provider": "openai"}, {}, "fatal", "fatal"),
        ("model mismatch", {"model": "some-other-model"}, {}, "fatal", "fatal"),
        ("ledger schema mismatch", {}, {"ledger_schema": "analysis-result-v0"},
         "fatal", "fatal"),
        ("non-analysis operation", {}, {"ledger_operation": "local-scoring"},
         "fatal", "fatal"),
        # Runtime reads bytes itself and refuses to parse; Weekly must isolate the
        # candidate so a valid sibling survives.  That asymmetry is the frozen
        # candidate-isolation rule, not a provenance divergence.
        ("malformed json", "malformed", {}, "fatal", "local"),
        ("unknown prompt identity", {"prompt_version": "analysis-prompt-v7"}, {},
         "fatal", "local"),
    ],
)
def test_runtime_and_weekly_agree_on_provenance(
    tmp_path: Path,
    case: str,
    payload_kwargs: dict,
    ledger_kwargs: dict,
    expected_runtime: str,
    expected_weekly: str,
) -> None:
    operations, repository, durable = _build(tmp_path)
    payload: dict | bytes = (
        b'{"one_sentence_summary": not-json'
        if payload_kwargs == "malformed"
        else _payload(durable, **payload_kwargs)
    )
    artifact_id = _install(
        operations, repository, durable, payload=payload,
        **ledger_kwargs,
    )
    runtime = _runtime_verdict(operations, VIDEO_ID, artifact_id)
    weekly = _weekly_verdict(operations, VIDEO_ID, artifact_id)
    assert _same_outcome(runtime, weekly), (
        f"{case}: runtime={runtime} weekly={weekly}"
    )
    assert _runtime_category(runtime) == expected_runtime, (
        f"{case}: runtime={runtime} category={_runtime_category(runtime)} "
        f"expected={expected_runtime}"
    )
    assert _weekly_category(weekly) == expected_weekly, (
        f"{case}: weekly={weekly} category={_weekly_category(weekly)} "
        f"expected={expected_weekly}"
    )


def test_omitted_schema_version_uses_the_domain_default(tmp_path: Path) -> None:
    """The reported defect: an omitted schema must not become an empty string."""

    operations, repository, durable = _build(tmp_path)
    artifact_id = _install(
        operations, repository, durable,
        payload=_payload(durable, schema_version=None),
    )
    parsed = AnalysisResult.model_validate(_payload(durable, schema_version=None))
    assert parsed.schema_version == ANALYSIS_RESULT_SCHEMA_VERSION
    assert _weekly_verdict(operations, VIDEO_ID, artifact_id).accepted


def test_omitted_prompt_version_uses_the_domain_default(tmp_path: Path) -> None:
    operations, repository, durable = _build(tmp_path)
    artifact_id = _install(
        operations, repository, durable,
        payload=_payload(durable, prompt_version=None),
    )
    parsed = AnalysisResult.model_validate(_payload(durable, prompt_version=None))
    # The historical default, so both paths classify it as stale, not forged.
    assert parsed.prompt_version == "analysis-prompt-v1"
    runtime = _runtime_verdict(operations, VIDEO_ID, artifact_id)
    weekly = _weekly_verdict(operations, VIDEO_ID, artifact_id)
    assert runtime.kind == "stale-legacy"
    assert weekly.kind == "candidate-local"


def test_genuine_v5_is_stale_not_forged(tmp_path: Path) -> None:
    operations, repository, durable = _build(tmp_path)
    artifact_id = _install(
        operations, repository, durable,
        payload=_payload(durable, prompt_version="analysis-prompt-v5"),
        ledger_prompt="analysis-prompt-v5",
    )
    runtime = _runtime_verdict(operations, VIDEO_ID, artifact_id)
    weekly = _weekly_verdict(operations, VIDEO_ID, artifact_id)
    assert runtime.kind == "stale-legacy"
    assert weekly.kind == "candidate-local"


def test_malformed_payload_under_genuine_ledger_is_candidate_local(
    tmp_path: Path,
) -> None:
    operations, repository, durable = _build(tmp_path)
    artifact_id = _install(
        operations, repository, durable,
        payload=b'{"one_sentence_summary": not-json',
    )
    weekly = _weekly_verdict(operations, VIDEO_ID, artifact_id)
    assert weekly.kind == "candidate-local"


def test_shared_contract_is_not_duplicated_in_reporting() -> None:
    import inspect

    from youtube_intel import reporting

    source = inspect.getsource(reporting._verified_analysis)
    # Payload provenance comes from the parsed result, never from raw JSON reads.
    assert 'document.get(' not in source
    assert "require_analysis_call_matches_payload" in source
    assert 'prompt_version=str(' not in source
    assert ANALYSIS_PROVIDER_SET == frozenset({"ollama", "openai"})
