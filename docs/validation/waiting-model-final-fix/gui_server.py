"""Real isolated runtime with no credential access or qualification override."""

import os
import signal
import threading
from pathlib import Path

import yaml

from youtube_intel.config import load_app_config
from youtube_intel.local_api import serve_loopback
from youtube_intel.native_picker_build import prepare_native_picker
from youtube_intel.runtime_composition import build_local_source_run_runtime

PROJECT = Path(__file__).resolve().parents[3]
FINAL = os.environ.get("WAITING_MODEL_FINAL_GUI") == "1"
ROOT = PROJECT / (".var/waiting-model-final-fix/gui-final" if FINAL else ".var/waiting-model-final-fix/gui")


class NoCredentials:
    def get(self) -> None:
        return None

    def save(self, secret: str) -> None:
        raise RuntimeError("GUI acceptance does not permit credentials")

    def delete(self) -> None:
        raise RuntimeError("GUI acceptance does not permit credentials")


if __name__ == "__main__":
    os.environ.pop("MOONSHOT_API_KEY", None)
    for name in ("config", "data", "vault", "logs"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    settings = ROOT / "config/settings.yaml"
    if not settings.exists():
        config = yaml.safe_load((PROJECT / "config/settings.example.yaml").read_text())
        config["storage"]["vault_root"] = str(ROOT / "vault")
        settings.write_text(yaml.safe_dump(config))
    channels = ROOT / "config/channels.yaml"
    if not channels.exists():
        channels.write_text("channels:\n  - channel_id: UC_x5XG1OV2P6uZZ5FSM9Ttw\n    enabled: false\n    priority: 1\n")
    picker = prepare_native_picker(PROJECT)
    stopped = threading.Event()
    while not stopped.is_set():
        runtime = build_local_source_run_runtime(
            config=load_app_config(channels, settings), project_root=ROOT,
            database=ROOT / "state.sqlite3", credential_store=NoCredentials(),
        )
        runtime.application.enable_native_import(
            (("http://127.0.0.1:5798", "http://localhost:5798") if FINAL else
             ("http://127.0.0.1:5788", "http://localhost:5788")), picker_executable=picker,
        )
        server = serve_loopback(runtime.application, port=5799 if FINAL else 5789)

        def stop(signum, frame):
            stopped.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        runtime.worker.start()
        try:
            print("isolated API ready", flush=True)
            server.serve_forever()
        finally:
            server.server_close()
            runtime.application.shutdown_native_import()
            runtime.worker.stop()
        if not runtime.backup_restore.restart_requested:
            break
