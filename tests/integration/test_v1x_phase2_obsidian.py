"""Explicit one-way publication through real SQLite and disposable vaults."""

import errno
import html
import json
import os
import zipfile
from datetime import timedelta
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


@pytest.mark.parametrize("attack", ["candidate", "missing_membership", "cross_content", "schema", "policy"])
def test_corrupt_authority_cannot_publish(tmp_path: Path, attack: str) -> None:
    repository, vault, publisher = setup(tmp_path)
    captured = {}
    view = authority.service(repository, capture=captured).run(content_id=authority.VIDEO)
    foreign = authority.service(repository).run(content_id=authority.seed_other(tmp_path, repository))
    with repository._connect() as connection:
        if attack == "candidate":
            authority.reseal(connection, view.result_identity, lambda p: p["claims"][0].update(evidence_refs=[captured["candidates"][0]]))
        elif attack == "missing_membership":
            connection.execute("DELETE FROM deep_analysis_evidence WHERE result_identity=?", (view.result_identity,))
        elif attack == "cross_content":
            connection.execute("INSERT INTO deep_analysis_evidence VALUES (?, ?, ?)", (view.result_identity, foreign.roles[0].evidence_ids[0], authority.NOW.isoformat()))
            authority.reseal(connection, view.result_identity, lambda p: p["claims"][0].update(evidence_refs=[foreign.roles[0].evidence_ids[0]]))
        else:
            column = "persistence_version" if attack == "schema" else "validation_policy_identity"
            value = "unsupported" if attack == "schema" else "a" * 64
            connection.execute(f"UPDATE deep_analysis_persisted_results SET {column}=? WHERE result_identity=?", (value, view.result_identity))
    assert publisher.status(content_id=authority.VIDEO)["state"] == "RESULT_INELIGIBLE"
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert rejected.value.code == "RESULT_INELIGIBLE"
    assert not list(vault.rglob("*.md"))


def rerun(repository, *, chinese=False):
    # A changed Content title changes request provenance, but never the stable
    # semantic Content identity. Generate another genuinely verified execution.
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET title='A revised Content title' WHERE video_id=?", (authority.VIDEO,))
    if chinese:
        repository.save_global_output_language(output_language="zh-CN", now=authority.NOW)
    def mutate(raw, refs):
        del refs
        for role in ("core_conclusion", "key_evidence", "uncertainty", "relevance_to_user", "next_question"):
            for index, claim in enumerate(raw[role]):
                claim["text"] = f"这段内容支持目前的分析结论，但还需要核验。{index}" if chinese else claim["text"] + " The new analysis adds a detail."
    instance = authority.service(repository, mutate=mutate)
    instance._clock = lambda: authority.NOW + timedelta(hours=1)
    return instance.run(content_id=authority.VIDEO)


def test_rerun_new_result_updates_same_note_and_keeps_user_region(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    first = authority.service(repository).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=first.result_identity)
    path = vault / "Knowledge" / published["relative_path"]
    path.write_text(path.read_text().replace("## My thoughts\n\n", "## My thoughts\n\nUser-owned reflections.\n"))
    newer = rerun(repository)
    assert newer.result_identity != first.result_identity
    assert newer.content_identity != first.content_identity
    update = publisher.publish(content_id=authority.VIDEO, result_identity=newer.result_identity)
    assert update["state"] == "UPDATED"
    assert update["relative_path"] == published["relative_path"]
    assert len(list(vault.rglob("*.md"))) == 1
    text = path.read_text()
    assert newer.result_identity in text and first.result_identity not in text
    assert "User-owned reflections." in text
    assert "The new analysis adds a detail." in text
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=first.result_identity)
    assert rejected.value.code == "RESULT_CHANGED"
    assert path.read_text() == text


def test_language_variants_are_distinct_and_evidence_remains_original(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    english = authority.service(repository).run(content_id=authority.VIDEO)
    en = publisher.publish(content_id=authority.VIDEO, result_identity=english.result_identity)
    en_path = vault / "Knowledge" / en["relative_path"]
    previous = en_path.read_bytes()
    chinese = rerun(repository, chinese=True)
    zh = publisher.publish(content_id=authority.VIDEO, result_identity=chinese.result_identity)
    assert en["relative_path"] != zh["relative_path"]
    assert len(list(vault.rglob("*.md"))) == 2
    assert en_path.read_bytes() == previous
    text = (vault / "Knowledge" / zh["relative_path"]).read_text()
    assert 'output_language: "zh-CN"' in text
    assert "## 核心结论" in text and "## 下一步追问" in text
    original = repository.resolve_verified_evidence_text(chinese.roles[0].evidence_ids[0])
    # The existing inline-note convention collapses source whitespace only;
    # the excerpt still comes exclusively from verified original authority.
    assert " ".join(original.excerpt.split()) in html.unescape(text)
    assert "[[" not in text


def test_schema_identity_separates_semantics_and_unsupported_schema_fails_closed(tmp_path: Path) -> None:
    from youtube_intel.deep_analysis_note import deep_analysis_note_identity
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    path = vault / "Knowledge" / published["relative_path"]
    before = path.read_bytes()
    args = {"content_identity": authority.VIDEO, "output_language": "en"}
    assert deep_analysis_note_identity(**args, knowledge_content_schema_identity="schema-a") != deep_analysis_note_identity(**args, knowledge_content_schema_identity="schema-b")
    with repository._connect() as connection:
        request = json.loads(connection.execute("SELECT request_projection_json FROM deep_analysis_persisted_results").fetchone()[0])
        request["knowledge_content_schema_identity"] = "future-schema"
        connection.execute("UPDATE deep_analysis_persisted_results SET request_projection_json=?", (json.dumps(request),))
    with pytest.raises(DeepAnalysisPublishError):
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert path.read_bytes() == before


@pytest.mark.parametrize("title", ["../../escape", "/tmp/escape", "C:\\Windows\\escape", "CON", "../[[Topic]]<img>" + "语言" * 200, "\x00\n"])
def test_titles_cannot_escape_vault(tmp_path: Path, title: str) -> None:
    repository, vault, publisher = setup(tmp_path)
    with repository._connect() as connection:
        connection.execute("UPDATE videos SET title=? WHERE video_id=?", (title, authority.VIDEO))
    view = authority.service(repository).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    path = vault / "Knowledge" / published["relative_path"]
    assert path.resolve().is_relative_to(vault.resolve())
    assert path.parent.name == "Deep Analysis"
    assert len(path.name.encode()) < 255
    assert "\\" not in path.name and "[[" not in path.read_text()
    assert list(tmp_path.rglob("*.md")) == [path]


@pytest.mark.parametrize("collision", ["user_file", "wrong_kind", "wrong_identity", "missing_markers", "indented_marker", "multiple", "unsafe_filename"])
def test_unrelated_files_and_conflicting_ownership_are_preserved(tmp_path: Path, collision: str) -> None:
    from youtube_intel.deep_analysis_note import render_deep_analysis_note
    from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    read = DeepAnalysisPersistenceStore(repository).read_deep_analysis_result_for_content(video_id=authority.VIDEO)
    rendered = render_deep_analysis_note(read, title=repository.get_video(authority.VIDEO).title)
    path = vault / "Knowledge" / rendered.relative_path
    path.parent.mkdir()
    content = rendered.content
    if collision == "user_file":
        content = "# My unrelated note\nPersonal writing.\n"
    elif collision == "wrong_kind":
        content = content.replace('type: "deep-analysis"', 'type: "video"')
    elif collision == "wrong_identity":
        content = content.replace('producer: "youtube-intel"', 'producer: "someone-else"')
    elif collision == "missing_markers":
        content = content.replace("<!-- youtube-intel:user:start:v1 -->", "")
    elif collision == "indented_marker":
        content = content.replace("<!-- youtube-intel:user:start:v1 -->", "  <!-- youtube-intel:user:start:v1 -->")
    elif collision == "unsafe_filename":
        path = path.parent / ("bad\\name--" + path.name.rsplit("--", 1)[1])
        content = content.replace("## Core conclusion", "## Old generated heading")
    else:
        (path.parent / ("duplicate--" + path.name.rsplit("--", 1)[1])).write_text(content)
    path.write_text(content)
    before = {f: f.read_bytes() for f in path.parent.iterdir()}
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert rejected.value.code == "WRITE_FAILED"
    assert {f: f.read_bytes() for f in path.parent.iterdir()} == before


@pytest.mark.parametrize("component", ["root", "subdir", "kind", "note"])
def test_symlink_escape_is_rejected(tmp_path: Path, component: str) -> None:
    from youtube_intel.deep_analysis_note import render_deep_analysis_note
    from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.md"
    sentinel.write_text("untouched")
    if component == "root":
        root_link = tmp_path / "vault-link"
        root_link.symlink_to(vault, target_is_directory=True)
        publisher = DeepAnalysisObsidianPublisher(repository, vault_root=root_link, vault_subdir="Knowledge")
    elif component == "subdir":
        (vault / "Knowledge").rmdir()
        (vault / "Knowledge").symlink_to(outside, target_is_directory=True)
    elif component == "kind":
        (vault / "Knowledge" / "Deep Analysis").symlink_to(outside, target_is_directory=True)
    else:
        read = DeepAnalysisPersistenceStore(repository).read_deep_analysis_result_for_content(video_id=authority.VIDEO)
        relative = render_deep_analysis_note(read, title=repository.get_video(authority.VIDEO).title).relative_path
        path = vault / "Knowledge" / relative
        path.parent.mkdir()
        path.symlink_to(sentinel)
    with pytest.raises(DeepAnalysisPublishError):
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert sentinel.read_text() == "untouched"
    assert list(outside.iterdir()) == [sentinel]


@pytest.mark.parametrize("failure", ["partial_write", "file_fsync", "replace", "directory_fsync"])
def test_atomic_update_failure_keeps_previous_note(tmp_path: Path, monkeypatch, failure: str) -> None:
    import youtube_intel.providers.obsidian as sink
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    path = vault / "Knowledge" / published["relative_path"]
    before = path.read_bytes()
    new = rerun(repository)
    if failure == "partial_write":
        def fail(fd, content):
            os.write(fd, content[:20])
            raise OSError(errno.ENOSPC, "injected partial write")
        monkeypatch.setattr(sink, "_write_all", fail)
    elif failure == "replace":
        monkeypatch.setattr(sink.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError(errno.EIO, "injected replace")))
    else:
        original = os.fsync
        failed = False
        def fail(fd):
            nonlocal failed
            import stat
            is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
            if not failed and is_dir == (failure == "directory_fsync"):
                failed = True
                raise OSError(errno.EIO, "injected fsync")
            original(fd)
        monkeypatch.setattr(sink.os, "fsync", fail)
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=new.result_identity)
    assert rejected.value.code == "WRITE_FAILED"
    assert path.read_bytes() == before
    assert sorted(path.parent.iterdir()) == [path]


def test_read_only_vault_safe_failure(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    (vault / "Knowledge").chmod(0o500)
    try:
        with pytest.raises(DeepAnalysisPublishError) as rejected:
            publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
        assert rejected.value.code == "WRITE_FAILED"
        assert not list(vault.rglob("*.md"))
    finally:
        (vault / "Knowledge").chmod(0o700)


def test_restart_and_backup_restore_exclude_external_vault(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    repository, vault, publisher = setup(tmp_path)
    view = authority.service(repository).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    path = vault / "Knowledge" / published["relative_path"]
    previous = path.read_bytes()
    path.write_text(path.read_text().replace(view.roles[0].text, "Edited projection is not authority."))
    restored_publisher = DeepAnalysisObsidianPublisher(SQLiteStateRepository(tmp_path / "state.sqlite3"), vault_root=vault, vault_subdir="Knowledge")
    republished = restored_publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert republished["state"] == "UPDATED"
    assert republished["relative_path"] == published["relative_path"]
    assert path.read_bytes() == previous

    service = BackupRestoreService(database=tmp_path / "state.sqlite3", data_root=tmp_path / "data")
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    with zipfile.ZipFile(archive) as contents:
        assert not any("vault" in name.lower() or "Deep Analysis" in name for name in contents.namelist())
        assert not any(contents.read(name) == previous for name in contents.namelist())
    # The owner may remove external projection files; core restore remains valid.
    path.unlink()
    preview = service.stage_restore(archive.read_bytes())
    service.confirm_restore(preview.restore_id)
    service.recover_and_apply_pending_restore()
    assert not path.exists()
    publisher = DeepAnalysisObsidianPublisher(SQLiteStateRepository(tmp_path / "state.sqlite3"), vault_root=vault, vault_subdir="Knowledge")
    assert publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)["relative_path"] == published["relative_path"]
    assert path.read_bytes() == previous


def test_model_authored_wikilinks_are_neutralized_without_changing_claim_text(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    def inject(raw, refs):
        del refs
        raw["core_conclusion"][0]["text"] = "The source's [[Topic]] <script>alert(1)</script> result remains uncertain."
    view = authority.service(repository, mutate=inject).run(content_id=authority.VIDEO)
    published = publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    text = (vault / "Knowledge" / published["relative_path"]).read_text()
    assert "[[" not in text and "<script>" not in text
    assert view.roles[0].text in html.unescape(text)


def test_atomic_first_publish_never_replaces_a_racing_user_file(tmp_path: Path, monkeypatch) -> None:
    import youtube_intel.providers.obsidian as sink
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original = os.link
    def collide(src, dst, **kwargs):
        if dst == "note.md":
            (tmp_path / "note.md").write_text("Owner's concurrent note")
        return original(src, dst, **kwargs)
    monkeypatch.setattr(sink.os, "link", collide)
    try:
        with pytest.raises(FileExistsError):
            sink._atomic_replace(directory_fd, "note.md", b"generated", expected=None)
    finally:
        os.close(directory_fd)
    assert (tmp_path / "note.md").read_text() == "Owner's concurrent note"
    assert list(tmp_path.iterdir()) == [tmp_path / "note.md"]


def test_atomic_update_preserves_concurrent_owner_edit(tmp_path: Path, monkeypatch) -> None:
    import youtube_intel.providers.obsidian as sink
    path = tmp_path / "note.md"
    path.write_text("previous managed note")
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    expected = sink._read_regular_file(directory_fd, "note.md")
    original = sink._write_all
    def edit(fd, content):
        original(fd, content)
        path.write_text("Owner edited during write")
    monkeypatch.setattr(sink, "_write_all", edit)
    try:
        with pytest.raises(sink.NotePersistenceError):
            sink._atomic_replace(directory_fd, "note.md", b"new managed note", expected=expected)
    finally:
        os.close(directory_fd)
    assert path.read_text() == "Owner edited during write"
    assert list(tmp_path.iterdir()) == [path]


def test_candidate_labels_in_canonical_prose_cannot_leak_into_export(tmp_path: Path) -> None:
    repository, vault, publisher = setup(tmp_path)
    def inject(raw, refs):
        raw["core_conclusion"][0]["text"] += f" The internal reference is {refs[0]}."
    view = authority.service(repository, mutate=inject).run(content_id=authority.VIDEO)
    with pytest.raises(DeepAnalysisPublishError) as rejected:
        publisher.publish(content_id=authority.VIDEO, result_identity=view.result_identity)
    assert rejected.value.code == "RESULT_INELIGIBLE"
    assert not list(vault.rglob("*.md"))
