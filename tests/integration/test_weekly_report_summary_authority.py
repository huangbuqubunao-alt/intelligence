"""P0: Weekly Report must consume only current trusted Summary authority.

Before this fix, ``WeeklyReportService._verified_analysis`` verified artifact
bytes and basic provenance but never applied current Summary authority, so a
hash-valid ``analysis-prompt-v5`` artifact could put legacy Summary text and
temporary ``t*``/``m*`` refs into a Weekly Report.

Frozen invariant proven here:

    Weekly reporting reuses the shared current-Summary gate, so it has exactly
    the same authority semantics as ``RuntimeOperations._load_analysis``.  An
    ineligible Summary excludes one candidate; it never publishes legacy text,
    never regenerates, and never calls a provider.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.domain import (
    AnalysisPoint,
    AnalysisResult,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PointKind,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.reporting import (
    WeeklyReportService,
    render_weekly_report,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    PipelineStatus,
    ProviderCallStatus,
    RetentionClass,
    StorageRoot,
    VideoRecord,
    WeeklyCandidateRecord,
)
from youtube_intel.summary_evidence_authority import CURRENT_SUMMARY_PROMPT_VERSION

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)
LEGACY_SUMMARY_TEXT = "LEGACY-V5-SUMMARY-TEXT-MUST-NOT-PUBLISH"
LEGACY_T_REF = "t0-4-legacy00000000"
LEGACY_M_REF = "mtitle-0-9-legacy00000000"
DURABLE = "a" * 64


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _Evidence:
    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.availability = "AVAILABLE"


class _VerifiedText:
    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.excerpt = "Verified excerpt."


#: Provider-call authority captured when each fixture candidate is built, so a
#: later artifact-row tamper is detectable.  Derived from the tampered row it
#: could never fail.
EXPECTED_PROVIDER_CALLS: dict[str, tuple[str, str]] = {}


class _ProviderCall:
    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        self.status = ProviderCallStatus.SUCCEEDED

@dataclass
class _Repository:
    candidates: tuple[WeeklyCandidateRecord, ...]
    reports: list[object] = field(default_factory=list)
    fail_next_upsert: bool = False
    durable_evidence_ids: frozenset[str] = frozenset({DURABLE})

    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]:
        del start_utc, end_utc
        return self.candidates

    def get_evidence(self, evidence_id: str) -> _Evidence | None:
        return _Evidence(evidence_id) if evidence_id in self.durable_evidence_ids else None

    def resolve_verified_evidence_text(self, evidence_id: str) -> _VerifiedText | None:
        return (
            _VerifiedText(evidence_id)
            if evidence_id in self.durable_evidence_ids
            else None
        )

    def get_provider_call(self, request_hash: str) -> _ProviderCall | None:
        expected = EXPECTED_PROVIDER_CALLS.get(request_hash)
        return None if expected is None else _ProviderCall(*expected)

    def upsert_report(self, report: object, *, now: datetime) -> object:
        del now
        self.reports.append(report)
        return report


def _scoring_reader(
    candidates: tuple[WeeklyCandidateRecord, ...], artifact_root: Path
):
    """Resolve each candidate's pre-verified fixture score, as the trusted reader does."""

    threshold = 7.0
    by_video = {candidate.video.video_id: candidate for candidate in candidates}

    def read(video_id: str) -> VerifiedScoringRead:
        candidate = by_video[video_id]
        assert candidate.score_artifact is not None
        body = (artifact_root / candidate.score_artifact.relative_path).read_bytes()
        result = ScoreResult.model_validate_json(body)
        final = result.score >= threshold
        outcome = ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=threshold,
                final_should_summarize=final,
                model_disagrees=(result.should_summarize != final),
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                started_at=NOW,
                finished_at=NOW,
                model=result.model,
            ),
        )
        return VerifiedScoringRead(
            scoring_outcome=outcome,
            video_id=video_id,
            scoring_job_id="job-1",
            scoring_success_provenance=None,
        )

    return read


def _artifact(
    video_id: str,
    kind: ArtifactKind,
    relative_path: str,
    content: bytes,
    artifact_key: str,
    provider: str | None,
    *,
    root_type: StorageRoot = StorageRoot.DATA,
) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=f"artifact-{hashlib.sha256(artifact_key.encode()).hexdigest()[:16]}",
        artifact_key=artifact_key,
        video_id=video_id,
        job_id=None,
        kind=kind,
        storage_root=root_type,
        relative_path=relative_path,
        content_hash=hashlib.sha256(content).hexdigest(),
        provider=provider,
        model="qwen3:8b" if provider == "ollama" else None,
        producer_version="fixture-v1",
        retention_class=RetentionClass.LONG_LIVED,
        created_at=NOW,
        expires_at=None,
        deleted_at=None,
    )


def _analysis(
    *,
    video_id: str,
    citation: str,
    summary_text: str,
    prompt_version: str,
) -> AnalysisResult:
    return AnalysisResult(
        one_sentence_summary=summary_text,
        core_points=(
            AnalysisPoint(
                text="Verified local fact.",
                kind=PointKind.FACT,
                evidence_ids=(citation,),
            ),
        ),
        keywords=("keyword-from-" + video_id,),
        evidence=(
            EvidenceExcerpt(
                evidence_id=citation,
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="Verified excerpt.",
            ),
        ),
        provider="ollama",
        model="qwen3:8b",
        prompt_version=prompt_version,
        request_hash=hashlib.sha256(f"analysis:{video_id}".encode()).hexdigest(),
    )


def _candidate(
    root: Path,
    video_id: str,
    citation: str,
    summary_text: str,
    prompt_version: str,
    *,
    score: float = 8.0,
) -> WeeklyCandidateRecord:
    analysis = _analysis(
        video_id=video_id,
        citation=citation,
        summary_text=summary_text,
        prompt_version=prompt_version,
    )
    score_result = ScoreResult(
        schema_version="score-result-v2",
        score=score,
        reason="This video provides useful practical guidance.",
        topics=("product",),
        should_summarize=True,
        provider="fixture",
        model="fixture",
        prompt_version="scoring-prompt-v2",
        request_hash=hashlib.sha256(f"score:{video_id}".encode()).hexdigest(),
        output_language="en",
    )
    score_bytes = score_result.model_dump_json().encode()
    analysis_bytes = analysis.model_dump_json().encode()
    EXPECTED_PROVIDER_CALLS[analysis.request_hash] = (
        analysis.provider,
        analysis.model,
    )
    score_path = f"scoring/{score_result.request_hash}/structured.json"
    analysis_path = f"analysis/{analysis.request_hash}/structured.json"
    for relative, content in ((score_path, score_bytes), (analysis_path, analysis_bytes)):
        path = root / "artifacts" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    video = VideoRecord(
        video_id=video_id,
        channel_id="channel-1",
        channel_name="Channel",
        title=f"Title {video_id}",
        description="",
        source_url=f"https://example.invalid/{video_id}",
        published_at=NOW,
        duration_seconds=60,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
        pipeline_status=PipelineStatus.COMPLETE,
        pipeline_version="pipeline-v1",
        score=score,
        should_summarize=True,
        discovered_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
    )
    return WeeklyCandidateRecord(
        video=video,
        score_artifact=_artifact(
            video_id,
            ArtifactKind.SCORING_STRUCTURED,
            score_path,
            score_bytes,
            f"scoring/{score_result.request_hash}/structured",
            "fixture",
        ),
        analysis_artifact=_artifact(
            video_id,
            ArtifactKind.ANALYSIS_STRUCTURED,
            analysis_path,
            analysis_bytes,
            f"analysis/{analysis.request_hash}/structured",
            "ollama",
        ),
        note_artifact=_artifact(
            video_id,
            ArtifactKind.VIDEO_NOTE,
            f"Videos/Title {video_id}--{video_id}.md",
            b"note-bytes",
            f"video-note/pipeline-v1/{video_id}",
            None,
            root_type=StorageRoot.VAULT,
        ),
    )


VAULT_SUBDIR = "Knowledge"


def _service(
    root: Path, candidates: tuple[WeeklyCandidateRecord, ...], repository: _Repository
) -> WeeklyReportService:
    return WeeklyReportService(
        repository=repository,
        sink=ObsidianNoteSink(
            vault_root=root / "vault",
            vault_subdir=VAULT_SUBDIR,
            repository=repository,
            context=NoteWriteContext(
                job_id="unused-job", owner="test", pipeline_version="pipeline-v1"
            ),
        ),
        artifact_root=root / "artifacts",
        timezone="UTC",
        top_n=10,
        scoring_reader=_scoring_reader(candidates, root / "artifacts"),
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "vault" / VAULT_SUBDIR / "Videos").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_note(root: Path, candidate: WeeklyCandidateRecord) -> None:
    note = candidate.note_artifact
    assert note is not None
    path = root / "vault" / VAULT_SUBDIR / note.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"note-bytes")


def _generate(
    root: Path, candidates: tuple[WeeklyCandidateRecord, ...], repository: _Repository
):
    for candidate in candidates:
        _write_note(root, candidate)
    return _service(root, candidates, repository).generate(now=NOW)


def _render(
    root: Path, candidates: tuple[WeeklyCandidateRecord, ...], repository: _Repository
) -> str:
    return render_weekly_report(_generate(root, candidates, repository).report)


# --- 1-3: legacy v5 is rejected and its payload never published ---------


def test_1_legacy_v5_candidate_is_excluded(workspace: Path) -> None:
    legacy = _candidate(
        workspace,
        video_id="video-legacy",
        citation=LEGACY_T_REF,
        summary_text=LEGACY_SUMMARY_TEXT,
        prompt_version="analysis-prompt-v5",
    )
    repository = _Repository(candidates=(legacy,))
    rendered = _render(workspace, (legacy,), repository)
    # Requirement 1: excluded.
    assert "video-legacy" not in rendered
    # Requirement 2: its legacy Summary text is not published.
    assert LEGACY_SUMMARY_TEXT not in rendered
    # Requirement 3: its temporary refs are not published.
    assert LEGACY_T_REF not in rendered


def test_2_legacy_metadata_ref_is_excluded(workspace: Path) -> None:
    legacy = _candidate(
        workspace,
        video_id="video-meta",
        citation=LEGACY_M_REF,
        summary_text=LEGACY_SUMMARY_TEXT,
        prompt_version="analysis-prompt-v5",
    )
    repository = _Repository(candidates=(legacy,))
    rendered = _render(workspace, (legacy,), repository)
    assert LEGACY_M_REF not in rendered
    assert LEGACY_SUMMARY_TEXT not in rendered


def test_3_a_hash_valid_legacy_artifact_is_still_excluded(workspace: Path) -> None:
    """The bytes and the artifact hash are genuinely valid; only trust fails."""

    legacy = _candidate(
        workspace,
        video_id="video-hashvalid",
        citation=LEGACY_T_REF,
        summary_text=LEGACY_SUMMARY_TEXT,
        prompt_version="analysis-prompt-v5",
    )
    artifact = legacy.analysis_artifact
    assert artifact is not None
    stored = (workspace / "artifacts" / artifact.relative_path).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == artifact.content_hash
    assert json.loads(stored)["prompt_version"] == "analysis-prompt-v5"
    repository = _Repository(candidates=(legacy,))
    assert LEGACY_SUMMARY_TEXT not in _render(workspace, (legacy,), repository)


# --- 6-8: corrupt current-identity artifacts are excluded --------------


def test_4_corrupt_v6_with_temporary_transcript_ref_is_excluded(workspace: Path) -> None:
    corrupt = _candidate(
        workspace,
        video_id="video-corrupt-t",
        citation=LEGACY_T_REF,
        summary_text="CORRUPT-V6-TEMP-REF",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(corrupt,))
    rendered = _render(workspace, (corrupt,), repository)
    assert LEGACY_T_REF not in rendered
    assert "CORRUPT-V6-TEMP-REF" not in rendered


def test_5_corrupt_v6_with_metadata_ref_is_excluded(workspace: Path) -> None:
    corrupt = _candidate(
        workspace,
        video_id="video-corrupt-m",
        citation=LEGACY_M_REF,
        summary_text="CORRUPT-V6-META-REF",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(corrupt,))
    rendered = _render(workspace, (corrupt,), repository)
    assert LEGACY_M_REF not in rendered
    assert "CORRUPT-V6-META-REF" not in rendered


def test_6_corrupt_v6_with_missing_evidence_is_excluded(workspace: Path) -> None:
    """A 64-hex citation that resolves to nothing is still untrusted."""

    missing = "b" * 64
    corrupt = _candidate(
        workspace,
        video_id="video-corrupt-missing",
        citation=missing,
        summary_text="CORRUPT-V6-MISSING-EVIDENCE",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(corrupt,), durable_evidence_ids=frozenset())
    rendered = _render(workspace, (corrupt,), repository)
    assert missing not in rendered
    assert "CORRUPT-V6-MISSING-EVIDENCE" not in rendered


# --- 9: valid current v6 is accepted -----------------------------------


def test_7_valid_current_v6_is_accepted(workspace: Path) -> None:
    trusted = _candidate(
        workspace,
        video_id="video-trusted",
        citation=DURABLE,
        summary_text="TRUSTED-V6-SUMMARY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(trusted,))
    generated = _generate(workspace, (trusted,), repository)
    rendered = render_weekly_report(generated.report)
    assert "TRUSTED-V6-SUMMARY" in rendered
    assert len(generated.report.items) == 1
    assert generated.report.items[0].one_sentence_summary == "TRUSTED-V6-SUMMARY"


def test_8_valid_v6_generation_is_provider_free(workspace: Path) -> None:
    """Requirement 10 and 20: no model call enters the reporting read path."""

    trusted = _candidate(
        workspace,
        video_id="video-provider-free",
        citation=DURABLE,
        summary_text="TRUSTED-V6-SUMMARY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(trusted,))
    calls: list[str] = []

    def _forbidden(*args: object, **kwargs: object) -> None:
        calls.append("provider")
        raise AssertionError("the reporting read path must never call a provider")

    import youtube_intel.analysis as analysis_module
    import youtube_intel.reporting as reporting_module

    originals = []
    for module, name in (
        (analysis_module, "AnalysisService"),
        (reporting_module, "WeeklyReportService"),
    ):
        original = getattr(module, name, None)
        if original is None:
            continue
        setattr(module, name, _forbidden)
        originals.append((module, name, original))
    generated = None
    try:
        generated = _generate(workspace, (trusted,), repository)
    finally:
        for module, name, original in originals:
            setattr(module, name, original)
    assert calls == []
    assert generated is not None
    assert repository.reports, "the report was still written"
    assert len(generated.report.items) == 1


# --- 11-13: mixed and all-invalid candidate sets -----------------------


def test_9_mixed_valid_v6_and_legacy_v5_publishes_only_v6(workspace: Path) -> None:
    trusted = _candidate(
        workspace,
        video_id="video-ok",
        citation=DURABLE,
        summary_text="TRUSTED-V6-SUMMARY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
        score=9.0,
    )
    legacy = _candidate(
        workspace,
        video_id="video-legacy-mixed",
        citation=LEGACY_T_REF,
        summary_text=LEGACY_SUMMARY_TEXT,
        prompt_version="analysis-prompt-v5",
        score=8.0,
    )
    candidates = (trusted, legacy)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    assert "TRUSTED-V6-SUMMARY" in rendered
    assert LEGACY_SUMMARY_TEXT not in rendered
    assert LEGACY_T_REF not in rendered
    # The report continues: exactly one item survived.
    assert len(generated.report.items) == 1


def test_10_mixed_valid_v6_and_corrupt_v6_publishes_only_valid(workspace: Path) -> None:
    trusted = _candidate(
        workspace,
        video_id="video-ok",
        citation=DURABLE,
        summary_text="TRUSTED-V6-SUMMARY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
        score=9.0,
    )
    corrupt = _candidate(
        workspace,
        video_id="video-corrupt-mixed",
        citation="c" * 64,
        summary_text="CORRUPT-V6-MIXED",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
        score=8.0,
    )
    candidates = (trusted, corrupt)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    assert "TRUSTED-V6-SUMMARY" in rendered
    assert "CORRUPT-V6-MIXED" not in rendered
    assert len(generated.report.items) == 1


def test_11_all_candidates_ineligible_yields_the_existing_empty_behavior(
    workspace: Path,
) -> None:
    """Requirement 13: no legacy payload is published merely to avoid empty."""

    legacy = _candidate(
        workspace,
        video_id="video-legacy-only",
        citation=LEGACY_T_REF,
        summary_text=LEGACY_SUMMARY_TEXT,
        prompt_version="analysis-prompt-v5",
    )
    corrupt = _candidate(
        workspace,
        video_id="video-corrupt-only",
        citation="d" * 64,
        summary_text="CORRUPT-ONLY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    candidates = (legacy, corrupt)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    report = generated.report
    assert LEGACY_SUMMARY_TEXT not in rendered
    assert "CORRUPT-ONLY" not in rendered
    # Existing empty / no-qualified-items behaviour, with no legacy payload.
    assert len(report.items) == 0
    assert getattr(report, "analysis_results", ()) == ()
    # The existing empty-report write still happens exactly once.
    assert repository.reports and len(repository.reports) == 1


# --- 5: a newer legacy artifact must not displace the trusted current ---


def test_12_candidate_source_is_the_current_pointer_not_the_latest(tmp_path: Path) -> None:
    """Requirements 4 and 5, enforced in the repository query itself."""

    import inspect

    from youtube_intel.state import SQLiteStateRepository

    source = inspect.getsource(SQLiteStateRepository.list_weekly_candidates)
    # The weekly Summary input is the explicit current Summary pointer.
    assert "FROM current_content_summaries" in source
    assert "analysis_artifact_id" in source
    # It must NOT fall back to "newest structured Analysis artifact".
    weekly_lines = [
        line
        for line in source.splitlines()
        if "ANALYSIS_STRUCTURED" in line and "_latest_weekly_artifact" in line
    ]
    assert not weekly_lines


def test_13_a_deep_analysis_pointer_yields_no_local_summary_text(tmp_path: Path) -> None:
    """A DA-backed pointer has no local artifact; no Summary text is invented."""

    import inspect

    from youtube_intel.state import SQLiteStateRepository

    source = inspect.getsource(SQLiteStateRepository.list_weekly_candidates)
    assert 'pointer["analysis_artifact_id"] is None' in source


# --- no trust-order bypass ---------------------------------------------


def test_14_other_validation_failures_still_refuse_the_whole_report(
    workspace: Path,
) -> None:
    """The exclusion cannot be used to launder a bad note past validation."""

    from youtube_intel.reporting import WeeklyReportValidationError

    trusted = _candidate(
        workspace,
        video_id="video-good",
        citation=DURABLE,
        summary_text="TRUSTED-V6-SUMMARY",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
    )
    _write_note(workspace, trusted)
    # Corrupt the managed note on disk.
    note = trusted.note_artifact
    assert note is not None
    (workspace / "vault" / VAULT_SUBDIR / note.relative_path).write_bytes(b"tampered")
    repository = _Repository(candidates=(trusted,))
    with pytest.raises(WeeklyReportValidationError):
        _service(workspace, (trusted,), repository).generate(now=NOW)


def test_15_the_shared_gate_is_reused_not_duplicated() -> None:
    """Weekly must call the shared helper, not restate the rules."""

    import inspect

    from youtube_intel.reporting import _verified_analysis

    source = inspect.getsource(_verified_analysis)
    assert "require_current_summary_authority" in source
    assert "CURRENT_SUMMARY_PROMPT_VERSION" not in source
    assert "prompt_version !=" not in source


# ---------------------------------------------------------------------------
# Candidate-local isolation: malformed / semantically invalid Summary payloads
# ---------------------------------------------------------------------------


def _corrupt_with(
    workspace: Path, candidate: WeeklyCandidateRecord, payload: bytes
) -> WeeklyCandidateRecord:
    """Write a hash-valid corrupt payload and return the updated candidate.

    The corruption is candidate-local: storage integrity stays intact, so only
    Summary semantics are wrong.
    """

    assert candidate.analysis_artifact is not None
    (workspace / "artifacts" / candidate.analysis_artifact.relative_path).write_bytes(
        payload
    )
    return replace(
        candidate,
        analysis_artifact=replace(
            candidate.analysis_artifact,
            content_hash=hashlib.sha256(payload).hexdigest(),
        ),
    )


def _doc(workspace: Path, candidate: WeeklyCandidateRecord) -> dict:
    assert candidate.analysis_artifact is not None
    return json.loads(
        (workspace / "artifacts" / candidate.analysis_artifact.relative_path).read_bytes()
    )


def test_6_point_citing_an_absent_evidence_id_is_excluded(workspace: Path) -> None:
    """Requirement 6: the stray point ref fails parsing, not the report."""

    candidate = _candidate(
        workspace, "video-stray", DURABLE, "STRAY-POINT-TEXT",
        CURRENT_SUMMARY_PROMPT_VERSION,
    )
    doc = _doc(workspace, candidate)
    doc["core_points"][0]["evidence_ids"] = ["d" * 64]
    corrupt = _corrupt_with(
        workspace, candidate, json.dumps(doc).encode()
    )
    repository = _Repository(candidates=(corrupt,))
    generated = _generate(workspace, (corrupt,), repository)
    rendered = render_weekly_report(generated.report)
    assert len(generated.report.items) == 0
    assert "STRAY-POINT-TEXT" not in rendered


def test_7_valid_plus_stray_point_reference_publishes_only_valid(workspace: Path) -> None:
    """Requirement 7."""

    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED-V6-SUMMARY",
        CURRENT_SUMMARY_PROMPT_VERSION, score=9.0,
    )
    stray = _candidate(
        workspace, "video-stray", DURABLE, "STRAY-POINT-TEXT",
        CURRENT_SUMMARY_PROMPT_VERSION, score=8.0,
    )
    doc = _doc(workspace, stray)
    doc["core_points"][0]["evidence_ids"] = ["e" * 64]
    corrupt = _corrupt_with(workspace, stray, json.dumps(doc).encode())
    candidates = (trusted, corrupt)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    assert len(generated.report.items) == 1
    assert "TRUSTED-V6-SUMMARY" in rendered
    assert "STRAY-POINT-TEXT" not in rendered


def test_8_valid_plus_malformed_json_publishes_only_valid(workspace: Path) -> None:
    """Requirement 8: malformed, hash-valid Summary content is candidate-local."""

    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED-V6-SUMMARY",
        CURRENT_SUMMARY_PROMPT_VERSION, score=9.0,
    )
    broken = _candidate(
        workspace, "video-broken", DURABLE, "MALFORMED",
        CURRENT_SUMMARY_PROMPT_VERSION, score=8.0,
    )
    corrupt = _corrupt_with(workspace, broken, b'{"one_sentence_summary": not-json')
    candidates = (trusted, corrupt)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    assert len(generated.report.items) == 1
    assert "TRUSTED-V6-SUMMARY" in rendered
    assert "not-json" not in rendered


def test_9_all_candidate_local_invalid_yields_the_empty_report(workspace: Path) -> None:
    """Requirements 9 and 10."""

    legacy = _candidate(
        workspace, "video-legacy", LEGACY_T_REF, "LEGACY-TEXT", "analysis-prompt-v5",
        score=9.0,
    )
    stray = _candidate(
        workspace, "video-stray", DURABLE, "STRAY-TEXT",
        CURRENT_SUMMARY_PROMPT_VERSION, score=8.0,
    )
    doc = _doc(workspace, stray)
    doc["core_points"][0]["evidence_ids"] = ["f" * 64]
    corrupt = _corrupt_with(workspace, stray, json.dumps(doc).encode())
    broken = _candidate(
        workspace, "video-broken", DURABLE, "MALFORMED-TEXT",
        CURRENT_SUMMARY_PROMPT_VERSION, score=7.0,
    )
    corrupt_broken = _corrupt_with(workspace, broken, b"[]not-an-object")
    candidates = (legacy, corrupt, corrupt_broken)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    rendered = render_weekly_report(generated.report)
    report = generated.report
    assert len(report.items) == 0
    assert getattr(report, "analysis_results", ()) == ()
    for leaked in ("LEGACY-TEXT", "STRAY-TEXT", "MALFORMED-TEXT"):
        assert leaked not in rendered
    assert len(repository.reports) == 1


def test_10_no_provider_call_and_no_regeneration(workspace: Path) -> None:
    """Requirements 11, 12 and 13."""

    import youtube_intel.analysis as analysis_module

    calls: list[str] = []
    original = getattr(analysis_module, "AnalysisService", None)
    if original is not None:
        analysis_module.AnalysisService = lambda *a, **k: calls.append("provider")
    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED-V6-SUMMARY",
        CURRENT_SUMMARY_PROMPT_VERSION, score=9.0,
    )
    stray = _candidate(
        workspace, "video-stray", DURABLE, "STRAY", CURRENT_SUMMARY_PROMPT_VERSION,
    )
    doc = _doc(workspace, stray)
    doc["core_points"][0]["evidence_ids"] = ["9" * 64]
    corrupt = _corrupt_with(workspace, stray, json.dumps(doc).encode())
    repository = _Repository(candidates=(trusted, corrupt))
    try:
        generated = _generate(workspace, (trusted, corrupt), repository)
    finally:
        if original is not None:
            analysis_module.AnalysisService = original
    assert calls == []
    assert len(generated.report.items) == 1
    # The corrupt artifact is untouched on disk; nothing regenerated or deleted.
    assert (workspace / "artifacts" / corrupt.analysis_artifact.relative_path).exists()


# ---------------------------------------------------------------------------
# FATAL: storage / security failures must still refuse the whole report
# ---------------------------------------------------------------------------


def test_14_artifact_hash_mismatch_is_still_fatal(workspace: Path) -> None:
    """Requirement 14: bytes that do not match the recorded hash are fatal."""

    from youtube_intel.reporting import WeeklyReportValidationError

    candidate = _candidate(
        workspace, "video-tampered", DURABLE, "TAMPERED",
        CURRENT_SUMMARY_PROMPT_VERSION,
    )
    assert candidate.analysis_artifact is not None
    # Write different bytes WITHOUT updating the recorded hash.
    (workspace / "artifacts" / candidate.analysis_artifact.relative_path).write_bytes(
        b"different bytes entirely"
    )
    repository = _Repository(candidates=(candidate,))
    with pytest.raises(WeeklyReportValidationError):
        _generate(workspace, (candidate,), repository)
    assert repository.reports == []


def test_15_artifact_path_escape_is_still_fatal(workspace: Path) -> None:
    """Requirement 15."""

    from youtube_intel.reporting import WeeklyReportValidationError

    candidate = _candidate(
        workspace, "video-escape", DURABLE, "ESCAPE", CURRENT_SUMMARY_PROMPT_VERSION,
    )
    assert candidate.analysis_artifact is not None
    escaping = replace(
        candidate,
        analysis_artifact=replace(
            candidate.analysis_artifact, relative_path="../../etc/structured.json"
        ),
    )
    repository = _Repository(candidates=(escaping,))
    with pytest.raises(WeeklyReportValidationError):
        _generate(workspace, (escaping,), repository)
    assert repository.reports == []


def test_16_artifact_provenance_tamper_is_still_fatal(workspace: Path) -> None:
    """Requirement 16: artifact_key / provider / model identity mismatch."""

    from youtube_intel.reporting import WeeklyReportValidationError

    candidate = _candidate(
        workspace, "video-provenance", DURABLE, "PROVENANCE",
        CURRENT_SUMMARY_PROMPT_VERSION,
    )
    assert candidate.analysis_artifact is not None
    for attribute, value in (
        ("artifact_key", "analysis/not-the-result/structured"),
        ("provider", "someone-else"),
        ("model", "someone-elses-model"),
    ):
        tampered = replace(
            candidate,
            analysis_artifact=replace(
                candidate.analysis_artifact, **{attribute: value}
            ),
        )
        repository = _Repository(candidates=(tampered,))
        with pytest.raises(WeeklyReportValidationError):
            _generate(workspace, (tampered,), repository)
        assert repository.reports == []


def test_17_tampered_note_is_still_fatal(workspace: Path) -> None:
    """Requirement 17: note integrity failures are not candidate exclusions."""

    from youtube_intel.reporting import WeeklyReportValidationError

    candidate = _candidate(
        workspace, "video-note", DURABLE, "TRUSTED", CURRENT_SUMMARY_PROMPT_VERSION,
    )
    _write_note(workspace, candidate)
    note = candidate.note_artifact
    assert note is not None
    (workspace / "vault" / VAULT_SUBDIR / note.relative_path).write_bytes(b"tampered")
    repository = _Repository(candidates=(candidate,))
    with pytest.raises(WeeklyReportValidationError):
        _service(workspace, (candidate,), repository).generate(now=NOW)
    assert repository.reports == []


def test_18_a_fatal_failure_still_aborts_even_beside_a_valid_candidate(
    workspace: Path,
) -> None:
    """One storage failure must not be diluted by an excluded sibling."""

    from youtube_intel.reporting import WeeklyReportValidationError

    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED-V6-SUMMARY",
        CURRENT_SUMMARY_PROMPT_VERSION, score=9.0,
    )
    broken = _candidate(
        workspace, "video-broken", DURABLE, "BROKEN", CURRENT_SUMMARY_PROMPT_VERSION,
        score=8.0,
    )
    assert broken.analysis_artifact is not None
    (workspace / "artifacts" / broken.analysis_artifact.relative_path).write_bytes(
        b"hash no longer matches"
    )
    candidates = (trusted, broken)
    repository = _Repository(candidates=candidates)
    with pytest.raises(WeeklyReportValidationError):
        _generate(workspace, candidates, repository)
    assert repository.reports == []


# ---------------------------------------------------------------------------
# COMBINATION: a fatal provenance fault must never be masked by bad content
# ---------------------------------------------------------------------------


def _malformed(workspace: Path, candidate: WeeklyCandidateRecord):
    """Hash-valid but unparseable Summary content."""

    return _corrupt_with(workspace, candidate, b'{"one_sentence_summary": not-json')


def _assert_fatal(workspace: Path, candidate: WeeklyCandidateRecord) -> None:
    from youtube_intel.reporting import WeeklyReportValidationError

    repository = _Repository(candidates=(candidate,))
    with pytest.raises(WeeklyReportValidationError):
        _generate(workspace, (candidate,), repository)
    assert repository.reports == []


def test_1_malformed_json_alone_is_candidate_local(workspace: Path) -> None:
    candidate = _corrupt_with(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
        ),
        b'{"one_sentence_summary": not-json',
    )
    repository = _Repository(candidates=(candidate,))
    generated = _generate(workspace, (candidate,), repository)
    assert len(generated.report.items) == 0


def test_2_malformed_json_with_valid_sibling_keeps_the_sibling(workspace: Path) -> None:
    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED-V6-SUMMARY",
        CURRENT_SUMMARY_PROMPT_VERSION, score=9.0,
    )
    broken = _corrupt_with(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION,
            score=8.0,
        ),
        b'{"one_sentence_summary": not-json',
    )
    candidates = (trusted, broken)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    assert len(generated.report.items) == 1
    assert "TRUSTED-V6-SUMMARY" in render_weekly_report(generated.report)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("artifact_key", "analysis/not-the-result/structured"),
        ("provider", "someone-else"),
        ("model", "someone-elses-model"),
    ],
)
def test_3_4_5_malformed_json_plus_provenance_tamper_still_fails_the_report(
    workspace: Path, attribute: str, value: str
) -> None:
    """Requirements 3, 4 and 5: the parse failure must not mask the tamper."""

    broken = _malformed(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
        ),
    )
    assert broken.analysis_artifact is not None
    tampered = replace(
        broken,
        analysis_artifact=replace(broken.analysis_artifact, **{attribute: value}),
    )
    _assert_fatal(workspace, tampered)


def test_6_malformed_json_plus_hash_mismatch_still_fails_the_report(
    workspace: Path,
) -> None:
    """Requirement 6."""

    candidate = _candidate(
        workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
    )
    assert candidate.analysis_artifact is not None
    # Write malformed bytes but leave the recorded hash pointing elsewhere.
    (workspace / "artifacts" / candidate.analysis_artifact.relative_path).write_bytes(
        b'{"one_sentence_summary": not-json'
    )
    _assert_fatal(workspace, candidate)


def test_7_malformed_json_plus_path_traversal_still_fails_the_report(
    workspace: Path,
) -> None:
    """Requirement 7."""

    broken = _malformed(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
        ),
    )
    assert broken.analysis_artifact is not None
    escaping = replace(
        broken,
        analysis_artifact=replace(
            broken.analysis_artifact, relative_path="../../etc/structured.json"
        ),
    )
    _assert_fatal(workspace, escaping)


def test_8_malformed_json_plus_symlink_escape_still_fails_the_report(
    workspace: Path,
) -> None:
    """Requirement 8."""

    broken = _malformed(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
        ),
    )
    _symlink_leaf_to_outside(workspace, broken, payload=b'{"one_sentence_summary": not-json')
    _assert_fatal(workspace, broken)


# ---------------------------------------------------------------------------
# Symlink escape: a trusted artifact read must not leave the artifact root
# ---------------------------------------------------------------------------


def _symlink_leaf_to_outside(
    workspace: Path, candidate: WeeklyCandidateRecord, *, payload: bytes
) -> Path:
    """Replace the leaf artifact file with a symlink to an outside file."""

    outside = workspace / "outside" / "payload.json"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_bytes(payload)
    assert candidate.analysis_artifact is not None
    link = workspace / "artifacts" / candidate.analysis_artifact.relative_path
    link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    # The recorded hash deliberately MATCHES the outside target.
    return outside


def test_9_valid_summary_with_leaf_symlink_outside_root_fails(workspace: Path) -> None:
    """Requirement 9."""

    candidate = _candidate(
        workspace, "video-link", DURABLE, "LINKED", CURRENT_SUMMARY_PROMPT_VERSION
    )
    assert candidate.analysis_artifact is not None
    original = (
        workspace / "artifacts" / candidate.analysis_artifact.relative_path
    ).read_bytes()
    _symlink_leaf_to_outside(workspace, candidate, payload=original)
    _assert_fatal(workspace, candidate)


def test_10_valid_summary_with_intermediate_directory_symlink_fails(
    workspace: Path,
) -> None:
    """Requirement 10."""

    candidate = _candidate(
        workspace, "video-dirlink", DURABLE, "DIRLINKED",
        CURRENT_SUMMARY_PROMPT_VERSION,
    )
    assert candidate.analysis_artifact is not None
    relative = candidate.analysis_artifact.relative_path
    head, _, leaf = relative.rpartition("/")
    real_dir = workspace / "outside_dir"
    real_dir.mkdir(parents=True, exist_ok=True)
    (real_dir / leaf).write_bytes((workspace / "artifacts" / relative).read_bytes())
    original_dir = workspace / "artifacts" / head
    original_dir.rename(workspace / "artifacts" / (head + "-moved"))
    original_dir.symlink_to(real_dir)
    _assert_fatal(workspace, candidate)


def test_11_symlink_with_matching_bytes_and_hash_is_still_fatal(workspace: Path) -> None:
    """Requirement 11: identical bytes do not make the path trusted."""

    from youtube_intel.reporting import _verified_data_artifact

    candidate = _candidate(
        workspace, "video-match", DURABLE, "MATCHED", CURRENT_SUMMARY_PROMPT_VERSION
    )
    assert candidate.analysis_artifact is not None
    original = (
        workspace / "artifacts" / candidate.analysis_artifact.relative_path
    ).read_bytes()
    _symlink_leaf_to_outside(workspace, candidate, payload=original)
    # The recorded hash matches the outside target byte for byte.
    assert candidate.analysis_artifact.content_hash == hashlib.sha256(original).hexdigest()
    with pytest.raises(ValueError):
        _verified_data_artifact(
            workspace / "artifacts",
            candidate.analysis_artifact,
            candidate.video.video_id,
            ArtifactKind.ANALYSIS_STRUCTURED,
        )


def test_12_a_valid_regular_file_artifact_is_accepted(workspace: Path) -> None:
    """Requirement 12."""

    candidate = _candidate(
        workspace, "video-regular", DURABLE, "REGULAR",
        CURRENT_SUMMARY_PROMPT_VERSION,
    )
    repository = _Repository(candidates=(candidate,))
    generated = _generate(workspace, (candidate,), repository)
    assert len(generated.report.items) == 1
    assert "REGULAR" in render_weekly_report(generated.report)


def test_13_valid_sibling_plus_fatal_candidate_fails_the_report(workspace: Path) -> None:
    """Requirement 13."""

    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED", CURRENT_SUMMARY_PROMPT_VERSION,
        score=9.0,
    )
    fatal = _candidate(
        workspace, "video-fatal", DURABLE, "FATAL", CURRENT_SUMMARY_PROMPT_VERSION,
        score=8.0,
    )
    assert fatal.analysis_artifact is not None
    (workspace / "artifacts" / fatal.analysis_artifact.relative_path).write_bytes(
        b"bytes no longer match"
    )
    from youtube_intel.reporting import WeeklyReportValidationError

    candidates = (trusted, fatal)
    repository = _Repository(candidates=candidates)
    with pytest.raises(WeeklyReportValidationError):
        _generate(workspace, candidates, repository)
    assert repository.reports == []


def test_14_valid_sibling_plus_candidate_local_bad_summary_survives(
    workspace: Path,
) -> None:
    """Requirement 14 (unchanged isolation)."""

    trusted = _candidate(
        workspace, "video-ok", DURABLE, "TRUSTED", CURRENT_SUMMARY_PROMPT_VERSION,
        score=9.0,
    )
    broken = _corrupt_with(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION,
            score=8.0,
        ),
        b'{"one_sentence_summary": not-json',
    )
    candidates = (trusted, broken)
    repository = _Repository(candidates=candidates)
    generated = _generate(workspace, candidates, repository)
    assert len(generated.report.items) == 1


def test_15_all_candidate_local_invalid_keeps_the_empty_report(workspace: Path) -> None:
    """Requirement 15 (unchanged behaviour)."""

    broken = _corrupt_with(
        workspace,
        _candidate(
            workspace, "video-bad", DURABLE, "BAD", CURRENT_SUMMARY_PROMPT_VERSION
        ),
        b"[]not-an-object",
    )
    repository = _Repository(candidates=(broken,))
    generated = _generate(workspace, (broken,), repository)
    assert len(generated.report.items) == 0
    assert len(repository.reports) == 1


def test_16_no_broad_exception_is_swallowed(workspace: Path) -> None:
    """The candidate loop still catches only the project-local signal."""

    import inspect

    from youtube_intel.reporting import WeeklyReportService, _WeeklySummaryNotTrusted

    source = inspect.getsource(WeeklyReportService._verified_or_excluded)
    assert "_WeeklySummaryNotTrusted" in source
    assert "WeeklyReportValidationError" not in source
    assert "except Exception" not in source
    assert issubclass(_WeeklySummaryNotTrusted, Exception)
    assert not issubclass(_WeeklySummaryNotTrusted, ValueError)
