"""Append-only cancellation proof; neither model results nor checkpoint rewrites."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .cloud_audit import ZHIPU_FAILURES

if TYPE_CHECKING:
    from .state import SQLiteStateRepository

TABLE = "distillation_waiting_model_cancellations"
BINDINGS = (
    "execution_id", "source_id", "video_id", "reason", "use_case",
    "selected_provider", "selected_model", "output_language", "budget_state",
)


def has_table(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,),
    ).fetchone() is not None


def verify_wait(connection: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None) -> None:
    """Revalidate immutable zero-call authority, including on restored snapshots."""
    execution_id = checkpoint["execution_id"]
    from .long_distillation_persistence import (
        PROOFS,
        RECEIPTS,
        _proof_digest,
        is_long,
        require_identity,
        verify_execution,
    )
    if is_long(execution_id):
        require_identity(execution_id)
        proof = connection.execute(f"SELECT * FROM {PROOFS} WHERE execution_id=?", (execution_id,)).fetchone()
        if proof is None or proof["proof_hash"] != _proof_digest(dict(proof)) or connection.execute(
            f"SELECT 1 FROM {RECEIPTS} WHERE execution_id=?", (execution_id,)).fetchone():
            raise ValueError("long cancellation input provenance differs")
        if repository is not None:
            verify_execution(repository, connection, execution_id)
    usage = connection.execute(
        "SELECT * FROM distillation_resource_usage WHERE execution_id=?", (execution_id,),
    ).fetchone()
    if (
        checkpoint["selected_provider"] != "ollama"
        or checkpoint["status"] != "WAITING_MODEL" or checkpoint["invocation_count"] != 0
        or checkpoint["intelligence_id"] is not None or checkpoint["revision_id"] is not None
        or checkpoint["budget_state"] not in {"RUNTIME_BUDGET_ADMITTED", "ADMITTED"}
        or usage is None
        or any(usage[key] != checkpoint[key] for key in BINDINGS if key != "output_language")
        or usage["status"] != "WAITING_MODEL" or usage["invocation_count"] != 0
        or usage["outcome"] != "MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
        or usage["created_at"] != checkpoint["updated_at"]
        or any(usage[key] is not None for key in (
            "intelligence_id", "revision_id", "actual_provider", "actual_model",
            "input_tokens", "output_tokens", "cost_microunits", "duration_ms", "http_status_code",
        ))
    ):
        raise ValueError("model wait has no safe zero-invocation proof")
    for table in (
        "distillation_no_new_intelligence_results", "distillation_cloud_response_failures",
        "distillation_unidentified_http_responses", "distillation_openai_unidentified_http_responses",
        "distillation_moonshot_unidentified_http_responses",
        *((ZHIPU_FAILURES,) if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (ZHIPU_FAILURES,)).fetchone() else ()),
    ):
        if connection.execute(f"SELECT 1 FROM {table} WHERE execution_id=?", (execution_id,)).fetchone():
            raise ValueError("model wait has conflicting execution authority")
    if connection.execute(
        "SELECT 1 FROM source_run_video_executions child JOIN source_runs run USING(run_id) "
        "WHERE child.distillation_execution_id=? AND (child.video_id!=? OR run.source_id!=? "
        "OR child.state!='WAITING' OR run.state!='NEEDS_ATTENTION' "
        "OR run.attention_reason!='MODEL_UNAVAILABLE') LIMIT 1",
        (execution_id, checkpoint["video_id"], checkpoint["source_id"]),
    ).fetchone():
        raise ValueError("model wait parent is still active or inconsistent")


def read_cancellation(connection: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None) -> sqlite3.Row | None:
    if not has_table(connection):
        return None
    cancellation = connection.execute(
        f"SELECT * FROM {TABLE} WHERE execution_id=?", (checkpoint["execution_id"],),
    ).fetchone()
    if cancellation is None:
        return None
    verify_wait(connection, checkpoint, repository=repository)
    if (
        any(cancellation[key] != checkpoint[key] for key in BINDINGS)
        or cancellation["checkpoint_updated_at"] != checkpoint["updated_at"]
        or cancellation["outcome"] != "CANCELLED_BEFORE_MODEL_INVOCATION"
    ):
        raise ValueError("model wait cancellation is inconsistent")
    cancelled_at = datetime.fromisoformat(cancellation["cancelled_at"])
    updated_at = datetime.fromisoformat(checkpoint["updated_at"])
    if cancelled_at.utcoffset() is None or updated_at.utcoffset() is None or cancelled_at < updated_at:
        raise ValueError("model wait cancellation predates its checkpoint")
    return cast(sqlite3.Row, cancellation)


def _schema(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple(
        (row[0], "".join(row[1].split()).rstrip(";"))
        for row in connection.execute(
            "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL "
            "AND (tbl_name=? OR name LIKE 'waiting_model_%') ORDER BY name", (TABLE,),
        )
    )


@lru_cache(maxsize=8)
def _expected_schema(version: int) -> tuple[tuple[str, str], ...]:
    from .state import SQLiteStateRepository

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("PRAGMA legacy_alter_table=ON")
        for migration in SQLiteStateRepository(Path(":memory:"))._load_migrations():
            if migration.version <= version:
                connection.executescript(migration.sql)
        return _schema(connection)
    finally:
        connection.close()


def verify_database(connection: sqlite3.Connection) -> None:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version < 37:
        if _schema(connection):
            raise ValueError("legacy database has unversioned cancellation authority")
        return
    if _schema(connection) != _expected_schema(version):
        raise ValueError("model wait cancellation schema is incompatible")
    for row in connection.execute(f"SELECT execution_id FROM {TABLE}"):
        checkpoint = connection.execute(
            "SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (row[0],),
        ).fetchone()
        if checkpoint is None or read_cancellation(connection, checkpoint) is None:
            raise ValueError("model wait cancellation lacks its checkpoint")
