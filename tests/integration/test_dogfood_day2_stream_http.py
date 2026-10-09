"""Real loopback cancellation, idle timeout and serialized admission boundaries."""

import http.client
import json
import socket
import threading
import time
from datetime import UTC, datetime

import pytest

from youtube_intel import local_api
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_authority import MAX_MEDIA_BYTES
from youtube_intel.state import SQLiteStateRepository


@pytest.fixture
def server(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=datetime(2026, 10, 9, tzinfo=UTC))
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=tmp_path / "data")
    server = serve_loopback(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, app, tmp_path
    server.shutdown()
    server.server_close()
    thread.join()


def connection(server, method="POST", length=4):
    request = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    request.putrequest(method, "/api/v1/local/imports?filename=notes.txt")
    request.putheader("Content-Length", str(length))
    request.putheader("Content-Type", "application/octet-stream")
    request.putheader("X-YIA-Request", "local-ui")
    request.endheaders()
    return request


def wait_idle(app):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if app._local_import_slot.acquire(blocking=False):
            app._local_import_slot.release()
            return
        time.sleep(0.01)
    raise AssertionError("import did not release its slot")


def test_incomplete_upload_cleans_and_allows_retry(server):
    service, app, root = server
    request = connection(service)
    request.send(b"x")
    request.sock.shutdown(socket.SHUT_WR)
    response = request.getresponse()
    assert response.status == 422
    assert json.loads(response.read())["error"]["code"] == "LOCAL_IMPORT_INTERRUPTED"
    request.close()
    wait_idle(app)
    assert list((root / "data/.imports").iterdir()) == []
    assert not app._repository.list_videos()
    retry = connection(service)
    retry.send(b"text")
    assert retry.getresponse().status == 201
    retry.close()


def test_idle_timeout_cleans_and_is_distinct(server, monkeypatch):
    service, app, root = server
    monkeypatch.setattr(local_api, "UPLOAD_IDLE_TIMEOUT_SECONDS", 0.05)
    request = connection(service)
    request.send(b"x")
    response = request.getresponse()
    assert response.status == 408
    assert json.loads(response.read())["error"]["code"] == "LOCAL_IMPORT_TIMEOUT"
    request.close()
    wait_idle(app)
    assert list((root / "data/.imports").iterdir()) == []


def test_overlap_returns_busy_without_second_staging(server):
    service, app, root = server
    request = connection(service)
    request.send(b"x")
    deadline = time.monotonic() + 3
    while not list((root / "data/.imports").glob(".import-*")) if (root / "data/.imports").exists() else True:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    repeated = connection(service)
    response = repeated.getresponse()
    assert response.status == 429
    assert json.loads(response.read())["error"]["code"] == "LOCAL_IMPORT_BUSY"
    repeated.close()
    request.sock.shutdown(socket.SHUT_WR)
    request.getresponse().read()
    request.close()
    wait_idle(app)


@pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
def test_stream_route_remains_post_only(server, method):
    service, app, _ = server
    request = connection(service, method, 2)
    request.send(b"{}")
    assert request.getresponse().status == 404
    request.close()
    assert not app._repository.list_videos()


def test_over_limit_rejected_before_any_body_is_received(server):
    service, app, _ = server
    request = http.client.HTTPConnection("127.0.0.1", service.server_port, timeout=5)
    request.putrequest("POST", "/api/v1/local/imports?filename=clip.mp4")
    request.putheader("Content-Length", str(MAX_MEDIA_BYTES + 1))
    request.putheader("Content-Type", "application/octet-stream")
    request.putheader("X-YIA-Request", "local-ui")
    request.endheaders()
    response = request.getresponse()
    assert response.status == 413
    assert json.loads(response.read())["error"]["code"] == "LOCAL_FILE_TOO_LARGE"
    request.close()
    assert not app._repository.list_videos()
