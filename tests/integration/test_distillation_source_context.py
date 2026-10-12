"""Persisted source attribution stays sealed without inventing speaker names."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from conftest import _load_module

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import OllamaLocalDistillationTransport
from youtube_intel.orchestration import SourceType
from youtube_intel.state import SQLiteStateRepository, StateStoreError

support = _load_module("test_task022_personalized_distillation")


def _workspace(tmp_path, *, display_name=None):
    repository = support._repository(tmp_path)
    channel_source_id, video_id = support._source_and_video(repository, "abcdefghijk")
    channel_source = repository.get_source_subscription(channel_source_id)
    assert channel_source is not None
    source = repository.create_source_subscription(replace(
        channel_source,
        source_id="video-source",
        source_type=SourceType.VIDEO_URL,
        canonical_url=f"https://www.youtube.com/watch?v={video_id}",
        channel_id=None,
        video_id=video_id,
        display_name=display_name,
    ))
    repository.link_source_video(source.source_id, video_id, discovered_at=support.NOW)
    support.SourcePolicyApplicationService(repository, now=lambda: support.NOW).evaluate_and_record_stage_one(
        source.source_id,
        support.MetadataFilterCandidate(
            video_id=video_id, title="AI Agent product update",
            description="Developer tools and product cases.",
            channel_name="Fixture channel", published_at=support.NOW,
            video_type=support.VideoType.STANDARD,
        ),
    )
    evidence_id = support._evidence(repository, video_id)
    transport = support._FakeTransport(support._no_new_raw(evidence_id))
    service = support._service(repository, transport)
    return repository, source, video_id, evidence_id, service, transport


def test_unnamed_video_source_uses_persisted_channel_and_survives_restart(tmp_path):
    repository, source, video_id, evidence_id, service, transport = _workspace(tmp_path)
    reservation = service.reserve_distillation_execution(
        source_id=source.source_id, video_id=video_id, evidence_ids=(evidence_id,),
    )
    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    command, verified = service._reserved_command_from_record(record)

    assert verified.source_display_name == "Fixture channel"
    assert repository.get_source_subscription(source.source_id) == source
    assert transport.calls == 0
    assert record.invocation_count == 0
    assert service._compose_verified_input(command) == verified

    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted_service = support._service(restarted, transport)
    assert restarted_service._reserved_command_from_record(record) == (command, verified)


def test_channel_fallback_reaches_only_the_ollama_source_data_role(tmp_path, monkeypatch):
    _repository, source, video_id, evidence_id, service, _transport = _workspace(tmp_path)
    command = replace(support._command(source.source_id, video_id, evidence_id),
        selected_provider="ollama", selected_model="qwen3:8b")
    verified = service._compose_verified_input(command)
    local = OllamaLocalDistillationTransport(settings=LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41",
    ))
    requests = []

    def request(path, *, method, body):
        requests.append(body)
        return {
            "model": "qwen3:8b",
            "message": {"content": support._no_new_raw(evidence_id)},
            "done": True,
        }

    monkeypatch.setattr(local, "_request", request)
    local.generate(verified)
    assert local.is_authorized_for_normal_production(verified) is False
    assert len(requests) == 1
    system, data = requests[0]["messages"]
    assert system["role"] == "system"
    assert "Fixture channel" not in system["content"]
    assert data["role"] == "user"
    context = json.loads(data["content"])
    assert context["source_display_name"] == "Fixture channel"
    assert context["evidence"][0]["excerpt"] == verified.evidence[0].excerpt


def test_explicit_source_display_name_takes_precedence(tmp_path):
    repository, source, video_id, evidence_id, service, _transport = _workspace(
        tmp_path, display_name="Named public source",
    )
    command = support._command(source.source_id, video_id, evidence_id)
    verified = service._compose_verified_input(command)
    assert verified.source_display_name == "Named public source"
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET channel_name = ? WHERE video_id = ?",
            ("Other persisted channel", video_id))
    assert service._compose_verified_input(command) == verified


def test_changed_channel_name_invalidates_the_previous_sealed_reservation(tmp_path):
    repository, source, video_id, evidence_id, service, transport = _workspace(tmp_path)
    reservation = service.reserve_distillation_execution(
        source_id=source.source_id, video_id=video_id, evidence_ids=(evidence_id,),
    )
    record = repository.get_distillation_execution(reservation.execution_id)
    assert record is not None
    command, before = service._reserved_command_from_record(record)
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET channel_name = ? WHERE video_id = ?",
            ("Changed persisted channel", video_id))
    after = service._compose_verified_input(command)
    assert after.source_display_name == "Changed persisted channel"
    assert after.semantic_hash != before.semantic_hash
    with pytest.raises(StateStoreError, match="not persistently reconstructible"):
        service._reserved_command_from_record(record)
    assert repository.get_distillation_execution(reservation.execution_id) == record
    assert transport.calls == 0


def test_absent_source_and_channel_names_remain_unknown(tmp_path):
    repository, source, video_id, evidence_id, service, _transport = _workspace(tmp_path)
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET channel_name = NULL WHERE video_id = ?", (video_id,))
    verified = service._compose_verified_input(support._command(source.source_id, video_id, evidence_id))
    assert verified.video_title == "AI Agent product update"
    assert verified.source_display_name is None
