"""Research contract tests: synthetic wire responses, never model qualification."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import qualify_readiness_qwen35_intelligence as research
from youtube_intel.distillation import (
    DistillationCommand,
    OllamaLocalDistillationTransport,
    VerifiedDistillationInput,
    VerifiedEvidenceInput,
)


def verified() -> VerifiedDistillationInput:
    return VerifiedDistillationInput(
        source_display_name="Synthetic contract source",
        video_id="synthetic-video",
        video_title="Synthetic AI source",
        evidence=(
            VerifiedEvidenceInput(
                evidence_id="e1",
                start_ms=1000,
                end_ms=2000,
                excerpt="The speaker reports an unverified AI tooling change.",
                excerpt_hash="a" * 64,
                timed_transcript_id="t1",
                timed_transcript_hash="b" * 64,
            ),
        ),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider="ollama",
        selected_model=research.MODEL,
        semantic_hash="c" * 64,
        output_language="en",
    )


def command() -> DistillationCommand:
    return DistillationCommand(
        execution_id="synthetic-test",
        source_id="source",
        video_id="synthetic-video",
        evidence_ids=("e1",),
        reason="MANUAL_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="ollama",
        selected_model=research.MODEL,
        output_language="en",
    )


def positive() -> dict[str, object]:
    return {
        "result": "INTELLIGENCE",
        "core_conclusion": "The speaker's AI tooling report needs verification.",
        "user_relevant_information": ["An AI reliability comparison would be useful."],
        "important_new_information": [
            "The speaker reports an unverified tooling change."
        ],
        "meaningful_details": ["The report does not establish measured reliability."],
        "filtered_noise": [],
        "claim_kind": "SYSTEM_INFERENCE",
        "evidence": [
            {
                "evidence_id": "e1",
                "start_ms": 1000,
                "end_ms": 2000,
                "stance": "supporting",
            }
        ],
    }


def test_marker_decode_preserves_every_content_field(tmp_path: Path) -> None:
    transport = research.Qwen35ResearchTransport(root=tmp_path)
    payload = positive()
    decoded = research.decode_marker(
        json.dumps(payload), command(), verified(), transport
    )
    assert json.loads(decoded) == {k: v for k, v in payload.items() if k != "result"}
    zero = '{ "result":"NO_NEW_INTELLIGENCE", "evidence":[] }'
    assert research.decode_marker(zero, command(), verified(), transport) == zero
    assert (
        transport.actual_model
        == research.MODEL
        != OllamaLocalDistillationTransport._MODEL
    )
    assert not transport.is_authorized_for_normal_production(verified())


@pytest.mark.parametrize(
    "invalid",
    [
        "command_tag",
        "verified_tag",
        "command_provider",
        "verified_provider",
        "digest",
        "profile",
        "extra",
        "missing",
        "unknown_marker",
    ],
)
def test_invalid_identity_or_wire_cannot_be_decoded(
    tmp_path: Path, invalid: str
) -> None:
    transport = research.Qwen35ResearchTransport(root=tmp_path)
    cmd, value, payload = command(), verified(), positive()
    if invalid == "command_tag":
        cmd = replace(cmd, selected_model="qwen3:8b")
    if invalid == "verified_tag":
        value = replace(value, selected_model="qwen3:8b")
    if invalid == "command_provider":
        cmd = replace(cmd, selected_provider="cloud")
    if invalid == "verified_provider":
        value = replace(value, selected_provider="cloud")
    if invalid == "digest":
        transport._DIGEST = "sha256:" + "d" * 64
    if invalid == "profile":
        transport.profile_id = "another-profile"
    if invalid == "extra":
        payload["extra"] = "not permitted"
    if invalid == "missing":
        del payload["filtered_noise"]
    if invalid == "unknown_marker":
        payload["result"] = "SUCCESS"
    with pytest.raises(ValueError):
        research.decode_marker(json.dumps(payload), cmd, value, transport)


def test_no_generation_without_explicit_execution_permit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail("No network is permitted"),
    )
    with pytest.raises(RuntimeError, match="not authorized"):
        research.Qwen35ResearchTransport(root=tmp_path).generate(verified())
    assert not tuple(tmp_path.iterdir())


def test_truthful_wire_parameters_and_once_only_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def fake_request(
        self: object, path: str, *, method: str, body: dict[str, object] | None = None
    ) -> dict[str, object]:
        assert path == "/api/chat" and body is not None
        calls.append(body)
        return {
            "model": research.MODEL,
            "done": True,
            "message": {"content": json.dumps(positive())},
        }

    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", fake_request)
    transport = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    result = transport.generate(verified())
    assert json.loads(result.raw) == positive()
    assert calls[0]["model"] == research.MODEL
    assert calls[0]["options"] == research.OPTIONS
    assert calls[0]["think"] is False
    assert calls[0]["format"] == OllamaLocalDistillationTransport._SCHEMA
    messages = calls[0]["messages"]
    assert isinstance(messages, list) and len(messages) == 2
    assert [m["role"] for m in messages] == ["system", "user"]
    with pytest.raises(RuntimeError, match="once"):
        transport.generate(verified())
    assert len(calls) == 1


def test_profile_corpora_and_case_order_are_frozen() -> None:
    profile = research.load_profile()
    assert [item["case"] for item in profile["case_order"]] == [
        "real-deepthink-en",
        "real-deepthink-zh-cn",
        "no-new-fifteen",
        "source-injection",
    ]
    for entry in profile["case_order"]:
        assert research.load_case(entry["case"])["id"] == entry["case"]
    assert profile["production_qualified"] is False


def test_missing_review_or_installation_permit_rejects_before_io(
    tmp_path: Path,
) -> None:
    permit = tmp_path / "permit.json"
    permit.write_text(json.dumps({"status": "APPROVED_ISOLATED_GENERATION"}))
    with pytest.raises(ValueError):
        research.validate_execution_permit(permit, "real-deepthink-en")


@pytest.mark.parametrize(
    "wire",
    [
        "positive",
        "no_new",
        "incomplete",
        "wrong_time",
        "unknown_id",
        "unknown_claim",
        "transport_unknown",
    ],
)
def test_ordinary_ledger_parser_and_restart_without_reinvocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wire: str
) -> None:
    """Synthetic wire contract only; no assertion of semantic model qualification."""
    case = research.load_case("no-new-fifteen")
    repository, source, video = research.setup_case(case, tmp_path, datetime.now(UTC))
    raw_outputs: list[str] = []
    requests: list[Mapping[str, object]] = []

    def fake_request(
        self: object,
        path: str,
        *,
        method: str,
        body: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        if path == "/api/tags":
            return {"models": [{"name": research.MODEL, "digest": research.DIGEST}]}
        assert path == "/api/chat" and body is not None
        requests.append(body)
        if wire == "transport_unknown":
            raise OSError("synthetic interrupted response")
        messages = body["messages"]
        assert isinstance(messages, list)
        context = json.loads(messages[1]["content"])
        refs = [
            {k: e[k] for k in ("evidence_id", "start_ms", "end_ms")}
            for e in context["evidence"]
        ]
        assert len(refs) == 15
        payload = (
            positive()
            if wire in {"positive", "unknown_claim"}
            else {"result": "NO_NEW_INTELLIGENCE"}
        )
        payload["evidence"] = (
            [{**refs[0], "stance": "supporting"}]
            if wire in {"positive", "unknown_claim"}
            else refs
        )
        if wire == "incomplete":
            payload["evidence"] = refs[:-1]
        if wire == "wrong_time":
            refs[0]["start_ms"] += 1
        if wire == "unknown_id":
            refs[0]["evidence_id"] = "unknown-source"
        if wire == "unknown_claim":
            payload["claim_kind"] = "UNCLASSIFIED"
        raw = json.dumps(payload)
        raw_outputs.append(raw)
        return {
            "model": research.MODEL,
            "done": True,
            "message": {"content": raw},
            "prompt_eval_count": 111,
            "eval_count": 222,
        }

    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", fake_request)
    service, transport = research.make_service(repository, case, tmp_path, execute=True)
    ids = repository.list_canonical_coverage_evidence_ids(video_id=video)
    reservation = service.reserve_distillation_execution(
        source_id=source, video_id=video, evidence_ids=ids
    )
    outcome = service.continue_qualification_reserved_distillation(
        reservation.execution_id
    )
    expected = {
        "positive": "SUCCEEDED",
        "no_new": "SUCCEEDED_NO_NEW_INTELLIGENCE",
        "transport_unknown": "AMBIGUOUS",
    }.get(wire, "REJECTED_OUTPUT")
    assert outcome.status.value == expected and outcome.invocation_count == 1
    assert (
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        == outcome
    )
    restart, restarted_transport = research.make_service(
        repository, case, tmp_path, execute=True
    )
    assert (
        restart.continue_qualification_reserved_distillation(reservation.execution_id)
        == outcome
    )
    assert (
        restarted_transport.generations == 0
        and transport.generations == 1
        and len(requests) == 1
    )
    ledger = repository.get_distillation_resource_usage(reservation.execution_id)
    assert ledger is not None
    if wire != "transport_unknown":
        assert ledger.actual_model == research.MODEL
    assert ledger.selected_model == research.MODEL and ledger.invocation_count == 1
    assert ledger.cost_microunits is None
    assert len(repository.list_canonical_coverage_evidence_ids(video_id=video)) == 15
    if raw_outputs:
        retained = json.loads((tmp_path / "response.json").read_text())
        assert retained["message"]["content"] == raw_outputs[0]
    else:
        assert (tmp_path / "generation.started.json").is_file()
        assert not (tmp_path / "response.json").exists()


def test_ordinary_production_continuation_stays_waiting_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail(
            "Unqualified production must never contact provider"
        ),
    )
    case = research.load_case("no-new-fifteen")
    repository, source, video = research.setup_case(case, tmp_path, datetime.now(UTC))
    service, transport = research.make_service(repository, case, tmp_path, execute=True)
    reservation = service.reserve_distillation_execution(
        source_id=source,
        video_id=video,
        evidence_ids=repository.list_canonical_coverage_evidence_ids(video_id=video),
    )
    normal = service.continue_reserved_distillation(reservation.execution_id)
    assert normal.status.value == "WAITING_MODEL" and normal.invocation_count == 0
    assert (
        service.continue_qualification_reserved_distillation(reservation.execution_id)
        == normal
    )
    assert transport.generations == 0


def test_durable_dispatch_marker_prevents_new_transport_reroll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail("No replay network"),
    )
    research.write_once(tmp_path / "generation.started.json", {"interrupted": True})
    with pytest.raises(RuntimeError, match="once"):
        research.Qwen35ResearchTransport(
            root=tmp_path, execute_authorized=True
        ).generate(verified())


def test_available_is_readonly_closed_without_execution_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail("No preparation network"),
    )
    assert not research.Qwen35ResearchTransport(root=tmp_path).available


def test_stale_code_or_profile_freeze_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze = tmp_path / "freeze.json"
    freeze.write_text(
        json.dumps(
            {
                "profile": research.PROFILE_ID,
                "production_qualified": False,
                "files": {"scripts/qualify_readiness_qwen35_intelligence.py": "0" * 64},
            }
        )
    )
    monkeypatch.setattr(research, "FREEZE_PATH", freeze)
    with pytest.raises(ValueError, match="changed"):
        research.validate_freeze()


def test_preparation_has_zero_network_and_never_overwrites_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail("No preparation provider access"),
    )
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path)
    monkeypatch.setattr(research, "validate_freeze", lambda: {})
    freeze = tmp_path / "synthetic-freeze.json"
    freeze.write_text("{}")
    monkeypatch.setattr(research, "FREEZE_PATH", freeze)
    # The profile/input validation remains real; only the outer review freeze is stubbed.
    prepared = research.prepare_case("no-new-fifteen")
    assert (
        prepared["actual_model"] == research.MODEL and prepared["evidence_count"] == 15
    )
    assert prepared["production_qualified"] is False
    root = tmp_path / "no-new-fifteen"
    assert prepared["prepared_database_sha256"] == research.sha256(
        root / "state.sqlite3"
    )
    assert not (root / "generation.started.json").exists()
    verified_input = json.loads((root / "verified-input.json").read_text())
    assert verified_input["selected_model"] == research.MODEL
    assert prepared["verified_input_sha256"] == research.sha256(
        root / "verified-input.json"
    )
    with pytest.raises(FileExistsError):
        research.prepare_case("no-new-fifteen")


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "tag",
        "cloud",
        "production",
        "runtime",
        "blob",
        "start",
        "prepared",
        "space",
        "prior",
    ],
)
def test_exact_external_receipt_and_prior_semantic_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    freeze = tmp_path / "freeze.json"
    freeze.write_text(
        json.dumps(
            {
                "profile": research.PROFILE_ID,
                "production_qualified": False,
                "files": {
                    "scripts/qualify_readiness_qwen35_intelligence.py": research.sha256(
                        Path(research.__file__)
                    )
                },
            }
        )
    )
    monkeypatch.setattr(research, "FREEZE_PATH", freeze)
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    root = research.CASE_ROOT / "real-deepthink-en"
    root.mkdir(parents=True)
    (root / "prepared.json").write_text("{}")
    permit = {
        "status": "APPROVED_ISOLATED_GENERATION",
        "case": "real-deepthink-en",
        "pre_output_review": "APPROVE",
        "root_start_authorized": True,
        "installed_manifest_verified": True,
        "all_installed_blob_hashes_verified": True,
        "runtime_parameters_verified": True,
        "installed_runtime": "0.40.1",
        "actual_provider": "ollama",
        "actual_model": research.MODEL,
        "manifest_digest": research.DIGEST,
        "profile": research.PROFILE_ID,
        "production_qualified": False,
        "cloud_authorized": False,
        "harness_sha256": research.sha256(Path(research.__file__)),
        "profile_sha256": research.sha256(research.PROFILE_PATH),
        "freeze_sha256": research.sha256(freeze),
        "prepared_sha256": research.sha256(root / "prepared.json"),
        "post_install_free_bytes": 15 * 1024**3,
        "prior_semantic_reviews": [],
    }
    modifications = {
        "tag": ("actual_model", "qwen3:8b"),
        "cloud": ("cloud_authorized", True),
        "production": ("production_qualified", True),
        "runtime": ("installed_runtime", "latest"),
        "blob": ("all_installed_blob_hashes_verified", False),
        "start": ("root_start_authorized", False),
        "prepared": ("prepared_sha256", "0" * 64),
        "space": ("post_install_free_bytes", 1),
        "prior": (
            "prior_semantic_reviews",
            [{"case": "not-a-case", "verdict": "PASS"}],
        ),
    }
    if change in modifications:
        key, value = modifications[change]
        permit[key] = value
    path = tmp_path / "permit.json"
    path.write_text(json.dumps(permit))
    if change == "none":
        assert research.validate_execution_permit(path, "real-deepthink-en") == permit
    else:
        with pytest.raises(ValueError):
            research.validate_execution_permit(path, "real-deepthink-en")

@pytest.fixture
def thinking_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PROFILE_ID",
        "PROFILE_PATH",
        "FREEZE_PATH",
        "OPTIONS",
        "CASE_ROOT",
        "THINK",
    ):
        monkeypatch.setattr(
            research, name, getattr(research, name, None), raising=False
        )
    research.select_profile("readiness-qwen35-9b-official-thinking-v2")


def test_thinking_changes_only_three_native_values_preserving_v1_inputs(
    thinking_profile: None,
) -> None:
    profile = research.load_profile()
    old = research.read_object(research.DOCS / "QWEN35_RESEARCH_PROFILE_V1.json")
    assert research.PROFILE_ID == "readiness-qwen35-9b-official-thinking-v2"
    assert profile["case_order"] == old["case_order"]
    assert profile["policy"] == old["policy"]
    for key in (
        "actual_model",
        "expected_manifest_digest",
        "installed_runtime",
        "prompt_version",
        "schema_sha256",
        "legacy_applicability_conflict",
        "representation_adapter",
    ):
        assert profile[key] == old[key]
    changes = {
        key: value
        for key, value in profile["request_parameters"].items()
        if old["request_parameters"][key] != value
    }
    assert changes == {"think": True, "temperature": 1.0, "top_p": 0.95}
    assert profile["production_qualified"] is False
    assert research.CASE_ROOT.name == research.PROFILE_ID


def test_thinking_wire_uses_final_content_and_ignores_private_field(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FinalContentOnly(dict[str, object]):
        def get(self, key: str, default: object = None) -> object:
            if key == "thinking":
                raise AssertionError("Private thinking must never be inspected")
            return super().get(key, default)

    calls: list[Mapping[str, object]] = []

    def fake(
        self: object,
        path: str,
        *,
        method: str,
        body: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        assert path == "/api/chat" and body is not None
        calls.append(body)
        return {
            "model": research.MODEL,
            "done": True,
            "done_reason": "stop",
            "eval_count": 47,
            "message": FinalContentOnly(
                content=json.dumps(positive()), thinking="opaque fixture"
            ),
        }

    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", fake)
    transport = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    result = transport.generate(verified())
    assert json.loads(result.raw) == positive()
    assert calls[0]["think"] is True
    assert calls[0]["options"] == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "repeat_penalty": 1.0,
        "seed": 20261013,
        "num_ctx": 8192,
        "num_predict": 4096,
    }
    messages = calls[0]["messages"]
    assert isinstance(messages, list) and len(messages) == 2
    assert [message["role"] for message in messages] == ["system", "user"]
    assert not transport.is_authorized_for_normal_production(verified())
    with pytest.raises(RuntimeError, match="once"):
        transport.generate(verified())
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["budget", "length", "timeout"])
def test_thinking_failure_preserves_attempt_and_never_reinvokes(
    thinking_profile: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    from youtube_intel.distillation import KnownLocalDistillationResponseError

    calls = []

    def fake(
        self: object,
        path: str,
        *,
        method: str,
        body: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        calls.append(path)
        if failure == "timeout":
            raise TimeoutError("synthetic 300s outcome unknown")
        return {
            "model": research.MODEL,
            "done": True,
            "done_reason": "length" if failure == "length" else "stop",
            "eval_count": 4096,
            "message": {
                "content": json.dumps(positive()),
                "thinking": "opaque fixture",
            },
        }

    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", fake)
    transport = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    with pytest.raises(
        TimeoutError if failure == "timeout" else KnownLocalDistillationResponseError
    ):
        transport.generate(verified())
    assert (tmp_path / "generation.started.json").exists()
    if failure != "timeout":
        assert (tmp_path / "response.json").exists()
    restarted = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    with pytest.raises(RuntimeError, match="once"):
        restarted.generate(verified())
    assert len(calls) == 1


def test_thinking_cannot_prepare_later_case_without_prior_review(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    monkeypatch.setattr(research, "validate_freeze", lambda: {})
    with pytest.raises(ValueError, match="prior"):
        research.prepare_case("real-deepthink-zh-cn")
    assert not research.CASE_ROOT.exists()


@pytest.mark.parametrize(
    "profile",
    ["v3", "qwen3:8b", "cloud", "readiness-qwen35-9b-official-nonthinking-v1"],
)
def test_cli_cannot_reopen_old_or_unknown_experiment(
    profile: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research",
            "--profile",
            profile,
            "--case",
            "real-deepthink-en",
            "--prepare-only",
        ],
    )
    monkeypatch.setattr(
        research,
        "prepare_case",
        lambda *a, **k: pytest.fail("Unauthorized CLI preparation"),
    )
    with pytest.raises(SystemExit):
        research.main()


def test_transport_cannot_dispatch_after_profile_switch(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OllamaLocalDistillationTransport,
        "_request",
        lambda *a, **k: pytest.fail("No profile-substitution network"),
    )
    transport = research.Qwen35ResearchTransport(root=tmp_path, execute_authorized=True)
    research.select_profile(research.V1_PROFILE_ID)
    with pytest.raises(ValueError, match="profile changed"):
        transport.generate(verified())
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "tamper",
    [
        "none",
        "exclusive",
        "unknown",
        "static",
        "installation",
        "meaning",
        "profile",
        "freeze",
        "code",
        "prior",
    ],
)
def test_v2_external_start_receipt_strict_binding(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    monkeypatch.setattr(research, "validate_freeze", lambda: {})
    freeze = tmp_path / "freeze.json"
    freeze.write_text("{}")
    monkeypatch.setattr(research, "FREEZE_PATH", freeze)
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path / "cases")
    root = research.CASE_ROOT / "real-deepthink-en"
    root.mkdir(parents=True)
    (root / "prepared.json").write_text("{}")
    permit = {
        "status": "APPROVED_ISOLATED_GENERATION",
        "case": "real-deepthink-en",
        "pre_output_review": "APPROVE",
        "root_start_authorized": True,
        "installed_manifest_verified": True,
        "all_installed_blob_hashes_verified": True,
        "runtime_parameters_verified": True,
        "installed_runtime": "0.40.1",
        "actual_provider": "ollama",
        "actual_model": research.MODEL,
        "manifest_digest": research.DIGEST,
        "profile": research.PROFILE_ID,
        "production_qualified": False,
        "cloud_authorized": False,
        "harness_sha256": research.sha256(Path(research.__file__)),
        "profile_sha256": research.sha256(research.PROFILE_PATH),
        "freeze_sha256": research.sha256(freeze),
        "prepared_sha256": research.sha256(root / "prepared.json"),
        "post_install_free_bytes": 15 * 1024**3,
        "prior_semantic_reviews": [],
        "exclusive_heavyweight_execution_confirmed": True,
        "no_unresolved_prior_heavyweight_execution": True,
        "runtime_parameters_verified_meaning": research.read_object(
            research.DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json"
        )["runtime_parameters_verified_meaning"],
        "runtime_static_provenance_sha256": research.sha256(
            research.DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json"
        ),
        "installation_receipt_sha256": research.sha256(
            research.DOCS / "MODEL_REPLACEMENT_INSTALL_RECEIPT.json"
        ),
    }
    changes = {
        "exclusive": ("exclusive_heavyweight_execution_confirmed", False),
        "unknown": ("no_unresolved_prior_heavyweight_execution", False),
        "static": ("runtime_static_provenance_sha256", "0" * 64),
        "installation": ("installation_receipt_sha256", "0" * 64),
        "meaning": ("runtime_parameters_verified_meaning", "Empirical behavior proved"),
        "profile": ("profile", research.V1_PROFILE_ID),
        "freeze": ("freeze_sha256", "0" * 64),
        "code": ("harness_sha256", "0" * 64),
        "prior": ("prior_semantic_reviews", [False]),
    }
    if tamper in changes:
        key, value = changes[tamper]
        permit[key] = value
    path = tmp_path / "permit.json"
    path.write_text(json.dumps(permit))
    if tamper == "none":
        assert research.validate_execution_permit(path, "real-deepthink-en") == permit
    else:
        with pytest.raises(ValueError):
            research.validate_execution_permit(path, "real-deepthink-en")


@pytest.mark.parametrize(
    "tamper", ["none", "semantic", "profile", "count", "wrong-order", "malformed"]
)
def test_v2_later_case_requires_actual_prior_v2_review_result(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    monkeypatch.setattr(research, "CASE_ROOT", tmp_path)
    root = tmp_path / "real-deepthink-en"
    root.mkdir()
    result = {
        "case": "real-deepthink-en",
        "profile": research.PROFILE_ID,
        "actual_model": research.MODEL,
        "manifest_digest": research.DIGEST,
        "production_qualified": False,
        "generations": 1,
        "outcome": {"status": "SUCCEEDED", "invocation_count": 1},
    }
    if tamper == "profile":
        result["profile"] = research.V1_PROFILE_ID
    if tamper == "count":
        result["outcome"]["invocation_count"] = 0
    path = root / "result.json"
    path.write_text(json.dumps(result))
    review = {
        "case": "real-deepthink-en",
        "verdict": "FAIL" if tamper == "semantic" else "PASS",
        "result_sha256": research.sha256(path),
    }
    reviews = [review] if tamper != "malformed" else [False]
    if tamper == "wrong-order":
        review["case"] = "source-injection"
    if tamper == "none":
        research.validate_prior_semantic_reviews("real-deepthink-zh-cn", reviews)
    else:
        with pytest.raises(ValueError):
            research.validate_prior_semantic_reviews("real-deepthink-zh-cn", reviews)

@pytest.mark.parametrize("change", ["thinking-type", "seed", "policy", "corpus"])
def test_v2_profile_cannot_change_native_types_or_original_standards(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    profile = research.read_object(research.PROFILE_PATH)
    if change == "thinking-type":
        profile["request_parameters"]["think"] = 1
    elif change == "seed":
        profile["request_parameters"]["seed"] += 1
    elif change == "policy":
        profile["policy"]["all_positive_claims_independently_semantically_reviewed"] = False
    else:
        profile["case_order"][0]["sha256"] = "0" * 64
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    monkeypatch.setattr(research, "PROFILE_PATH", path)
    with pytest.raises(ValueError):
        research.load_profile()


def test_v2_partial_freeze_cannot_omit_core_or_legacy_policy(
    thinking_profile: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps({"profile": research.PROFILE_ID, "production_qualified": False,
        "files": {"scripts/qualify_readiness_qwen35_intelligence.py": research.sha256(Path(research.__file__))}}))
    monkeypatch.setattr(research, "FREEZE_PATH", path)
    with pytest.raises(ValueError, match="complete"):
        research.validate_freeze()


def test_retired_v1_cannot_execute_even_with_a_supplied_permit(tmp_path: Path) -> None:
    assert research.PROFILE_ID == research.V1_PROFILE_ID
    with pytest.raises(ValueError, match="retired"):
        research.execute_case("real-deepthink-en", tmp_path / "permit.json")
    assert not list(tmp_path.iterdir())
