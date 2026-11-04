"""Finite, machine-local synthesis reservations that Backup cannot rewind.

This is a conservative reservation journal, not a bill, balance, eligibility
receipt or permission to execute. No secret or source text is stored here.
"""

from __future__ import annotations

import fcntl
import os
import re
import sqlite3
import stat
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from . import system_synthesis_persistence as synthesis
from . import system_synthesis_profile as profile
from .backup_restore import BackupRestoreService
from .source_authority import managed_directory
from .state import SQLiteStateRepository, StateStoreError, format_utc_datetime

MAX_MICROCNY = 10_000_000_000  # Explicit finite cumulative ceiling: 10,000 CNY.
MAX_CALLS = 1000
MAX_EVENTS = 5000
MAX_BYTES = 4 * 1024 * 1024
_HASH = re.compile(r"[0-9a-f]{64}")


class SpendingPolicyRejected(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def money(value: object) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,6})?", value):
        raise SpendingPolicyRejected("CLOUD_POLICY_INVALID")
    whole, _, fraction = value.partition(".")
    result = int(whole) * 1_000_000 + int(fraction.ljust(6, "0") or "0")
    if not 1 <= result <= MAX_MICROCNY:
        raise SpendingPolicyRejected("CLOUD_POLICY_INVALID")
    return result


def price_disclosure() -> dict[str, object]:
    descriptor = profile.resolve_profile(profile.PROFILE_ID)
    return {"profile_id": profile.PROFILE_ID, "provider": profile.PAIR[0], "model": profile.PAIR[1],
        "price_hash": profile.sha(profile.canonical(descriptor)), "price_date": descriptor["price_date"],
        "input_microcny_per_token_worst": descriptor["input_microcny_per_token_worst"],
        "output_microcny_per_token": descriptor["output_microcny_per_token"],
        "max_completion_tokens": descriptor["max_completion_tokens"], "currency": "CNY", "billing_guarantee": False}


def _valid_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return format_utc_datetime(datetime.fromisoformat(value.replace("Z", "+00:00"))) == value
    except (ValueError, TypeError):
        return False


class CloudSpendingPolicy:
    def __init__(self, repository: SQLiteStateRepository, backup: BackupRestoreService) -> None:
        self.repository = repository
        self.backup = backup
        self.control = backup.control_root.absolute()
        self.root = self.control / "cloud-spending"
        self.path = self.root / "journal.json"
        self.anchor = self.control / "cloud-spending-anchor.json"
        self.lock = self.control / "cloud-spending.lock"
        if (self.root.is_relative_to(backup.data_root) or backup.data_root.is_relative_to(self.root)
            or backup.database.is_relative_to(self.root)):
            raise SpendingPolicyRejected("CLOUD_JOURNAL_UNSAFE")
        self.binding = profile.sha(str(backup.database.absolute()) + "\0" + str(backup.data_root.absolute()))

    @staticmethod
    def _owned(metadata: os.stat_result, *, directory: bool = False) -> None:
        valid = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
        if not valid or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise SpendingPolicyRejected("CLOUD_JOURNAL_UNSAFE")

    def _read(self, root: Path, name: str) -> dict[str, Any]:
        with managed_directory(root) as directory:
            self._owned(os.fstat(directory), directory=True)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                self._owned(os.fstat(fd))
                if os.fstat(fd).st_size > MAX_BYTES:
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
                raw = os.read(fd, MAX_BYTES + 1)
                after = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if (after.st_dev, after.st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_UNSAFE")
            finally:
                os.close(fd)
        return synthesis.loads(raw.decode("utf-8"))

    def _write(self, root: Path, name: str, value: dict[str, Any]) -> None:
        raw = profile.canonical(value).encode()
        if len(raw) > MAX_BYTES:
            raise SpendingPolicyRejected("CLOUD_JOURNAL_FULL")
        with managed_directory(root) as directory:
            self._owned(os.fstat(directory), directory=True)
            try:
                self._owned(os.stat(name, dir_fd=directory, follow_symlinks=False))
            except FileNotFoundError:
                pass
            temporary = "." + uuid.uuid4().hex + ".tmp"
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)

    @contextmanager
    def _locked(self, *, write: bool) -> Iterator[None]:
        with self.backup.admission_lock(), managed_directory(self.control) as directory:
            self._owned(os.fstat(directory), directory=True)
            flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if write else 0)
            fd = os.open(self.lock.name, flags, 0o600, dir_fd=directory)
            try:
                self._owned(os.fstat(fd))
                fcntl.flock(fd, fcntl.LOCK_EX if write else fcntl.LOCK_SH)
                identity = os.stat(self.lock.name, dir_fd=directory, follow_symlinks=False)
                if (identity.st_dev, identity.st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_UNSAFE")
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def _normal_claims(self) -> list[dict[str, Any]]:
        with closing(self.repository._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM system_synthesis_cloud_authorizations WHERE consent_kind='USER_CONFIRMATION'").fetchall()
            for row in rows:
                synthesis.verify_execution(self.repository, connection, row["execution_id"])
            result = []
            for row in rows:
                proof = connection.execute("SELECT proof_json FROM system_synthesis_input_proofs WHERE execution_id=?", (row["execution_id"],)).fetchone()
                result.append({**dict(row), "wire_sha256": synthesis.loads(proof[0])["wire_sha256"]})
            return result

    def _load(self) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]], dict[str, Any] | None]:
        claims = self._normal_claims()
        if not self.anchor.exists() and not self.anchor.is_symlink():
            if self.root.exists() or self.root.is_symlink() or claims:
                raise SpendingPolicyRejected("CLOUD_JOURNAL_HISTORY_MISSING")
            return None, {}, None
        anchor = self._read(self.control, self.anchor.name)
        if (set(anchor) != {"version", "id", "binding"} or type(anchor["version"]) is not int or anchor["version"] != 1
            or not isinstance(anchor["id"], str) or re.fullmatch(r"[0-9a-f]{32}", anchor["id"]) is None
            or anchor["binding"] != self.binding):
            raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
        journal = self._read(self.root, self.path.name)
        if set(journal) != {"version", "id", "events"} or type(journal["version"]) is not int or journal["version"] != 1 or journal["id"] != anchor["id"]:
            raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
        events = journal["events"]
        if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS:
            raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
        entries: dict[str, dict[str, Any]] = {}
        policy = None
        previous = "0" * 64
        for index, event in enumerate(events, 1):
            if not isinstance(event, dict) or set(event) != {"sequence", "previous", "kind", "payload", "sha256"}:
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
            body = {k: v for k, v in event.items() if k != "sha256"}
            if type(event["sequence"]) is not int or event["sequence"] != index or event["previous"] != previous or profile.sha(profile.canonical(body)) != event["sha256"]:
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
            previous = event["sha256"]
            payload = event["payload"]
            if not isinstance(payload, dict):
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
            if event["kind"] == "POLICY":
                if (set(payload) != {"enabled", "total_microunits", "per_request_microunits", "max_calls", "price_hash"}
                    or type(payload["enabled"]) is not bool
                    or any(type(payload[k]) is not int for k in ("total_microunits", "per_request_microunits", "max_calls"))
                    or not 1 <= payload["per_request_microunits"] <= payload["total_microunits"] <= MAX_MICROCNY
                    or not 1 <= payload["max_calls"] <= MAX_CALLS or not isinstance(payload["price_hash"], str)
                    or _HASH.fullmatch(payload["price_hash"]) is None):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
                policy = payload
                held, count = self._totals(entries)
                if held > policy["total_microunits"] or count > policy["max_calls"]:
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
            elif event["kind"] == "RESERVE":
                if (set(payload) != {"execution_id", "proof_sha256", "wire_sha256", "price_hash", "amount", "created_at"}
                    or not isinstance(payload["execution_id"], str) or payload["execution_id"] in entries
                    or payload["execution_id"] != synthesis.PREFIX + payload["proof_sha256"]
                    or any(not isinstance(payload[k], str) or _HASH.fullmatch(payload[k]) is None
                        for k in ("proof_sha256", "wire_sha256", "price_hash"))
                    or type(payload["amount"]) is not int or not 1 <= payload["amount"] <= MAX_MICROCNY
                    or not _valid_time(payload["created_at"])):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
                held, count = self._totals(entries)
                if (policy is None or not policy["enabled"] or payload["price_hash"] != policy["price_hash"]
                    or payload["amount"] > policy["per_request_microunits"]
                    or held + payload["amount"] > policy["total_microunits"] or count + 1 > policy["max_calls"]):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
                entries[payload["execution_id"]] = {**payload, "held": True, "prior_held": held, "prior_count": count,
                    "budget_limit": policy["total_microunits"], "max_calls": policy["max_calls"]}
            elif event["kind"] == "ABORT":
                if (set(payload) != {"execution_id", "created_at", "reason"} or payload["reason"] != "VERIFIED_SYNCHRONOUS_PRECLAIM_FAILURE"
                    or not _valid_time(payload["created_at"]) or payload["execution_id"] not in entries or not entries[payload["execution_id"]]["held"]):
                    raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
                entries[payload["execution_id"]]["held"] = False
            else:
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
        for claim in claims:
            entry = entries.get(claim["execution_id"])
            if (entry is None or not entry["held"] or entry["proof_sha256"] != claim["verified_input_hash"]
                or entry["price_hash"] != claim["price_sha256"] or entry["amount"] != claim["reserve_microunits"]):
                raise SpendingPolicyRejected("CLOUD_JOURNAL_HISTORY_MISSING")
            if entry["wire_sha256"] != claim["wire_sha256"]:
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
            if (claim["budget_scope"] != "normal-cloud:" + journal["id"] + ":" + entry["proof_sha256"]
                or claim["prior_reserved_microunits"] != entry["prior_held"] or claim["prior_calls"] != entry["prior_count"]
                or claim["budget_limit_microunits"] != entry["budget_limit"] or claim["max_calls"] != entry["max_calls"]):
                raise SpendingPolicyRejected("CLOUD_JOURNAL_CORRUPT")
        return journal, entries, policy

    def _append(self, journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
        events = journal["events"]
        if len(events) >= MAX_EVENTS:
            raise SpendingPolicyRejected("CLOUD_JOURNAL_FULL")
        body = {"sequence": len(events) + 1, "previous": events[-1]["sha256"] if events else "0" * 64,
            "kind": kind, "payload": payload}
        events.append({**body, "sha256": profile.sha(profile.canonical(body))})
        self._write(self.root, self.path.name, journal)

    @staticmethod
    def _totals(entries: dict[str, dict[str, Any]]) -> tuple[int, int]:
        return sum(e["amount"] for e in entries.values() if e["held"]), sum(1 for e in entries.values() if e["held"])

    def _status(self, loaded: tuple[dict[str, Any] | None, dict[str, dict[str, Any]], dict[str, Any] | None]) -> dict[str, Any]:
        journal, entries, policy = loaded
        held, count = self._totals(entries)
        code = "CLOUD_SPENDING_POLICY_REQUIRED" if policy is None or not policy["enabled"] else (
            "CLOUD_PRICE_ACCEPTANCE_REQUIRED" if policy["price_hash"] != price_disclosure()["price_hash"] else None)
        return {"revision": 0 if journal is None else len(journal["events"]), "policy": policy,
            "policy_revision": None if journal is None else max(e["sequence"] for e in journal["events"] if e["kind"] == "POLICY"),
            "held_microunits": held, "held_requests": count, "consumed_execution_ids": len(entries),
            "remaining_microunits": 0 if policy is None else max(0, policy["total_microunits"] - held),
            "remaining_requests": 0 if policy is None else max(0, policy["max_calls"] - count),
            "actual_cost_status": "UNKNOWN", "price": price_disclosure(), "blocker": code,
            "currency": "CNY", "scope": "CUMULATIVE_NORMAL_SYNTHESIS_RESERVATIONS"}

    def status(self) -> dict[str, Any]:
        try:
            if not self.anchor.exists() and not self.anchor.is_symlink() and not self.root.exists() and not self.root.is_symlink():
                return self._status(self._load())  # Physically readonly virgin preview.
            with self._locked(write=False):
                return self._status(self._load())
        except (OSError, ValueError, StateStoreError, sqlite3.Error, KeyError, TypeError, RuntimeError) as error:
            code = error.code if isinstance(error, SpendingPolicyRejected) else "CLOUD_JOURNAL_UNAVAILABLE"
            return {"revision": None, "policy": None, "blocker": code, "price": price_disclosure(),
                "held_microunits": None, "held_requests": None, "actual_cost_status": "UNKNOWN", "currency": "CNY"}

    def update(self, *, expected_revision: object, enabled: object, total_cny: object, per_request_cny: object,
        max_calls: object, accept_price_hash: object, acknowledge: object) -> dict[str, Any]:
        total, per = money(total_cny), money(per_request_cny)
        if (type(expected_revision) is not int or expected_revision < 0 or type(enabled) is not bool
            or type(max_calls) is not int or not 1 <= max_calls <= MAX_CALLS or per > total
            or acknowledge is not True or accept_price_hash != price_disclosure()["price_hash"]):
            raise SpendingPolicyRejected("CLOUD_POLICY_INVALID")
        try:
            with self._locked(write=True):
                journal, entries, _ = self._load()
                revision = 0 if journal is None else len(journal["events"])
                if expected_revision != revision:
                    raise SpendingPolicyRejected("CLOUD_POLICY_CONFLICT")
                held, count = self._totals(entries)
                if total < held or max_calls < count:
                    raise SpendingPolicyRejected("CLOUD_POLICY_BELOW_HELD")
                if journal is None:
                    with managed_directory(self.root, create=True) as directory:
                        self._owned(os.fstat(directory), directory=True)
                    identity = uuid.uuid4().hex
                    self._write(self.control, self.anchor.name, {"version": 1, "id": identity, "binding": self.binding})
                    journal = {"version": 1, "id": identity, "events": []}
                self._append(journal, "POLICY", {"enabled": enabled, "total_microunits": total,
                    "per_request_microunits": per, "max_calls": max_calls, "price_hash": accept_price_hash})
                return self._status(self._load())
        except SpendingPolicyRejected:
            raise
        except (OSError, ValueError, StateStoreError, sqlite3.Error, KeyError, TypeError):
            raise SpendingPolicyRejected("CLOUD_JOURNAL_UNAVAILABLE") from None

    def preview(self, prepared: synthesis.PreparedSynthesis) -> dict[str, Any]:
        state = self.status()
        proof = synthesis.loads(prepared.proof_json)
        reserve = proof["reserve_microunits"]
        blocker = state["blocker"]
        if blocker is None:
            try:
                with self._locked(write=False):
                    _, entries, _ = self._load()
                if prepared.execution_id in entries:
                    blocker = "CLOUD_EXECUTION_REPLAY_BLOCKED"
                elif reserve > state["policy"]["per_request_microunits"]:
                    blocker = "CLOUD_PER_REQUEST_CAP_EXCEEDED"
                elif reserve > state["remaining_microunits"]:
                    blocker = "CLOUD_BUDGET_EXHAUSTED"
                elif state["remaining_requests"] < 1:
                    blocker = "CLOUD_REQUEST_COUNT_EXHAUSTED"
            except (OSError, ValueError, StateStoreError, sqlite3.Error):
                blocker = "CLOUD_JOURNAL_UNAVAILABLE"
        return {**state, "blocker": blocker, "reserve_microunits": reserve}

    def claim(self, prepared: synthesis.PreparedSynthesis, *, validate_current: Callable[[], None], now: datetime,
        expected_policy_revision: int | None) -> None:
        try:
            with self._locked(write=True):
                journal, entries, policy = self._load()
                if (journal is None or policy is None or not policy["enabled"]):
                    raise SpendingPolicyRejected("CLOUD_SPENDING_POLICY_REQUIRED")
                if expected_policy_revision != self._status((journal, entries, policy))["policy_revision"]:
                    raise SpendingPolicyRejected("CLOUD_POLICY_CHANGED_REVIEW_REQUIRED")
                if not self.backup.background_allowed:
                    raise SpendingPolicyRejected("CLOUD_EXECUTION_DISABLED")
                if policy["price_hash"] != price_disclosure()["price_hash"]:
                    raise SpendingPolicyRejected("CLOUD_PRICE_ACCEPTANCE_REQUIRED")
                synthesis.request_from_proof(prepared)
                proof = synthesis.loads(prepared.proof_json)
                amount = proof["reserve_microunits"]
                held, count = self._totals(entries)
                if prepared.execution_id in entries:
                    raise SpendingPolicyRejected("CLOUD_EXECUTION_REPLAY_BLOCKED")
                if amount > policy["per_request_microunits"]:
                    raise SpendingPolicyRejected("CLOUD_PER_REQUEST_CAP_EXCEEDED")
                if amount + held > policy["total_microunits"]:
                    raise SpendingPolicyRejected("CLOUD_BUDGET_EXHAUSTED")
                if count + 1 > policy["max_calls"]:
                    raise SpendingPolicyRejected("CLOUD_REQUEST_COUNT_EXHAUSTED")
                validate_current()
                self._append(journal, "RESERVE", {"execution_id": prepared.execution_id,
                    "proof_sha256": prepared.proof_sha256, "wire_sha256": proof["wire_sha256"],
                    "price_hash": policy["price_hash"], "amount": amount, "created_at": format_utc_datetime(now)})
                reserved = False
                try:
                    synthesis.reserve(self.repository, prepared, now=now)
                    reserved = True
                    synthesis.confirm_and_claim(self.repository, prepared,
                        budget=synthesis.SynthesisBudget("normal-cloud:" + journal["id"] + ":" + prepared.proof_sha256,
                            policy["total_microunits"], policy["max_calls"], held, count),
                        consent_kind="USER_CONFIRMATION", now=now)
                except Exception:
                    # This block contains no network. Only exact current-state
                    # proof can release this synchronous failed reservation.
                    with closing(self.repository._connect()) as c:
                        checkpoint = c.execute("SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (prepared.execution_id,)).fetchone()
                        auth = c.execute("SELECT 1 FROM system_synthesis_cloud_authorizations WHERE execution_id=?", (prepared.execution_id,)).fetchone()
                    if auth is None and (checkpoint is None or (reserved and checkpoint["status"] == "PENDING" and checkpoint["invocation_count"] == 0)):
                        if checkpoint is not None:
                            synthesis.abandon_unclaimed(self.repository, prepared.execution_id, now=now)
                        self._append(journal, "ABORT", {"execution_id": prepared.execution_id,
                            "created_at": format_utc_datetime(now), "reason": "VERIFIED_SYNCHRONOUS_PRECLAIM_FAILURE"})
                        raise SpendingPolicyRejected("CLOUD_PRECLAIM_ABORTED") from None
                    raise
        except SpendingPolicyRejected:
            raise
        except (OSError, ValueError, StateStoreError, sqlite3.Error, KeyError, TypeError, RuntimeError):
            raise SpendingPolicyRejected("CLOUD_JOURNAL_UNAVAILABLE") from None
