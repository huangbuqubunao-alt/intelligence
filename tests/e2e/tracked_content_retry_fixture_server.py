"""Ordinary runtime factory, isolated tracked history and offline caption boundary."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import _load_module, isolated_credential_store  # noqa: E402

from youtube_intel.extractive_summary import ExtractiveSummaryService  # noqa: E402
from youtube_intel.local_api import serve_loopback  # noqa: E402
from youtube_intel.runtime_composition import (
    build_local_source_run_runtime,  # noqa: E402
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    arguments = parser.parse_args()
    arguments.root = arguments.root.resolve()
    arguments.root.mkdir(parents=True)
    patch = pytest.MonkeyPatch()
    isolated_credential_store.__wrapped__(patch)
    support = _load_module('test_tracked_content_retry')
    repo, _source, cid, _old, adapter, fixture, runtime, _service = support.failed_tracked(arguments.root, patch)
    composition = build_local_source_run_runtime(
        config=runtime._config, project_root=arguments.root,
        database=repo._database_path, dependencies=runtime._dependencies,
        now=lambda: fixture.now,
    )
    calls: list[str] = []
    for name in ('enumerate_tracks', 'read_track'):
        original = getattr(adapter, name)

        def count(value, *, operation=original, label=name):
            calls.append(label)
            return operation(value)

        setattr(adapter, name, count)
    create = ExtractiveSummaryService.create
    state = {'local_failure': True}

    def create_summary(self, *args, **kwargs):
        if state['local_failure']:
            raise OSError('isolated local finalization failure')
        return create(self, *args, **kwargs)

    patch.setattr(ExtractiveSummaryService, 'create', create_summary)
    application = composition.application
    handle = application.handle

    def route(method, path, body=b''):
        if method == 'POST' and path == '/api/v1/fixture/run':
            composition.worker.run_once()
            return 200, {'calls': calls}
        if method == 'POST' and path == '/api/v1/fixture/local-ready':
            state['local_failure'] = False
            return 200, {'calls': calls}
        if method == 'GET' and path == '/api/v1/fixture/proof':
            with composition.repository._connect() as connection:
                attempts = [dict(row) for row in connection.execute("SELECT job_id,attempt_count,status FROM jobs WHERE job_id GLOB 'tracked-content-retry-job:*'")]
            return 200, {'calls': calls, 'attempts': attempts, 'content_id': cid}
        try:
            return handle(method, path, body)
        except Exception:
            traceback.print_exc()
            raise

    application.handle = route
    server = serve_loopback(application, port=arguments.port)
    print(json.dumps({'port': arguments.port, 'content_id': cid}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        patch.undo()


if __name__ == '__main__':
    main()
