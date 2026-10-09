"""Native authorization, real APFS independence and bounded fallback regressions."""

import http.client
import json
import stat
import threading
import time
from datetime import UTC, datetime

import pytest

from youtube_intel import native_import, source_authority
from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.local_content import LocalContentProvider, LocalImportError
from youtube_intel.native_import import NativeImportService
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_authority import hash_managed, stage_native
from youtube_intel.state import SQLiteStateRepository

ORIGIN = "http://127.0.0.1:5598"
NOW = datetime(2026, 10, 9, tzinfo=UTC)


def settled(service, key, states=("SELECTED", "COMPLETE", "FAILED", "CANCELLED")):
    end = time.monotonic() + 10
    while time.monotonic() < end:
        result = service.status(key, ORIGIN)
        if result["state"] in states:
            return result
        time.sleep(0.01)
    raise AssertionError("native job did not settle")


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path.resolve()
    repo = SQLiteStateRepository(root / "state.sqlite")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, root / "data")
    source = root / "notes.md"
    source.write_bytes(b"Native isolated authoritative source.\n")
    return root, repo, provider, source


def selected(provider, source, **kwargs):
    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [source], **kwargs)
    key = service.choose(ORIGIN)["job_id"]
    assert settled(service, key)["state"] == "SELECTED"
    return service, key


def test_true_apfs_snapshot_is_independent_of_original_edits_move_and_deletion(workspace):
    root, repo, provider, source = workspace
    original = source.read_bytes()
    before = source.stat()
    service, key = selected(provider, source)
    try:
        assert "path" not in json.dumps(service.status(key, ORIGIN))
        assert service.confirm(key, ORIGIN)["state"] == "IMPORTING"
        result = settled(service, key, ("COMPLETE",))
        item = result["files"][0]
        assert item["snapshot_method"] == "APFS_CLONE"
        content = item["import"]["content_id"]
        saved = root / "data" / f"transcripts/local/{content}/source.md"
        assert saved.stat().st_ino != before.st_ino
        assert stat.S_IMODE(saved.stat().st_mode) == 0o600
        assert source.read_bytes() == original
        assert source.stat().st_mtime_ns == before.st_mtime_ns
        source.write_bytes(b"Changed original after the snapshot committed.\n")
        moved = source.rename(root / "moved.md")
        moved.unlink()  # only this isolated test's original
        assert saved.read_bytes() == original
        assert hash_managed(provider.data_root, str(saved.relative_to(provider.data_root)), maximum=1000)[1] == content[6:]
        assert repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(content)[0])
        assert len(repo.list_videos()) == 1
        assert not list((provider.data_root / ".imports").iterdir())
    finally:
        service.shutdown()


def test_read_only_source_permissions_are_preserved(workspace):
    _, _, provider, source = workspace
    source.chmod(0o400)
    service, key = selected(provider, source)
    try:
        service.confirm(key, ORIGIN)
        result = settled(service, key, ("COMPLETE",))
        assert result["files"][0]["import"]
        assert stat.S_IMODE(source.stat().st_mode) == 0o400
    finally:
        service.shutdown()


def test_unsupported_clone_falls_back_to_actual_bounded_copy_progress(workspace, monkeypatch):
    root, _, _, source = workspace
    source.write_bytes(b"x" * (3 * 1024 * 1024 + 17))
    monkeypatch.setattr(source_authority, "clone_descriptor", lambda *_: False)
    events = []
    with source.open("rb") as input_file:
        with stage_native(root / "stage", input_file, maximum=4 * 1024 * 1024,
                          cancelled=lambda: False, progress=lambda *event: events.append(event)) as staged:
            assert staged.size == source.stat().st_size
            assert staged.publish(root / "saved", "source.bin")
    copied = [event[1] for event in events if event[0] == "COPYING"]
    assert copied == [1024 * 1024, 2 * 1024 * 1024, 3 * 1024 * 1024, 3 * 1024 * 1024 + 17]
    assert all(event[3] == "STREAM_COPY" for event in events if event[0] == "COPYING")
    assert (root / "saved/source.bin").read_bytes() == source.read_bytes()


def test_copy_source_mutation_fails_before_publication(workspace, monkeypatch):
    root, _, _, source = workspace
    monkeypatch.setattr(source_authority, "clone_descriptor", lambda *_: False)
    def mutation(phase, *_):
        if phase == "COPYING":
            source.write_bytes(b"A different same-length source value.\n")
    with source.open("rb") as input_file, pytest.raises(ValueError, match="changed during copying"):
        with stage_native(root / "stage", input_file, maximum=1000, cancelled=lambda: False, progress=mutation):
            pytest.fail("changed source gained authority")
    assert not list((root / "stage").iterdir())


def test_grant_is_one_use_bound_to_origin_and_expires(workspace, monkeypatch):
    _, repo, provider, source = workspace
    service, key = selected(provider, source)
    try:
        with pytest.raises(LocalImportError, match="LOCAL_SELECTION_EXPIRED"):
            service.confirm(key, "http://localhost:5598")
        monkeypatch.setattr(native_import, "GRANT_TTL_SECONDS", -1)
        with pytest.raises(LocalImportError, match="LOCAL_SELECTION_EXPIRED"):
            service.confirm(key, ORIGIN)
        assert not service._jobs[key].grants
        assert len(repo.list_videos()) == 0
    finally:
        service.shutdown()


def test_changed_selection_rejected_then_new_grant_deduplicates(workspace):
    _, repo, provider, source = workspace
    service, key = selected(provider, source)
    source.write_bytes(b"Changed before confirm.\n")
    service.confirm(key, ORIGIN)
    result = settled(service, key, ("COMPLETE",))
    assert result["files"][0]["error_code"] == "LOCAL_SELECTED_FILE_CHANGED"
    assert not repo.list_videos()
    key = service.choose(ORIGIN)["job_id"]
    settled(service, key)
    service.confirm(key, ORIGIN)
    first = settled(service, key, ("COMPLETE",))["files"][0]["import"]
    with pytest.raises(LocalImportError, match="LOCAL_SELECTION_EXPIRED"):
        service.confirm(key, ORIGIN)
    key = service.choose(ORIGIN)["job_id"]
    settled(service, key)
    service.confirm(key, ORIGIN)
    repeated = settled(service, key, ("COMPLETE",))["files"][0]["import"]
    assert repeated["duplicate"]
    assert repeated["content_id"] == first["content_id"]
    assert len(repo.list_videos()) == 1
    service.shutdown()


@pytest.mark.parametrize("kind", ["empty", "over_text", "over_media", "unsupported", "symlink", "ancestor_symlink"])
def test_invalid_native_selections_never_gain_content(workspace, kind):
    root, repo, provider, source = workspace
    if kind in {"empty", "over_text", "over_media"}:
        source = root / ("large.mp4" if kind == "over_media" else "bad.md")
        with source.open("wb") as output:
            output.truncate(0 if kind == "empty" else 2 * 1024 ** (3 if kind == "over_media" else 2) + 1)
    elif kind == "unsupported":
        source = root / "file.exe"
        source.write_bytes(b"unsupported")
    elif kind == "symlink":
        link = root / "alias.md"
        link.symlink_to(source)
        source = link
    else:
        alias = root / "alias"
        alias.symlink_to(root, target_is_directory=True)
        source = alias / "notes.md"
    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [source])
    try:
        key = service.choose(ORIGIN)["job_id"]
        result = settled(service, key)
        assert result["state"] == "FAILED"
        assert result["files"][0]["error_code"]
        assert not repo.list_videos()
        assert not provider.data_root.exists()
    finally:
        service.shutdown()


def test_cancel_copy_removes_only_attempt_and_preserves_existing_evidence(workspace, monkeypatch):
    root, repo, provider, source = workspace
    old = provider.import_bytes("old.md", b"Previously committed source Evidence.\n")
    source.write_bytes(b"s" * (3 * 1024 * 1024))
    event = threading.Event()
    monkeypatch.setattr(source_authority, "clone_descriptor", lambda *_: False)
    with source.open("rb") as input_file, pytest.raises(InterruptedError):
        with stage_native(root / "stage", input_file, maximum=4 * 1024 * 1024,
                          cancelled=event.is_set, progress=lambda phase, *_: event.set() if phase == "COPYING" else None):
            pytest.fail("cancelled source was admitted")
    assert not list((root / "stage").iterdir())
    assert repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(old.content_id)[0])


def test_native_background_window_blocks_backup_and_restore_without_deleting_data(workspace):
    root, _, _, _ = workspace
    backup = BackupRestoreService(database=root / "state.sqlite", data_root=root / "data")
    with backup.background_work(native_import=True) as allowed:
        assert allowed and not backup.readiness()["ready"]
        with pytest.raises(BackupRestoreError, match="local snapshot"):
            backup.stage_restore(b"not parsed")
        with pytest.raises(BackupRestoreError, match="local snapshot"):
            backup.confirm_restore("a" * 32)
    assert backup.background_allowed
    assert not backup.restore_pending


@pytest.fixture
def http_native(workspace):
    _, repo, _, source = workspace
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=source.parent / "data")
    app.enable_native_import((ORIGIN, "http://localhost:5598"), picker_executable=source.parent / "unused-test-selector")
    calls = []
    app._native_import.picker = lambda _: calls.append("picker") or [source]
    server = serve_loopback(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, app, calls
    app.shutdown_native_import()
    server.shutdown()
    server.server_close()
    thread.join()


def request(server, path="/api/v1/local/native/picks", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    connection.request("POST", path, json.dumps(body or {}), headers=headers or {"Origin": ORIGIN, "X-YIA-Request": "local-ui", "Sec-Fetch-Site": "same-origin"})
    response = connection.getresponse()
    result = response.status, json.loads(response.read())
    connection.close()
    return result


@pytest.mark.parametrize("origin", [None, "null", "https://evil.example", "http://127.0.0.1:5488", "http://localhost:1234"])
def test_native_http_exact_origin_denial_never_opens_picker(http_native, origin):
    server, _, calls = http_native
    headers = {"X-YIA-Request": "local-ui"}
    if origin is not None:
        headers["Origin"] = origin
    assert request(server, headers=headers)[0] == 403
    assert calls == []


@pytest.mark.parametrize("field", ["path", "filename", "script", "source_url", "grant"])
def test_client_cannot_authorize_paths_or_scripts(http_native, field):
    server, _, calls = http_native
    status, _ = request(server, body={field: "/etc/passwd"})
    assert status == 422
    assert calls == []


@pytest.mark.parametrize("override", [{"Host": "evil.example"}, {"Sec-Fetch-Site": "cross-site"}, {"X-YIA-Request": "wrong"}])
def test_host_fetch_site_and_header_denials(http_native, override):
    server, _, calls = http_native
    headers = {"Origin": ORIGIN, "X-YIA-Request": "local-ui", "Sec-Fetch-Site": "same-origin", **override}
    assert request(server, headers=headers)[0] == 403
    assert not calls


def test_control_http_is_small_confirm_returns_without_copying_and_replay_rejected(http_native):
    server, app, _ = http_native
    code, result = request(server)
    assert code == 202
    key = result["job"]["job_id"]
    assert settled(app._native_import, key)["state"] == "SELECTED"
    code, result = request(server, f"/api/v1/local/native/picks/{key}/confirm")
    assert code == 202
    assert len(json.dumps(result)) < 4096
    completed = settled(app._native_import, key, ("COMPLETE",))
    assert completed["files"][0]["import"]
    assert request(server, f"/api/v1/local/native/picks/{key}/confirm")[0] == 409
    assert request(server, headers={"Origin": ORIGIN, "X-YIA-Request": "local-ui"}, body={"padding": "x" * 4097})[0] == 413


def test_completed_history_does_not_block_new_authorized_batches(workspace):
    _, _, provider, source = workspace
    service = NativeImportService(provider, origins=(ORIGIN,), picker=lambda _: [source])
    try:
        for _ in range(18):
            key = service.choose(ORIGIN)["job_id"]
            assert settled(service, key)["state"] == "SELECTED"
            service.cancel(key, ORIGIN)
        assert len(service.jobs(ORIGIN)) <= 16
    finally:
        service.shutdown()


def test_picker_cache_refuses_symlinked_ancestor(workspace):
    from youtube_intel.native_picker_build import prepare_native_picker
    root, _, _, _ = workspace
    project = root / "project"
    source = project / "src/youtube_intel/native_picker.m"
    source.parent.mkdir(parents=True)
    source.write_text("// test-owned picker source")
    foreign = root / "foreign"
    foreign.mkdir()
    (project / ".var").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(OSError):
        prepare_native_picker(project)
    assert not list(foreign.iterdir())


def test_attempt_cleanup_preserves_a_foreign_replacement(workspace):
    import io
    root, _, _, _ = workspace
    stage = root / "stage"
    with source_authority.stage_stream(stage, io.BytesIO(b"private attempt"), 15, maximum=16) as pending:
        replacement = pending.path
        replacement.unlink()
        replacement.write_bytes(b"foreign replacement must not be deleted")
    assert replacement.read_bytes() == b"foreign replacement must not be deleted"


def test_native_live_stage_cannot_be_removed_by_startup_cleanup(workspace):
    root, _, _, source = workspace
    with source.open("rb") as input_file:
        with stage_native(root / "stage", input_file, maximum=1000,
                          cancelled=lambda: False, progress=lambda *_: None) as pending:
            source_authority.cleanup_abandoned_imports(root / "stage")
            assert pending.path.exists()
    assert not list((root / "stage").iterdir())
