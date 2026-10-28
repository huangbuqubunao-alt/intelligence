"""Non-authoritative schema43 allowlisted BigModel HTTP429 observations."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import SQLiteStateRepository

TABLE = 'distillation_zhipu_http429_observations'
CODES = frozenset({'1113','1302','1305','1308','1315'})


def _schema(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple((row[0], ''.join(row[1].split()).rstrip(';')) for row in connection.execute(
        "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL AND (tbl_name=? OR name LIKE 'zhipu_http429_%') ORDER BY name", (TABLE,)))


@lru_cache(maxsize=1)
def _expected_schema() -> tuple[tuple[str, str], ...]:
    from .state import SQLiteStateRepository
    with closing(sqlite3.connect(':memory:')) as expected:
        expected.executescript('CREATE TABLE distillation_execution_checkpoints(execution_id TEXT); CREATE TABLE source_run_video_executions(distillation_execution_id TEXT);')
        expected.executescript(next(m.sql for m in SQLiteStateRepository(Path(':memory:'))._load_migrations() if m.version == 43))
        return _schema(expected)


def verify_schema(connection: sqlite3.Connection) -> None:
    version = int(connection.execute('PRAGMA user_version').fetchone()[0])
    schema = _schema(connection)
    if version < 43:
        if schema:
            raise ValueError('HTTP429 observation lacks schema43 authority')
    elif schema != _expected_schema():
        raise ValueError('HTTP429 observation schema differs')


def read_code(connection: sqlite3.Connection, execution_id: str, *, repository: SQLiteStateRepository) -> str | None:
    from .state import _read_snapshot, _zhipu_audit_utc
    with _read_snapshot(connection):
        verify_schema(connection)
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) < 43:
            return None
        row = connection.execute(f'SELECT * FROM {TABLE} WHERE execution_id=?', (execution_id,)).fetchone()
        if row is None:
            return None
        checkpoint = connection.execute('SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?', (execution_id,)).fetchone()
        if checkpoint is None:
            raise ValueError('HTTP429 observation is orphaned')
        repository._validate_zhipu_execution(connection, checkpoint)
        usage = connection.execute('SELECT * FROM distillation_resource_usage WHERE execution_id=?', (execution_id,)).fetchone()
        consent = connection.execute('SELECT * FROM distillation_zhipu_cloud_authorizations WHERE execution_id=?', (execution_id,)).fetchone()
        failure = connection.execute('SELECT * FROM distillation_zhipu_cloud_response_failures WHERE execution_id=?', (execution_id,)).fetchone()
        if (consent is None or failure is None or usage is not None
            or (row['selected_provider'],row['selected_model']) != ('zhipu_bigmodel','glm-4.7-flash')
            or (checkpoint['selected_provider'],checkpoint['selected_model']) != ('zhipu_bigmodel','glm-4.7-flash')
            or checkpoint['status'] != 'REJECTED_OUTPUT' or type(checkpoint['invocation_count']) is not int or checkpoint['invocation_count'] != 1
            or checkpoint['intelligence_id'] is not None or checkpoint['revision_id'] is not None
            or type(row['http_status_code']) is not int or row['http_status_code'] != 429 or row['error_code'] not in CODES
            or type(failure['http_status_code']) is not int or failure['http_status_code'] != 429 or failure['outcome'] != 'CLOUD_HTTP_ERROR'
            or failure['actual_provider'] != 'zhipu_bigmodel' or failure['actual_model'] is not None
            or any(failure[key] is not None for key in ('input_tokens','output_tokens','cost_microunits','duration_ms'))
            or row['observed_at'] != checkpoint['updated_at'] or row['observed_at'] != failure['received_at']):
            raise ValueError('HTTP429 observation binding differs')
        repository._validate_zhipu_consent_row(consent, checkpoint)
        _zhipu_audit_utc(row['observed_at'])
        return str(row['error_code'])


def verify_database(connection: sqlite3.Connection, *, repository: SQLiteStateRepository) -> None:
    from .state import _read_snapshot
    with _read_snapshot(connection):
        verify_schema(connection)
        if int(connection.execute('PRAGMA user_version').fetchone()[0]) < 43:
            return
        for row in connection.execute(f'SELECT execution_id FROM {TABLE}').fetchall():
            if read_code(connection, row[0], repository=repository) is None:
                raise ValueError('HTTP429 observation is orphaned')
