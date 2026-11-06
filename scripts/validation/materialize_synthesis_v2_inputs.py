"""Finite v2-r1 readonly package preparation; never fee consent or model IO."""
from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_specification = importlib.util.spec_from_file_location('_v2_preparation_controller', Path(__file__).with_name('bounded_synthesis_trial.py'))
assert _specification is not None and _specification.loader is not None
trial: Any = importlib.util.module_from_spec(_specification)
_specification.loader.exec_module(trial)


def materialize(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = trial.trial_spec('v2-r1') if spec is None else spec
    trial.require(selected['variant'] in {'v2-r1', 'v3-r1', 'v4-r1'}, 'FINITE_MATERIALIZATION_ONLY')
    original = selected['original']
    if selected['variant'] in {'v3-r1', 'v4-r1'}:
        parent = trial.stopped_v3_parent(selected) if selected['variant'] == 'v4-r1' else trial.stopped_v2_parent(selected)
        source_binding = trial.parsed(original['package'] / 'proposal-not-authorized.json')['binding']
    else:
        source_binding = trial.package_binding('v1-r4', _spec=original)
        parent = trial.parent_binding(selected)
    source_package: Path = original['package']
    destination: Path = selected['package']
    trial.require(not destination.exists() and not destination.is_symlink(), 'EXISTING_V2_BUNDLE_REFUSED')
    trial.directory(destination, create=True)
    inputs = trial.inputs
    source_manifest = trial.parsed(source_package / 'manifest.json')
    rows = []
    with inputs.offline():
        for old in source_manifest['cases']:
            source = Path(old['data_root'])
            before = inputs.inventory(source)
            root = destination / 'cases' / old['case'] / 'project'
            inputs.clone(source, root)
            synthetic = old['nominal_synthesis_scope_is_not_real_acquisition']
            if synthetic:
                inputs.write_once(root / 'fixture-identity.json', trial.read(source / 'fixture-identity.json'))
            row = inputs.materialize_case(root, root.parent / 'artifacts', old['case'], old['video_id'], old['language'],
                synthetic=synthetic, injection=old['injection'], clock=[datetime.now(UTC)], profile_id=selected['profile_id'])
            old_proof = trial.parsed(Path(old['artifacts']) / 'prepared-proof.json')
            new_proof = trial.parsed(Path(row['artifacts']) / 'prepared-proof.json')
            trial.require(new_proof['command'] == old_proof['command'] and new_proof['capture'] == old_proof['capture']
                and inputs.inventory(root) == before == inputs.inventory(source), 'V2_CHANGED_FROZEN_SOURCE')
            if selected['variant'] == 'v4-r1':
                old_body = trial.parsed(Path(old['artifacts']) / 'provider-body.json')
                new_body = trial.parsed(Path(row['artifacts']) / 'provider-body.json')
                trial.require(new_body['messages'][:3] == old_body['messages'][:3], 'V4_CHANGED_SOURCE_MESSAGES')
            rows.append(row)
    for name in ('input-only-oracle.md', 'source-before.json', 'source-after.json', 'official-price-recheck.md'):
        if (source_package / name).exists():
            inputs.write_once(destination / name, trial.read(source_package / name))
    for name in source_manifest['official_supplement']['document_hashes']:
        inputs.write_once(destination / 'official-supplement' / Path(name).name,
            trial.read(source_package / 'official-supplement' / Path(name).name))
    inputs.save(destination / 'immutable-profile.json', trial.profile.resolve_profile(selected['profile_id']))
    inventory = trial.code_hashes()
    inputs.save(destination / 'source-code-inventory.json', inventory)
    manifest = {'variant': selected['variant'], 'status': 'PREPARED_NOT_AUTHORIZED', 'qualification': 'CLOSED',
        'case_count': 8, 'cases': rows, 'parent_input_manifest_sha256': source_binding['manifest_sha256'],
        'parent_summary_sha256': trial.sha(trial.encoded(parent)) if selected['variant'] in {'v3-r1', 'v4-r1'} else parent['summary_sha256'], 'oracle_sha256': source_binding['oracle_sha256'],
        'source_code_inventory_sha256': trial.sha(trial.encoded(inventory)),
        'official_supplement': source_manifest['official_supplement'],
        'historical_calls': parent['historical_calls'], 'historical_held_microcny': parent['historical_held_microcny'],
        'actual_bill': 'UNKNOWN', 'model_calls': 0, 'credential_access': 0}
    inputs.save(destination / 'manifest.json', manifest)
    proposal: dict[str, Any] = trial.Trial(variant=selected['variant'], _spec=selected).proposal()
    trial.require(proposal['approval']['approved'] is False, 'PREPARATION_MUST_NOT_AUTHORIZE')
    inputs.save(destination / 'proposal-not-authorized.json', proposal)
    return proposal


if __name__ == '__main__':
    print(trial.profile.canonical(materialize()))
