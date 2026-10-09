"""Isolated real Local UI fixture; no cloud/model/network provider calls."""

import argparse
import json
import resource
import struct
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel import local_content
from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisService,
)
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.native_picker_build import prepare_native_picker
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import SQLiteStateRepository

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--port", type=int, default=5599)
parser.add_argument("--native", action="store_true")
args = parser.parse_args()
args.root.mkdir(parents=True, exist_ok=True)
repo = SQLiteStateRepository(args.root / "state.sqlite")
repo.initialize(now=datetime(2026, 10, 9, tzinfo=UTC))
seed = args.root / "small.mp4"
if not seed.exists():
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:r=5:d=1", str(seed)], check=True, timeout=20)
for size, name in [(65 * 1024 * 1024, "over64.mp4"), (2 * 1024 ** 3, "two-gib.mp4")]:
    path = args.root / name
    if not path.exists():
        with path.open("wb") as output:
            output.write(seed.read_bytes())
            output.write(struct.pack(">I4s", size - output.tell(), b"free"))
            output.truncate(size)
(args.root / "notes.md").write_text("Browser D2-01 focus and success navigation source.\n")

probe = local_content.probe_media
def delayed_probe(path, extension):
    time.sleep(1)
    return probe(path, extension)
local_content.probe_media = delayed_probe
transcription = LocalTranscriptionJobs(repo, args.root / "data")
reader = AuthoritativeScoringReader(repository=repo, data_root=args.root / "data", summary_threshold=7, pipeline_version="d2-02-browser", current_model="unavailable")
deep_analysis = DeepAnalysisService(repository=repo, capability=DeepAnalysisCapability(), scoring_reader=reader.read, transcript_reader=repo.get_verified_timed_transcript, evidence_reader=repo.list_canonical_coverage_evidence_ids, evidence_text_reader=repo.resolve_verified_evidence_text)
app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=args.root / "data", transcription_jobs=transcription, deep_analysis_service=deep_analysis)
if args.native:
    app.enable_native_import(("http://127.0.0.1:5598",), picker_executable=prepare_native_picker(Path.cwd()))
original = app._local_provider.import_stream
class SlowReceive:
    def __init__(self, source):
        self.source = source

    def read(self, maximum):
        return self.read1(maximum)

    def read1(self, maximum):
        time.sleep(0.001)
        return self.source.read1(maximum)

def streamed(name, source, length, **kwargs):
    # Fixed fixture delay gives the browser time to observe real byte progress;
    # validation still calls real ffprobe and publication/integrity is unchanged.
    result = original(name, SlowReceive(source), length, **kwargs)
    (args.root / "rss.json").write_text(json.dumps({"process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
    return result
app._local_provider.import_stream = streamed
server = serve_loopback(app, port=args.port)
print(f"ISOLATED_D2_02_UI_READY {server.server_port}", flush=True)
server.serve_forever()
