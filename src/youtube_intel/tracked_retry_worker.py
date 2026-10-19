"""One locked logical acquisition followed by bounded, strictly local finalization."""

from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from youtube_intel.domain import AppError, ErrorCode, VideoMetadata
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.state import SQLiteStateRepository, format_utc_datetime
from youtube_intel.tracked_retry_context import (
    NativeTimingUnavailable,
    RetryConflict,
    RetryIntegrity,
    authority,
    request_lock,
    store_lock,
)
from youtube_intel.tracked_retry_files import RetryFiles
from youtube_intel.tracked_retry_store import (
    ACQUISITION_EVENT_RESERVE,
    CONTRACT,
    HISTORY_LIMIT,
    TERMINAL,
    canonical,
    digest,
    event,
    local_event_reserve,
    provider_request,
    public,
    read,
    validate_source,
)
from youtube_intel.transcripts import (
    FORMAT_POLICY_VERSION,
    NORMALIZATION_VERSION,
    QUALITY_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    InvalidSubtitleCandidate,
    SubtitleAcquisitionService,
    SubtitleAdapter,
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    TranscriptError,
    TranscriptJobContext,
)

if TYPE_CHECKING:
    from youtube_intel.tracked_content_retry import TrackedContentRetryService


class UnknownOutcome(BaseException):
    """Do not let the legacy service turn an uncertain transport into known failure."""


class HistoryLimitReached(BaseException):
    """Stop before transport while a terminal receipt still fits."""


class CheckedAdapter:
    """Synchronous adapter boundary; the caller holds both locks until return.

    The production yt-dlp adapter disables downloads, cache and all output files;
    body reads close their response in finally. No callback receives repository,
    DATA path or write authority. Unexpected exceptions remain unknown.
    """

    def __init__(self, adapter: SubtitleAdapter, preflight: Callable[[], None], known_receipt: Callable[[AppError], None]) -> None:
        self.adapter, self.preflight = adapter, preflight
        self.known_receipt = known_receipt
        self.provider_name, self.provider_version = (
            adapter.provider_name,
            adapter.provider_version,
        )
        self.known_failure = False
        self.known_error: str | None = None

    def _call(self, operation: Callable[[], Any]) -> Any:
        self.preflight()
        try:
            return operation()
        except TranscriptError as error:
            if error.error.code in {
                ErrorCode.INVALID_RESPONSE,
                ErrorCode.CONTENT_UNAVAILABLE,
                ErrorCode.CONFIG_INVALID,
                ErrorCode.PERMISSION_DENIED,
                ErrorCode.RATE_LIMITED,
                ErrorCode.CAPABILITY_UNAVAILABLE,
                ErrorCode.TRUST_INTEGRITY_INVALID,
            }:
                self.known_receipt(error.error)
                self.known_failure = True
                self.known_error = error.error.code.value
                raise
            raise UnknownOutcome() from None
        except InvalidSubtitleCandidate:
            raise
        except Exception:
            raise UnknownOutcome() from None

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        result: SubtitleTrackListing = self._call(
            lambda: self.adapter.enumerate_tracks(video_id)
        )
        return result

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        result: SubtitleReadResult = self._call(lambda: self.adapter.read_track(track))
        return result


class UnavailableAdapter:
    def __init__(self, parameters: dict[str, Any]) -> None:
        self.provider_name=parameters['adapter_name']
        self.provider_version=parameters['adapter_version']

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        raise RetryConflict('Frozen caption adapter is unavailable')

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        raise RetryConflict('Frozen caption adapter is unavailable')


def transition(
    connection: sqlite3.Connection,
    execution: dict[str, Any],
    state: str,
    *,
    at: str,
    name: str,
    action: dict[str, Any] | None = None,
    local_attempt: dict[str, Any] | None = None,
    **changes: Any,
) -> dict[str, Any]:
    revision = execution["revision"] + 1
    values = dict(state=state, revision=revision, updated_at=at, **changes)
    if state not in ("ACQUIRING", "FINALIZING"):
        values.update(lease_owner=None, lease_until=None)
    values.setdefault("error_code", None)
    if state in TERMINAL:
        values["finished_at"] = at
    history = json.loads(execution["events_json"])
    history.append(
        event(
            state,
            prior=execution["state"],
            revision=revision,
            epoch=values.get("fencing_epoch", execution["fencing_epoch"]),
            at=at,
            name=name,
            action=action,
            local_attempt=local_attempt,
        )
    )
    values["events_json"] = canonical(history)
    changed = connection.execute(
        "UPDATE tracked_content_retry_executions SET "
        + ",".join(f"{key}=?" for key in values)
        + " WHERE request_id=? AND revision=? AND fencing_epoch=?",
        (
            *values.values(),
            execution["request_id"],
            execution["revision"],
            execution["fencing_epoch"],
        ),
    ).rowcount
    if changed != 1:
        raise RetryConflict("Content retry ownership changed")
    return {**execution, **values}


class RetryWorker:
    def __init__(self, service: TrackedContentRetryService) -> None:
        self.service = service
        self.repository: SQLiteStateRepository = service.repository
        self.owner = "tracked-retry-" + secrets.token_hex(16)
        self.epoch = -1
        self.request: dict[str, Any] = {}

    def timestamp(self) -> str:
        return format_utc_datetime(self.service.now())

    def check(self) -> None:
        with (
            closing(self.repository._connect(read_only=True)) as connection,
            connection,
        ):
            _, execution = read(connection, self.request["request_id"], data_root=self.service.data_root)
            checked_at = self.timestamp()
            if (
                execution["fencing_epoch"] != self.epoch
                or execution["lease_owner"] != self.owner
                or execution["state"] not in ("ACQUIRING", "FINALIZING")
                or execution["lease_until"] <= checked_at
                or execution["updated_at"] > checked_at
            ):
                raise RetryConflict("Content retry writer is fenced or expired")

    def _preflight(self) -> None:
        self.check()
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            validate_source(
                connection,
                self.repository,
                self.request["video_id"],
                source_id=self.request["source_id"],
            )
            row = connection.execute(
                "SELECT status FROM provider_dispatch_states WHERE request_hash=?",
                (self.request["provider_request_hash"],),
            ).fetchone()
            if row is None or row[0] not in (
                "NOT_DISPATCHED",
                "DISPATCH_INTENT_DURABLE",
            ):
                raise RetryIntegrity(
                    "Content retry cannot repeat an uncertain dispatch"
                )
            _, execution = read(connection, self.request['request_id'], data_root=self.service.data_root)
            if len(json.loads(execution['events_json'])) + ACQUISITION_EVENT_RESERVE > HISTORY_LIMIT:
                raise HistoryLimitReached()
            if row[0] == 'NOT_DISPATCHED':
                transition(connection,execution,'ACQUIRING',at=self.timestamp(),name='DISPATCH_INTENT')
            connection.execute(
                "UPDATE provider_dispatch_states SET status='DISPATCH_INTENT_DURABLE',updated_at=? WHERE request_hash=? AND status='NOT_DISPATCHED'",
                (self.timestamp(), self.request["provider_request_hash"]),
            )

    def _record_known_failure(self, error: AppError) -> None:
        self.check()
        self.repository.fail_provider_call(self.request['provider_request_hash'],owner=self.owner,
            retryable=False,available_at=self.service.now(),error_code=error.code,
            error_message=error.message,now=self.service.now())

    def _finish_failure(
        self, files: RetryFiles, state: str, code: str, *, underlying_code: str | None = None
    ) -> dict[str, Any]:
        files.settle()
        self.check()
        at = self.timestamp()
        underlying_code=underlying_code or ({'AMBIGUOUS':'PROVIDER_UNAVAILABLE'}.get(state) or {
            'NATIVE_TIMING_UNAVAILABLE':'CONTENT_UNAVAILABLE','CAPTIONS_UNAVAILABLE':'CONTENT_UNAVAILABLE',
            'LOCAL_FINALIZATION_FAILED':'LOCAL_RESOURCE','RETRY_CONTRACT_UNAVAILABLE':'CAPABILITY_UNAVAILABLE',
        }.get(code,'INVALID_RESPONSE'))
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            request, execution = read(connection, self.request["request_id"], data_root=self.service.data_root)
            call = connection.execute(
                "SELECT * FROM provider_calls WHERE request_hash=?",
                (request["provider_request_hash"],),
            ).fetchone()
            if call is not None and call['status'] in {'FAILED_FINAL','FAILED_RETRYABLE'} and state!='AMBIGUOUS':
                if call['status']=='FAILED_RETRYABLE':
                    connection.execute("UPDATE provider_calls SET status='FAILED_FINAL',reservation_owner=NULL,lease_until=NULL,finished_at=?,updated_at=? WHERE request_hash=?",(at,at,request['provider_request_hash']))
                connection.execute("UPDATE provider_dispatch_states SET status='FAILED_KNOWN',updated_at=? WHERE request_hash=? AND status!='FAILED_KNOWN'",(at,request['provider_request_hash']))
            elif call is not None and call["status"] != "SUCCEEDED":
                dispatch = "AMBIGUOUS" if state == "AMBIGUOUS" else "FAILED_KNOWN"
                connection.execute(
                    "UPDATE provider_dispatch_states SET status=?,updated_at=? WHERE request_hash=?",
                    (dispatch, at, request["provider_request_hash"]),
                )
                connection.execute(
                    "UPDATE provider_calls SET status='FAILED_FINAL',reservation_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code=?,last_error_message=? WHERE request_hash=?",
                    (
                        at,
                        at,
                        underlying_code,
                        code,
                        request["provider_request_hash"],
                    ),
                )
            target = connection.execute(
                "SELECT status FROM jobs WHERE job_id=?", (request["target_job_id"],)
            ).fetchone()
            if target[0] != "SUCCEEDED":
                job_error = (
                    "PROVIDER_UNAVAILABLE"
                    if state == "AMBIGUOUS"
                    else "INVALID_RESPONSE"
                )
                connection.execute(
                    "UPDATE job_attempts SET finished_at=?,outcome='FAILED_FINAL',error_code=?,error_message=? WHERE job_id=? AND finished_at IS NULL",
                    (at, job_error, code, request["target_job_id"]),
                )
                connection.execute(
                    "UPDATE jobs SET status='FAILED_FINAL',lease_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code=?,last_error_message=? WHERE job_id=?",
                    (at, at, job_error, code, request["target_job_id"]),
                )
            execution = transition(
                connection,
                execution,
                state,
                at=at,
                name="AMBIGUOUS" if state == "AMBIGUOUS" else "FAILED",
                error_code=code,
            )
            return public(request, execution)

    def run(self, request_id: str) -> dict[str, Any]:
        with (
            store_lock(self.repository._database_path),
            request_lock(self.repository._database_path, request_id),
        ):
            with closing(self.repository._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                request, execution = read(connection, request_id, data_root=self.service.data_root)
                self.request = request
                if execution["state"] in TERMINAL:
                    from youtube_intel.tracked_retry_reader import verify_request

                    request, execution, _files = verify_request(self.repository,self.service.data_root,request_id,settled=True)
                    return public(request, execution)
                substrate=connection.execute('SELECT status FROM jobs WHERE job_id=?',(request['target_job_id'],)).fetchone()
                reserve=local_event_reserve(execution['local_attempt_count']) if substrate[0]=='SUCCEEDED' else ACQUISITION_EVENT_RESERVE
                if len(json.loads(execution['events_json'])) + reserve > HISTORY_LIMIT:
                    connection.commit()
                    return self._close_history_limit(request, execution)
                # One actual instant owns this atomic claim/reservation. A later
                # reserve clock followed by the earlier claim timestamp would
                # move provider.updated_at behind its own started_at.
                claimed_at = self.service.now()
                at = format_utc_datetime(claimed_at)
                until = format_utc_datetime(claimed_at + timedelta(minutes=5))
                parameters = json.loads(request["parameters_json"])
                contract_available=True
                adapter: SubtitleAdapter
                try:
                    adapter = self.service.adapter_factory()
                    if (
                        parameters["adapter_name"] != adapter.provider_name
                        or parameters["adapter_version"] != adapter.provider_version
                        or parameters["selection_policy_version"]
                        != SELECTION_POLICY_VERSION
                        or parameters["format_policy_version"] != FORMAT_POLICY_VERSION
                        or parameters["normalization_version"] != NORMALIZATION_VERSION
                        or parameters["quality_policy_version"]
                        != QUALITY_POLICY_VERSION
                        or parameters["native_timing_policy_version"]
                        != "tracked-native-timed-v1"
                        or parameters["local_finalize_max_attempts"] != 3
                    ):
                        raise RetryConflict(
                            "Content retry frozen contract is unavailable"
                        )
                except Exception:
                    if execution["state"] == "QUEUED":
                        connection.execute(
                            "UPDATE jobs SET status='FAILED_FINAL',last_error_code='CAPABILITY_UNAVAILABLE',last_error_message='RETRY_CONTRACT_UNAVAILABLE',finished_at=?,updated_at=? WHERE job_id=?",
                            (at, at, request["target_job_id"]),
                        )
                        execution = transition(
                            connection,
                            execution,
                            "FAILED",
                            at=at,
                            name="FAILED",
                            error_code="RETRY_CONTRACT_UNAVAILABLE",
                        )
                        return public(request, execution)
                    contract_available=False
                    adapter=UnavailableAdapter(parameters)
                if execution["state"] == "QUEUED":
                    try:
                        validate_source(
                            connection,
                            self.repository,
                            request["video_id"],
                            source_id=request["source_id"],
                        )
                    except RetryConflict:
                        source = connection.execute(
                            "SELECT enabled FROM source_subscriptions WHERE source_id=?",
                            (request["source_id"],),
                        ).fetchone()
                        code = (
                            "SOURCE_PAUSED"
                            if source is not None and source[0] == 0
                            else "SOURCE_CONTEXT_CHANGED"
                        )
                        connection.execute(
                            "UPDATE jobs SET status='FAILED_FINAL',last_error_code='CAPABILITY_UNAVAILABLE',last_error_message=?,finished_at=?,updated_at=? WHERE job_id=?",
                            (code, at, at, request["target_job_id"]),
                        )
                        execution = transition(
                            connection,
                            execution,
                            "FAILED",
                            at=at,
                            name="FAILED",
                            error_code=code,
                        )
                        return public(request, execution)
                    connection.execute(
                        "UPDATE jobs SET status='RUNNING',attempt_count=1,lease_owner=?,lease_until=?,updated_at=? WHERE job_id=? AND status='PENDING'",
                        (self.owner, until, at, request["target_job_id"]),
                    )
                    connection.execute(
                        "INSERT INTO job_attempts(job_id,attempt_number,lease_owner,started_at,lease_until) VALUES(?,1,?,?,?)",
                        (request["target_job_id"], self.owner, at, until),
                    )
                    self.repository._reserve_provider_call_in_transaction(
                        connection,
                        provider_request(request),
                        owner=self.owner,
                        lease_until=claimed_at + timedelta(minutes=5),
                        available_at=claimed_at,
                        now=claimed_at,
                    )
                    connection.execute(
                        "INSERT INTO provider_dispatch_states(request_hash,status,updated_at) VALUES(?,'NOT_DISPATCHED',?)",
                        (request["provider_request_hash"], at),
                    )
                target = connection.execute(
                    "SELECT status FROM jobs WHERE job_id=?",
                    (request["target_job_id"],),
                ).fetchone()
                state = (
                    "FINALIZING"
                    if target[0] == "SUCCEEDED"
                    or execution["state"] in ("FINALIZING", "ATTENTION")
                    else "ACQUIRING"
                )
                self.epoch = execution["fencing_epoch"] + 1
                if state == "ACQUIRING":
                    pending = connection.execute(
                        "SELECT started_at,updated_at,available_at FROM provider_calls WHERE request_hash=? AND status='PENDING'",
                        (request['provider_request_hash'],),
                    ).fetchone()
                    if pending is not None and (
                        not pending['started_at'] <= pending['updated_at'] <= at or pending['available_at'] > at
                    ):
                        raise RetryIntegrity('Content retry provider reservation time is inconsistent')
                    connection.execute(
                        "UPDATE jobs SET lease_owner=?,lease_until=?,updated_at=? WHERE job_id=? AND status='RUNNING'",
                        (self.owner, until, at, request["target_job_id"]),
                    )
                    connection.execute(
                        "UPDATE job_attempts SET lease_owner=?,lease_until=? WHERE job_id=? AND finished_at IS NULL",
                        (self.owner, until, request["target_job_id"]),
                    )
                    connection.execute(
                        "UPDATE provider_calls SET reservation_owner=?,lease_until=?,updated_at=? WHERE request_hash=? AND status='PENDING'",
                        (self.owner, until, at, request["provider_request_hash"]),
                    )
                execution = transition(
                    connection,
                    execution,
                    state,
                    at=at,
                    name="CLAIMED" if execution["state"] == "QUEUED" else "RECOVERED",
                    fencing_epoch=self.epoch,
                    lease_owner=self.owner,
                    lease_until=until,
                    provider_call_hash=request["provider_request_hash"],
                )
            files = RetryFiles(
                self.repository,
                self.service.data_root,
                request,
                epoch=self.epoch,
                check=self.check,
                timestamp=self.timestamp,
            )
            guarded = CheckedAdapter(adapter, self._preflight, self._record_known_failure)
            service = SubtitleAcquisitionService(
                adapter=guarded,
                repository=self.repository,
                data_root=self.service.data_root,
                context=TranscriptJobContext(
                    job_id=request["target_job_id"],
                    owner=self.owner,
                    pipeline_version=request["pipeline_version"],
                    refresh_generation=request["refresh_generation"],
                ),
                clock=self.service.now,
            )
            with authority(
                request["target_job_id"],
                request["provider_request_hash"],
                self.check,
                files.write,
            ):
                files.settle(terminal=state!='FINALIZING')
                if state == "ACQUIRING":
                    dispatch = self.repository.get_provider_dispatch(
                        request["provider_request_hash"]
                    )
                    if dispatch is None:
                        raise RetryIntegrity("Content retry dispatch disappeared")
                    if dispatch.status.value == 'FAILED_KNOWN':
                        call=self.repository.get_provider_call(request['provider_request_hash'])
                        if call is None or call.status.value not in {'FAILED_RETRYABLE','FAILED_FINAL'} or call.last_error_code is None:
                            raise RetryIntegrity('Content retry known failure lost its provider receipt')
                        return self._finish_failure(files,'FAILED','KNOWN_PROVIDER_FAILURE',underlying_code=call.last_error_code)
                    if dispatch.status.value != "NOT_DISPATCHED":
                        return self._finish_failure(
                            files, "AMBIGUOUS", "DISPATCH_OUTCOME_UNKNOWN"
                        )
                    if not contract_available:
                        return self._finish_failure(files,'FAILED','RETRY_CONTRACT_UNAVAILABLE')
                    try:
                        result = service._fetch_reserved(
                            video_id=request["video_id"],
                            language_preferences=parameters["language_preferences"],
                            raw_request_hash=request["raw_request_hash"],
                            provider_request=provider_request(request),
                            now=self.service.now(),
                        )
                        from youtube_intel.domain import TranscriptReady

                        if not isinstance(result, TranscriptReady):
                            return self._finish_failure(
                                files, "FAILED", "CAPTIONS_UNAVAILABLE"
                            )
                    except HistoryLimitReached:
                        with closing(self.repository._connect(read_only=True)) as connection:
                            _, execution=read(connection,request_id, data_root=self.service.data_root)
                        return self._close_history_limit(request,execution)
                    except UnknownOutcome:
                        return self._finish_failure(
                            files, "AMBIGUOUS", "DISPATCH_OUTCOME_UNKNOWN"
                        )
                    except NativeTimingUnavailable:
                        return self._finish_failure(
                            files, "FAILED", "NATIVE_TIMING_UNAVAILABLE"
                        )
                    except Exception:
                        target = self.repository.get_job(request["target_job_id"])
                        if target is None or target.status.value != "SUCCEEDED":
                            if guarded.known_failure:
                                return self._finish_failure(files,'FAILED','KNOWN_PROVIDER_FAILURE',underlying_code=guarded.known_error)
                            from youtube_intel.tracked_retry_reader import (
                                verify_request,
                            )
                            _request,_execution,accepted_files=verify_request(self.repository,self.service.data_root,request_id)
                            if any(row['role']=='CAPTURE' and row['state']=='VERIFIED' for row in accepted_files):
                                return self._finish_failure(files,'FAILED','LOCAL_FINALIZATION_FAILED')
                            return self._finish_failure(files,'AMBIGUOUS','DISPATCH_OUTCOME_UNKNOWN')
                    with closing(self.repository._connect()) as connection, connection:
                        connection.execute("BEGIN IMMEDIATE")
                        _, execution = read(connection, request_id, data_root=self.service.data_root)
                        transition(
                            connection,
                            execution,
                            "FINALIZING",
                            at=self.timestamp(),
                            name="RECOVERED",
                        )
                if not contract_available:
                    with closing(self.repository._connect()) as connection, connection:
                        connection.execute('BEGIN IMMEDIATE')
                        _, execution=read(connection,request_id, data_root=self.service.data_root)
                        execution=transition(connection,execution,'ATTENTION',at=self.timestamp(),name='LOCAL_ATTENTION',error_code='RETRY_CONTRACT_UNAVAILABLE')
                        return public(request,execution)
                return self._finalize(service, files, parameters)

    def _close_history_limit(self, request: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
        """Reserve a terminal receipt instead of consuming the last slots on claim.

        Both OS locks are already held: prior synchronous writers have exited.
        This closure grants no transport or artifact-production authority and
        never treats an expired lease as proof that dispatch did not happen.
        """
        with closing(self.repository._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            _,current=read(connection,request['request_id'], data_root=self.service.data_root)
            substrate=connection.execute('SELECT status FROM jobs WHERE job_id=?',(request['target_job_id'],)).fetchone()
            if (current['revision'],current['fencing_epoch'])!=(execution['revision'],execution['fencing_epoch']):
                raise RetryConflict('Content retry closure ownership changed')
            if substrate[0]=='SUCCEEDED' and current['state']=='ACQUIRING':
                execution=transition(connection,current,'FINALIZING',at=self.timestamp(),name='RECOVERED')
        expected = (execution['revision'], execution['fencing_epoch'])

        def check() -> None:
            with closing(self.repository._connect(read_only=True)) as connection:
                _, current = read(connection, request['request_id'], data_root=self.service.data_root)
                if (current['revision'], current['fencing_epoch']) != expected:
                    raise RetryConflict('Content retry closure ownership changed')

        files = RetryFiles(self.repository, self.service.data_root, request,
            epoch=execution['fencing_epoch'], check=check, timestamp=self.timestamp)
        with closing(self.repository._connect(read_only=True)) as connection:
            substrate=connection.execute('SELECT status FROM jobs WHERE job_id=?',(request['target_job_id'],)).fetchone()
        if (substrate is not None and substrate[0]=='SUCCEEDED' and execution['state']=='FINALIZING'
            and execution['local_attempt_count']<3):
            return self._complete_local_history_limit(request,execution,files,check)
        files.settle()
        with closing(self.repository._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            _, current = read(connection, request['request_id'], data_root=self.service.data_root)
            if (current['revision'], current['fencing_epoch']) != expected:
                raise RetryConflict('Content retry closure ownership changed')
            target = connection.execute('SELECT * FROM jobs WHERE job_id=?',(request['target_job_id'],)).fetchone()
            call = connection.execute('SELECT * FROM provider_calls WHERE request_hash=?',(request['provider_request_hash'],)).fetchone()
            dispatch = connection.execute('SELECT status FROM provider_dispatch_states WHERE request_hash=?',(request['provider_request_hash'],)).fetchone()
            if call is None or dispatch is None:
                raise RetryIntegrity('Content retry closure lost its dispatch proof')
            at = self.timestamp()
            inputs = dict(request_id=request['request_id'],operation='CLOSE_HISTORY_LIMIT',
                expected_revision=current['revision'],prior_state=current['state'],prior_epoch=current['fencing_epoch'],
                dispatch_status=dispatch[0],target_status=target['status'],attempt_count=target['attempt_count'],
                provider_attempt_count=call['attempt_count'],local_attempt_count=current['local_attempt_count'],
                had_dispatch_intent=any(item['event']=='DISPATCH_INTENT' for item in json.loads(current['events_json'])))
            inputs['command_id']='history-limit:'+digest(inputs)
            receipt=dict(operation=inputs['operation'],command_id=inputs['command_id'],expected_revision=current['revision'],
                input_json=canonical(inputs),input_sha256=digest(inputs),applied_revision=current['revision']+1)
            if target['status'] == 'SUCCEEDED' and call['status'] == 'SUCCEEDED' and dispatch[0] == 'SUCCESS_DURABLY_RECORDED':
                state, code = 'FAILED', 'LOCAL_FINALIZATION_LIMIT'
            else:
                if current['state'] != 'ACQUIRING' or target['status'] not in {'RUNNING','FAILED_FINAL'} or call['status'] not in {'PENDING','FAILED_FINAL'}:
                    raise RetryIntegrity('Content retry closure substrate is inconsistent')
                known = dispatch[0] in {'NOT_DISPATCHED','FAILED_KNOWN'}
                state, code = ('FAILED','RETRY_CONTRACT_UNAVAILABLE') if known else ('AMBIGUOUS','DISPATCH_OUTCOME_UNKNOWN')
                underlying = 'CAPABILITY_UNAVAILABLE' if known else 'PROVIDER_UNAVAILABLE'
                connection.execute("UPDATE provider_calls SET status='FAILED_FINAL',reservation_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code=?,last_error_message=? WHERE request_hash=?",(at,at,underlying,code,request['provider_request_hash']))
                connection.execute('UPDATE provider_dispatch_states SET status=?,updated_at=? WHERE request_hash=?',('FAILED_KNOWN' if known else 'AMBIGUOUS',at,request['provider_request_hash']))
                connection.execute("UPDATE job_attempts SET finished_at=?,outcome='FAILED_FINAL',error_code=?,error_message=? WHERE job_id=? AND finished_at IS NULL",(at,underlying,code,request['target_job_id']))
                connection.execute("UPDATE jobs SET status='FAILED_FINAL',lease_owner=NULL,lease_until=NULL,finished_at=?,updated_at=?,last_error_code=?,last_error_message=? WHERE job_id=?",(at,at,underlying,code,request['target_job_id']))
            closed = transition(connection,current,state,at=at,name='HISTORY_LIMIT_CLOSED',action=receipt,error_code=code)
            return public(request,closed)

    def _complete_local_history_limit(self, request: dict[str, Any], execution: dict[str, Any], files: RetryFiles, check: Callable[[], None]) -> dict[str, Any]:
        """Use the remaining slot for real local work, never another caption call."""
        parameters=json.loads(request['parameters_json'])
        proof=None
        with authority(request['target_job_id'],request['provider_request_hash'],check,files.write):
            try:
                check()
                files.settle(terminal=False)
                service=SubtitleAcquisitionService(adapter=UnavailableAdapter(parameters),repository=self.repository,data_root=self.service.data_root,
                    context=TranscriptJobContext(job_id=request['target_job_id'],owner=execution['lease_owner'],pipeline_version=request['pipeline_version'],refresh_generation=request['refresh_generation']),clock=self.service.now)
                service.load_verified_transcript(VideoMetadata.model_validate(parameters['metadata_snapshot']),parameters['language_preferences'])
                summary=ExtractiveSummaryService(self.repository,self.service.data_root)
                summary_id=summary.create(request['video_id'],now=self.service.now())
                summary.read(request['video_id'],summary_id)
                proof=completion(self.repository,request,summary_id)
            except Exception:
                pass
            files.settle()
        check()
        with closing(self.repository._connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            _, current=read(connection,request['request_id'], data_root=self.service.data_root)
            if (current['revision'],current['fencing_epoch'])!=(execution['revision'],execution['fencing_epoch']):
                raise RetryConflict('Content retry local closure ownership changed')
            changes=dict(local_attempt_count=current['local_attempt_count']+1)
            changes['local_attempt'] = dict(phase='INLINE_RESULT', before=current['local_attempt_count'], after=changes['local_attempt_count'])
            if proof is None:
                code='LOCAL_FINALIZATION_FAILED' if changes['local_attempt_count']<3 else 'LOCAL_FINALIZATION_LIMIT'
                result=transition(connection,current,'ATTENTION',at=self.timestamp(),name='LOCAL_INLINE_ATTENTION',error_code=code,**changes)
            else:
                result=transition(connection,current,'SUCCEEDED',at=self.timestamp(),name='LOCAL_INLINE_COMPLETED',completion_json=canonical(proof),completion_sha256=digest(proof),
                    canonical_artifact_id=proof['canonical_artifact_id'],timed_transcript_id=proof['timed_transcript_id'],summary_artifact_id=proof['summary_artifact_id'],**changes)
            return public(request,result)

    def _finalize(
        self,
        service: SubtitleAcquisitionService,
        files: RetryFiles,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            _, execution = read(connection, self.request["request_id"], data_root=self.service.data_root)
            if len(json.loads(execution['events_json'])) + local_event_reserve(execution['local_attempt_count']) > HISTORY_LIMIT:
                connection.commit()
                return self._close_history_limit(self.request,execution)
            exhausted = execution["local_attempt_count"] >= 3
            if not exhausted:
                transition(
                    connection,
                    execution,
                    "FINALIZING",
                    at=self.timestamp(),
                    name="LOCAL_ATTEMPT_STARTED",
                    local_attempt=dict(phase='START', before=execution['local_attempt_count'], after=execution['local_attempt_count']+1),
                    local_attempt_count=execution["local_attempt_count"] + 1,
                )
        if exhausted:
            return self._finish_failure(files, "FAILED", "LOCAL_FINALIZATION_LIMIT")
        try:
            self.check()
            service.load_verified_transcript(
                VideoMetadata.model_validate(parameters["metadata_snapshot"]),
                parameters["language_preferences"],
            )
            summary = ExtractiveSummaryService(self.repository, self.service.data_root)
            summary_id = summary.create(
                self.request["video_id"], now=self.service.now()
            )
            summary.read(self.request["video_id"], summary_id)
            proof = completion(self.repository, self.request, summary_id)
            files.settle()
        except Exception:
            with closing(self.repository._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                _, execution = read(connection, self.request["request_id"], data_root=self.service.data_root)
                execution = transition(
                    connection,
                    execution,
                    "ATTENTION",
                    at=self.timestamp(),
                    name="LOCAL_ATTENTION",
                    error_code="LOCAL_FINALIZATION_FAILED",
                )
                return public(self.request, execution)
        self.check()
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            _, execution = read(connection, self.request["request_id"], data_root=self.service.data_root)
            execution = transition(
                connection,
                execution,
                "SUCCEEDED",
                at=self.timestamp(),
                name="COMPLETED",
                completion_json=canonical(proof),
                completion_sha256=digest(proof),
                canonical_artifact_id=proof["canonical_artifact_id"],
                timed_transcript_id=proof["timed_transcript_id"],
                summary_artifact_id=summary_id,
            )
            return public(self.request, execution)


def completion(
    repository: SQLiteStateRepository, request: dict[str, Any], summary_id: str
) -> dict[str, Any]:
    timed = repository.get_verified_timed_transcript(video_id=request["video_id"])
    call = repository.get_provider_call(request["provider_request_hash"])
    if (
        timed is None
        or call is None
        or call.status.value != "SUCCEEDED"
        or call.response_artifact_id is None
    ):
        raise RetryIntegrity("Content retry completion lacks timed provider authority")
    raw = repository.get_artifact(call.response_artifact_id)
    canonical_artifact = repository.get_artifact(timed.canonical_artifact_id)
    summary = repository.get_artifact(summary_id)
    if (
        raw is None
        or canonical_artifact is None
        or summary is None
        or raw.job_id != request["target_job_id"]
        or canonical_artifact.job_id != request["target_job_id"]
    ):
        raise RetryIntegrity("Content retry completion artifact is foreign")
    with closing(repository._connect(read_only=True)) as connection, connection:
        rows = connection.execute(
            "SELECT e.evidence_id,b.* FROM evidence e JOIN evidence_text_bindings b USING(evidence_id) WHERE e.video_id=? AND e.lineage_kind='ORIGINAL_TRANSCRIPT' AND b.timed_transcript_id=? ORDER BY b.start_cue_index",
            (request["video_id"], timed.timed_transcript_id),
        ).fetchall()
    evidence = []
    position = 0
    for row in rows:
        verified = repository.resolve_verified_evidence_text(row["evidence_id"])
        if verified is None or row["start_cue_index"] != position:
            raise RetryIntegrity("Content retry Evidence coverage changed")
        position = row["end_cue_index"]
        evidence.append(
            dict(
                evidence_id=row["evidence_id"],
                excerpt_hash=verified.excerpt_hash,
                locator_type=verified.locator_type,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=row["start_cue_index"],
                end_cue_index=position,
            )
        )
    if position != len(timed.cues):
        raise RetryIntegrity("Content retry Evidence does not cover its full source")
    return dict(
        contract=CONTRACT,
        request_id=request["request_id"],
        target_job_id=request["target_job_id"],
        provider_request_hash=request["provider_request_hash"],
        parameters_sha256=request["parameters_sha256"],
        raw_artifact_id=raw.artifact_id,
        raw_sha256=raw.content_hash,
        canonical_artifact_id=canonical_artifact.artifact_id,
        canonical_sha256=canonical_artifact.content_hash,
        timed_transcript_id=timed.timed_transcript_id,
        timed_transcript_hash=timed.timed_transcript_hash,
        summary_artifact_id=summary_id,
        summary_sha256=summary.content_hash,
        summary_producer_version=summary.producer_version,
        evidence=evidence,
    )
