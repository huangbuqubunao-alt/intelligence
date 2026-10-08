"""Task-owned real runtime: actual providers/network, empty model credentials.

Only the explicit offline fault seam wraps feed acquisition; it never returns
fixture XML. The normal CLI/composition, signal and restore lifecycle run intact.
"""
import sys
from pathlib import Path

import youtube_intel.runtime_composition as composition
from youtube_intel.cli import main
from youtube_intel.following_provider import TrackingError

root = Path(sys.argv[1])
original = composition.build_local_source_run_runtime


class NoCredentials:
    def get(self):
        return None

    def set(self, value):
        raise AssertionError("task-owned runtime does not edit credentials")

    def delete(self):
        raise AssertionError("task-owned runtime does not edit credentials")


def build(**kwargs):
    kwargs["credential_store"] = NoCredentials()
    runtime = original(**kwargs)
    provider = runtime.application._source_tracking.providers["YOUTUBE"]
    real_feed = provider._fetch

    def feed(channel):
        if (root / "simulate-offline").exists():
            raise TrackingError("NETWORK_UNAVAILABLE")
        return real_feed(channel)

    provider._fetch = feed
    generation_path = root / "generation.txt"
    generation = int(generation_path.read_text()) + 1 if generation_path.exists() else 1
    generation_path.write_text(str(generation))
    print("runtime_generation", generation, flush=True)
    return runtime


composition.build_local_source_run_runtime = build
raise SystemExit(main([
    "--project-root", str(root), "serve-api", "--database", str(root / "state.sqlite"),
    "--port", "18865",
]))
