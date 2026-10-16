"""Transactional identities for tracked Content retry; no Source Run is synthesized."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any

from youtube_intel.domain import ProcessingStage, VideoMetadata
from youtube_intel.following_tracking import verify_tracking
from youtube_intel.state import (
    JobType,
    ProviderCallRequest,
    SQLiteStateRepository,
    format_utc_datetime,
)
from youtube_intel.tracked_retry_context import RetryConflict, RetryIntegrity
from youtube_intel.transcripts import build_raw_request_hash

CONTRACT = "tracked-content-retry-v1"
OPERATION = "RETRY_NATIVE_TRANSCRIPT"
PREFIX = "tracked-content-retry:v1:"
JOB_PREFIX = "tracked-content-retry-job:v1:"
LIVE = ("QUEUED", "ACQUIRING", "FINALIZING", "ATTENTION")
TERMINAL = ("SUCCEEDED", "FAILED", "CANCELLED", "AMBIGUOUS")
KNOWN_RETRYABLE = frozenset({"TRANSIENT_NETWORK", "RATE_LIMITED", "PROVIDER_UNAVAILABLE", "INVALID_RESPONSE", "CONTENT_UNAVAILABLE"})


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise RetryConflict("Content retry command identity is invalid")
    return value


def provider_request(row: dict[str, Any]) -> ProviderCallRequest:
    parameters = json.loads(row["parameters_json"])
    return ProviderCallRequest(operation="subtitle.fetch", normalized_input_hash=row["raw_request_hash"],
        provider=parameters["adapter_name"], model=None, prompt_version=parameters["selection_policy_version"],
        schema_version=parameters["format_policy_version"], deterministic_artifact_key="subtitle-source:" + row["raw_request_hash"])


def request_identity(source_id: str, command_id: str) -> str:
    return PREFIX + digest({"contract": CONTRACT, "source_id": source_id, "operation": OPERATION, "command_id": command_id})


def target_identity(request_id: str, old_job_id: str, pipeline: str) -> str:
    return JOB_PREFIX + digest({"request_id": request_id, "old_job_id": old_job_id, "stage": "TRANSCRIPT", "pipeline_version": pipeline})


def event(state: str, *, prior: str | None, revision: int, epoch: int, at: str,
          name: str, action: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"event": name, "prior_state": prior, "state": state, "revision": revision,
            "fencing_epoch": epoch, "at": at, "action": action}


def read(connection: sqlite3.Connection, request_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    r = connection.execute("SELECT * FROM tracked_content_retry_requests WHERE request_id=?", (request_id,)).fetchone()
    e = connection.execute("SELECT * FROM tracked_content_retry_executions WHERE request_id=?", (request_id,)).fetchone()
    if r is None or e is None:
        raise RetryIntegrity("Content retry request or execution is missing")
    request, execution = dict(r), dict(e)
    if request["contract"] != CONTRACT or request["operation"] != OPERATION:
        raise RetryIntegrity("Content retry protocol is unknown")
    for value, checksum in (("client_input_json", "client_input_sha256"), ("old_job_snapshot_json", "old_job_snapshot_sha256"), ("parameters_json", "parameters_sha256")):
        parsed = json.loads(request[value])
        if not isinstance(parsed, dict) or canonical(parsed) != request[value] or digest(parsed) != request[checksum]:
            raise RetryIntegrity("Content retry frozen input changed")
    expected = request_identity(request["source_id"], request["command_id"])
    client = {"contract": CONTRACT, "operation": OPERATION, "video_id": request["video_id"], "command_id": request["command_id"], "expected_job_id": request["expected_old_job_id"]}
    if (request_id != expected or json.loads(request["client_input_json"]) != client
        or request["target_job_id"] != target_identity(expected, request["expected_old_job_id"], request["pipeline_version"])
        or request["provider"] != "YOUTUBE" or request["target_stage"] != "TRANSCRIPT"
        or execution["source_id"] != request["source_id"]):
        raise RetryIntegrity("Content retry identity changed")
    parameters = json.loads(request["parameters_json"])
    if set(parameters) != {"language_preferences", "adapter_name", "adapter_version", "selection_policy_version", "format_policy_version", "native_timing_policy_version", "normalization_version", "quality_policy_version", "metadata_snapshot", "local_finalize_max_attempts"}:
        raise RetryIntegrity("Content retry parameter contract changed")
    generation = int(expected.removeprefix(PREFIX)[:15], 16)
    raw_hash = build_raw_request_hash(video_id=request["video_id"], language_preferences=parameters["language_preferences"],
        provider=parameters["adapter_name"], provider_version=parameters["adapter_version"], refresh_generation=generation,
        selection_policy_version=parameters["selection_policy_version"], format_policy_version=parameters["format_policy_version"])
    if request["refresh_generation"] != generation or raw_hash != request["raw_request_hash"] or provider_request(request).request_hash != request["provider_request_hash"]:
        raise RetryIntegrity("Content retry provider identity changed")
    old = connection.execute("SELECT * FROM jobs WHERE job_id=?", (request["expected_old_job_id"],)).fetchone()
    target = connection.execute("SELECT * FROM jobs WHERE job_id=?", (request["target_job_id"],)).fetchone()
    if old is None or target is None or canonical(dict(old)) != request["old_job_snapshot_json"]:
        raise RetryIntegrity("Content retry job history is missing or changed")
    if (old["video_id"] != request["video_id"] or old["status"] != "FAILED_FINAL" or old["job_type"] != "VIDEO_STAGE"
        or old["target_stage"] != "TRANSCRIPT" or old["last_error_code"] not in KNOWN_RETRYABLE
        or old["lease_owner"] is not None or old["lease_until"] is not None or old["finished_at"] is None):
        raise RetryIntegrity("Content retry original failure is not known and eligible")
    if (target["video_id"] != request["video_id"] or target["target_stage"] != "TRANSCRIPT" or target["job_type"] != "VIDEO_STAGE"
        or target["pipeline_version"] != request["pipeline_version"] or target["max_attempts"] != 1
        or target["scope_key"] != f"video:{request['video_id']}:TRANSCRIPT" or target["scoring_lineage_version"] is not None):
        raise RetryIntegrity("Content retry target changed")
    observation = connection.execute("SELECT * FROM source_observations WHERE source_id=? AND canonical_identity=?", (request["source_id"], request["observation_identity"])).fetchone()
    if observation is None or observation["baseline"] != 0 or observation["enrollment"] != "ENROLLED" or observation["content_id"] != request["video_id"]:
        raise RetryIntegrity("Content retry enrollment changed")
    if execution["provider_call_hash"] not in (None, request["provider_request_hash"]):
        raise RetryIntegrity("Content retry provider association changed")
    events = json.loads(execution["events_json"])
    if canonical(events) != execution["events_json"] or not isinstance(events, list) or not events:
        raise RetryIntegrity("Content retry history changed")
    prior = None
    previous_revision = -1
    for item in events:
        if (not isinstance(item, dict) or set(item) != {"event", "prior_state", "state", "revision", "fencing_epoch", "at", "action"}
            or item["prior_state"] != prior or type(item["revision"]) is not int or item["revision"] <= previous_revision):
            raise RetryIntegrity("Content retry history is inconsistent")
        prior, previous_revision = item["state"], item["revision"]
    if prior != execution["state"] or previous_revision > execution["revision"]:
        raise RetryIntegrity("Content retry projection is inconsistent")
    return request, execution


def public(request: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    return {"request_id": request["request_id"], "video_id": request["video_id"], "source_id": request["source_id"],
        "expected_job_id": request["expected_old_job_id"], "target_job_id": request["target_job_id"],
        "state": execution["state"], "revision": execution["revision"], "error_code": execution["error_code"],
        "can_resume_local": execution["state"] == "ATTENTION" and execution["local_attempt_count"] < 3,
        "can_close_local": execution["state"] == "ATTENTION", "can_cancel": execution["state"] == "QUEUED"}


def validate_source(connection: sqlite3.Connection, repository: SQLiteStateRepository, video_id: str,
                    *, source_id: str | None = None, require_enabled: bool = True) -> sqlite3.Row:
    rows = connection.execute("SELECT s.* FROM source_subscriptions s JOIN source_observations o ON o.source_id=s.source_id JOIN source_video_links l ON l.source_id=s.source_id AND l.video_id=o.content_id JOIN videos v ON v.video_id=o.content_id WHERE o.content_id=? AND o.baseline=0 AND o.enrollment='ENROLLED' AND s.provider='YOUTUBE' AND s.source_type='CHANNEL' AND v.provider='YOUTUBE' AND v.channel_id=s.channel_id", (video_id,)).fetchall()
    if len(rows) != 1 or (source_id is not None and rows[0]["source_id"] != source_id):
        raise RetryConflict("Content retry needs one exact tracked enrollment")
    source: sqlite3.Row = rows[0]
    verify_tracking(connection, source["source_id"], repository=repository)
    tracking = connection.execute("SELECT health FROM source_tracking_state WHERE source_id=?", (source["source_id"],)).fetchone()
    if tracking is None or tracking[0] in {"STATE_INVALID", "RISK_CONTROLLED", "ACCESS_DENIED"}:
        raise RetryConflict("Content retry source authority is unavailable")
    if require_enabled and source["enabled"] != 1:
        raise RetryConflict("Content retry source is paused")
    return source


def admit(repository: SQLiteStateRepository, video_id: str, *, command_id: str, expected_job_id: str,
          parameters: dict[str, Any], now: datetime) -> dict[str, Any]:
    command_id, expected_job_id = identifier(command_id), identifier(expected_job_id)
    identifier(video_id)
    client = {"contract": CONTRACT, "operation": OPERATION, "video_id": video_id, "command_id": command_id, "expected_job_id": expected_job_id}
    timestamp = format_utc_datetime(now)
    with repository._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        history = connection.execute("SELECT request_id FROM tracked_content_retry_requests WHERE video_id=? AND operation=? AND command_id=? LIMIT 2", (video_id, OPERATION, command_id)).fetchall()
        if history:
            if len(history) != 1:
                raise RetryIntegrity("Content retry command has ambiguous history")
            request, execution = read(connection, history[0][0])
            if request["client_input_json"] != canonical(client):
                raise RetryConflict("Content retry command input conflicts")
            return public(request, execution)
        source = validate_source(connection, repository, video_id)
        source_id = source["source_id"]
        if connection.execute("SELECT 1 FROM source_runs WHERE source_id=? AND state IN ('QUEUED','RUNNING','WAITING','PARTIAL','NEEDS_ATTENTION') UNION ALL SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING' UNION ALL SELECT 1 FROM tracked_content_retry_executions WHERE source_id=? AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION') LIMIT 1", (source_id, source_id, source_id)).fetchone():
            raise RetryConflict("Content retry cannot overlap Source work")
        video = connection.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
        old = connection.execute("SELECT * FROM jobs WHERE job_id=?", (expected_job_id,)).fetchone()
        latest = connection.execute("SELECT job_id FROM jobs WHERE video_id=? AND job_type='VIDEO_STAGE' ORDER BY created_at DESC,job_id DESC LIMIT 1", (video_id,)).fetchone()
        if (video is None or video["pipeline_status"] != "METADATA_READY" or old is None or latest is None or latest[0] != expected_job_id
            or old["video_id"] != video_id or old["target_stage"] != "TRANSCRIPT" or old["job_type"] != "VIDEO_STAGE" or old["status"] != "FAILED_FINAL"
            or old["pipeline_version"] != video["pipeline_version"] or old["last_error_code"] not in KNOWN_RETRYABLE
            or old["lease_owner"] is not None or old["lease_until"] is not None or old["finished_at"] is None):
            raise RetryConflict("Content retry needs the current known terminal transcript failure")
        attempt = connection.execute("SELECT * FROM job_attempts WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1", (expected_job_id,)).fetchone()
        if attempt is None or attempt["outcome"] != "FAILED_FINAL" or attempt["error_code"] != old["last_error_code"] or attempt["finished_at"] is None:
            raise RetryConflict("Content retry terminal attempt is unverified")
        if connection.execute("SELECT 1 FROM jobs WHERE video_id=? AND status NOT IN ('SUCCEEDED','FAILED_FINAL') UNION ALL SELECT 1 FROM job_attempts a JOIN jobs j ON j.job_id=a.job_id WHERE j.video_id=? AND a.finished_at IS NULL LIMIT 1", (video_id, video_id)).fetchone():
            raise RetryConflict("Content work is already active")
        # Legacy calls have no complete job linkage. Unresolved calls cannot be
        # guessed to be unrelated; their existing recovery must settle them first.
        if connection.execute("SELECT 1 FROM provider_calls WHERE status NOT IN ('SUCCEEDED','FAILED_FINAL') UNION ALL SELECT 1 FROM provider_dispatch_states WHERE status NOT IN ('SUCCESS_DURABLY_RECORDED','FAILED_KNOWN') LIMIT 1").fetchone():
            raise RetryConflict("A provider outcome is unresolved")
        metadata = VideoMetadata.model_validate(parameters["metadata_snapshot"])
        if metadata.video_id != video_id or metadata.channel_id != source["channel_id"] or metadata.availability.value != "public":
            raise RetryConflict("Content retry metadata is unavailable")
        request_id = request_identity(source_id, command_id)
        generation = int(request_id.removeprefix(PREFIX)[:15], 16)
        raw_hash = build_raw_request_hash(video_id=video_id, language_preferences=parameters["language_preferences"], provider=parameters["adapter_name"], provider_version=parameters["adapter_version"], refresh_generation=generation)
        target_id = target_identity(request_id, expected_job_id, video["pipeline_version"])
        values = {"request_id": request_id, "contract": CONTRACT, "operation": OPERATION, "command_id": command_id,
            "client_input_json": canonical(client), "client_input_sha256": digest(client), "source_id": source_id, "video_id": video_id,
            "observation_identity": video_id, "provider": "YOUTUBE", "channel_id": source["channel_id"], "expected_old_job_id": expected_job_id,
            "old_job_snapshot_json": canonical(dict(old)), "old_job_snapshot_sha256": digest(dict(old)), "target_job_id": target_id,
            "pipeline_version": video["pipeline_version"], "target_stage": "TRANSCRIPT", "parameters_json": canonical(parameters),
            "parameters_sha256": digest(parameters), "refresh_generation": generation, "raw_request_hash": raw_hash, "created_at": timestamp}
        values["provider_request_hash"] = provider_request(values).request_hash
        if connection.execute("SELECT 1 FROM provider_calls WHERE request_hash=?", (values["provider_request_hash"],)).fetchone():
            raise RetryConflict("Content retry provider identity already exists")
        repository._insert_job(connection, job_id=target_id, scope_key=f"video:{video_id}:TRANSCRIPT", video_id=video_id,
            job_type=JobType.VIDEO_STAGE, target_stage=ProcessingStage.TRANSCRIPT, pipeline_version=video["pipeline_version"], max_attempts=1,
            available_at=timestamp, now=timestamp)
        columns = ",".join(values)
        connection.execute(f"INSERT INTO tracked_content_retry_requests ({columns}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
        action = {"operation": OPERATION, "command_id": command_id, "expected_revision": None, "input_json": canonical(client), "input_sha256": digest(client), "applied_revision": 0}
        connection.execute("INSERT INTO tracked_content_retry_executions(request_id,source_id,state,events_json,updated_at) VALUES(?,?,'QUEUED',?,?)", (request_id, source_id, canonical([event("QUEUED", prior=None, revision=0, epoch=0, at=timestamp, name="ADMITTED", action=action)]), timestamp))
        request, execution = read(connection, request_id)
        connection.commit()
        return public(request, execution)
