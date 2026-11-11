"""v5 judgment qualification controller; prepare/check are NOT consent or qualification.

DIRECT reuse of the r4 bounded controller's guarded execution core (ordinary
composition, exact proof, finite transport, owner claim, admission, receipts).
Intentional differences, all fixed BEFORE any v5 call:

* Inputs: the frozen v4-r2 package (same Source snapshots, complete Summaries,
  refs, focus and oracle). v5 proofs are re-assembled from each case's frozen
  command/capture and must equal the ordinary review of an offline clone.
* Prior fee history is a read-only, SHA-pinned snapshot of the stopped v4-r2
  control (7 real calls + 1 unsent hold, 8,608,798 microCNY held, bill UNKNOWN).
  Nothing in older controls is modified, released or re-derived.
* Order: IwglW (most room for a positive judgment) first, then aircAruvnKk,
  then the four synthetic controls. Stop on any technical/unknown/semantic
  failure, and also when an IwglW case returns NO_NEW (the positive-capability
  hypothesis is then falsified for that language and must be re-diagnosed).
* Only Root writes grant.json (after an explicit user approval) and per-case
  semantic decisions bound to an independent review. No retries, no output repair.
"""
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
import sqlite3
import subprocess
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel import system_synthesis_persistence as p
from youtube_intel import system_synthesis_profile as profile
from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    PersonalizedDistillationService,
    _moonshot_chat_completions_http_transport,
    _MoonshotWireResponse,
)
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.synthesis_runtime import MoonshotJudgmentSynthesisTransport
from youtube_intel.system_synthesis_qualification import JUDGMENT_CASE_LANGUAGES

_spec = importlib.util.spec_from_file_location('_judgment_bounded_core', Path(__file__).with_name('bounded_synthesis_trial.py'))
assert _spec is not None and _spec.loader is not None
core: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)  # definitions only
inputs = core.inputs
require, encoded, sha, read, parsed = core.require, core.encoded, core.sha, core.read, core.parsed
directory, once, replace_ledger, strings = core.directory, core.once, core.replace_ledger, core.strings

REPO = Path(__file__).resolve().parents[2]
PACKAGE = core.V4_R2_PACKAGE
PACKAGE_MANIFEST_SHA = '4f399f0d9e709200b00a75a3763400b7d963029058c6b1e512a6f82ea09ccdc2'
ORACLE_SHA = '0b6dbae640f06539660d5c112069d6af7a210fbff68ed52ee9a486caaf77e29d'
ADDENDUM = REPO / 'docs/validation/antigravity-readiness-20261112/V5_ORACLE_ADDENDUM_2026_11_12.md'
CONTROL = REPO / '.var/judgment-v5-control-20261112'
RUNS = REPO / '.var/judgment-v5-runs-20261112'
ORDER = tuple(JUDGMENT_CASE_LANGUAGES)
PARENT_CONTROL = core.V4_R2_CONTROL
PARENT_PINS = {
    'anchor.json': 'bee299fcc15512b83f37e63e168ac385d26205c8f90b6215b31dba20dd7805bd',
    'approval-skeleton.json': '617a5133399ccdc49a9bde8f8e28ffd33ae14d07d838b79103b65858e517b9d0',
    'attempt-1.json': '654a1e921159ec64a48d78125a235ca9354f353cbfaac9d597c052769376139b',
    'grant.json': '9642356e24820164ccf5a6ad63214a234a07ca195157d8299a95603b59f5fda7',
    'ledger.json': 'b45ddea5c6c19a63a27934e8125f60aedfcac7491da8ca0d511a6e83249ba75a',
    'lock': '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
    'public-aircAruvnKk-en.final.json': 'a07d0f4f189ddcff49cb85b597223139eef6cedf1f52fef247c56c2080ba9929',
    'public-aircAruvnKk-en.result.json': '53df574a574577cca7a16bd66ab3ec2dd7d9e813fbdcbad5ddf6365bf25557e0',
    'public-aircAruvnKk-en.semantic.json': 'd7d0feeec006aac7a472256c5726832e898ab6f68adcd20833a99eca25232962'}
PARENT_HISTORY = {'known_real_model_calls': 7, 'unsent_hold_slots': 1, 'held_microcny': 8608798,
    'actual_bill': 'UNKNOWN', 'holds_released': False}
LIMITS = {'runner_new_calls': 8, 'optional_gui_calls': 2, 'max_new_calls': 10,
    'per_call_microcny': 1900000, 'gui_held_microcny': 3698492, 'new_total_microcny': 15000000}
PURPOSE = 'ROOT_RECORDED_V5_JUDGMENT_QUALIFICATION'
QACredentialStore = core.QACredentialStore
Wire = Callable[[Mapping[str, object], str, float, int], _MoonshotWireResponse]


def parent_history() -> dict[str, Any]:
    """Read-only pin of the stopped v4-r2 control; never writes or releases anything."""
    directory(PARENT_CONTROL)
    names = {f.name for f in PARENT_CONTROL.iterdir()}
    require(names == set(PARENT_PINS), 'PARENT_CONTROL_FILES_CHANGED')
    for name, expected in PARENT_PINS.items():
        require(sha(read(PARENT_CONTROL / name, private=True)) == expected, 'PARENT_CONTROL_CHANGED')
    grant = parsed(PARENT_CONTROL / 'grant.json', private=True)
    attempt = parsed(PARENT_CONTROL / 'attempt-1.json', private=True)
    semantic = parsed(PARENT_CONTROL / 'public-aircAruvnKk-en.semantic.json', private=True)
    held = grant['limits']['historical_held_microcny'] + attempt['reserve_microcny']
    require(held == PARENT_HISTORY['held_microcny'] and grant['limits']['historical_calls'] == 7
        and semantic['decision'] == 'REJECT', 'PARENT_ACCOUNTING_DIFFERS')
    return {'control': str(PARENT_CONTROL), 'pins': dict(PARENT_PINS), **PARENT_HISTORY,
        'parent_semantic': 'REJECT', 'parent_status': 'STOPPED_NOT_CONTINUED'}


def code_hashes() -> dict[str, str]:
    result: dict[str, str] = core.code_hashes()
    for path in (Path(__file__).resolve(), ADDENDUM):
        result[str(path.relative_to(REPO))] = sha(read(path))
    return result


def case_rows() -> list[dict[str, Any]]:
    manifest = parsed(PACKAGE / 'manifest.json')
    by_case = {row['case']: row for row in manifest['cases']}
    rows = []
    for case in ORDER:
        row = by_case[case]
        frozen = parsed(PACKAGE / 'cases' / case / 'artifacts/prepared-proof.json')
        prepared = p._assemble(frozen['command'], frozen['capture'], profile_id=profile.JUDGMENT_PROFILE_ID)
        proof = p.loads(prepared.proof_json)
        rows.append({'case': case, 'execution_id': prepared.execution_id, 'proof_sha256': prepared.proof_sha256,
            'wire_sha256': proof['wire_sha256'], 'reserve_microcny': proof['reserve_microunits'],
            'language': row['language'], 'video_id': row['video_id'], 'source_identity': row['source_identity'],
            'source_refs_sha256': row['source_refs_sha256'], 'summary_sha256': row['summary_sha256'],
            'expected': row['expected'], 'frozen_v4_proof_sha256': row['proof_sha256']})
    return rows


def binding() -> dict[str, Any]:
    require(sha(read(PACKAGE / 'manifest.json')) == PACKAGE_MANIFEST_SHA, 'MANIFEST_CHANGED')
    manifest = parsed(PACKAGE / 'manifest.json')
    require(manifest['oracle_sha256'] == ORACLE_SHA and sha(read(PACKAGE / 'input-only-oracle.md')) == ORACLE_SHA, 'ORACLE_CHANGED')
    require(set(ORDER) == {c['case'] for c in manifest['cases']} and len(ORDER) == 8, 'CASE_SET_CHANGED')
    for row in manifest['cases']:
        artifacts = PACKAGE / 'cases' / row['case'] / 'artifacts'
        for name, expected in row['semantic_files'].items():
            raw = read(artifacts / name)
            require(sha(raw) == expected['sha256'] and len(raw) == expected['bytes'], 'ARTIFACT_CHANGED')
        require(inputs.inventory(PACKAGE / 'cases' / row['case'] / 'project')
            == parsed(artifacts / 'inventory-review-before-after.json')['before'], 'SOURCE_INVENTORY_CHANGED')
    cases = case_rows()
    require(all(0 < c['reserve_microcny'] <= LIMITS['per_call_microcny'] for c in cases), 'RESERVE_CHANGED')
    require(sum(c['reserve_microcny'] for c in cases) + LIMITS['gui_held_microcny'] <= LIMITS['new_total_microcny'],
        'BUDGET_CHANGED')
    return {'variant': 'v5-judgment-r1', 'package_manifest_sha256': PACKAGE_MANIFEST_SHA, 'oracle_sha256': ORACLE_SHA,
        'addendum_sha256': sha(read(ADDENDUM)), 'profile': profile.resolve_profile(profile.JUDGMENT_PROFILE_ID),
        'parent_history': parent_history(), 'source_hashes': code_hashes(),
        'source_revision': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
        'cases': cases, 'limits': dict(LIMITS)}


class JudgmentTrial:
    def __init__(self, *, control: Path = CONTROL, runs: Path = RUNS,
        _binding: Callable[[], dict[str, Any]] = binding) -> None:
        self.control, self.runs, self._binding = control, runs, _binding

    def proposal(self) -> dict[str, Any]:
        value = self._binding()
        return {'status': 'NOT_AUTHORIZED', 'binding': value, 'approval': {'approved': False, 'purpose': PURPOSE,
            'decision_id': '', 'expires_at': '', 'binding_sha256': sha(encoded(value)), 'limits': dict(LIMITS)}}

    def prepare(self) -> dict[str, Any]:
        report = self.proposal()
        value = report['binding']
        directory(self.control, create=True)
        anchor = self.control / 'anchor.json'
        if not anchor.exists():
            require(not any(self.control.iterdir()) and not self.runs.exists(), 'LEDGER_INITIALIZATION_REFUSED')
            once(anchor, {'binding_sha256': sha(encoded(value)), 'control_inode': self.control.stat().st_ino})
            once(self.control / 'ledger.json', {'binding_sha256': sha(encoded(value)), 'attempts': []})
            once(self.control / 'lock', {})
            once(self.control / 'approval-skeleton.json', report['approval'])
        with self.locked():
            self.ledger(value)
        return report

    @contextmanager
    def locked(self) -> Iterator[None]:
        directory(self.control)
        fds = []
        try:
            fd = os.open(PARENT_CONTROL / 'lock', os.O_RDONLY | os.O_NOFOLLOW)
            fds.append(fd)
            fcntl.flock(fd, fcntl.LOCK_SH)
            fd = os.open(self.control / 'lock', os.O_RDONLY | os.O_NOFOLLOW)
            fds.append(fd)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            for fd in reversed(fds):
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def ledger(self, value: dict[str, Any]) -> dict[str, Any]:
        try:
            anchor = parsed(self.control / 'anchor.json', private=True)
            ledger = parsed(self.control / 'ledger.json', private=True)
            require(anchor == {'binding_sha256': sha(encoded(value)), 'control_inode': self.control.stat().st_ino}
                and set(ledger) == {'binding_sha256', 'attempts'} and ledger['binding_sha256'] == sha(encoded(value))
                and isinstance(ledger['attempts'], list) and len(ledger['attempts']) <= 8, 'LEDGER_INVALID')
            for index, attempt in enumerate(ledger['attempts']):
                require(set(attempt) == {'case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'grant_sha256'}
                    and all(attempt[k] == value['cases'][index][k] for k in attempt if k != 'grant_sha256')
                    and parsed(self.control / f'attempt-{index + 1}.json', private=True) == attempt, 'LEDGER_ATTEMPT_INVALID')
            require({f.name for f in self.control.glob('attempt-*.json')}
                == {f'attempt-{i + 1}.json' for i in range(len(ledger['attempts']))}, 'ORPHANED_RESERVATION_STOP')
            return dict(ledger)
        except (ValueError, KeyError, TypeError):
            raise ValueError('LEDGER_MISSING_CORRUPT_OR_CHANGED') from None

    def grant(self, value: dict[str, Any]) -> str:
        try:
            grant = parsed(self.control / 'grant.json', private=True)
            require(set(grant) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
                and grant['approved'] is True and grant['purpose'] == PURPOSE
                and isinstance(grant['decision_id'], str) and 1 <= len(grant['decision_id']) <= 200
                and grant['binding_sha256'] == sha(encoded(value)) and encoded(grant['limits']) == encoded(LIMITS), 'GRANT_INVALID')
            expiry = datetime.fromisoformat(grant['expires_at'])
            require(expiry.tzinfo is not None and datetime.now(UTC) < expiry, 'GRANT_EXPIRED')
            return sha(read(self.control / 'grant.json', private=True))
        except (ValueError, KeyError, TypeError):
            raise ValueError('GRANT_REQUIRED_OR_INVALID') from None

    def previous(self, ledger: dict[str, Any], value: dict[str, Any], grant_sha: str) -> None:
        for attempt in ledger['attempts']:
            case = attempt['case']
            try:
                require(attempt['grant_sha256'] == grant_sha, 'GRANT_CHANGED_AFTER_ATTEMPT')
                result = parsed(self.control / (case + '.result.json'), private=True)
                decision = parsed(self.control / (case + '.semantic.json'), private=True)
                final = parsed(self.control / (case + '.final.json'), private=True)
                require(all(result[k] == attempt[k] for k in attempt) and result['invocation_count'] == 1
                    and result['receipt_sha256'] == sha(encoded(result['receipt']))
                    and final == {'raw_text': result['receipt']['raw_text'], 'sha256': result['final_sha256']}
                    and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT', 'PREVIOUS_RESULT_BINDING_DIFFERS')
                root = self.runs / case
                inputs.safe_tree(root)
                repository = SQLiteStateRepository(root / 'state.sqlite3')
                repository.bind_source_storage(root / 'data')
                with sqlite3.connect((root / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as connection:
                    connection.row_factory = sqlite3.Row
                    p.verify_database(repository, connection)
                    receipt = connection.execute('SELECT * FROM system_synthesis_result_receipts WHERE execution_id=?',
                        (attempt['execution_id'],)).fetchone()
                    require(receipt is not None and dict(receipt) == result['receipt'], 'PREVIOUS_DB_RECEIPT_DIFFERS')
                outcome = 'NO_NEW_INTELLIGENCE' if result['execution_status'] == 'SUCCEEDED_NO_NEW_INTELLIGENCE' else 'INTELLIGENCE'
                require(set(decision) == {'case', 'decision', 'reviewer', 'decision_id', 'result_sha256', 'receipt_sha256',
                        'oracle_sha256', 'addendum_sha256', 'outcome', 'independent_review_sha256'}
                    and decision['case'] == case and decision['decision'] == 'PASS' and decision['reviewer'] == 'ROOT'
                    and decision['result_sha256'] == sha(encoded(result)) and decision['receipt_sha256'] == result['receipt_sha256']
                    and decision['oracle_sha256'] == value['oracle_sha256'] and decision['addendum_sha256'] == value['addendum_sha256']
                    and decision['outcome'] == outcome and len(decision['independent_review_sha256']) == 64,
                    'ROOT_SEMANTIC_APPROVAL_REQUIRED')
                # Predeclared falsification stop: the best positive material yielded no judgment.
                require(not (case.startswith('public-IwglW_hIL_g') and outcome == 'NO_NEW_INTELLIGENCE'),
                    'POSITIVE_CAPABILITY_FALSIFIED_STOP')
            except Exception:
                raise ValueError('PREVIOUS_UNKNOWN_FAILED_OR_NOT_APPROVED_STOP') from None

    def execute(self, *, credential: Callable[[], str | None] | None = None, wire: Wire | None = None) -> dict[str, Any]:
        value = self._binding()
        with self.locked():
            grant_sha = self.grant(value)  # before clone/credentials/claim
            ledger = self.ledger(value)
            self.previous(ledger, value, grant_sha)
            index = len(ledger['attempts'])
            require(index < 8, 'EIGHT_CASES_EXHAUSTED')
            row = value['cases'][index]
            directory(self.runs, create=True)
            root = self.runs / row['case']
            source = PACKAGE / 'cases' / row['case'] / 'project'
            with inputs.offline():
                inputs.clone(source, root)
                require(inputs.inventory(root)['schema'] == 44, 'QUALIFICATION_REQUIRES_SCHEMA44')
                active = inputs.runtime(root, [datetime.now(UTC)])
                before = inputs.inventory(root)
                require(before == inputs.inventory(source), 'FACTORY_CHANGED_SOURCE')
                review, verified = inputs.ordinary_review(active, row['video_id'], row['case'],
                    profile_id=profile.JUDGMENT_PROFILE_ID)
                require(review['verified_input_hash'] == row['proof_sha256'] and review['execution_id'] == row['execution_id']
                    and inputs.inventory(root) == before, 'NORMAL_REVIEW_CHANGED')

            def authority_unchanged() -> bool:
                return (self.grant(value) == grant_sha and self.ledger(value) == ledger
                    and code_hashes() == value['source_hashes'])

            require(authority_unchanged(), 'SOURCE_CHANGED_BEFORE_RESERVATION')
            attempt = {k: row[k] for k in ('case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny')}
            attempt['grant_sha256'] = grant_sha
            ledger['attempts'].append(attempt)
            require(sum(a['reserve_microcny'] for a in ledger['attempts']) + LIMITS['gui_held_microcny']
                <= LIMITS['new_total_microcny'], 'CUMULATIVE_BUDGET_EXCEEDED')
            once(self.control / f'attempt-{index + 1}.json', attempt)
            replace_ledger(self.control / 'ledger.json', ledger)  # BEFORE key/claim/wire
            result: dict[str, Any] = {**attempt, 'status': 'UNKNOWN_STOP', 'actual_bill': 'UNKNOWN',
                'send_attempted': False, 'semantic': 'NOT_REVIEWED'}
            final: list[str] = []

            def resolve() -> str:
                require(authority_unchanged(), 'AUTHORITY_CHANGED')
                secret = (credential or QACredentialStore().get)()
                require(isinstance(secret, str) and secret and '\r' not in secret and '\n' not in secret, 'CREDENTIAL_UNAVAILABLE')
                assert isinstance(secret, str)
                require(authority_unchanged(), 'AUTHORITY_CHANGED_AFTER_KEY')
                return secret

            def guarded(request: Mapping[str, object], secret: str, timeout_seconds: float, max_retries: int) -> _MoonshotWireResponse:
                require(not result['send_attempted'] and max_retries == 0 and timeout_seconds == 300, 'RETRY_FORBIDDEN')
                require(authority_unchanged(), 'AUTHORITY_CHANGED')
                body = {k: v for k, v in request.items() if k not in {'endpoint_identity', 'max_retries'}}
                require(sha(encoded(body)) == row['wire_sha256'], 'WIRE_CHANGED')
                result['send_attempted'] = True
                response = (wire or _moonshot_chat_completions_http_transport)(request, secret, timeout_seconds, max_retries)
                if (response.http_status == 200 and response.finish_reason == 'stop' and response.stream_complete
                    and not response.malformed_envelope and not response.model_identity_invalid
                    and response.model_identity == profile.PAIR[1] and response.choices_count == 1
                    and response.message_exists and response.content_present and response.final_content):
                    require(secret not in response.final_content and len(response.final_content.encode()) <= 2_000_000,
                        'FINAL_REFUSED')
                    try:
                        decoded = json.loads(response.final_content)
                    except json.JSONDecodeError:
                        decoded = None  # preserve invalid authentic raw for rejection review
                    require(all(secret not in text for text in strings(decoded)), 'SECRET_IN_FINAL_REFUSED')
                    final.append(response.final_content)  # never inspect reasoning text
                return response

            try:
                original = active.application._cloud_synthesis_v5_service
                require(original is not None, 'SYNTHESIS_SERVICE_REQUIRED')
                authorization = CloudDistillationAuthorization(cloud_enabled=True, provider=profile.PAIR[0],
                    model=profile.PAIR[1], credential_available=True, provider_available=True,
                    qualification_input_hash=row['proof_sha256'], qualification_max_calls=1)
                transport = MoonshotJudgmentSynthesisTransport(authorization=authorization,
                    credential_resolver=resolve, wire_transport=guarded)
                service = PersonalizedDistillationService(active.repository, original._source_policy, transport,
                    original._budget, now=lambda: datetime.now(UTC), output_language_for_video=original._output_language_for_video)
                approved = service.preview_cloud_execution(source_id=review['source_id'], video_id=row['video_id'],
                    evidence_ids=tuple(review['evidence_ids']), manual_command_id='materialize-' + row['case'],
                    qualified=False, credential_available=False)
                readiness = approved['readiness']
                token = approved['review_hash']
                assert isinstance(readiness, dict) and isinstance(token, str)
                require(not readiness['can_confirm'] and approved['verified_input_hash'] == row['proof_sha256'],
                    'NORMAL_ELIGIBILITY_MUST_STAY_CLOSED')
                require(authority_unchanged(), 'AUTHORITY_CHANGED_BEFORE_CLAIM')
                outcome = service.confirm_synthesis_qualification(video_id=row['video_id'], execution_id=row['execution_id'],
                    review_hash=token, budget=p.SynthesisBudget('owner-trial:' + row['proof_sha256'], row['reserve_microcny'], 1))
                with active.repository._connect() as c:
                    p.verify_database(active.repository, c)
                    receipt_row = c.execute('SELECT * FROM system_synthesis_result_receipts WHERE execution_id=?', (row['execution_id'],)).fetchone()
                    receipt = dict(receipt_row) if receipt_row else None
                    auth = dict(c.execute('SELECT * FROM system_synthesis_cloud_authorizations WHERE execution_id=?', (row['execution_id'],)).fetchone())
                    usage = [dict(r) for r in c.execute('SELECT * FROM distillation_resource_usage WHERE execution_id=?', (row['execution_id'],))]
                after = inputs.inventory(root)
                require(after['data'] == before['data'] and all(after['tables'][k] == v
                    for k, v in before['tables'].items() if k not in core.ALLOWED_WRITES), 'SOURCE_PARENT_CHANGED')
                inputs.managed_parent_preflight(root)
                require(auth['consent_kind'] == 'OWNER_QUALIFICATION' and outcome.invocation_count == 1, 'QUALIFICATION_CLAIM_INVALID')
                technical = outcome.status.value in {'SUCCEEDED', 'SUCCEEDED_NO_NEW_INTELLIGENCE'}
                require(not technical or (receipt is not None and final and receipt['raw_text'] == final[0]), 'AUTHENTIC_RECEIPT_REQUIRED')
                backup = active.backup_restore.readiness()
                result.update(status='TECHNICAL_PASS_AWAITING_ROOT' if technical and backup['ready'] else 'TECHNICAL_FAILURE_STOP',
                    execution_status=outcome.status.value, invocation_count=outcome.invocation_count,
                    receipt=receipt, receipt_sha256=sha(encoded(receipt)), usage=usage, backup_readiness=backup,
                    source_parents_unchanged=True, qualification='CLOSED', normal_execution_enabled=False)
            except Exception:
                # Never serialize exception/provider/credential content or infer no charge.
                result['status'] = 'UNKNOWN_STOP'
            try:
                with active.repository._connect() as connection:
                    p.verify_database(active.repository, connection)
                    trace = {table: [dict(r) for r in connection.execute(f'SELECT * FROM {table} WHERE execution_id=?',
                        (row['execution_id'],))] for table in ('distillation_execution_checkpoints',
                        'system_synthesis_cloud_authorizations', 'system_synthesis_result_receipts',
                        'distillation_resource_usage', 'distillation_cloud_response_failures',
                        'distillation_no_new_intelligence_results')}
                    result.update(state_trace=trace, trace_status='VERIFIED_PERSISTED_STATE')
            except Exception:
                result.update(status='UNKNOWN_STOP', trace_status='STATE_UNAVAILABLE_OR_UNVERIFIED')
            if final:
                once(self.control / (row['case'] + '.final.json'), {'raw_text': final[0], 'sha256': sha(final[0].encode())})
                result['final_sha256'] = sha(final[0].encode())
            try:
                require(self._binding() == value, 'FROZEN_PACKAGE_CHANGED')
            except Exception:
                result['status'] = 'UNKNOWN_STOP'
            once(self.control / (row['case'] + '.result.json'), result)
            return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('describe', 'prepare', 'check', 'execute'), default='describe', nargs='?')
    args = parser.parse_args()
    trial = JudgmentTrial()
    if args.action == 'describe':
        report = trial.proposal()
    elif args.action == 'prepare':
        report = trial.prepare()
    elif args.action == 'check':
        value = binding()
        with trial.locked():
            report = {'status': 'CHECKED_NOT_AUTHORIZED', 'binding_sha256': sha(encoded(value)),
                'attempts': trial.ledger(value)['attempts']}
    else:
        report = trial.execute()
    print(profile.canonical(report))


if __name__ == '__main__':
    main()
