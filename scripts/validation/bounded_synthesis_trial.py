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
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from youtube_intel import system_synthesis_persistence as p
from youtube_intel import system_synthesis_profile as profile
from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    PersonalizedDistillationService,
    _moonshot_chat_completions_http_transport,
    _MoonshotWireResponse,
)
from youtube_intel.model_settings import MacOSKeychainCredentialStore
from youtube_intel.state import SQLiteStateRepository, StateStoreError
from youtube_intel.synthesis_runtime import (
    MoonshotAttributionSynthesisTransport,
    MoonshotReadableSummarySynthesisTransport,
    MoonshotSourceLevelSynthesisTransport,
    MoonshotSystemSynthesisTransport,
)

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
V2_PACKAGE = Path('/Users/hua/Documents/yia-worktrees/readiness-bounded-synthesis-v2-trial/.var/bounded-synthesis-v2-trial/prepared-20261106-r2')
V2_CONTROL = Path('/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/bounded-synthesis-v2-trial-20261106-r2')
PARENT_SUMMARY = Path('/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/fee-parent-v2-20261105.json')
PARENT_SUMMARY_SHA = '80eac13761caba485618f69ec444f2676a24ed83779522f951d5a33eb8f51fb6'
PARENT_LOCATION_PROOF = PARENT_SUMMARY.with_name('fee-parent-location-v2-20261105.json')
PARENT_TERMINAL = Path('/Users/hua/Documents/yia-worktrees/readiness-final-acceptance/.var/bounded-synthesis-trial-runs/public-aircAruvnKk-en')
V2_LIMITS = {**LIMITS, 'historical_calls': 3, 'historical_held_microcny': 2913136,
    'max_total_calls': 12, 'total_microcny': 10000000, 'runner_held_microcny': 5713190,
    'gui_held_microcny': 984136, 'prospective_total_microcny': 9610462}
V3_PACKAGE = Path('/Users/hua/Documents/yia-worktrees/readiness-bounded-synthesis-v3-trial/.var/bounded-synthesis-v3-trial/prepared-20261106-r1')
V3_CONTROL = CONTROL.with_name('bounded-synthesis-v3-trial-20261106-r1')
V3_LIMITS = {**V2_LIMITS, 'historical_calls': 5, 'historical_held_microcny': 4881252,
    'max_total_calls': 14, 'total_microcny': 12000000, 'runner_held_microcny': 5735030,
    'gui_held_microcny': 986866, 'prospective_total_microcny': 11603148}
V4_PACKAGE = Path('/Users/hua/Documents/yia-worktrees/readiness-bounded-synthesis-v4-trial/.var/bounded-synthesis-v4-trial/prepared-20261107-r1')
V4_CONTROL = CONTROL.with_name('bounded-synthesis-v4-trial-20261107-r1')
V4_LIMITS = {**V3_LIMITS, 'historical_calls': 6, 'historical_held_microcny': 5867962,
    'max_total_calls': 15, 'per_call_microcny': 1500000, 'total_microcny': 14000000,
    'runner_held_microcny': 6693390, 'gui_held_microcny': 1370574, 'prospective_total_microcny': 13931926}
V4_R2_PACKAGE = Path('/Users/hua/Documents/yia-worktrees/readiness-bounded-synthesis-v4-r2-trial/.var/bounded-synthesis-v4-r2-trial/prepared-20261107-r1')
V4_R2_CONTROL = CONTROL.with_name('bounded-synthesis-v4-r2-trial-20261107-r1')
V4_R2_LIMITS = {**V4_LIMITS, 'historical_calls': 7, 'historical_held_microcny': 7238380,
    'max_total_calls': 16, 'total_microcny': 16000000, 'prospective_total_microcny': 15302344}
V4_R2_WITNESS = CONTROL.with_name('fee-parent-v4-r2-20261107.json')
V4_R2_WITNESS_SHA = '041db3e008b5a5f97f3640cbbb715f2b17dd832a2e8c4cafe8e36ff85e88a84b'
DEVICE_CONTINUITY = {'path': CONTROL.with_name('fee-device-continuity-20261107.json'),
    'sha256': '0a1744f92194421d2ba36adda89fad02fd4325f84f47558a1a6cff3cb2217e85',
    'historical_device': 16777231, 'current_device': 16777232,
    'decision_id': 'ROOT_DEVICE_CONTINUITY_31_TO_32_20261107'}
V4_PARENT_SUMMARY = CONTROL.with_name('fee-parent-v4-20261107.json')
V4_PARENT_SUMMARY_SHA = '33cdd1fb69d6ce4805fdf882cd3ccb3a8d8e0830eadc0edd03ef8face569b59c'
V2_PARENT_PINS = {
    'anchor.json': 'a2ddbf2a7cd1c5ac5d959cdbd627bd560eb4fa4f63fae68a057570ee051cb639',
    'approval-skeleton.json': '4290006410d5b17bf743b5a11c0e87ae23abf39814738f8bb54209a13675c4b0',
    'ledger.json': '8cb82a60331ccf2900c21db4c4444126cfc8931a9f330c75b2895f887272f291',
    'grant.json': '1d875cef20d88ae57ad7c30875313603d60bcfa5ae8c67b77f9250913df6346f',
    'lock': '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
    'attempt-1.json': '1e9ff264bd19d49d563d81a37e352783f7028131b36925e521da24eed78cdfe9',
    'attempt-2.json': '6d647ae552b83336dc73c879309c489818f53ff654cb061c7411f605d9832d47',
    'public-aircAruvnKk-en.result.json': '19951a1af61432e4d58794926893c4358532e25f5053efca239bb51ef7e36b3d',
    'public-aircAruvnKk-en.final.json': 'ea7081d145e864da8dd3cb04ae146de6128b6b510321384f02387e16eb3a9059',
    'public-aircAruvnKk-en.semantic.json': '1066bdd9e0cb339537b483e3fedb00d5595cd3860d65082e411b9509a207f148',
    'public-aircAruvnKk-zh-CN.result.json': '228955ccb657aeded079fd48696743b9eebfa036e5ac14999bdabfd8575b9a07',
    'public-aircAruvnKk-zh-CN.final.json': '01c56c3f3a1a197d40494f130244026ddca6a6a0a2f9328d82acbd430aafffdb',
    'public-aircAruvnKk-zh-CN.semantic.json': 'fac1dc569debd7cd1b748f211fdb48fcc935df61d56d961b6b54777ea22a4fc4'}
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


def trial_spec(variant: str = 'v1-r4') -> dict[str, Any]:
    """Five finite operator choices. No arbitrary CLI path/model/budget inputs."""
    one = {'variant': 'v1-r4', 'package': PACKAGE, 'manifest_sha256': MANIFEST_SHA,
        'control': CONTROL, 'runs': RUNS, 'order': ORDER, 'seed': inputs.SEED,
        'profile_id': profile.PROFILE_ID, 'limits': dict(LIMITS),
        'purpose': 'ROOT_RECORDED_PAID_QUALIFICATION'}
    if variant == 'v1-r4':
        return one
    two = {**one, 'variant': 'v2-r1', 'package': V2_PACKAGE, 'manifest_sha256': None,
            'control': V2_CONTROL, 'runs': REPO / '.var/bounded-synthesis-v2-trial-runs',
            'profile_id': profile.ATTRIBUTION_PROFILE_ID, 'limits': dict(V2_LIMITS),
            'purpose': 'ROOT_RECORDED_ATTRIBUTION_V2_CONTINUATION', 'original': one,
            'parent_summary': PARENT_SUMMARY, 'parent_summary_sha256': PARENT_SUMMARY_SHA,
            'bundle_parent_summary_sha256': PARENT_SUMMARY_SHA,
            'parent_location_proof': PARENT_LOCATION_PROOF, 'parent_terminal': PARENT_TERMINAL,
            'parent_location_transition': {'old_device': 16777234, 'current_device': 16777231, 'inode': 144261833}}
    if variant == 'v2-r1':
        return two
    frozen = Path('/Users/hua/Documents/yia-worktrees/readiness-release-validation')
    three = {**two, 'variant': 'v3-r1', 'package': V3_PACKAGE, 'control': V3_CONTROL,
            'runs': REPO / '.var/bounded-synthesis-v3-trial-runs', 'original': two,
            'profile_id': profile.SOURCE_LEVEL_PROFILE_ID, 'limits': dict(V3_LIMITS),
            'purpose': 'ROOT_RECORDED_SOURCE_LEVEL_V3_CONTINUATION', 'parent_pins': dict(V2_PARENT_PINS),
            'frozen_parent_source': frozen, 'parent_runs': frozen / '.var/bounded-synthesis-v2-trial-runs',
            'historical_revision': '7203c1f49b62139488027d3bdc7fadb937e6f519',
            'historical_binding_sha256': '346a5905a1d767f4ee04b4d769f1f10c2d97651fb4ca2f15d2dc580e1dcdb12d',
            'historical_manifest_sha256': '0ff6faeed2fde5ce18921b3570b291c851914b7dbea52ccba0488410127d041c',
            'historical_marker_sha256': V2_PARENT_PINS['anchor.json'],
            'historical_location_sha256': 'ac14a8e3eb871cf04d82ae783cb1033fc28cc22652b2155f88b43de7e8141b2a',
            'independent_report_pins': ('bc4f9a9b11f26f44323cf124e6061c76c76e076f25b0e2eb1c2ddb32f7be0992',
                '07ba2e05b7bf27d24f0841b6d2684863e3a56ba1cac0af2f52c5acf25edcfe54'),
            'restore_report': frozen / '.var/final-checks/v2-real-20261106/zh-rejected-result-backup-restore.json'}
    if variant == 'v3-r1':
        return three
    frozen_v3 = Path('/Users/hua/Documents/yia-worktrees/readiness-source-level-final-validation')
    four = {**three, 'variant': 'v4-r1', 'original': three, 'package': V4_PACKAGE, 'control': V4_CONTROL,
            'runs': REPO / '.var/bounded-synthesis-v4-trial-runs', 'limits': dict(V4_LIMITS),
            'profile_id': profile.READABLE_SUMMARY_PROFILE_ID,
            'purpose': 'ROOT_RECORDED_READABLE_SUMMARY_V4_CONTINUATION',
            'stopped_v3_summary': V4_PARENT_SUMMARY, 'stopped_v3_summary_sha256': V4_PARENT_SUMMARY_SHA,
            'frozen_parent_source': frozen_v3, 'parent_runs': frozen_v3 / '.var/bounded-synthesis-v3-trial-runs',
            'historical_revision': '6fe094912457856fc6dea311f196baf1f64deef8',
            'historical_binding_sha256': '0a4166d848081b435c76432cf357573af7e88fd18d830ffb5b4617f1da5e9dc0',
            'historical_manifest_sha256': '70527e71da5b6d4ddbc2c7fe6cbde519e9fe224e81ce190a9eb8bcdfb7dfaee7',
            'restore_report': frozen_v3 / '.var/final-checks/v3-real-20261107/rejected-case-backup-restore.json'}
    if variant == 'v4-r1':
        return four
    if variant == 'v4-r2':
        frozen_r1 = Path('/Users/hua/Documents/yia-worktrees/readiness-readable-summary-final-validation')
        return {**four, 'variant': variant, 'original': four, 'package': V4_R2_PACKAGE, 'control': V4_R2_CONTROL,
            'runs': REPO / '.var/bounded-synthesis-v4-r2-trial-runs', 'limits': dict(V4_R2_LIMITS),
            'purpose': 'ROOT_RECORDED_READABLE_SUMMARY_V4_R2_CONTINUATION',
            'device_continuity': dict(DEVICE_CONTINUITY),
            'preclaim_parent_witness': V4_R2_WITNESS, 'preclaim_parent_witness_sha256': V4_R2_WITNESS_SHA,
            'frozen_parent_source': frozen_r1, 'parent_runs': frozen_r1 / '.var/bounded-synthesis-v4-trial-runs',
            'historical_revision': '469f11a2307c4ed841f533b42e067c0c800ce247',
            'historical_binding_sha256': 'ce7691625666c128470de575339e0f5617d2ce49699e34c363049439f0ac857d',
            'historical_manifest_sha256': 'ac2fd8bf807fd6c43c34026adb84de24ce6e845623d738f03fec5bdc85792d27'}
    raise ValueError('TRIAL_VARIANT_UNKNOWN')


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


def code_hashes(*, source_root: Path = REPO) -> dict[str, str]:
    paths = [*sorted((source_root / 'src').rglob('*.py')), *sorted((source_root / 'src').rglob('*.sql')),
        source_root / 'scripts/validation/bounded_synthesis_trial.py',
        source_root / 'scripts/validation/materialize_synthesis_inputs.py', source_root / 'config/settings.example.yaml',
        source_root / 'pyproject.toml', source_root / 'uv.lock']
    v2_helper = source_root / 'scripts/validation/materialize_synthesis_v2_inputs.py'
    if v2_helper.exists():
        paths.append(v2_helper)
    result = {str(path.relative_to(source_root)): sha(read(path)) for path in paths}
    if source_root != REPO:
        return result
    for name, module in list(sys.modules.items()):
        if name == 'youtube_intel' or name.startswith('youtube_intel.'):
            location = getattr(module, '__file__', None)
            if location and location.endswith('.py'):
                path = Path(location).resolve()
                require(path.is_relative_to(REPO / 'src')
                    and result.get(str(path.relative_to(REPO))) == sha(read(path)), 'IMPORTED_SOURCE_DIFFERS')
    return result


def physical_identity(path: Path, *, directory_only: bool = False) -> dict[str, Any]:
    """Actual identity only; historical metadata never changes filesystem APIs."""
    if directory_only:
        directory(path)
        meta = path.stat()
    else:
        raw = read(path)
        meta = path.stat()
    value: dict[str, Any] = {'current_device': meta.st_dev, 'inode': meta.st_ino, 'owner_uid': meta.st_uid,
        'mode': stat.S_IMODE(meta.st_mode), 'nlink': meta.st_nlink}
    if not directory_only:
        value.update(mtime_ns=meta.st_mtime_ns, bytes=len(raw), sha256=sha(raw))
        require(meta == path.stat(), 'CONTINUITY_FILE_CHANGED_DURING_READ')
    return value


class HistoricalMetadata(NamedTuple):
    path: Path
    raw: bytes
    identity_json: bytes

    def device(self, path: Path) -> int:
        value = json.loads(self.raw)
        is_directory = str(path) in value['controls']
        record = (value['controls'] if is_directory else value['files']).get(str(path))
        require(record is not None, 'CONTINUITY_UNPINNED_PATH')
        expected = {key: child for key, child in record.items() if key not in {'historical_device', 'anchor_device'}}
        require(physical_identity(path, directory_only=is_directory) == expected, 'CONTINUITY_IDENTITY_CHANGED')
        result: int = record['historical_device']
        return result

    def evidence(self) -> dict[str, Any]:
        value = json.loads(self.raw)
        return {'path': str(self.path), 'sha256': sha(self.raw), 'witness_identity': json.loads(self.identity_json),
            'transition': value['transition'], 'new_fee_authorized': False,
            'current_controls': {name: {key: child for key, child in record.items()
                if key not in {'historical_device', 'anchor_device'}} for name, record in value['controls'].items()},
            'current_files': {name: {key: child for key, child in record.items() if key != 'historical_device'}
                for name, record in value['files'].items()}}


def historical_metadata(spec: dict[str, Any]) -> HistoricalMetadata | None:
    configured = spec.get('device_continuity')
    if configured is None:
        return None
    require(spec['variant'] == 'v4-r2', 'CONTINUITY_R2_ONLY')
    path: Path = configured['path']
    raw = read(path, private=True)
    require(sha(raw) == configured['sha256'], 'CONTINUITY_WITNESS_CHANGED')
    value = parsed(path, private=True)
    transition = {key: configured[key] for key in ('historical_device', 'current_device')}
    require(set(value) == {'baseline_snapshot', 'comparison_report', 'controls', 'decision_id', 'files',
        'new_fee_authorized', 'purpose', 'transition', 'version'}
        and value['version'] == 'bounded-trial-apfs-device-continuity-v1'
        and value['purpose'] == 'HISTORICAL_METADATA_ONLY_NOT_FEE_AUTHORIZATION'
        and value['decision_id'] == configured['decision_id'] and value['new_fee_authorized'] is False
        and encoded(value['transition']) == encoded(transition)
        and all(type(number) is int and number > 0 for number in transition.values())
        and transition['historical_device'] != transition['current_device'], 'CONTINUITY_WITNESS_INVALID')
    original = spec['original']
    controls = {str(original['control']), str(original['original']['control']),
        str(original['original']['original']['control']), str(original['original']['original']['original']['control'])}
    require(set(value['controls']) == controls and value['files'], 'CONTINUITY_PATH_SET_DIFFERS')
    context = HistoricalMetadata(path, raw, encoded(physical_identity(path)))
    require(json.loads(context.identity_json)['current_device'] == transition['current_device'],
        'CONTINUITY_WITNESS_DEVICE_DIFFERS')
    for group, names in (('files', {'mtime_ns', 'bytes', 'sha256'}), ('controls', {'anchor_device'})):
        for name, record in value[group].items():
            target = Path(name)
            require(target.is_absolute() and str(target) == name and '..' not in target.parts
                and target != path and set(record) == names | {'historical_device', 'current_device', 'inode',
                    'owner_uid', 'mode', 'nlink'} and all(type(child) is int and child >= 0
                    for key, child in record.items() if key != 'sha256')
                and record['historical_device'] == transition['historical_device']
                and record['current_device'] == transition['current_device']
                and record['owner_uid'] == os.getuid(), 'CONTINUITY_RECORD_INVALID')
            context.device(target)
            if group == 'controls':
                anchor = parsed(target / 'anchor.json', private=True)
                require(anchor['control_device'] == record['anchor_device'] and anchor['control_inode'] == record['inode']
                    and {str(child) for child in target.iterdir()}
                    == {child for child in value['files'] if Path(child).parent == target}, 'CONTINUITY_CONTROL_DIFFERS')
    for key in ('baseline_snapshot', 'comparison_report'):
        support = value[key]
        target = Path(support['path'])
        require(set(support) == {'path', 'sha256'} and str(target) not in value['files']
            and str(target) not in value['controls'] and target != path
            and sha(read(target)) == support['sha256']
            and physical_identity(target)['current_device'] == transition['current_device'], 'CONTINUITY_SUPPORT_CHANGED')
    return context


def historical_device(path: Path, context: HistoricalMetadata | None) -> int:
    if context is not None:
        return context.device(path)
    actual: int = physical_identity(path, directory_only=path.is_dir())['current_device']
    return actual


def parent_history(spec: dict[str, Any], *, _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    """Historical rejected invocation is a held cost, never new consent."""
    try:
        summary_path: Path = spec['parent_summary']
        summary_raw = read(summary_path, private=True)
        require(sha(summary_raw) == spec['parent_summary_sha256'], 'PARENT_SUMMARY_CHANGED')
        summary = parsed(summary_path, private=True)
        require(set(summary) == {'status', 'parent_control', 'parent_hashes', 'historical_calls',
            'historical_held_microcny', 'actual_bill', 'parent_semantic', 'further_calls_authorized'}
            and summary['status'] == 'HISTORICAL_PARENT_ONLY_NOT_NEW_FEE_AUTHORIZATION'
            and summary['actual_bill'] == 'UNKNOWN' and summary['parent_semantic'] == 'REJECT'
            and summary['further_calls_authorized'] is False, 'PARENT_SUMMARY_INVALID')
        original = spec['original']
        parent = Path(summary['parent_control'])
        require(parent == original['control'], 'PARENT_CONTROL_DIFFERS')
        directory(parent)
        case = original['order'][0]
        names = ('anchor.json', 'ledger.json', 'grant.json', 'attempt-1.json',
            case + '.result.json', case + '.final.json', case + '.semantic.json')
        require(set(summary['parent_hashes']) == set(names)
            and {f.name for f in parent.iterdir()} == set(names) | {'lock', 'approval-skeleton.json'}, 'PARENT_UNKNOWN_ATTEMPT')
        files = {}
        values = {}
        for name in names:
            path = parent / name
            raw = read(path, private=True)
            require(sha(raw) == summary['parent_hashes'][name], 'PARENT_FILE_CHANGED')
            meta = path.stat()
            files[name] = {'sha256': sha(raw), 'device': historical_device(path, _history), 'inode': meta.st_ino, 'bytes': len(raw)}
            values[name] = parsed(path, private=True)
        anchor, ledger, grant, attempt = (values[name] for name in names[:4])
        result, final, decision = (values[name] for name in names[4:])
        require(anchor == {'binding_sha256': ledger['binding_sha256'], 'control_inode': parent.stat().st_ino,
            'control_device': anchor['control_device']} and ledger['attempts'] == [attempt]
            and set(ledger) == {'binding_sha256', 'attempts'}, 'PARENT_ANCHOR_LEDGER_INVALID')
        require(set(grant) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
            and grant['approved'] is True and grant['purpose'] == original['purpose']
            and grant['limits'] == original['limits'] and encoded(grant['limits']) == encoded(original['limits'])
            and grant['binding_sha256'] == anchor['binding_sha256']
            and isinstance(grant['decision_id'], str) and 0 < len(grant['decision_id']) <= 160
            and datetime.fromisoformat(grant['expires_at']).tzinfo is not None, 'PARENT_OLD_GRANT_INVALID')
        old_manifest = parsed(original['package'] / 'manifest.json')
        require(sha(read(original['package'] / 'manifest.json')) == original['manifest_sha256'], 'PARENT_INPUT_MANIFEST_CHANGED')
        first = old_manifest['cases'][0]
        require(set(attempt) == {'case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'grant_sha256'}
            and all(attempt[k] == first[k] for k in attempt if k != 'grant_sha256')
            and attempt['case'] == case and attempt['grant_sha256'] == files['grant.json']['sha256']
            and type(attempt['reserve_microcny']) is int and 0 < attempt['reserve_microcny'] <= original['limits']['per_call_microcny'], 'PARENT_ATTEMPT_INVALID')
        receipt = result['receipt']
        require(all(result[k] == attempt[k] for k in attempt) and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
            and result['execution_status'] in {'SUCCEEDED', 'SUCCEEDED_NO_NEW_INTELLIGENCE'}
            and type(result['invocation_count']) is int and result['invocation_count'] == 1 and result['send_attempted'] is True
            and result['actual_bill'] == 'UNKNOWN' and result['qualification'] == 'CLOSED'
            and result['normal_execution_enabled'] is False and result['source_parents_unchanged'] is True
            and result['trace_status'] == 'VERIFIED_PERSISTED_STATE'
            and result['receipt_sha256'] == sha(encoded(receipt))
            and final == {'raw_text': receipt['raw_text'], 'sha256': result['final_sha256']}
            and final['sha256'] == sha(final['raw_text'].encode()) == receipt['raw_sha256'], 'PARENT_RESULT_FINAL_INVALID')
        trace = result['state_trace']
        require(trace['system_synthesis_result_receipts'] == [receipt]
            and len(trace['distillation_execution_checkpoints']) == 1
            and len(trace['system_synthesis_cloud_authorizations']) == 1, 'PARENT_TRACE_INVALID')
        checkpoint, authorization = trace['distillation_execution_checkpoints'][0], trace['system_synthesis_cloud_authorizations'][0]
        require(checkpoint['execution_id'] == attempt['execution_id'] and checkpoint['invocation_count'] == 1
            and type(checkpoint['invocation_count']) is int
            and checkpoint['status'] == ('PENDING' if result['execution_status'] == 'SUCCEEDED_NO_NEW_INTELLIGENCE' else 'SUCCEEDED')
            and receipt['execution_id'] == attempt['execution_id']
            and receipt['proof_sha256'] == attempt['proof_sha256']
            and authorization['execution_id'] == attempt['execution_id']
            and authorization['verified_input_hash'] == attempt['proof_sha256']
            and (authorization['provider'], authorization['model']) == profile.PAIR
            and authorization['consent_kind'] == 'OWNER_QUALIFICATION' and authorization['max_calls'] == 1
            and type(authorization['max_calls']) is int and authorization['prior_calls'] == 0
            and authorization['prior_reserved_microunits'] == 0
            and authorization['reserve_microunits'] == attempt['reserve_microcny'], 'PARENT_CLAIM_INVALID')
        authorized_at = datetime.fromisoformat(authorization['authorized_at'])
        require(authorized_at.tzinfo is not None
            and authorized_at < datetime.fromisoformat(grant['expires_at']), 'PARENT_INVOCATION_OUTSIDE_GRANT')
        observation = p.loads(receipt['observation_json'])
        require(observation['table'] == ('distillation_no_new_intelligence_results'
            if result['execution_status'] == 'SUCCEEDED_NO_NEW_INTELLIGENCE' else 'distillation_resource_usage')
            and trace[observation['table']] == [observation['row']]
            and sum(len(trace[table]) for table in ('distillation_resource_usage',
                'distillation_no_new_intelligence_results', 'distillation_cloud_response_failures')) == 1
            and observation['row']['execution_id'] == attempt['execution_id']
            and (observation['row']['actual_provider'], observation['row']['actual_model']) == profile.PAIR,
            'PARENT_OBSERVATION_INVALID')
        require(decision == {'case': case, 'decision': 'REJECT', 'reviewer': 'ROOT',
            'decision_id': decision['decision_id'], 'result_sha256': files[case + '.result.json']['sha256'],
            'receipt_sha256': result['receipt_sha256'], 'oracle_sha256': old_manifest['oracle_sha256']}
            and isinstance(decision['decision_id'], str) and 0 < len(decision['decision_id']) <= 160, 'PARENT_REJECTION_INVALID')
        calls = grant['limits']['historical_calls'] + 1
        held = grant['limits']['historical_held_microcny'] + attempt['reserve_microcny']
        require(type(calls) is int and type(held) is int and calls == summary['historical_calls'] == spec['limits']['historical_calls']
            and held == summary['historical_held_microcny'] == spec['limits']['historical_held_microcny'], 'PARENT_HISTORY_TOTALS_INVALID')
        read(parent / 'lock', private=True)
        lock_meta = (parent / 'lock').stat()
        return {'summary_sha256': sha(summary_raw), 'summary_inode': summary_path.stat().st_ino,
            'parent_control': str(parent), 'parent_inode': parent.stat().st_ino, 'parent_device': historical_device(parent, _history),
            'lock_inode': lock_meta.st_ino, 'lock_device': historical_device(parent / 'lock', _history), 'files': files,
            'historical_calls': calls, 'historical_held_microcny': held, 'actual_bill': 'UNKNOWN', 'parent_semantic': 'REJECT', 'anchor': anchor}
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise ValueError('PARENT_HISTORY_UNVERIFIABLE') from None


def parent_location_evidence(spec: dict[str, Any], history: dict[str, Any], *,
    _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    """One pinned historical location transition, with the original DB intact."""
    parent = Path(history['parent_control'])
    anchor = history['anchor']
    transition = {'old_device': anchor['control_device'], 'current_device': historical_device(parent, _history),
        'inode': parent.stat().st_ino}
    require(transition == spec['parent_location_transition']
        and transition['old_device'] != transition['current_device'], 'PARENT_LOCATION_TRANSITION_NOT_APPROVED')
    root: Path = spec['parent_terminal']
    inputs.safe_tree(root)
    database = root / 'state.sqlite3'
    database_sha = sha(read(database))
    repository = SQLiteStateRepository(database)
    repository.bind_source_storage(root / 'data')
    case = spec['original']['order'][0]
    result = parsed(parent / (case + '.result.json'), private=True)
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        p.verify_database(repository, connection)
        for table, expected in result['state_trace'].items():
            require(table in {'distillation_execution_checkpoints', 'system_synthesis_cloud_authorizations',
                'system_synthesis_result_receipts', 'distillation_resource_usage',
                'distillation_cloud_response_failures', 'distillation_no_new_intelligence_results'}, 'PARENT_TRACE_TABLE_INVALID')
            actual = [dict(row) for row in connection.execute(
                f'SELECT * FROM {table} WHERE execution_id=?', (result['execution_id'],))]
            require(actual == expected, 'PARENT_TERMINAL_DATABASE_DIFFERS')
    require(database_sha == sha(read(database)), 'PARENT_TERMINAL_DATABASE_CHANGED')
    summary = parsed(spec['parent_summary'], private=True)
    return {'parent_control': str(parent), 'parent_summary_sha256': history['summary_sha256'],
        'parent_hashes': summary['parent_hashes'],
        'old_identity': {'device': anchor['control_device'], 'inode': anchor['control_inode'],
            'owner_uid': os.getuid(), 'mode': 0o700},
        'current_identity': {'device': historical_device(parent, _history), 'inode': parent.stat().st_ino,
            'owner_uid': parent.stat().st_uid, 'mode': stat.S_IMODE(parent.stat().st_mode)},
        'terminal_root': str(root), 'terminal_database_sha256': database_sha,
        'terminal_inventory_sha256': sha(encoded(inputs.inventory(root))),
        'receipt_sha256': result['receipt_sha256'], 'historical_calls': history['historical_calls'],
        'historical_held_microcny': history['historical_held_microcny'],
        'actual_bill': 'UNKNOWN', 'parent_semantic': 'REJECT'}


def parent_location_proposal(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = trial_spec('v2-r1') if spec is None else spec
    require(selected['variant'] == 'v2-r1', 'V2_LOCATION_PROPOSAL_ONLY')
    history = parent_history(selected)
    return {'approved': False, 'purpose': 'PARENT_LOCATION_ONLY', 'decision_id': '',
        'binding': parent_location_evidence(selected, history)}


def parent_binding(spec: dict[str, Any], *, _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    try:
        history = parent_history(spec, _history=_history)
        anchor = history.pop('anchor')
        history['location_recovery'] = None
        if anchor['control_device'] == history['parent_device']:
            require(not spec['parent_location_proof'].exists(), 'PARENT_LOCATION_PROOF_NOT_APPLICABLE')
            return history
        evidence = parent_location_evidence(spec, {**history, 'anchor': anchor}, _history=_history)
        proof: Path = spec['parent_location_proof']
        value = parsed(proof, private=True)
        require(value == {'approved': True, 'purpose': 'PARENT_LOCATION_ONLY',
            'decision_id': value['decision_id'], 'binding': evidence}
            and value['approved'] is True and encoded(value['binding']) == encoded(evidence)
            and isinstance(value['decision_id'], str) and 0 < len(value['decision_id']) <= 160,
            'PARENT_LOCATION_PROOF_REQUIRED_OR_INVALID')
        history['location_recovery'] = {'sha256': sha(read(proof, private=True)), 'path': str(proof),
            'device': historical_device(proof, _history), 'inode': proof.stat().st_ino, 'binding': evidence}
        return history
    except (OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError):
        raise ValueError('PARENT_LOCATION_OR_HISTORY_UNVERIFIABLE') from None


def verified_stopped_terminal(original: dict[str, Any], binding: dict[str, Any],
    files: dict[str, Any], values: dict[str, Any], *, index: int, verdict: str, expiry: datetime,
    report_path: Path, report_sha256: str, runs: Path) -> dict[str, Any]:
    """Readonly verification shared by the two finite stopped parent versions."""
    row = binding['cases'][index]
    attempt = values[f'attempt-{index + 1}.json']
    case = row['case']
    require(set(attempt) == {'case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'grant_sha256'}
        and all(attempt[key] == row[key] for key in attempt if key != 'grant_sha256')
        and attempt['grant_sha256'] == files['grant.json']['sha256'], 'V3_PARENT_ATTEMPT_DIFFERS')
    result, final, decision = (values[case + suffix] for suffix in ('.result.json', '.final.json', '.semantic.json'))
    receipt = result['receipt']
    require(all(result[key] == attempt[key] for key in attempt)
        and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' and result['execution_status'] == 'SUCCEEDED'
        and type(result['invocation_count']) is int and result['invocation_count'] == 1
        and result['send_attempted'] is True and result['actual_bill'] == 'UNKNOWN'
        and result['qualification'] == 'CLOSED' and result['normal_execution_enabled'] is False
        and result['source_parents_unchanged'] is True and result['trace_status'] == 'VERIFIED_PERSISTED_STATE'
        and result['receipt_sha256'] == sha(encoded(receipt))
        and final == {'raw_text': receipt['raw_text'], 'sha256': result['final_sha256']}
        and final['sha256'] == sha(final['raw_text'].encode()) == receipt['raw_sha256'], 'V3_PARENT_RESULT_DIFFERS')
    require(decision == {'case': case, 'decision': verdict, 'reviewer': 'ROOT',
        'decision_id': decision['decision_id'], 'result_sha256': files[case + '.result.json']['sha256'],
        'receipt_sha256': result['receipt_sha256'], 'oracle_sha256': binding['oracle_sha256']}
        and isinstance(decision['decision_id'], str) and 0 < len(decision['decision_id']) <= 160,
        'V3_PARENT_SEMANTIC_DIFFERS')
    report_raw = read(report_path, private=True)
    report = parsed(report_path, private=True)
    require(sha(report_raw) == report_sha256
        and report['case'] == case and report['verdict'] == verdict, 'V3_INDEPENDENT_REVIEW_DIFFERS')
    root = runs / case
    inputs.safe_tree(root)
    database = root / 'state.sqlite3'
    before = sha(read(database))
    repository = SQLiteStateRepository(database)
    repository.bind_source_storage(root / 'data')
    trace = result['state_trace']
    tables = {'distillation_execution_checkpoints', 'system_synthesis_cloud_authorizations',
        'system_synthesis_result_receipts', 'distillation_resource_usage',
        'distillation_cloud_response_failures', 'distillation_no_new_intelligence_results'}
    require(set(trace) == tables and trace['system_synthesis_result_receipts'] == [receipt], 'V3_PARENT_TRACE_INVALID')
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        p.verify_database(repository, connection)
        for table in tables:
            actual = [dict(item) for item in connection.execute(
                f'SELECT * FROM {table} WHERE execution_id=?', (attempt['execution_id'],))]
            require(actual == trace[table], 'V3_PARENT_DATABASE_DIFFERS')
    require(len(trace['system_synthesis_cloud_authorizations']) == 1
        and len(trace['distillation_execution_checkpoints']) == 1, 'V3_PARENT_CLAIM_INVALID')
    authorization = trace['system_synthesis_cloud_authorizations'][0]
    checkpoint = trace['distillation_execution_checkpoints'][0]
    authorized = datetime.fromisoformat(authorization['authorized_at'])
    require(authorized.tzinfo is not None and authorized < expiry
        and authorization['consent_kind'] == 'OWNER_QUALIFICATION'
        and authorization['verified_input_hash'] == attempt['proof_sha256']
        and (authorization['provider'], authorization['model']) == profile.PAIR
        and type(authorization['max_calls']) is int and authorization['max_calls'] == 1
        and authorization['prior_calls'] == 0 and authorization['prior_reserved_microunits'] == 0
        and authorization['reserve_microunits'] == attempt['reserve_microcny']
        and checkpoint['status'] == 'SUCCEEDED' and type(checkpoint['invocation_count']) is int
        and checkpoint['invocation_count'] == 1, 'V3_PARENT_INVOCATION_NOT_AUTHORIZED')
    current = inputs.inventory(root)
    source = inputs.inventory(original['package'] / 'cases' / case / 'project')
    require(current['data'] == source['data'] and all(current['tables'][key] == value
        for key, value in source['tables'].items() if key not in ALLOWED_WRITES), 'V3_PARENT_SOURCE_CHANGED')
    inputs.managed_parent_preflight(root)
    require(before == sha(read(database)), 'V3_PARENT_DATABASE_CHANGED')
    return {'case': case, 'database_sha256': before, 'inventory_sha256': sha(encoded(current)),
        'receipt_sha256': result['receipt_sha256'], 'independent_sha256': sha(report_raw),
        'decision': verdict}


def stopped_v2_parent(spec: dict[str, Any], *, _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    """Verify the frozen stopped two-call parent and retain all five held costs."""
    try:
        original = spec['original']
        frozen = spec['frozen_parent_source']
        saved = parsed(original['package'] / 'proposal-not-authorized.json')
        binding = package_binding('v2-r1', _spec=original, _source_root=frozen, _history=_history)
        require(binding == saved['binding']
            and sha(encoded(binding)) == spec['historical_binding_sha256']
            and binding['manifest_sha256'] == spec['historical_manifest_sha256']
            and binding['source_revision'] == spec['historical_revision'], 'V3_FROZEN_PARENT_SOURCE_DIFFERS')
        nested = parent_binding(original, _history=_history)
        require(nested == binding['parent'] and nested['historical_calls'] == 3
            and nested['historical_held_microcny'] == original['limits']['historical_held_microcny'],
            'V3_NESTED_HISTORY_DIFFERS')
        recovery = nested['location_recovery']
        if recovery is not None:
            require(recovery['sha256'] == spec['historical_location_sha256'], 'V3_LOCATION_WITNESS_DIFFERS')
        control: Path = original['control']
        directory(control)
        require({path.name for path in control.iterdir()} == set(spec['parent_pins']), 'V3_PARENT_UNKNOWN_FILE')
        files = {}
        values = {}
        for name, expected in spec['parent_pins'].items():
            path = control / name
            raw = read(path, private=True)
            require(sha(raw) == expected, 'V3_PARENT_HASH_DIFFERS')
            meta = path.stat()
            files[name] = {'sha256': sha(raw), 'device': historical_device(path, _history), 'inode': meta.st_ino, 'bytes': len(raw)}
            values[name] = parsed(path, private=True)
        anchor, ledger, grant = (values[name] for name in ('anchor.json', 'ledger.json', 'grant.json'))
        require(anchor == {'binding_sha256': sha(encoded(binding)), 'control_inode': control.stat().st_ino,
            'control_device': historical_device(control, _history)}, 'V3_PARENT_IDENTITY_DIFFERS')
        marker = control.with_name(control.name + '-initialized.json')
        require(parsed(marker, private=True) == anchor and sha(read(marker, private=True)) == spec['historical_marker_sha256'],
            'V3_PARENT_INITIALIZATION_DIFFERS')
        require(set(grant) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
            and grant['approved'] is True and grant['purpose'] == original['purpose']
            and grant['binding_sha256'] == sha(encoded(binding))
            and encoded(grant['limits']) == encoded(original['limits'])
            and isinstance(grant['decision_id'], str) and 0 < len(grant['decision_id']) <= 160,
            'V3_PARENT_GRANT_INVALID')
        expiry = datetime.fromisoformat(grant['expires_at'])
        require(expiry.tzinfo is not None, 'V3_PARENT_GRANT_TIME_INVALID')
        attempts = [values['attempt-1.json'], values['attempt-2.json']]
        require(ledger == {'binding_sha256': sha(encoded(binding)), 'attempts': attempts}, 'V3_PARENT_LEDGER_DIFFERS')
        terminals = []
        for index, verdict in enumerate(('PASS', 'REJECT')):
            case = binding['cases'][index]['case']
            terminals.append(verified_stopped_terminal(original, binding, files, values, index=index,
                verdict=verdict, expiry=expiry,
                report_path=frozen / '.var/independent-v2-semantic-20261106' / (case + '.json'),
                report_sha256=spec['independent_report_pins'][index], runs=spec['parent_runs']))
        restore_raw = read(spec['restore_report'])
        restore = parsed(spec['restore_report'])
        require(restore['status'] == 'REAL_PAID_RESULT_RESTORE_PASS_NO_REEXECUTION'
            and restore['case'] == binding['cases'][1]['case'] and restore['semantic'] == 'REJECT'
            and all(restore[key] is True for key in ('all_data_files_equal', 'all_table_rows_equal',
                'external_controls_hashes_equal', 'backup_ready_after_restore'))
            and restore['new_model_calls_during_backup_restore'] == 0 and restore['original_invocation_count'] == 1,
            'V3_PARENT_RESTORE_UNVERIFIED')
        held = nested['historical_held_microcny'] + sum(attempt['reserve_microcny'] for attempt in attempts)
        require(held == spec['limits']['historical_held_microcny']
            and nested['historical_calls'] + len(attempts) == spec['limits']['historical_calls'], 'V3_HISTORY_TOTALS_DIFFER')
        return {'nested_v1': nested, 'files': files, 'parent_control': str(control),
            'control_inode': control.stat().st_ino, 'control_device': historical_device(control, _history),
            'marker_inode': marker.stat().st_ino, 'marker_sha256': sha(read(marker, private=True)),
            'manifest_sha256': binding['manifest_sha256'], 'binding_sha256': sha(encoded(binding)),
            'terminals': terminals, 'restore_report_sha256': sha(restore_raw),
            'historical_calls': 5, 'historical_held_microcny': held, 'actual_bill': 'UNKNOWN', 'parent_semantic': 'REJECT'}
    except (OSError, ValueError, KeyError, TypeError, IndexError, sqlite3.DatabaseError):
        raise ValueError('V3_STOPPED_PARENT_UNVERIFIABLE') from None


def stopped_v3_parent(spec: dict[str, Any], *, _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    """Retain the one rejected v3 call over the complete five-call parent."""
    try:
        summary_path: Path = spec['stopped_v3_summary']
        summary_raw = read(summary_path, private=True)
        require(sha(summary_raw) == spec['stopped_v3_summary_sha256'], 'V4_PARENT_SUMMARY_CHANGED')
        summary = parsed(summary_path, private=True)
        require(set(summary) == {'actual_bill', 'binding_sha256', 'control', 'historical_calls',
            'historical_held_microcny', 'independent_report_sha256', 'manifest_sha256', 'new_fee_authorized',
            'parent_source', 'pins', 'semantic', 'source_revision'}
            and summary['actual_bill'] == 'UNKNOWN' and summary['semantic'] == 'REJECT'
            and summary['new_fee_authorized'] is False, 'V4_PARENT_SUMMARY_INVALID')
        original = spec['original']
        frozen: Path = spec['frozen_parent_source']
        saved = parsed(original['package'] / 'proposal-not-authorized.json')
        binding = package_binding('v3-r1', _spec=original, _source_root=frozen, _history=_history)
        require(binding == saved['binding'] and sha(encoded(binding)) == summary['binding_sha256']
            == spec['historical_binding_sha256'] and binding['manifest_sha256'] == summary['manifest_sha256']
            == spec['historical_manifest_sha256'] and binding['source_revision'] == summary['source_revision']
            == spec['historical_revision'] and str(frozen) == summary['parent_source'], 'V4_FROZEN_PARENT_SOURCE_DIFFERS')
        nested = stopped_v2_parent(original, _history=_history)
        require(nested == binding['parent'] and nested['historical_calls'] == 5
            and nested['historical_held_microcny'] == original['limits']['historical_held_microcny'],
            'V4_NESTED_HISTORY_DIFFERS')
        control: Path = original['control']
        require(str(control) == summary['control'], 'V4_PARENT_CONTROL_DIFFERS')
        directory(control)
        case = binding['cases'][0]['case']
        names = {'anchor.json', 'ledger.json', 'lock', 'grant.json', 'approval-skeleton.json',
            'attempt-1.json', case + '.result.json', case + '.final.json', case + '.semantic.json'}
        require(set(summary['pins']) == names and {path.name for path in control.iterdir()} == names,
            'V4_PARENT_UNKNOWN_FILE')
        files = {}
        values = {}
        for name, expected in summary['pins'].items():
            path = control / name
            raw = read(path, private=True)
            require(sha(raw) == expected, 'V4_PARENT_HASH_DIFFERS')
            meta = path.stat()
            files[name] = {'sha256': sha(raw), 'device': historical_device(path, _history), 'inode': meta.st_ino, 'bytes': len(raw)}
            values[name] = parsed(path, private=True)
        anchor, ledger, grant = (values[name] for name in ('anchor.json', 'ledger.json', 'grant.json'))
        require(anchor == {'binding_sha256': sha(encoded(binding)), 'control_inode': control.stat().st_ino,
            'control_device': historical_device(control, _history)}, 'V4_PARENT_IDENTITY_DIFFERS')
        marker = control.with_name(control.name + '-initialized.json')
        require(parsed(marker, private=True) == anchor
            and sha(read(marker, private=True)) == summary['pins']['anchor.json'], 'V4_PARENT_INITIALIZATION_DIFFERS')
        require(set(grant) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
            and grant['approved'] is True and grant['purpose'] == original['purpose']
            and grant['binding_sha256'] == sha(encoded(binding)) and encoded(grant['limits']) == encoded(original['limits'])
            and isinstance(grant['decision_id'], str) and 0 < len(grant['decision_id']) <= 160, 'V4_PARENT_GRANT_INVALID')
        expiry = datetime.fromisoformat(grant['expires_at'])
        require(expiry.tzinfo is not None, 'V4_PARENT_GRANT_TIME_INVALID')
        attempt = values['attempt-1.json']
        require(ledger == {'binding_sha256': sha(encoded(binding)), 'attempts': [attempt]}, 'V4_PARENT_LEDGER_DIFFERS')
        terminal = verified_stopped_terminal(original, binding, files, values, index=0, verdict='REJECT', expiry=expiry,
            report_path=frozen / '.var/independent-v3-semantic-20261107' / (case + '.json'),
            report_sha256=summary['independent_report_sha256'], runs=spec['parent_runs'])
        restore_raw = read(spec['restore_report'])
        restore = parsed(spec['restore_report'])
        require(restore['status'] == 'REAL_V3_PAID_REJECTED_RESULT_RESTORE_PASS_NO_REEXECUTION'
            and restore['case'] == case and restore['semantic'] == 'REJECT'
            and all(restore[key] is True for key in ('all_data_files_equal', 'all_table_rows_equal',
                'external_controls_hashes_equal', 'backup_ready_after_restore'))
            and restore['external_control_files'] == 9 and restore['new_model_calls_during_backup_restore'] == 0
            and restore['original_invocation_count'] == 1, 'V4_PARENT_RESTORE_UNVERIFIED')
        held = nested['historical_held_microcny'] + attempt['reserve_microcny']
        require(type(attempt['reserve_microcny']) is int and held == summary['historical_held_microcny']
            == spec['limits']['historical_held_microcny'] and nested['historical_calls'] + 1
            == summary['historical_calls'] == spec['limits']['historical_calls'], 'V4_HISTORY_TOTALS_DIFFER')
        return {'nested_v2': nested, 'summary_sha256': sha(summary_raw), 'summary_inode': summary_path.stat().st_ino,
            'files': files, 'parent_control': str(control), 'control_inode': control.stat().st_ino,
            'control_device': historical_device(control, _history), 'marker_inode': marker.stat().st_ino,
            'marker_sha256': sha(read(marker, private=True)), 'manifest_sha256': binding['manifest_sha256'],
            'binding_sha256': sha(encoded(binding)), 'terminals': [terminal], 'restore_report_sha256': sha(restore_raw),
            'historical_calls': 6, 'historical_held_microcny': held, 'actual_bill': 'UNKNOWN', 'parent_semantic': 'REJECT'}
    except (OSError, ValueError, KeyError, TypeError, IndexError, sqlite3.DatabaseError, StateStoreError):
        raise ValueError('V4_STOPPED_PARENT_UNVERIFIABLE') from None


def stopped_preclaim_parent(spec: dict[str, Any]) -> dict[str, Any]:
    """Preserve a stopped fee slot without inventing an invocation or output."""
    try:
        context = historical_metadata(spec)
        witness_path: Path = spec['preclaim_parent_witness']
        raw_witness = read(witness_path, private=True)
        require(sha(raw_witness) == spec['preclaim_parent_witness_sha256'], 'PRECLAIM_WITNESS_CHANGED')
        witness = parsed(witness_path, private=True)
        require(set(witness) == {'actual_bill', 'approved_grant_record', 'approved_grant_record_sha256',
            'binding_sha256', 'control', 'historical_calls', 'historical_held_microcny', 'known_real_invocations',
            'manifest_sha256', 'marker_sha256', 'new_fee_authorized', 'note', 'parent_source', 'pins',
            'postrestore_database_sha256', 'postrestore_inventory_sha256', 'preclaim_stop_slots',
            'restore_report', 'restore_report_sha256', 'root_stop_report', 'root_stop_report_sha256',
            'source_revision', 'version'} and witness['version'] == 'v4-r1-preclaim-stopped-parent-v1'
            and witness['actual_bill'] == 'UNKNOWN' and witness['new_fee_authorized'] is False,
            'PRECLAIM_WITNESS_INVALID')
        original = spec['original']
        frozen: Path = spec['frozen_parent_source']
        saved = parsed(original['package'] / 'proposal-not-authorized.json')
        binding = package_binding('v4-r1', _spec=original, _source_root=frozen, _history=context)
        require(binding == saved['binding'] and sha(encoded(binding)) == witness['binding_sha256']
            == spec['historical_binding_sha256'] and binding['manifest_sha256'] == witness['manifest_sha256']
            == spec['historical_manifest_sha256'] and binding['source_revision'] == witness['source_revision']
            == spec['historical_revision'] and str(frozen) == witness['parent_source'], 'PRECLAIM_SOURCE_DIFFERS')
        nested = stopped_v3_parent(original, _history=context)
        require(nested == binding['parent'] and nested['historical_calls'] == 6
            and nested['historical_held_microcny'] == original['limits']['historical_held_microcny'],
            'PRECLAIM_NESTED_HISTORY_DIFFERS')
        control: Path = original['control']
        require(str(control) == witness['control'], 'PRECLAIM_CONTROL_DIFFERS')
        directory(control)
        row = binding['cases'][0]
        case = row['case']
        names = {'anchor.json', 'ledger.json', 'lock', 'grant.json', 'approval-skeleton.json',
            'attempt-1.json', case + '.result.json'}
        require(set(witness['pins']) == names and {path.name for path in control.iterdir()} == names,
            'PRECLAIM_UNKNOWN_FILE')
        files = {}
        values = {}
        for name, expected in witness['pins'].items():
            path = control / name
            raw = read(path, private=True)
            require(sha(raw) == expected, 'PRECLAIM_FILE_CHANGED')
            meta = path.stat()
            files[name] = {'sha256': sha(raw), 'device': historical_device(path, None), 'inode': meta.st_ino, 'bytes': len(raw)}
            values[name] = parsed(path, private=True)
        anchor, ledger, grant = (values[name] for name in ('anchor.json', 'ledger.json', 'grant.json'))
        require(anchor == {'binding_sha256': sha(encoded(binding)), 'control_inode': control.stat().st_ino,
            'control_device': historical_device(control, context)}, 'PRECLAIM_CONTROL_IDENTITY_DIFFERS')
        marker = control.with_name(control.name + '-initialized.json')
        require(parsed(marker, private=True) == anchor and sha(read(marker, private=True)) == witness['marker_sha256'],
            'PRECLAIM_MARKER_DIFFERS')
        require(set(grant) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
            and grant['approved'] is True and grant['purpose'] == original['purpose']
            and grant['binding_sha256'] == sha(encoded(binding)) and encoded(grant['limits']) == encoded(original['limits'])
            and isinstance(grant['decision_id'], str) and 0 < len(grant['decision_id']) <= 160
            and datetime.fromisoformat(grant['expires_at']).tzinfo is not None, 'PRECLAIM_OLD_GRANT_INVALID')
        attempt = values['attempt-1.json']
        require(set(attempt) == {'case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'grant_sha256'}
            and all(attempt[key] == row[key] for key in attempt if key != 'grant_sha256')
            and attempt['grant_sha256'] == files['grant.json']['sha256']
            and type(attempt['reserve_microcny']) is int
            and ledger == {'binding_sha256': sha(encoded(binding)), 'attempts': [attempt]}, 'PRECLAIM_ATTEMPT_DIFFERS')
        tables = {'distillation_execution_checkpoints', 'system_synthesis_cloud_authorizations',
            'system_synthesis_result_receipts', 'distillation_resource_usage',
            'distillation_cloud_response_failures', 'distillation_no_new_intelligence_results'}
        result = values[case + '.result.json']
        require(result == {**attempt, 'actual_bill': 'UNKNOWN', 'semantic': 'NOT_REVIEWED', 'send_attempted': False,
            'state_trace': {table: [] for table in tables}, 'status': 'UNKNOWN_STOP', 'trace_status': 'VERIFIED_PERSISTED_STATE'}
            and result['send_attempted'] is False, 'PRECLAIM_RESULT_NOT_PROVEN')
        reports = {}
        for name in ('approved_grant_record', 'root_stop_report', 'restore_report'):
            path = Path(witness[name])
            require(path.is_relative_to(frozen / '.var/final-checks/v4-real-20261107'), 'PRECLAIM_REPORT_PATH_DIFFERS')
            raw = read(path, private=True)
            require(sha(raw) == witness[name + '_sha256'], 'PRECLAIM_REPORT_CHANGED')
            reports[name] = parsed(path, private=True)
        approval = reports['approved_grant_record']
        require(approval['status'] == 'USER_EXPLICITLY_APPROVED_BOUNDED_V4'
            and approval['decision_id'] == grant['decision_id'] and approval['expires_at'] == grant['expires_at']
            and approval['grant_sha256'] == files['grant.json']['sha256']
            and approval['binding_sha256'] == sha(encoded(binding)) and encoded(approval['limits']) == encoded(original['limits'])
            and approval['source_revision'] == binding['source_revision'] and approval['new_attempts_before_dispatch'] == 0
            and approval['qualification'] == 'CLOSED' and approval['actual_bill'] == 'UNKNOWN', 'PRECLAIM_APPROVAL_DIFFERS')
        stop = reports['root_stop_report']
        require(stop['status'] == 'V4_BATCH_STOPPED_PRECLAIM_QUALIFICATION_CAP_MISMATCH'
            and stop['case'] == case and stop['binding_sha256'] == sha(encoded(binding))
            and stop['source_revision'] == binding['source_revision']
            and stop['actual_result_sha256'] == files[case + '.result.json']['sha256']
            and stop['result_status'] == 'UNKNOWN_STOP' and stop['send_attempted'] is False
            and stop['new_real_model_invocations'] == 0 and stop['raw_final_or_receipt_exists'] is False
            and stop['target_execution_trace_rows'] == {table: 0 for table in tables}
            and stop['new_reserve_microcny'] == attempt['reserve_microcny']
            and stop['qualification'] == 'CLOSED', 'PRECLAIM_ROOT_STOP_DIFFERS')
        restore = reports['restore_report']
        require(restore['status'] == 'REAL_V4_PRECLAIM_STOPPED_RESULT_RESTORE_PASS_NO_REEXECUTION'
            and restore['case'] == case and restore['result_status'] == 'UNKNOWN_STOP'
            and all(restore[key] is True for key in ('all_data_files_equal', 'all_table_rows_equal',
                'external_controls_hashes_equal', 'backup_ready_after_restore', 'backup_ready_before'))
            and restore['external_control_files'] == 7 and restore['new_fee_attempts_during_backup_restore'] == 0
            and restore['new_model_calls_during_backup_restore'] == 0 and restore['target_invocation_count'] == 0
            and restore['original_stopped_fee_hold_microcny'] == attempt['reserve_microcny'], 'PRECLAIM_RESTORE_UNPROVEN')
        root = spec['parent_runs'] / case
        inputs.safe_tree(root)
        database = root / 'state.sqlite3'
        database_sha = sha(read(database))
        require(database_sha == witness['postrestore_database_sha256'], 'PRECLAIM_DATABASE_CHANGED')
        repository = SQLiteStateRepository(database)
        repository.bind_source_storage(root / 'data')
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            p.verify_database(repository, connection)
            for table in tables | {'system_synthesis_input_proofs'}:
                require(connection.execute(f'SELECT count(*) FROM {table} WHERE execution_id=?',
                    (attempt['execution_id'],)).fetchone()[0] == 0, 'PRECLAIM_EXECUTION_NOT_EMPTY')
        inventory = inputs.inventory(root)
        require(inventory == inputs.inventory(original['package'] / 'cases' / case / 'project')
            and sha(encoded(inventory)) == witness['postrestore_inventory_sha256']
            and len(inventory['tables']) == restore['sql_tables'] and len(inventory['data']) == restore['data_files'],
            'PRECLAIM_SOURCE_INVENTORY_DIFFERS')
        inputs.managed_parent_preflight(root)
        require(database_sha == sha(read(database)), 'PRECLAIM_DATABASE_CHANGED_DURING_READ')
        held = nested['historical_held_microcny'] + attempt['reserve_microcny']
        require(type(witness['known_real_invocations']) is int and witness['known_real_invocations'] == 6
            and type(witness['preclaim_stop_slots']) is int and witness['preclaim_stop_slots'] == 1
            and witness['historical_calls'] == spec['limits']['historical_calls'] == nested['historical_calls'] + 1
            and witness['historical_held_microcny'] == spec['limits']['historical_held_microcny'] == held,
            'PRECLAIM_ACCOUNTING_DIFFERS')
        require(historical_metadata(spec) == context, 'CONTINUITY_CHANGED_DURING_HISTORY_READ')
        current = {} if context is None else {'device_continuity': context.evidence()}
        return {**current, 'nested_v4': nested, 'witness_sha256': sha(raw_witness), 'witness_inode': witness_path.stat().st_ino,
            'files': files, 'parent_control': str(control), 'control_inode': control.stat().st_ino,
            'control_device': historical_device(control, None), 'marker_inode': marker.stat().st_ino,
            'marker_sha256': sha(read(marker, private=True)), 'manifest_sha256': binding['manifest_sha256'],
            'binding_sha256': sha(encoded(binding)), 'database_sha256': database_sha,
            'inventory_sha256': sha(encoded(inventory)), 'historical_calls': 7, 'known_real_invocations': 6,
            'preclaim_stop_slots': 1, 'historical_held_microcny': held, 'actual_bill': 'UNKNOWN', 'parent_status': 'UNKNOWN_STOP'}
    except (OSError, ValueError, KeyError, TypeError, IndexError, sqlite3.DatabaseError, StateStoreError):
        raise ValueError('PRECLAIM_PARENT_UNVERIFIABLE') from None


def package_binding(variant: str = 'v1-r4', *, _spec: dict[str, Any] | None = None,
    _source_root: Path = REPO, _history: HistoricalMetadata | None = None) -> dict[str, Any]:
    spec = trial_spec(variant) if _spec is None else _spec
    require(spec['variant'] == variant, 'TRIAL_VARIANT_UNKNOWN')
    package: Path = spec['package']
    manifest_sha = sha(read(package / 'manifest.json'))
    require(spec['manifest_sha256'] is None or manifest_sha == spec['manifest_sha256'], 'MANIFEST_CHANGED')
    manifest = parsed(package / 'manifest.json')
    require(manifest['status'] == 'PREPARED_NOT_AUTHORIZED' and manifest['qualification'] == 'CLOSED'
        and manifest['case_count'] == 8 and tuple(c['case'] for c in manifest['cases']) == tuple(spec['order']), 'CASE_SET_CHANGED')
    require(sha(read(package / 'input-only-oracle.md')) == manifest['oracle_sha256'], 'ORACLE_CHANGED')
    require(parsed(package / 'immutable-profile.json') == profile.resolve_profile(spec['profile_id']), 'PROFILE_CHANGED')
    require(sha(read(package / 'source-code-inventory.json')) == manifest['source_code_inventory_sha256'], 'INPUT_SOURCE_INVENTORY_CHANGED')
    seed_before = parsed(package / 'source-before.json')
    require(seed_before == parsed(package / 'source-after.json') == inputs.inventory(spec['seed']), 'SEED_CHANGED')
    for name, expected in manifest['official_supplement']['document_hashes'].items():
        require(sha(read(package / 'official-supplement' / Path(name).name)) == expected, 'PRICE_DOCUMENT_CHANGED')
    cases = []
    for row in manifest['cases']:
        root = package / 'cases' / row['case'] / 'project'
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
            and proof['transport'] == profile.resolve_profile(spec['profile_id']), 'PROOF_CHANGED')
        require(profile.canonical(parsed(artifacts / 'provider-body.json')) == proof['provider_wire'], 'BODY_CHANGED')
        p.request_from_proof(p.PreparedSynthesis(row['execution_id'], profile.canonical(proof), row['proof_sha256']))
        cases.append({key: row[key] for key in ('case', 'execution_id', 'proof_sha256', 'wire_sha256',
            'reserve_microcny', 'language', 'video_id', 'source_identity', 'source_refs_sha256', 'summary_sha256', 'expected')})
    require(sum(c['reserve_microcny'] for c in cases) == spec['limits']['runner_held_microcny']
        and all(type(c['reserve_microcny']) is int and 0 < c['reserve_microcny'] <= spec['limits']['per_call_microcny'] for c in cases), 'RESERVE_CHANGED')
    binding = {'manifest_sha256': manifest_sha, 'oracle_sha256': manifest['oracle_sha256'],
        'profile': profile.resolve_profile(spec['profile_id']), 'source_hashes': code_hashes() if _source_root == REPO else code_hashes(source_root=_source_root),
        'seed_inventory_sha256': sha(encoded(seed_before)),
        'supplementary_price_documents': manifest['official_supplement'],
        'source_revision': subprocess.check_output(['git', '-C', str(_source_root), 'rev-parse', 'HEAD'], text=True).strip(),
        'cases': cases}

    if variant == 'v2-r1':
        original = package_binding('v1-r4', _spec=spec['original'], _source_root=_source_root, _history=_history)
        require(manifest.get('variant') == variant
            and manifest.get('parent_input_manifest_sha256') == original['manifest_sha256']
            and manifest['oracle_sha256'] == original['oracle_sha256'], 'V2_INPUT_PARENT_DIFFERS')
        old_package = spec['original']['package']
        for row, old in zip(manifest['cases'], original['cases'], strict=True):
            require(all(row[k] == old[k] for k in ('case', 'video_id', 'language', 'source_identity',
                'summary_sha256', 'source_refs_sha256', 'expected')), 'V2_SOURCE_METADATA_CHANGED')
            old_proof = parsed(old_package / 'cases' / old['case'] / 'artifacts/prepared-proof.json')
            new_proof = parsed(package / 'cases' / row['case'] / 'artifacts/prepared-proof.json')
            require(new_proof['capture'] == old_proof['capture'] and new_proof['command'] == old_proof['command']
                and inputs.inventory(package / 'cases' / row['case'] / 'project')
                == inputs.inventory(old_package / 'cases' / old['case'] / 'project'), 'V2_SOURCE_SNAPSHOT_CHANGED')
        parent = parent_binding(spec, _history=_history)
        require(manifest.get('parent_summary_sha256') == spec['bundle_parent_summary_sha256'], 'V2_PARENT_SUMMARY_DIFFERS')
        binding.update(variant=variant, parent=parent, original_manifest_sha256=original['manifest_sha256'])
    if variant in {'v3-r1', 'v4-r1', 'v4-r2'}:
        parent = (stopped_preclaim_parent(spec) if variant == 'v4-r2'
            else stopped_v3_parent(spec, _history=_history) if variant == 'v4-r1' else stopped_v2_parent(spec, _history=_history))
        old_package = spec['original']['package']
        old_manifest = parsed(old_package / 'manifest.json')
        require(manifest.get('variant') == variant
            and manifest.get('parent_input_manifest_sha256') == parent['manifest_sha256']
            and manifest.get('parent_summary_sha256') == sha(encoded(parent))
            and manifest['oracle_sha256'] == old_manifest['oracle_sha256'], 'V3_INPUT_PARENT_DIFFERS')
        for row, old in zip(manifest['cases'], old_manifest['cases'], strict=True):
            require(all(row[k] == old[k] for k in ('case', 'video_id', 'language', 'source_identity',
                'summary_sha256', 'source_refs_sha256', 'expected')), 'V3_SOURCE_METADATA_CHANGED')
            old_proof = parsed(old_package / 'cases' / old['case'] / 'artifacts/prepared-proof.json')
            new_proof = parsed(package / 'cases' / row['case'] / 'artifacts/prepared-proof.json')
            require(new_proof['capture'] == old_proof['capture'] and new_proof['command'] == old_proof['command']
                and inputs.inventory(package / 'cases' / row['case'] / 'project')
                == inputs.inventory(old_package / 'cases' / old['case'] / 'project'), 'V3_SOURCE_SNAPSHOT_CHANGED')
            if variant in {'v4-r1', 'v4-r2'}:
                old_messages = parsed(old_package / 'cases' / old['case'] / 'artifacts/provider-body.json')['messages']
                new_messages = parsed(package / 'cases' / row['case'] / 'artifacts/provider-body.json')['messages']
                require(new_messages[:3] == old_messages[:3], 'V4_SOURCE_MESSAGES_CHANGED')
        binding.update(variant=variant, parent=parent, original_manifest_sha256=parent['manifest_sha256'])
        if variant == 'v4-r2':
            binding.update(known_real_invocations=parent['known_real_invocations'],
                preclaim_stop_slots=parent['preclaim_stop_slots'])
            require(manifest.get('known_real_invocations') == parent['known_real_invocations']
                and manifest.get('preclaim_stop_slots') == parent['preclaim_stop_slots'], 'PRECLAIM_COUNTS_DIFFER')
            for row, old in zip(cases, old_manifest['cases'], strict=True):
                require(all(row[key] == old[key] for key in ('execution_id', 'proof_sha256',
                    'wire_sha256', 'reserve_microcny')), 'V4_R2_REQUEST_CHANGED')
    return binding


class QACredentialStore(MacOSKeychainCredentialStore):
    _service = b'com.huangbuqubunao.intelligence.qa.kimi-public-20261029'
    _account = b'api-key'


class Trial:
    def __init__(self, *, variant: str = 'v1-r4', control: Path | None = None, runs: Path | None = None,
        _spec: dict[str, Any] | None = None) -> None:
        # Internal injection for isolated tests only. CLI offers no path/key/model overrides.
        self.spec = trial_spec(variant) if _spec is None else _spec
        require(self.spec['variant'] == variant, 'TRIAL_VARIANT_UNKNOWN')
        self.variant = variant
        self.control = control if control is not None else self.spec['control']
        self.runs = runs if runs is not None else self.spec['runs']

    def initialization_marker(self) -> Path:
        return Path(self.control).with_name(Path(self.control).name + '-initialized.json')

    def proposal(self) -> dict[str, Any]:
        binding = package_binding(self.variant, _spec=self.spec)
        return {'status': 'NOT_AUTHORIZED', 'binding': binding, 'limits': self.spec['limits'],
            'approval': {'approved': False, 'purpose': self.spec['purpose'],
                'decision_id': '', 'expires_at': '', 'binding_sha256': sha(encoded(binding)),
                'limits': self.spec['limits']}}

    def prepare(self) -> dict[str, Any]:
        report = self.proposal()
        binding = report['binding']
        directory(self.control, create=True)
        anchor, ledger = self.control / 'anchor.json', self.control / 'ledger.json'
        if not anchor.exists():
            require(not any(self.control.iterdir()), 'LEDGER_INITIALIZATION_REFUSED')
            if self.variant in {'v2-r1', 'v3-r1', 'v4-r1', 'v4-r2'}:
                require(not self.initialization_marker().exists() and not self.runs.exists(), 'CHILD_INITIALIZATION_ALREADY_CONSUMED')
                once(self.initialization_marker(), {'binding_sha256': sha(encoded(binding)),
                    'control_inode': self.control.stat().st_ino, 'control_device': self.control.stat().st_dev})
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
        fds = []
        try:
            if self.variant == 'v4-r2':
                parent = stopped_preclaim_parent(self.spec)
                ancestor = parent['nested_v4']['nested_v2']
                paths = [Path(ancestor['nested_v1']['parent_control']), Path(ancestor['parent_control']),
                    Path(parent['nested_v4']['parent_control']), self.spec['original']['control']]
            elif self.variant == 'v4-r1':
                parent = stopped_v3_parent(self.spec)
                paths = [Path(parent['nested_v2']['nested_v1']['parent_control']),
                    Path(parent['nested_v2']['parent_control']), self.spec['original']['control']]
            elif self.variant == 'v3-r1':
                parent = stopped_v2_parent(self.spec)
                paths = [Path(parent['nested_v1']['parent_control']), self.spec['original']['control']]
            elif self.variant == 'v2-r1':
                parent = parent_binding(self.spec)
                paths = [Path(parent['parent_control'])]
            else:
                parent, paths = None, []
            for path in paths:
                fd = os.open(path / 'lock', os.O_RDONLY | os.O_NOFOLLOW)
                fds.append(fd)
                fcntl.flock(fd, fcntl.LOCK_SH)
            if parent is not None:
                current = (stopped_preclaim_parent(self.spec) if self.variant == 'v4-r2'
                    else stopped_v3_parent(self.spec) if self.variant == 'v4-r1'
                    else stopped_v2_parent(self.spec) if self.variant == 'v3-r1' else parent_binding(self.spec))
                require(current == parent, 'PARENT_CHANGED_WHILE_LOCKING')
            fd = os.open(self.control / 'lock', os.O_RDONLY | os.O_NOFOLLOW)
            fds.append(fd)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            for fd in reversed(fds):
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def ledger(self, binding: dict[str, Any]) -> dict[str, Any]:
        try:
            anchor = parsed(self.control / 'anchor.json', private=True)
            value = parsed(self.control / 'ledger.json', private=True)
            require(anchor == {'binding_sha256': sha(encoded(binding)), 'control_inode': self.control.stat().st_ino,
                'control_device': self.control.stat().st_dev}, 'LEDGER_ANCHOR_DIFFERS')
            if self.variant in {'v2-r1', 'v3-r1', 'v4-r1', 'v4-r2'}:
                require(parsed(self.initialization_marker(), private=True) == anchor, 'CHILD_INITIALIZATION_HISTORY_MISSING')
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
            if self.variant in {'v2-r1', 'v3-r1', 'v4-r1', 'v4-r2'}:
                parent = (stopped_preclaim_parent(self.spec) if self.variant == 'v4-r2'
                    else stopped_v3_parent(self.spec) if self.variant == 'v4-r1'
                    else stopped_v2_parent(self.spec) if self.variant == 'v3-r1' else parent_binding(self.spec))
                require(parent == binding['parent'], 'PARENT_CHANGED')
            value = parsed(self.control / 'grant.json', private=True)
            require(set(value) == {'approved', 'purpose', 'decision_id', 'expires_at', 'binding_sha256', 'limits'}
                and value['approved'] is True and value['purpose'] == self.spec['purpose']
                and isinstance(value['decision_id'], str) and 1 <= len(value['decision_id']) <= 160
                and value['binding_sha256'] == sha(encoded(binding)) and value['limits'] == self.spec['limits']
                and encoded(value['limits']) == encoded(self.spec['limits']), 'GRANT_INVALID')
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
        binding = package_binding(self.variant, _spec=self.spec)
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
                inputs.clone(self.spec['package'] / 'cases' / row['case'] / 'project', root)
                require(inputs.inventory(root)['schema'] == 44, 'QUALIFICATION_REQUIRES_SCHEMA44')
                active = inputs.runtime(root, [datetime.now(UTC)])
                before = inputs.inventory(root)
                require(before == inputs.inventory(self.spec['package'] / 'cases' / row['case'] / 'project'), 'FACTORY_CHANGED_SOURCE')
                review, value = inputs.ordinary_review(active, row['video_id'], row['case'], profile_id=self.spec['profile_id'])
                require(review['verified_input_hash'] == row['proof_sha256']
                    and review['execution_id'] == row['execution_id']
                    and value.input_json == profile.canonical(parsed(self.spec['package'] / 'cases' / row['case'] / 'artifacts/prepared-proof.json'))
                    and inputs.inventory(root) == before, 'NORMAL_REVIEW_CHANGED')
            self.grant(binding)
            require(code_hashes() == binding['source_hashes'], 'SOURCE_CHANGED_BEFORE_RESERVATION')
            attempt = {k: row[k] for k in ('case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny')}
            attempt['grant_sha256'] = grant_sha
            ledger['attempts'].append(attempt)
            require(self.spec['limits']['historical_held_microcny'] + sum(a['reserve_microcny'] for a in ledger['attempts'])
                + self.spec['limits']['gui_held_microcny'] <= self.spec['limits']['total_microcny'], 'CUMULATIVE_BUDGET_EXCEEDED')
            # Immutable reservation detects journal rollback/truncation. A crash
            # between these writes is an orphaned hold and permanently blocks,
            # never evidence that the invocation was free or safe to replay.
            once(self.control / f'attempt-{index + 1}.json', attempt)
            replace_ledger(self.control / 'ledger.json', ledger)  # BEFORE key/claim/wire
            result: dict[str, Any] = {**attempt, 'status': 'UNKNOWN_STOP', 'actual_bill': 'UNKNOWN',
                'send_attempted': False, 'semantic': 'NOT_REVIEWED'}
            final: list[str] = []

            def resolve() -> str:
                require(self.grant(binding)[1] == grant_sha and self.ledger(binding) == ledger
                    and code_hashes() == binding['source_hashes'], 'AUTHORITY_CHANGED')
                secret = (credential or QACredentialStore().get)()
                require(isinstance(secret, str) and secret and '\r' not in secret and '\n' not in secret, 'CREDENTIAL_UNAVAILABLE')
                assert isinstance(secret, str)
                require(self.grant(binding)[1] == grant_sha and self.ledger(binding) == ledger
                    and code_hashes() == binding['source_hashes'], 'AUTHORITY_CHANGED_AFTER_KEY')
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
                original = (active.application._cloud_synthesis_v4_service if self.variant in {'v4-r1', 'v4-r2'}
                    else active.application._cloud_synthesis_v3_service if self.variant == 'v3-r1'
                    else active.application._cloud_synthesis_v2_service if self.variant == 'v2-r1'
                    else active.application._cloud_synthesis_service)
                require(original is not None, 'SYNTHESIS_SERVICE_REQUIRED')
                authorization = CloudDistillationAuthorization(cloud_enabled=True, provider=profile.PAIR[0],
                    model=profile.PAIR[1], credential_available=True, provider_available=True,
                    qualification_input_hash=row['proof_sha256'], qualification_max_calls=1)
                adapter = (MoonshotReadableSummarySynthesisTransport if self.variant in {'v4-r1', 'v4-r2'}
                    else MoonshotSourceLevelSynthesisTransport if self.variant == 'v3-r1'
                    else MoonshotAttributionSynthesisTransport if self.variant == 'v2-r1' else MoonshotSystemSynthesisTransport)
                transport = adapter(authorization=authorization,
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
                require(self.grant(binding)[1] == grant_sha and self.ledger(binding) == ledger
                    and code_hashes() == binding['source_hashes'], 'AUTHORITY_CHANGED_BEFORE_CLAIM')
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
                require(package_binding(self.variant, _spec=self.spec) == binding, 'FROZEN_PACKAGE_CHANGED')
            except Exception:
                result['status'] = 'UNKNOWN_STOP'
            once(self.control / (row['case'] + '.result.json'), result)
            return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'execute', 'describe', 'materialize', 'location-proposal'), default='prepare', nargs='?')
    parser.add_argument('--variant', choices=('v1-r4', 'v2-r1', 'v3-r1', 'v4-r1', 'v4-r2'), default='v1-r4')
    args = parser.parse_args()
    trial = Trial(variant=args.variant)
    if args.action == 'prepare':
        report = trial.prepare()
    elif args.action == 'check':
        binding = package_binding(args.variant)
        with trial.locked():
            ledger = trial.ledger(binding)
        report = {'status': 'CHECKED_NOT_AUTHORIZED', 'binding': binding, 'limits': trial.spec['limits'], 'attempts': ledger['attempts']}
    elif args.action == 'location-proposal':
        require(args.variant == 'v2-r1', 'V2_LOCATION_PROPOSAL_ONLY')
        with inputs.offline():
            report = parent_location_proposal(trial.spec)
    elif args.action == 'describe':
        report = trial.proposal()
    elif args.action == 'materialize':
        require(args.variant in {'v2-r1', 'v3-r1', 'v4-r1', 'v4-r2'}, 'FINITE_MATERIALIZATION_ONLY')
        specification = importlib.util.spec_from_file_location('_finite_v2_materializer', Path(__file__).with_name('materialize_synthesis_v2_inputs.py'))
        assert specification is not None and specification.loader is not None
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        report = module.materialize(trial.spec)
    else:
        report = trial.execute()
    print(profile.canonical(report))


if __name__ == '__main__':
    main()
