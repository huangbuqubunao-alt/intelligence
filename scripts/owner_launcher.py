"""Local private-stage launcher; no installer, launchd or public packaging."""

import argparse
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import yaml


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


def launch(project: Path, *, open_browser: bool = True) -> str:
    root = prepare_workspace(project)
    url = "http://127.0.0.1:5488/"
    pid_file = root / "launcher.json"
    if pid_file.exists():
        try:
            with urlopen("http://127.0.0.1:5489/api/v1/system", timeout=2) as response:
                healthy = json.load(response)["runtime"]["demo_data"] is False
            with urlopen(url, timeout=2) as response:
                healthy = healthy and response.status == 200
        except OSError:
            healthy = False
        if healthy:
            if open_browser:
                subprocess.run(["/usr/bin/open", url], check=True)
            return url
        # Removing a stale launcher receipt cannot remove any library authority.
        # Port checks below still refuse to replace any running process.
        pid_file.unlink()
    for port in (5488, 5489):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    python = project / ".venv" / "bin" / "python"
    vite = project / "frontend" / "node_modules" / ".bin" / "vite"
    if not python.exists() or not vite.exists() or not (project / "frontend" / "dist" / "index.html").exists():
        raise RuntimeError("The candidate must have its existing runtime and frontend build prepared first.")
    env = dict(os.environ)
    inherited_paths = [str(Path(p).resolve()) for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join([str(project / "src"), *inherited_paths])
    commands = [
        [str(python), "-m", "youtube_intel", "--project-root", str(root), "serve-api", "--database", str(root / "state.sqlite3"), "--port", "5489"],
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
    pid_file.write_text(json.dumps({"pids": [process.pid for process in processes], "url": url}))
    if open_browser:
        subprocess.run(["/usr/bin/open", url], check=True)
    return url


def stop(project: Path) -> None:
    receipt = project / ".var" / "owner" / "launcher.json"
    if not receipt.exists():
        return
    for pid in json.loads(receipt.read_text())["pids"]:
        command = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, check=False)
        if command.returncode == 0:
            if str(project) not in command.stdout:
                raise RuntimeError("A launcher process identity changed; no process was stopped.")
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
