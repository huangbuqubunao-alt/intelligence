"""Local private-stage launcher; no installer, launchd or public packaging."""

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import yaml


def build_identity(project: Path) -> dict[str, str]:
    """Bind installed UI bytes to revision and actual source, including dirty work."""
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=project, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    digest = hashlib.sha256()
    frontend = project / "frontend"
    paths = []
    for directory, directories, files in os.walk(frontend):
        directories[:] = sorted(name for name in directories if name not in {"node_modules", "dist", ".git"})
        paths.extend(Path(directory) / name for name in files)
    for path in sorted(paths):
        relative = path.relative_to(frontend)
        if relative.parts[0] in {"src", "public"} or path.suffix in {".ts", ".tsx", ".css", ".html", ".json", ".mjs"}:
            digest.update(str(relative).encode() + b"\0" + path.read_bytes() + b"\0")
    return {"revision": revision, "source_sha256": digest.hexdigest()}


def build_assets(project: Path) -> dict[str, str]:
    dist = project / "frontend" / "dist"
    return {
        str(path.relative_to(dist)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dist.rglob("*"))
        if path.is_file() and path.name != "build-provenance.json"
    }


def current_build(project: Path, identity: dict[str, str]) -> bool:
    try:
        manifest = json.loads((project / "frontend/dist/build-provenance.json").read_text())
        assets = build_assets(project)
        return manifest["identity"] == identity and "index.html" in assets and manifest["assets"] == assets
    except (OSError, ValueError, KeyError, TypeError):
        return False


def prepare_frontend(project: Path) -> dict[str, str]:
    identity = build_identity(project)
    if current_build(project, identity):
        return identity
    if not (project / "frontend/node_modules/.bin/vite").exists():
        raise RuntimeError("Intelligence cannot prepare its current interface: installed frontend tools are missing. Restore the application runtime and reopen Intelligence.")
    try:
        subprocess.run(["npm", "run", "build"], cwd=project / "frontend", check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("Intelligence could not prepare its current interface. Inspect the launcher build error and reopen; an older interface will not be served.") from error
    if build_identity(project) != identity:
        raise RuntimeError("Application source changed while preparing the interface. Reopen Intelligence to rebuild it.")
    assets = build_assets(project)
    if "index.html" not in assets:
        raise RuntimeError("The interface build did not produce index.html. Reopen Intelligence after correcting the build error.")
    (project / "frontend/dist/build-provenance.json").write_text(
        json.dumps({"identity": identity, "assets": assets}, sort_keys=True) + "\n"
    )
    return identity


def prepare_workspace(project: Path) -> Path:
    """Fresh candidate workspace, separate from owner/M13 production data."""
    root = project / ".var" / "owner"
    (root / "config").mkdir(parents=True, exist_ok=True)
    for name in ("data", "logs", "vault"):
        (root / name).mkdir(exist_ok=True)
    settings = root / "config" / "settings.yaml"
    if not settings.exists():
        config = yaml.safe_load((project / "config" / "settings.example.yaml").read_text())
        config["storage"]["vault_root"] = str(root / "vault")
        settings.write_text(yaml.safe_dump(config, allow_unicode=True))
    channels = root / "config" / "channels.yaml"
    if not channels.exists():
        channels.write_text("channels:\n  - channel_id: UC_x5XG1OV2P6uZZ5FSM9Ttw\n    enabled: false\n    priority: 1\n")
    return root


def check_port_available(port: int) -> None:
    # On BSD/macOS SO_REUSEADDR can bind a specific address even while a
    # wildcard listener is active. Detect that listener without sending data.
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            pass
    except ConnectionRefusedError:
        pass
    except OSError as error:
        raise RuntimeError(f"Intelligence could not verify local port {port}. Inspect the local networking error and reopen Intelligence.") from error
    else:
        raise RuntimeError(f"Intelligence cannot start: local port {port} is in use. Close the application using it and reopen Intelligence.")
    with socket.socket() as probe:
        # Match the application servers' restart behavior: closed connections
        # may remain in TIME_WAIT, but a live listener must still be refused.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"Intelligence cannot start: local port {port} is in use. Close the application using it and reopen Intelligence.") from error


def launch(project: Path, *, open_browser: bool = True) -> str:
    identity = prepare_frontend(project)
    root = prepare_workspace(project)
    url = "http://127.0.0.1:5488/"
    pid_file = root / "launcher.json"
    if pid_file.exists():
        receipt = json.loads(pid_file.read_text())
        try:
            with urlopen("http://127.0.0.1:5489/api/v1/system", timeout=2) as response:
                healthy = json.load(response)["runtime"]["demo_data"] is False
            with urlopen(url, timeout=2) as response:
                healthy = healthy and response.status == 200
        except OSError:
            healthy = False
        if healthy and receipt.get("build_identity") == identity:
            if open_browser:
                subprocess.run(["/usr/bin/open", url], check=True)
            return url
        if healthy:
            stop(project)
            for _ in range(50):
                if all(subprocess.run(["/bin/ps", "-p", str(pid)], capture_output=True, check=False).returncode != 0 for pid in receipt["pids"]):
                    break
                time.sleep(0.1)
        # Removing a stale launcher receipt cannot remove any library authority.
        # Port checks below still refuse to replace any running process.
        pid_file.unlink(missing_ok=True)
    for port in (5488, 5489):
        check_port_available(port)
    python = project / ".venv" / "bin" / "python"
    vite = project / "frontend" / "node_modules" / ".bin" / "vite"
    if not python.exists() or not vite.exists() or not (project / "frontend" / "dist" / "index.html").exists():
        raise RuntimeError("The candidate must have its existing runtime and frontend build prepared first.")
    from youtube_intel.native_picker_build import prepare_native_picker
    picker = prepare_native_picker(project)
    env = dict(os.environ)
    inherited_paths = [str(Path(p).resolve()) for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join([str(project / "src"), *inherited_paths])
    commands = [
        [str(python), "-m", "youtube_intel", "--project-root", str(root), "serve-api", "--database", str(root / "state.sqlite3"), "--port", "5489", "--native-import-origin", "http://127.0.0.1:5488", "--native-import-origin", "http://localhost:5488", "--native-picker-executable", str(picker)],
        [str(vite), "preview", "--host", "127.0.0.1", "--port", "5488", "--strictPort"],
    ]
    processes = []
    try:
        for name, command in zip(("api", "ui"), commands):
            with (root / "logs" / f"{name}.log").open("ab") as log:
                child_env = dict(env, YIA_API_BASE="http://127.0.0.1:5489")
                processes.append(subprocess.Popen(command, cwd=project / "frontend", env=child_env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        for _ in range(100):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("The application could not start. Inspect the candidate workspace logs.")
            try:
                with urlopen("http://127.0.0.1:5489/api/v1/system", timeout=1) as api:
                    assert json.load(api)["runtime"]["demo_data"] is False
                with urlopen(url, timeout=1) as ui:
                    if ui.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("The application did not become ready.")
    except BaseException:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        raise
    pid_file.write_text(json.dumps({"pids": [process.pid for process in processes], "url": url, "build_identity": identity}))
    if open_browser:
        subprocess.run(["/usr/bin/open", url], check=True)
    return url


def stop(project: Path) -> None:
    receipt = project / ".var" / "owner" / "launcher.json"
    if not receipt.exists():
        return
    pids = []
    for pid in json.loads(receipt.read_text())["pids"]:
        command = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, check=False)
        if command.returncode == 0:
            if str(project) not in command.stdout:
                raise RuntimeError("A launcher process identity changed; no process was stopped.")
            pids.append(pid)
    # Verify every identity before stopping any process.
    for pid in pids:
        os.kill(pid, signal.SIGTERM)
    receipt.unlink()


def choose_vault(project: Path) -> None:
    root = prepare_workspace(project)
    selected = subprocess.run(["/usr/bin/osascript", "-e", 'POSIX path of (choose folder with prompt "Choose the Obsidian vault for explicit one-way publication / 选择 Obsidian 仓库")'], capture_output=True, text=True, check=True)
    vault = Path(selected.stdout.strip()).resolve(strict=True)
    if not vault.is_dir():
        raise ValueError("Choose an existing folder")
    settings = root / "config" / "settings.yaml"
    config = yaml.safe_load(settings.read_text())
    config["storage"]["vault_root"] = str(vault)
    stop(project)
    settings.write_text(yaml.safe_dump(config, allow_unicode=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--choose-vault", action="store_true")
    args = parser.parse_args()
    project = args.project_root.resolve()
    if args.stop:
        stop(project)
    else:
        if args.choose_vault:
            choose_vault(project)
        print(launch(project, open_browser=not args.no_browser))
