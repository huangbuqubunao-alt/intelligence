"""One public English diagnostic. Preparation never resolves a key or calls wire.

Only Root may execute after independent source AND concrete-package approval.
No production qualification, billing guarantee, retry, or alternate case.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from youtube_intel.distillation import (
    BigModelGlm47FlashDistillationTransport as Adapter,
)
from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCommand,
    KnownCloudDistillationResponseError,
    PersonalizedDistillationService,
    _bigmodel_chat_completions_http_transport,
    _bigmodel_request_bytes,
    _BigModelWireResponse,
    verified_distillation_input_projection,
)
from youtube_intel.model_settings import MacOSBigModelQACredentialStore
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.state import SQLiteStateRepository

PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
SOURCE = Path('/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/bigmodel-public-diagnostic-20261028')
PACKAGE = PROJECT / '.var/bigmodel-public-first-case'
ATTEMPT = PROJECT / '.var/bigmodel-public-first-case.attempt.json'
CORPUS = PROJECT / 'docs/validation/end-to-end-user-readiness/INTELLIGENCE_REAL_CORPUS_V2.json'
PRICE_SHA = '8b8c1f41835842f9f8dd316486ec2a3f34353d5e9d42eeb08a7b42876e5f1886'
VIDEO = 'QoXRfTb7ves'
CASE = 'real-deepthink-en'
MANUAL = 'free-public-diagnostic-case-1'
PRODUCER = 'cloud_preview_writer'
PAIR = ('zhipu_bigmodel', 'glm-4.7-flash')
THOUGHT = re.compile(r'<\s*/?\s*(?:think|analysis|reasoning)\b|<\|(?:analysis|thinking)|PRIVATE_REASONING_MARKER', re.I)


class Refused(ValueError):
    def __init__(self) -> None:
        super().__init__('public diagnostic refused; preserve package and attempt')


def require(condition: object) -> None:
    if not condition:
        raise Refused()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> Any:
    require(not path.is_symlink() and path.stat().st_size <= 16 * 1024 * 1024)
    return json.loads(path.read_bytes())


def write_once(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def paths_safe(root: Path) -> None:
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)))
    require(not any(p.is_symlink() for p in root.rglob('*')))


def data_manifest(root: Path) -> list[dict[str, object]]:
    paths_safe(root)
    return [{'path': str(p.relative_to(root)), 'size': p.stat().st_size, 'sha256': sha(p.read_bytes())}
        for p in sorted(root.rglob('*')) if p.is_file()]


def sql_snapshot(root: Path, execution_id: str | None = None) -> dict[str, Any]:
    with sqlite3.connect((root / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        tables = {}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [r[1] for r in db.execute('PRAGMA table_info(' + quoted + ')')]
            rows = []
            for row in db.execute('SELECT * FROM ' + quoted):
                if execution_id and name in {'distillation_execution_checkpoints', 'distillation_zhipu_cloud_authorizations'}:
                    if row[columns.index('execution_id')] == execution_id:
                        continue
                rows.append(json.dumps([{'bytes_hex': v.hex()} if isinstance(v, bytes) else v for v in row],
                    ensure_ascii=False, separators=(',', ':')))
            tables[name] = {'columns': columns, 'rows': sorted(rows)}
        require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)] and not db.execute('PRAGMA foreign_key_check').fetchall())
        schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        return {'tables': tables, 'schema': schema}


def code_hashes() -> dict[str, str]:
    files = [*PROJECT.joinpath('src').rglob('*.py'), *PROJECT.joinpath('src/youtube_intel/migrations').glob('*.sql'), SCRIPT, CORPUS]
    return {str(p.relative_to(PROJECT)): sha(p.read_bytes()) for p in sorted(files)}


class ReadOnlyRepository(SQLiteStateRepository):
    def _connect(self, *, read_only: bool = True) -> sqlite3.Connection:
        return super()._connect(read_only=True)


def never(*args: object) -> Any:
    raise Refused()


def denied_wire(request: Mapping[str, object], credential: str, timeout_seconds: float, max_retries: int) -> _BigModelWireResponse:
    raise Refused()


def context(root: Path) -> tuple[Any, Any, Any]:
    """Pure production prospective builder on a read-only connection."""
    case = next(c for c in read(CORPUS)['cases'] if c['id'] == CASE)
    repo = ReadOnlyRepository(root / 'state.sqlite3')
    repo.bind_source_storage(root / 'data')
    timed = repo.get_verified_timed_transcript(video_id=VIDEO)
    if timed is None:
        raise Refused()
    require([{'start_ms': c.start_ms, 'end_ms': c.end_ms, 'text': c.text} for c in timed.cues] == case['timed_segments'])
    artifact = repo.get_artifact(timed.canonical_artifact_id)
    if artifact is None or artifact.content_hash != case['canonical_sha256']:
        raise Refused()
    require(sha((root / 'data' / artifact.relative_path).read_bytes()) == case['canonical_sha256'])
    source = next(s for s in repo.list_source_subscriptions() if s.video_id == VIDEO)
    require(source.provider == 'YOUTUBE' and source.canonical_url == case['public_source_url'])
    adapter = Adapter(authorization=CloudDistillationAuthorization(), credential_resolver=never, wire_transport=denied_wire)
    service = PersonalizedDistillationService(repo, SourcePolicyApplicationService(repo, now=lambda: datetime.now(UTC)),
        adapter, type('NoBudget', (), {'check': never})(), now=lambda: datetime.now(UTC), output_language_for_video=lambda _: 'en')
    ids = repo.list_canonical_coverage_evidence_ids(VIDEO)
    require(0 < len(ids) <= 20)
    command, value = service._prospective_cloud_command(source_id=source.source_id, video_id=VIDEO,
        evidence_ids=ids, manual_command_id=MANUAL)
    require(value.personalization == () and value.source_focus_rules == tuple(case['focus_rules'])
        and value.source_ignore_rules == () and value.distillation_style == 'BALANCED'
        and (value.selected_provider, value.selected_model) == PAIR and value.content_provider == 'YOUTUBE')
    request = adapter._request(value)
    return command, value, request


def summary(root: Path) -> dict[str, object]:
    with sqlite3.connect((root / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        pointer = db.execute('SELECT * FROM current_content_summaries WHERE video_id=?', (VIDEO,)).fetchone()
        require(pointer is not None)
        artifact = db.execute('SELECT * FROM artifacts WHERE artifact_id=?', (pointer['analysis_artifact_id'],)).fetchone()
        require(artifact is not None and artifact['storage_root'] == 'DATA')
        path = root / 'data' / artifact['relative_path']
        require(path.resolve().is_relative_to((root / 'data').resolve()) and sha(path.read_bytes()) == artifact['content_hash'])
        return {'sent_to_model': False, 'pointer': dict(pointer), 'artifact': dict(artifact), 'published_summary': read(path)}


def pricing_day() -> str:
    return (datetime.now(UTC) + timedelta(hours=8)).date().isoformat()


def prepare() -> dict[str, object]:
    paths_safe(SOURCE)
    require(not PACKAGE.exists() and not ATTEMPT.exists())
    initial = read(SOURCE / 'initial.json')
    baseline = sql_snapshot(SOURCE)
    require(len(baseline['tables']) == 81)
    for name, entry in baseline['tables'].items():
        require(initial['tables'][name] == {'rows': len(entry['rows']), 'sha256': sha(json.dumps(entry['rows'], ensure_ascii=False, separators=(',', ':')).encode())})
    require(data_manifest(SOURCE / 'data') == initial['data'])
    price = (SOURCE / 'official-pricing-20261028.txt').read_bytes()
    require(sha(price) == PRICE_SHA)
    require(not baseline['tables']['preferences']['rows'])
    with sqlite3.connect((SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        require(set(db.execute('SELECT provider,video_id FROM videos')) == {('YOUTUBE', v) for v in ('0eMzc-WnBfQ', 'IwglW_hIL_g', VIDEO, 'aircAruvnKk')})
    PACKAGE.mkdir(parents=True, mode=0o700)
    with sqlite3.connect((SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as source:
        with sqlite3.connect(PACKAGE / 'state.sqlite3') as target:
            source.backup(target)
    shutil.copytree(SOURCE / 'data', PACKAGE / 'data')
    command, value, request = context(PACKAGE)
    require(sql_snapshot(PACKAGE) == baseline and sql_snapshot(SOURCE) == baseline)
    case = next(c for c in read(CORPUS)['cases'] if c['id'] == CASE)
    artifacts = {'baseline.json': canonical(baseline), 'request.json': canonical(request),
        'request-body.json': _bigmodel_request_bytes(request), 'verified-input.json': canonical(verified_distillation_input_projection(value)),
        'oracle.json': canonical(case), 'summary.json': canonical(summary(PACKAGE)), 'price.txt': price, 'provenance.json': (SOURCE / 'provenance.json').read_bytes()}
    for name, raw in artifacts.items():
        write_once(PACKAGE / name, raw)
    record = {'version': 'bigmodel-public-first-case-v1', 'case': CASE, 'producer': PRODUCER,
        'destination': str(PACKAGE.resolve()), 'source': str(SOURCE), 'video_id': VIDEO,
        'command': asdict(command), 'input_hash': value.semantic_hash, 'profile': Adapter.profile_projection(),
        'files': {name: sha(raw) for name, raw in artifacts.items()}, 'data': initial['data'], 'code': code_hashes(),
        'maximum_calls': 1, 'production_qualified': False, 'cost_status': 'UNKNOWN',
        'authorization': 'ANTICIPATED_FREE_EXACT_MODEL_ONLY', 'account_entitlement': 'UNKNOWN'}
    write_once(PACKAGE / 'prepared.json', canonical(record))
    return record


def validate(*, allow_case: bool = False) -> tuple[Any, Any, Any, Any]:
    paths_safe(PACKAGE)
    require(pricing_day() == '2026-10-28')
    p = read(PACKAGE / 'prepared.json')
    require(p['destination'] == str(PACKAGE.resolve()) and p['source'] == str(SOURCE)
        and p['case'] == CASE and p['video_id'] == VIDEO and type(p['maximum_calls']) is int and p['maximum_calls'] == 1
        and p['production_qualified'] is False and p['authorization'] == 'ANTICIPATED_FREE_EXACT_MODEL_ONLY'
        and p['cost_status'] == 'UNKNOWN' and p['code'] == code_hashes() and canonical(p['profile']) == canonical(Adapter.profile_projection()))
    require(set(p['files']) == {'baseline.json', 'request.json', 'request-body.json', 'verified-input.json', 'oracle.json', 'summary.json', 'price.txt', 'provenance.json'})
    require(p['files']['price.txt'] == PRICE_SHA)
    for name, digest in p['files'].items():
        require(name in {'baseline.json', 'request.json', 'request-body.json', 'verified-input.json', 'oracle.json', 'summary.json', 'price.txt', 'provenance.json'})
        require(sha((PACKAGE / name).read_bytes()) == digest)
    require(data_manifest(PACKAGE / 'data') == p['data'])
    require(canonical(sql_snapshot(PACKAGE, p['command']['execution_id'] if allow_case else None)) == canonical(read(PACKAGE / 'baseline.json')))
    command, value, request = context(PACKAGE)
    require(canonical(asdict(command)) == canonical(p['command']) and value.semantic_hash == p['input_hash'])
    require(canonical(request) == (PACKAGE / 'request.json').read_bytes()
        and _bigmodel_request_bytes(request) == (PACKAGE / 'request-body.json').read_bytes())
    return p, command, value, request


class Capture(Adapter):
    secrets: list[str]
    public_final: str | None = None
    raw_hash: str | None = None

    def generate(self, value: Any) -> Any:
        result = super().generate(value)
        if THOUGHT.search(result.raw) or any(secret and secret in result.raw for secret in self.secrets):
            raise KnownCloudDistillationResponseError(replace(result, raw=''), reason='CLOUD_FINAL_CONTENT_MISSING', http_status=200)
        self.public_final = result.raw
        return result


def execute(*, store: Any = None, wire: Any = None) -> dict[str, object]:
    """Python-only fake injection for tests; CLI has no credential/source arguments."""
    p, command, value, request = validate()
    review = read(PACKAGE / 'review.json')
    require(set(review) == {'decision', 'prepared_sha256', 'reviewer', 'review_commit', 'maximum_calls', 'cost_authorization'})
    require(review['decision'] == 'APPROVE_ONE_PUBLIC_DIAGNOSTIC' and review['prepared_sha256'] == sha((PACKAGE / 'prepared.json').read_bytes())
        and review['reviewer'] != PRODUCER and bool(review['reviewer']) and re.fullmatch('[0-9a-f]{40}', review['review_commit'])
        and type(review['maximum_calls']) is int and review['maximum_calls'] == 1 and review['cost_authorization'] == p['authorization'])
    write_once(ATTEMPT, canonical({'execution_id': command.execution_id, 'prepared_sha256': review['prepared_sha256'], 'state': 'ARMED_NOT_PROOF_OF_POST'}))
    secrets: list[str] = []
    repo = SQLiteStateRepository(PACKAGE / 'state.sqlite3')
    repo.bind_source_storage(PACKAGE / 'data')
    def credential() -> str:
        validate(allow_case=True)
        if not secrets:
            native = store if store is not None else MacOSBigModelQACredentialStore()
            secrets.append(native.get() or '')
        return secrets[0]
    def send(request: Mapping[str, object], credential: str, timeout_seconds: float, max_retries: int) -> _BigModelWireResponse:
        require(canonical(request) == (PACKAGE / "request.json").read_bytes() and timeout_seconds == 300.0 and max_retries == 0)
        response = (wire or _bigmodel_chat_completions_http_transport)(request, credential, timeout_seconds, max_retries)
        adapter.raw_hash = sha(response.body)
        return response
    adapter = Capture(authorization=CloudDistillationAuthorization(cloud_enabled=True, provider=PAIR[0], model=PAIR[1],
        credential_available=True, provider_available=True, qualification_input_hash=value.semantic_hash),
        credential_resolver=credential, wire_transport=send)
    adapter.secrets = secrets
    class Budget:
        def check(self, candidate: DistillationCommand) -> BudgetDecision:
            validate(allow_case=True)
            return BudgetDecision(candidate == command, 'PUBLIC_DIAGNOSTIC_ANTICIPATED_FREE_MAX_ONE')
    service = PersonalizedDistillationService(repo, SourcePolicyApplicationService(repo, now=lambda: datetime.now(UTC)), adapter,
        Budget(), now=lambda: datetime.now(UTC), output_language_for_video=lambda _: 'en')
    result: dict[str, object] = {'case': CASE, 'execution_id': command.execution_id, 'production_qualified': False,
        'semantic_acceptance': 'NOT_REVIEWED', 'actual_bill': 'UNKNOWN'}
    try:
        reservation = service.reserve_distillation_execution(source_id=command.source_id, video_id=VIDEO,
            evidence_ids=command.evidence_ids, manual_command_id=MANUAL)
        require(reservation.execution_id == command.execution_id)
        service.authorize_reserved_cloud_execution(command.execution_id, consent_kind='OWNER_QUALIFICATION')
        outcome = service.continue_qualification_reserved_distillation(command.execution_id)
        result.update(status=outcome.status.value, invocation_count=outcome.invocation_count)
    except Exception:
        record = repo.get_distillation_execution(command.execution_id)
        if record is not None and record.status == 'PENDING':
            repo.finish_distillation_without_admission(execution_id=command.execution_id, status='AMBIGUOUS',
                budget_state='UNKNOWN', outcome='TRANSPORT_OUTCOME_UNKNOWN', invocation_count=record.invocation_count,
                actual_provider=None, actual_model=None, input_tokens=None, output_tokens=None,
                cost_microunits=None, duration_ms=None, now=datetime.now(UTC))
        result['error'] = 'EXECUTION_FAILED_STOP'
    finally:
        secrets.clear()
    record = repo.get_distillation_execution(command.execution_id)
    usage = None if record is None else asdict(repo.get_distillation_resource_usage(command.execution_id))
    post = sql_snapshot(PACKAGE)
    baseline = read(PACKAGE / 'baseline.json')
    require(canonical(post['schema']) == canonical(baseline['schema']) and set(post['tables']) == set(baseline['tables']))
    for table, old in baseline['tables'].items():
        current = post['tables'][table]
        require(current['columns'] == old['columns'] and not (Counter(old['rows']) - Counter(current['rows'])))
        for extra in (Counter(current['rows']) - Counter(old['rows'])).elements():
            row = dict(zip(current['columns'], json.loads(extra), strict=True))
            if table in {'distillation_execution_checkpoints', 'distillation_zhipu_cloud_authorizations', 'distillation_resource_usage', 'distillation_zhipu_cloud_response_failures', 'distillation_no_new_intelligence_results'}:
                require(row.get('execution_id') == command.execution_id)
            elif table == 'intelligences':
                require(record is not None and row.get('intelligence_id') == record.intelligence_id)
            elif table in {'intelligence_revisions', 'intelligence_revision_evidence', 'intelligence_state_history', 'distillation_cards'}:
                require(record is not None and row.get('revision_id') == record.revision_id)
            elif table == 'dependency_edges':
                require(record is not None and row.get('dependent_revision_id') == record.revision_id)
            else:
                raise Refused()
    require(data_manifest(PACKAGE / 'data') == p['data'])
    result.update(usage=usage, public_final=adapter.public_final, opaque_response_sha256=adapter.raw_hash,
        diagnostic='POSITIVE_AWAITING_INDEPENDENT_REVIEW' if result.get('status') == 'SUCCEEDED' else 'FAIL_STOP')
    write_once(PACKAGE / 'result.json', json.dumps(result, ensure_ascii=False, sort_keys=True, default=lambda x: x.isoformat()).encode())
    return result


def main() -> None:
    # Never echo arbitrary argv (an accidentally supplied secret must not enter
    # argparse's unknown-argument diagnostics or a provider/config selector).
    if len(sys.argv) != 2 or sys.argv[1] not in {'prepare', 'execute'}:
        print('Use exactly prepare or execute; no credential or path arguments.')
        raise SystemExit(2)
    action = sys.argv[1]
    try:
        result = prepare() if action == 'prepare' else execute()
        print(json.dumps({'action': action, 'case': CASE, 'status': result.get('diagnostic', 'PREPARED'), 'production_qualified': False}))
        if result.get('diagnostic') == 'FAIL_STOP':
            raise SystemExit(1)
    except Exception:
        print(json.dumps({'case': CASE, 'status': 'REFUSED_STOP', 'production_qualified': False}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
