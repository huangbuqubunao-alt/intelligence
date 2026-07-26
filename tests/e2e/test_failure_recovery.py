"""Failure injection and recovery acceptance for the offline MVP composition."""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest


def _load_flow_module():  # type: ignore[no-untyped-def]
    path = Path(__file__).with_name("test_mvp_flow.py")
    specification = importlib.util.spec_from_file_location("_mvp_flow_support", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


_FLOW = _load_flow_module()


@pytest.mark.parametrize("failure", ("subtitle", "transcription", "scoring", "analysis", "note", "weekly"))
def test_service_boundary_failures_recover_without_duplicate_outputs(
    tmp_path: Path, failure: str
) -> None:
    flow = _FLOW._OfflineMvpFlow(tmp_path, failure=None if failure == "weekly" else failure)

    flow.run()
    if failure == "weekly":
        weekly = flow.weekly_service(fail_once=True)
        with pytest.raises(Exception, match="weekly report could not be committed"):
            weekly.generate(now=_FLOW.NOW)
        weekly.generate(now=_FLOW.NOW + timedelta(minutes=1))
    flow.run(now=_FLOW.NOW + timedelta(minutes=1))
    if failure != "weekly":
        flow.weekly_service().generate(now=_FLOW.NOW + timedelta(minutes=1))

    assert all(
        flow.repository.get_video(scenario.video_id).pipeline_status is _FLOW.PipelineStatus.COMPLETE
        for scenario in _FLOW.SCENARIOS
    )
    counts = flow.counts()
    calls = (flow.whisper.calls, flow.scoring.calls, flow.analysis.calls)
    flow.run(now=_FLOW.NOW + timedelta(minutes=2))
    flow.weekly_service().generate(now=_FLOW.NOW + timedelta(minutes=2))

    assert flow.counts() == counts
    assert (flow.whisper.calls, flow.scoring.calls, flow.analysis.calls) == calls
    assert len(list((flow.vault_root / "Knowledge" / "Videos").glob("*.md"))) == 4
    assert len(list((flow.vault_root / "Knowledge" / "Weekly").glob("*.md"))) == 1
