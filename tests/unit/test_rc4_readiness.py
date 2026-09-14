from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.cli import _build_parser, _validate_arguments
from youtube_intel.distillation import (
    DistillationCapabilityScope,
    NormalV1ProductionAuthorizationAuthority,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.readiness import (
    BudgetReadiness,
    ProductionReadinessAuthority,
)
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 9, 14, 8, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 16
    return repository


def _eligibility(*, available: bool = True):
    return NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=available,
    )


def _source(repository: SQLiteStateRepository) -> str:
    return (
        ProductOrchestrationService(repository, now=lambda: NOW)
        .add_source(
            url="https://www.youtube.com/channel/UC1234567890123456789012",
            processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
        )
        .source_id
    )


def test_all_independent_prerequisites_are_required_for_ready(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    authority = ProductionReadinessAuthority(
        repository,
        runtime_enabled=True,
        eligibility=_eligibility(),
        credential_available=True,
        budget=BudgetReadiness.within_limit(limit=5, used=0),
    )

    projection = authority.project(source_id=source_id)

    assert projection["overall"]["code"] == "READY"
    assert projection["application"]["code"] == "CONNECTED"
    assert projection["video_distillation"]["code"] == "READY_TO_START"
    assert projection["model"]["code"] == "APPROVED"
    assert projection["credential"]["code"] == "AVAILABLE"
    assert projection["budget"]["code"] == "WITHIN_LIMIT"
    assert projection["source"]["code"] == "READY_FOR_MANUAL_CHECK"
    assert "credential_value" not in str(projection).lower()
    assert "api_key_value" not in str(projection).lower()


@pytest.mark.parametrize(
    (
        "runtime_enabled",
        "provider_available",
        "credential_available",
        "budget",
        "expected",
    ),
    [
        (
            False,
            True,
            True,
            BudgetReadiness.within_limit(limit=5, used=0),
            "SETUP_REQUIRED",
        ),
        (
            True,
            False,
            True,
            BudgetReadiness.within_limit(limit=5, used=0),
            "TEMPORARILY_UNAVAILABLE",
        ),
        (
            True,
            True,
            False,
            BudgetReadiness.within_limit(limit=5, used=0),
            "SETUP_REQUIRED",
        ),
        (
            True,
            True,
            True,
            BudgetReadiness.limit_reached(limit=5, used=5),
            "BUDGET_BLOCKED",
        ),
    ],
)
def test_readiness_never_collapses_missing_independent_gate_to_ready(
    tmp_path: Path,
    runtime_enabled: bool,
    provider_available: bool,
    credential_available: bool,
    budget: BudgetReadiness,
    expected: str,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    authority = ProductionReadinessAuthority(
        repository,
        runtime_enabled=runtime_enabled,
        eligibility=_eligibility(available=provider_available),
        credential_available=credential_available,
        budget=budget,
    )

    projection = authority.project(source_id=source_id)

    assert projection["overall"]["code"] == expected
    assert projection["overall"]["code"] != "READY"
    serialized = str(projection).lower()
    if not credential_available:
        assert "enter it in this browser" in serialized
        assert "will not store" in serialized
        assert projection["credential"]["recovery"]["action"] == (
            "VIEW_SETUP_INSTRUCTIONS"
        )
    if not provider_available:
        assert "will not switch provider or model" in serialized
        assert projection["model"]["code"] == "TEMPORARILY_UNAVAILABLE"
        assert projection["video_distillation"]["recovery"]["action"] == (
            "CHECK_READINESS"
        )
    if budget.code == "LIMIT_REACHED":
        assert "will not increase the limit" in serialized
        assert projection["budget"]["recovery"]["action"] == "VIEW_USAGE"


def test_unsupported_capability_and_source_configuration_are_not_ready(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = (
        ProductOrchestrationService(repository, now=lambda: NOW)
        .add_source(
            url="https://youtu.be/abcdefghijk",
            processing_policy=ProcessingPolicy.DISCOVER_ONLY,
        )
        .source_id
    )
    unsupported = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.DEEP_ANALYSIS,
        available=True,
    )
    authority = ProductionReadinessAuthority(
        repository,
        runtime_enabled=True,
        eligibility=unsupported,
        credential_available=True,
        budget=BudgetReadiness.within_limit(limit=5, used=0),
    )

    projection = authority.project(source_id=source_id)

    assert projection["overall"]["code"] == "SETUP_REQUIRED"
    assert projection["model"]["code"] == "NOT_APPROVED"
    assert projection["source"]["code"] == "FIX_CONFIGURATION"
    assert projection["source"]["recovery"]["action"] == ("EDIT_SOURCE_CONFIGURATION")
    assert projection["deep_analysis"]["code"] == "BLOCKED"


def test_unconfigured_api_runtime_fails_closed_without_guessing_secret_or_budget(
    tmp_path: Path,
) -> None:
    projection = ProductionReadinessAuthority.unconfigured(
        _repository(tmp_path)
    ).project()

    assert projection["overall"]["code"] == "SETUP_REQUIRED"
    assert projection["credential"]["code"] == "STATUS_UNAVAILABLE"
    assert projection["budget"]["code"] == "STATUS_UNAVAILABLE"
    assert "NVIDIA_API_KEY" not in str(projection)


def test_supported_serve_api_requires_explicit_enablement_and_bounded_budget() -> None:
    parser = _build_parser()
    safe_default = parser.parse_args(["serve-api", "--database", "state.sqlite3"])
    _validate_arguments(safe_default)
    assert safe_default.enable_video_distillation is False
    assert safe_default.video_distillation_call_limit == 0

    enabled = parser.parse_args(
        [
            "serve-api",
            "--database",
            "state.sqlite3",
            "--enable-video-distillation",
            "--video-distillation-call-limit",
            "5",
        ]
    )
    _validate_arguments(enabled)
    assert enabled.enable_video_distillation is True
    assert enabled.video_distillation_call_limit == 5

    invalid = parser.parse_args(
        [
            "serve-api",
            "--database",
            "state.sqlite3",
            "--video-distillation-call-limit",
            "6",
        ]
    )
    with pytest.raises(ValueError, match="between 0 and 5"):
        _validate_arguments(invalid)
