"""Failure injection and recovery acceptance for the offline MVP composition."""

from __future__ import annotations

import gc
import importlib.util
import sqlite3
import sys
from collections import Counter
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


def _knowledge_videos(flow: object) -> list[str]:
    return sorted(
        path.name
        for path in (flow.vault_root / "Knowledge" / "Videos").glob("*.md")  # type: ignore[attr-defined]
    )


def _statuses(flow: object) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            scenario.video_id,
            str(flow.repository.get_video(scenario.video_id).pipeline_status),  # type: ignore[attr-defined]
        )
        for scenario in _FLOW.SCENARIOS
    )


def _planned_stages(flow: object) -> Counter[tuple[str, str]]:
    with sqlite3.connect(flow.data_root / "state.sqlite") as connection:  # type: ignore[attr-defined]
        return Counter(
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                "SELECT video_id, target_stage FROM jobs"
            )
        )


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

    statuses = _statuses(recovered)
    completed = tuple(
        video_id
        for video_id, status in statuses
        if status.endswith("COMPLETE")
    )
    # Managed audio transcription carries no cue-level transcript authority, so
    # the backend-authoritative Summary stage fails closed for it. Every
    # subtitle scenario below has real timed cues and is unaffected.
    assert (
        "whisper-high",
        str(_FLOW.PipelineStatus.SCORED),
    ) in statuses
    weekly_notes = len(
        list((recovered.vault_root / "Knowledge" / "Weekly").glob("*.md"))
    )

    if failure == "analysis":
        # The injected ANALYSIS failure is the only additional SCORED video.
        assert statuses.count(("whisper-high", str(_FLOW.PipelineStatus.SCORED))) == 1
        assert len(completed) == 3
        assert statuses.count(("high-value", str(_FLOW.PipelineStatus.SCORED))) == 1
        assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 0, 0)
        assert recovered.credentials.calls == 0
        assert len(_knowledge_videos(recovered)) == 2
        assert weekly_notes == 1
        return

    assert all(
        recovered.repository.get_video(scenario.video_id).pipeline_status
        is _FLOW.expected_final_status(scenario.video_id)
        for scenario in _FLOW.SCENARIOS
    )
    assert len(completed) == 4
    counts = recovered.counts()
    calls = (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls)
    knowledge = _knowledge_videos(recovered)
    planned_before = _planned_stages(recovered)
    recovered.run(now=_FLOW.NOW + timedelta(minutes=3))
    recovered.weekly_service().generate(now=_FLOW.NOW + timedelta(minutes=3))

    after = recovered.counts()
    # No duplicate output of any kind: no new provider call, artifact, or
    # report, and exactly the same set of knowledge notes.
    assert after[:3] == counts[:3]
    # Any newly planned job is another bounded ANALYSIS attempt for the
    # canonical-only video, which has no Summary authority. No other stage of
    # any other video is re-planned, so no duplicate work or output occurs.
    planned_after = _planned_stages(recovered)
    assert Counter(planned_after - planned_before) in (
        Counter(),
        Counter({("whisper-high", "ANALYSIS"): 1}),
    )
    assert not planned_before - planned_after
    assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == calls
    assert _knowledge_videos(recovered) == knowledge
    assert len(knowledge) == 3
    assert weekly_notes == 1
    if failure == "scoring":
        assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 1, 1)
        assert recovered.credentials.calls == 1
        assert all(
            (adapter.enumerate_calls, adapter.read_calls) == (0, 0)
            for adapter in recovered.subtitle_adapters.values()
        )
