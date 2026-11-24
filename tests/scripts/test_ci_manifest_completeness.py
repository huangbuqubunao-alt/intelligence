"""Verify scripts/ci_test_manifest.py leaves zero collected pytest tests unallocated."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.ci_test_manifest import (
    INTEGRATION_SHARD_COUNT,
    UNIT_SHARD_COUNT,
    integration_files,
    unit_files,
    verify_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ci_manifest_covers_every_collected_test_and_restores_e2e_smoke() -> None:
    summary = verify_manifest(python_exe=sys.executable, root=REPO_ROOT)
    assert summary["total_collected"] > 7300
    assert summary["total_runnable"] > 7100
    assert (
        summary["total_runnable"]
        + summary["gov001_excluded"]
        + summary["capacity_excluded"]
        == summary["total_collected"]
    )

    u_shards = [
        unit_files(REPO_ROOT)[i::UNIT_SHARD_COUNT] for i in range(UNIT_SHARD_COUNT)
    ]
    i_shards = [
        integration_files(REPO_ROOT)[i::INTEGRATION_SHARD_COUNT]
        for i in range(INTEGRATION_SHARD_COUNT)
    ]
    all_u = [f for s in u_shards for f in s]
    all_i = [f for s in i_shards for f in s]

    # Recover previously dropped runnable E2E & smoke files (P1-6)
    for required in (
        "tests/e2e/test_failure_recovery.py",
        "tests/e2e/test_mvp_flow.py",
        "tests/e2e/test_po_demo.py",
        "tests/test_smoke.py",
        "tests/scripts/test_ci_manifest_completeness.py",
    ):
        assert required in all_i

    # Standalone contract tests inside mixed GOV-001 files stay enabled in unit shards
    for standalone_mixed in (
        "tests/unit/test_bounded_synthesis_v2_trial.py",
        "tests/unit/test_bounded_synthesis_v3_trial.py",
        "tests/unit/test_bounded_synthesis_v4_trial.py",
        "tests/unit/test_bounded_synthesis_v4_r2_trial.py",
        "tests/unit/test_bounded_trial_device_continuity.py",
    ):
        assert standalone_mixed in all_u

    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "ci_test_manifest.py"), "verify"],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "CI manifest verified:" in proc.stdout
