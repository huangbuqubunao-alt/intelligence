"""Transactional identities for tracked Content retry; no Source Run is synthesized."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
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
HISTORY_LIMIT = 128
ACQUISITION_EVENT_RESERVE = 16


def local_event_reserve(attempts: int) -> int:
    # For every remaining local attempt: user resume, recovery claim, attempt
    # event, and result; two extra slots cover entry/recovery and final Close.
    return 4 * (3 - attempts) + 2


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
          name: str, action: dict[str, Any] | None = None,
          local_attempt: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {"event": name, "prior_state": prior, "state": state, "revision": revision,
              "fencing_epoch": epoch, "at": at, "action": action}
    if local_attempt is not None:
        result['local_attempt'] = local_attempt
    return result


def _read(connection: sqlite3.Connection, request_id: str, *, verify_parent: bool = True, data_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
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
    metadata = VideoMetadata.model_validate(parameters['metadata_snapshot'])
    if (metadata.video_id != request['video_id'] or metadata.channel_id != request['channel_id']
        or parameters['local_finalize_max_attempts'] != 3
        or not isinstance(parameters['language_preferences'], list)
        or any(type(value) is not str for value in parameters['language_preferences'])
        or connection.execute("SELECT 1 FROM source_subscriptions s JOIN source_video_links l ON l.source_id=s.source_id JOIN videos v ON v.video_id=l.video_id WHERE s.source_id=? AND v.video_id=? AND s.provider='YOUTUBE' AND s.source_type='CHANNEL' AND v.provider='YOUTUBE' AND s.channel_id=? AND v.channel_id=s.channel_id", (request['source_id'],request['video_id'],request['channel_id'])).fetchone() is None):
        raise RetryIntegrity('Content retry historical source or frozen parameters changed')
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
        or old["target_stage"] != "TRANSCRIPT" or old['pipeline_version'] != request['pipeline_version']
        or old["lease_owner"] is not None or old["lease_until"] is not None or old["finished_at"] is None):
        raise RetryIntegrity("Content retry original failure is not known and eligible")
    if (target["video_id"] != request["video_id"] or target["target_stage"] != "TRANSCRIPT" or target["job_type"] != "VIDEO_STAGE"
        or target["pipeline_version"] != request["pipeline_version"] or target["max_attempts"] != 1
        or target["scope_key"] != f"video:{request['video_id']}:TRANSCRIPT" or target["scoring_lineage_version"] is not None):
        raise RetryIntegrity("Content retry target changed")
    if verify_parent:
        verify_old_failure(connection, old, source_id=request['source_id'], data_root=data_root)
    if (execution['state'] == 'QUEUED' and (target['status'] != 'PENDING' or target['attempt_count'] != 0 or execution['provider_call_hash'] is not None)
        or execution['state'] in {'FINALIZING','ATTENTION','SUCCEEDED'} and target['status'] != 'SUCCEEDED'
        or execution['state'] in {'CANCELLED','AMBIGUOUS'} and target['status'] != 'FAILED_FINAL'
        or execution['state'] == 'FAILED' and target['status'] not in {'FAILED_FINAL','SUCCEEDED'}):
        raise RetryIntegrity('Content retry execution and target disagree')
    observation = connection.execute("SELECT * FROM source_observations WHERE source_id=? AND canonical_identity=?", (request["source_id"], request["observation_identity"])).fetchone()
    if observation is None or observation["baseline"] != 0 or observation["enrollment"] != "ENROLLED" or observation["content_id"] != request["video_id"]:
        raise RetryIntegrity("Content retry enrollment changed")
    if execution["provider_call_hash"] not in (None, request["provider_request_hash"]):
        raise RetryIntegrity("Content retry provider association changed")
    events = json.loads(execution["events_json"])
    if canonical(events) != execution["events_json"] or not isinstance(events, list) or not events:
        raise RetryIntegrity("Content retry history changed")
    _verify_events(request, execution, events)
    return request, execution


def verify_old_failure(connection: sqlite3.Connection, old: sqlite3.Row, *, source_id: str, data_root: Path | None = None) -> str | None:
    """Keep generic failure admission strict; zero-call successors need an intact parent."""
    first_owner: str | None = None
    seen: set[str] = set()
    while True:
        owner = connection.execute('SELECT request_id FROM tracked_content_retry_requests WHERE target_job_id=?', (old['job_id'],)).fetchone()
        if owner is None:
            if old['job_id'].startswith('tracked-content-retry-job:'):
                raise RetryIntegrity('Content retry parent request is missing')
            _verify_known_attempt(connection, old)
            return first_owner
        if owner[0] in seen:
            raise RetryIntegrity('Content retry parent chain is cyclic')
        seen.add(owner[0])
        if first_owner is None:
            first_owner = identifier(owner[0])
        # Iterative traversal keeps arbitrarily long retained histories off the
        # Python call stack. Every ancestor is checked; none is truncated.
        parent, execution = _read(connection, owner[0], verify_parent=False, data_root=data_root)
        if parent['source_id'] != source_id or parent['video_id'] != old['video_id'] or parent['pipeline_version'] != old['pipeline_version']:
            raise RetryIntegrity('Content retry parent source changed')
        if old['attempt_count'] != 0:
            if execution['state'] != 'FAILED':
                raise RetryIntegrity('Content retry parent is not a known failure')
            call = connection.execute('SELECT * FROM provider_calls WHERE request_hash=?', (parent['provider_request_hash'],)).fetchone()
            dispatch = connection.execute('SELECT status,updated_at FROM provider_dispatch_states WHERE request_hash=?', (parent['provider_request_hash'],)).fetchone()
            terminal=json.loads(execution['events_json'])[-1]
            history_closed=terminal['event']=='HISTORY_LIMIT_CLOSED'
            captured_failure = execution['error_code'] == 'LOCAL_FINALIZATION_FAILED'
            if captured_failure:
                if call is None or dispatch is None:
                    raise RetryIntegrity('Content retry capture failure provider receipt is missing')
                from youtube_intel.tracked_retry_capture_failure import (
                    verify_capture_failure,
                )

                verify_capture_failure(connection, parent, execution, old, call, dispatch, data_root=data_root)
                _verify_known_attempt(connection, old)
            elif history_closed:
                proof=json.loads(terminal['action']['input_json'])
                attempt=connection.execute('SELECT * FROM job_attempts WHERE job_id=?',(old['job_id'],)).fetchall()
                if (proof['dispatch_status']!='NOT_DISPATCHED' or proof['had_dispatch_intent']
                    or proof['prior_state']!='ACQUIRING' or proof['target_status']!='RUNNING'
                    or proof['local_attempt_count']!=0 or execution['local_attempt_count']!=0
                    or execution['error_code']!='RETRY_CONTRACT_UNAVAILABLE'
                    or old['attempt_count']!=1 or old['last_error_code']!='CAPABILITY_UNAVAILABLE'
                    or old['last_error_message']!=execution['error_code']
                    or old['lease_owner'] is not None or old['lease_until'] is not None
                    or old['finished_at']!=execution['finished_at'] or old['updated_at']!=execution['finished_at']
                    or len(attempt)!=1 or attempt[0]['attempt_number']!=1 or attempt[0]['outcome']!='FAILED_FINAL'
                    or attempt[0]['error_code']!='CAPABILITY_UNAVAILABLE' or attempt[0]['finished_at']!=execution['finished_at']
                    or connection.execute('SELECT 1 FROM tracked_content_retry_files WHERE request_id=?',(parent['request_id'],)).fetchone()
                    or connection.execute('SELECT 1 FROM artifacts WHERE job_id=?',(old['job_id'],)).fetchone()):
                    raise RetryIntegrity('Content retry undispatched history closure proof changed')
            else:
                _verify_known_attempt(connection, old)
            if (call is None or dispatch is None or call['status'] != 'FAILED_FINAL'
                or call['last_error_code'] not in ({'LOCAL_RESOURCE'} if captured_failure else {'CAPABILITY_UNAVAILABLE'} if history_closed else KNOWN_RETRYABLE) or dispatch[0] != 'FAILED_KNOWN'
                or not SQLiteStateRepository._provider_request_matches(call,provider_request(parent)) or call['attempt_count']!=1
                or call['reservation_owner'] is not None or call['lease_until'] is not None):
                raise RetryIntegrity('Content retry parent provider failure is not known and eligible')
            old = connection.execute('SELECT * FROM jobs WHERE job_id=?', (parent['expected_old_job_id'],)).fetchone()
            continue
        terminal = json.loads(execution['events_json'])[-1]
        cancelled = execution['state'] == 'CANCELLED'
        if (parent['source_id'] != source_id or parent['video_id'] != old['video_id']
            or parent['pipeline_version'] != old['pipeline_version']
            or execution['state'] not in {'CANCELLED', 'FAILED'}
            or execution['error_code'] not in ({'CANCELLED_BEFORE_DISPATCH'} if cancelled else {'SOURCE_PAUSED','SOURCE_CONTEXT_CHANGED','RETRY_CONTRACT_UNAVAILABLE'})
            or execution['provider_call_hash'] is not None or execution['local_attempt_count'] != 0
            or execution['lease_owner'] is not None or execution['lease_until'] is not None
            or execution['finished_at'] != terminal['at'] or execution['updated_at'] != terminal['at']
            or execution['fencing_epoch'] != (1 if cancelled else 0)
            or len(json.loads(execution['events_json'])) != 2
            or terminal['prior_state'] != 'QUEUED' or terminal['event'] != ('CANCELLED' if cancelled else 'FAILED')
            or (cancelled and terminal['action'] is None)
            or (not cancelled and terminal['action'] is not None)
            or old['status'] != 'FAILED_FINAL' or old['last_error_code'] != 'CAPABILITY_UNAVAILABLE'
            or old['last_error_message'] != execution['error_code']
            or old['lease_owner'] is not None or old['lease_until'] is not None
            or old['finished_at'] != execution['finished_at'] or old['updated_at'] != execution['finished_at']
            or connection.execute('SELECT 1 FROM job_attempts WHERE job_id=?', (old['job_id'],)).fetchone()
            or connection.execute('SELECT 1 FROM artifacts WHERE job_id=?', (old['job_id'],)).fetchone()
            or connection.execute('SELECT 1 FROM tracked_content_retry_files WHERE request_id=?', (parent['request_id'],)).fetchone()
            or connection.execute('SELECT 1 FROM provider_calls WHERE request_hash=? UNION ALL SELECT 1 FROM provider_dispatch_states WHERE request_hash=?', (parent['provider_request_hash'], parent['provider_request_hash'])).fetchone()):
            raise RetryIntegrity('Content retry zero-dispatch parent proof changed')
        old = connection.execute('SELECT * FROM jobs WHERE job_id=?', (parent['expected_old_job_id'],)).fetchone()


def _verify_known_attempt(connection: sqlite3.Connection, old: sqlite3.Row) -> None:
    attempt = connection.execute('SELECT * FROM job_attempts WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1', (old['job_id'],)).fetchone()
    if (old['last_error_code'] not in KNOWN_RETRYABLE or old['attempt_count'] < 1
        or attempt is None or attempt['attempt_number'] != old['attempt_count']
        or attempt['outcome'] != 'FAILED_FINAL' or attempt['error_code'] != old['last_error_code']
        or attempt['finished_at'] is None):
        raise RetryIntegrity('Content retry original terminal attempt changed')


def public(request: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    return {"request_id": request["request_id"], "video_id": request["video_id"], "source_id": request["source_id"],
        "expected_job_id": request["expected_old_job_id"], "target_job_id": request["target_job_id"],
        "state": execution["state"], "revision": execution["revision"], "error_code": execution["error_code"],
        "can_resume_local": execution["state"] == "ATTENTION" and execution["local_attempt_count"] < 3 and len(json.loads(execution['events_json'])) + local_event_reserve(execution['local_attempt_count']) - 1 <= HISTORY_LIMIT,
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
    with closing(repository._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        history = connection.execute("SELECT request_id FROM tracked_content_retry_requests WHERE video_id=? AND operation=? AND command_id=? LIMIT 2", (video_id, OPERATION, command_id)).fetchall()
        if history:
            if len(history) != 1:
                raise RetryIntegrity("Content retry command has ambiguous history")
            request, execution = read(connection, history[0][0], data_root=repository._source_data_root)
            if request["client_input_json"] != canonical(client):
                raise RetryConflict("Content retry command input conflicts")
            return public(request, execution)
        source = validate_source(connection, repository, video_id)
        source_id = source["source_id"]
        if connection.execute("SELECT 1 FROM source_runs WHERE source_id=? AND state IN ('QUEUED','RUNNING','WAITING','PARTIAL','NEEDS_ATTENTION') UNION ALL SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING' UNION ALL SELECT 1 FROM tracked_content_retry_executions WHERE source_id=? AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION') LIMIT 1", (source_id, source_id, source_id)).fetchone():
            raise RetryConflict("Content retry cannot overlap Source work")
        video = connection.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
        old = connection.execute("SELECT * FROM jobs WHERE job_id=?", (expected_job_id,)).fetchone()
        latest = connection.execute("SELECT job_id FROM jobs j WHERE video_id=? AND job_type='VIDEO_STAGE' AND NOT EXISTS(SELECT 1 FROM tracked_content_retry_requests r WHERE r.expected_old_job_id=j.job_id) ORDER BY created_at DESC,job_id DESC LIMIT 1", (video_id,)).fetchone()
        if (video is None or video["pipeline_status"] != "METADATA_READY" or old is None or latest is None or latest[0] != expected_job_id
            or old["video_id"] != video_id or old["target_stage"] != "TRANSCRIPT" or old["job_type"] != "VIDEO_STAGE" or old["status"] != "FAILED_FINAL"
            or old["pipeline_version"] != video["pipeline_version"]
            or old["lease_owner"] is not None or old["lease_until"] is not None or old["finished_at"] is None):
            raise RetryConflict("Content retry needs the current known terminal transcript failure")
        verify_old_failure(connection, old, source_id=source_id, data_root=repository._source_data_root)
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
        request, execution = read(connection, request_id, data_root=repository._source_data_root)
        connection.commit()
        return public(request, execution)


TRANSITIONS = {
    "QUEUED": {"ACQUIRING", "FAILED", "CANCELLED"},
    "ACQUIRING": {"ACQUIRING", "FINALIZING", "FAILED", "AMBIGUOUS"},
    "FINALIZING": {"FINALIZING", "SUCCEEDED", "ATTENTION", "FAILED"},
    "ATTENTION": {"FINALIZING", "FAILED"},
}
EVENT_STATES = {
    "ADMITTED": {"QUEUED"}, "CLAIMED": {"ACQUIRING"},
    "RECOVERED": {"ACQUIRING", "FINALIZING"}, "LOCAL_ATTENTION": {"ATTENTION"},
    "LOCAL_RESUMED": {"FINALIZING"}, "COMPLETED": {"SUCCEEDED"},
    "LOCAL_ATTEMPT_STARTED": {"FINALIZING"},
    "LOCAL_INLINE_ATTENTION": {"ATTENTION"}, "LOCAL_INLINE_COMPLETED": {"SUCCEEDED"},
    "FAILED": {"FAILED"}, "CANCELLED": {"CANCELLED"}, "AMBIGUOUS": {"AMBIGUOUS"},
    'DISPATCH_INTENT': {'ACQUIRING'}, 'HISTORY_LIMIT_CLOSED': {'FAILED','AMBIGUOUS'},
}
ERRORS = {"SOURCE_PAUSED", "SOURCE_CONTEXT_CHANGED", "RETRY_CONTRACT_UNAVAILABLE", "NATIVE_TIMING_UNAVAILABLE",
    "CAPTIONS_UNAVAILABLE", "KNOWN_PROVIDER_FAILURE", "LOCAL_FINALIZATION_FAILED", "LOCAL_FINALIZATION_LIMIT",
    "LOCAL_FINALIZATION_CLOSED", "CANCELLED_BEFORE_DISPATCH", "DISPATCH_OUTCOME_UNKNOWN"}


def _verify_events(request: dict[str, Any], execution: dict[str, Any], events: list[Any]) -> None:
    prior = None
    revision, epoch = -1, 0
    local_attempts, attempt_open, attention_without_attempt = 0, False, False
    actions: set[tuple[str, str]] = set()
    previous_at = request['created_at']
    for index, item in enumerate(events):
        fields = {"event", "prior_state", "state", "revision", "fencing_epoch", "at", "action"}
        if (not isinstance(item, dict) or set(item) not in (fields, fields | {'local_attempt'})
            or item['event'] not in EVENT_STATES or item['state'] not in EVENT_STATES[item['event']]
            or item['prior_state'] != prior or type(item['revision']) is not int or item['revision'] <= revision
            or type(item['fencing_epoch']) is not int or not epoch <= item['fencing_epoch'] <= epoch + 1
            or not isinstance(item['at'], str) or len(item['at']) != 27 or not item['at'].endswith('Z')
            or item['at'] < previous_at):
            raise RetryIntegrity('Content retry history is inconsistent')
        if index == 0:
            if item['event'] != 'ADMITTED' or item['state'] != 'QUEUED' or item['revision'] != 0 or item['fencing_epoch'] != 0 or item['at'] != request['created_at']:
                raise RetryIntegrity('Content retry admission event changed')
        elif item['state'] not in TRANSITIONS.get(prior or '', set()) or item['event'] == 'ADMITTED':
            raise RetryIntegrity('Content retry event transition is invalid')
        if item['event'] == 'DISPATCH_INTENT' and (prior != 'ACQUIRING' or item['action'] is not None
            or any(old['event']=='DISPATCH_INTENT' for old in events[:index])):
            raise RetryIntegrity('Content retry dispatch marker changed')
        takes_ownership = item['event'] in {'CLAIMED','LOCAL_RESUMED','CANCELLED'} or (
            isinstance(item['action'], dict) and item['action'].get('operation') == 'CLOSE_LOCAL')
        if (takes_ownership and item['fencing_epoch'] != epoch + 1
            or not takes_ownership and item['event'] != 'RECOVERED' and item['fencing_epoch'] != epoch):
            raise RetryIntegrity('Content retry event ownership changed')
        # Legacy ordinary starts are unambiguous: same-owner FINALIZING ->
        # FINALIZING RECOVERED. Inline results previously had no such proof and
        # cannot be recovered from a projection counter. New event names make
        # missing witnesses distinguishable from that legacy start contract.
        start = item['event'] == 'LOCAL_ATTEMPT_STARTED' or (
            item['event'] == 'RECOVERED' and prior == item['state'] == 'FINALIZING' and item['fencing_epoch'] == epoch)
        inline = item['event'] in {'LOCAL_INLINE_ATTENTION','LOCAL_INLINE_COMPLETED'}
        witness = item.get('local_attempt')
        if 'local_attempt' in item or item['event'] == 'LOCAL_ATTEMPT_STARTED' or inline:
            if (not isinstance(witness, dict) or set(witness) != {'phase','before','after'}
                or type(witness['phase']) is not str
                or type(witness['before']) is not int or type(witness['after']) is not int
                or witness['before'] != local_attempts or witness['after'] != local_attempts + 1
                or witness['phase'] != ('START' if start else 'INLINE_RESULT')
                or prior != 'FINALIZING' or item['fencing_epoch'] != epoch or item['action'] is not None
                or not (start or inline)
                or inline and index + local_event_reserve(local_attempts) <= HISTORY_LIMIT):
                raise RetryIntegrity('Content retry local attempt witness changed')
        if item['event'] in {'COMPLETED','LOCAL_ATTENTION'} and index + local_event_reserve(local_attempts) > HISTORY_LIMIT:
            raise RetryIntegrity('Content retry legacy inline result has no local attempt witness')
        attention_without_attempt = False
        if start or inline:
            local_attempts += 1
            if local_attempts > 3:
                raise RetryIntegrity('Content retry local attempt limit changed')
            attempt_open = start
        elif item['event'] == 'COMPLETED':
            if not attempt_open:
                raise RetryIntegrity('Content retry completion has no real local attempt')
            attempt_open = False
        elif item['event'] == 'LOCAL_ATTENTION':
            attention_without_attempt = not attempt_open
            attempt_open = False
        elif item['event'] == 'RECOVERED' and item['fencing_epoch'] != epoch:
            # Ownership recovery is not another attempt. A previously started
            # interrupted attempt stays counted, but cannot supply a new result.
            attempt_open = False
        action = item['action']
        if action is not None:
            if not isinstance(action, dict) or set(action) != {'operation','command_id','expected_revision','input_json','input_sha256','applied_revision'}:
                raise RetryIntegrity('Content retry action contract changed')
            key = (action['operation'], action['command_id'])
            if key in actions or not isinstance(action['command_id'], str) or not action['command_id'].strip():
                raise RetryIntegrity('Content retry action command is ambiguous')
            actions.add(key)
            if index == 0:
                expected = json.loads(request['client_input_json'])
                if action['operation'] != OPERATION or action['command_id'] != request['command_id'] or action['expected_revision'] is not None:
                    raise RetryIntegrity('Content retry admission receipt changed')
            elif action['operation'] == 'CLOSE_HISTORY_LIMIT':
                expected = json.loads(action['input_json'])
                if not isinstance(expected, dict):
                    raise RetryIntegrity('Content retry history closure input changed')
                fields={'request_id','operation','command_id','expected_revision','prior_state','prior_epoch','dispatch_status','target_status','attempt_count','provider_attempt_count','local_attempt_count','had_dispatch_intent'}
                without_command={key:value for key,value in expected.items() if key!='command_id'}
                if (set(expected)!=fields or expected['request_id']!=request['request_id']
                    or expected['operation']!='CLOSE_HISTORY_LIMIT' or expected['command_id']!=action['command_id']
                    or action['command_id']!='history-limit:'+digest(without_command)
                    or type(action['expected_revision']) is not int or action['expected_revision']!=item['revision']-1
                    or type(expected['expected_revision']) is not int or expected['expected_revision']!=action['expected_revision'] or expected['prior_state']!=prior
                    or type(expected['prior_epoch']) is not int or expected['prior_epoch']!=epoch
                    or expected['dispatch_status'] not in {'NOT_DISPATCHED','DISPATCH_INTENT_DURABLE','DISPATCHED_RESULT_UNKNOWN','SUCCESS_DURABLY_RECORDED','FAILED_KNOWN','AMBIGUOUS'}
                    or expected['target_status'] not in {'RUNNING','FAILED_FINAL','SUCCEEDED'}
                    or any(type(expected[key]) is not int for key in ('attempt_count','provider_attempt_count','local_attempt_count'))
                    or expected['attempt_count']!=1 or expected['provider_attempt_count']!=1
                    or expected['local_attempt_count'] != local_attempts
                    or type(expected['had_dispatch_intent']) is not bool
                    or expected['had_dispatch_intent']!=any(old['event']=='DISPATCH_INTENT' for old in events[:index])
                    or expected['had_dispatch_intent']!=(expected['dispatch_status']!='NOT_DISPATCHED')
                    or item['event']!='HISTORY_LIMIT_CLOSED' or index+ACQUISITION_EVENT_RESERVE<=HISTORY_LIMIT):
                    raise RetryIntegrity('Content retry history closure receipt changed')
                expected_state='FAILED' if expected['dispatch_status'] in {'NOT_DISPATCHED','FAILED_KNOWN','SUCCESS_DURABLY_RECORDED'} else 'AMBIGUOUS'
                if item['state']!=expected_state:
                    raise RetryIntegrity('Content retry history closure outcome changed')
            else:
                if action['operation'] not in {'RESUME_LOCAL','CLOSE_LOCAL','CANCEL_BEFORE_DISPATCH'} or type(action['expected_revision']) is not int or action['expected_revision'] != item['revision']-1:
                    raise RetryIntegrity('Content retry local action revision changed')
                expected = dict(request_id=request['request_id'],operation=action['operation'],command_id=action['command_id'],expected_revision=action['expected_revision'])
                allowed = {'RESUME_LOCAL': ('ATTENTION','FINALIZING','LOCAL_RESUMED'), 'CLOSE_LOCAL': ('ATTENTION','FAILED','FAILED'), 'CANCEL_BEFORE_DISPATCH': ('QUEUED','CANCELLED','CANCELLED')}
                if (prior,item['state'],item['event']) != allowed[action['operation']]:
                    raise RetryIntegrity('Content retry local action state changed')
            if action['input_json'] != canonical(expected) or action['input_sha256'] != digest(expected) or type(action['applied_revision']) is not int or action['applied_revision'] != item['revision']:
                raise RetryIntegrity('Content retry action input changed')
        elif index == 0 or item['event'] in {'LOCAL_RESUMED','CANCELLED','HISTORY_LIMIT_CLOSED'}:
            raise RetryIntegrity('Content retry command receipt missing')
        prior, revision, epoch, previous_at = item['state'], item['revision'], item['fencing_epoch'], item['at']
    if (prior != execution['state'] or revision > execution['revision'] or epoch != execution['fencing_epoch']
        or execution['updated_at'] < previous_at or len(events)>128
        or type(execution['local_attempt_count']) is not int or execution['local_attempt_count'] != local_attempts
        or attention_without_attempt and execution['error_code'] != 'RETRY_CONTRACT_UNAVAILABLE'
        or (execution['error_code'] is not None and execution['error_code'] not in ERRORS)):
        raise RetryIntegrity('Content retry projection is inconsistent')


def read(connection: sqlite3.Connection, request_id: str, *, data_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        return _read(connection,request_id,data_root=data_root)
    except RetryIntegrity:
        raise
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        raise RetryIntegrity('Content retry typed persistence is invalid') from error
