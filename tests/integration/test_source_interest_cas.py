"""Interest-only commands preserve raw policy and never create processing work."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from conftest import _load_module

from youtube_intel.local_api import ApiError

support = _load_module("test_task021_source_policy_filtering")


def _body(command="interest", expected=None, **changes):
    return {
        "command_id": command,
        "expected_source_policy_revision_id": expected,
        "focus_mode": "OVERRIDE",
        "focus_rules": ["robotics"],
        "ignore_mode": "INHERIT",
        "ignore_rules": [],
        "distillation_style_mode": "INHERIT",
        "distillation_style": None,
        **changes,
    }


def _put(app, source, body, interest=True):
    return app.handle(
        "PUT",
        f"/api/v1/sources/{source}/" + ("interests" if interest else "policy"),
        json.dumps(body).encode(),
    )[1]


def _snapshot(repository):
    with repository._connect() as c:
        return {
            r[0]: [
                tuple(v)
                for v in c.execute('SELECT * FROM "' + r[0] + '" ORDER BY rowid')
            ]
            for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


@pytest.mark.parametrize(
    "counts", [(None, None), (0, 10), (3, 1), (None, 3), (5, None), (1, 5), (10, 3)]
)
def test_interest_preserves_raw_counts_and_only_appends_policy(tmp_path, counts):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    full = _put(
        app,
        sid,
        _body(
            "full", initial_history_count=counts[0], per_run_max_new_videos=counts[1]
        ),
        False,
    )
    before = _snapshot(r)
    result = _put(app, sid, _body(expected=full["policy"]["source_policy_revision_id"]))
    raw = r.get_source_policy_revision(sid)
    assert (raw.initial_history_count, raw.per_run_max_new_videos) == counts
    assert raw.focus_rules == ("robotics",)
    after = _snapshot(r)
    assert {
        k: v
        for k, v in before.items()
        if k not in {"source_policy_current", "source_policy_revisions"}
    } == {
        k: v
        for k, v in after.items()
        if k not in {"source_policy_current", "source_policy_revisions"}
    }
    assert (
        len(after["source_policy_revisions"])
        == len(before["source_policy_revisions"]) + 1
    )
    assert result["applied_source_policy_revision_id"] == raw.revision_id
    assert result["historical_replay"] is False


@pytest.mark.parametrize("seeded", [False, True])
@pytest.mark.parametrize("interest_first", [True, False])
def test_both_full_put_interest_commit_orders_conflict_instead_of_losing_updates(
    tmp_path, interest_first, seeded
):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    expected = (
        _put(
            app,
            sid,
            _body("seed", initial_history_count=0, per_run_max_new_videos=5),
            False,
        )["applied_source_policy_revision_id"]
        if seeded
        else None
    )
    first = (
        _body(
            "interest" if interest_first else "full",
            initial_history_count=3,
            per_run_max_new_videos=10,
        )
        if not interest_first
        else _body()
    )
    first["expected_source_policy_revision_id"] = expected
    _put(app, sid, first, interest_first)
    stale = (
        _body(
            "full" if interest_first else "interest",
            initial_history_count=0,
            per_run_max_new_videos=1,
        )
        if interest_first
        else _body()
    )
    stale["expected_source_policy_revision_id"] = expected
    before = _snapshot(r)
    with pytest.raises(ApiError) as error:
        _put(app, sid, stale, not interest_first)
    assert error.value.status == 409
    assert _snapshot(r) == before


def test_complete_command_replay_survives_restart_and_never_moves_head(tmp_path):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    original = _body()
    applied = _put(app, sid, original)["applied_source_policy_revision_id"]
    current = _put(app, sid, _body("later", applied, focus_rules=["later"]))[
        "applied_source_policy_revision_id"
    ]
    before = _snapshot(r)
    from youtube_intel.state import SQLiteStateRepository

    restarted = SQLiteStateRepository(r._database_path)
    replay = _put(support._app(restarted), sid, original)
    assert replay["applied_source_policy_revision_id"] == applied
    assert replay["current_source_policy_revision_id"] == current
    assert replay["historical_replay"] is True
    assert _snapshot(r) == before
    for changed in (
        _body(expected=applied),
        _body(focus_rules=["different"]),
        _body(distillation_style_mode="OVERRIDE", distillation_style="BALANCED"),
    ):
        with pytest.raises(ApiError) as error:
            _put(app, sid, changed)
        assert error.value.status == 409
    assert _snapshot(r) == before


@pytest.mark.parametrize(
    "change",
    [
        {"initial_history_count": 3},
        {"enabled": False},
        {"schedule": {}},
        {"focus_mode": "BAD"},
        {"focus_mode": "INHERIT"},
        {"expected_source_policy_revision_id": 2},
    ],
)
def test_interest_rejects_non_interest_unknown_or_invalid_values(tmp_path, change):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    before = _snapshot(r)
    with pytest.raises(ApiError) as error:
        _put(app, sid, _body(**change))
    assert error.value.status == 422
    assert _snapshot(r) == before


def test_missing_expected_is_distinct_from_null_and_legacy_blind_full_put_is_closed(
    tmp_path,
):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    missing = _body()
    del missing["expected_source_policy_revision_id"]
    with pytest.raises(ApiError) as error:
        _put(app, sid, missing)
    assert error.value.status == 422
    full = {**missing, "initial_history_count": None, "per_run_max_new_videos": None}
    result = _put(app, sid, full, False)
    assert (
        _put(app, sid, full, False)["applied_source_policy_revision_id"]
        == result["applied_source_policy_revision_id"]
    )
    full["command_id"] = "blind"
    with pytest.raises(ApiError) as error:
        _put(app, sid, full, False)
    assert error.value.status == 409


def test_real_concurrent_commands_have_one_winner(tmp_path):
    r = support._repository(tmp_path)
    sid = support._source(r)
    barrier = Barrier(2)

    def write(interest):
        app = support._app(r)
        barrier.wait()
        try:
            _put(
                app,
                sid,
                _body(
                    "interest" if interest else "full",
                    **(
                        {}
                        if interest
                        else {"initial_history_count": 3, "per_run_max_new_videos": 10}
                    ),
                ),
                interest,
            )
            return 200
        except ApiError as error:
            return error.status

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(write, [True, False])) == [200, 409]


def test_get_policy_and_modes_use_one_read_snapshot(tmp_path, monkeypatch):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)

    # The old GET calls these separately, permitting a write between versions.
    def forbidden(*_args):
        raise AssertionError("mixed snapshot getter")

    monkeypatch.setattr(r, "get_source_policy_revision", forbidden)
    monkeypatch.setattr(r, "get_global_source_policy_revision", forbidden)
    detail = app.handle("GET", f"/api/v1/sources/{sid}")[1]
    assert detail["policy"]["source_policy_revision_id"] is None
    assert detail["policy_modes"] == {
        "focus": "INHERIT",
        "ignore": "INHERIT",
        "style": "INHERIT",
    }


def test_full_command_binds_expected_and_all_fields_and_never_rolls_head_back(tmp_path):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    body = _body("full", initial_history_count=None, per_run_max_new_videos=10)
    applied = _put(app, sid, body, False)["applied_source_policy_revision_id"]
    current = _put(app, sid, _body("later", applied))[
        "applied_source_policy_revision_id"
    ]
    before = _snapshot(r)
    replay = _put(support._app(r), sid, body, False)
    assert replay["historical_replay"] is True
    assert replay["current_source_policy_revision_id"] == current
    for change in (
        {"expected_source_policy_revision_id": applied},
        {"initial_history_count": 3},
        {"per_run_max_new_videos": 1},
        {"focus_rules": ["changed"]},
    ):
        with pytest.raises(ApiError) as error:
            _put(app, sid, {**body, **change}, False)
        assert error.value.status == 409
    assert _snapshot(r) == before


def test_legacy_command_replay_remains_readable_but_cannot_repurpose_identity(tmp_path):
    from dataclasses import replace

    from youtube_intel.state import PolicyOverrideMode, SourcePolicyRevisionWrite

    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    old = SourcePolicyRevisionWrite(
        revision_id="source-policy:source:"
        + support.SourcePolicyApplicationService._identity_digest(sid, "old-command"),
        policy_scope="SOURCE",
        source_id=sid,
        initial_history_count=None,
        per_run_max_new_videos=None,
        focus_mode=PolicyOverrideMode.OVERRIDE,
        focus_rules=("robotics",),
        ignore_mode=PolicyOverrideMode.INHERIT,
        ignore_rules=(),
        distillation_style_mode=PolicyOverrideMode.INHERIT,
        distillation_style=None,
        created_at=support.NOW,
    )
    r.create_source_policy_revision(old)
    r.create_source_policy_revision(replace(old, revision_id="later-fixture"))
    before = _snapshot(r)
    body = _body("old-command", initial_history_count=None, per_run_max_new_videos=None)
    del body["expected_source_policy_revision_id"]
    assert _put(app, sid, body, False)["historical_replay"] is True
    for change in (
        {"expected_source_policy_revision_id": "later-fixture"},
        {"focus_rules": ["different"]},
    ):
        with pytest.raises(ApiError) as error:
            _put(app, sid, {**body, **change}, False)
        assert error.value.status == 409
    assert _snapshot(r) == before


def test_interest_null_counts_continue_inheriting_and_all_rows_survive_backup(tmp_path):
    import hashlib

    from youtube_intel.backup_restore import BackupRestoreService

    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    _put(app, sid, _body())
    support._policy(r).update_global(
        command_id="global-later",
        initial_history_count=3,
        per_run_max_new_videos=1,
        focus_rules=["global-later"],
        ignore_rules=[],
        distillation_style=support.DistillationStyle.BALANCED,
    )
    current = app.handle("GET", f"/api/v1/sources/{sid}")[1]
    assert current["policy"]["initial_history_count"] == 3
    assert current["policy"]["per_run_max_new_videos"] == 1
    assert r.get_source_policy_revision(sid).initial_history_count is None
    data = tmp_path / "DATA"
    data.mkdir()
    from youtube_intel.local_content import LocalContentProvider

    imported = LocalContentProvider(r, data, now=lambda: support.NOW).import_bytes(
        "restore-notes.txt",
        "隔离恢复材料🙂\nOriginal text retains qualifications.".encode(),
    )
    assert imported.status == "READY"
    before = _snapshot(r)

    def files():
        return {
            p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in data.rglob("*")
            if p.is_file()
        }

    before_files = files()
    assert before_files
    backup = BackupRestoreService(database=r._database_path, data_root=data)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    preview = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert _snapshot(r) == before
    assert files() == before_files
    assert _put(support._app(r), sid, _body())["historical_replay"] is False
    assert _snapshot(r) == before


def test_pointer_failure_rolls_back_new_revision(tmp_path):
    import sqlite3

    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    with r._connect() as c:
        c.execute(
            "CREATE TRIGGER fixture_reject_pointer BEFORE INSERT ON source_policy_current BEGIN SELECT RAISE(ABORT,'injected pointer failure'); END"
        )
    before = _snapshot(r)
    with pytest.raises(ApiError) as error:
        _put(app, sid, _body())
    assert error.value.status == 409
    assert isinstance(error.value.__cause__.__cause__, sqlite3.IntegrityError)
    assert _snapshot(r) == before


@pytest.mark.parametrize(
    "style",
    [
        None,
        "BALANCED",
        "TECHNICAL_DETAIL_FIRST",
        "PRODUCT_CASE_FIRST",
        "TREND_OPINION_FIRST",
    ],
)
@pytest.mark.parametrize("mode", ["INHERIT", "OVERRIDE"])
def test_interest_legal_inherit_and_explicit_empty_overrides(tmp_path, style, mode):
    r = support._repository(tmp_path)
    sid = support._source(r)
    app = support._app(r)
    _put(
        app,
        sid,
        _body(
            focus_mode=mode,
            focus_rules=[],
            ignore_mode=mode,
            ignore_rules=[],
            distillation_style_mode="INHERIT" if style is None else "OVERRIDE",
            distillation_style=style,
        ),
    )
    raw = r.get_source_policy_revision(sid)
    assert raw.focus_mode.value == raw.ignore_mode.value == mode
    assert raw.focus_rules == raw.ignore_rules == ()
    assert raw.distillation_style == style
    assert raw.initial_history_count is None and raw.per_run_max_new_videos is None


def test_unknown_source_is_rejected_without_mutation(tmp_path):
    r = support._repository(tmp_path)
    before = _snapshot(r)
    with pytest.raises(ApiError) as error:
        _put(support._app(r), "missing-source", _body())
    assert error.value.status == 422
    assert _snapshot(r) == before
