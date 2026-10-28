"""Narrow schema43 proof of a public BigModel wait that has not invoked a model."""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .cloud_audit import ZHIPU_AUTHORIZATIONS, ZHIPU_FAILURES, ZHIPU_PAIR
from .distillation_cancellation import BINDINGS

if TYPE_CHECKING:
    from .state import SQLiteStateRepository

TABLE = 'distillation_cloud_waiting_model_cancellations'
OUTCOME = 'CANCELLED_BEFORE_CLOUD_MODEL_INVOCATION'
BUDGETS = frozenset({'ADMITTED', 'PUBLIC_DIAGNOSTIC_ANTICIPATED_FREE_MAX_ONE'})
OUTCOMES = frozenset({'MODEL_UNAVAILABLE_BEFORE_TRANSPORT', 'CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH'})


def has_table(connection: sqlite3.Connection) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone() is not None


def _schema(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple((row[0], ''.join(row[1].split()).rstrip(';')) for row in connection.execute(
        "SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL AND (tbl_name=? OR name LIKE 'cloud_wait_%') ORDER BY name", (TABLE,)))


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
            raise ValueError('cloud cancellation has no schema43 authority')
    elif schema != _expected_schema():
        raise ValueError('cloud cancellation schema differs')


def verify_wait(connection: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None) -> None:
    from .distillation import (
        BigModelGlm47FlashBoundEvidenceDistillationTransport,
        BigModelGlm47FlashDistillationTransport,
        BigModelGlm47FlashGroundingV2DistillationTransport,
        PersonalizedDistillationService,
    )
    from .state import (
        EvidenceLineageKind,
        SQLiteStateRepository,
        _read_snapshot,
        _zhipu_audit_utc,
    )
    repo = repository or SQLiteStateRepository(Path(':memory:'))
    with _read_snapshot(connection):
        verify_schema(connection)
        if not has_table(connection):
            raise ValueError('cloud cancellation needs schema43')
        current = connection.execute('SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?', (checkpoint['execution_id'],)).fetchone()
        if current is None or dict(current) != dict(checkpoint):
            raise ValueError('cloud cancellation checkpoint changed')
        usage = connection.execute('SELECT * FROM distillation_resource_usage WHERE execution_id=?', (checkpoint['execution_id'],)).fetchone()
        if ((checkpoint['selected_provider'], checkpoint['selected_model']) != ZHIPU_PAIR
            or checkpoint['status'] != 'WAITING_MODEL' or type(checkpoint['invocation_count']) is not int or checkpoint['invocation_count'] != 0
            or checkpoint['intelligence_id'] is not None or checkpoint['revision_id'] is not None
            or checkpoint['budget_state'] not in BUDGETS or usage is None
            or any(usage[key] != checkpoint[key] for key in BINDINGS if key != 'output_language')
            or usage['status'] != 'WAITING_MODEL' or type(usage['invocation_count']) is not int or usage['invocation_count'] != 0
            or usage['outcome'] not in OUTCOMES or usage['created_at'] != checkpoint['updated_at']
            or any(usage[key] is not None for key in ('intelligence_id','revision_id','actual_provider','actual_model','input_tokens','output_tokens','cost_microunits','duration_ms','http_status_code'))):
            raise ValueError('cloud wait lacks reliable zero-call accounting')
        repo._validate_zhipu_execution(connection, checkpoint)
        consent = connection.execute(f'SELECT * FROM {ZHIPU_AUTHORIZATIONS} WHERE execution_id=?', (checkpoint['execution_id'],)).fetchone()
        if consent is None:
            raise ValueError('cloud cancellation needs existing consent')
        repo._validate_zhipu_consent_row(consent, checkpoint)
        _zhipu_audit_utc(checkpoint['updated_at'])
        public = connection.execute("SELECT 1 FROM source_video_links link JOIN videos v USING(video_id) JOIN source_subscriptions s USING(source_id) WHERE link.source_id=? AND link.video_id=? AND s.provider='YOUTUBE' AND v.provider='YOUTUBE' AND v.availability='public'", (checkpoint['source_id'], checkpoint['video_id'])).fetchone()
        if public is None or re.fullmatch(r'local-[0-9a-f]{64}', checkpoint['video_id']):
            raise ValueError('cloud cancellation source is not public YouTube')
        if (checkpoint['use_case'] != PersonalizedDistillationService._RESERVATION_USE_CASE
            or (checkpoint['reason'] != PersonalizedDistillationService._RESERVATION_REASON
                and re.fullmatch(r'MANUAL_CONTENT:[A-Za-z0-9._:-]{1,80}', checkpoint['reason']) is None)):
            raise ValueError('cloud cancellation command is unknown')
        ids = repo._evidence_ids_for_lineages_in_snapshot(connection, checkpoint['video_id'], lineage_kinds=(EvidenceLineageKind.ORIGINAL_TRANSCRIPT,))
        if not 1 <= len(ids) <= 20 or len(set(ids)) != len(ids):
            raise ValueError('cloud cancellation canonical Evidence is incomplete')
        for evidence_id in ids:
            text = repo._resolve_verified_evidence_text_in_transaction(connection, evidence_id)
            if text is None or text.video_id != checkpoint['video_id'] or text.locator_type != 'TIMED_MEDIA':
                raise ValueError('cloud cancellation Evidence is unverified')
        # The original consent hash is opaque authority: do not rebuild today's
        # interests/metadata into a fictional historical semantic input.
        identities = {PersonalizedDistillationService._reservation_id(
            source_id=checkpoint['source_id'], video_id=checkpoint['video_id'], evidence_ids=ids,
            selected_provider=ZHIPU_PAIR[0], selected_model=ZHIPU_PAIR[1],
            output_language=checkpoint['output_language'], verified_input_hash=consent['verified_input_hash'],
            cloud_prompt_version=profile._PROMPT_VERSION, cloud_request_profile_version=profile._REQUEST_PROFILE_VERSION,
            reason=checkpoint['reason']) for profile in (BigModelGlm47FlashDistillationTransport, BigModelGlm47FlashGroundingV2DistillationTransport, BigModelGlm47FlashBoundEvidenceDistillationTransport)}
        if checkpoint['execution_id'] not in identities:
            raise ValueError('cloud cancellation reservation profile cannot be proved')
        for table in ('distillation_no_new_intelligence_results','distillation_cloud_response_failures',
            'distillation_unidentified_http_responses','distillation_openai_unidentified_http_responses',
            'distillation_moonshot_unidentified_http_responses',ZHIPU_FAILURES,'distillation_waiting_model_cancellations'):
            if connection.execute(f'SELECT 1 FROM {table} WHERE execution_id=?', (checkpoint['execution_id'],)).fetchone():
                raise ValueError('cloud wait has conflicting authority')
        execution_id = checkpoint['execution_id']
        for table, column, identity in [('intelligences','intelligence_id',f'intelligence:distillation:{execution_id}'),
            ('intelligence_revisions','revision_id',f'revision:distillation:{execution_id}'),('distillation_cards','revision_id',f'revision:distillation:{execution_id}')]:
            if connection.execute(f'SELECT 1 FROM {table} WHERE {column}=?', (identity,)).fetchone():
                raise ValueError('cloud wait already has a result')
        if connection.execute("SELECT 1 FROM source_run_video_executions child LEFT JOIN source_runs run USING(run_id) WHERE child.distillation_execution_id=? AND (run.run_id IS NULL OR child.video_id!=? OR run.source_id!=? OR child.state!='WAITING' OR run.state!='NEEDS_ATTENTION' OR run.attention_reason!='MODEL_UNAVAILABLE') LIMIT 1", (execution_id, checkpoint['video_id'], checkpoint['source_id'])).fetchone():
            raise ValueError('cloud wait parent is active or inconsistent')


def read_cancellation(connection: sqlite3.Connection, checkpoint: sqlite3.Row, *, repository: SQLiteStateRepository | None = None) -> sqlite3.Row | None:
    from .state import _read_snapshot, _zhipu_audit_utc
    with _read_snapshot(connection):
        verify_schema(connection)
        if not has_table(connection):
            return None
        row = connection.execute(f'SELECT * FROM {TABLE} WHERE execution_id=?', (checkpoint['execution_id'],)).fetchone()
        if row is None:
            return None
        verify_wait(connection, checkpoint, repository=repository)
        if (any(row[key] != checkpoint[key] for key in BINDINGS)
            or row['checkpoint_updated_at'] != checkpoint['updated_at'] or row['outcome'] != OUTCOME
            or _zhipu_audit_utc(row['cancelled_at']) < _zhipu_audit_utc(checkpoint['updated_at'])):
            raise ValueError('cloud cancellation receipt binding differs')
        return cast(sqlite3.Row, row)


def verify_database(connection: sqlite3.Connection, *, repository: SQLiteStateRepository | None = None) -> None:
    from .state import _read_snapshot
    with _read_snapshot(connection):
        verify_schema(connection)
        if not has_table(connection):
            return
        for row in connection.execute(f'SELECT execution_id FROM {TABLE}').fetchall():
            checkpoint = connection.execute('SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?', (row[0],)).fetchone()
            if checkpoint is None or read_cancellation(connection, checkpoint, repository=repository) is None:
                raise ValueError('cloud cancellation receipt is orphaned')
