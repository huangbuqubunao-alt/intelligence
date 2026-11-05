"""Fixed r4 qualification controller; prepare is NOT consent or qualification.

DIRECT existing ordinary composition, proof, finite transport, owner claim and
admission. Only Root may record a new paid grant and semantic decisions. No
normal eligibility mutation, output repair, retries or GUI-smoke dispatch.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import sqlite3
import stat
import subprocess
import sys
import uuid
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
from youtube_intel.model_settings import MacOSKeychainCredentialStore
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.synthesis_runtime import MoonshotSystemSynthesisTransport

REPO = Path(__file__).resolve().parents[2]
PACKAGE = Path('/Users/hua/Documents/yia-worktrees/readiness-synthesis-input-materialization/.var/synthesis-input-materialization/prepared-20261105-r4')
MANIFEST_SHA = '01d7020ba1fe621a4b59d566e1b4816086463c0365ebffdb79807c5ecac1e621'
CONTROL = Path('/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/bounded-synthesis-trial-20261105')
RUNS = REPO / '.var/bounded-synthesis-trial-runs'
ORDER = ('public-aircAruvnKk-en', 'public-aircAruvnKk-zh-CN', 'public-IwglW_hIL_g-en',
    'public-IwglW_hIL_g-zh-CN', 'no-new-en', 'no-new-zh-CN', 'injection-en', 'injection-zh-CN')
LIMITS = {'historical_calls': 2, 'historical_held_microcny': 1943326, 'runner_new_calls': 8,
    'optional_gui_calls': 1, 'max_new_calls': 9, 'max_total_calls': 11, 'per_call_microcny': 1000000,
    'total_microcny': 9000000, 'runner_held_microcny': 5599830, 'gui_held_microcny': 969966,
    'prospective_total_microcny': 8513122}
ALLOWED_WRITES = frozenset({'system_synthesis_input_proofs', 'system_synthesis_cloud_authorizations',
    'system_synthesis_result_receipts', 'system_synthesis_wait_cancellations',
    'distillation_execution_checkpoints', 'distillation_resource_usage', 'distillation_cloud_response_failures',
    'distillation_no_new_intelligence_results', 'intelligences', 'intelligence_revisions',
    'intelligence_revision_evidence', 'intelligence_state_history', 'dependency_edges', 'distillation_cards'})
_spec = importlib.util.spec_from_file_location('_bounded_trial_input_helpers', Path(__file__).with_name('materialize_synthesis_inputs.py'))
assert _spec is not None and _spec.loader is not None
inputs: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inputs)  # definitions only; never materialize or acquire
Wire = Callable[[Mapping[str, object], str, float, int], _MoonshotWireResponse]


def require(ok: object, code: str) -> None:
    if not ok:
        raise ValueError(code)


def encoded(value: object) -> bytes:
    return profile.canonical(value).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def read(path: Path, *, private: bool = False) -> bytes:
    require(path.is_absolute() and not any(x.is_symlink() for x in (path, *path.parents)), 'UNSAFE_PATH')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise ValueError('MISSING_OR_UNSAFE_FILE') from None
    with os.fdopen(fd, 'rb') as file:
        st = os.fstat(file.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size <= 16 * 1024 * 1024, 'UNSAFE_FILE')
        if private:
            require(st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o600, 'PRIVATE_FILE_REQUIRED')
        return file.read()


def parsed(path: Path, *, private: bool = False) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    try:
        return json.loads(read(path, private=private), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('INVALID_JSON_NUMBER')))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError('INVALID_JSON') from None


def directory(path: Path, *, create: bool = False) -> None:
    require(path.is_absolute() and not any(x.is_symlink() for x in (path, *path.parents)), 'UNSAFE_DIRECTORY')
    if create and not path.exists():
        path.mkdir(parents=True, mode=0o700)
    st = path.stat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700, 'PRIVATE_DIRECTORY_REQUIRED')


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def once(path: Path, value: object) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(encoded(value))
        file.flush()
        os.fsync(file.fileno())
    sync_directory(path.parent)


def replace_ledger(path: Path, value: object) -> None:
    read(path, private=True)  # refuse absent/replaced/redirected journal
    temporary = path.with_name('.ledger-' + uuid.uuid4().hex)
    once(temporary, value)
    os.replace(temporary, path)
    sync_directory(path.parent)


def code_hashes() -> dict[str, str]:
    paths = [*sorted((REPO / 'src').rglob('*.py')), *sorted((REPO / 'src').rglob('*.sql')),
        Path(__file__).resolve(), Path(inputs.__file__).resolve(), REPO / 'config/settings.example.yaml',
        REPO / 'pyproject.toml', REPO / 'uv.lock']
    result = {str(path.relative_to(REPO)): sha(read(path)) for path in paths}
    for name, module in list(sys.modules.items()):
        if name == 'youtube_intel' or name.startswith('youtube_intel.'):
            location = getattr(module, '__file__', None)
            if location and location.endswith('.py'):
                path = Path(location).resolve()
                require(path.is_relative_to(REPO / 'src')
                    and result.get(str(path.relative_to(REPO))) == sha(read(path)), 'IMPORTED_SOURCE_DIFFERS')
    return result


def package_binding() -> dict[str, Any]:
    require(sha(read(PACKAGE / 'manifest.json')) == MANIFEST_SHA, 'MANIFEST_CHANGED')
    manifest = parsed(PACKAGE / 'manifest.json')
    require(manifest['status'] == 'PREPARED_NOT_AUTHORIZED' and manifest['qualification'] == 'CLOSED'
        and manifest['case_count'] == 8 and tuple(c['case'] for c in manifest['cases']) == ORDER, 'CASE_SET_CHANGED')
    require(sha(read(PACKAGE / 'input-only-oracle.md')) == manifest['oracle_sha256'], 'ORACLE_CHANGED')
    require(parsed(PACKAGE / 'immutable-profile.json') == profile.resolve_profile(profile.PROFILE_ID), 'PROFILE_CHANGED')
    require(sha(read(PACKAGE / 'source-code-inventory.json')) == manifest['source_code_inventory_sha256'], 'INPUT_SOURCE_INVENTORY_CHANGED')
    seed_before = parsed(PACKAGE / 'source-before.json')
    require(seed_before == parsed(PACKAGE / 'source-after.json') == inputs.inventory(inputs.SEED), 'SEED_CHANGED')
    for name, expected in manifest['official_supplement']['document_hashes'].items():
        require(sha(read(PACKAGE / 'official-supplement' / Path(name).name)) == expected, 'PRICE_DOCUMENT_CHANGED')
    cases = []
    for row in manifest['cases']:
        root = PACKAGE / 'cases' / row['case'] / 'project'
        artifacts = root.parent / 'artifacts'
        require(str(root) == row['data_root'] and str(artifacts) == row['artifacts'], 'CASE_PATH_CHANGED')
        for name, expected in row['semantic_files'].items():
            require(Path(name).name == name, 'ARTIFACT_PATH_INVALID')
            raw = read(artifacts / name)
            require(sha(raw) == expected['sha256'] and len(raw) == expected['bytes'], 'ARTIFACT_CHANGED')
        before = parsed(artifacts / 'inventory-review-before-after.json')['before']
        require(before['schema'] == 44 and inputs.inventory(root) == before, 'SOURCE_INVENTORY_CHANGED')
        inputs.managed_parent_preflight(root)
        proof = parsed(artifacts / 'prepared-proof.json')
        require(sha(encoded(proof)) == row['proof_sha256'] and proof['wire_sha256'] == row['wire_sha256']
            and sha(proof['capture']['summary_raw'].encode()) == row['summary_sha256']
            and sha(encoded(proof['capture']['source_refs'])) == row['source_refs_sha256']
            and proof['reserve_microunits'] == row['reserve_microcny']
            and proof['transport'] == profile.resolve_profile(profile.PROFILE_ID), 'PROOF_CHANGED')
        require(profile.canonical(parsed(artifacts / 'provider-body.json')) == proof['provider_wire'], 'BODY_CHANGED')
        p.request_from_proof(p.PreparedSynthesis(row['execution_id'], profile.canonical(proof), row['proof_sha256']))
        cases.append({key: row[key] for key in ('case', 'execution_id', 'proof_sha256', 'wire_sha256',
            'reserve_microcny', 'language', 'video_id', 'source_identity', 'source_refs_sha256', 'summary_sha256', 'expected')})
    require(sum(c['reserve_microcny'] for c in cases) == LIMITS['runner_held_microcny']
        and all(type(c['reserve_microcny']) is int and 0 < c['reserve_microcny'] <= 1000000 for c in cases), 'RESERVE_CHANGED')
    return {'manifest_sha256': MANIFEST_SHA, 'oracle_sha256': manifest['oracle_sha256'],
        'profile': profile.resolve_profile(profile.PROFILE_ID), 'source_hashes': code_hashes(),
        'seed_inventory_sha256': sha(encoded(seed_before)),
        'supplementary_price_documents': manifest['official_supplement'],
        'source_revision': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
        'cases': cases}


class QACredentialStore(MacOSKeychainCredentialStore):
    _service = b'com.huangbuqubunao.intelligence.qa.kimi-public-20261029'
    _account = b'api-key'


class Trial:
    def __init__(self, *, control: Path = CONTROL, runs: Path = RUNS) -> None:
        # Internal injection for isolated tests only. CLI offers no path/key/model overrides.
        self.control, self.runs = control, runs

    def prepare(self) -> dict[str, Any]:
        binding = package_binding()
        report = {'status': 'NOT_AUTHORIZED', 'binding': binding, 'limits': LIMITS,
            'approval': {'approved': False, 'purpose': 'ROOT_RECORDED_PAID_QUALIFICATION',
                'decision_id': '', 'expires_at': '', 'binding_sha256': sha(encoded(binding)),
                'limits': LIMITS}}
        directory(self.control, create=True)
        anchor, ledger = self.control / 'anchor.json', self.control / 'ledger.json'
        if not anchor.exists():
            require(not any(self.control.iterdir()), 'LEDGER_INITIALIZATION_REFUSED')
            once(anchor, {'binding_sha256': sha(encoded(binding)), 'control_inode': self.control.stat().st_ino,
                'control_device': self.control.stat().st_dev})
            once(ledger, {'binding_sha256': sha(encoded(binding)), 'attempts': []})
            once(self.control / 'lock', {})
            once(self.control / 'approval-skeleton.json', report['approval'])
        with self.locked():
            self.ledger(binding)
        return report

    @contextmanager
    def locked(self) -> Iterator[None]:
        directory(self.control)
        read(self.control / 'lock', private=True)
        fd = os.open(self.control / 'lock', os.O_RDONLY | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def ledger(self, binding: dict[str, Any]) -> dict[str, Any]:
        try:
            anchor = parsed(self.control / 'anchor.json', private=True)
            value = parsed(self.control / 'ledger.json', private=True)
            require(anchor == {'binding_sha256': sha(encoded(binding)), 'control_inode': self.control.stat().st_ino,
                'control_device': self.control.stat().st_dev}, 'LEDGER_ANCHOR_DIFFERS')
            require(set(value) == {'binding_sha256', 'attempts'} and value['binding_sha256'] == sha(encoded(binding))
                and isinstance(value['attempts'], list) and len(value['attempts']) <= 8, 'LEDGER_INVALID')
            for index, attempt in enumerate(value['attempts']):
                require(set(attempt) == {'case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'grant_sha256'}
                    and all(attempt[k] == binding['cases'][index][k] for k in attempt if k != 'grant_sha256')
                    and isinstance(attempt['grant_sha256'], str) and len(attempt['grant_sha256']) == 64, 'LEDGER_ATTEMPT_INVALID')
                require(parsed(self.control / f'attempt-{index + 1}.json', private=True) == attempt,
                    'IMMUTABLE_RESERVATION_DIFFERS')
            require({f.name for f in self.control.glob('attempt-*.json')}
                == {f'attempt-{i + 1}.json' for i in range(len(value['attempts']))}, 'ORPHANED_RESERVATION_STOP')
            return dict(value)
        except (ValueError, KeyError, TypeError):
            raise ValueError('LEDGER_MISSING_CORRUPT_OR_CHANGED') from None

    def grant(self, binding: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            value = parsed(self.control / 'grant.json', private=True)
            require(set(value) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
                and value['approved'] is True and value['purpose'] == 'ROOT_RECORDED_PAID_QUALIFICATION'
                and isinstance(value['decision_id'], str) and 1 <= len(value['decision_id']) <= 160
                and value['binding_sha256'] == sha(encoded(binding)) and value['limits'] == LIMITS
                and encoded(value['limits']) == encoded(LIMITS), 'GRANT_INVALID')
            expiry = datetime.fromisoformat(value['expires_at'])
            require(expiry.tzinfo is not None and datetime.now(UTC) < expiry, 'GRANT_EXPIRED')
            return value, sha(read(self.control / 'grant.json', private=True))
        except (ValueError, KeyError, TypeError):
            raise ValueError('GRANT_REQUIRED_OR_INVALID') from None

    def previous(self, ledger: dict[str, Any], binding: dict[str, Any], grant_sha: str) -> None:
        for attempt in ledger['attempts']:
            require(attempt['grant_sha256'] == grant_sha, 'GRANT_CHANGED_AFTER_ATTEMPT')
            case = attempt['case']
            try:
                result = parsed(self.control / (case + '.result.json'), private=True)
                decision = parsed(self.control / (case + '.semantic.json'), private=True)
                require(all(result[k] == attempt[k] for k in attempt)
                    and result['receipt_sha256'] == sha(encoded(result['receipt']))
                    and result['invocation_count'] == 1, 'PREVIOUS_RESULT_BINDING_DIFFERS')
                final = parsed(self.control / (case + '.final.json'), private=True)
                require(final == {'raw_text': result['receipt']['raw_text'], 'sha256': result['final_sha256']}
                    and sha(final['raw_text'].encode()) == final['sha256'], 'PREVIOUS_FINAL_DIFFERS')
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
                require(result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' and result['actual_bill'] == 'UNKNOWN'
                    and decision == {'case': case, 'decision': 'PASS', 'reviewer': 'ROOT',
                        'decision_id': decision['decision_id'], 'result_sha256': sha(encoded(result)),
                        'receipt_sha256': result['receipt_sha256'], 'oracle_sha256': binding['oracle_sha256']}
                    and isinstance(decision['decision_id'], str) and 1 <= len(decision['decision_id']) <= 160,
                    'ROOT_SEMANTIC_APPROVAL_REQUIRED')
            except Exception:
                raise ValueError('PREVIOUS_UNKNOWN_FAILED_OR_NOT_APPROVED_STOP') from None

    def execute(self, *, credential: Callable[[], str | None] | None = None, wire: Wire | None = None) -> dict[str, Any]:
        binding = package_binding()
        with self.locked():
            _, grant_sha = self.grant(binding)  # before clone/credentials/claim
            ledger = self.ledger(binding)
            self.previous(ledger, binding, grant_sha)
            index = len(ledger['attempts'])
            require(index < 8, 'EIGHT_CASES_EXHAUSTED_GUI_SLOT_NOT_EXECUTABLE')
            row = binding['cases'][index]
            directory(self.runs, create=True)
            root = self.runs / row['case']
            with inputs.offline():
                inputs.clone(PACKAGE / 'cases' / row['case'] / 'project', root)
                require(inputs.inventory(root)['schema'] == 44, 'QUALIFICATION_REQUIRES_SCHEMA44')
                active = inputs.runtime(root, [datetime.now(UTC)])
                before = inputs.inventory(root)
                require(before == inputs.inventory(PACKAGE / 'cases' / row['case'] / 'project'), 'FACTORY_CHANGED_SOURCE')
                review, value = inputs.ordinary_review(active, row['video_id'], row['case'])
                require(review['verified_input_hash'] == row['proof_sha256']
                    and review['execution_id'] == row['execution_id']
                    and value.input_json == profile.canonical(parsed(PACKAGE / 'cases' / row['case'] / 'artifacts/prepared-proof.json'))
                    and inputs.inventory(root) == before, 'NORMAL_REVIEW_CHANGED')
            self.grant(binding)
            require(code_hashes() == binding['source_hashes'], 'SOURCE_CHANGED_BEFORE_RESERVATION')
            attempt = {k: row[k] for k in ('case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny')}
            attempt['grant_sha256'] = grant_sha
            ledger['attempts'].append(attempt)
            require(LIMITS['historical_held_microcny'] + sum(a['reserve_microcny'] for a in ledger['attempts'])
                + LIMITS['gui_held_microcny'] <= LIMITS['total_microcny'], 'CUMULATIVE_BUDGET_EXCEEDED')
            # Immutable reservation detects journal rollback/truncation. A crash
            # between these writes is an orphaned hold and permanently blocks,
            # never evidence that the invocation was free or safe to replay.
            once(self.control / f'attempt-{index + 1}.json', attempt)
            replace_ledger(self.control / 'ledger.json', ledger)  # BEFORE key/claim/wire
            result: dict[str, Any] = {**attempt, 'status': 'UNKNOWN_STOP', 'actual_bill': 'UNKNOWN',
                'send_attempted': False, 'semantic': 'NOT_REVIEWED'}
            final: list[str] = []

            def resolve() -> str:
                require(self.grant(binding)[1] == grant_sha and self.ledger(binding) == ledger, 'AUTHORITY_CHANGED')
                secret = (credential or QACredentialStore().get)()
                require(isinstance(secret, str) and secret and '\r' not in secret and '\n' not in secret, 'CREDENTIAL_UNAVAILABLE')
                assert isinstance(secret, str)
                return secret

            def guarded(request: Mapping[str, object], credential: str, timeout_seconds: float, max_retries: int) -> _MoonshotWireResponse:
                require(not result['send_attempted'] and max_retries == 0 and timeout_seconds == 300, 'RETRY_FORBIDDEN')
                require(self.grant(binding)[1] == grant_sha and self.ledger(binding) == ledger
                    and code_hashes() == binding['source_hashes'], 'AUTHORITY_CHANGED')
                body = {k: v for k, v in request.items() if k not in {'endpoint_identity', 'max_retries'}}
                require(sha(encoded(body)) == row['wire_sha256'], 'WIRE_CHANGED')
                result['send_attempted'] = True
                response = (wire or _moonshot_chat_completions_http_transport)(request, credential, timeout_seconds, max_retries)
                if (response.http_status == 200 and response.finish_reason == 'stop' and response.stream_complete
                    and not response.malformed_envelope and not response.model_identity_invalid
                    and response.model_identity == profile.PAIR[1] and response.choices_count == 1
                    and response.message_exists and response.content_present and response.final_content):
                    require(credential not in response.final_content, 'SECRET_IN_FINAL_REFUSED')
                    require(len(response.final_content.encode()) <= 2_000_000, 'FINAL_TOO_LARGE')
                    try:
                        decoded = json.loads(response.final_content)
                    except json.JSONDecodeError:
                        decoded = None  # preserve invalid authentic raw for rejection review
                    require(all(credential not in text for text in strings(decoded)), 'SECRET_IN_FINAL_REFUSED')
                    final.append(response.final_content)  # never inspect reasoning text
                return response

            try:
                original = active.application._cloud_synthesis_service
                require(original is not None, 'SYNTHESIS_SERVICE_REQUIRED')
                authorization = CloudDistillationAuthorization(cloud_enabled=True, provider=profile.PAIR[0],
                    model=profile.PAIR[1], credential_available=True, provider_available=True,
                    qualification_input_hash=row['proof_sha256'], qualification_max_calls=1)
                transport = MoonshotSystemSynthesisTransport(authorization=authorization,
                    credential_resolver=resolve, wire_transport=guarded)
                service = PersonalizedDistillationService(active.repository, original._source_policy, transport,
                    original._budget, now=lambda: datetime.now(UTC), output_language_for_video=original._output_language_for_video)
                approved_review = service.preview_cloud_execution(source_id=review['source_id'], video_id=row['video_id'],
                    evidence_ids=tuple(review['evidence_ids']), manual_command_id='materialize-' + row['case'],
                    qualified=False, credential_available=False)
                readiness = approved_review['readiness']
                token = approved_review['review_hash']
                assert isinstance(readiness, dict) and isinstance(token, str)
                require(not readiness['can_confirm']
                    and approved_review['verified_input_hash'] == row['proof_sha256'], 'NORMAL_ELIGIBILITY_MUST_STAY_CLOSED')
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
                    for k, v in before['tables'].items() if k not in ALLOWED_WRITES), 'SOURCE_PARENT_CHANGED')
                inputs.managed_parent_preflight(root)
                require(auth['consent_kind'] == 'OWNER_QUALIFICATION' and outcome.invocation_count == 1, 'QUALIFICATION_CLAIM_INVALID')
                technical = outcome.status.value in {'SUCCEEDED', 'SUCCEEDED_NO_NEW_INTELLIGENCE'}
                require(not technical or (receipt is not None and final and receipt['raw_text'] == final[0]), 'AUTHENTIC_RECEIPT_REQUIRED')
                readiness = active.backup_restore.readiness()
                result.update(status='TECHNICAL_PASS_AWAITING_ROOT' if technical and readiness['ready'] else 'TECHNICAL_FAILURE_STOP',
                    execution_status=outcome.status.value, invocation_count=outcome.invocation_count,
                    receipt=receipt, receipt_sha256=sha(encoded(receipt)), usage=usage,
                    backup_readiness=readiness, source_parents_unchanged=True,
                    qualification='CLOSED', normal_execution_enabled=False)
            except Exception:
                # Never serialize exception/provider/credential content or infer no charge.
                result['status'] = 'UNKNOWN_STOP'
            try:
                with active.repository._connect() as connection:
                    p.verify_database(active.repository, connection)
                    trace = {}
                    for table in ('distillation_execution_checkpoints', 'system_synthesis_cloud_authorizations',
                        'system_synthesis_result_receipts', 'distillation_resource_usage',
                        'distillation_cloud_response_failures', 'distillation_no_new_intelligence_results'):
                        trace[table] = [dict(r) for r in connection.execute(
                            f'SELECT * FROM {table} WHERE execution_id=?', (row['execution_id'],))]
                    result.update(state_trace=trace, trace_status='VERIFIED_PERSISTED_STATE')
            except Exception:
                result.update(status='UNKNOWN_STOP', trace_status='STATE_UNAVAILABLE_OR_UNVERIFIED')
            if final:
                once(self.control / (row['case'] + '.final.json'), {'raw_text': final[0], 'sha256': sha(final[0].encode())})
                result['final_sha256'] = sha(final[0].encode())
            # Recheck frozen seed/cases after execution, including physical DATA.
            try:
                require(package_binding() == binding, 'FROZEN_PACKAGE_CHANGED')
            except Exception:
                result['status'] = 'UNKNOWN_STOP'
            once(self.control / (row['case'] + '.result.json'), result)
            return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'execute'), default='prepare', nargs='?')
    args = parser.parse_args()
    trial = Trial()
    if args.action == 'prepare':
        report = trial.prepare()
    elif args.action == 'check':
        binding = package_binding()
        with trial.locked():
            ledger = trial.ledger(binding)
        report = {'status': 'CHECKED_NOT_AUTHORIZED', 'binding': binding, 'limits': LIMITS, 'attempts': ledger['attempts']}
    else:
        report = trial.execute()
    print(profile.canonical(report))


if __name__ == '__main__':
    main()
