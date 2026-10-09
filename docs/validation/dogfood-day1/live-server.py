"""Isolated real-provider validation: normal composition, no owner credentials."""
import sys
from pathlib import Path

import youtube_intel.runtime_composition as composition
from youtube_intel.cli import main

root = Path(sys.argv[1]).resolve()
original = composition.build_local_source_run_runtime
class NoCredentials:
    def get(self): return None
    def save(self, value): raise AssertionError("validation never stores credentials")
    def delete(self): raise AssertionError("validation never deletes credentials")
def build(**kwargs):
    kwargs["credential_store"] = NoCredentials()
    return original(**kwargs)
composition.build_local_source_run_runtime = build
raise SystemExit(main(["--project-root", str(root), "serve-api", "--database", str(root / "state.sqlite3"), "--port", sys.argv[2] if len(sys.argv) > 2 else "18965"]))
