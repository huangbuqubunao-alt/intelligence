"""Isolated pilot launcher for the OpenCode user-pilot dogfood session.

Mirrors scripts/owner_launcher.py but never touches the production owner
runtime, database, ports or browser profile:

  UI   http://127.0.0.1:5588/
  API  http://127.0.0.1:5589/
  data <project>/.var/user-pilot   (config, data, logs, vault, state.sqlite3)
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import yaml

DEFAULT_UI_PORT = 5588
DEFAULT_API_PORT = 5589
RUNTIME_DIRNAME = "user-pilot"


def pilot_root(project: Path) -> Path:
    return project / ".var" / RUNTIME_DIRNAME


def prepare_workspace(project: Path) -> Path:
    root = pilot_root(project)
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
        channels.write_text(
            "channels:\n  - channel_id: UC_x5XG1OV2P6uZZ5FSM9Ttw\n    enabled: false\n    priority: 1\n"
        )
    return root


def check_port_available(port: int) -> None:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            pass
    except ConnectionRefusedError:
        pass
    except OSError as error:
        raise RuntimeError(f"cannot verify pilot port {port}: {error}") from error
    else:
        raise RuntimeError(f"pilot port {port} is already in use")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"pilot port {port} is in use: {error}") from error


def launch(project: Path, *, ui_port: int, api_port: int) -> str:
    root = prepare_workspace(project)
    url = f"http://127.0.0.1:{ui_port}/"
    receipt_path = root / "launcher.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if all(
            subprocess.run(["/bin/ps", "-p", str(pid)], capture_output=True, check=False).returncode == 0
            for pid in receipt["pids"]
        ):
            raise RuntimeError("pilot instance already running; stop it first")
        receipt_path.unlink()
    for port in (ui_port, api_port):
        check_port_available(port)

    python = project / ".venv" / "bin" / "python"
    vite = project / "frontend" / "node_modules" / ".bin" / "vite"
    if not vite.exists():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=project / "frontend", check=True)
    if not (project / "frontend" / "dist" / "index.html").exists():
        subprocess.run(["npm", "run", "build"], cwd=project / "frontend", check=True)
    if not python.exists() or not vite.exists():
        raise RuntimeError("pilot runtime prerequisites are missing")

    sys.path.insert(0, str(project / "src"))
    from youtube_intel.native_picker_build import prepare_native_picker

    picker = prepare_native_picker(project)

    env = dict(os.environ)
    inherited = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join([str(project / "src"), *inherited])

    commands = [
        [
            str(python), "-m", "youtube_intel", "--project-root", str(root), "serve-api",
            "--database", str(root / "state.sqlite3"), "--port", str(api_port),
            "--native-import-origin", f"http://127.0.0.1:{ui_port}",
            "--native-import-origin", f"http://localhost:{ui_port}",
            "--native-picker-executable", str(picker),
        ],
        [str(vite), "preview", "--host", "127.0.0.1", "--port", str(ui_port), "--strictPort"],
    ]
    processes = []
    try:
        for name, command in zip(("api", "ui"), commands):
            with (root / "logs" / f"{name}.log").open("ab") as log:
                child_env = dict(env, YIA_API_BASE=f"http://127.0.0.1:{api_port}")
                processes.append(
                    subprocess.Popen(
                        command, cwd=project / "frontend", env=child_env,
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                    )
                )
        for _ in range(200):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError(f"pilot failed to start; see {root / 'logs'}")
            try:
                with urlopen(f"http://127.0.0.1:{api_port}/api/v1/system", timeout=1) as api:
                    if json.load(api)["runtime"]["demo_data"] is not False:
                        raise RuntimeError("pilot refused: runtime is demo data")
                with urlopen(url, timeout=1) as ui:
                    if ui.status == 200:
                        break
            except (OSError, RuntimeError):
                time.sleep(0.1)
        else:
            raise RuntimeError("pilot did not become ready")
    except BaseException:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        raise
    receipt_path.write_text(
        json.dumps(
            {
                "pids": [p.pid for p in processes],
                "url": url,
                "api": f"http://127.0.0.1:{api_port}",
                "runtime_root": str(root),
            }
        )
    )
    return url


def stop(project: Path) -> None:
    receipt_path = pilot_root(project) / "launcher.json"
    if not receipt_path.exists():
        print("no pilot receipt")
        return
    receipt = json.loads(receipt_path.read_text())
    for pid in receipt["pids"]:
        command = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, check=False)
        if command.returncode == 0 and str(project) not in command.stdout:
            raise RuntimeError("a pilot process identity changed; nothing was stopped")
    for pid in receipt["pids"]:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    receipt_path.unlink()
    print("pilot stopped")


def restart_backend(project: Path) -> None:
    """Restart only the API process (used after code edits while exploring)."""
    receipt_path = pilot_root(project) / "launcher.json"
    receipt = json.loads(receipt_path.read_text())
    api_pid, ui_pid = receipt["pids"]
    sys.path.insert(0, str(project / "src"))
    from youtube_intel.native_picker_build import prepare_native_picker

    picker = prepare_native_picker(project)
    root = pilot_root(project)
    env = dict(os.environ)
    inherited = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join([str(project / "src"), *inherited])
    ui_port, api_port = receipt["url"].rstrip("/").rsplit(":", 1)[1], receipt["api"].rsplit(":", 1)[1]
    try:
        os.kill(api_pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    time.sleep(1.5)
    command = [
        str(project / ".venv/bin/python"), "-m", "youtube_intel", "--project-root", str(root), "serve-api",
        "--database", str(root / "state.sqlite3"), "--port", api_port,
        "--native-import-origin", f"http://127.0.0.1:{ui_port}",
        "--native-import-origin", f"http://localhost:{ui_port}",
        "--native-picker-executable", str(picker),
    ]
    with (root / "logs" / "api.log").open("ab") as log:
        process = subprocess.Popen(
            command, cwd=project / "frontend", env=env, stdout=log,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
    receipt["pids"] = [process.pid, ui_pid]
    receipt_path.write_text(json.dumps(receipt))
    for _ in range(200):
        try:
            with urlopen(f"http://127.0.0.1:{api_port}/api/v1/system", timeout=1) as api:
                if json.load(api)["runtime"]["demo_data"] is False:
                    print("api restarted")
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("api did not come back")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--ui-port", type=int, default=DEFAULT_UI_PORT)
    parser.add_argument("--api-port", type=int, default=DEFAULT_API_PORT)
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--restart-api", action="store_true")
    args = parser.parse_args()
    project = args.project_root.resolve()
    if args.stop:
        stop(project)
    elif args.restart_api:
        restart_backend(project)
    else:
        print(launch(project, ui_port=args.ui_port, api_port=args.api_port))