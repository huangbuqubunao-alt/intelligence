"""Strict forward and reverse retry ownership and byte provenance validation."""

from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
from typing import Any

from youtube_intel.domain import VideoMetadata
from youtube_intel.source_authority import read_managed, sha256
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.tracked_retry_context import RetryIntegrity
from youtube_intel.tracked_retry_files import provenance, read_buffer
from youtube_intel.tracked_retry_store import (
    CONTRACT,
    LIVE,
    canonical,
    digest,
    provider_request,
    read,
    verify_old_failure,
)
from youtube_intel.transcripts import (
    SUBTITLE_QUALITY_POLICY,
    TranscriptJobContext,
    _capture_artifact_write,
    _decode_source_metadata,
    _validate_source_provenance,
)


def verify_request(
    repository: SQLiteStateRepository,
    root: Path,
    request_id: str,
    *,
    settled: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    with closing(repository._connect(read_only=True)) as connection, connection:
        request, execution = read(connection, request_id)
        target = connection.execute(
            "SELECT * FROM jobs WHERE job_id=?", (request["target_job_id"],)
        ).fetchone()
        call = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash=?",
            (request["provider_request_hash"],),
        ).fetchone()
        dispatch = connection.execute(
            "SELECT * FROM provider_dispatch_states WHERE request_hash=?",
            (request["provider_request_hash"],),
        ).fetchone()
        files = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM tracked_content_retry_files WHERE request_id=?",
                (request_id,),
            )
        ]
        source = connection.execute(
            "SELECT * FROM source_subscriptions WHERE source_id=?",
            (request["source_id"],),
        ).fetchone()
        video = connection.execute(
            "SELECT * FROM videos WHERE video_id=?", (request["video_id"],)
        ).fetchone()
        link = connection.execute(
            "SELECT 1 FROM source_video_links WHERE source_id=? AND video_id=?",
            (request["source_id"], request["video_id"]),
        ).fetchone()
        if (
            source is None
            or video is None
            or link is None
            or source["provider"] != "YOUTUBE"
            or source["source_type"] != "CHANNEL"
            or source["channel_id"] != request["channel_id"]
            or video["provider"] != "YOUTUBE"
            or video["channel_id"] != request["channel_id"]
        ):
            raise RetryIntegrity("Content retry historical source identity changed")
        parameters = json.loads(request["parameters_json"])
        video_metadata = VideoMetadata.model_validate(parameters["metadata_snapshot"])
        if (
            video_metadata.video_id != request["video_id"]
            or video_metadata.channel_id != request["channel_id"]
            or parameters["local_finalize_max_attempts"] != 3
            or not isinstance(parameters["language_preferences"], list)
            or any(type(v) is not str for v in parameters["language_preferences"])
        ):
            raise RetryIntegrity("Content retry frozen parameters are invalid")
        state = execution["state"]
        history=json.loads(execution['events_json'])
        marker=any(item['event']=='DISPATCH_INTENT' for item in history)
        if settled and state in LIVE:
            raise RetryIntegrity(
                "Content retry is still active or needs local attention"
            )
        if execution["provider_call_hash"] is None:
            if (
                call is not None
                or dispatch is not None
                or files
                or state not in ("QUEUED", "FAILED", "CANCELLED")
                or target["status"]
                != ("PENDING" if state == "QUEUED" else "FAILED_FINAL")
                or target["attempt_count"] != 0
            ):
                raise RetryIntegrity("Content retry pre-dispatch projection changed")
            if state in {'FAILED', 'CANCELLED'}:
                verify_old_failure(connection, target, source_id=request['source_id'])
        else:
            attempts=connection.execute('SELECT * FROM job_attempts WHERE job_id=? ORDER BY attempt_number',(target['job_id'],)).fetchall()
            if (target['attempt_count']!=1 or len(attempts)!=1 or attempts[0]['attempt_number']!=1
                or (target['status']=='RUNNING' and (attempts[0]['outcome'] is not None or attempts[0]['finished_at'] is not None))
                or (target['status'] in {'SUCCEEDED','FAILED_FINAL'} and (
                    attempts[0]['outcome']!=target['status'] or attempts[0]['finished_at']!=target['finished_at']
                    or attempts[0]['error_code']!=target['last_error_code']))):
                raise RetryIntegrity('Content retry real target attempt changed')
            if (
                call is None
                or dispatch is None
                or not repository._provider_request_matches(
                    call, provider_request(request)
                )
                or call["attempt_count"] != 1
                or any(
                    call[k] is not None
                    for k in ("input_tokens", "output_tokens", "cost_microusd")
                )
            ):
                raise RetryIntegrity("Content retry provider proof changed")
            closed_before_dispatch = history[-1]['event']=='HISTORY_LIMIT_CLOSED' and json.loads(history[-1]['action']['input_json'])['dispatch_status']=='NOT_DISPATCHED'
            if (dispatch['status']=='NOT_DISPATCHED' and marker
                or dispatch['status']!='NOT_DISPATCHED' and not marker and not closed_before_dispatch):
                raise RetryIntegrity('Content retry durable dispatch marker changed')
            if state in ("FINALIZING", "ATTENTION", "SUCCEEDED"):
                if (
                    call["status"] != "SUCCEEDED"
                    or target["status"] != "SUCCEEDED"
                    or dispatch["status"] != "SUCCESS_DURABLY_RECORDED"
                ):
                    raise RetryIntegrity(
                        "Content retry local finalization lost provider success"
                    )
            elif state == "AMBIGUOUS":
                if (
                    call["status"] != "FAILED_FINAL"
                    or target["status"] != "FAILED_FINAL"
                    or dispatch["status"] != "AMBIGUOUS"
                    or execution["error_code"] != "DISPATCH_OUTCOME_UNKNOWN"
                ):
                    raise RetryIntegrity("Content retry unknown receipt changed")
            elif state == "FAILED":
                if (call["status"], target["status"], dispatch["status"]) not in {
                    ("FAILED_FINAL", "FAILED_FINAL", "FAILED_KNOWN"),
                    ("SUCCEEDED", "SUCCEEDED", "SUCCESS_DURABLY_RECORDED"),
                }:
                    raise RetryIntegrity(
                        "Content retry terminal failure is inconsistent"
                    )
            elif state != "ACQUIRING" or target["status"] not in (
                "RUNNING",
                "SUCCEEDED",
                "FAILED_FINAL",
            ):
                raise RetryIntegrity("Content retry execution and target disagree")
            if state not in ("ACQUIRING",):
                if (
                    any(
                        call[k] is not None
                        for k in ("reservation_owner", "lease_until")
                    )
                    or any(
                        target[k] is not None for k in ("lease_owner", "lease_until")
                    )
                    or connection.execute(
                        "SELECT 1 FROM job_attempts WHERE job_id=? AND finished_at IS NULL",
                        (target["job_id"],),
                    ).fetchone()
                ):
                    raise RetryIntegrity(
                        "Content retry terminal/local target still has an active writer"
                    )
    by_path = {row["relative_path"]: row for row in files}
    for row in files:
        proof = json.loads(row["proof_json"])
        if (
            canonical(proof) != row["proof_json"]
            or digest(proof) != row["proof_sha256"]
            or set(proof)
            != {
                "contract",
                "request_id",
                "provider_request_hash",
                "parameters_sha256",
                "fencing_epoch",
                "logical_target_path",
                "expected_artifact_id",
                "capture_artifact_id",
                "source_format",
                "source_language",
                "requested_language",
                "source_type",
                "normalization_version",
                "quality_policy_version",
            }
        ):
            raise RetryIntegrity("Content retry file intent changed")
        if (
            proof["contract"] != CONTRACT
            or proof["request_id"] != request_id
            or proof["provider_request_hash"] != request["provider_request_hash"]
            or proof["parameters_sha256"] != request["parameters_sha256"]
            or type(proof["fencing_epoch"]) is not int
            or not 0 < proof["fencing_epoch"] <= execution["fencing_epoch"]
        ):
            raise RetryIntegrity("Content retry file ownership changed")
        logical = proof["logical_target_path"]
        original = by_path.get(logical)
        if (
            original is None
            or original["role"] == "WRITE_BUFFER"
            or (row["role"] != "WRITE_BUFFER" and row["relative_path"] != logical)
        ):
            raise RetryIntegrity("Content retry buffer lost its logical producer")
        if row["role"] == "WRITE_BUFFER":
            expected_buffer = str(
                Path(logical).with_name(
                    ".tracked-buffer-"
                    + digest(
                        {
                            "request_id": request_id,
                            "relative": logical,
                            "epoch": proof["fencing_epoch"],
                        }
                    )
                )
            )
            if (row['relative_path'] != expected_buffer
                or any(row[k]!=original[k] for k in ('expected_sha256','expected_size_bytes'))
                or {k:v for k,v in proof.items() if k!='fencing_epoch'} != {k:v for k,v in json.loads(original['proof_json']).items() if k!='fencing_epoch'}):
                raise RetryIntegrity("Content retry buffer identity changed")
        if row["state"] == "PLANNED":
            if settled or state not in LIVE:
                raise RetryIntegrity("Content retry file intent is not settled")
            continue
        try:
            body = (
                read_buffer(root, row["relative_path"])
                if row["role"] == "WRITE_BUFFER"
                else read_managed(
                    root,
                    row["relative_path"],
                    maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
                )
            )
        except FileNotFoundError:
            if row["state"] != "ABSENT":
                raise RetryIntegrity(
                    "Content retry retained bytes are missing"
                ) from None
            body = None
        if row["state"] == "ABSENT":
            if (
                body is not None
                or (root / row["relative_path"]).is_symlink()
                or row["observed_sha256"] is not None
                or row["observed_size_bytes"] is not None
            ):
                raise RetryIntegrity("Content retry absent file exists")
        else:
            if (
                body is None
                or sha256(body) != row["observed_sha256"]
                or len(body) != row["observed_size_bytes"]
            ):
                raise RetryIntegrity("Content retry retained bytes changed")
            if row["state"] == "VERIFIED":
                if (
                    sha256(body) != row["expected_sha256"]
                    or len(body) != row["expected_size_bytes"]
                ):
                    raise RetryIntegrity(
                        "Content retry verified file differs from its intent"
                    )
            elif row["state"] != "RETAINED_PARTIAL" or row["role"] != "WRITE_BUFFER":
                raise RetryIntegrity("Content retry file state is invalid")
        if row["role"] == "WRITE_BUFFER":
            continue
        if original["role"] == "CAPTURE":
            metadata = _decode_source_metadata(
                Path(logical).name, video_id=request["video_id"]
            )
            _validate_source_provenance(
                metadata,
                parameters["language_preferences"],
                video_id=request["video_id"],
            )
            capture = _capture_artifact_write(
                video_id=request["video_id"],
                context=TranscriptJobContext(
                    job_id=request["target_job_id"],
                    owner="proof",
                    pipeline_version=request["pipeline_version"],
                    refresh_generation=request["refresh_generation"],
                ),
                raw_request_hash=request["raw_request_hash"],
                metadata=metadata,
                content_hash=row["expected_sha256"],
                provider=parameters["adapter_name"],
                provider_version=parameters["adapter_version"],
            )
            if (
                proof["expected_artifact_id"] != capture.artifact_id
                or proof["capture_artifact_id"] != capture.artifact_id
                or capture.relative_path != logical
            ):
                raise RetryIntegrity("Content retry capture producer changed")
        if body is not None:
            role, rebuilt = provenance(
                repository, root, request, logical, body, epoch=proof["fencing_epoch"]
            )
            if role != row["role"] or rebuilt != proof:
                raise RetryIntegrity(
                    "Content retry file producer cannot be reconstructed"
                )
        elif row["role"] not in ("CAPTURE",):
            payload=derivation_body(repository,root,request,row)
            role,rebuilt=provenance(repository,root,request,logical,payload,epoch=proof['fencing_epoch'])
            if (sha256(payload)!=row['expected_sha256'] or len(payload)!=row['expected_size_bytes']
                or role!=row['role'] or rebuilt!=proof):
                raise RetryIntegrity('Content retry absent derivative proof changed')
    with closing(repository._connect(read_only=True)) as connection, connection:
        owned_artifacts = connection.execute(
            "SELECT * FROM artifacts WHERE job_id=? AND deleted_at IS NULL",
            (request["target_job_id"],),
        ).fetchall()
        for artifact in owned_artifacts:
            intent = by_path.get(artifact["relative_path"])
            if (
                intent is None
                or intent["state"] != "VERIFIED"
                or intent["expected_sha256"] != artifact["content_hash"]
                or artifact["storage_root"] != "DATA"
            ):
                raise RetryIntegrity(
                    "Content retry artifact lost its verified file intent"
                )
        if execution["state"] == "SUCCEEDED":
            summary = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id=?",
                (execution["summary_artifact_id"],),
            ).fetchone()
            if (
                summary is None
                or summary["relative_path"] not in by_path
                or by_path[summary["relative_path"]]["role"] != "SUMMARY_DERIVATION"
            ):
                raise RetryIntegrity(
                    "Content retry completed Summary lost its file intent"
                )
    if execution["state"] == "SUCCEEDED":
        from youtube_intel.extractive_summary import ExtractiveSummaryService
        from youtube_intel.tracked_retry_worker import completion

        proof = json.loads(execution["completion_json"])
        if (
            canonical(proof) != execution["completion_json"]
            or digest(proof) != execution["completion_sha256"]
            or completion(repository, request, execution["summary_artifact_id"])
            != proof
        ):
            raise RetryIntegrity("Content retry completion changed")
        ExtractiveSummaryService(repository, root).read(
            request["video_id"], execution["summary_artifact_id"]
        )
    return request, execution, files


def verify_all(
    repository: SQLiteStateRepository, root: Path, *, settled: bool = False
) -> list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]]:
    with closing(repository._connect(read_only=True)) as connection, connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required = {
            "tracked_content_retry_requests",
            "tracked_content_retry_executions",
            "tracked_content_retry_files",
        }
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if not required <= tables:
            if (
                version >= 40
                or required & tables
                or connection.execute(
                    "SELECT 1 FROM jobs WHERE job_id GLOB 'tracked-content-retry-job:*'"
                ).fetchone()
            ):
                raise RetryIntegrity("Content retry protocol tables are missing")
            return []
        if connection.execute(
            "SELECT 1 FROM jobs j LEFT JOIN tracked_content_retry_requests r ON r.target_job_id=j.job_id LEFT JOIN tracked_content_retry_executions e USING(request_id) WHERE j.job_id GLOB 'tracked-content-retry-job:*' AND (r.request_id IS NULL OR e.request_id IS NULL) UNION ALL SELECT 1 FROM tracked_content_retry_requests r LEFT JOIN tracked_content_retry_executions e USING(request_id) WHERE e.request_id IS NULL LIMIT 1"
        ).fetchone():
            raise RetryIntegrity(
                "Content retry explicit target lost its request or execution"
            )
        ids = [
            row[0]
            for row in connection.execute(
                "SELECT request_id FROM tracked_content_retry_requests ORDER BY request_id"
            )
        ]
    return [
        verify_request(repository, root, request_id, settled=settled)
        for request_id in ids
    ]


def verify_schema(connection: Any) -> None:
    """Compare the exact additive 040 SQL objects without touching owner state."""
    import sqlite3
    from importlib import resources

    names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'tracked_content_retry_%'"
        )
    }
    expected = sqlite3.connect(":memory:")
    try:
        expected.executescript(
            "CREATE TABLE jobs(job_id TEXT); CREATE TABLE source_runs(source_id TEXT,state TEXT); CREATE TABLE source_checks(source_id TEXT,status TEXT);"
        )
        expected.executescript(
            resources.files("youtube_intel.migrations")
            .joinpath("040_add_tracked_content_retry.sql")
            .read_text()
        )
        objects = {
            row[0]: row[1]
            for row in expected.execute(
                "SELECT name,sql FROM sqlite_master WHERE name LIKE 'tracked_content_retry_%'"
            )
        }
        actual = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name,sql FROM sqlite_master WHERE name LIKE 'tracked_content_retry_%'"
            )
        }
        if names != set(objects) or actual != objects:
            raise RetryIntegrity("Content retry schema objects changed")
    finally:
        expected.close()


def derivation_body(repository: SQLiteStateRepository, root: Path, request: dict[str, Any], row: dict[str, Any]) -> bytes:
    """A failed local publication is still reconstructable without provider IO."""
    if row['role']=='SUMMARY_DERIVATION':
        from youtube_intel.extractive_summary import ExtractiveSummaryService
        return ExtractiveSummaryService(repository,root)._result(request['video_id'],use_timed_candidates=True).model_dump_json().encode()
    if row['role']=='CANONICAL_DERIVATION':
        from youtube_intel.transcripts import (
            _canonical_relative_path,
            build_canonical_request_hash,
            normalize_timed_subtitle,
        )
        with closing(repository._connect(read_only=True)) as connection:
            captures=connection.execute("SELECT * FROM artifacts WHERE job_id=? AND artifact_key LIKE 'subtitle-source-capture:%'",(request['target_job_id'],)).fetchall()
        for capture in captures:
            source=read_managed(root,capture['relative_path'],maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes)
            if sha256(source)!=capture['content_hash']:
                raise RetryIntegrity('Content retry derivative source changed')
            metadata=_decode_source_metadata(Path(capture['relative_path']).name,video_id=request['video_id'])
            normalized=normalize_timed_subtitle(source,metadata.source_format)
            ch=build_canonical_request_hash(source_content_hash=normalized.source_content_hash,source_format=metadata.source_format)
            relative=_canonical_relative_path(video_id=request['video_id'],raw_request_hash=request['raw_request_hash'],canonical_request_hash=ch,quality_flags=normalized.quality_flags)
            if relative==row['relative_path']:
                return normalized.text.encode()
    raise RetryIntegrity('Content retry derivative producer is unavailable')
