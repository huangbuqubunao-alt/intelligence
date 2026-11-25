"""Explicit opt-in YouTube authentication fallback for single-video imports.

Principle:
1. Default state is strictly ``disabled``. Anonymous public fetches run first;
   this module is NEVER invoked unless an anonymous single-video import fails
   specifically because YouTube requested login / bot verification
   (``YOUTUBE_AUTH_REQUIRED``).
2. Credentials (uploaded Netscape ``cookies.txt``) are stored exclusively in the
   macOS Keychain (via ``CredentialStore``), never in SQLite, backups, logs, or
   API GET responses.
3. Strict frequency guardrails protect user accounts: configurable daily cap
   (default 20/day, max 50/day), inter-attempt cooldown (default 15s, min 10s),
   and automatic 30-minute circuit breaker upon HTTP 429 or auth rejection.
   Never attempts CAPTCHA solving.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import secrets
import sqlite3
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit

import yt_dlp  # type: ignore[import-untyped]

from youtube_intel.domain import JobStatus
from youtube_intel.model_settings import CredentialStore, MacOSKeychainCredentialStore
from youtube_intel.providers.subtitles import (
    YtDlpSubtitleAdapter,
)
from youtube_intel.providers.subtitles import (
    _bind_test_hooks as _bind_subtitle_hooks,
)
from youtube_intel.providers.youtube import (
    YtDlpMetadataProvider,
    _resolve_system_proxy_url,
)
from youtube_intel.providers.youtube import (
    _bind_test_hooks as _bind_metadata_hooks,
)
from youtube_intel.state import format_utc_datetime

if TYPE_CHECKING:
    from youtube_intel.runtime import RuntimeOperations

SUPPORTED_AUTH_BROWSERS: Final[tuple[str, ...]] = (
    "chrome",
    "firefox",
    "edge",
    "brave",
    "safari",
    "vivaldi",
    "chromium",
)
VALID_AUTH_MODES: Final[frozenset[str]] = frozenset({"disabled", "browser", "cookie_file"})
DEFAULT_DAILY_LIMIT: Final[int] = 20
MAX_DAILY_LIMIT: Final[int] = 50
DEFAULT_COOLDOWN_SECONDS: Final[int] = 15
MIN_COOLDOWN_SECONDS: Final[int] = 10
MAX_COOLDOWN_SECONDS: Final[int] = 300
CIRCUIT_BREAK_MINUTES: Final[int] = 30
MAX_COOKIES_BYTES: Final[int] = 512 * 1024

_ALLOWED_COOKIE_ROOTS: Final[tuple[str, ...]] = (
    "youtube.com",
    "youtu.be",
    "google.com",
    "googlevideo.com",
    "ytimg.com",
)
_PRIMARY_COOKIE_ROOTS: Final[tuple[str, ...]] = ("youtube.com", "google.com")
_HOST_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_SAFE_SUBTITLE_HOST_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:[A-Za-z0-9-]+\.)*(?:youtube\.com|googlevideo\.com)$",
    re.IGNORECASE,
)


class _SilentLogger:
    def debug(self, msg: str) -> None:
        del msg

    def warning(self, msg: str) -> None:
        del msg

    def error(self, msg: str) -> None:
        del msg


class WorkspaceYouTubeCookiesKeychainStore(MacOSKeychainCredentialStore):
    """Dedicated macOS Keychain slot for optional YouTube fallback cookies."""

    _service = b"com.huangbuqubunao.intelligence.workspace-youtube-cookies"
    _account = b"netscape-cookies"


def _parse_iso_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_cookie_domain(raw_domain: str) -> str | None:
    cleaned = raw_domain.strip().lower()
    if not cleaned or cleaned != raw_domain.lower():
        return None
    host = cleaned[1:] if cleaned.startswith(".") else cleaned
    if not host or host.endswith(".") or ".." in host or any(c in host for c in "*:/[]"):
        return None
    labels = host.split(".")
    if len(labels) < 2 or labels[-1].isdigit():
        return None
    if any(_HOST_LABEL_RE.fullmatch(label) is None for label in labels):
        return None
    return host


def _is_allowed_cookie_domain(
    raw_domain: str,
    roots: tuple[str, ...] = _ALLOWED_COOKIE_ROOTS,
) -> bool:
    host = _normalize_cookie_domain(raw_domain)
    if host is None:
        return False
    return any(host == root or host.endswith(f".{root}") for root in roots)


def validate_netscape_cookies_txt(raw: str) -> str:
    """Validate and minimally filter Netscape HTTP cookie text to YouTube/Google domains."""
    if not isinstance(raw, str):
        raise ValueError("cookies.txt must be text")
    text = raw.lstrip("\ufeff").strip("\r\n")
    if not text.strip():
        raise ValueError("cookies.txt cannot be empty")
    if "\x00" in text:
        raise ValueError("cookies.txt contains binary NUL bytes")
    if len(text.encode("utf-8")) > MAX_COOKIES_BYTES:
        raise ValueError("cookies.txt exceeds 512 KiB size limit")

    lines = text.splitlines()
    filtered_lines: list[str] = []
    has_youtube_or_google = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_httponly = stripped.startswith("#HttpOnly_")
        if stripped.startswith("#") and not is_httponly:
            filtered_lines.append(line)
            continue
        entry = stripped[len("#HttpOnly_") :] if is_httponly else stripped
        parts = entry.split("\t")
        if len(parts) != 7:
            raise ValueError("cookies.txt must use valid Netscape 7-column tab format")
        domain = parts[0]
        if not _is_allowed_cookie_domain(domain, _ALLOWED_COOKIE_ROOTS):
            continue
        filtered_lines.append(stripped)
        if _is_allowed_cookie_domain(domain, _PRIMARY_COOKIE_ROOTS):
            has_youtube_or_google = True
    if not has_youtube_or_google:
        raise ValueError("cookies.txt must contain at least one youtube.com or google.com cookie")
    return "\n".join(filtered_lines) + "\n"


def _validate_subtitle_redirect_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (parsed.port not in {None, 443})
        or bool(parsed.fragment)
        or _SAFE_SUBTITLE_HOST_RE.fullmatch(parsed.hostname) is None
    ):
        raise urllib.error.URLError("unsafe redirect target")


class _SafeCookieRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        _validate_subtitle_redirect_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class _AuthConfigRow:
    enabled: bool
    auth_mode: str
    browser_name: str
    daily_limit: int
    cooldown_seconds: int
    circuit_open_until: str
    updated_at: str


class YouTubeAuthFallbackService:
    """Manages opt-in authenticated YouTube fallback & frequency protection."""

    def __init__(
        self,
        *,
        project_root: Path,
        cookie_store: CredentialStore | None = None,
        ydl_factory: Callable[[dict[str, Any]], Any] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._project_root = project_root.resolve()
        self.db_path = self._project_root / ".workspace-ai" / "hub.sqlite3"
        self._cookie_store: CredentialStore = (
            cookie_store
            if cookie_store is not None
            else WorkspaceYouTubeCookiesKeychainStore()
        )
        self._ydl_factory = ydl_factory
        self._now = now or (lambda: datetime.now(UTC))
        self._db_lock = threading.RLock()

    def _has_cookie_secret(self) -> bool:
        try:
            secret = self._cookie_store.get()
        except Exception:  # noqa: BLE001
            return False
        return bool(secret and secret.strip())

    def _read_cookie_secret(self) -> str | None:
        try:
            secret = self._cookie_store.get()
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(secret, str) or not secret.strip():
            return None
        return secret

    def _connect_read(self) -> sqlite3.Connection | None:
        if not self.db_path.is_file():
            return None
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(
                f"{self.db_path.resolve().as_uri()}?mode=ro",
                uri=True,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=5000")
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='youtube_auth_config'"
            ).fetchone()
            if has_table is None:
                conn.close()
                return None
            return conn
        except sqlite3.Error:
            if conn is not None:
                conn.close()
            return None

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_auth_config (
                singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                auth_mode TEXT NOT NULL DEFAULT 'disabled',
                browser_name TEXT NOT NULL DEFAULT '',
                daily_limit INTEGER NOT NULL DEFAULT 20,
                cooldown_seconds INTEGER NOT NULL DEFAULT 15,
                circuit_open_until TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_auth_usage (
                usage_id TEXT PRIMARY KEY,
                day_utc TEXT NOT NULL,
                video_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def _connect_write(self, *, immediate: bool = False) -> sqlite3.Connection:
        self.db_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            isolation_level=None if immediate else "DEFERRED",
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            with self._db_lock:
                self._ensure_schema(conn)
            return conn
        except BaseException:
            conn.close()
            raise

    @staticmethod
    def _begin_immediate(conn: sqlite3.Connection) -> None:
        deadline = time.monotonic() + 5.0
        while True:
            try:
                conn.execute("BEGIN IMMEDIATE")
                return
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if ("locked" in msg or "busy" in msg) and time.monotonic() < deadline:
                    time.sleep(0.01)
                    continue
                raise

    @staticmethod
    def _read_config_from_conn(conn: sqlite3.Connection) -> _AuthConfigRow:
        default = _AuthConfigRow(
            enabled=False,
            auth_mode="disabled",
            browser_name="",
            daily_limit=DEFAULT_DAILY_LIMIT,
            cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
            circuit_open_until="",
            updated_at="",
        )
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='youtube_auth_config'"
        ).fetchone()
        if has_table is None:
            return default
        row = conn.execute(
            "SELECT * FROM youtube_auth_config WHERE singleton_id = 1"
        ).fetchone()
        if row is None:
            return default
        mode = str(row["auth_mode"] or "disabled")
        if mode not in VALID_AUTH_MODES:
            mode = "disabled"
        browser = str(row["browser_name"] or "").strip().lower()
        if browser not in SUPPORTED_AUTH_BROWSERS:
            browser = ""
        return _AuthConfigRow(
            enabled=bool(row["enabled"]) and mode != "disabled",
            auth_mode=mode,
            browser_name=browser,
            daily_limit=max(1, min(MAX_DAILY_LIMIT, int(row["daily_limit"] or DEFAULT_DAILY_LIMIT))),
            cooldown_seconds=max(
                MIN_COOLDOWN_SECONDS,
                min(MAX_COOLDOWN_SECONDS, int(row["cooldown_seconds"] or DEFAULT_COOLDOWN_SECONDS)),
            ),
            circuit_open_until=str(row["circuit_open_until"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    def _read_config_row(self) -> _AuthConfigRow:
        default = _AuthConfigRow(
            enabled=False,
            auth_mode="disabled",
            browser_name="",
            daily_limit=DEFAULT_DAILY_LIMIT,
            cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
            circuit_open_until="",
            updated_at="",
        )
        conn = self._connect_read()
        if conn is None:
            return default
        try:
            return self._read_config_from_conn(conn)
        finally:
            conn.close()

    @staticmethod
    def _usage_stats_from_conn(conn: sqlite3.Connection, day_utc: str) -> tuple[int, str | None]:
        has_usage = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='youtube_auth_usage'"
        ).fetchone()
        if has_usage is None:
            return 0, None
        cnt_row = conn.execute(
            "SELECT COUNT(*) FROM youtube_auth_usage WHERE day_utc = ? AND outcome != 'CANCELLED'",
            (day_utc,),
        ).fetchone()
        last_row = conn.execute(
            "SELECT created_at FROM youtube_auth_usage WHERE outcome != 'CANCELLED' "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        used = int(cnt_row[0]) if cnt_row is not None else 0
        last_ts = str(last_row["created_at"]) if last_row is not None else None
        return used, last_ts

    def _usage_stats(self, day_utc: str) -> tuple[int, str | None]:
        conn = self._connect_read()
        if conn is None:
            return 0, None
        try:
            return self._usage_stats_from_conn(conn, day_utc)
        finally:
            conn.close()

    def get_status(self) -> dict[str, object]:
        """Return safe YouTube fallback authorization status (zero secrets)."""
        now = self._now()
        day_utc = now.astimezone(UTC).strftime("%Y-%m-%d")
        cfg = self._read_config_row()
        used_today, _ = self._usage_stats(day_utc)
        circuit_until = _parse_iso_utc(cfg.circuit_open_until)
        circuit_open = bool(circuit_until is not None and circuit_until > now)
        return {
            "enabled": cfg.enabled,
            "auth_mode": cfg.auth_mode,
            "browser_name": cfg.browser_name,
            "supported_browsers": list(SUPPORTED_AUTH_BROWSERS),
            "cookie_configured": self._has_cookie_secret(),
            "daily_limit": cfg.daily_limit,
            "used_today": used_today,
            "cooldown_seconds": cfg.cooldown_seconds,
            "circuit_open_until": cfg.circuit_open_until if circuit_open else "",
            "circuit_open": circuit_open,
        }

    def update_config(self, payload: Mapping[str, object]) -> dict[str, object]:
        """Update opt-in YouTube auth fallback settings and validate inputs."""
        if not isinstance(payload, Mapping):
            raise ValueError("Payload must be a JSON object")
        allowed_keys = {
            "enabled",
            "auth_mode",
            "browser_name",
            "cookies_txt",
            "daily_limit",
            "cooldown_seconds",
        }
        unknown = set(payload.keys()) - allowed_keys
        if unknown:
            raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")

        current = self._read_config_row()
        raw_mode = payload.get("auth_mode", current.auth_mode)
        if not isinstance(raw_mode, str) or raw_mode.strip() not in VALID_AUTH_MODES:
            raise ValueError("auth_mode must be 'disabled', 'browser', or 'cookie_file'")
        auth_mode = raw_mode.strip()

        enabled_raw = payload.get("enabled", auth_mode != "disabled")
        if not isinstance(enabled_raw, bool):
            raise ValueError("enabled must be a boolean")
        enabled = enabled_raw and auth_mode != "disabled"
        if auth_mode == "disabled":
            enabled = False

        browser_name = current.browser_name
        if auth_mode == "browser":
            raw_browser = payload.get("browser_name", current.browser_name)
            if not isinstance(raw_browser, str) or raw_browser.strip().lower() not in SUPPORTED_AUTH_BROWSERS:
                raise ValueError(
                    f"browser_name must be one of: {', '.join(SUPPORTED_AUTH_BROWSERS)}"
                )
            browser_name = raw_browser.strip().lower()
        elif "browser_name" in payload and isinstance(payload["browser_name"], str):
            candidate = payload["browser_name"].strip().lower()
            if candidate and candidate not in SUPPORTED_AUTH_BROWSERS:
                raise ValueError("Unsupported browser_name")
            browser_name = candidate

        raw_limit = payload.get("daily_limit", current.daily_limit)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, (int, str)):
            raise ValueError("daily_limit must be an integer between 1 and 50")
        try:
            daily_limit = int(raw_limit)
        except ValueError as err:
            raise ValueError("daily_limit must be an integer between 1 and 50") from err
        if daily_limit < 1 or daily_limit > MAX_DAILY_LIMIT:
            raise ValueError("daily_limit must be an integer between 1 and 50")

        raw_cooldown = payload.get("cooldown_seconds", current.cooldown_seconds)
        if isinstance(raw_cooldown, bool) or not isinstance(raw_cooldown, (int, str)):
            raise ValueError("cooldown_seconds must be an integer between 10 and 300")
        try:
            cooldown_seconds = int(raw_cooldown)
        except ValueError as err:
            raise ValueError("cooldown_seconds must be an integer between 10 and 300") from err
        if cooldown_seconds < MIN_COOLDOWN_SECONDS or cooldown_seconds > MAX_COOLDOWN_SECONDS:
            raise ValueError("cooldown_seconds must be an integer between 10 and 300")

        if "cookies_txt" in payload and payload["cookies_txt"] is not None:
            raw_cookies = payload["cookies_txt"]
            if not isinstance(raw_cookies, str):
                raise ValueError("cookies_txt must be a string")
            if raw_cookies.strip():
                validated_cookies = validate_netscape_cookies_txt(raw_cookies)
                self._cookie_store.save(validated_cookies)
            elif auth_mode == "cookie_file" and not self._has_cookie_secret():
                raise ValueError("cookies_txt is required when no cookies are stored")

        if auth_mode == "cookie_file" and enabled and not self._has_cookie_secret():
            raise ValueError("Please paste or import a valid cookies.txt first")

        ts = format_utc_datetime(self._now())
        with self._db_lock:
            conn = self._connect_write(immediate=True)
            try:
                self._begin_immediate(conn)
                try:
                    conn.execute(
                        """
                        INSERT INTO youtube_auth_config (
                            singleton_id, enabled, auth_mode, browser_name,
                            daily_limit, cooldown_seconds, circuit_open_until, updated_at
                        ) VALUES (1, ?, ?, ?, ?, ?, '', ?)
                        ON CONFLICT(singleton_id) DO UPDATE SET
                            enabled = excluded.enabled,
                            auth_mode = excluded.auth_mode,
                            browser_name = excluded.browser_name,
                            daily_limit = excluded.daily_limit,
                            cooldown_seconds = excluded.cooldown_seconds,
                            circuit_open_until = '',
                            updated_at = excluded.updated_at
                        """,
                        (
                            1 if enabled else 0,
                            auth_mode,
                            browser_name,
                            daily_limit,
                            cooldown_seconds,
                            ts,
                        ),
                    )
                    conn.execute("COMMIT")
                except BaseException:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
            finally:
                conn.close()
        return self.get_status()

    def disconnect(self) -> dict[str, object]:
        """Disable authenticated fallback, clear circuit state, and purge Keychain cookies."""
        with contextlib.suppress(Exception):
            self._cookie_store.delete()
        if self.db_path.is_file():
            ts = format_utc_datetime(self._now())
            with self._db_lock:
                conn = self._connect_write(immediate=True)
                try:
                    self._begin_immediate(conn)
                    try:
                        conn.execute(
                            """
                            INSERT INTO youtube_auth_config (
                                singleton_id, enabled, auth_mode, browser_name,
                                daily_limit, cooldown_seconds, circuit_open_until, updated_at
                            ) VALUES (1, 0, 'disabled', '', ?, ?, '', ?)
                            ON CONFLICT(singleton_id) DO UPDATE SET
                                enabled = 0,
                                auth_mode = 'disabled',
                                browser_name = '',
                                circuit_open_until = '',
                                updated_at = excluded.updated_at
                            """,
                            (DEFAULT_DAILY_LIMIT, DEFAULT_COOLDOWN_SECONDS, ts),
                        )
                        conn.execute("COMMIT")
                    except BaseException:
                        with contextlib.suppress(sqlite3.Error):
                            conn.execute("ROLLBACK")
                        raise
                finally:
                    conn.close()
        return self.get_status()

    def _evaluate_eligibility(
        self,
        cfg: _AuthConfigRow,
        used_today: int,
        last_ts: str | None,
        now: datetime,
    ) -> tuple[bool, str | None]:
        if not cfg.enabled or cfg.auth_mode == "disabled":
            return False, "YOUTUBE_AUTH_DISABLED"
        if cfg.auth_mode == "browser" and cfg.browser_name not in SUPPORTED_AUTH_BROWSERS:
            return False, "YOUTUBE_AUTH_DISABLED"
        if cfg.auth_mode == "cookie_file" and not self._has_cookie_secret():
            return False, "YOUTUBE_AUTH_DISABLED"

        circuit_until = _parse_iso_utc(cfg.circuit_open_until)
        if circuit_until is not None and circuit_until > now:
            return False, "YOUTUBE_AUTH_RATE_LIMITED"

        if used_today >= cfg.daily_limit:
            return False, "YOUTUBE_AUTH_RATE_LIMITED"

        last_dt = _parse_iso_utc(last_ts)
        updated_dt = _parse_iso_utc(cfg.updated_at)
        # Apply inter-attempt cooldown only for attempts after the latest config update,
        # so re-authorizing fresh cookies lets a user retry immediately.
        if last_dt is not None and (updated_dt is None or last_dt >= updated_dt):
            elapsed = (now - last_dt).total_seconds()
            if elapsed < cfg.cooldown_seconds:
                return False, "YOUTUBE_AUTH_RATE_LIMITED"
        return True, None

    def can_attempt(self, video_id: str) -> tuple[bool, str | None]:
        """Verify fallback is enabled, configured, and within rate limits."""
        del video_id
        cfg = self._read_config_row()
        now = self._now()
        day_utc = now.astimezone(UTC).strftime("%Y-%m-%d")
        used_today, last_ts = self._usage_stats(day_utc)
        return self._evaluate_eligibility(cfg, used_today, last_ts, now)

    def _reserve_attempt_slot(
        self, video_id: str
    ) -> tuple[_AuthConfigRow, str] | tuple[None, str]:
        """Atomically reserve quota & cooldown slot inside SQLite BEGIN IMMEDIATE."""
        if not self.db_path.is_file():
            return None, "YOUTUBE_AUTH_DISABLED"
        with self._db_lock:
            conn = self._connect_write(immediate=True)
            try:
                self._begin_immediate(conn)
                try:
                    cfg = self._read_config_from_conn(conn)
                    now = self._now()
                    day_utc = now.astimezone(UTC).strftime("%Y-%m-%d")
                    used_today, last_ts = self._usage_stats_from_conn(conn, day_utc)
                    allowed, deny_code = self._evaluate_eligibility(
                        cfg, used_today, last_ts, now
                    )
                    if not allowed:
                        conn.execute("ROLLBACK")
                        return None, deny_code or "YOUTUBE_AUTH_DISABLED"
                    usage_id = f"ytauth-{uuid.uuid4().hex}"
                    now_iso = format_utc_datetime(now)
                    conn.execute(
                        "INSERT INTO youtube_auth_usage (usage_id, day_utc, video_id, outcome, created_at) "
                        "VALUES (?, ?, ?, 'RESERVED', ?)",
                        (usage_id, day_utc, video_id, now_iso),
                    )
                    conn.execute("COMMIT")
                    return cfg, usage_id
                except BaseException:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
            finally:
                conn.close()

    def _finalize_attempt_slot(
        self,
        usage_id: str,
        *,
        video_id: str,
        outcome: str,
        open_circuit: bool = False,
    ) -> None:
        now = self._now()
        now_iso = format_utc_datetime(now)
        day_utc = now.astimezone(UTC).strftime("%Y-%m-%d")
        circuit_iso = (
            format_utc_datetime(now + timedelta(minutes=CIRCUIT_BREAK_MINUTES))
            if open_circuit
            else None
        )
        with self._db_lock:
            conn = self._connect_write(immediate=True)
            try:
                self._begin_immediate(conn)
                try:
                    cur = conn.execute(
                        "UPDATE youtube_auth_usage SET outcome = ? WHERE usage_id = ?",
                        (outcome, usage_id),
                    )
                    if cur.rowcount == 0:
                        conn.execute(
                            "INSERT INTO youtube_auth_usage (usage_id, day_utc, video_id, outcome, created_at) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (usage_id, day_utc, video_id, outcome, now_iso),
                        )
                    if circuit_iso is not None:
                        conn.execute(
                            "UPDATE youtube_auth_config SET circuit_open_until = ?, updated_at = ? "
                            "WHERE singleton_id = 1",
                            (circuit_iso, now_iso),
                        )
                    conn.execute("COMMIT")
                except BaseException:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
            finally:
                conn.close()

    def _record_usage(
        self,
        *,
        video_id: str,
        outcome: str,
        open_circuit: bool = False,
    ) -> None:
        self._finalize_attempt_slot(
            f"ytauth-{uuid.uuid4().hex}",
            video_id=video_id,
            outcome=outcome,
            open_circuit=open_circuit,
        )

    @contextlib.contextmanager
    def _auth_execution_context(
        self, cfg: _AuthConfigRow
    ) -> Iterator[
        tuple[
            Callable[[dict[str, Any]], Any],
            Callable[[urllib.request.Request, float], object],
        ]
    ]:
        with tempfile.TemporaryDirectory(prefix="yia-yt-auth-") as tmp_dir:
            auth_opts: dict[str, Any] = {}
            if cfg.auth_mode == "browser":
                auth_opts["cookiesfrombrowser"] = (cfg.browser_name,)
            elif cfg.auth_mode == "cookie_file":
                secret = self._read_cookie_secret()
                if not secret:
                    raise ValueError("YOUTUBE_AUTH_DISABLED")
                cookie_path = Path(tmp_dir) / "cookies.txt"
                fd = os.open(cookie_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    os.write(fd, secret.encode("utf-8"))
                finally:
                    os.close(fd)
                auth_opts["cookiefile"] = str(cookie_path)

            proxy_url = _resolve_system_proxy_url()
            info_cache: dict[str, object] = {}
            base_factory = self._ydl_factory
            holder: dict[str, Any] = {"cookiejar": None}

            class _CachingYdl:
                def __init__(self, inner: Any) -> None:
                    self._inner = inner

                def extract_info(self, url: str, download: bool = True) -> object:
                    cache_key = f"{int(bool(download))}:{url}"
                    if base_factory is None and cache_key in info_cache:
                        return info_cache[cache_key]
                    result = self._inner.extract_info(url, download=download)
                    if base_factory is None and not download and isinstance(result, Mapping):
                        info_cache[cache_key] = result
                    return result

            def factory(opts: dict[str, Any]) -> Any:
                merged = dict(opts)
                merged.update(auth_opts)
                if proxy_url and "proxy" not in merged:
                    merged["proxy"] = proxy_url
                if base_factory is not None:
                    handle = base_factory(merged)
                else:
                    handle = yt_dlp.YoutubeDL(merged)
                cj = getattr(handle, "cookiejar", None)
                if cj is not None:
                    holder["cookiejar"] = cj
                return _CachingYdl(handle)

            def opener(request: urllib.request.Request, timeout: float) -> object:
                handlers: list[urllib.request.BaseHandler] = [
                    _SafeCookieRedirectHandler(),
                ]
                if proxy_url:
                    handlers.append(
                        urllib.request.ProxyHandler(
                            {"https": proxy_url, "http": proxy_url}
                        )
                    )
                if holder["cookiejar"] is not None:
                    handlers.append(urllib.request.HTTPCookieProcessor(holder["cookiejar"]))
                built = urllib.request.build_opener(*handlers)
                return built.open(request, timeout=timeout)  # noqa: S310

            yield factory, opener

    def attempt_authenticated_ingest(
        self,
        runtime: RuntimeOperations,
        source_id: str,
        video_id: str,
    ) -> str | None:
        """Attempt bounded authenticated ingest for one video after anonymous block.

        Returns ``None`` on success, or a closed safe ``YOUTUBE_*`` error code.
        """
        cfg, reserved_or_deny = self._reserve_attempt_slot(video_id)
        if cfg is None:
            return reserved_or_deny
        usage_id = reserved_or_deny

        from youtube_intel.extractive_summary import ExtractiveSummaryService
        from youtube_intel.runtime import RuntimeOperations as RuntimeOpsCls

        timeout = float(runtime._config.settings.timeouts.http_seconds)
        now = self._now()

        latest_job = runtime._repository.latest_content_job(video_id)
        if (
            latest_job is not None
            and latest_job.status is JobStatus.FAILED_FINAL
            and latest_job.target_stage is not None
            and latest_job.target_stage.value in {"METADATA", "TRANSCRIPT"}
            and latest_job.last_error_code
            not in {"CAPABILITY_UNAVAILABLE", "TRUST_INTEGRITY_INVALID"}
        ):
            runtime._repository.rerun_job(
                latest_job.job_id,
                new_job_id="content-auth-" + secrets.token_hex(16),
                available_at=now,
                now=now,
            )

        try:
            with self._auth_execution_context(cfg) as (auth_factory, auth_opener):
                meta_provider = YtDlpMetadataProvider(timeout_seconds=timeout)
                _bind_metadata_hooks(meta_provider, ydl_factory=auth_factory)

                def _make_sub_adapter() -> YtDlpSubtitleAdapter:
                    sub_adapter = YtDlpSubtitleAdapter(timeout_seconds=timeout)
                    _bind_subtitle_hooks(
                        sub_adapter,
                        ydl_factory=auth_factory,
                        opener=auth_opener,
                    )
                    return sub_adapter

                auth_deps = replace(
                    runtime._dependencies,
                    metadata_provider=meta_provider,
                    subtitle_adapter_factory=_make_sub_adapter,
                )
                auth_runtime = RuntimeOpsCls(
                    config=runtime._config,
                    project_root=runtime._root,
                    dependencies=auth_deps,
                    repository=runtime._repository,
                )
                auth_runtime.ingest_source_to_transcript(source_id, limit=1)
        except Exception as err:  # noqa: BLE001 — mapped via closed classification
            return self._classify_and_record_auth_failure(
                runtime, video_id, err, usage_id=usage_id
            )

        timed = runtime._repository.get_verified_timed_transcript(video_id=video_id)
        job = runtime._repository.latest_content_job(video_id)
        if (
            timed is not None
            and (job is None or job.status.value not in {"PENDING", "RUNNING", "RETRY_PENDING", "FAILED_FINAL"})
        ):
            if runtime._repository.current_local_summary_pointer(video_id) is None:
                ExtractiveSummaryService(
                    runtime._repository,
                    runtime._data_root,
                ).create(video_id, now=datetime.now(UTC))
            self._finalize_attempt_slot(usage_id, video_id=video_id, outcome="SUCCEEDED")
            return None

        return self._classify_and_record_auth_failure(
            runtime, video_id, None, usage_id=usage_id
        )

    def _classify_and_record_auth_failure(
        self,
        runtime: RuntimeOperations,
        video_id: str,
        err: BaseException | None,
        *,
        usage_id: str | None = None,
    ) -> str:
        app_err = getattr(err, "error", None) if err is not None else None
        raw_code = getattr(getattr(app_err, "code", None), "value", None)
        raw_msg = str(getattr(app_err, "message", "") or ("" if err is None else str(err))).lower()

        if raw_code is None:
            job = runtime._repository.latest_content_job(video_id)
            if job is not None and job.status.value in {"PENDING", "RUNNING", "RETRY_PENDING", "FAILED_FINAL"}:
                raw_code = job.last_error_code
                raw_msg = (job.last_error_message or "").lower()

        def finish(outcome: str, *, open_circuit: bool = False) -> None:
            if usage_id is not None:
                self._finalize_attempt_slot(
                    usage_id,
                    video_id=video_id,
                    outcome=outcome,
                    open_circuit=open_circuit,
                )
            else:
                self._record_usage(
                    video_id=video_id, outcome=outcome, open_circuit=open_circuit
                )

        if raw_code == "RATE_LIMITED":
            finish("RATE_LIMITED", open_circuit=True)
            return "YOUTUBE_RATE_LIMITED"
        if raw_code == "PERMISSION_DENIED" or any(
            m in raw_msg for m in ("sign in", "not a bot", "authentication", "login_required", "401", "403")
        ):
            finish("AUTH_EXPIRED", open_circuit=True)
            return "YOUTUBE_AUTH_EXPIRED"
        if raw_code in {"TRANSIENT_NETWORK", "PROVIDER_UNAVAILABLE"}:
            finish("NETWORK_UNAVAILABLE")
            return "YOUTUBE_NETWORK_UNAVAILABLE"
        if raw_code == "CONTENT_UNAVAILABLE":
            if runtime._repository.get_video(video_id) is not None and (
                "no usable subtitle" in raw_msg or "transcription" in raw_msg
            ):
                finish("NO_CAPTIONS")
                return "YOUTUBE_NO_CAPTIONS"
            finish("CONTENT_UNAVAILABLE")
            return "YOUTUBE_CONTENT_UNAVAILABLE"
        if runtime._repository.get_video(video_id) is not None and runtime._repository.get_verified_timed_transcript(video_id=video_id) is None:
            finish("NO_CAPTIONS")
            return "YOUTUBE_NO_CAPTIONS"
        finish("IMPORT_FAILED")
        return "YOUTUBE_IMPORT_FAILED"


def _source_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


__all__: Sequence[str] = (
    "CIRCUIT_BREAK_MINUTES",
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_DAILY_LIMIT",
    "SUPPORTED_AUTH_BROWSERS",
    "WorkspaceYouTubeCookiesKeychainStore",
    "YouTubeAuthFallbackService",
    "validate_netscape_cookies_txt",
)
