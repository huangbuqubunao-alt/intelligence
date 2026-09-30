"""P0 follow-up: historical readability vs current trusted Summary authority.

A readable ``analysis-prompt-v1``..``v5`` artifact is **not** current trusted
Summary authority.  Its citations are temporary model-facing refs
(``t0-20-…`` / ``mtitle-…``), which fail both ``get_evidence`` and
``resolve_verified_evidence_text``.

Frozen invariant proven here:

    Historical artifacts stay parseable and inspectable.  Current trusted
    Summary authority requires the live durable-citation contract *and* a
    citation that actually resolves through the repository.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.domain import AnalysisResult, EvidenceSource
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    LiveStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
)
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    SummaryDraft,
    SummaryDraftPoint,
)
from youtube_intel.summary_evidence_authority import (
    CURRENT_SUMMARY_PROMPT_VERSION,
    HISTORICAL_SUMMARY_PROMPT_VERSIONS,
    LegacySummaryNotCurrentAuthority,
    SummaryCitationNotDurable,
    current_summary_authority_defects,
    hydrate_summary_evidence,
    require_current_summary_authority,
)
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry

NOW = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
ARTIFACT_ID = "artifact-legacy"
CUE_TEXTS = tuple(f"cue{index} source sentence" for index in range(8))
LEGACY_VERSIONS = (
    "analysis-prompt-v1",
    "analysis-prompt-v2",
    "analysis-prompt-v3",
    "analysis-prompt-v4",
    "analysis-prompt-v5",
)


# ---------------------------------------------------------------------------
# One repository-backed source of truth for candidate refs
# ---------------------------------------------------------------------------


def _seed(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC_TEST",
            channel_name="3Blue1Brown",
            title="The Phone Number puzzle",
            description="d",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=44,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="runtime-v1",
        now=NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=ARTIFACT_ID,
            artifact_key=f"transcript/{VIDEO_ID}",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{VIDEO_ID}/canonical.txt",
            content_hash=sha256("".join(CUE_TEXTS).encode()).hexdigest(),
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
            canonical_artifact_id=ARTIFACT_ID,
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
    return repository


def _registry(repository: SQLiteStateRepository):
    """The one registry whose refs match what the repository will promote."""

    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    return build_trusted_evidence_registry(
        transcript=verified,
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="short description",
        input_identity="a" * 64,
    )


def _ref(repository: SQLiteStateRepository, source: EvidenceSource) -> str:
    return next(c.ref for c in _registry(repository).candidates if c.source is source)


def _t_ref(repository: SQLiteStateRepository) -> str:
    return _ref(repository, EvidenceSource.TRANSCRIPT_SAMPLE)


def _m_ref(repository: SQLiteStateRepository) -> str:
    return _ref(repository, EvidenceSource.TITLE)


def _promote(repository: SQLiteStateRepository, ref: str) -> str:
    """Persist one durable EXTRACTION row and return its durable identity."""

    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    draft = SummaryDraft(
        one_sentence_summary="s",
        core_points=(SummaryDraftPoint(text="t", kind="fact", evidence_refs=(ref,)),),
        keywords=("k",),
    )
    hydrated = hydrate_summary_evidence(
        draft,
        _registry(repository),
        video_id=VIDEO_ID,
        canonical_artifact_id=ARTIFACT_ID,
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )
    promotion = hydrated.promotions[0]
    repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    return promotion.evidence_id


def _result(prompt_version: str, *, evidence_ids, point_ids) -> AnalysisResult:
    """Build a persisted-shape AnalysisResult with explicit citation ids."""

    return AnalysisResult.model_validate(
        {
            "one_sentence_summary": "s",
            "core_points": [
                {"text": "t", "kind": "fact", "evidence_ids": list(point_ids)}
            ],
            "keywords": ["k"],
            "evidence": [
                {
                    "evidence_id": str(evidence_id),
                    "source": "transcript_sample",
                    "excerpt": "e",
                }
                for evidence_id in evidence_ids
            ],
            "provider": "ollama",
            "model": "qwen3:8b",
            "prompt_version": prompt_version,
            "schema_version": "analysis-result-v1",
            "request_hash": "0" * 64,
        }
    )


# --- 1-6: historical readability through the persisted parser ------------


@pytest.mark.parametrize("version", LEGACY_VERSIONS + ("analysis-prompt-v6",))
def test_1_historical_artifact_still_parses(version: str) -> None:
    """Requirements 1-6: every historical identity stays parseable."""

    result = _result(version, evidence_ids=["a" * 64], point_ids=["a" * 64])
    assert result.prompt_version == version
    assert result.schema_version == "analysis-result-v1"


@pytest.mark.parametrize("version", LEGACY_VERSIONS + ("analysis-prompt-v6",))
def test_2_historical_bytes_round_trip_unchanged(version: str) -> None:
    """Requirement 11: the stored bytes and their hash are untouched."""

    result = _result(version, evidence_ids=["a" * 64], point_ids=["a" * 64])
    body = result.model_dump_json().encode()
    before = sha256(body).hexdigest()
    assert AnalysisResult.model_validate_json(body) == result
    assert sha256(result.model_dump_json().encode()).hexdigest() == before


def test_3_the_readability_set_covers_v1_to_v6() -> None:
    assert HISTORICAL_SUMMARY_PROMPT_VERSIONS == (
        "analysis-prompt-v1",
        "analysis-prompt-v2",
        "analysis-prompt-v3",
        "analysis-prompt-v4",
        "analysis-prompt-v5",
        "analysis-prompt-v6",
    )
    assert CURRENT_SUMMARY_PROMPT_VERSION == "analysis-prompt-v6"
    assert CURRENT_SUMMARY_PROMPT_VERSION == SUMMARY_DRAFT_PROMPT_VERSION


# --- 7: v1-v5 are not current-authority eligible -----------------------


@pytest.mark.parametrize("version", LEGACY_VERSIONS)
def test_4_v1_to_v5_are_not_current_trusted_summary_eligible(
    version: str, tmp_path: Path
) -> None:
    """Requirement 7: a legacy identity is disqualified even with a durable id."""

    repository = _seed(tmp_path)
    durable = _promote(repository, _t_ref(repository))
    result = _result(version, evidence_ids=[durable], point_ids=[durable])
    defects = current_summary_authority_defects(result, repository)
    assert any(d.startswith("summary_prompt_identity_is_legacy") for d in defects)
    with pytest.raises(LegacySummaryNotCurrentAuthority):
        require_current_summary_authority(result, repository)


# --- 8-9: legacy t*/m* refs can never become current authority ----------


def test_5_legacy_v5_with_temporary_transcript_ref_is_rejected(tmp_path: Path) -> None:
    """Requirement 8."""

    repository = _seed(tmp_path)
    ref = _t_ref(repository)
    assert ref.startswith("t")
    result = _result("analysis-prompt-v5", evidence_ids=[ref], point_ids=[ref])
    defects = current_summary_authority_defects(result, repository)
    assert any("summary_prompt_identity_is_legacy" in d for d in defects)
    assert any("summary_citation_is_not_durable" in d for d in defects)
    assert any("summary_citation_is_temporary_ref" in d for d in defects)
    with pytest.raises(LegacySummaryNotCurrentAuthority):
        require_current_summary_authority(result, repository)


def test_6_legacy_v5_with_metadata_ref_is_rejected(tmp_path: Path) -> None:
    """Requirement 9."""

    repository = _seed(tmp_path)
    ref = _m_ref(repository)
    assert ref.startswith("m")
    result = _result("analysis-prompt-v5", evidence_ids=[ref], point_ids=[ref])
    defects = current_summary_authority_defects(result, repository)
    assert any("summary_citation_is_not_durable" in d for d in defects)
    assert any("summary_citation_is_temporary_ref" in d for d in defects)
    with pytest.raises(LegacySummaryNotCurrentAuthority):
        require_current_summary_authority(result, repository)


def test_7_a_legacy_pointer_cannot_satisfy_a_v6_current_summary(
    tmp_path: Path,
) -> None:
    """Requirement 10: v1-v5 never satisfies a v6 current reuse."""

    repository = _seed(tmp_path)
    ref = _t_ref(repository)
    legacy = _result("analysis-prompt-v5", evidence_ids=[ref], point_ids=[ref])
    # The current path only ever accepts the live identity, so it can never be
    # satisfied by the stored legacy artifact.
    assert legacy.prompt_version != CURRENT_SUMMARY_PROMPT_VERSION
    with pytest.raises(LegacySummaryNotCurrentAuthority):
        require_current_summary_authority(legacy, repository)


# --- 13-15: a valid v6 Summary is eligible ----------------------------


def test_8_valid_v6_summary_is_current_authority_eligible(tmp_path: Path) -> None:
    """Requirements 13-15."""

    repository = _seed(tmp_path)
    durable = _promote(repository, _t_ref(repository))
    result = _result(
        CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[durable], point_ids=[durable]
    )
    assert current_summary_authority_defects(result, repository) == ()
    require_current_summary_authority(result, repository)
    assert repository.get_evidence(durable) is not None
    assert repository.resolve_verified_evidence_text(durable) is not None
    assert result.evidence[0].evidence_id == durable
    assert all(len(item.evidence_id) == 64 for item in result.evidence)
    assert all(len(eid) == 64 for eid in result.core_points[0].evidence_ids)


def test_9_a_v6_summary_is_provider_free_to_reuse(tmp_path: Path) -> None:
    """Requirement 23: eligibility is decided without any provider call."""

    repository = _seed(tmp_path)
    durable = _promote(repository, _t_ref(repository))
    result = _result(
        CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[durable], point_ids=[durable]
    )
    before = repository.get_provider_call(result.request_hash)
    require_current_summary_authority(result, repository)
    assert repository.get_provider_call(result.request_hash) == before


# --- 16-17: corrupt v6 must not be trusted on identity alone ----------


def test_10_corrupt_v6_with_temporary_transcript_ref_fails(tmp_path: Path) -> None:
    """Requirement 16: identity alone is not authority."""

    repository = _seed(tmp_path)
    ref = _t_ref(repository)
    result = _result(CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[ref], point_ids=[ref])
    defects = current_summary_authority_defects(result, repository)
    assert not any(
        d.startswith("summary_prompt_identity_is_legacy") for d in defects
    )
    assert any("summary_citation_is_not_durable" in d for d in defects)
    assert any("summary_citation_is_temporary_ref" in d for d in defects)
    with pytest.raises(SummaryCitationNotDurable):
        require_current_summary_authority(result, repository)


def test_11_corrupt_v6_with_metadata_ref_fails(tmp_path: Path) -> None:
    """Requirement 17."""

    repository = _seed(tmp_path)
    ref = _m_ref(repository)
    result = _result(CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[ref], point_ids=[ref])
    with pytest.raises(SummaryCitationNotDurable):
        require_current_summary_authority(result, repository)


def test_12_corruption_and_staleness_are_distinguishable(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    durable = _promote(repository, _t_ref(repository))
    stale = _result("analysis-prompt-v5", evidence_ids=[durable], point_ids=[durable])
    corrupt = _result(
        CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=["f" * 64], point_ids=["f" * 64]
    )
    with pytest.raises(LegacySummaryNotCurrentAuthority):
        require_current_summary_authority(stale, repository)
    with pytest.raises(SummaryCitationNotDurable):
        require_current_summary_authority(corrupt, repository)


def test_13_a_point_citing_a_non_authoritative_id_fails(tmp_path: Path) -> None:
    """The persisted contract already refuses it; the gate defends the bypass."""

    from pydantic import ValidationError

    repository = _seed(tmp_path)
    durable = _promote(repository, _t_ref(repository))
    with pytest.raises(ValidationError):
        _result(
            CURRENT_SUMMARY_PROMPT_VERSION,
            evidence_ids=[durable],
            point_ids=[durable, "9" * 64],
        )
    with pytest.raises(SummaryCitationNotDurable) as caught:
        require_current_summary_authority(_BypassedPoint(durable, "9" * 64), repository)
    assert "not_authoritative" in str(caught.value)


class _Point:
    def __init__(self, evidence_ids):
        self.evidence_ids = tuple(evidence_ids)


class _Excerpt:
    def __init__(self, evidence_id):
        self.evidence_id = evidence_id


class _BypassedPoint:
    """An object that skips AnalysisResult validation entirely."""

    prompt_version = CURRENT_SUMMARY_PROMPT_VERSION
    key_facts = ()
    product_opportunities = ()
    business_opportunities = ()
    actionable_directions = ()
    hypotheses_to_validate = ()
    action_recommendations = ()
    risks = ()

    def __init__(self, authoritative: str, stray: str):
        self.evidence = (_Excerpt(authoritative),)
        self.core_points = (_Point((authoritative, stray)),)


def test_14_an_empty_citation_is_rejected_by_the_persisted_contract(
    tmp_path: Path,
) -> None:
    """The domain layer already forbids an empty citation id; the gate keeps a
    defensive branch for any object that bypasses it."""

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _result(CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[""], point_ids=[""])
    repository = _seed(tmp_path)

    class _Bypass:
        prompt_version = CURRENT_SUMMARY_PROMPT_VERSION
        evidence = ()
        core_points = ()
        key_facts = ()
        product_opportunities = ()
        business_opportunities = ()
        actionable_directions = ()
        hypotheses_to_validate = ()
        action_recommendations = ()
        risks = ()

    assert current_summary_authority_defects(_Bypass(), repository) == ()


# --- restart ------------------------------------------------------------


def test_15_eligibility_survives_repository_restart(tmp_path: Path) -> None:
    first = _seed(tmp_path)
    durable = _promote(first, _t_ref(first))
    result = _result(
        CURRENT_SUMMARY_PROMPT_VERSION, evidence_ids=[durable], point_ids=[durable]
    )
    del first
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    reopened.initialize(now=NOW)
    require_current_summary_authority(result, reopened)


# --- runtime + API layering --------------------------------------------


def test_16_runtime_provenance_requires_only_the_current_contract() -> None:
    """The layering fix: validator is current-only, parser stays v1-v6."""

    import inspect

    from youtube_intel.runtime import RuntimeOperations

    source = inspect.getsource(RuntimeOperations._validate_analysis_provenance)
    # The current-contract requirement now lives in the shared Analysis
    # provenance verifier, which runtime and Weekly both call.
    assert "require_analysis_call_matches_payload" in source
    assert "require_analysis_provider_call" in source
    assert '"analysis-prompt-v5"' not in source
    assert "CURRENT_SUMMARY_PROMPT_VERSION" in source
    load_source = inspect.getsource(RuntimeOperations._load_analysis)
    assert "require_current_summary_authority" in load_source


def test_17_legacy_pointer_surfaces_a_truthful_regeneration_state() -> None:
    """Requirements 18-20: the API never emits a temporary ref."""

    import inspect

    from youtube_intel.local_api import LocalApiApplication

    source = inspect.getsource(LocalApiApplication._note_projection)
    assert "LegacySummaryNotCurrentAuthority" in source
    assert "CURRENT_SUMMARY_LEGACY_REGENERATION_REQUIRED" in source


def test_17b_eligibility_is_decided_before_integrity() -> None:
    """A genuine legacy record is *stale*, not corrupt.

    The legacy verdict must be reached before the provider-call integrity check,
    otherwise a real historical artifact would surface a generic provenance
    failure and lose its truthful regeneration-required state.
    """

    import inspect

    from youtube_intel.runtime import RuntimeOperations

    source = inspect.getsource(RuntimeOperations._validate_analysis_provenance)
    legacy_at = source.index("LegacySummaryNotCurrentAuthority")
    provenance_at = source.index("persisted analysis provider call provenance is invalid")
    assert legacy_at < provenance_at
    assert "HISTORICAL_SUMMARY_PROMPT_VERSIONS" in source
    # An identity outside the known readability set is still an integrity fault.
    assert "persisted analysis prompt identity is unknown" in source


def test_17c_an_unknown_prompt_identity_is_not_treated_as_legacy() -> None:
    """Widening readability must never silently authorize an unknown identity."""

    from youtube_intel.summary_evidence_authority import (
        CURRENT_SUMMARY_PROMPT_VERSION,
        HISTORICAL_SUMMARY_PROMPT_VERSIONS,
    )

    assert "analysis-prompt-v7" not in HISTORICAL_SUMMARY_PROMPT_VERSIONS
    assert "analysis-prompt-v7" != CURRENT_SUMMARY_PROMPT_VERSION


def test_18_no_alias_or_backfill_helper_was_introduced() -> None:
    """No compatibility alias may make a legacy citation durable."""

    from youtube_intel import summary_evidence_authority as authority

    for forbidden in ("alias", "backfill", "rewrite", "upgrade", "migrate"):
        assert not hasattr(authority, f"{forbidden}_legacy")
        assert not hasattr(authority, f"legacy_{forbidden}")


def test_19_defects_are_deterministic_and_deduplicated(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    t_ref, m_ref = _t_ref(repository), _m_ref(repository)
    result = _result(
        CURRENT_SUMMARY_PROMPT_VERSION,
        evidence_ids=[t_ref, m_ref],
        point_ids=[t_ref, m_ref],
    )
    first = current_summary_authority_defects(result, repository)
    assert first == current_summary_authority_defects(result, repository)
    assert len(first) == len(set(first))
    assert json.dumps([str(defect) for defect in first])
