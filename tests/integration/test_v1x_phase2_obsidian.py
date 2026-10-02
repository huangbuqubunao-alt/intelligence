"""Explicit one-way publication through real SQLite and disposable vaults."""

import html
import json
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.deep_analysis_obsidian import (
    DeepAnalysisObsidianPublisher,
    DeepAnalysisPublishError,
)

authority = _load_module("test_v1x_phase1b_authority")


def setup(tmp_path: Path):
    repository = authority.seed(tmp_path)
    vault = tmp_path / "external-vault"
    (vault / "Knowledge").mkdir(parents=True)
    publisher = DeepAnalysisObsidianPublisher(
        repository, vault_root=vault, vault_subdir="Knowledge"
    )
    return repository, vault, publisher


def test_trusted_publish_is_explicit_and_preserves_claim_evidence(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    captured = {}
    view = authority.service(repository, capture=captured).run(content_id=authority.VIDEO)
    assert list(vault.rglob("*.md")) == []
    with repository._connect() as connection:
        before = "\n".join(connection.iterdump())
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert published["state"] == "PUBLISHED"
    path = vault / "Knowledge" / published["relative_path"]
    text = path.read_text()
    assert 'type: "deep-analysis"' in text
    assert 'output_language: "en"' in text
    assert view.result_identity in text
    assert "[[" not in text
    assert all(candidate not in text for candidate in captured["candidates"])
    for claim in view.roles:
        line = next(line for line in text.splitlines() if claim.text in html.unescape(line))
        assert all(ref in line for ref in claim.evidence_ids)
    for heading in ["Core conclusion", "Key evidence", "Uncertainty", "Relevance to you", "Next question"]:
        assert f"## {heading}" in text
    with repository._connect() as connection:
        assert "\n".join(connection.iterdump()) == before
    repeated = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert repeated["relative_path"] == published["relative_path"]
    assert len(list(vault.rglob("*.md"))) == 1


def test_phase1a_is_not_publishable(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    view = authority.activation._service(repository).run(content_id=authority.VIDEO)
    assert publisher.status(content_id=authority.VIDEO)["state"] == "RESULT_INELIGIBLE"
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert rejected.value.code == "RESULT_INELIGIBLE"
    assert not list(vault.rglob("*.md"))


def test_missing_vault_fails_without_writes(tmp_path: Path) -> None:
    repository = authority.seed(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    publisher = DeepAnalysisObsidianPublisher(repository, vault_root=None)
    assert publisher.status(content_id=authority.VIDEO)["state"] == "NO_VAULT"
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert rejected.value.code == "NO_VAULT"
    assert not list(tmp_path.rglob("*.md"))


def test_local_api_publish_is_separate_explicit_action_without_qualified_model(tmp_path: Path) -> None:
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repository, vault, _ = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    app = LocalApiApplication(repository, ProductOrchestrationService(repository), vault_root=vault / "Knowledge")
    path = f"/api/v1/videos/{authority.VIDEO}/deep-analysis/obsidian"
    status, body = app.handle("GET", path)
    assert status == 200
    assert body["publish"]["state"] == "AVAILABLE"
    assert not list(vault.rglob("*.md"))
    status, body = app.handle("POST", path, json.dumps({"result_identity": view.result_identity}).encode())
    assert status == 200
    assert body["publish"]["state"] == "PUBLISHED"
    assert len(list(vault.rglob("*.md"))) == 1
