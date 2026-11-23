"""Integration tests for zero-config ``youtube-intel start`` launcher and preflight diagnostics."""

from __future__ import annotations

import sqlite3
from http import HTTPStatus
from pathlib import Path

import pytest

from youtube_intel import cli
from youtube_intel.fast_read_api import run_cli_with_fast_reads
from youtube_intel.operations import ExitCode
from youtube_intel.workspace_launcher import (
    prepare_local_workspace,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class _MemorySecret:
    def __init__(self) -> None:
        self.secret: str | None = None

    def get(self) -> str | None:
        return self.secret

    def load(self) -> str | None:
        return self.secret

    def save(self, value: str) -> None:
        self.secret = value

    def delete(self) -> None:
        self.secret = None


def test_prepare_local_workspace_cold_start_initializes_safe_runtime_and_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *_: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *_: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *_: "MODEL_UNAVAILABLE"
    )

    project_dir = (tmp_path / "fresh_clone").resolve()
    project_dir.mkdir(parents=True)
    web_dist = project_dir / "frontend" / "dist"
    web_dist.mkdir(parents=True)
    (web_dist / "index.html").write_text("<html><body>Intelligence UI</body></html>", encoding="utf-8")

    runtime = prepare_local_workspace(
        project_dir,
        ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        byok_credential_store=_MemorySecret(),
    )

    assert runtime.workspace_root == (project_dir / ".var" / "workspace").resolve()
    assert not (project_dir / ".var" / "owner").exists()
    assert runtime.settings_path.is_file()
    settings_text = runtime.settings_path.read_text(encoding="utf-8")
    assert "/absolute/path/to/obsidian/vault" not in settings_text
    assert runtime.config.settings.cloud.enabled is False
    assert runtime.config.settings.intelligence.mode.value == "local-only"
    assert runtime.vault_root == (runtime.workspace_root / "vault").resolve()
    assert runtime.web_dir == web_dist.resolve()
    assert runtime.preflight.ollama_reachable is True
    assert runtime.preflight.ollama_models == ("qwen3.5:9b",)

    sys_code, sys_body = runtime.fast_app.handle("GET", "/api/v1/system")
    assert sys_code == HTTPStatus.OK
    assert sys_body["release_posture"] == "PUBLIC_BETA"
    assert sys_body["runtime"]["demo_data"] is False

    dash_code, _ = runtime.fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_code == HTTPStatus.OK

    imp_code, imp_body = runtime.fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=quickstart.md",
        b"# Field Notes\nParagraph 2: Zero-config workspace binds TEXT_RANGE offsets cleanly.\n",
    )
    assert imp_code == HTTPStatus.CREATED
    md_id = str(imp_body["import"]["content_id"])

    sess_code, sess_body = runtime.fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert sess_code == HTTPStatus.OK
    scope_vids = {v["video_id"]: v for v in sess_body["scope_options"]["videos"]}
    assert md_id in scope_vids
    assert scope_vids[md_id]["locator_kind"] == "TEXT_RANGE"


def test_prepare_local_workspace_is_idempotent_and_preserves_custom_settings_and_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *_: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *_: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *_: "MODEL_UNAVAILABLE"
    )

    ws_root = (tmp_path / "ws").resolve()
    first = prepare_local_workspace(
        REPO_ROOT,
        workspace_root=ws_root,
        ollama_probe=lambda _url: (False, ()),
        byok_credential_store=_MemorySecret(),
    )
    imp_code, imp_body = first.fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=persist-me.md",
        b"# Persist\nKeep imported content intact across restarts.\n",
    )
    assert imp_code == HTTPStatus.CREATED
    md_id = str(imp_body["import"]["content_id"])

    # Simulate user customizing settings.yaml (summary_score threshold)
    custom_text = first.settings_path.read_text(encoding="utf-8").replace(
        "summary_score: 7.0", "summary_score: 8.5"
    )
    first.settings_path.write_text(custom_text, encoding="utf-8")

    second = prepare_local_workspace(
        REPO_ROOT,
        workspace_root=ws_root,
        ollama_probe=lambda _url: (False, ()),
        byok_credential_store=_MemorySecret(),
    )
    assert second.config.settings.thresholds.summary_score == 8.5
    with sqlite3.connect(second.database) as conn:
        row = conn.execute("SELECT video_id FROM videos WHERE video_id = ?", (md_id,)).fetchone()
        assert row is not None


def test_prepare_local_workspace_explicit_vault_and_symlink_or_missing_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *_: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *_: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *_: "MODEL_UNAVAILABLE"
    )

    obsidian_vault = (tmp_path / "ObsidianVault").resolve()
    obsidian_vault.mkdir()
    runtime = prepare_local_workspace(
        REPO_ROOT,
        workspace_root=tmp_path / "ws",
        vault_dir=obsidian_vault,
        ollama_probe=lambda _url: (False, ()),
        byok_credential_store=_MemorySecret(),
    )
    assert runtime.vault_root == obsidian_vault
    assert Path(runtime.config.settings.storage.vault_root) == obsidian_vault
    assert (obsidian_vault / "YouTube Intel").is_dir()

    missing_vault = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="Explicit --vault directory does not exist"):
        prepare_local_workspace(
            REPO_ROOT,
            workspace_root=tmp_path / "ws_bad1",
            vault_dir=missing_vault,
            ollama_probe=lambda _url: (False, ()),
            byok_credential_store=_MemorySecret(),
        )

    symlink_vault = tmp_path / "vault_link"
    symlink_vault.symlink_to(obsidian_vault)
    with pytest.raises(ValueError, match="must not be a symlink"):
        prepare_local_workspace(
            REPO_ROOT,
            workspace_root=tmp_path / "ws_bad2",
            vault_dir=symlink_vault,
            ollama_probe=lambda _url: (False, ()),
            byok_credential_store=_MemorySecret(),
        )


def test_cli_start_check_only_across_both_entrypoints_without_touching_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *_: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *_: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *_: "MODEL_UNAVAILABLE"
    )
    monkeypatch.setattr(
        "youtube_intel.workspace_launcher._probe_ollama_models_default",
        lambda _url: (False, ()),
    )

    ws_a = (tmp_path / "ws_cli").resolve()
    ws_b = (tmp_path / "ws_module").resolve()
    missing_dist = tmp_path / "no_dist"

    rc_cli = cli.main(
        [
            "--project-root",
            str(REPO_ROOT),
            "start",
            "--workspace-root",
            str(ws_a),
            "--web-dir",
            str(missing_dist),
            "--check-only",
        ]
    )
    out_cli = capsys.readouterr().out
    assert rc_cli == ExitCode.OK
    assert "Preflight Checklist (--check-only)" in out_cli
    assert "npm run build" in out_cli
    assert "ollama pull qwen3.5:9b" in out_cli
    assert "15-Min Verification" in out_cli

    rc_mod = run_cli_with_fast_reads(
        [
            "--project-root",
            str(REPO_ROOT),
            "start",
            "--workspace-root",
            str(ws_b),
            "--web-dir",
            str(missing_dist),
            "--check-only",
        ]
    )
    out_mod = capsys.readouterr().out
    assert rc_mod == ExitCode.OK
    assert "Preflight Checklist (--check-only)" in out_mod

    # Invalid explicit vault exits cleanly with USAGE_OR_CONFIGURATION
    rc_bad = cli.main(
        [
            "--project-root",
            str(REPO_ROOT),
            "start",
            "--workspace-root",
            str(tmp_path / "ws_invalid"),
            "--vault",
            str(tmp_path / "missing_obsidian_vault"),
            "--check-only",
        ]
    )
    err_bad = capsys.readouterr().err
    assert rc_bad == ExitCode.USAGE_OR_CONFIGURATION
    assert "does not exist" in err_bad


def test_serve_api_reports_actionable_hint_when_vault_root_placeholder_is_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_proj = (tmp_path / "proj").resolve()
    (fake_proj / "config").mkdir(parents=True)
    (fake_proj / "config" / "settings.yaml").write_text(
        (REPO_ROOT / "config" / "settings.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (fake_proj / "config" / "channels.yaml").write_text(
        (REPO_ROOT / "config" / "channels.example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run_cli_with_fast_reads(
        [
            "--project-root",
            str(fake_proj),
            "serve-api",
            "--database",
            str(fake_proj / ".var" / "owner" / "state.sqlite3"),
            "--port",
            "18791",
        ]
    )
    err = capsys.readouterr().err
    assert rc == ExitCode.LOCAL_RESOURCE
    assert "storage.vault_root does not exist" in err
    assert "uv run youtube-intel start" in err

    # Direct cli.main entrypoint behaves consistently
    rc2 = cli.main(
        [
            "--project-root",
            str(fake_proj),
            "serve-api",
            "--database",
            str(fake_proj / ".var" / "owner" / "state.sqlite3"),
            "--port",
            "18791",
        ]
    )
    err2 = capsys.readouterr().err
    assert rc2 == ExitCode.LOCAL_RESOURCE
    assert "storage.vault_root does not exist" in err2
    assert "uv run youtube-intel start" in err2
