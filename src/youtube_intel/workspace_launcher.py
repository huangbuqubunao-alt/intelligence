"""Zero-config local workspace launcher and environment preflight checks."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from youtube_intel.config import AppConfig, AppSettings, load_app_config
from youtube_intel.fast_read_api import (
    FastReadApiApplication,
    _raise_open_file_limit,
    run_fast_read_server_loop,
)
from youtube_intel.model_settings import CredentialStore
from youtube_intel.offline_transcription import media_tool
from youtube_intel.operations import ExitCode
from youtube_intel.runtime_composition import (
    LocalSourceRunRuntime,
    build_local_source_run_runtime,
)
from youtube_intel.workspace_intelligence_hub import (
    DEFAULT_OLLAMA_BASE_URL,
    WorkspaceIntelligenceHub,
    _infer_ollama_model_vision_by_name,
    _probe_ollama_model_vision_http,
    _probe_ollama_models_default,
)

OllamaProbe = Callable[[str], tuple[bool, tuple[str, ...]]]

_DEFAULT_CHANNELS_YAML = (
    "channels:\n"
    "  - channel_id: UCExampleDisabledPlaceholder\n"
    "    enabled: false\n"
    "    priority: 10\n"
)


def default_workspace_root(project_root: Path) -> Path:
    """Return the default isolated runtime directory for ``youtube-intel start``."""

    return project_root.resolve() / ".var" / "workspace"


@dataclass(frozen=True, slots=True)
class WorkspacePreflight:
    platform_supported: bool
    frontend_ready: bool
    ollama_reachable: bool
    ollama_models: tuple[str, ...]
    yt_dlp_available: bool
    ffmpeg_available: bool
    web_dir: Path
    ollama_vision_ready: bool | None = None
    ollama_vision_models: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LocalWorkspaceRuntime:
    project_root: Path
    workspace_root: Path
    database: Path
    data_root: Path
    vault_root: Path
    web_dir: Path | None
    settings_path: Path
    channels_path: Path
    config: AppConfig
    preflight: WorkspacePreflight
    composition: LocalSourceRunRuntime
    hub: WorkspaceIntelligenceHub
    fast_app: FastReadApiApplication


def collect_workspace_preflight(
    project_root: Path,
    *,
    web_dir: Path | None = None,
    ollama_url: str = DEFAULT_OLLAMA_BASE_URL,
    ollama_probe: OllamaProbe | None = None,
) -> WorkspacePreflight:
    """Probe local OS, built frontend bundle, Ollama loopback, yt-dlp, and ffmpeg."""

    resolved_web = (web_dir or (project_root.resolve() / "frontend" / "dist")).resolve()
    probe = ollama_probe or _probe_ollama_models_default
    try:
        reachable, models = probe(ollama_url)
    except Exception:
        reachable, models = False, ()
    clean_models = tuple(models)
    vision_models: list[str] = []
    if reachable and clean_models:
        for model_name in clean_models[:8]:
            name_hint = _infer_ollama_model_vision_by_name(model_name)
            if name_hint is True:
                vision_models.append(model_name)
                continue
            if name_hint is False:
                continue
            if ollama_probe is None:
                probed = _probe_ollama_model_vision_http(ollama_url, model_name)
                if probed is True:
                    vision_models.append(model_name)
    return WorkspacePreflight(
        platform_supported=importlib.util.find_spec("fcntl") is not None,
        frontend_ready=(resolved_web / "index.html").is_file(),
        ollama_reachable=bool(reachable),
        ollama_models=clean_models,
        yt_dlp_available=importlib.util.find_spec("yt_dlp") is not None,
        ffmpeg_available=media_tool("ffmpeg") is not None,
        web_dir=resolved_web,
        ollama_vision_ready=bool(vision_models),
        ollama_vision_models=tuple(vision_models),
    )


def _find_example_settings(project_root: Path) -> Path:
    candidate = project_root / "config" / "settings.example.yaml"
    if candidate.is_file():
        return candidate
    fallback = Path(__file__).resolve().parents[2] / "config" / "settings.example.yaml"
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(
        "Could not locate config/settings.example.yaml to initialize local workspace settings."
    )


def _ensure_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{label} must be a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _resolve_vault_dir(workspace_root: Path, vault_dir: Path | None) -> Path:
    if vault_dir is None:
        return _ensure_directory(workspace_root / "vault", label="vault directory")
    if vault_dir.is_symlink():
        raise ValueError(f"Explicit --vault path must not be a symlink: {vault_dir}")
    resolved = vault_dir.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Explicit --vault directory does not exist: {vault_dir}")
    return resolved


def _ensure_workspace_configs(
    *,
    project_root: Path,
    workspace_root: Path,
    vault_dir: Path | None,
) -> tuple[Path, Path, Path, AppConfig]:
    config_dir = _ensure_directory(
        workspace_root / "config", label="workspace config directory"
    )
    settings_path = config_dir / "settings.yaml"
    channels_path = config_dir / "channels.yaml"

    explicit_vault = (
        _resolve_vault_dir(workspace_root, vault_dir) if vault_dir is not None else None
    )
    if not settings_path.exists():
        default_vault = explicit_vault or _resolve_vault_dir(workspace_root, None)
        example_path = _find_example_settings(project_root)
        raw_loaded: Any = yaml.safe_load(example_path.read_text(encoding="utf-8"))
        if not isinstance(raw_loaded, dict):
            raise ValueError(f"Invalid settings template at {example_path}")
        raw_dict = dict(raw_loaded)
        storage_cfg = dict(raw_dict.get("storage") or {})
        storage_cfg["vault_root"] = str(default_vault)
        raw_dict["storage"] = storage_cfg
        cloud_cfg = dict(raw_dict.get("cloud") or {})
        cloud_cfg["enabled"] = False
        raw_dict["cloud"] = cloud_cfg
        intel_cfg = dict(raw_dict.get("intelligence") or {})
        intel_cfg["mode"] = "local-only"
        raw_dict["intelligence"] = intel_cfg
        AppSettings.model_validate(raw_dict)
        settings_path.write_text(
            yaml.safe_dump(raw_dict, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    if not channels_path.exists():
        channels_path.write_text(_DEFAULT_CHANNELS_YAML, encoding="utf-8")

    config = load_app_config(channels_path, settings_path)
    if (
        explicit_vault is not None
        and Path(config.settings.storage.vault_root) != explicit_vault
    ):
        values = config.settings.model_dump(mode="json")
        values["storage"]["vault_root"] = str(explicit_vault)
        config = AppConfig(
            channels=config.channels,
            settings=AppSettings.model_validate(values),
        )
        effective_vault = explicit_vault
    else:
        configured_vault = Path(config.settings.storage.vault_root)
        if configured_vault.is_symlink():
            raise ValueError(
                f"Configured storage.vault_root must not be a symlink: {configured_vault}"
            )
        if not configured_vault.is_dir():
            raise FileNotFoundError(
                f"Configured storage.vault_root does not exist: {configured_vault}"
            )
        effective_vault = configured_vault.resolve()
    return settings_path, channels_path, effective_vault, config


def _resolve_workspace_config(
    *,
    project_root: Path,
    workspace_root: Path | None,
    vault_dir: Path | None,
) -> tuple[Path, Path, Path, Path, Path, AppConfig]:
    resolved_project = project_root.resolve()
    raw_root = workspace_root if workspace_root is not None else default_workspace_root(resolved_project)
    if raw_root.is_symlink():
        raise ValueError(f"workspace_root must not be a symlink: {raw_root}")
    if raw_root.exists() and not raw_root.is_dir():
        raise ValueError(f"workspace_root must be a directory: {raw_root}")
    resolved_root = _ensure_directory(raw_root, label="workspace_root")

    for sub in ("data", "logs", "templates"):
        _ensure_directory(resolved_root / sub, label=f"workspace {sub} directory")

    settings_path, channels_path, resolved_vault, config = _ensure_workspace_configs(
        project_root=resolved_project,
        workspace_root=resolved_root,
        vault_dir=vault_dir,
    )
    return (
        resolved_project,
        resolved_root,
        resolved_vault,
        settings_path,
        channels_path,
        config,
    )


def prepare_local_workspace(
    project_root: Path,
    *,
    workspace_root: Path | None = None,
    vault_dir: Path | None = None,
    web_dir: Path | None = None,
    ollama_probe: OllamaProbe | None = None,
    byok_credential_store: CredentialStore | None = None,
) -> LocalWorkspaceRuntime:
    """Idempotently initialize and validate a zero-config local workspace runtime."""

    (
        resolved_project,
        resolved_root,
        resolved_vault,
        settings_path,
        channels_path,
        config,
    ) = _resolve_workspace_config(
        project_root=project_root,
        workspace_root=workspace_root,
        vault_dir=vault_dir,
    )
    db_path = resolved_root / "state.sqlite3"
    data_root = resolved_root / "data"

    composition = build_local_source_run_runtime(
        config=config,
        project_root=resolved_root,
        database=db_path,
        credential_store=byok_credential_store,
        bigmodel_credential_store=byok_credential_store,
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
    )
    preflight = collect_workspace_preflight(
        resolved_project,
        web_dir=web_dir,
        ollama_url=str(config.settings.local_scoring.base_url),
        ollama_probe=ollama_probe,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=data_root,
        project_root=resolved_root,
        byok_credential_store=byok_credential_store,
        installed_ollama_probe=ollama_probe,
    )
    hub.ensure_ready()
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    active_web_dir = preflight.web_dir if preflight.frontend_ready else None
    return LocalWorkspaceRuntime(
        project_root=resolved_project,
        workspace_root=resolved_root,
        database=db_path,
        data_root=data_root,
        vault_root=resolved_vault,
        web_dir=active_web_dir,
        settings_path=settings_path,
        channels_path=channels_path,
        config=config,
        preflight=preflight,
        composition=composition,
        hub=hub,
        fast_app=fast_app,
    )


def _resolve_preflight_vision(pf: WorkspacePreflight) -> tuple[bool, tuple[str, ...]]:
    if pf.ollama_vision_ready is not None:
        return pf.ollama_vision_ready, pf.ollama_vision_models
    if pf.ollama_reachable and pf.ollama_models:
        inferred = tuple(
            m for m in pf.ollama_models if _infer_ollama_model_vision_by_name(m) is True
        )
        if not inferred and pf.ollama_vision_models:
            return True, pf.ollama_vision_models
        return bool(inferred), inferred
    return False, pf.ollama_vision_models


def _format_readiness_verdict(pf: WorkspacePreflight, *, serve_web: bool) -> str:
    """Summarize launch readiness into an actionable single-line verdict."""

    if not pf.platform_supported:
        return (
            "[BLOCKED] Native Windows without fcntl is unsupported — "
            "run inside WSL2 (Ubuntu) / 原生 Windows 暂不支持，请在 WSL2 (Ubuntu) 中运行"
        )
    if serve_web and not pf.frontend_ready:
        return (
            "[ACTION NEEDED] Web UI bundle missing — run: cd frontend && npm ci && npm run build "
            "(or pass --no-web) / 前端未构建，请先构建或加 --no-web"
        )
    vision_ready, _ = _resolve_preflight_vision(pf)
    gaps: list[str] = []
    if not pf.ollama_reachable or not pf.ollama_models:
        gaps.append("Ollama model")
    elif not vision_ready:
        gaps.append("Ollama vision model")
    if not pf.yt_dlp_available:
        gaps.append("yt-dlp")
    if not pf.ffmpeg_available:
        gaps.append("ffmpeg")
    if gaps:
        if pf.ollama_reachable and pf.ollama_models and not vision_ready:
            return (
                "[READY WITH WARNINGS] Launchable now (`uv run youtube-intel start`) "
                "for text AI & browsing; frame extraction (`ffmpeg`) is "
                f"{'ready' if pf.ffmpeg_available else 'missing'}, while current Ollama models are text-only "
                f"(setup: {', '.join(gaps)} — pull e.g. `gemma3:4b` or `qwen3.5:9b` for visual interpretation)."
            )
        return (
            "[READY WITH WARNINGS] Launchable now (`uv run youtube-intel start`) "
            f"for browsing & .md import; optional setup ({', '.join(gaps)}) unlocks "
            "local AI / media & visual keyframes."
        )
    return (
        "[ALL READY] Launch now with `uv run youtube-intel start` — "
        "local AI, media import & visual keyframes ready."
    )


def format_startup_banner(
    runtime: LocalWorkspaceRuntime,
    *,
    port: int,
    serve_web: bool,
    check_only: bool,
) -> str:
    """Format a bilingual status banner with actionable fixes for any missing prereqs."""

    pf = runtime.preflight
    vision_ready, vision_models = _resolve_preflight_vision(pf)
    mode_tag = "Preflight Checklist (--check-only)" if check_only else "Workspace Ready"
    ui_url = (
        f"http://127.0.0.1:{port}/"
        if (serve_web and pf.frontend_ready)
        else f"http://127.0.0.1:{port}/api/v1/system (API-only)"
    )
    if pf.ollama_models:
        preview = ", ".join(pf.ollama_models[:4])
        ollama_models_summary = (
            f"{preview} (+{len(pf.ollama_models) - 4} more)"
            if len(pf.ollama_models) > 4
            else preview
        )
    else:
        ollama_models_summary = "none pulled — run: ollama pull qwen3.5:9b"

    lines = [
        f"[youtube-intel start] {mode_tag}",
        f"  URL / 访问地址      : {ui_url}",
        f"  Workspace / 工作区  : {runtime.workspace_root}",
        f"  Database / 数据库   : {runtime.database}",
        f"  Obsidian Vault      : {runtime.vault_root}",
        "  Preflight / 环境自检:",
        (
            "    [OK]   Platform   : POSIX runtime supported (macOS / Linux / WSL2)"
            if pf.platform_supported
            else "    [FAIL] Platform   : fcntl unavailable; run inside WSL2 on Windows"
        ),
        (
            f"    [OK]   Frontend   : Built Web UI ready ({pf.web_dir})"
            if pf.frontend_ready
            else f"    [WARN] Frontend   : Bundle missing at {pf.web_dir}. Build via: cd frontend && npm ci && npm run build"
        ),
        (
            f"    [OK]   Ollama     : Reachable ({len(pf.ollama_models)} models: {ollama_models_summary})"
            if pf.ollama_reachable
            else "    [WARN] Ollama     : Local Ollama offline (optional for browsing/import; install at https://ollama.com/ then run: ollama pull qwen3.5:9b)"
        ),
        (
            f"    [OK]   Vision     : Local multimodal interpretation ready ({', '.join(vision_models[:3])})"
            if vision_ready
            else "    [WARN] Vision     : No vision-capable Ollama model detected (text-only models cannot interpret keyframe images; run: ollama pull gemma3:4b or qwen3.5:9b)"
        ),
        (
            "    [OK]   yt-dlp     : Installed (YouTube & Bilibili captions ready)"
            if pf.yt_dlp_available
            else "    [WARN] yt-dlp     : Missing from Python env; reinstall deps via: uv sync"
        ),
        (
            "    [OK]   ffmpeg     : Installed (audio/video import, transcription & frame extraction ready)"
            if pf.ffmpeg_available
            else "    [WARN] ffmpeg     : Optional media tool missing (needed for .mp4/.m4a import & frame extraction); install via `brew install ffmpeg` or `apt install ffmpeg`"
        ),
        f"  Readiness / 就绪结论 : {_format_readiness_verdict(pf, serve_web=serve_web)}",
        "  15-Min Verification / 15分钟体验指南:",
        "    1) Import 1 video/URL + 1 local .md/.txt note via UI or `POST /api/v1/local/imports`",
        "    2) Ask 1 cross-source question (check clickable `?t=` & `P#` citations) + 1 trick unanswerable question (verify honest refusal)",
        "    3) Copy or download Markdown note into Obsidian and click the timestamp deep link.",
    ]
    if not check_only:
        lines.append("  Press Ctrl+C to stop cleanly.")
    return "\n".join(lines)


def serve_local_workspace(
    project_root: Path,
    *,
    port: int = 8765,
    workspace_root: Path | None = None,
    vault_dir: Path | None = None,
    web_dir: Path | None = None,
    serve_web: bool = True,
    check_only: bool = False,
    ollama_probe: OllamaProbe | None = None,
    byok_credential_store: CredentialStore | None = None,
) -> ExitCode:
    """Prepare the zero-config local workspace, print diagnostics, and optionally serve."""

    if port < 1024 or port > 65535:
        print(
            f"ERROR: Invalid port {port}; choose a port between 1024 and 65535.",
            file=sys.stderr,
        )
        return ExitCode.USAGE_OR_CONFIGURATION

    _raise_open_file_limit()
    if importlib.util.find_spec("fcntl") is None:
        print(
            "ERROR: Native Windows without fcntl is not supported at runtime. Please run inside WSL2 (Ubuntu).",
            file=sys.stderr,
        )
        return ExitCode.LOCAL_RESOURCE

    runtime = prepare_local_workspace(
        project_root,
        workspace_root=workspace_root,
        vault_dir=vault_dir,
        web_dir=web_dir,
        ollama_probe=ollama_probe,
        byok_credential_store=byok_credential_store,
    )
    print(
        format_startup_banner(
            runtime,
            port=port,
            serve_web=serve_web,
            check_only=check_only,
        ),
        flush=True,
    )
    if check_only:
        return ExitCode.OK

    static_dir = runtime.web_dir if serve_web else None

    def _compose_on_boot() -> LocalSourceRunRuntime:
        (_, _, _, _, _, latest_cfg) = _resolve_workspace_config(
            project_root=runtime.project_root,
            workspace_root=runtime.workspace_root,
            vault_dir=vault_dir,
        )
        return build_local_source_run_runtime(
            config=latest_cfg,
            project_root=runtime.workspace_root,
            database=runtime.database,
            credential_store=byok_credential_store,
            bigmodel_credential_store=byok_credential_store,
            allow_environment_credentials=False,
            allow_cloud_execution=False,
            probe_local_runtime=False,
        )

    return run_fast_read_server_loop(
        compose_runtime=_compose_on_boot,
        port=port,
        static_dir=static_dir,
        hub_factory=lambda comp: WorkspaceIntelligenceHub(
            repository=comp.repository,
            data_root=runtime.data_root,
            project_root=runtime.workspace_root,
            byok_credential_store=byok_credential_store,
            installed_ollama_probe=ollama_probe,
        ),
    )


__all__ = [
    "LocalWorkspaceRuntime",
    "WorkspacePreflight",
    "collect_workspace_preflight",
    "default_workspace_root",
    "format_startup_banner",
    "prepare_local_workspace",
    "serve_local_workspace",
]
