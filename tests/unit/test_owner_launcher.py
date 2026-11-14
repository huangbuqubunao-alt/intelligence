"""Launcher must bind served bytes to current source, never existence/timestamps."""
import importlib.util
import json
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

_SPEC = importlib.util.spec_from_file_location('owner_launcher', Path(__file__).resolve().parents[2] / 'scripts/owner_launcher.py')
assert _SPEC and _SPEC.loader
launcher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(launcher)


def test_port_probe_allows_closed_server_connections_to_finish() -> None:
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        port = server.getsockname()[1]
        server.listen(1)
        with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
            accepted, _ = server.accept()
            accepted.close()
            assert client.recv(1) == b''
    # The accepted server connection can remain in TIME_WAIT after the listener
    # exits. Both supported application servers allow address reuse on restart.
    launcher.check_port_available(port)


@pytest.mark.parametrize('host', ['127.0.0.1', '0.0.0.0'])
def test_port_probe_still_refuses_an_actual_listener(host: str) -> None:
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, 0))
        server.listen(1)
        with pytest.raises(RuntimeError, match='port .* in use'):
            launcher.check_port_available(server.getsockname()[1])


def test_port_probe_fails_closed_when_listener_detection_times_out() -> None:
    with patch.object(launcher.socket, 'create_connection', side_effect=TimeoutError), patch.object(launcher.socket, 'socket') as probe:
        with pytest.raises(RuntimeError, match='verify local port'):
            launcher.check_port_available(12345)
        probe.assert_not_called()


def workspace(tmp_path: Path) -> Path:
    (tmp_path / 'frontend/dist').mkdir(parents=True)
    (tmp_path / 'frontend/src').mkdir()
    (tmp_path / 'frontend/src/App.tsx').write_text('current interface')
    (tmp_path / 'frontend/dist/index.html').write_text('old interface')
    return tmp_path


def test_old_build_without_provenance_is_stale(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    assert not launcher.current_build(root, {'revision': 'new', 'source_sha256': 'hash'})


def test_revision_source_and_asset_changes_each_invalidate_build(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    identity = {'revision': 'main', 'source_sha256': 'source'}
    manifest = root / 'frontend/dist/build-provenance.json'
    manifest.write_text(json.dumps({'identity': identity, 'assets': launcher.build_assets(root)}))
    assert launcher.current_build(root, identity)
    assert not launcher.current_build(root, dict(identity, revision='next'))
    assert not launcher.current_build(root, dict(identity, source_sha256='changed'))
    (root / 'frontend/dist/index.html').write_text('tampered')
    assert not launcher.current_build(root, identity)


def test_launch_prepares_stale_frontend_and_reuses_current_build(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    tools = root / 'frontend/node_modules/.bin'
    tools.mkdir(parents=True)
    (tools / 'vite').touch()
    identity = {'revision': 'accepted-main', 'source_sha256': 'source'}
    def build(*args: object, **kwargs: object) -> None:
        (root / 'frontend/dist/index.html').write_text('accepted interface')
    with patch.object(launcher, 'build_identity', return_value=identity), patch.object(launcher.subprocess, 'run', side_effect=build) as run:
        assert launcher.prepare_frontend(root) == identity
        assert run.call_args.args[0] == ['npm', 'run', 'build']
        assert launcher.current_build(root, identity)
        launcher.prepare_frontend(root)
        assert run.call_count == 1


def test_missing_tools_fails_actionably_instead_of_serving_old_bytes(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    with patch.object(launcher, 'build_identity', return_value={'revision': 'main', 'source_sha256': 'source'}):
        with pytest.raises(RuntimeError, match='older|missing'):
            launcher.prepare_frontend(root)


def test_identity_is_content_based_including_dirty_source(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    with patch.object(launcher.subprocess, 'run') as run:
        run.return_value.stdout = 'main\n'
        before = launcher.build_identity(root)
        (root / 'frontend/src/App.tsx').write_text('new dirty interface')
        assert launcher.build_identity(root) != before
        after = launcher.build_identity(root)
        (root / 'frontend/dist/index.html').write_text('build output')
        assert launcher.build_identity(root) == after


def test_healthy_launcher_receipt_only_reused_for_current_identity(tmp_path: Path) -> None:
    from io import BytesIO
    root = workspace(tmp_path)
    owner = root / '.var/owner'
    owner.mkdir(parents=True)
    identity = {'revision': 'accepted-main', 'source_sha256': 'source'}
    (owner / 'launcher.json').write_text(json.dumps({'pids': [123, 456], 'build_identity': identity}))
    class Response(BytesIO):
        status = 200
    def get(url, **kwargs):
        return Response(b'{"runtime":{"demo_data":false}}' if '/api/' in url else b'current interface')
    with patch.object(launcher, 'prepare_frontend', return_value=identity), patch.object(launcher, 'prepare_workspace', return_value=owner), patch.object(launcher, 'urlopen', side_effect=get), patch.object(launcher.subprocess, 'Popen') as start:
        assert launcher.launch(root, open_browser=False) == 'http://127.0.0.1:5488/'
        start.assert_not_called()


def test_healthy_old_launcher_cannot_be_reused_when_revision_changes(tmp_path: Path) -> None:
    from io import BytesIO
    root = workspace(tmp_path)
    owner = root / '.var/owner'
    owner.mkdir(parents=True)
    (owner / 'launcher.json').write_text(json.dumps({'pids': [], 'build_identity': {'revision': 'october3'}}))
    class Response(BytesIO):
        status = 200
    def get(url, **kwargs):
        return Response(b'{"runtime":{"demo_data":false}}' if '/api/' in url else b'old interface')
    with patch.object(launcher, 'prepare_frontend', return_value={'revision': 'adopted-main'}), patch.object(launcher, 'prepare_workspace', return_value=owner), patch.object(launcher, 'urlopen', side_effect=get), patch.object(launcher, 'stop') as stop, patch.object(launcher, 'check_port_available'):
        # A fresh process cannot start in the unprepared fixture. It must never
        # succeed by reusing a healthy but stale receipt.
        with pytest.raises(RuntimeError, match='prepared'):
            launcher.launch(root, open_browser=False)
        stop.assert_called_once_with(root)


def test_ensure_local_ollama_if_available_discovers_macos_ollama_app_bundle(
    tmp_path: Path,
) -> None:
    app_ollama = Path("/Applications/Ollama.app/Contents/Resources/ollama")

    def fake_is_file(self: Path) -> bool:
        return self == app_ollama

    def fake_access(path: object, mode: int) -> bool:
        return Path(str(path)) == app_ollama

    conn_calls = 0

    class _DummySock:
        def __enter__(self) -> "_DummySock":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_connect(*args: object, **kwargs: object) -> _DummySock:
        nonlocal conn_calls
        conn_calls += 1
        if conn_calls == 1:
            raise ConnectionRefusedError()
        return _DummySock()

    with (
        patch.object(Path, "is_file", fake_is_file),
        patch.object(launcher.os, "access", side_effect=fake_access),
        patch.object(launcher.socket, "create_connection", side_effect=fake_connect),
        patch.object(launcher.subprocess, "Popen") as popen_mock,
    ):
        launcher.ensure_local_ollama_if_available(tmp_path)
        popen_mock.assert_called_once()
        assert popen_mock.call_args.args[0] == [str(app_ollama), "serve"]

