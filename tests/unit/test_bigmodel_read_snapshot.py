"""Real WAL interleavings through accepted storage APIs; no model or wire."""

import sqlite3

import pytest
from test_backup_restore import (
    NOW,
    _add_source,
    _corrupt_zhipu_scalar_preserving_schema,
    _waiting_model,
    _workspace,
)
from test_bigmodel_claims import _request_fields

from youtube_intel.state import (
    DistillationExecutionWrite,
    SQLiteStateRepository,
    StateStoreError,
)


def _reserve(repository, execution_id, *, claim=True):
    request = dict(_request_fields(), execution_id=execution_id)
    repository.reserve_distillation_execution(
        DistillationExecutionWrite(**request), now=NOW
    )
    repository.authorize_cloud_execution(
        authorization_id="offline-owner-consent:" + execution_id,
        execution_id=execution_id,
        provider="zhipu_bigmodel",
        model="glm-4.7-flash",
        verified_input_hash="a" * 64,
        consent_kind="OWNER_QUALIFICATION",
        now=NOW,
    )
    if claim:
        assert repository.claim_reserved_distillation_execution(**request, now=NOW)
    return request


def _finish(repository, request):
    return repository.finish_distillation_without_admission(
        execution_id=request["execution_id"],
        status="AMBIGUOUS",
        budget_state="UNKNOWN",
        outcome="TRANSPORT_OUTCOME_UNKNOWN",
        invocation_count=1,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )


def _snapshot(repository, data):
    with repository._connect() as connection:
        rows = tuple(connection.iterdump())
    return rows, {
        str(p.relative_to(data)): p.read_bytes() for p in data.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "method",
    [
        "get_distillation_execution",
        "get_cloud_execution_authorization",
        "get_distillation_resource_usage",
        "verify_cloud_audit_database",
    ],
)
@pytest.mark.parametrize("transition", ["claim", "finish"])
def test_finish_between_checkpoint_and_audit_reads_is_one_valid_moment(
    tmp_path, monkeypatch, method, transition
):
    database, data, _, writer, _ = _workspace(tmp_path)
    _add_source(writer)
    request = _reserve(writer, "snapshot-owner", claim=transition == "finish")
    reader = SQLiteStateRepository(database)
    validate = reader._validate_zhipu_execution
    captured = []

    def interleave(connection, checkpoint):
        if not captured:
            captured.append(
                (
                    checkpoint["status"],
                    checkpoint["invocation_count"],
                    connection.in_transaction,
                )
            )
            if transition == "finish":
                _finish(writer, request)
            else:
                assert writer.claim_reserved_distillation_execution(**request, now=NOW)
        validate(connection, checkpoint)

    monkeypatch.setattr(reader, "_validate_zhipu_execution", interleave)
    before_data = _snapshot(writer, data)[1]
    if method == "verify_cloud_audit_database":
        with reader._connect() as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            reader.verify_cloud_audit_database(connection)
            assert not connection.in_transaction
    elif method == "get_distillation_resource_usage":
        # At the chosen old read moment, no terminal usage exists yet. This
        # ordinary absence is valid; a mismatched/corrupt audit diagnosis is not.
        with pytest.raises(StateStoreError, match="resource usage does not exist"):
            reader.get_distillation_resource_usage(request["execution_id"])
    else:
        result = getattr(reader, method)(request["execution_id"])
        assert result is not None
        if method == "get_distillation_execution":
            assert result.status == "PENDING" and result.invocation_count == (
                1 if transition == "finish" else 0
            )
        else:
            assert result.consent_kind == "OWNER_QUALIFICATION"
    assert captured == [("PENDING", 1 if transition == "finish" else 0, True)]
    if transition == "claim":
        _finish(writer, request)
    fresh = writer.get_distillation_execution(request["execution_id"])
    assert fresh.status == "AMBIGUOUS" and fresh.invocation_count == 1
    assert not writer.claim_reserved_distillation_execution(**request, now=NOW)
    with writer._connect() as connection:
        writer.verify_cloud_audit_database(connection)
    settled = _snapshot(writer, data)
    assert settled[1] == before_data
    assert reader.get_distillation_execution(request["execution_id"]) == fresh
    assert _snapshot(writer, data) == settled


def test_activity_list_does_not_mix_old_usage_with_new_response_union(
    tmp_path, monkeypatch
):
    database, data, _, writer, _ = _workspace(tmp_path)
    _add_source(writer)
    old = _reserve(writer, "old-usage")
    _finish(writer, old)
    old_failure = _reserve(writer, "old-failure")
    writer.finish_distillation_cloud_response_failure(
        execution_id=old_failure["execution_id"],
        budget_state="ADMITTED",
        outcome="CLOUD_HTTP_ERROR",
        http_status_code=401,
        now=NOW,
    )
    pending_usage = _reserve(writer, "future-usage")
    pending_failure = _reserve(writer, "future-failure")
    reader = SQLiteStateRepository(database)
    connect = reader._connect
    events, errors, opened = [], [], []

    def connection_with_interleave():
        connection = connect()
        opened.append(connection)

        def trace(sql):
            if "SELECT execution_id FROM (" in sql and not events:
                events.append(connection.in_transaction)
                try:
                    _finish(writer, pending_usage)
                    writer.finish_distillation_cloud_response_failure(
                        execution_id=pending_failure["execution_id"],
                        budget_state="ADMITTED",
                        outcome="CLOUD_HTTP_ERROR",
                        http_status_code=429,
                        now=NOW,
                    )
                except BaseException as error:
                    errors.append(
                        error
                    )  # SQLite trace callback errors must not be hidden.

        connection.set_trace_callback(trace)
        return connection

    monkeypatch.setattr(reader, "_connect", connection_with_interleave)
    data_before = _snapshot(writer, data)[1]
    result = reader.list_distillation_resource_usage()
    assert errors == [] and events == [True]
    assert len(opened) == 1  # The response union must use the same snapshot too.
    assert {item.execution_id for item in result} == {
        old["execution_id"],
        old_failure["execution_id"],
    }
    fresh = writer.list_distillation_resource_usage()
    assert {item.execution_id for item in fresh} == {
        old["execution_id"],
        old_failure["execution_id"],
        pending_usage["execution_id"],
        pending_failure["execution_id"],
    }
    assert _snapshot(writer, data)[1] == data_before


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("caller_transaction", [False, True])
def test_whole_audit_preserves_transaction_ownership_and_cleanup(
    tmp_path, monkeypatch, fail, caller_transaction
):
    _, data, _, repository, _ = _workspace(tmp_path)
    _add_source(repository)
    _reserve(repository, "ownership")
    before = _snapshot(repository, data)
    if fail:

        def reject(*args):
            raise StateStoreError("controlled audit refusal")

        monkeypatch.setattr(repository, "_validate_zhipu_execution", reject)
    with repository._connect() as connection:
        if caller_transaction:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE videos SET title='uncommitted caller change' WHERE video_id='video-1'"
            )
        if fail:
            with pytest.raises(StateStoreError, match="controlled audit refusal"):
                repository.verify_cloud_audit_database(connection)
        else:
            repository.verify_cloud_audit_database(connection)
        assert connection.in_transaction is caller_transaction
        if caller_transaction:
            assert (
                connection.execute(
                    "SELECT title FROM videos WHERE video_id='video-1'"
                ).fetchone()[0]
                == "uncommitted caller change"
            )
            connection.rollback()
        assert not connection.in_transaction
    assert _snapshot(repository, data) == before


@pytest.mark.parametrize(
    "method",
    [
        "get_distillation_execution",
        "get_cloud_execution_authorization",
        "get_distillation_resource_usage",
        "list_distillation_resource_usage",
        "verify_cloud_audit_database",
    ],
)
def test_real_corrupt_scalar_still_refuses_and_leaves_rows_data_and_connections_closed(
    tmp_path, monkeypatch, method
):
    database, data, _, writer, _ = _workspace(tmp_path)
    _add_source(writer)
    request = _reserve(writer, "corrupt-scalar")
    _finish(writer, request)
    with writer._connect() as connection:
        _corrupt_zhipu_scalar_preserving_schema(
            connection,
            "distillation_zhipu_cloud_authorizations",
            "verified_input_hash",
            b"a" * 64,
        )
    before = _snapshot(writer, data)
    reader = SQLiteStateRepository(database)
    connect = reader._connect
    opened = []

    def tracked_connection():
        connection = connect()
        opened.append(connection)
        return connection

    monkeypatch.setattr(reader, "_connect", tracked_connection)
    with pytest.raises(StateStoreError, match="consent identity"):
        if method == "verify_cloud_audit_database":
            connection = reader._connect()
            try:
                reader.verify_cloud_audit_database(connection)
            finally:
                assert not connection.in_transaction
                connection.close()
        elif method == "list_distillation_resource_usage":
            reader.list_distillation_resource_usage()
        else:
            getattr(reader, method)(request["execution_id"])
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
    assert _snapshot(writer, data) == before


def test_cancelled_local_wait_does_not_change_the_getters_old_snapshot(
    tmp_path, monkeypatch
):
    from youtube_intel import distillation_cancellation

    database, data, _, writer, _ = _workspace(tmp_path)
    _add_source(writer)
    execution_id = _waiting_model(writer)
    reader = SQLiteStateRepository(database)
    read = distillation_cancellation.read_cancellation
    events = []

    def cancel_after_checkpoint(connection, checkpoint, *, repository):
        if repository is reader and not events:
            events.append(connection.in_transaction)
            writer.cancel_waiting_model_execution(
                execution_id, video_id="video-1", now=NOW
            )
        return read(connection, checkpoint, repository=repository)

    monkeypatch.setattr(
        distillation_cancellation, "read_cancellation", cancel_after_checkpoint
    )
    files = _snapshot(writer, data)[1]
    old = reader.get_distillation_execution(execution_id)
    assert old.status == "WAITING_MODEL" and old.invocation_count == 0
    assert events == [True]
    fresh = writer.get_distillation_execution(execution_id)
    assert fresh.status == "CANCELLED" and fresh.invocation_count == 0
    settled = _snapshot(writer, data)
    assert settled[1] == files
    assert reader.get_distillation_execution(execution_id) == fresh
    assert _snapshot(writer, data) == settled
