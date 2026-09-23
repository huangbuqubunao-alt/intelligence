from __future__ import annotations

import io
import json
from dataclasses import fields, replace

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    DistillationCommand,
    DistillationTransportKind,
    OllamaLocalDistillationTransport,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
)

_DIGEST = "sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"


def _input() -> VerifiedDistillationInput:
    return VerifiedDistillationInput(
        source_display_name="Public source",
        video_id="video-1",
        video_title="A public title",
        evidence=(
            VerifiedEvidenceInput(
                evidence_id="e1",
                start_ms=1000,
                end_ms=2000,
                excerpt="The product launched in April.",
                excerpt_hash="a" * 64,
                timed_transcript_id="transcript-1",
                timed_transcript_hash="b" * 64,
            ),
        ),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider="ollama",
        selected_model="qwen3:8b",
        semantic_hash="c" * 64,
        output_language="en",
    )


def _command() -> DistillationCommand:
    return DistillationCommand(
        execution_id="execution-1",
        source_id="source-1",
        video_id="video-1",
        evidence_ids=("e1",),
        reason="MANUAL_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="ollama",
        selected_model="qwen3:8b",
        output_language="en",
    )


def test_sealed_distillation_languages_are_required_and_finite() -> None:
    command = _command()
    verified = _input()

    with pytest.raises(TypeError):
        DistillationCommand(
            execution_id=command.execution_id,
            source_id=command.source_id,
            video_id=command.video_id,
            evidence_ids=command.evidence_ids,
            reason=command.reason,
            use_case=command.use_case,
            selected_provider=command.selected_provider,
            selected_model=command.selected_model,
        )
    with pytest.raises(TypeError):
        VerifiedDistillationInput(
            **{
                field.name: getattr(verified, field.name)
                for field in fields(verified)
                if field.name != "output_language"
            }
        )
    with pytest.raises(ValueError):
        replace(command, output_language="fr-FR")
    with pytest.raises(ValueError):
        replace(verified, output_language="fr-FR")


def test_local_distillation_is_exact_digest_loopback_and_structured(
    monkeypatch,
) -> None:
    settings = LocalScoringSettings(model="qwen3:8b", expected_model_digest=_DIGEST)
    transport = OllamaLocalDistillationTransport(settings=settings)
    requests = []

    class Response(io.BytesIO):
        pass

    def urlopen(request, timeout):
        requests.append(request)
        assert timeout == 300.0
        if request.full_url.endswith("/api/tags"):
            body = {
                "models": [
                    {"name": "qwen3:8b", "digest": _DIGEST.removeprefix("sha256:")}
                ]
            }
        else:
            outbound = json.loads(request.data)
            assert outbound["model"] == "qwen3:8b"
            assert outbound["stream"] is False
            schemas = outbound["format"]["anyOf"]
            assert len(schemas) == 2
            intelligence_schema, zero_schema = schemas
            assert "result" not in intelligence_schema["properties"]
            assert intelligence_schema["additionalProperties"] is False
            assert zero_schema["properties"]["result"]["enum"] == [
                "NO_NEW_INTELLIGENCE"
            ]
            assert "in en" in outbound["messages"][0]["content"]
            body = {
                "model": "qwen3:8b",
                "message": {"content": '{"result":"NO_NEW_INTELLIGENCE"}'},
                "done": True,
                "prompt_eval_count": 400,
                "eval_count": 50,
            }
        return Response(json.dumps(body).encode())

    monkeypatch.setattr("youtube_intel.distillation.urllib.request.urlopen", urlopen)
    assert transport.transport_kind is DistillationTransportKind.LOCAL_PRODUCTION
    assert transport.is_authorized_for_normal_production(_input())
    result = transport.generate(_input())
    assert result.actual_provider == "ollama"
    assert result.actual_model == "qwen3:8b"
    assert result.input_tokens == 400 and result.output_tokens == 50
    assert result.cost_microunits is None
    assert len(requests) == 2
    assert all(
        request.full_url.startswith("http://127.0.0.1:11434/") for request in requests
    )


def test_local_distillation_refuses_same_model_name_with_unexpected_digest() -> None:
    settings = LocalScoringSettings(
        model="qwen3:8b", expected_model_digest="sha256:" + "0" * 64
    )
    transport = OllamaLocalDistillationTransport(settings=settings)
    assert transport.is_authorized_for_normal_production(_input()) is False
    assert transport.available is False
