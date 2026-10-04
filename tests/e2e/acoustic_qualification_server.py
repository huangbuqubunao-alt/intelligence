"""Read the actual Phase 9 product database; production MLX capability, no fake ASR."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel import deep_analysis_activation
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.deep_analysis_service import DeepAnalysisService
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.runtime_composition import _deep_analysis_production_capability
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import SQLiteStateRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=5598)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[2] / ".var" / "phase9")
    assert (root / "state.sqlite3").exists()
    repo = SQLiteStateRepository(root / "state.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    jobs = LocalTranscriptionJobs(repo, root / "data")
    # Discovery must not contact another model/provider during this qualification.
    deep_analysis_activation._local_probe = lambda _: "UNREACHABLE"
    capability = _deep_analysis_production_capability()
    assert capability.execution_route() is None
    reader = AuthoritativeScoringReader(repository=repo, data_root=root / "data", summary_threshold=7, pipeline_version="phase9-browser", current_model="unavailable")
    deep_analysis = DeepAnalysisService(repository=repo, capability=capability, scoring_reader=reader.read, transcript_reader=repo.get_verified_timed_transcript, evidence_reader=repo.list_canonical_coverage_evidence_ids, evidence_text_reader=repo.resolve_verified_evidence_text)
    backup = BackupRestoreService(database=root / "state.sqlite3", data_root=root / "data")
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=root / "data", transcription_jobs=jobs, deep_analysis_service=deep_analysis, backup_restore_service=backup)
    server = serve_loopback(app, port=args.port)
    print(json.dumps({"port": server.server_port, "real_acoustic_authority": True}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
