"""Runtime-admitted Note V2 handoff for deterministic Weekly V2 aggregation.

``NoteV2`` is semantic presentation data, not an authority token.  This module
projects the separate, weekly-relevant facts from the existing authoritative
stores while constructing that Note, then admits the resulting immutable value
only in the current process.  The admission receipt is deliberately absent
from the public object and from its semantic identity.
"""

from __future__ import annotations

import math
import weakref
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from youtube_intel.deep_analysis_contracts import (
    TrustedDeepAnalysisSuccess,
    dacs1_sha256,
    verify_trusted_deep_analysis_success,
)
from youtube_intel.deep_analysis_persistence import (
    VerifiedPersistedDeepAnalysisRead,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.deep_analysis_runtime import _capture_trusted_success_for_persistence
from youtube_intel.domain import PipelineStatus
from youtube_intel.note_v2 import NoteV2, NoteV2Error, build_note_v2
from youtube_intel.scoring import AuthoritativeScoringReader, VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository, VideoRecord


class VerifiedNoteV2ArtifactError(ValueError):
    """The Note-to-Weekly handoff lacks authoritative, bound metadata."""


@dataclass(frozen=True, slots=True, weakref_slot=True)
class VerifiedNoteV2Artifact:
    """A runtime-verified aggregation handoff; its fields are semantic data."""

    schema_version: str
    note: NoteV2
    note_identity: str
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    source_url: str
    language: str
    completed_at: datetime
    ranking_score: float
    ranking_reason: str
    scoring_request_hash: str
    scoring_success_provenance: str
    deep_analysis_result_identity: str
    payload_scope: str
    identity: str


def _build_from_authorities(
    source: object,
    *,
    repository: SQLiteStateRepository,
    scoring_reader: AuthoritativeScoringReader,
    admit: object,
) -> VerifiedNoteV2Artifact:
    """Build and admit one weekly handoff from an authoritative 016D/016E source.

    No caller-provided score, date, URL, or arbitrary ``NoteV2`` is accepted.
    The only metadata path is the repository's completed video record plus the
    established verified scoring reader, both cross-checked against the Deep
    Analysis lineage already frozen in the Note provenance.
    """

    canonical_video_id = _authoritative_video_id(source)
    try:
        note = build_note_v2(source)
    except NoteV2Error as error:
        raise VerifiedNoteV2ArtifactError(
            "authoritative Note V2 source is invalid"
        ) from error
    if note.video_id != canonical_video_id:
        raise VerifiedNoteV2ArtifactError("Note V2 video identity is invalid")
    record = repository.get_video(note.video_id)
    _validate_video_record(record, note)
    assert record is not None
    read = scoring_reader.read(note.video_id)
    _validate_scoring_read(read, note, record)
    assert type(read) is VerifiedScoringRead
    assert record.channel_name is not None
    assert record.title is not None
    assert record.source_url is not None
    assert record.completed_at is not None
    assert read.scoring_success_provenance is not None
    artifact = VerifiedNoteV2Artifact(
        schema_version="verified-note-v2-artifact-v1",
        note=note,
        note_identity=note.identity,
        video_id=record.video_id,
        channel_id=record.channel_id,
        channel_name=record.channel_name,
        title=record.title,
        source_url=record.source_url,
        language=note.language,
        completed_at=record.completed_at,
        ranking_score=read.scoring_outcome.result.score,
        ranking_reason=read.scoring_outcome.result.reason,
        scoring_request_hash=read.scoring_outcome.result.request_hash,
        scoring_success_provenance=read.scoring_success_provenance,
        deep_analysis_result_identity=note.provenance.deep_analysis_result_identity,
        payload_scope=note.provenance.payload_scope,
        identity="",
    )
    admitted = replace(artifact, identity=_identity(artifact))
    if not callable(admit):
        raise RuntimeError("verified Note V2 admission authority is unavailable")
    admit(admitted)
    return admitted


def _make_boundary_authority() -> tuple[
    Callable[[type[object]], None], Callable[[object], bool]
]:
    admitted_artifacts: dict[
        int,
        tuple[weakref.ReferenceType[VerifiedNoteV2Artifact], str],
    ] = {}
    runtime_boundaries: weakref.WeakKeyDictionary[object, object] = (
        weakref.WeakKeyDictionary()
    )
    bound_runtime_type: type[object] | None = None

    def admit(artifact: VerifiedNoteV2Artifact) -> None:
        key = id(artifact)

        def remove(_reference: weakref.ReferenceType[VerifiedNoteV2Artifact]) -> None:
            admitted_artifacts.pop(key, None)

        admitted_artifacts[key] = (
            weakref.ref(artifact, remove),
            _snapshot(artifact),
        )

    def verify(value: object) -> bool:
        if type(value) is not VerifiedNoteV2Artifact:
            return False
        admitted = admitted_artifacts.get(id(value))
        if admitted is None or admitted[0]() is not value:
            return False
        try:
            return admitted[1] == _snapshot(value) and value.identity == _identity(
                value
            )
        except (TypeError, ValueError):
            return False

    build_from_authorities = _build_from_authorities  # noqa: F821

    def bind_runtime(runtime_type: type[object]) -> None:
        """Bind this one production composition type to an unexposed builder."""

        # Importing the composition root here makes a pre-runtime caller finish
        # its real module initialization first; a caller-defined lookalike can
        # never consume this one-time binding slot.
        from youtube_intel.runtime import RuntimeOperations

        if runtime_type is not RuntimeOperations:
            raise RuntimeError(
                "verified Note V2 requires RuntimeOperations composition"
            )
        nonlocal bound_runtime_type
        if bound_runtime_type is not None:
            if bound_runtime_type is runtime_type:
                return
            raise RuntimeError("verified Note V2 runtime authority is already bound")
        original_init = cast(Callable[..., None], runtime_type.__init__)

        def bind_instance(instance: object) -> None:
            repository = getattr(instance, "_repository", None)
            if type(repository) is not SQLiteStateRepository:
                raise RuntimeError("verified Note V2 runtime repository is invalid")
            database_path = repository._database_path
            data_root = getattr(instance, "_data_root", None)
            config = getattr(instance, "_config", None)
            if not isinstance(data_root, Path) or config is None:
                raise RuntimeError("verified Note V2 runtime configuration is invalid")
            authoritative_data_root = data_root
            settings = config.settings
            summary_threshold = settings.thresholds.summary_score
            model = settings.local_scoring.model
            output_language = settings.general.output_language

            class Boundary:
                """A capability with no caller-visible admission or metadata controls."""

                __slots__ = ()

                def build(self, source: object) -> VerifiedNoteV2Artifact:
                    authoritative_repository = SQLiteStateRepository(database_path)
                    scoring_reader = AuthoritativeScoringReader(
                        repository=authoritative_repository,
                        data_root=authoritative_data_root,
                        summary_threshold=summary_threshold,
                        pipeline_version="runtime-v1",
                        current_model=model,
                        current_output_language=output_language,
                    )
                    return build_from_authorities(
                        source,
                        repository=authoritative_repository,
                        scoring_reader=scoring_reader,
                        admit=admit,
                    )

            runtime_boundaries[instance] = Boundary()

        def initialized(instance: object, *args: object, **kwargs: object) -> None:
            original_init(instance, *args, **kwargs)
            bind_instance(instance)

        def build(instance: object, source: object) -> VerifiedNoteV2Artifact:
            boundary = runtime_boundaries.get(instance)
            build_artifact = (
                None if boundary is None else getattr(boundary, "build", None)
            )
            if not callable(build_artifact):
                raise VerifiedNoteV2ArtifactError(
                    "verified Note V2 requires a runtime-owned composition"
                )
            return cast(VerifiedNoteV2Artifact, build_artifact(source))

        setattr(runtime_type, "__init__", initialized)
        setattr(runtime_type, "build_verified_note_v2_artifact", build)
        bound_runtime_type = runtime_type

    return bind_runtime, verify


_runtime_binder, _artifact_verifier = _make_boundary_authority()
_bind_verified_note_v2_runtime: Callable[[type[object]], None] = _runtime_binder
verify_verified_note_v2_artifact: Callable[[object], bool] = _artifact_verifier
del _make_boundary_authority
del _runtime_binder
del _artifact_verifier
del _build_from_authorities


def _authoritative_video_id(source: object) -> str:
    if type(source) is TrustedDeepAnalysisSuccess:
        if not verify_trusted_deep_analysis_success(source):
            raise VerifiedNoteV2ArtifactError(
                "runtime Deep Analysis source is untrusted"
            )
        material = _capture_trusted_success_for_persistence(source)
        if material is None:
            raise VerifiedNoteV2ArtifactError(
                "runtime Deep Analysis material is unavailable"
            )
        return material.envelope.canonical_input.video_identity
    if type(source) is VerifiedPersistedDeepAnalysisRead:
        if not verify_persisted_deep_analysis_read(source):
            raise VerifiedNoteV2ArtifactError(
                "persisted Deep Analysis source is untrusted"
            )
        return source.canonical_input.video_identity
    raise VerifiedNoteV2ArtifactError(
        "verified Note V2 requires authoritative Deep Analysis input"
    )


def _validate_video_record(record: VideoRecord | None, note: NoteV2) -> None:
    if type(record) is not VideoRecord:
        raise VerifiedNoteV2ArtifactError("authoritative video record is invalid")
    if (
        record.video_id != note.video_id
        or record.pipeline_status is not PipelineStatus.COMPLETE
        or not record.should_summarize
        or record.completed_at is None
        or record.completed_at.tzinfo is None
        or record.completed_at.utcoffset() != timedelta(0)
        or not all(
            (record.channel_id, record.channel_name, record.title, record.source_url)
        )
    ):
        raise VerifiedNoteV2ArtifactError("authoritative weekly metadata is invalid")
    parsed = urlparse(record.source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VerifiedNoteV2ArtifactError("authoritative source URL is invalid")


def _validate_scoring_read(read: object, note: NoteV2, record: VideoRecord) -> None:
    if type(read) is not VerifiedScoringRead:
        raise VerifiedNoteV2ArtifactError("authoritative scoring read is invalid")
    result = read.scoring_outcome.result
    if (
        read.video_id != note.video_id
        or (
            record.authoritative_scoring_job_id is not None
            and read.scoring_job_id != record.authoritative_scoring_job_id
        )
        or read.scoring_success_provenance != note.provenance.scoring_success_provenance
        or result.request_hash != note.provenance.scoring_request_hash
        or record.score != result.score
        or not read.scoring_outcome.decision.final_should_summarize
        or not math.isfinite(result.score)
    ):
        raise VerifiedNoteV2ArtifactError("authoritative ranking score is invalid")


def _identity(artifact: VerifiedNoteV2Artifact) -> str:
    _validate_artifact_shape(artifact)
    return dacs1_sha256(
        {
            "schema_version": artifact.schema_version,
            "note_identity": artifact.note_identity,
            "video": {
                "video_id": artifact.video_id,
                "channel_id": artifact.channel_id,
                "channel_name": artifact.channel_name,
                "title": artifact.title,
                "source_url": artifact.source_url,
                "language": artifact.language,
            },
            "weekly_membership_completed_at": _utc_text(artifact.completed_at),
            "ranking": {
                "score": artifact.ranking_score,
                "reason": artifact.ranking_reason,
                "scoring_request_hash": artifact.scoring_request_hash,
                "scoring_success_provenance": artifact.scoring_success_provenance,
            },
            "provenance": {
                "deep_analysis_result_identity": artifact.deep_analysis_result_identity,
                "payload_scope": artifact.payload_scope,
            },
        }
    )


def _validate_artifact_shape(artifact: VerifiedNoteV2Artifact) -> None:
    if artifact.schema_version != "verified-note-v2-artifact-v1":
        raise ValueError("verified Note V2 artifact schema is invalid")
    if (
        artifact.note_identity != artifact.note.identity
        or artifact.video_id != artifact.note.video_id
    ):
        raise ValueError("verified Note V2 artifact Note binding is invalid")
    if artifact.language != artifact.note.language:
        raise ValueError("verified Note V2 artifact language binding is invalid")
    if (
        artifact.deep_analysis_result_identity
        != artifact.note.provenance.deep_analysis_result_identity
    ):
        raise ValueError("verified Note V2 artifact provenance binding is invalid")
    if artifact.payload_scope != artifact.note.provenance.payload_scope:
        raise ValueError("verified Note V2 artifact payload scope binding is invalid")
    if artifact.scoring_request_hash != artifact.note.provenance.scoring_request_hash:
        raise ValueError("verified Note V2 artifact scoring binding is invalid")
    if (
        artifact.scoring_success_provenance
        != artifact.note.provenance.scoring_success_provenance
    ):
        raise ValueError("verified Note V2 artifact scoring provenance is invalid")
    if (
        artifact.completed_at.tzinfo is None
        or artifact.completed_at.utcoffset() != timedelta(0)
        or not math.isfinite(artifact.ranking_score)
        or not all(
            (
                artifact.channel_id,
                artifact.channel_name,
                artifact.title,
                artifact.source_url,
            )
        )
    ):
        raise ValueError("verified Note V2 artifact metadata is invalid")


def _utc_text(value: datetime) -> str:
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _snapshot(artifact: VerifiedNoteV2Artifact) -> str:
    return dacs1_sha256(
        {
            "schema_version": "verified-note-v2-artifact-admission-v1",
            "identity": artifact.identity,
            "semantic_identity": _identity(artifact),
        }
    )


__all__ = [
    "VerifiedNoteV2Artifact",
    "VerifiedNoteV2ArtifactError",
    "verify_verified_note_v2_artifact",
]
