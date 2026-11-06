"""Portable owned continuation fixtures; no real fee grant or external IO."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest


def controller() -> Any:
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/validation/bounded_synthesis_trial.py"
    )
    spec = importlib.util.spec_from_file_location("owned_bounded_v2_controller", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finite_v2_is_not_consent_or_a_v1_default_change() -> None:
    m = controller()
    one, two = m.trial_spec(), m.trial_spec("v2-r1")
    assert one["variant"] == "v1-r4" and one["limits"] == m.LIMITS
    assert one["profile_id"] == m.profile.PROFILE_ID
    assert two["profile_id"] == m.profile.ATTRIBUTION_PROFILE_ID
    assert (
        two["limits"]["historical_calls"] == 3
        and two["limits"]["historical_held_microcny"] == 2913136
    )
    assert (
        two["limits"]["max_total_calls"] == 12
        and two["limits"]["total_microcny"] == 10000000
    )
    with pytest.raises(ValueError, match="VARIANT"):
        m.trial_spec("unknown")


def approve(m: Any, trial: Any) -> Any:
    from datetime import UTC, datetime, timedelta

    proposal = trial.prepare()
    m.once(
        trial.control / "grant.json",
        {
            **proposal["approval"],
            "approved": True,
            "decision_id": "SYNTHETIC_TEST_ONLY_NOT_REAL_FEE_PERMISSION",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
    )
    return proposal


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> Any:
    import copy

    from conftest import _load_module

    old = _load_module("test_bounded_synthesis_trial")
    old.owned_synthetic_package.__wrapped__(tmp_path_factory)
    bundle = old._bundle
    assert bundle is not None
    m = controller()
    root = tmp_path_factory.mktemp("owned-continuation-template")
    one = m.trial_spec()
    one.update(
        package=bundle["package"],
        manifest_sha256=bundle["manifest_sha256"],
        order=bundle["order"],
        seed=bundle["seed"],
        control=root / "old-control",
        runs=root / "old-runs",
    )
    one["limits"].update(bundle["reserve_totals"])
    old_trial = m.Trial(_spec=one)
    original_proposal = approve(m, old_trial)
    result = old_trial.execute(
        credential=lambda: "synthetic-external-key", wire=old.fake_wire(m, [])
    )
    assert result["status"] == "TECHNICAL_PASS_AWAITING_ROOT", result
    m.once(
        old_trial.control / (result["case"] + ".semantic.json"),
        {
            "case": result["case"],
            "decision": "REJECT",
            "reviewer": "ROOT",
            "decision_id": "SYNTHETIC_PARENT_REJECT_NOT_REAL_QUALITY",
            "result_sha256": m.sha(m.encoded(result)),
            "receipt_sha256": result["receipt_sha256"],
            "oracle_sha256": original_proposal["binding"]["oracle_sha256"],
        },
    )
    case = one["order"][0]
    names = (
        "anchor.json",
        "ledger.json",
        "grant.json",
        "attempt-1.json",
        case + ".result.json",
        case + ".final.json",
        case + ".semantic.json",
    )
    held = one["limits"]["historical_held_microcny"] + result["reserve_microcny"]
    summary = {
        "status": "HISTORICAL_PARENT_ONLY_NOT_NEW_FEE_AUTHORIZATION",
        "parent_control": str(old_trial.control),
        "parent_hashes": {
            name: m.sha(m.read(old_trial.control / name, private=True))
            for name in names
        },
        "historical_calls": 3,
        "historical_held_microcny": held,
        "actual_bill": "UNKNOWN",
        "parent_semantic": "REJECT",
        "further_calls_authorized": False,
    }
    summary_path = root / "parent-summary.json"
    m.once(summary_path, summary)
    two = m.trial_spec("v2-r1")
    two.update(
        package=root / "v2-package",
        original=one,
        order=one["order"],
        seed=one["seed"],
        parent_summary=summary_path,
        parent_summary_sha256=m.sha(m.encoded(summary)),
        bundle_parent_summary_sha256=m.sha(m.encoded(summary)),
        parent_location_proof=root / "template-location-only.json",
    )
    manifest = m.parsed(one["package"] / "manifest.json")
    estimates = [
        m.p.loads(
            m.p._assemble(
                m.parsed(Path(row["artifacts"]) / "prepared-proof.json")["command"],
                m.parsed(Path(row["artifacts"]) / "prepared-proof.json")["capture"],
                profile_id=m.profile.ATTRIBUTION_PROFILE_ID,
            ).proof_json
        )["reserve_microunits"]
        for row in manifest["cases"]
    ]
    two["limits"].update(
        historical_held_microcny=held,
        runner_held_microcny=sum(estimates),
        gui_held_microcny=estimates[1],
        prospective_total_microcny=held + sum(estimates) + estimates[1],
    )
    path = Path(m.__file__).with_name("materialize_synthesis_v2_inputs.py")
    spec = importlib.util.spec_from_file_location("owned_v2_package_builder", path)
    assert spec and spec.loader
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    proposal = helper.materialize(two)
    assert proposal["approval"]["approved"] is False
    assert m.parent_binding(two)["historical_calls"] == 3
    return m, old, copy.deepcopy(two), root


@pytest.fixture
def owned(tmp_path: Path, template: Any) -> Any:
    import copy

    m, old, original, _ = template
    spec = copy.deepcopy(original)
    parent = tmp_path / "parent"
    m.directory(parent, create=True)
    for path in original["original"]["control"].iterdir():
        if path.is_file():
            m.once(parent / path.name, m.parsed(path, private=True))
    anchor = m.parsed(parent / "anchor.json", private=True)
    anchor.update(
        control_inode=parent.stat().st_ino, control_device=parent.stat().st_dev
    )
    (parent / "anchor.json").write_bytes(m.encoded(anchor))
    summary = m.parsed(original["parent_summary"], private=True)
    summary["parent_control"] = str(parent)
    summary["parent_hashes"] = {
        name: m.sha(m.read(parent / name, private=True))
        for name in summary["parent_hashes"]
    }
    summary_path = tmp_path / "parent-summary.json"
    m.once(summary_path, summary)
    spec.update(
        parent_summary=summary_path,
        parent_summary_sha256=m.sha(m.encoded(summary)),
        parent_location_proof=tmp_path / "location-only.json",
    )
    spec["original"]["control"] = parent
    trial = m.Trial(
        variant="v2-r1", control=tmp_path / "child", runs=tmp_path / "runs", _spec=spec
    )
    return m, old, trial, parent


def test_parent_rejection_is_counted_and_never_becomes_child_fee_permission(
    owned: Any,
) -> None:
    m, _, trial, parent = owned
    report = trial.prepare()
    assert report["approval"]["approved"] is False
    assert report["binding"]["parent"]["historical_calls"] == 3
    old_attempt = m.parsed(parent / "attempt-1.json", private=True)
    assert (
        report["binding"]["parent"]["historical_held_microcny"]
        == 1943326 + old_attempt["reserve_microcny"]
    )
    assert (
        m.parsed(parent / (old_attempt["case"] + ".semantic.json"), private=True)[
            "decision"
        ]
        == "REJECT"
    )
    with pytest.raises(ValueError, match="GRANT"):
        trial.execute(credential=lambda: pytest.fail("new fee decision required"))
    assert trial.ledger(report["binding"])["attempts"] == []


def test_exact_child_fake_wire_keeps_parent_bytes_and_counts_hold_before_key(
    owned: Any,
) -> None:
    m, old, trial, parent = owned
    report = approve(m, trial)
    parent_before = {
        p.name: m.sha(m.read(p, private=True)) for p in parent.iterdir() if p.is_file()
    }
    calls = []

    def key() -> str:
        assert len(trial.ledger(report["binding"])["attempts"]) == 1
        assert m.parent_binding(trial.spec) == report["binding"]["parent"]
        return "synthetic-external-key"

    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result["status"] == "TECHNICAL_PASS_AWAITING_ROOT" and len(calls) == 1
    assert result["actual_bill"] == "UNKNOWN" and result["qualification"] == "CLOSED"
    assert {
        p.name: m.sha(m.read(p, private=True)) for p in parent.iterdir() if p.is_file()
    } == parent_before
    assert (
        trial.spec["limits"]["historical_held_microcny"] + result["reserve_microcny"]
        > report["binding"]["parent"]["historical_held_microcny"]
    )


@pytest.mark.parametrize(
    "kind", ["absent", "expired", "old-purpose", "wrong-binding", "budget", "profile"]
)
def test_no_new_authority_precedes_key_or_claim(owned: Any, kind: str) -> None:
    m, _, trial, _ = owned
    report = trial.prepare()
    if kind != "absent":
        grant = {
            **report["approval"],
            "approved": True,
            "decision_id": "SYNTHETIC_ONLY",
            "expires_at": "2099-01-01T00:00:00+00:00",
        }
        if kind == "expired":
            grant["expires_at"] = "2020-01-01T00:00:00+00:00"
        if kind == "old-purpose":
            grant["purpose"] = "ROOT_RECORDED_PAID_QUALIFICATION"
        if kind in {"wrong-binding", "profile"}:
            grant["binding_sha256"] = "a" * 64
        if kind == "budget":
            grant["limits"] = {**grant["limits"], "total_microcny": 11000000}
        m.once(trial.control / "grant.json", grant)
    with pytest.raises(ValueError, match="GRANT"):
        trial.execute(credential=lambda: pytest.fail("no key before new exact consent"))
    assert not trial.runs.exists()


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "changed",
        "extra-attempt",
        "orphan",
        "relabeled-pass",
        "unknown-status",
        "counter",
    ],
)
def test_parent_history_tampering_stops_even_when_resigned_fixture_summary(
    owned: Any, kind: str
) -> None:
    m, _, trial, parent = owned
    case = trial.spec["order"][0]
    if kind == "missing":
        (parent / "attempt-1.json").rename(parent / "preserved-attempt.json")
    elif kind in {"extra-attempt", "orphan"}:
        m.once(parent / "attempt-2.json", {"unknown": True})
    else:
        name = (
            case + ".semantic.json"
            if kind == "relabeled-pass"
            else case + ".result.json"
            if kind == "unknown-status"
            else "ledger.json"
            if kind == "counter"
            else "attempt-1.json"
        )
        value = m.parsed(parent / name, private=True)
        if kind == "relabeled-pass":
            value["decision"] = "PASS"
        elif kind == "unknown-status":
            value["execution_status"] = "AMBIGUOUS"
        elif kind == "counter":
            value["attempts"] = []
        else:
            value["reserve_microcny"] += 1
        (parent / name).write_bytes(m.encoded(value))
        summary = m.parsed(trial.spec["parent_summary"], private=True)
        summary["parent_hashes"][name] = m.sha(m.read(parent / name, private=True))
        trial.spec["parent_summary"].write_bytes(m.encoded(summary))
        trial.spec["parent_summary_sha256"] = m.sha(m.encoded(summary))
    with pytest.raises(ValueError, match="PARENT"):
        trial.prepare()
    assert not trial.control.exists()


@pytest.mark.parametrize("branch", ["timeout", "429", "truncated"])
def test_child_unknown_or_failure_stops_without_releasing_hold(
    owned: Any, branch: str
) -> None:
    m, old, trial, _ = owned
    report = approve(m, trial)
    calls = []
    result = trial.execute(
        credential=lambda: "synthetic-external-key",
        wire=old.fake_wire(m, calls, branch),
    )
    assert (
        result["status"] in {"TECHNICAL_FAILURE_STOP", "UNKNOWN_STOP"}
        and len(calls) == 1
    )
    assert len(trial.ledger(report["binding"])["attempts"]) == 1
    with pytest.raises(ValueError, match="PREVIOUS"):
        trial.execute(
            credential=lambda: pytest.fail("failed or unknown is not free/retryable")
        )


def semantic(m: Any, trial: Any, result: Any, decision: str = "PASS") -> None:
    m.once(
        trial.control / (result["case"] + ".semantic.json"),
        {
            "case": result["case"],
            "decision": decision,
            "reviewer": "ROOT",
            "decision_id": "SYNTHETIC_ONLY_NOT_REAL_SEMANTIC_QUALIFICATION",
            "result_sha256": m.sha(m.encoded(result)),
            "receipt_sha256": result["receipt_sha256"],
            "oracle_sha256": trial.proposal()["binding"]["oracle_sha256"],
        },
    )


def test_eight_v2_cases_require_exact_semantics_and_refuse_ninth(owned: Any) -> None:
    m, old, trial, _ = owned
    report = approve(m, trial)
    calls = []
    for case in trial.spec["order"]:
        result = trial.execute(
            credential=lambda: "synthetic-external-key", wire=old.fake_wire(m, calls)
        )
        assert result["case"] == case
        assert result["status"] == "TECHNICAL_PASS_AWAITING_ROOT", result
        assert result["qualification"] == "CLOSED"
        with pytest.raises(ValueError, match="PREVIOUS"):
            trial.execute(credential=lambda: pytest.fail("semantic decision required"))
        semantic(m, trial, result)
    with pytest.raises(ValueError, match="GUI_SLOT_NOT_EXECUTABLE"):
        trial.execute(credential=lambda: pytest.fail("no automatic GUI spend"))
    ledger = trial.ledger(report["binding"])
    assert len(calls) == len(ledger["attempts"]) == 8
    assert (
        sum(a["reserve_microcny"] for a in ledger["attempts"])
        == trial.spec["limits"]["runner_held_microcny"]
    )


def test_v2_child_rejection_stops_next_case(owned: Any) -> None:
    m, old, trial, _ = owned
    approve(m, trial)
    result = trial.execute(
        credential=lambda: "synthetic-external-key", wire=old.fake_wire(m, [])
    )
    semantic(m, trial, result, "REJECT")
    with pytest.raises(ValueError, match="PREVIOUS"):
        trial.execute(credential=lambda: pytest.fail("rejected case cannot continue"))


def test_v2_concurrent_execute_has_one_immutable_hold(owned: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    m, old, trial, _ = owned
    report = approve(m, trial)
    calls = []

    def invoke() -> Any:
        try:
            return trial.execute(
                credential=lambda: "synthetic-external-key",
                wire=old.fake_wire(m, calls),
            )
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert (
        sum(
            isinstance(r, dict) and r["status"] == "TECHNICAL_PASS_AWAITING_ROOT"
            for r in results
        )
        == 1
    )
    assert any(isinstance(r, str) and "PREVIOUS" in r for r in results)
    assert len(calls) == len(trial.ledger(report["binding"])["attempts"]) == 1


@pytest.mark.parametrize("phase", ["before-claim", "after-key"])
def test_changed_parent_is_rechecked_at_dispatch_boundaries(
    owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    m, old, trial, parent = owned
    approve(m, trial)
    calls = []
    keys = []

    def mutate() -> None:
        path = parent / "ledger.json"
        path.write_bytes(path.read_bytes() + b" ")

    original_preview = m.PersonalizedDistillationService.preview_cloud_execution

    def preview(service: Any, **kwargs: Any) -> Any:
        result = original_preview(service, **kwargs)
        if phase == "before-claim" and (trial.control / "attempt-1.json").exists():
            mutate()
        return result

    monkeypatch.setattr(
        m.PersonalizedDistillationService, "preview_cloud_execution", preview
    )

    def key() -> str:
        keys.append(True)
        if phase == "after-key":
            mutate()
        return "synthetic-external-key"

    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result["status"] == "UNKNOWN_STOP" and calls == []
    assert len(keys) == (1 if phase == "after-key" else 0)
    assert (
        m.parsed(trial.control / "attempt-1.json", private=True)["reserve_microcny"] > 0
    )


@pytest.mark.parametrize(
    "kind", ["mode", "symlink", "hardlink", "same-bytes-new-inode"]
)
def test_parent_identity_and_private_files_are_bound(owned: Any, kind: str) -> None:
    import os

    m, _, trial, parent = owned
    approve(m, trial)
    path = parent / "ledger.json"
    if kind == "mode":
        path.chmod(0o644)
    else:
        saved = parent.parent / "saved-ledger.json"
        path.rename(saved)
        if kind == "symlink":
            path.symlink_to(saved)
        elif kind == "hardlink":
            os.link(saved, path)
        else:
            m.once(path, m.parsed(saved, private=True))
    with pytest.raises(ValueError, match="PARENT|GRANT"):
        trial.execute(credential=lambda: pytest.fail("parent identity before key"))
    assert not trial.runs.exists()


@pytest.mark.parametrize(
    "kind", ["missing-marker", "lost-control", "orphan-hold", "missing-key"]
)
def test_v2_restart_and_restore_cannot_reset_consumed_authority(
    owned: Any, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    m, _, trial, _ = owned
    report = approve(m, trial)
    if kind == "missing-marker":
        trial.initialization_marker().rename(
            trial.initialization_marker().with_suffix(".preserved")
        )
    elif kind == "lost-control":
        trial.control.rename(trial.control.with_name("preserved-control"))
    elif kind == "orphan-hold":

        def crash(*args: Any) -> None:
            raise RuntimeError("SYNTHETIC_CRASH_AFTER_IMMUTABLE_HOLD")

        monkeypatch.setattr(m, "replace_ledger", crash)
        with pytest.raises(RuntimeError, match="SYNTHETIC_CRASH"):
            trial.execute(credential=lambda: pytest.fail("crash before key"))
        assert m.parsed(trial.control / "ledger.json", private=True)["attempts"] == []
        assert (trial.control / "attempt-1.json").exists()
    else:

        def missing() -> str:
            raise RuntimeError("SYNTHETIC_KEY_UNAVAILABLE")

        result = trial.execute(credential=missing)
        assert result["status"] == "UNKNOWN_STOP" and result["send_attempted"] is False
        assert len(trial.ledger(report["binding"])["attempts"]) == 1
    restarted = m.Trial(
        variant="v2-r1", control=trial.control, runs=trial.runs, _spec=trial.spec
    )
    with pytest.raises(ValueError, match="LEDGER|INITIALIZATION|PREVIOUS"):
        if kind == "lost-control":
            restarted.prepare()
        else:
            restarted.execute(credential=lambda: pytest.fail("no reset or replay"))


def test_v2_concurrent_prepare_cannot_replace_initialization(owned: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    m, _, trial, _ = owned

    def prepare() -> Any:
        try:
            return trial.prepare()
        except (ValueError, OSError) as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: prepare(), range(2)))
    assert any(isinstance(r, dict) for r in results)
    report = trial.proposal()
    assert trial.ledger(report["binding"])["attempts"] == []
    assert m.parsed(trial.initialization_marker(), private=True) == m.parsed(
        trial.control / "anchor.json", private=True
    )


def rewrite_parent_grant(m: Any, trial: Any, parent: Path, expiry: str) -> None:
    """Resign an owned synthetic chain only, never the pinned actual parent."""
    case = trial.spec["order"][0]
    grant = m.parsed(parent / "grant.json", private=True)
    grant["expires_at"] = expiry
    (parent / "grant.json").write_bytes(m.encoded(grant))
    attempt = m.parsed(parent / "attempt-1.json", private=True)
    attempt["grant_sha256"] = m.sha(m.encoded(grant))
    (parent / "attempt-1.json").write_bytes(m.encoded(attempt))
    ledger = m.parsed(parent / "ledger.json", private=True)
    ledger["attempts"] = [attempt]
    (parent / "ledger.json").write_bytes(m.encoded(ledger))
    result = m.parsed(parent / (case + ".result.json"), private=True)
    result["grant_sha256"] = attempt["grant_sha256"]
    (parent / (case + ".result.json")).write_bytes(m.encoded(result))
    decision = m.parsed(parent / (case + ".semantic.json"), private=True)
    decision["result_sha256"] = m.sha(m.encoded(result))
    (parent / (case + ".semantic.json")).write_bytes(m.encoded(decision))
    summary = m.parsed(trial.spec["parent_summary"], private=True)
    summary["parent_hashes"] = {
        name: m.sha(m.read(parent / name, private=True))
        for name in summary["parent_hashes"]
    }
    trial.spec["parent_summary"].write_bytes(m.encoded(summary))
    trial.spec["parent_summary_sha256"] = m.sha(m.encoded(summary))


@pytest.mark.parametrize("invoked_in_time", [True, False])
def test_expired_parent_retains_only_historically_authorized_hold(
    owned: Any, invoked_in_time: bool
) -> None:
    from datetime import datetime, timedelta

    m, _, trial, parent = owned
    case = trial.spec["order"][0]
    result = m.parsed(parent / (case + ".result.json"), private=True)
    authorized_at = datetime.fromisoformat(
        result["state_trace"]["system_synthesis_cloud_authorizations"][0][
            "authorized_at"
        ]
    )
    expiry = authorized_at + timedelta(microseconds=1 if invoked_in_time else -1)
    rewrite_parent_grant(m, trial, parent, expiry.isoformat())
    if not invoked_in_time:
        with pytest.raises(ValueError, match="PARENT"):
            trial.prepare()
        return
    proposal = trial.prepare()
    assert proposal["binding"]["parent"]["historical_calls"] == 3
    assert proposal["binding"]["parent"]["parent_semantic"] == "REJECT"
    m.once(
        trial.control / "grant.json",
        {
            **proposal["approval"],
            "approved": True,
            "decision_id": "SYNTHETIC_EXPIRED_CHILD_ONLY",
            "expires_at": expiry.isoformat(),
        },
    )
    with pytest.raises(ValueError, match="GRANT"):
        trial.execute(
            credential=lambda: pytest.fail("parent expiry grants no new call")
        )
    assert trial.ledger(proposal["binding"])["attempts"] == []


@pytest.mark.parametrize("kind", ["untracked-result", "unknown-file", "bare-pending"])
def test_parent_extra_or_nonterminal_history_is_rejected(owned: Any, kind: str) -> None:
    m, _, trial, parent = owned
    if kind != "bare-pending":
        name = (
            "another-case.result.json" if kind == "untracked-result" else "unknown.json"
        )
        m.once(parent / name, {"unknown": True})
    else:
        case = trial.spec["order"][0]
        name = case + ".result.json"
        value = m.parsed(parent / name, private=True)
        value["execution_status"] = "PENDING"
        (parent / name).write_bytes(m.encoded(value))
        summary = m.parsed(trial.spec["parent_summary"], private=True)
        summary["parent_hashes"][name] = m.sha(m.encoded(value))
        trial.spec["parent_summary"].write_bytes(m.encoded(summary))
        trial.spec["parent_summary_sha256"] = m.sha(m.encoded(summary))
    with pytest.raises(ValueError, match="PARENT"):
        trial.prepare()


def test_v2_changed_source_binding_requires_new_grant(
    owned: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, _, trial, _ = owned
    approve(m, trial)
    current = m.code_hashes()
    monkeypatch.setattr(
        m, "code_hashes", lambda: {**current, "changed-source.py": "f" * 64}
    )
    with pytest.raises(ValueError, match="GRANT"):
        trial.execute(credential=lambda: pytest.fail("source grant cannot carry over"))
    assert not trial.runs.exists()


@pytest.fixture
def relocated(owned: Any) -> Any:
    m, old, trial, parent = owned
    trial.spec.update(
        parent_location_proof=parent.parent / "location-only.json",
        parent_location_transition={
            "old_device": parent.stat().st_dev + 1,
            "current_device": parent.stat().st_dev,
            "inode": parent.stat().st_ino,
        },
        parent_terminal=trial.spec["original"]["runs"] / trial.spec["order"][0],
    )
    anchor = m.parsed(parent / "anchor.json", private=True)
    anchor["control_device"] = trial.spec["parent_location_transition"]["old_device"]
    (parent / "anchor.json").write_bytes(m.encoded(anchor))
    summary = m.parsed(trial.spec["parent_summary"], private=True)
    summary["parent_hashes"]["anchor.json"] = m.sha(m.encoded(anchor))
    trial.spec["parent_summary"].write_bytes(m.encoded(summary))
    trial.spec["parent_summary_sha256"] = m.sha(m.encoded(summary))
    return m, old, trial, parent


def location_only(m: Any, trial: Any) -> Any:
    proposal = m.parent_location_proposal(trial.spec)
    assert (
        proposal["approved"] is False and proposal["purpose"] == "PARENT_LOCATION_ONLY"
    )
    value = {
        **proposal,
        "approved": True,
        "decision_id": "SYNTHETIC_LOCATION_ONLY_NOT_FEE_CONSENT",
    }
    m.once(trial.spec["parent_location_proof"], value)
    return value


def test_location_only_proof_preserves_original_history_and_requires_child_fee_grant(
    relocated: Any,
) -> None:
    m, old, trial, parent = relocated
    before = {p.name: m.sha(m.read(p, private=True)) for p in parent.iterdir()}
    with pytest.raises(ValueError, match="PARENT"):
        trial.prepare()
    location_only(m, trial)
    report = trial.prepare()
    assert report["binding"]["parent"]["location_recovery"]["sha256"] == m.sha(
        m.read(trial.spec["parent_location_proof"], private=True)
    )
    assert report["binding"]["parent"]["historical_calls"] == 3
    with pytest.raises(ValueError, match="GRANT"):
        trial.execute(
            credential=lambda: pytest.fail("location proof is not a fee grant")
        )
    approve(m, trial)
    result = trial.execute(
        credential=lambda: "synthetic-external-key", wire=old.fake_wire(m, [])
    )
    assert result["status"] == "TECHNICAL_PASS_AWAITING_ROOT", result
    assert {p.name: m.sha(m.read(p, private=True)) for p in parent.iterdir()} == before


@pytest.mark.parametrize(
    "kind",
    [
        "unapproved",
        "wrong-purpose",
        "wrong-path",
        "wrong-inode",
        "wrong-device",
        "wrong-sha",
        "wrong-owner",
        "mode",
        "replaced",
        "wrong-terminal",
        "numeric-approved",
        "numeric-device",
    ],
)
def test_location_only_proof_is_exact_and_bound(relocated: Any, kind: str) -> None:
    m, _, trial, _ = relocated
    value = location_only(m, trial)
    proof = trial.spec["parent_location_proof"]
    if kind == "replaced":
        approve(m, trial)
        saved = proof.with_suffix(".preserved")
        proof.rename(saved)
        m.once(proof, value)
    elif kind == "wrong-terminal":
        trial.spec["parent_terminal"] = (
            trial.spec["original"]["package"]
            / "cases"
            / trial.spec["order"][0]
            / "project"
        )
    elif kind == "mode":
        proof.chmod(0o644)
    else:
        if kind == "numeric-approved":
            value["approved"] = 1
        elif kind == "numeric-device":
            value["binding"]["current_identity"]["device"] = float(
                value["binding"]["current_identity"]["device"]
            )
        elif kind == "unapproved":
            value["approved"] = False
        elif kind == "wrong-purpose":
            value["purpose"] = "ROOT_RECORDED_ATTRIBUTION_V2_CONTINUATION"
        elif kind == "wrong-path":
            value["binding"]["parent_control"] += "-another"
        elif kind == "wrong-inode":
            value["binding"]["current_identity"]["inode"] += 1
        elif kind == "wrong-device":
            value["binding"]["current_identity"]["device"] += 1
        elif kind == "wrong-owner":
            value["binding"]["current_identity"]["owner_uid"] += 1
        else:
            value["binding"]["parent_hashes"]["anchor.json"] = "f" * 64
        proof.write_bytes(m.encoded(value))
    with pytest.raises(ValueError, match="PARENT|GRANT|PRIVATE"):
        trial.execute(credential=lambda: pytest.fail("bad location proof before key"))
    assert not trial.runs.exists()


def test_location_proof_cannot_accept_another_device_transition(relocated: Any) -> None:
    m, _, trial, _ = relocated
    location_only(m, trial)
    trial.spec["parent_location_transition"]["current_device"] += 2
    with pytest.raises(ValueError, match="PARENT"):
        trial.prepare()
