"""v5 controller grant scoping: user-approved case count and reservation cap only widen."""
from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/validation/judgment_v5_trial.py'
_spec = importlib.util.spec_from_file_location('judgment_v5_trial_under_test', SCRIPT)
assert _spec is not None and _spec.loader is not None
trial_module: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trial_module)

VALUE = {'variant': 'owned-unit', 'cases': [{'case': f'case-{i}', 'reserve_microcny': 1_000_000 + i} for i in range(8)]}


def control(tmp_path: Path) -> Any:
    root = tmp_path / 'control'
    root.mkdir(mode=0o700)
    os.chmod(tmp_path, 0o700)
    return trial_module.JudgmentTrial(control=root, runs=tmp_path / 'runs', _binding=lambda: VALUE)


def grant(cases: int, microcny: int, *, hours: int = 1, **changes: Any) -> dict[str, Any]:
    value = {'approved': True, 'purpose': trial_module.PURPOSE, 'decision_id': 'owned-unit-decision',
        'expires_at': (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
        'binding_sha256': trial_module.sha(trial_module.encoded(VALUE)), 'limits': dict(trial_module.LIMITS),
        'approved_cases': cases, 'approved_new_microcny': microcny}
    value.update(changes)
    return value


def test_two_case_grant_scope_is_exact(tmp_path: Path) -> None:
    trial = control(tmp_path)
    with pytest.raises(ValueError, match='GRANT_REQUIRED'):
        trial.grant(VALUE)
    trial_module.once(trial.control / 'grant.json', grant(2, 2_000_001))
    assert trial.current_scope(VALUE) == (2, 2_000_001)
    assert len(trial.grant(VALUE)) == 64


@pytest.mark.parametrize('bad', [
    {'approved_cases': 0}, {'approved_cases': 9}, {'approved_cases': True},
    {'approved_new_microcny': 2_000_000},  # below the two exact reserves
    {'approved_new_microcny': trial_module.LIMITS['new_total_microcny'] + 1},
    {'approved': False}, {'binding_sha256': '0' * 64}, {'limits': {}},
])
def test_invalid_or_underfunded_grant_is_refused(tmp_path: Path, bad: dict[str, Any]) -> None:
    trial = control(tmp_path)
    trial_module.once(trial.control / 'grant.json', grant(2, 2_000_001, **bad))
    with pytest.raises(ValueError, match='GRANT_REQUIRED'):
        trial.grant(VALUE)


def test_expired_grant_is_refused(tmp_path: Path) -> None:
    trial = control(tmp_path)
    trial_module.once(trial.control / 'grant.json', grant(2, 2_000_001, hours=-1))
    with pytest.raises(ValueError, match='GRANT_REQUIRED'):
        trial.grant(VALUE)


def test_successor_grant_only_widens_and_keeps_history(tmp_path: Path) -> None:
    trial = control(tmp_path)
    trial_module.once(trial.control / 'grant.json', grant(2, 2_000_001))
    first = trial.grant(VALUE)
    trial_module.once(trial.control / 'grant-2.json', grant(8, 8_000_028))
    assert trial.current_scope(VALUE) == (8, 8_000_028)
    assert [digest for _, digest in trial.grants(VALUE)][0] == first and trial.grant(VALUE) != first
    trial_module.once(trial.control / 'grant-3.json', grant(8, 9_000_000))
    with pytest.raises(ValueError, match='GRANT_REQUIRED'):
        trial.grants(VALUE)  # case count must strictly widen


def test_grant_sequence_gap_is_refused(tmp_path: Path) -> None:
    trial = control(tmp_path)
    trial_module.once(trial.control / 'grant.json', grant(2, 2_000_001))
    trial_module.once(trial.control / 'grant-3.json', grant(4, 4_000_006))
    with pytest.raises(ValueError, match='GRANT_REQUIRED'):
        trial.grants(VALUE)


def test_v5_order_and_falsification_stop_are_declared() -> None:
    assert trial_module.ORDER[:2] == ('public-IwglW_hIL_g-en', 'public-IwglW_hIL_g-zh-CN')
    assert 'POSITIVE_CAPABILITY_FALSIFIED_STOP' in SCRIPT.read_text()
