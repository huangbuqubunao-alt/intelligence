"""Launcher must bind served bytes to current source, never existence/timestamps."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

_SPEC = importlib.util.spec_from_file_location('owner_launcher', Path(__file__).resolve().parents[2] / 'scripts/owner_launcher.py')
assert _SPEC and _SPEC.loader
launcher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(launcher)


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
