"""Single-source-of-truth Python CI sharding and collected-nodeid completeness gate."""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

UNIT_SHARD_COUNT = 4
INTEGRATION_SHARD_COUNT = 8

# Root sealed TASK-016 trial fixture (`owned_synthetic_package` autouse=True fails
# closed by design against post-seal tree hashes).
EXCLUDED_GOV001_FILES: frozenset[str] = frozenset(
    {
        "tests/unit/test_bounded_synthesis_trial.py",
    }
)

# Sealed-fixture functions in mixed trial files whose standalone contract tests
# still run and pass on clean trees.
GOV001_UNIT_DESELECT: dict[str, tuple[str, ...]] = {
    "tests/unit/test_synthesis_attribution_v2.py": (
        "tests/unit/test_synthesis_attribution_v2.py::"
        "test_actual_factory_declares_finite_profiles_and_keeps_synthesis_unqualified",
    ),
    "tests/unit/test_synthesis_judgment_v5.py": (
        "tests/unit/test_synthesis_judgment_v5.py::"
        "test_v5_transport_is_distinct_and_sealed_qualification_never_cross_permits",
    ),
    "tests/unit/test_bounded_synthesis_v2_trial.py": tuple(
        f"tests/unit/test_bounded_synthesis_v2_trial.py::{name}"
        for name in (
            "test_parent_rejection_is_counted_and_never_becomes_child_fee_permission",
            "test_exact_child_fake_wire_keeps_parent_bytes_and_counts_hold_before_key",
            "test_no_new_authority_precedes_key_or_claim",
            "test_parent_history_tampering_stops_even_when_resigned_fixture_summary",
            "test_child_unknown_or_failure_stops_without_releasing_hold",
            "test_eight_v2_cases_require_exact_semantics_and_refuse_ninth",
            "test_v2_child_rejection_stops_next_case",
            "test_v2_concurrent_execute_has_one_immutable_hold",
            "test_changed_parent_is_rechecked_at_dispatch_boundaries",
            "test_parent_identity_and_private_files_are_bound",
            "test_v2_restart_and_restore_cannot_reset_consumed_authority",
            "test_v2_concurrent_prepare_cannot_replace_initialization",
            "test_expired_parent_retains_only_historically_authorized_hold",
            "test_parent_extra_or_nonterminal_history_is_rejected",
            "test_v2_changed_source_binding_requires_new_grant",
            "test_location_only_proof_preserves_original_history_and_requires_child_fee_grant",
            "test_location_only_proof_is_exact_and_bound",
            "test_location_proof_cannot_accept_another_device_transition",
        )
    ),
    "tests/unit/test_bounded_synthesis_v3_trial.py": tuple(
        f"tests/unit/test_bounded_synthesis_v3_trial.py::{name}"
        for name in (
            "test_five_calls_are_held_and_old_rejection_blocks_only_old_batch",
            "test_new_exact_grant_precedes_key_and_claim",
            "test_old_parent_tamper_refuses_before_new_control",
            "test_every_new_case_needs_new_semantics_and_ninth_is_forbidden",
            "test_unknown_or_failure_retains_once_hold_and_stops",
            "test_parent_rechecked_at_each_dispatch_boundary",
            "test_concurrent_call_and_whole_control_loss_keep_consumed_marker",
            "test_old_expired_grant_keeps_only_its_historical_authorization",
            "test_crash_after_immutable_hold_cannot_be_reinitialized",
            "test_parent_files_remain_private_and_identity_bound",
            "test_current_source_is_rechecked_around_credential_resolution",
            "test_backup_restore_of_executed_child_preserves_sql_data_and_external_hold",
            "test_old_v2_english_pass_cannot_approve_new_v3_result",
        )
    ),
    "tests/unit/test_bounded_synthesis_v4_trial.py": tuple(
        f"tests/unit/test_bounded_synthesis_v4_trial.py::{name}"
        for name in (
            "test_six_holds_new_permission_and_old_v3_rejection_are_independent",
            "test_all_ten_summary_fields_are_literal_and_original_source_is_exact",
            "test_fresh_exact_grant_precedes_credentials",
            "test_parent_chain_tampering_stops_before_child_creation",
            "test_new_eight_require_new_root_semantics_and_refuse_ninth",
            "test_failed_or_unknown_call_keeps_hold_and_stops_after_restart",
            "test_parent_is_revalidated_at_dispatch_boundaries",
            "test_concurrent_once_and_consumed_control_loss_are_closed",
            "test_orphan_hold_stays_closed_before_credentials",
            "test_current_source_is_rechecked_before_and_after_key",
            "test_child_backup_restore_keeps_all_sql_data_and_external_hold",
            "test_v3_decision_cannot_approve_new_v4_receipt",
            "test_expired_v3_grant_retains_only_its_historical_hold",
            "test_parent_private_file_and_identity_precede_credentials",
            "test_restored_preexecution_parent_database_cannot_erase_old_invocation",
        )
    ),
    "tests/unit/test_bounded_synthesis_v4_r2_trial.py": tuple(
        f"tests/unit/test_bounded_synthesis_v4_r2_trial.py::{name}"
        for name in (
            "test_old_preclaim_slot_is_not_an_invocation_or_new_consent",
            "test_r2_proofs_wires_and_source_match_r1_exactly",
            "test_unproven_parent_closes_before_child_or_key",
            "test_fresh_grant_precedes_key",
            "test_eight_new_receipts_need_new_root_semantics_and_no_ninth",
            "test_new_failure_holds_after_restart",
            "test_parent_revalidated_at_claim_and_key",
            "test_current_source_revalidated_around_key",
            "test_concurrent_once_and_lost_control",
            "test_orphan_hold",
            "test_child_restore_keeps_data_and_outside_hold",
            "test_parent_identity_is_private_and_bound",
            "test_expired_historical_preclaim_grant_does_not_become_new_permission",
            "test_parent_database_identity_and_absent_claim_are_independent_guards",
        )
    ),
    "tests/unit/test_bounded_trial_device_continuity.py": tuple(
        f"tests/unit/test_bounded_trial_device_continuity.py::{name}"
        for name in (
            "test_saved_history_stays_exact_new_parent_binds_current_and_needs_new_grant",
            "test_owned_new_receipt_keeps_current_control_and_original_unknown_parent",
            "test_continuity_drift_rechecked_before_claim_and_after_key",
            "test_missing_continuity_witness_blocks_before_child_control",
        )
    ),
}

# Tests requiring developer-local untracked sibling worktree `.var` artifacts.
CAPACITY_UNIT_DESELECT: dict[str, tuple[str, ...]] = {
    "tests/unit/test_readiness_qwen35_capacity.py": (
        "tests/unit/test_readiness_qwen35_capacity.py::test_projection_is_exact_old_actual_request_except_predict",
        "tests/unit/test_readiness_qwen35_capacity.py::test_capacity_one_attempt_preserves_response_and_stops",
        "tests/unit/test_readiness_qwen35_capacity.py::test_capacity_unpaired_counters_remain_unknown_below_limit",
        "tests/unit/test_readiness_qwen35_capacity.py::test_capacity_preparation_seals_original_input_data_and_fresh_execution",
        "tests/unit/test_readiness_qwen35_capacity.py::test_capacity_external_root_receipt_is_exact",
    ),
}

CAPACITY_INTEGRATION_DESELECT: dict[str, tuple[str, ...]] = {
    "tests/integration/test_local_capacity_composition.py": (
        "tests/integration/test_local_capacity_composition.py::"
        "test_all_original_four_inputs_fit_without_truncating_fifteen_evidence",
    ),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def unit_files(root: Path | None = None) -> list[str]:
    base = root or _repo_root()
    cwd = Path.cwd()
    try:
        os.chdir(base)
        return sorted(
            f
            for f in glob.glob("tests/unit/test_*.py")
            if f not in EXCLUDED_GOV001_FILES
        )
    finally:
        os.chdir(cwd)


def integration_files(root: Path | None = None) -> list[str]:
    base = root or _repo_root()
    cwd = Path.cwd()
    try:
        os.chdir(base)
        return sorted(
            glob.glob("tests/integration/test_*.py")
            + glob.glob("tests/e2e/test_*.py")
            + glob.glob("tests/test_*.py")
            + glob.glob("tests/scripts/test_*.py")
        )
    finally:
        os.chdir(cwd)


def unit_deselects_for_shard(files: list[str]) -> list[str]:
    out: list[str] = []
    for file_path in files:
        out.extend(GOV001_UNIT_DESELECT.get(file_path, ()))
        out.extend(CAPACITY_UNIT_DESELECT.get(file_path, ()))
    return out


def integration_deselects_for_shard(files: list[str]) -> list[str]:
    out: list[str] = []
    for file_path in files:
        out.extend(CAPACITY_INTEGRATION_DESELECT.get(file_path, ()))
    return out


def collect_all_nodeids(python_exe: str | None = None, root: Path | None = None) -> list[str]:
    base = root or _repo_root()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(base) + (
        f"{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else ""
    )
    proc = subprocess.run(
        [python_exe or sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        cwd=base,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"pytest --collect-only failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    nodeids: list[str] = []
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s.startswith("tests/") and "::" in s:
            nodeids.append(s)
    return nodeids


def _matches_rule(nodeid: str, rule: str) -> bool:
    return nodeid == rule or nodeid.startswith(f"{rule}[")


def verify_manifest(python_exe: str | None = None, root: Path | None = None) -> dict[str, int]:
    base = root or _repo_root()
    all_nodeids = collect_all_nodeids(python_exe=python_exe, root=base)
    all_set = set(all_nodeids)
    assert len(all_set) == len(all_nodeids), "Duplicate collected pytest nodeids detected"

    u_shards = [unit_files(base)[i::UNIT_SHARD_COUNT] for i in range(UNIT_SHARD_COUNT)]
    i_shards = [
        integration_files(base)[i::INTEGRATION_SHARD_COUNT]
        for i in range(INTEGRATION_SHARD_COUNT)
    ]

    all_unit_files = [f for s in u_shards for f in s]
    all_integ_files = [f for s in i_shards for f in s]
    if len(all_unit_files) != len(set(all_unit_files)):
        raise RuntimeError("Duplicate file across unit shards")
    if len(all_integ_files) != len(set(all_integ_files)):
        raise RuntimeError("Duplicate file across integration shards")
    overlap_files = set(all_unit_files) & set(all_integ_files)
    if overlap_files:
        raise RuntimeError(f"File overlap between unit & integration shards: {sorted(overlap_files)}")

    shard_file_set = set(all_unit_files) | set(all_integ_files)
    unit_deselect_rules = [
        rule
        for rules in (*GOV001_UNIT_DESELECT.values(), *CAPACITY_UNIT_DESELECT.values())
        for rule in rules
    ]
    integ_deselect_rules = [
        rule for rules in CAPACITY_INTEGRATION_DESELECT.values() for rule in rules
    ]

    # Validate zero stale exclusion rules
    for excl_file in EXCLUDED_GOV001_FILES:
        if not any(nid.startswith(f"{excl_file}::") for nid in all_nodeids):
            raise RuntimeError(f"Stale EXCLUDED_GOV001_FILES entry: {excl_file}")
    for rule in (*unit_deselect_rules, *integ_deselect_rules):
        if not any(_matches_rule(nid, rule) for nid in all_nodeids):
            raise RuntimeError(f"Stale deselect rule (matches 0 tests): {rule}")

    gov001_excluded = 0
    capacity_excluded = 0
    unit_runnable = 0
    integration_runnable = 0
    unallocated: list[str] = []

    gov001_rules = [r for rules in GOV001_UNIT_DESELECT.values() for r in rules]
    cap_unit_rules = [r for rules in CAPACITY_UNIT_DESELECT.values() for r in rules]

    for nid in all_nodeids:
        fpath = nid.split("::", 1)[0]
        if fpath in EXCLUDED_GOV001_FILES:
            gov001_excluded += 1
            continue
        if fpath not in shard_file_set:
            unallocated.append(nid)
            continue
        if fpath in set(all_unit_files):
            if any(_matches_rule(nid, r) for r in gov001_rules):
                gov001_excluded += 1
            elif any(_matches_rule(nid, r) for r in cap_unit_rules):
                capacity_excluded += 1
            else:
                unit_runnable += 1
        else:
            if any(_matches_rule(nid, r) for r in integ_deselect_rules):
                capacity_excluded += 1
            else:
                integration_runnable += 1

    if unallocated:
        raise RuntimeError(
            f"CI sharding omitted {len(unallocated)} collected tests, e.g. {unallocated[:10]}"
        )

    summary = {
        "total_collected": len(all_nodeids),
        "unit_files": len(all_unit_files),
        "integration_files": len(all_integ_files),
        "unit_runnable": unit_runnable,
        "integration_runnable": integration_runnable,
        "total_runnable": unit_runnable + integration_runnable,
        "gov001_excluded": gov001_excluded,
        "capacity_excluded": capacity_excluded,
    }
    if (
        summary["total_runnable"] + summary["gov001_excluded"] + summary["capacity_excluded"]
        != summary["total_collected"]
    ):
        raise RuntimeError(f"Partition sum mismatch: {summary}")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Workspace CI sharding manifest & gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="Verify collected pytest IDs == union of shards + exclusions")
    p_u = sub.add_parser("run-unit", help="Run a python-unit-full shard")
    p_u.add_argument("--shard", type=int, required=True)
    p_i = sub.add_parser("run-integration", help="Run a python-integration-full shard")
    p_i.add_argument("--shard", type=int, required=True)

    args = parser.parse_args(argv)
    root = _repo_root()
    if args.cmd == "verify":
        info = verify_manifest(root=root)
        print(
            "CI manifest verified:"
            f" total_collected={info['total_collected']}"
            f" unit_files={info['unit_files']}"
            f" integration_files={info['integration_files']}"
            f" unit_runnable={info['unit_runnable']}"
            f" integration_runnable={info['integration_runnable']}"
            f" total_runnable={info['total_runnable']}"
            f" gov001_excluded={info['gov001_excluded']}"
            f" capacity_excluded={info['capacity_excluded']}"
        )
        return 0
    if args.cmd == "run-unit":
        if not 0 <= args.shard < UNIT_SHARD_COUNT:
            raise SystemExit(f"Invalid unit shard {args.shard}")
        files = unit_files(root)[args.shard :: UNIT_SHARD_COUNT]
        deselects = [f"--deselect={r}" for r in unit_deselects_for_shard(files)]
        return subprocess.call(
            [sys.executable, "-m", "pytest", *deselects, "-q", "--tb=short", *files],
            cwd=root,
        )
    if args.cmd == "run-integration":
        if not 0 <= args.shard < INTEGRATION_SHARD_COUNT:
            raise SystemExit(f"Invalid integration shard {args.shard}")
        files = integration_files(root)[args.shard :: INTEGRATION_SHARD_COUNT]
        deselects = [f"--deselect={r}" for r in integration_deselects_for_shard(files)]
        return subprocess.call(
            [sys.executable, "-m", "pytest", *deselects, "-q", "--tb=short", *files],
            cwd=root,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
