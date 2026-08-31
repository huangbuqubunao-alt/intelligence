"""Failure injection and recovery acceptance for the offline MVP composition."""

from __future__ import annotations

import gc
import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from youtube_intel import analysis as analysis_mod


def _load_flow_module():  # type: ignore[no-untyped-def]
    path = Path(__file__).with_name("test_mvp_flow.py")
    specification = importlib.util.spec_from_file_location("_mvp_flow_support", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


_FLOW = _load_flow_module()


@pytest.fixture(autouse=True)
def _recovery_token_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recovery assertions are independent from explicit BPE provisioning."""

    monkeypatch.setattr(analysis_mod, "_input_tokens", lambda _parts, _root: 2)


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
        del weekly
    del flow
    gc.collect()

    recovered = _FLOW._OfflineMvpFlow(tmp_path, restore=True)
    assert recovered.transcripts == {}
    assert recovered.scores == {}
    assert recovered.analyses == {}
    assert recovered.note_sinks == {}
    assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 0, 0)
    assert recovered.credentials.calls == 0
    recovered.run(now=_FLOW.NOW + timedelta(minutes=1))
    recovered.run(now=_FLOW.NOW + timedelta(minutes=2))
    recovered.weekly_service().generate(now=_FLOW.NOW + timedelta(minutes=2))

    if failure == "analysis":
        statuses = tuple(
            recovered.repository.get_video(scenario.video_id).pipeline_status
            for scenario in _FLOW.SCENARIOS
        )
        assert statuses.count(_FLOW.PipelineStatus.COMPLETE) == 4
        assert statuses.count(_FLOW.PipelineStatus.SCORED) == 1
        assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 0, 0)
        assert recovered.credentials.calls == 0
        assert len(list((recovered.vault_root / "Knowledge" / "Videos").glob("*.md"))) == 3
        assert len(list((recovered.vault_root / "Knowledge" / "Weekly").glob("*.md"))) == 1
        return

    assert all(
        recovered.repository.get_video(scenario.video_id).pipeline_status is _FLOW.PipelineStatus.COMPLETE
        for scenario in _FLOW.SCENARIOS
    )
    counts = recovered.counts()
    calls = (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls)
    recovered.run(now=_FLOW.NOW + timedelta(minutes=3))
    recovered.weekly_service().generate(now=_FLOW.NOW + timedelta(minutes=3))

    assert recovered.counts() == counts
    assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == calls
    assert len(list((recovered.vault_root / "Knowledge" / "Videos").glob("*.md"))) == 4
    assert len(list((recovered.vault_root / "Knowledge" / "Weekly").glob("*.md"))) == 1
    if failure == "scoring":
        assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 1, 1)
        assert recovered.credentials.calls == 1
        assert all(
            (adapter.enumerate_calls, adapter.read_calls) == (0, 0)
            for adapter in recovered.subtitle_adapters.values()
        )
