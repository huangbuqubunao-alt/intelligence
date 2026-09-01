"""Loopback-only local API exposing safe application-service projections."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    provider_model_statuses,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import (
    AutomationRunRecord,
    AutomationScheduleRecord,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    VideoRecord,
)


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def _timestamp(value: datetime | None) -> str | None:
    return (
        None
        if value is None
        else value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    )


def _source_dto(source: SourceSubscriptionRecord) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "source_type": source.source_type.value,
        "canonical_url": source.canonical_url,
        "channel_id": source.channel_id,
        "video_id": source.video_id,
        "display_name": source.display_name,
        "enabled": source.enabled,
        "processing_policy": source.processing_policy.value,
        "last_checked_at": _timestamp(source.last_checked_at),
        "last_success_at": _timestamp(source.last_success_at),
        "last_error": None
        if source.last_error_code is None
        else {"code": source.last_error_code, "message": source.last_error_message},
        "created_at": _timestamp(source.created_at),
        "updated_at": _timestamp(source.updated_at),
    }


def _video_dto(video: VideoRecord) -> dict[str, object]:
    # Do not expose raw scoring/analysis artifacts.  Score authority is read by
    # AuthoritativeScoringReader only and intentionally omitted until that safe
    # reader is wired to a dedicated projection service.
    return {
        "video_id": video.video_id,
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "title": video.title,
        "source_url": video.source_url,
        "published_at": _timestamp(video.published_at),
        "processing_status": video.pipeline_status.value,
        "scoring": {"status": "NOT_EXPOSED_PENDING_VERIFIED_READER"},
        "note": {"status": "UNKNOWN"},
        "deep_analysis": {"status": "BLOCKED", "reason": "No qualified live provider."},
        "last_updated": _timestamp(video.updated_at),
    }


class LocalApiApplication:
    """Framework-free route dispatcher.  Controllers validate then delegate."""

    def __init__(
        self, repository: SQLiteStateRepository, service: ProductOrchestrationService
    ) -> None:
        self._repository = repository
        self._service = service

    @staticmethod
    def _body(body: bytes) -> dict[str, object]:
        if len(body) > 32_768:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "PAYLOAD_TOO_LARGE",
                "Request body is too large.",
            )
        try:
            parsed: object = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "INVALID_JSON",
                "Request must contain valid JSON.",
            ) from error
        if not isinstance(parsed, dict):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request JSON must be an object.",
            )
        return parsed

    @staticmethod
    def _string(
        data: dict[str, object], key: str, *, required: bool = False
    ) -> str | None:
        value = data.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > 2048:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} is invalid.",
            )
        return value.strip()

    @staticmethod
    def _boolean(data: dict[str, object], key: str) -> bool | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, bool):
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                f"{key} must be boolean.",
            )
        return value

    def handle(
        self, method: str, path: str, body: bytes = b""
    ) -> tuple[int, dict[str, object]]:
        route = urlparse(path).path.rstrip("/") or "/"
        try:
            if method == "GET":
                return HTTPStatus.OK, self._get(route)
            data = self._body(body)
            if method == "POST" and route == "/api/v1/sources":
                policy = ProcessingPolicy(
                    self._string(data, "processing_policy", required=True) or ""
                )
                source = self._service.add_source(
                    url=self._string(data, "url", required=True) or "",
                    processing_policy=policy,
                )
                return HTTPStatus.CREATED, {"source": _source_dto(source)}
            if method == "PATCH" and route.startswith("/api/v1/sources/"):
                source_id = route.rsplit("/", 1)[1]
                policy_value = self._string(data, "processing_policy")
                updated_source = self._service.update_source(
                    source_id,
                    enabled=self._boolean(data, "enabled"),
                    processing_policy=None
                    if policy_value is None
                    else ProcessingPolicy(policy_value),
                )
                if updated_source is None:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                    )
                return HTTPStatus.OK, {"source": _source_dto(updated_source)}
            if (
                method == "POST"
                and route.endswith("/check")
                and route.startswith("/api/v1/sources/")
            ):
                source_id = route.split("/")[-2]
                result = self._service.check_source(source_id)
                return HTTPStatus.OK, {
                    "status": result.status.value,
                    "message": result.safe_message,
                }
            if method == "POST" and route == "/api/v1/automation":
                target_type = AutomationTargetType(
                    self._string(data, "target_type", required=True) or ""
                )
                frequency = ScheduleFrequency(
                    self._string(data, "frequency", required=True) or ""
                )
                weekday = data.get("weekday")
                if weekday is not None and (
                    not isinstance(weekday, int) or isinstance(weekday, bool)
                ):
                    raise ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "VALIDATION_ERROR",
                        "weekday is invalid.",
                    )
                schedule = self._service.save_schedule(
                    schedule_id=self._string(data, "schedule_id"),
                    target_type=target_type,
                    target_id=self._string(data, "target_id"),
                    frequency=frequency,
                    weekday=weekday,
                    local_time=self._string(data, "local_time"),
                    timezone=self._string(data, "timezone", required=True) or "",
                    enabled=self._boolean(data, "enabled") is not False,
                )
                return HTTPStatus.CREATED, {"schedule": self._schedule_dto(schedule)}
            if method == "PUT" and route == "/api/v1/settings/model-preference":
                pref = self._service.set_desired_model(
                    provider=self._string(data, "provider"),
                    model=self._string(data, "model"),
                )
                return HTTPStatus.OK, {
                    "desired_provider": pref.desired_provider,
                    "desired_model": pref.desired_model,
                    "active_production_default": None,
                    "reason": "No production-eligible Deep Analysis model is currently available.",
                }
            raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")
        except ApiError:
            raise
        except (ValueError, KeyError) as error:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "Request values are invalid or unavailable.",
            ) from error

    def _get(self, route: str) -> dict[str, object]:
        if route == "/api/v1/dashboard":
            sources = self._repository.list_source_subscriptions()
            videos = self._repository.list_videos(limit=20)
            runs = self._repository.list_automation_runs(limit=10)
            return {
                "sources": {
                    "total": len(sources),
                    "needs_attention": sum(
                        source.last_error_code is not None for source in sources
                    ),
                },
                "new_videos": len(videos),
                "recent_videos": [_video_dto(video) for video in videos[:5]],
                "next_scheduled_run": self._next_schedule_dto(),
                "recent_processing": [self._run_dto(run) for run in runs[:5]],
                "deep_analysis": {
                    "status": "BLOCKED",
                    "reason": "No qualified live provider.",
                },
            }
        if route == "/api/v1/sources":
            return {
                "sources": [
                    _source_dto(source)
                    for source in self._repository.list_source_subscriptions()
                ]
            }
        if route.startswith("/api/v1/sources/"):
            source = self._repository.get_source_subscription(route.rsplit("/", 1)[1])
            if source is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Source was not found."
                )
            return {
                "source": _source_dto(source),
                "schedules": [
                    self._schedule_dto(item)
                    for item in self._repository.list_automation_schedules()
                    if item.target_id == source.source_id
                ],
                "recent_activity": [
                    self._run_dto(run)
                    for run in self._repository.list_automation_runs(limit=50)
                    if run.target_id == source.source_id
                ],
            }
        if route == "/api/v1/videos":
            return {
                "videos": [
                    _video_dto(video) for video in self._repository.list_videos()
                ]
            }
        if route.startswith("/api/v1/videos/"):
            video = self._repository.get_video(route.rsplit("/", 1)[1])
            if video is None:
                raise ApiError(
                    HTTPStatus.NOT_FOUND, "NOT_FOUND", "Video was not found."
                )
            return {
                "video": _video_dto(video),
                "transcript": {"status": "UNKNOWN"},
                "history": [],
            }
        if route == "/api/v1/weekly":
            return {
                "weekly": [
                    {
                        "report_id": item.report_id,
                        "iso_year": item.iso_year,
                        "iso_week": item.iso_week,
                        "version": "UNKNOWN",
                        "status": item.status.value,
                        "updated_at": _timestamp(item.updated_at),
                    }
                    for item in self._repository.list_reports()
                ]
            }
        if route == "/api/v1/activity":
            return {
                "runs": [
                    self._run_dto(run)
                    for run in self._repository.list_automation_runs()
                ]
            }
        if route == "/api/v1/automation":
            return {
                "schedules": [
                    self._schedule_dto(item)
                    for item in self._repository.list_automation_schedules()
                ]
            }
        if route == "/api/v1/settings":
            preference = self._repository.get_global_model_preference()
            return {
                "processing_defaults": {
                    "policy": ProcessingPolicy.STANDARD_INTELLIGENCE.value
                },
                "model_preference": {
                    "desired_provider": None
                    if preference is None
                    else preference.desired_provider,
                    "desired_model": None
                    if preference is None
                    else preference.desired_model,
                    "active_production_default": None,
                },
                "providers": [
                    asdict(item)
                    for item in provider_model_statuses(
                        None if preference is None else preference.desired_provider,
                        None if preference is None else preference.desired_model,
                    )
                ],
            }
        if route == "/api/v1/system":
            return {
                "release_posture": "NO-GO",
                "version": "0.1.0",
                "doctor": {"status": "NOT_RUN"},
                "backup": {"status": "NOT_RUN"},
                "credential_status": "Blocked",
            }
        raise ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Route was not found.")

    def _next_schedule_dto(self) -> dict[str, object] | None:
        schedules = self._repository.list_automation_schedules()
        schedule = next(
            (
                item
                for item in schedules
                if item.enabled and item.frequency is not ScheduleFrequency.MANUAL
            ),
            None,
        )
        return None if schedule is None else self._schedule_dto(schedule)

    @staticmethod
    def _schedule_dto(schedule: AutomationScheduleRecord) -> dict[str, object]:
        return {
            "schedule_id": schedule.schedule_id,
            "target_type": schedule.target_type.value,
            "target_id": schedule.target_id,
            "frequency": schedule.frequency.value,
            "weekday": schedule.weekday,
            "local_time": schedule.local_time,
            "timezone": schedule.timezone,
            "enabled": schedule.enabled,
            "last_run": None,
            "next_run": None,
        }

    @staticmethod
    def _run_dto(run: AutomationRunRecord) -> dict[str, object]:
        return {
            "run_id": run.run_id,
            "schedule_id": run.schedule_id,
            "target_type": run.target_type.value,
            "target_id": run.target_id,
            "scheduled_for": _timestamp(run.scheduled_for),
            "status": run.status.value,
            "error": None
            if run.error_code is None
            else {"code": run.error_code, "message": run.error_message},
            "summary": run.result_summary,
        }


_LOCAL_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")


def serve_loopback(
    application: LocalApiApplication, *, port: int = 8765
) -> ThreadingHTTPServer:
    """Create, but do not start, a loopback-only server with mutation protection."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send(self, status: int, payload: dict[str, object]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; connect-src 'self'"
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _handle(self) -> None:
            is_mutation = self.command not in {"GET", "HEAD"}
            origin = self.headers.get("Origin")
            if is_mutation and (
                self.headers.get("X-YIA-Request") != "local-ui"
                or (origin is not None and _LOCAL_ORIGIN.fullmatch(origin) is None)
            ):
                self._send(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error": {
                            "code": "ORIGIN_REJECTED",
                            "message": "Unsafe local mutation request was rejected.",
                        }
                    },
                )
                return
            length = int(self.headers.get("Content-Length", "0")) if is_mutation else 0
            try:
                status, payload = application.handle(
                    self.command, self.path, self.rfile.read(length)
                )
                self._send(status, payload)
            except ApiError as error:
                self._send(
                    error.status,
                    {"error": {"code": error.code, "message": error.message}},
                )
            except Exception:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Local service failed safely.",
                        }
                    },
                )

        do_GET = _handle
        do_POST = _handle
        do_PATCH = _handle
        do_PUT = _handle

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
