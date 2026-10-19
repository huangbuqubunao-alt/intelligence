"""Explicit tracked Content retry application boundary; never the full pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import ExitStack, closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel.domain import VideoMetadata
from youtube_intel.state import SQLiteStateRepository, VideoRecord
from youtube_intel.tracked_retry_context import (
    RetryConflict,
    RetryIntegrity,
    request_lock,
    store_lock,
)
from youtube_intel.tracked_retry_store import admit, canonical, identifier, public, read
from youtube_intel.transcripts import (
    FORMAT_POLICY_VERSION,
    NORMALIZATION_VERSION,
    QUALITY_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    SubtitleAdapter,
)


class TrackedContentRetryService:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        data_root: Path,
        *,
        adapter_factory: Callable[[], SubtitleAdapter],
        language_preferences: Sequence[str],
        metadata_for_video: Callable[[VideoRecord], VideoMetadata],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.data_root = data_root.resolve()
        repository.bind_source_storage(self.data_root)
        self.adapter_factory = adapter_factory
        self.languages = tuple(language_preferences)
        self.metadata_for_video = metadata_for_video
        self.now = now or (lambda: datetime.now(UTC))

    def request(
        self, video_id: str, *, command_id: str, expected_job_id: str
    ) -> dict[str, Any]:
        identifier(command_id)
        identifier(expected_job_id)
        with (
            closing(self.repository._connect(read_only=True)) as connection,
            connection,
        ):
            prior = connection.execute(
                "SELECT request_id FROM tracked_content_retry_requests WHERE video_id=? AND command_id=? LIMIT 2",
                (video_id, command_id),
            ).fetchall()
            if prior:
                if len(prior) != 1:
                    raise RetryConflict("Content retry command is ambiguous")
                request, execution = read(connection, prior[0][0], data_root=self.data_root)
                client = {
                    "contract": request["contract"],
                    "operation": request["operation"],
                    "video_id": video_id,
                    "command_id": command_id,
                    "expected_job_id": expected_job_id,
                }
                if request["client_input_json"] != canonical(client):
                    raise RetryConflict("Content retry command input conflicts")
                from youtube_intel.tracked_retry_reader import verify_request

                request, execution, _files = verify_request(self.repository, self.data_root, request['request_id'])
                return public(request, execution)
        video = self.repository.get_video(video_id)
        if video is None:
            raise RetryConflict("Content is unavailable")
        adapter = self.adapter_factory()
        parameters = {
            "language_preferences": list(self.languages),
            "adapter_name": adapter.provider_name,
            "adapter_version": adapter.provider_version,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "format_policy_version": FORMAT_POLICY_VERSION,
            "native_timing_policy_version": "tracked-native-timed-v1",
            "normalization_version": NORMALIZATION_VERSION,
            "quality_policy_version": QUALITY_POLICY_VERSION,
            "metadata_snapshot": self.metadata_for_video(video).model_dump(mode="json"),
            "local_finalize_max_attempts": 3,
        }
        with store_lock(self.repository._database_path), ExitStack() as locks:
            with closing(self.repository._connect(read_only=True)) as connection:
                parent = connection.execute('SELECT request_id FROM tracked_content_retry_requests WHERE target_job_id=?', (expected_job_id,)).fetchone()
            if parent is not None:
                locks.enter_context(request_lock(self.repository._database_path, parent[0]))
                from youtube_intel.tracked_retry_reader import verify_request

                verify_request(self.repository, self.data_root, parent[0], settled=True)
            return admit(
                self.repository,
                video_id,
                command_id=command_id,
                expected_job_id=expected_job_id,
                parameters=parameters,
                now=self.now(),
            )

    def run(self, request_id: str) -> dict[str, Any]:
        from youtube_intel.tracked_retry_worker import RetryWorker

        return RetryWorker(self).run(request_id)

    def action(
        self,
        request_id: str,
        *,
        operation: str,
        command_id: str,
        expected_revision: int,
        expected_video_id: str | None = None,
    ) -> dict[str, Any]:
        import json
        from datetime import timedelta

        from youtube_intel.state import format_utc_datetime
        from youtube_intel.tracked_retry_context import request_lock
        from youtube_intel.tracked_retry_files import RetryFiles
        from youtube_intel.tracked_retry_store import (
            HISTORY_LIMIT,
            digest,
            local_event_reserve,
        )
        from youtube_intel.tracked_retry_worker import transition

        identifier(command_id)
        if (
            operation not in {"RESUME_LOCAL", "CLOSE_LOCAL", "CANCEL_BEFORE_DISPATCH"}
            or type(expected_revision) is not int
            or expected_revision < 0
        ):
            raise RetryConflict("Content retry action is invalid")
        inputs = dict(
            request_id=request_id,
            operation=operation,
            command_id=command_id,
            expected_revision=expected_revision,
        )
        with (
            store_lock(self.repository._database_path),
            request_lock(self.repository._database_path, request_id),
        ):
            with (
                closing(self.repository._connect(read_only=True)) as connection,
                connection,
            ):
                request, execution = read(connection, request_id, data_root=self.data_root)
                if expected_video_id is not None and request['video_id'] != expected_video_id:
                    raise RetryConflict('Content retry action does not belong to this Content')
                from youtube_intel.tracked_retry_reader import verify_request

                verify_request(self.repository,self.data_root,request_id)
                for entry in json.loads(execution["events_json"]):
                    action = entry["action"]
                    if action is not None and (
                        action["operation"],
                        action["command_id"],
                    ) == (operation, command_id):
                        if action["input_json"] != canonical(inputs):
                            raise RetryConflict("Content retry action input conflicts")
                        return public(request, execution)
                required = (
                    "QUEUED" if operation == "CANCEL_BEFORE_DISPATCH" else "ATTENTION"
                )
                if (
                    execution["state"] != required
                    or execution["revision"] != expected_revision
                ):
                    raise RetryConflict("Content retry action state changed")
                if operation == "RESUME_LOCAL" and (
                    execution["local_attempt_count"] >= 3
                    or len(json.loads(execution["events_json"])) + local_event_reserve(execution['local_attempt_count']) - 1 > HISTORY_LIMIT
                ):
                    raise RetryConflict(
                        "Content retry local finalization limit reached"
                    )
            epoch = execution["fencing_epoch"]

            def check() -> None:
                with (
                    closing(self.repository._connect(read_only=True)) as connection,
                    connection,
                ):
                    _, current = read(connection, request_id, data_root=self.data_root)
                    if (
                        current["fencing_epoch"] != epoch
                        or current["revision"] != expected_revision
                    ):
                        raise RetryConflict("Content retry action ownership changed")

            files = RetryFiles(
                self.repository,
                self.data_root,
                request,
                epoch=epoch,
                check=check,
                timestamp=lambda: format_utc_datetime(self.now()),
            )
            files.settle(terminal=operation!='RESUME_LOCAL')
            with closing(self.repository._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                _, execution = read(connection, request_id, data_root=self.data_root)
                if execution["revision"] != expected_revision:
                    raise RetryConflict("Content retry action state changed")
                at = format_utc_datetime(self.now())
                action = dict(
                    operation=operation,
                    command_id=command_id,
                    expected_revision=expected_revision,
                    input_json=canonical(inputs),
                    input_sha256=digest(inputs),
                    applied_revision=expected_revision + 1,
                )
                changes: dict[str, Any] = dict(fencing_epoch=epoch + 1)
                if operation == "RESUME_LOCAL":
                    state, name = "FINALIZING", "LOCAL_RESUMED"
                    changes.update(
                        lease_owner="local-resume-" + command_id[:100],
                        lease_until=format_utc_datetime(
                            self.now() + timedelta(minutes=5)
                        ),
                    )
                elif operation == "CLOSE_LOCAL":
                    state, name = "FAILED", "FAILED"
                    changes["error_code"] = "LOCAL_FINALIZATION_CLOSED"
                else:
                    if execution["provider_call_hash"] is not None:
                        raise RetryConflict("Content retry dispatch has already begun")
                    state, name = "CANCELLED", "CANCELLED"
                    changes["error_code"] = "CANCELLED_BEFORE_DISPATCH"
                    connection.execute(
                        "UPDATE jobs SET status='FAILED_FINAL',last_error_code='CAPABILITY_UNAVAILABLE',last_error_message='CANCELLED_BEFORE_DISPATCH',finished_at=?,updated_at=? WHERE job_id=? AND status='PENDING'",
                        (at, at, request["target_job_id"]),
                    )
                execution = transition(
                    connection,
                    execution,
                    state,
                    at=at,
                    name=name,
                    action=action,
                    **changes,
                )
                return public(request, execution)

    def status(self, video_id: str) -> dict[str, Any]:
        from youtube_intel.tracked_retry_reader import verify_request
        from youtube_intel.tracked_retry_store import (
            validate_source,
            verify_old_failure,
        )

        result: dict[str, Any] = {
            "request": None,
            "retry_allowed": False,
            "expected_job_id": None,
        }
        with (
            closing(self.repository._connect(read_only=True)) as connection,
            connection,
        ):
            rows = connection.execute(
                "SELECT request_id FROM tracked_content_retry_requests r WHERE video_id=? AND NOT EXISTS(SELECT 1 FROM tracked_content_retry_requests child WHERE child.expected_old_job_id=r.target_job_id) ORDER BY created_at DESC,request_id DESC LIMIT 1",
                (video_id,),
            ).fetchall()
            if rows:
                request, execution, _files = verify_request(
                    self.repository, self.data_root, rows[0][0]
                )
                result["request"] = public(request, execution)
            video = connection.execute(
                "SELECT * FROM videos WHERE video_id=?", (video_id,)
            ).fetchone()
            old = connection.execute(
                "SELECT * FROM jobs j WHERE video_id=? AND job_type='VIDEO_STAGE' AND NOT EXISTS(SELECT 1 FROM tracked_content_retry_requests r WHERE r.expected_old_job_id=j.job_id) ORDER BY created_at DESC,job_id DESC LIMIT 1",
                (video_id,),
            ).fetchone()
            if (
                video is None
                or old is None
                or video["pipeline_status"] != "METADATA_READY"
                or old["status"] != "FAILED_FINAL"
                or old["target_stage"] != "TRANSCRIPT"
            ):
                return result
            try:
                source = validate_source(connection, self.repository, video_id)
            except RetryConflict:
                return result
            try:
                parent_id = verify_old_failure(connection, old, source_id=source['source_id'], data_root=self.data_root)
                if parent_id is not None:
                    with request_lock(self.repository._database_path, parent_id):
                        verify_request(self.repository, self.data_root, parent_id, settled=True)
            except (RetryConflict, RetryIntegrity):
                return result
            if (
                old["lease_owner"] is not None
                or old["lease_until"] is not None
                or old["finished_at"] is None
                or old["pipeline_version"] != video["pipeline_version"]
                or connection.execute(
                    "SELECT 1 FROM tracked_content_retry_requests WHERE expected_old_job_id=?",
                    (old["job_id"],),
                ).fetchone()
                or connection.execute(
                    "SELECT 1 FROM tracked_content_retry_executions WHERE source_id=? AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION') UNION ALL SELECT 1 FROM source_runs WHERE source_id=? AND state IN ('QUEUED','RUNNING','WAITING','PARTIAL','NEEDS_ATTENTION') UNION ALL SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING'",
                    (source["source_id"], source["source_id"], source["source_id"]),
                ).fetchone()
                or connection.execute(
                    "SELECT 1 FROM jobs WHERE video_id=? AND status NOT IN ('SUCCEEDED','FAILED_FINAL') UNION ALL SELECT 1 FROM job_attempts a JOIN jobs j USING(job_id) WHERE j.video_id=? AND a.finished_at IS NULL",
                    (video_id, video_id),
                ).fetchone()
                or connection.execute(
                    "SELECT 1 FROM provider_calls WHERE status NOT IN ('SUCCEEDED','FAILED_FINAL') UNION ALL SELECT 1 FROM provider_dispatch_states WHERE status NOT IN ('SUCCESS_DURABLY_RECORDED','FAILED_KNOWN')"
                ).fetchone()
            ):
                return result
            result.update(retry_allowed=True, expected_job_id=old["job_id"])
            return result
