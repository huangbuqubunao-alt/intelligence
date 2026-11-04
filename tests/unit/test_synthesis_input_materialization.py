"""Read-only input tooling cannot overwrite owners or trust corrupt parents."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pytest


def materializer() -> Any:
    script = Path(__file__).resolve().parents[2] / 'scripts/validation/materialize_synthesis_inputs.py'
    specification = importlib.util.spec_from_file_location('materialize_synthesis_inputs', script)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize('language', ['en', 'zh-CN'])
@pytest.mark.parametrize('injection', [False, True])
def test_stored_synthetic_parents_replay_after_restore_without_invocation(
    tmp_path: Path, language: str, injection: bool
) -> None:
    module = materializer()
    root = tmp_path / 'project'
    case = ('injection-' if injection else 'no-new-') + language
    clock = [module.FIXTURE_TIME]
    with module.offline():
        video = module.seed_synthetic(root, case, language, injection)
        result = module.materialize_case(root, tmp_path / 'artifacts', case, video, language,
            synthetic=True, injection=injection, clock=clock)
    assert result['expected'] == 'NO_NEW_INTELLIGENCE'
    assert result['status'] == 'PREPARED_NOT_AUTHORIZED'
    assert result['checks']['synthetic_restore'] == 'PASS_OWNED_SYNTHETIC_STORAGE_ONLY'
    tables = module.inventory(root)['tables']
    for table in ('jobs', 'provider_calls', 'distillation_execution_checkpoints',
        'distillation_resource_usage', 'system_synthesis_input_proofs', 'system_synthesis_cloud_authorizations',
        'system_synthesis_result_receipts'):
        assert tables[table]['rows'] == 0
    proof = json.loads((tmp_path / 'artifacts/prepared-proof.json').read_bytes())
    body = json.loads((tmp_path / 'artifacts/provider-body.json').read_bytes())
    assert proof['capture']['source']['display_name'] == module.SYNTHETIC
    assert proof['command']['output_language'] == language
    assert len(proof['capture']['source_refs']) == (3 if injection else 2)
    assert module.profile.canonical(body) == proof['provider_wire']
    messages = body['messages']
    assert messages[1]['content'].startswith('TASK_AND_PERSONALIZATION=')
    task = json.loads(messages[1]['content'].removeprefix('TASK_AND_PERSONALIZATION='))
    focus = module.SYNTHETIC_FOCUS[language]
    assert task['focus'] == [focus]
    assert 'NO_NEW' not in focus.upper()
    # The trusted preference uses the existing task context only. It does not
    # rewrite the first system contract or become source/quoted Summary text.
    assert all(focus not in messages[index]['content'] for index in (0, 2, 3))


def test_corrupt_data_copy_cannot_change_trusted_cues_and_blocks_preparation_and_backup(tmp_path: Path) -> None:
    module = materializer()
    root = tmp_path / 'project'
    clock = [module.FIXTURE_TIME]
    with module.offline():
        video = module.seed_synthetic(root, 'corrupt-parent', 'en', False)
        active = module.runtime(root, clock)
        original_review, original_value = module.ordinary_review(active, video, 'same-command')
        module.managed_parent_preflight(root)
        before = module.inventory(root)
        canonical = root / 'data/owned-synthetic-canonical.txt'
        canonical.write_bytes(canonical.read_bytes() + b'\nINVALID MUTATED PARENT')
        # The established reader trusts immutable, hash-checked SQLite timed
        # cues, not the retained canonical DATA copy. No mutated file text can
        # become an input; preparation and Backup separately reject disk loss.
        later_review, later_value = module.ordinary_review(active, video, 'same-command')
        assert later_value.input_json == original_value.input_json
        assert later_review['outgoing_request'] == original_review['outgoing_request']
        proof = module.persistence.loads(later_value.input_json)
        for ref in proof['capture']['source_refs']:
            resolved = active.repository.resolve_verified_evidence_text(ref['evidence_id'])
            assert resolved is not None and resolved.excerpt == ref['excerpt']
            assert 'INVALID MUTATED PARENT' not in resolved.excerpt
        with pytest.raises(ValueError, match='MANAGED_PARENT_BYTES_DIFFER'):
            module.managed_parent_preflight(root)
        readiness = active.backup_restore.readiness()
        assert readiness['ready'] is False
        assert 'DATABASE_UNAVAILABLE' in readiness['reasons']
        assert 'artifact changed or is missing' in readiness['message']
        after = module.inventory(root)
    assert after['tables'] == before['tables']
    assert after['data'] != before['data']


def test_readonly_clone_preserves_all_rows_and_data_and_refuses_existing_destination(tmp_path: Path) -> None:
    module = materializer()
    source, copied = tmp_path / 'source', tmp_path / 'copy'
    module.seed_synthetic(source, 'copy-safety', 'en', False)
    before = module.inventory(source)
    module.clone(source, copied)
    assert module.inventory(source) == module.inventory(copied) == before
    with pytest.raises(ValueError, match='EXISTING_CASE_REFUSED'):
        module.clone(source, copied)
    assert module.inventory(copied) == before


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_redirected_source_is_refused_before_copy(tmp_path: Path, kind: str) -> None:
    module = materializer()
    source, copied = tmp_path / 'source', tmp_path / 'copy'
    module.seed_synthetic(source, 'link-safety', 'en', False)
    owner = tmp_path / 'owner.txt'
    owner.write_bytes(b'synthetic-owner-never-change')
    if kind == 'symlink':
        (source / 'data/link.txt').symlink_to(owner)
    else:
        os.link(owner, source / 'data/link.txt')
    with pytest.raises(ValueError, match='(SYMLINK_REDIRECTION_REFUSED|HARDLINK_REFUSED)'):
        module.clone(source, copied)
    assert not copied.exists()
    assert owner.read_bytes() == b'synthetic-owner-never-change'


def test_existing_preparation_package_is_never_replaced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = materializer()
    monkeypatch.setattr(module, 'REPO', tmp_path)
    root = tmp_path / '.var/synthesis-input-materialization/existing'
    root.mkdir(parents=True)
    sentinel = root / 'owner.json'
    sentinel.write_bytes(b'preserve-nonmatching-input-package')
    with pytest.raises(ValueError, match='EXISTING_PACKAGE_REFUSED'):
        module.materialize(root)
    assert sentinel.read_bytes() == b'preserve-nonmatching-input-package'
