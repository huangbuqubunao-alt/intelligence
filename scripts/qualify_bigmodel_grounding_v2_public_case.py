"""Fixed public v2 capsule; Root-only max-one execution after separate review.

Run from the project root with python -m scripts.qualify_bigmodel_grounding_v2_public_case.
Preparation never creates application state or resolves credentials.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.qualify_bigmodel_public_first_case import (
    Capture,
    ReadOnlyRepository,
    Refused,
    canonical,
    data_manifest,
    denied_wire,
    never,
    paths_safe,
    pricing_day,
    read,
    require,
    sha,
    sql_snapshot,
    write_once,
)
from youtube_intel.distillation import (
    BigModelGlm47FlashGroundingV2DistillationTransport as Adapter,
)
from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCommand,
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
PACKAGE = PROJECT / '.var/bigmodel-grounding-v2-public-case'
ATTEMPT = PROJECT / '.var/bigmodel-grounding-v2-public-case.attempt.json'
ORACLE = PROJECT / 'docs/validation/end-to-end-user-readiness/UNSEEN_PUBLIC_ORACLE_V1.json'
ORACLE_SHA = '6760fd0da95e220e8599c585a11afee9ca7c0c71cd7737291ad03ce3b1ff9cc2'
PRICE_SHA = '8b8c1f41835842f9f8dd316486ec2a3f34353d5e9d42eeb08a7b42876e5f1886'
CASE, VIDEO = 'unseen-deepmind-interactive-coding-en', 'IwglW_hIL_g'
MANUAL, PRODUCER = 'free-public-grounding-v2-case-1', 'cloud_preview_writer'
PAIR = ('zhipu_bigmodel', 'glm-4.7-flash')
TASK = 'TASK-READINESS-GROUNDING-V2-PUBLIC-CAPSULE'
FILES = {'baseline.json', 'request.json', 'request-body.json', 'verified-input.json',
    'oracle.json', 'source.json', 'summary.json', 'price.txt', 'provenance.json'}


class CaptureV2(Capture, Adapter):
    """Reuse the accepted pre-admission privacy guard over the explicit v2 MRO."""


def code_hashes() -> dict[str, str]:
    files = [*PROJECT.joinpath('src').rglob('*.py'), *PROJECT.joinpath('src/youtube_intel/migrations').glob('*.sql'),
        SCRIPT, SCRIPT.with_name('qualify_bigmodel_public_first_case.py'), ORACLE, PROJECT / 'pyproject.toml']
    files += [p for p in (PROJECT / 'uv.lock', PROJECT / 'requirements.lock') if p.is_file()]
    return {str(p.relative_to(PROJECT)): sha(p.read_bytes()) for p in sorted(files)}


def context(root: Path) -> tuple[Any, Any, Any, Any, bytes]:
    oracle = read(ORACLE)
    require(sha(ORACLE.read_bytes()) == ORACLE_SHA)
    require(oracle['case_id'] == CASE and oracle['source']['video_id'] == VIDEO)
    repo = ReadOnlyRepository(root / 'state.sqlite3')
    repo.bind_source_storage(root / 'data')
    timed = repo.get_verified_timed_transcript(video_id=VIDEO)
    if timed is None:
        raise Refused()
    cues = [{'cue_index': c.cue_index, 'start_ms': c.start_ms, 'end_ms': c.end_ms, 'text': c.text} for c in timed.cues]
    require(len(cues) == 104 and cues == oracle['timed_segments'])
    require(timed.timed_transcript_id == oracle['source']['timed_transcript_id']
        and timed.timed_transcript_hash == oracle['source']['timed_transcript_hash'])
    ids = repo.list_canonical_coverage_evidence_ids(VIDEO)
    require(len(ids) == 5 and set(ids) == {item['evidence_id'] for item in oracle['canonical_evidence']})
    with sqlite3.connect((root / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        source = dict(db.execute('SELECT * FROM source_subscriptions WHERE source_id=?', (oracle['source']['source_id'],)).fetchone())
        video = dict(db.execute('SELECT * FROM videos WHERE video_id=?', (VIDEO,)).fetchone())
        pointer = dict(db.execute('SELECT * FROM current_content_summaries WHERE video_id=?', (VIDEO,)).fetchone())
        artifact = dict(db.execute('SELECT * FROM artifacts WHERE artifact_id=?', (pointer['analysis_artifact_id'],)).fetchone())
        evidence = []
        for item in oracle['canonical_evidence']:
            text = repo.resolve_verified_evidence_text(item['evidence_id'])
            if text is None:
                raise Refused()
            binding = db.execute('SELECT start_cue_index,end_cue_index FROM evidence_text_bindings WHERE evidence_id=?', (item['evidence_id'],)).fetchone()
            actual = {**asdict(text), 'start_cue_index': binding[0], 'end_cue_index': binding[1]}
            require(actual == item)
            evidence.append(actual)
    require(source['provider'] == video['provider'] == 'YOUTUBE' and source['video_id'] == VIDEO
        and source['canonical_url'] == oracle['source']['public_url'] and video['title'] == oracle['source']['title'])
    require(source['source_type'] == oracle['source']['source_type']
        and source['processing_policy'] == oracle['source']['source_processing_policy']
        and video['channel_name'] == oracle['source']['publisher']
        and video['description'] == oracle['source']['description']
        and video['duration_seconds'] == oracle['source']['metadata_duration_seconds']
        and video['availability'] == oracle['source']['availability']
        and datetime.fromisoformat(video['published_at']) == datetime.fromisoformat(oracle['source']['published_at']))
    require(pointer == oracle['actual_summary']['pointer'] and artifact == oracle['actual_summary']['artifact'])
    summary_path = root / 'data' / artifact['relative_path']
    require(summary_path.resolve().is_relative_to((root / 'data').resolve()))
    summary = summary_path.read_bytes()
    require(sha(summary) == oracle['actual_summary']['published_file_sha256'])
    canonical_path = root / 'data' / oracle['source']['canonical_file_path']
    require(canonical_path.resolve().is_relative_to((root / 'data').resolve())
        and timed.canonical_artifact_id == oracle['source']['canonical_artifact_id']
        and sha(canonical_path.read_bytes()) == oracle['source']['canonical_file_sha256'])
    policy = SourcePolicyApplicationService(repo, now=lambda: datetime.now(UTC))
    effective = policy.effective_policy(source['source_id'])
    require(effective.global_revision_id == oracle['original_context']['global_policy_revision_id']
        and effective.source_policy_revision_id == oracle['original_context']['source_policy_revision_id'])
    adapter = Adapter(authorization=CloudDistillationAuthorization(), credential_resolver=never, wire_transport=denied_wire)
    service = PersonalizedDistillationService(repo, policy, adapter, type('NoBudget', (), {'check': never})(),
        now=lambda: datetime.now(UTC), output_language_for_video=lambda _: 'en')
    command, value = service._prospective_cloud_command(source_id=source['source_id'], video_id=VIDEO, evidence_ids=ids, manual_command_id=MANUAL)
    original = oracle['original_context']
    require(value.personalization == () and value.source_focus_rules == tuple(original['focus_rules'])
        and value.source_ignore_rules == () and value.distillation_style == original['distillation_style']
        and value.output_language == 'en' and value.content_provider == 'YOUTUBE'
        and (value.selected_provider, value.selected_model) == PAIR)
    snapshot = {'source': source, 'video': video, 'timed_segments': cues, 'canonical_evidence': evidence,
        'summary_pointer': pointer, 'summary_artifact': artifact, 'summary_sent_to_model': False}
    return command, value, adapter._request(value), snapshot, summary


def prepare() -> dict[str, object]:
    require(pricing_day() == '2026-10-28' and not PACKAGE.exists() and not ATTEMPT.exists())
    paths_safe(SOURCE)
    initial, baseline = read(SOURCE / 'initial.json'), sql_snapshot(SOURCE)
    require(len(baseline['tables']) == 81 and not baseline['tables']['preferences']['rows'])
    for name, entry in baseline['tables'].items():
        require(initial['tables'][name] == {'rows': len(entry['rows']), 'sha256': sha(json.dumps(entry['rows'], ensure_ascii=False, separators=(',', ':')).encode())})
    data = data_manifest(SOURCE / 'data')
    require(data == initial['data'] == read(ORACLE)['read_only_evidence']['data_manifest'] and len(data) == 19)
    with sqlite3.connect((SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        require(db.execute('PRAGMA user_version').fetchone() == (42,))
        require(not db.execute('SELECT 1 FROM distillation_execution_checkpoints WHERE video_id=?', (VIDEO,)).fetchone())
        require(set(db.execute('SELECT provider,video_id FROM videos')) == {('YOUTUBE', v) for v in ('0eMzc-WnBfQ', VIDEO, 'QoXRfTb7ves', 'aircAruvnKk')})
    price = (SOURCE / 'official-pricing-20261028.txt').read_bytes()
    require(sha(price) == PRICE_SHA)
    command, value, request, source, summary = context(SOURCE)
    PACKAGE.mkdir(parents=True, mode=0o700)
    with sqlite3.connect((SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as origin:
        with sqlite3.connect(PACKAGE / 'state.sqlite3') as target:
            origin.backup(target)
    shutil.copytree(SOURCE / 'data', PACKAGE / 'data')
    require(sql_snapshot(PACKAGE) == baseline == sql_snapshot(SOURCE))
    artifacts = {'baseline.json': canonical(baseline), 'source.json': canonical(source), 'summary.json': summary,
        'request.json': canonical(request), 'request-body.json': _bigmodel_request_bytes(request),
        'verified-input.json': canonical(verified_distillation_input_projection(value)), 'oracle.json': ORACLE.read_bytes(),
        'price.txt': price, 'provenance.json': (SOURCE / 'provenance.json').read_bytes()}
    for name, raw in artifacts.items():
        write_once(PACKAGE / name, raw)
    record = {'version': 'bigmodel-grounding-v2-public-capsule-v1', 'task': TASK, 'case': CASE, 'producer': PRODUCER,
        'destination': str(PACKAGE.resolve()), 'source': str(SOURCE), 'video_id': VIDEO, 'manual_id': MANUAL,
        'command': asdict(command), 'input_hash': value.semantic_hash, 'profile': Adapter.profile_projection(),
        'files': {name: sha(raw) for name, raw in artifacts.items()}, 'data': data, 'code': code_hashes(),
        'python': sys.version, 'sqlite': sqlite3.sqlite_version, 'maximum_calls': 1, 'production_qualified': False,
        'authorization': 'ANTICIPATED_FREE_EXACT_MODEL_ONLY', 'actual_bill': 'UNKNOWN', 'account_entitlement': 'UNKNOWN'}
    write_once(PACKAGE / 'prepared.json', canonical(record))
    return record


def validate(*, allow_case: bool = False) -> tuple[Any, Any, Any, Any]:
    paths_safe(PACKAGE)
    require(pricing_day() == '2026-10-28')
    p = read(PACKAGE / 'prepared.json')
    require(p['task'] == TASK and p['case'] == CASE and p['producer'] == PRODUCER and p['video_id'] == VIDEO
        and p['manual_id'] == MANUAL and p['source'] == str(SOURCE) and p['destination'] == str(PACKAGE.resolve())
        and p['production_qualified'] is False and type(p['maximum_calls']) is int and p['maximum_calls'] == 1
        and p['authorization'] == 'ANTICIPATED_FREE_EXACT_MODEL_ONLY' and p['actual_bill'] == p['account_entitlement'] == 'UNKNOWN'
        and p['code'] == code_hashes() and p['python'] == sys.version and p['sqlite'] == sqlite3.sqlite_version
        and canonical(p['profile']) == canonical(Adapter.profile_projection()) and set(p['files']) == FILES
        and p['files']['oracle.json'] == ORACLE_SHA and p['files']['price.txt'] == PRICE_SHA)
    for name, digest in p['files'].items():
        require(name in FILES and sha((PACKAGE / name).read_bytes()) == digest)
    with sqlite3.connect((PACKAGE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        require(db.execute('PRAGMA user_version').fetchone() == (42,))
    require(data_manifest(PACKAGE / 'data') == p['data'])
    require(canonical(sql_snapshot(PACKAGE, p['command']['execution_id'] if allow_case else None)) == canonical(read(PACKAGE / 'baseline.json')))
    command, value, request, source, summary = context(PACKAGE)
    require(canonical(asdict(command)) == canonical(p['command']) and value.semantic_hash == p['input_hash']
        and canonical(source) == (PACKAGE / 'source.json').read_bytes() and summary == (PACKAGE / 'summary.json').read_bytes()
        and canonical(verified_distillation_input_projection(value)) == (PACKAGE / 'verified-input.json').read_bytes()
        and canonical(request) == (PACKAGE / 'request.json').read_bytes() and _bigmodel_request_bytes(request) == (PACKAGE / 'request-body.json').read_bytes())
    return p, command, value, request


def execute(*, store: Any = None, wire: Any = None) -> dict[str, object]:
    p, command, value, _ = validate()
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
            secrets.append((store if store is not None else MacOSBigModelQACredentialStore()).get() or '')
        return secrets[0]
    def send(request: Mapping[str, object], credential: str, timeout_seconds: float, max_retries: int) -> _BigModelWireResponse:
        validate(allow_case=True)
        require(canonical(request) == (PACKAGE / 'request.json').read_bytes() and timeout_seconds == 300 and max_retries == 0)
        response = (wire or _bigmodel_chat_completions_http_transport)(request, credential, timeout_seconds, max_retries)
        adapter.raw_hash = sha(response.body)
        return response
    adapter = CaptureV2(authorization=CloudDistillationAuthorization(cloud_enabled=True, provider=PAIR[0], model=PAIR[1],
        credential_available=True, provider_available=True, qualification_input_hash=value.semantic_hash), credential_resolver=credential, wire_transport=send)
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
        reservation = service.reserve_distillation_execution(source_id=command.source_id, video_id=VIDEO, evidence_ids=command.evidence_ids, manual_command_id=MANUAL)
        require(reservation.execution_id == command.execution_id)
        service.authorize_reserved_cloud_execution(command.execution_id, consent_kind='OWNER_QUALIFICATION')
        outcome = service.continue_qualification_reserved_distillation(command.execution_id)
        result.update(status=outcome.status.value, invocation_count=outcome.invocation_count)
    except Exception:
        record = repo.get_distillation_execution(command.execution_id)
        if record is not None and record.status == 'PENDING':
            repo.finish_distillation_without_admission(execution_id=command.execution_id, status='AMBIGUOUS', budget_state='UNKNOWN',
                outcome='TRANSPORT_OUTCOME_UNKNOWN', invocation_count=record.invocation_count, actual_provider=None, actual_model=None,
                input_tokens=None, output_tokens=None, cost_microunits=None, duration_ms=None, now=datetime.now(UTC))
        result['error'] = 'EXECUTION_FAILED_STOP'
    finally:
        secrets.clear()
    record = repo.get_distillation_execution(command.execution_id)
    post, baseline = sql_snapshot(PACKAGE), read(PACKAGE / 'baseline.json')
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
    result.update(usage=None if record is None else asdict(repo.get_distillation_resource_usage(command.execution_id)),
        public_final=adapter.public_final, opaque_response_sha256=adapter.raw_hash,
        diagnostic='POSITIVE_AWAITING_INDEPENDENT_REVIEW' if result.get('status') == 'SUCCEEDED' else 'FAIL_STOP')
    write_once(PACKAGE / 'result.json', json.dumps(result, ensure_ascii=False, sort_keys=True, default=lambda x: x.isoformat()).encode())
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in {'prepare', 'execute'}:
        print('Use exactly prepare or execute; no credential or path arguments.')
        raise SystemExit(2)
    try:
        output = prepare() if sys.argv[1] == 'prepare' else execute()
        print(json.dumps({'case': CASE, 'status': output.get('diagnostic', 'PREPARED'), 'production_qualified': False}))
        if output.get('diagnostic') == 'FAIL_STOP':
            raise SystemExit(1)
    except Exception:
        print('REFUSED_STOP; preserve capsule and attempt.')
        raise SystemExit(1) from None
