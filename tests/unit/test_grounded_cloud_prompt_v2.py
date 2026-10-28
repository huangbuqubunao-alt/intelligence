"""Offline version/authority compatibility; fake outputs grant no model quality."""

import hashlib
import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from conftest import _load_module

from youtube_intel import distillation as d
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.runtime_composition import ProductionDistillationBudget
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StateStoreError,
    StorageRoot,
)

adapter_support = _load_module('test_bigmodel_distillation_adapter')
_load_module('test_task022_personalized_distillation')
service_support = _load_module('test_bigmodel_distillation_transport')
V2 = 'bigmodel-glm-4.7-flash-thinking-json-grounding-qualification-v2'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()


def _profiled(value, profile):
    if profile is None:
        return value
    return d._GroundingV2VerifiedDistillationInput(
        **{item.name: getattr(value, item.name) for item in fields(d.VerifiedDistillationInput)},
        cloud_profile_id=profile)


def test_v1_input_prompt_profile_request_and_execution_stay_golden():
    value = adapter_support._input()
    assert digest(d.verified_distillation_input_projection(value)) == 'b49628928ee84e1eb812464b93a0591cb379279001193a0af7cc569e96afd9a3'
    assert digest(d._distillation_prompt_messages(value, task_role='system')) == '9683bd6aec5341aa3c3380e778ccadd8eab56d1adb65cf5a7e2969aefedf329d'
    assert digest(d.BigModelGlm47FlashDistillationTransport.profile_projection()) == '89ae2936d1fb8291af97dd3b7eda476010134a65f5c196b30e3ae1292ec0c486'
    assert hashlib.sha256(d._bigmodel_request_bytes(d.BigModelGlm47FlashDistillationTransport._request(value))).hexdigest() == '012ef86eae4e73affb58cbc11e264603c59d70f97068d1aafead3541653723aa'
    assert d.PersonalizedDistillationService._reservation_id(source_id='source-golden',
        video_id=value.video_id, evidence_ids=value.evidence_ids, selected_provider=value.selected_provider,
        selected_model=value.selected_model, output_language=value.output_language,
        verified_input_hash=value.semantic_hash) == 'distillation:reservation:v3:e7e3af2acad9ad52b5d806597f8c15a300ddfe32172d4cab2742822c8bbbb5fd'


@pytest.mark.parametrize('language', ['en', 'zh-CN'])
def test_v2_is_generic_additive_and_keeps_source_separate(language):
    value = _profiled(adapter_support._input(language), V2)
    old = d._distillation_prompt_messages(value, task_role='system')
    request = d.BigModelGlm47FlashGroundingV2DistillationTransport._request(value)
    assert request['messages'][1:] == old[1:]
    assert request['messages'][0]['content'].startswith(old[0]['content'])
    extra = request['messages'][0]['content'][len(old[0]['content']):]
    for phrase in ['product user', 'source speaker', 'publisher', 'attribute', 'modality',
            'approximate', 'measurement', 'magnitude', 'causal', 'SYSTEM_INFERENCE',
            'revisable', 'user_relevant_information', 'NO_NEW_INTELLIGENCE']:
        assert phrase in extra
    for forbidden in ['QoXR', 'Gemini', 'DeepMind', 'conjecture', 'IMO', '20', '100', 'decades']:
        assert forbidden not in extra
    assert request | {'messages': old} == d.BigModelGlm47FlashDistillationTransport._request(
        adapter_support._input(language))
    profile = d.BigModelGlm47FlashGroundingV2DistillationTransport.profile_projection()
    assert profile['request_profile_version'] == V2
    assert profile['prompt_version'] != d.BigModelGlm47FlashDistillationTransport._PROMPT_VERSION
    assert profile['grounding_contract_sha256'] == hashlib.sha256(extra.lstrip('\n').encode()).hexdigest()
    assert not d.BigModelGlm47FlashGroundingV2DistillationTransport(
        authorization=d.CloudDistillationAuthorization(), credential_resolver=lambda: pytest.fail('no key')
    ).is_authorized_for_normal_production(value)


@pytest.mark.parametrize('transport_name, profile', [
    ('BigModelGlm47FlashDistillationTransport', V2),
    ('BigModelGlm47FlashGroundingV2DistillationTransport', None),
    ('BigModelGlm47FlashGroundingV2DistillationTransport', 'unknown-profile'),
])
def test_cross_or_unknown_profile_never_resolves_key_or_wire(transport_name, profile):
    value = _profiled(adapter_support._input(), profile)
    transport = getattr(d, transport_name)(authorization=d.CloudDistillationAuthorization(
        cloud_enabled=True, provider='zhipu_bigmodel', model='glm-4.7-flash',
        credential_available=True, provider_available=True, qualification_input_hash=value.semantic_hash),
        credential_resolver=lambda: pytest.fail('profile refusal must precede key'),
        wire_transport=lambda *_: pytest.fail('profile refusal must precede wire'))
    assert not transport.is_authorized_for_qualification(value)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        transport.generate(value)


def _variant(repository, transport_class, calls):
    def wire(request, key, timeout, retries):
        calls.append(('wire', request))
        assert (key, timeout, retries) == ('synthetic-key', 300, 0)
        evidence = json.loads(request['messages'][2]['content'].split('=', 1)[1])['evidence']
        output = {'core_conclusion': 'Offline synthetic retained judgment.',
            'user_relevant_information': [], 'important_new_information': [],
            'meaningful_details': [], 'filtered_noise': [], 'claim_kind': 'SYSTEM_INFERENCE',
            'evidence': [{**{k: item[k] for k in ('evidence_id', 'start_ms', 'end_ms')},
                'stance': 'supporting'} for item in evidence]}
        return d._BigModelWireResponse(200, json.dumps({'model': 'glm-4.7-flash',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': json.dumps(output)}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10}}).encode())
    transport = transport_class(authorization=d.CloudDistillationAuthorization(),
        credential_resolver=lambda: calls.append(('key', None)) or 'synthetic-key', wire_transport=wire)
    return service_support._service(repository, transport)



def _physical_source(tmp_path):
    """Reuse trusted builders, registering real DATA before immutable Evidence."""
    fixture = service_support.fixtures
    repository = fixture._repository(tmp_path)
    source, video = fixture._source_and_video(repository, 'grounding-v2-offline')
    data = tmp_path / 'DATA'
    data.mkdir()
    name = f'{video}-1000-1500.txt'
    raw = b'Fixture canonical evidence.'
    (data / name).write_bytes(raw)
    repository.upsert_artifact(ArtifactWrite(
        artifact_id=f'artifact-{video}-1000-1500', artifact_key=f'artifact-key-{video}-1000-1500',
        video_id=video, job_id=None, kind=ArtifactKind.TRANSCRIPT_CANONICAL,
        storage_root=StorageRoot.DATA, relative_path=name,
        content_hash=hashlib.sha256(raw).hexdigest(), provider=None, model=None,
        producer_version='v1', retention_class=RetentionClass.LONG_LIVED, expires_at=None), now=fixture.NOW)
    evidence = fixture._evidence(repository, video)
    return repository, source, video, evidence


def test_new_identity_consent_history_read_and_backup_remain_isolated(tmp_path):
    repository, source, video, evidence = _physical_source(tmp_path)
    calls = []
    v1 = _variant(repository, d.BigModelGlm47FlashDistillationTransport, calls)
    v2 = _variant(repository, d.BigModelGlm47FlashGroundingV2DistillationTransport, calls)
    arguments = dict(source_id=source, video_id=video, evidence_ids=(evidence,))
    old_command, old_input = v1._prospective_cloud_command(**arguments)
    new_command, new_input = v2._prospective_cloud_command(**arguments)
    assert old_command.execution_id != new_command.execution_id
    assert old_input.semantic_hash != new_input.semantic_hash
    assert type(old_input) is d.VerifiedDistillationInput and not hasattr(old_input, 'cloud_profile_id')
    assert type(new_input) is d._GroundingV2VerifiedDistillationInput and new_input.cloud_profile_id == V2
    assert all(type(item) is d.VerifiedEvidenceInput for item in new_input.evidence)
    assert d.verified_distillation_input_projection(new_input)['cloud_profile_id'] == V2
    assert 'cloud_profile_id' not in d.verified_distillation_input_projection(old_input)
    assert not ProductionDistillationBudget().check(new_command).allowed
    old = v1.reserve_distillation_execution(**arguments)
    service_support._permit(v1, old_input)
    v1.authorize_reserved_cloud_execution(old.execution_id, consent_kind='OWNER_QUALIFICATION')
    before = service_support._snapshot(repository, tmp_path)
    with pytest.raises((ValueError, StateStoreError)):
        v2.authorize_reserved_cloud_execution(old.execution_id, consent_kind='OWNER_QUALIFICATION')
    assert calls == [] and before == service_support._snapshot(repository, tmp_path)
    old_result = v1.continue_qualification_reserved_distillation(old.execution_id)
    old_record = repository.get_distillation_execution(old.execution_id)
    old_consent = repository.get_cloud_execution_authorization(old.execution_id)
    old_usage = repository.get_distillation_resource_usage(old.execution_id)
    old_card = AuthoritativeIntelligenceReader(repository).read_current_card(old_result.intelligence_id)
    new = v2.reserve_distillation_execution(**arguments)
    # A v1 one-call hash is not authority for the new profile/input.
    v2._transport._authorization = v1._transport._authorization
    assert not v2._transport.is_authorized_for_qualification(new_input)
    count = len(calls)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        v2._transport.generate(new_input)
    assert len(calls) == count
    service_support._permit(v2, new_input)
    before_consent = service_support._snapshot(repository, tmp_path / 'DATA')
    with pytest.raises(d.CloudConsentRequiredError):
        v2.continue_qualification_reserved_distillation(new.execution_id)
    assert len(calls) == count
    assert service_support._snapshot(repository, tmp_path / 'DATA') == before_consent
    v2.authorize_reserved_cloud_execution(new.execution_id, consent_kind='OWNER_QUALIFICATION')
    assert repository.get_cloud_execution_authorization(new.execution_id).verified_input_hash == new_input.semantic_hash
    result = v2.continue_qualification_reserved_distillation(new.execution_id)
    assert result.status.value == old_result.status.value == 'SUCCEEDED'
    assert result.invocation_count == old_result.invocation_count == 1
    assert len([call for call in calls if call[0] == 'wire']) == 2
    assert repository.get_distillation_execution(old.execution_id) == old_record
    assert repository.get_cloud_execution_authorization(old.execution_id) == old_consent
    assert repository.get_distillation_resource_usage(old.execution_id) == old_usage
    reread = AuthoritativeIntelligenceReader(repository).read_current_card(old_result.intelligence_id)
    assert reread.core_conclusion == old_card.core_conclusion
    assert reread.verified.revision_id == old_card.verified.revision_id
    assert reread.verified.evidence_ids == old_card.verified.evidence_ids
    with repository._connect() as connection:
        repository.verify_cloud_audit_database(connection)
    service = BackupRestoreService(database=tmp_path / 'state.sqlite3', data_root=tmp_path / 'DATA')
    before = service_support._snapshot(repository, tmp_path / 'DATA')
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(tmp_path / 'state.sqlite3')
    assert service_support._snapshot(restored, tmp_path / 'DATA') == before
    with restored._connect() as connection:
        restored.verify_cloud_audit_database(connection)
    assert restored.get_distillation_execution(old.execution_id) == old_record
    assert restored.get_cloud_execution_authorization(old.execution_id) == old_consent
    assert restored.get_distillation_resource_usage(old.execution_id) == old_usage


@pytest.mark.parametrize('changed', ['cross-profile', 'changed-contract'])
def test_reserved_profile_mismatch_is_terminal_before_credentials(tmp_path, monkeypatch, changed):
    repository, source, video, evidence, _ = service_support._setup(tmp_path)
    calls = []
    old_class = (d.BigModelGlm47FlashDistillationTransport if changed == 'cross-profile'
        else d.BigModelGlm47FlashGroundingV2DistillationTransport)
    old = _variant(repository, old_class, calls)
    new = _variant(repository, d.BigModelGlm47FlashGroundingV2DistillationTransport, calls)
    arguments = dict(source_id=source, video_id=video, evidence_ids=(evidence,))
    reserved = old.reserve_distillation_execution(**arguments)
    _, value = old._reserved_command_from_record(repository.get_distillation_execution(reserved.execution_id))
    service_support._permit(old, value)
    old.authorize_reserved_cloud_execution(reserved.execution_id, consent_kind='OWNER_QUALIFICATION')
    consent = repository.get_cloud_execution_authorization(reserved.execution_id)
    if changed == 'changed-contract':
        monkeypatch.setattr(d, '_GROUNDING_V2_CONTRACT', d._GROUNDING_V2_CONTRACT + ' Contract changed.')
    result = new.continue_qualification_reserved_distillation(reserved.execution_id)
    assert result.status.value == 'REJECTED_EVIDENCE' and result.invocation_count == 0
    assert calls == []
    assert repository.get_cloud_execution_authorization(reserved.execution_id) == consent
    assert repository.get_distillation_execution(reserved.execution_id).status != 'PENDING'
    assert new.continue_qualification_reserved_distillation(reserved.execution_id) == result
    assert calls == []


@pytest.mark.parametrize('provider', ['LOCAL', 'BILIBILI'])
def test_v2_does_not_expand_cloud_content_permissions(provider):
    value = _profiled(replace(adapter_support._input(), content_provider=provider), V2)
    transport = d.BigModelGlm47FlashGroundingV2DistillationTransport(
        authorization=d.CloudDistillationAuthorization(cloud_enabled=True, provider='zhipu_bigmodel',
            model='glm-4.7-flash', credential_available=True, provider_available=True,
            qualification_input_hash=value.semantic_hash),
        credential_resolver=lambda: pytest.fail('private content must not resolve key'),
        wire_transport=lambda *_: pytest.fail('private content must not reach wire'))
    assert not transport.is_authorized_for_qualification(value)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        transport.generate(value)


def test_v2_owner_permit_never_grants_normal_production(tmp_path):
    repository, source, video, evidence, _ = service_support._setup(tmp_path)
    calls = []
    service = _variant(repository, d.BigModelGlm47FlashGroundingV2DistillationTransport, calls)
    reserved = service.reserve_distillation_execution(source_id=source, video_id=video, evidence_ids=(evidence,))
    _, value = service._reserved_command_from_record(repository.get_distillation_execution(reserved.execution_id))
    service_support._permit(service, value)
    service.authorize_reserved_cloud_execution(reserved.execution_id, consent_kind='OWNER_QUALIFICATION')
    result = service.continue_reserved_distillation(reserved.execution_id)
    assert result.status.value == 'WAITING_MODEL' and result.invocation_count == 0
    assert calls == []


def test_legacy_base_dataclass_fields_and_raw_asdict_remain_exact():
    from dataclasses import asdict, fields
    assert tuple(field.name for field in fields(d.VerifiedDistillationInput)) == (
        'source_display_name', 'video_id', 'video_title', 'evidence', 'personalization',
        'source_focus_rules', 'source_ignore_rules', 'distillation_style', 'selected_provider',
        'selected_model', 'semantic_hash', 'output_language', 'content_provider',
        'local_content_context_hash', 'wire_version', 'input_json', 'context_json',
        'local_profile_id', 'local_profile_hash')
    assert digest(asdict(adapter_support._input())) == '525f0ea4c1bc7cc923d17b81c9975ff2feff36ce7c491e548f0d39c7a7c02a72'


def test_legacy_long_raw_value_snapshot_hash_is_unchanged():
    long = _load_module('test_long_grounding_projection')
    assert long.prepare().semantic_snapshot_hash == '4f6bdfc09fd434eac242f9daef4bfe9c568d6d7fe793d1f5bac8e0d159b25027'



def test_v2_subtype_is_frozen_keeps_typed_refs_and_rejects_other_subtypes():
    value = adapter_support._input()
    v2 = _profiled(value, V2)
    assert v2.evidence is value.evidence
    assert v2.evidence[0] is value.evidence[0]
    with pytest.raises(FrozenInstanceError):
        v2.cloud_profile_id = 'unknown'
    class Foreign(d.VerifiedDistillationInput):
        pass
    foreign = Foreign(**{item.name: getattr(value, item.name) for item in fields(d.VerifiedDistillationInput)})
    assert not d._cloud_source_allowed(foreign)
    assert not d._cloud_source_allowed(replace(v2, selected_provider='openai', selected_model='gpt-4.1'))
    assert not d._cloud_source_allowed(replace(v2, cloud_profile_id='unknown'))
