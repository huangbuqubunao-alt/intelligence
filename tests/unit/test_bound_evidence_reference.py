"""Synthetic reference-format evidence; never a model/oracle qualification."""
import hashlib
import importlib
import json
from dataclasses import fields, replace

import pytest
from conftest import _load_module

from youtube_intel import distillation as d

PROFILE = 'bigmodel-glm-4.7-flash-thinking-json-bound-evidence-qualification-v3'
PROTOCOL = 'bound-evidence-reference-v1'


def codec():
    return importlib.import_module('youtube_intel.bound_evidence_reference')


def value(count=2):
    evidence=tuple(d.VerifiedEvidenceInput(evidence_id=f'synthetic-id-{i}',start_ms=i*1000,end_ms=i*1000+321,
        excerpt=f'Public synthetic excerpt {i}: café 中文.',
        excerpt_hash=hashlib.sha256(f'Public synthetic excerpt {i}: café 中文.'.encode()).hexdigest(),
        timed_transcript_id='synthetic-transcript',timed_transcript_hash='b'*64) for i in range(count))
    return d._BoundEvidenceVerifiedDistillationInput(source_display_name='Synthetic public publisher',video_id='synthetic-public',
        video_title='Synthetic title',evidence=evidence,personalization=('Synthetic product preference',),
        source_focus_rules=(),source_ignore_rules=(),distillation_style='BALANCED',selected_provider='zhipu_bigmodel',
        selected_model='glm-4.7-flash',semantic_hash='c'*64,output_language='en',cloud_profile_id=PROFILE)


def output(refs=('E01','E02'), *, no_new=False):
    if no_new:
        return {'reference_protocol':PROTOCOL,'result':'NO_NEW_INTELLIGENCE','evidence':[{'ref':ref} for ref in refs]}
    return {'reference_protocol':PROTOCOL,'core_conclusion':'The publisher reports a tentative interpretation; this is a revisable system inference.',
        'user_relevant_information':['Relevant to the product user; not their experience.'],
        'important_new_information':[],'meaningful_details':['Approximately three synthetic examples.'],
        'filtered_noise':[],'claim_kind':'SYSTEM_INFERENCE',
        'evidence':[{'ref':ref,'stance':'supporting' if i==0 else 'conditional'} for i,ref in enumerate(refs)]}


def test_bound_format_restores_exact_references_without_changing_claims():
    c=codec()
    v=value()
    context=c.reference_context(v)
    assert context['evidence']==[{'ref':f'E{i+1:02}','excerpt':item.excerpt} for i,item in enumerate(v.evidence)]
    raw=json.dumps(output(),ensure_ascii=False)
    restored=json.loads(c.normalize_response(raw,v,request_origin_hash=context['request_origin_hash']))
    assert {k:item for k,item in restored.items() if k!='evidence'}=={k:item for k,item in output().items() if k not in {'evidence','reference_protocol'}}
    assert restored['evidence']==[{'evidence_id':item.evidence_id,'start_ms':item.start_ms,'end_ms':item.end_ms,
        'stance':output()['evidence'][i]['stance']} for i,item in enumerate(v.evidence)]
    assert json.loads(raw)==output()


def test_no_new_requires_complete_exact_bound_set():
    c=codec()
    v=value()
    origin=c.reference_context(v)['request_origin_hash']
    restored=json.loads(c.normalize_response(json.dumps(output(no_new=True)),v,request_origin_hash=origin))
    assert restored['result']=='NO_NEW_INTELLIGENCE' and len(restored['evidence'])==2
    with pytest.raises(ValueError):
        c.normalize_response(json.dumps(output(('E01',),no_new=True)),v,request_origin_hash=origin)


@pytest.mark.parametrize('change', ['foreign','duplicate','old-id','old-time','extra','bad-marker','stance','ref-type','claim-type','extra-top','incomplete-zero'])
def test_strict_new_representation_rejects_invented_or_mixed_reference_schema(change):
    c=codec()
    v=value()
    payload=output()
    if change=='foreign':
        payload['evidence'][0]['ref']='E99'
    if change=='duplicate':
        payload['evidence'][1]['ref']='E01'
    if change=='old-id':
        payload['evidence'][0]['evidence_id']=v.evidence[0].evidence_id
    if change=='old-time':
        payload['evidence'][0]['end_ms']=999999
    if change=='extra':
        payload['evidence'][0]['confidence']=1
    if change=='bad-marker':
        payload['reference_protocol']='unknown'
    if change=='stance':
        payload['evidence'][0]['stance']='fact'
    if change=='ref-type':
        payload['evidence'][0]['ref']=True
    if change=='claim-type':
        payload['claim_kind']=[]
    if change=='extra-top':
        payload['request_origin_hash']='c'*64
    if change=='incomplete-zero':
        payload=output(('E01',),no_new=True)
    with pytest.raises(ValueError):
        c.normalize_response(json.dumps(payload),v,request_origin_hash=c.reference_context(v)['request_origin_hash'])


@pytest.mark.parametrize('change', ['title','text','position','order','hash','profile'])
def test_backend_origin_rejects_cross_input_not_model_echo(change):
    c=codec()
    original=value()
    origin=c.reference_context(original)['request_origin_hash']
    changed=replace(original,video_title='Changed synthetic title')
    if change=='text':
        item=original.evidence[0]
        text='Changed exact synthetic excerpt.'
        changed=replace(original,evidence=(replace(item,excerpt=text,excerpt_hash=hashlib.sha256(text.encode()).hexdigest()),original.evidence[1]))
    if change=='position':
        changed=replace(original,evidence=(replace(original.evidence[0],end_ms=322),original.evidence[1]))
    if change=='order':
        changed=replace(original,evidence=original.evidence[::-1])
    if change=='hash':
        changed=replace(original,semantic_hash='d'*64)
    if change=='profile':
        changed=replace(original,cloud_profile_id='unknown')
    with pytest.raises(ValueError):
        c.normalize_response(json.dumps(output()),changed,request_origin_hash=origin)


@pytest.mark.parametrize('count', [1,20])
def test_full_existing_evidence_bound_unicode_and_no_truncation(count):
    c=codec()
    v=value(count)
    context=c.reference_context(v)
    assert len(context['evidence'])==count
    assert context['evidence'][-1]['ref']==f'E{count:02}'
    normalized=c.normalize_response(json.dumps(output(tuple(row['ref'] for row in context['evidence']),no_new=True)),v,
        request_origin_hash=context['request_origin_hash'])
    assert {row['evidence_id'] for row in json.loads(normalized)['evidence']}==set(v.evidence_ids)
    assert context==c.reference_context(v)


@pytest.mark.parametrize('change',['overflow','bool','hash','locator','duplicate','over20'])
def test_invalid_input_rejects_before_credentials(change):
    v=value()
    item=v.evidence[0]
    if change=='overflow':
        v=replace(v,evidence=(replace(item,end_ms=2**63),))
    if change=='bool':
        v=replace(v,evidence=(replace(item,start_ms=False),))
    if change=='hash':
        v=replace(v,evidence=(replace(item,excerpt_hash='a'*64),))
    if change=='locator':
        v=replace(v,evidence=(replace(item,locator_type='TEXT_RANGE'),))
    if change=='duplicate':
        v=replace(v,evidence=(item,item))
    if change=='over20':
        v=value(21)
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(
        cloud_enabled=True,provider='zhipu_bigmodel',model='glm-4.7-flash',credential_available=True,
        provider_available=True,qualification_input_hash=v.semantic_hash),
        credential_resolver=lambda:pytest.fail('invalid input resolved key'),wire_transport=lambda *_:pytest.fail('invalid wire'))
    with pytest.raises(d.CloudDistillationPreDispatchError):
        adapter.generate(v)


def test_new_prompt_keeps_v2_semantic_rules_and_task_but_replaces_only_reference_representation():
    v=value()
    old=d._grounding_v2_prompt_messages(v)
    request=d.BigModelGlm47FlashBoundEvidenceDistillationTransport._request(v)
    messages=request['messages']
    assert messages[1]==old[1]
    assert d._GROUNDING_V2_CONTRACT in messages[0]['content']
    source=json.loads(messages[2]['content'].split('=',1)[1])
    assert source['evidence']==codec().reference_context(v)['evidence']
    assert source['video_title']==v.video_title and source['reference_protocol']==PROTOCOL
    assert 'request_origin_hash' not in source
    assert all(set(row)=={'ref','excerpt'} for row in source['evidence'])
    assert 'with exact evidence_id' not in messages[0]['content']
    assert 'only ref' not in d._GROUNDING_V2_CONTRACT
    assert request|{'messages':[]}==d.BigModelGlm47FlashDistillationTransport._request(
        d.VerifiedDistillationInput(**{f.name:getattr(v,f.name) for f in fields(d.VerifiedDistillationInput)}))|{'messages':[]}


@pytest.mark.parametrize('adapter_name', ['BigModelGlm47FlashDistillationTransport','BigModelGlm47FlashGroundingV2DistillationTransport'])
def test_new_typed_input_is_not_old_profile_permission(adapter_name):
    adapter=getattr(d,adapter_name)(authorization=d.CloudDistillationAuthorization(),credential_resolver=lambda:pytest.fail('old key'))
    assert not adapter.is_authorized_for_qualification(value())
    with pytest.raises(d.CloudDistillationPreDispatchError):
        adapter.generate(value())


@pytest.mark.parametrize('provider',['LOCAL','BILIBILI'])
def test_v3_does_not_expand_cloud_content_permissions(provider):
    v=replace(value(),content_provider=provider)
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(),
        credential_resolver=lambda:pytest.fail('private key'),wire_transport=lambda *_:pytest.fail('private wire'))
    assert not adapter.is_authorized_for_qualification(v)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        adapter.generate(v)


def services(tmp_path, *, outcome='positive', credential=True):
    support=_load_module('test_grounded_cloud_prompt_v2')
    repo,source,video,eid=support._physical_source(tmp_path)
    calls=[]
    raws=[]
    def key():
        calls.append('fake-key')
        return 'synthetic-key' if credential else None
    def wire(request,*_):
        calls.append('fake-wire')
        if outcome=='tls':
            raise d.CloudDistillationPreDispatchError('known fake no POST')
        if outcome=='timeout':
            raise TimeoutError('synthetic secret and private reasoning')
        if outcome=='202':
            return d._BigModelWireResponse(202,b'')
        source_payload=json.loads(request['messages'][2]['content'].split('=',1)[1])
        refs=tuple(row['ref'] for row in source_payload['evidence'])
        payload=output(refs,no_new=outcome=='no-new')
        if outcome=='bad-alias':
            payload['evidence'][0]['ref']='E99'
        if outcome=='no-support':
            payload['evidence'][0]['stance']='conditional'
        raw=json.dumps(payload,ensure_ascii=False)
        raws.append(raw)
        return d._BigModelWireResponse(200,json.dumps({'model':'glm-4.7-flash','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':raw,'reasoning_content':'private synthetic reasoning'}}],
            'usage':{'prompt_tokens':20,'completion_tokens':10}}).encode())
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(),
        credential_resolver=key,wire_transport=wire)
    service=support.service_support._service(repo,adapter)
    return support,repo,source,video,eid,service,calls,raws


@pytest.mark.parametrize('outcome',['positive','no-new','bad-alias','no-support','timeout','202'])
def test_v3_production_service_original_validator_once_and_restore(tmp_path,outcome):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    support,repo,source,video,eid,service,calls,raws=services(tmp_path,outcome=outcome)
    command,v=service._prospective_cloud_command(source_id=source,video_id=video,evidence_ids=(eid,))
    assert type(v) is d._BoundEvidenceVerifiedDistillationInput
    before=support.service_support._snapshot(repo,tmp_path/'DATA')
    preview=service.preview_cloud_execution(source_id=source,video_id=video,evidence_ids=(eid,),qualified=False,credential_available=False)
    assert not preview['readiness']['can_confirm'] and not calls
    assert support.service_support._snapshot(repo,tmp_path/'DATA')==before
    reserved=service.reserve_distillation_execution(source_id=source,video_id=video,evidence_ids=(eid,))
    assert reserved.execution_id==command.execution_id
    support.service_support._permit(service,v)
    assert not service._transport.is_authorized_for_normal_production(v)
    with pytest.raises(d.CloudConsentRequiredError):
        service.continue_qualification_reserved_distillation(reserved.execution_id)
    assert not calls
    service.authorize_reserved_cloud_execution(reserved.execution_id,consent_kind='OWNER_QUALIFICATION')
    result=service.continue_qualification_reserved_distillation(reserved.execution_id)
    expected={'positive':'SUCCEEDED','no-new':'SUCCEEDED_NO_NEW_INTELLIGENCE','bad-alias':'REJECTED_OUTPUT',
        'no-support':'REJECTED_OUTPUT','timeout':'AMBIGUOUS','202':'AMBIGUOUS'}[outcome]
    assert result.status.value==expected and result.invocation_count==1
    assert calls.count('fake-wire')==1 and not repo.can_cancel_waiting_model_execution(reserved.execution_id)
    old_calls=list(calls)
    assert service.continue_qualification_reserved_distillation(reserved.execution_id)==result
    assert calls==old_calls
    usage=repo.get_distillation_resource_usage(reserved.execution_id)
    assert usage.cost_microunits is None
    backup=BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=tmp_path/'DATA')
    if outcome in {'timeout','202'}:
        assert usage.outcome=='TRANSPORT_OUTCOME_UNKNOWN' and usage.invocation_count==1
        assert backup.readiness()['ready']
    if outcome=='positive':
        card=repo.get_distillation_card(result.revision_id)
        assert card.core_conclusion==json.loads(raws[0])['core_conclusion']
        assert card.meaningful_details==tuple(json.loads(raws[0])['meaningful_details'])
    before=support.service_support._snapshot(repo,tmp_path/'DATA')
    archive=backup.create_backup()
    path,_=backup.backup_download(archive.backup_id)
    staged=backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restarted=SQLiteStateRepository(tmp_path/'state.sqlite3')
    assert support.service_support._snapshot(restarted,tmp_path/'DATA')==before
    assert restarted.get_distillation_execution(reserved.execution_id).status==expected


@pytest.mark.parametrize('credential',[False,True])
def test_v3_known_zero_wait_cancels_restart_and_backup_without_replay(tmp_path,credential):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    support,repo,source,video,eid,service,calls,_=services(tmp_path,outcome='tls',credential=credential)
    reserved=service.reserve_distillation_execution(source_id=source,video_id=video,evidence_ids=(eid,))
    _,v=service._reserved_command_from_record(repo.get_distillation_execution(reserved.execution_id))
    support.service_support._permit(service,v)
    service.authorize_reserved_cloud_execution(reserved.execution_id,consent_kind='OWNER_QUALIFICATION')
    result=service.continue_qualification_reserved_distillation(reserved.execution_id)
    assert result.status.value=='WAITING_MODEL' and result.invocation_count==0
    backup=BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=tmp_path/'DATA')
    assert not backup.readiness()['ready'] and repo.can_cancel_waiting_model_execution(reserved.execution_id)
    cancelled=repo.cancel_waiting_model_execution(reserved.execution_id,video_id=video,now=support.service_support.NOW)
    assert cancelled.status=='CANCELLED' and cancelled.invocation_count==0
    old_calls=list(calls)
    assert service.continue_qualification_reserved_distillation(reserved.execution_id).status.value=='CANCELLED'
    assert calls==old_calls and backup.readiness()['ready']
    restarted=SQLiteStateRepository(tmp_path/'state.sqlite3')
    assert restarted.get_distillation_execution(reserved.execution_id)==cancelled
    archive=backup.create_backup()
    path,_=backup.backup_download(archive.backup_id)
    staged=backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert restarted.get_distillation_execution(reserved.execution_id)==cancelled


def test_adapter_retains_raw_and_separately_derives_normalized_public_result():
    v=value()
    raw=json.dumps(output(),ensure_ascii=False,indent=2)
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(
        cloud_enabled=True,provider='zhipu_bigmodel',model='glm-4.7-flash',credential_available=True,
        provider_available=True,qualification_input_hash=v.semantic_hash),credential_resolver=lambda:'synthetic-key',
        wire_transport=lambda *_:d._BigModelWireResponse(200,json.dumps({'model':'glm-4.7-flash',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':raw,
                'reasoning_content':'PRIVATE SYNTHETIC REASONING'}}]}).encode()))
    result=adapter.generate(v)
    assert type(result) is d._BoundEvidenceTransportResult and result.raw==raw
    assert result.request_origin_hash==codec().reference_context(v)['request_origin_hash']
    assert result.normalized_raw!=raw and 'PRIVATE' not in repr(result)
    assert json.loads(result.normalized_raw)['core_conclusion']==output()['core_conclusion']
    assert set(f.name for f in fields(d.DistillationTransportResult))=={'raw','actual_provider','actual_model',
        'input_tokens','output_tokens','cost_microunits','duration_ms','http_status_code'}
    assert 'cloud_profile_id' not in {f.name for f in fields(d.VerifiedDistillationInput)}


@pytest.mark.parametrize('tamper',['origin','normalized','bare-result','old-protocol-raw'])
def test_service_independently_rejects_result_mix_or_forged_normalization(tmp_path,monkeypatch,tamper):
    support,repo,source,video,eid,service,calls,_=services(tmp_path)
    reserved=service.reserve_distillation_execution(source_id=source,video_id=video,evidence_ids=(eid,))
    _,v=service._reserved_command_from_record(repo.get_distillation_execution(reserved.execution_id))
    support.service_support._permit(service,v)
    service.authorize_reserved_cloud_execution(reserved.execution_id,consent_kind='OWNER_QUALIFICATION')
    generate=service._transport.generate
    def mixed(value):
        response=generate(value)
        if tamper=='origin':
            return replace(response,request_origin_hash='0'*64)
        if tamper=='normalized':
            return replace(response,normalized_raw=response.normalized_raw.replace('tentative','established'))
        if tamper=='old-protocol-raw':
            return replace(response,raw=response.normalized_raw)
        return d.DistillationTransportResult(**{item.name:getattr(response,item.name) for item in fields(d.DistillationTransportResult)})
    monkeypatch.setattr(service._transport,'generate',mixed)
    result=service.continue_qualification_reserved_distillation(reserved.execution_id)
    assert result.status.value=='REJECTED_OUTPUT' and result.invocation_count==1
    assert calls.count('fake-wire')==1
    assert repo.get_distillation_resource_usage(reserved.execution_id).outcome=='STRUCTURED_OR_EVIDENCE_VALIDATION_REJECTED'
    assert not repo.can_cancel_waiting_model_execution(reserved.execution_id)


@pytest.mark.parametrize('raw', ['{"reference_protocol":"bound-evidence-reference-v1","reference_protocol":"bound-evidence-reference-v1"}',
    '{"reference_protocol":"bound-evidence-reference-v1","evidence":NaN}', '{}', '['*2000+'0'+']'*2000, 'x'*(2*1024*1024+1)])
def test_duplicate_nonfinite_malformed_or_oversized_new_body_rejects(raw):
    c=codec()
    v=value()
    with pytest.raises(ValueError):
        c.normalize_response(raw,v,request_origin_hash=c.reference_context(v)['request_origin_hash'])


def test_v2_versus_v3_profiles_bind_distinct_hash_reservation_and_consent(tmp_path):
    support,repo,source,video,eid,new,_,_=services(tmp_path)
    old=support._variant(repo,d.BigModelGlm47FlashGroundingV2DistillationTransport,[])
    args=dict(source_id=source,video_id=video,evidence_ids=(eid,))
    old_command,old_input=old._prospective_cloud_command(**args)
    command,v=new._prospective_cloud_command(**args)
    assert command.execution_id!=old_command.execution_id and v.semantic_hash!=old_input.semantic_hash
    assert type(old_input) is d._GroundingV2VerifiedDistillationInput
    assert type(v) is d._BoundEvidenceVerifiedDistillationInput
    reserved=new.reserve_distillation_execution(**args)
    # A permit for the old profile's semantic hash grants the new one nothing.
    support.service_support._permit(new,old_input)
    assert not new._transport.is_authorized_for_qualification(v)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        new._transport.generate(v)
    support.service_support._permit(new,v)
    new.authorize_reserved_cloud_execution(reserved.execution_id,consent_kind='OWNER_QUALIFICATION')
    assert repo.get_cloud_execution_authorization(reserved.execution_id).verified_input_hash==v.semantic_hash



def test_catalog_is_chronological_and_deterministic_for_reordered_input():
    c=codec()
    initial=value()
    v=replace(initial,evidence=(replace(initial.evidence[0],evidence_id='z-earliest'),
        replace(initial.evidence[1],evidence_id='a-later')))
    reordered=replace(v,evidence=v.evidence[::-1])
    first=c.reference_context(v)
    second=c.reference_context(reordered)
    assert first['evidence']==second['evidence']
    assert first['evidence'][0]=={'ref':'E01','excerpt':v.evidence[0].excerpt}
    assert first['request_origin_hash']!=second['request_origin_hash']
    for current,context in ((v,first),(reordered,second)):
        restored=json.loads(c.normalize_response(json.dumps(output()),current,request_origin_hash=context['request_origin_hash']))
        assert [row['evidence_id'] for row in restored['evidence']]==['z-earliest','a-later']



@pytest.mark.parametrize('attribute,changed',[('_REQUEST_PROFILE_VERSION','unknown'),('_CLOUD_PROFILE_ID','unknown'),
    ('_PROMPT_VERSION','unknown'),('_MODEL','other-model'),('_TIMEOUT_SECONDS',301)])
def test_unknown_v3_profile_refuses_before_credentials(monkeypatch,attribute,changed):
    v=value()
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(
        cloud_enabled=True,provider='zhipu_bigmodel',model='glm-4.7-flash',credential_available=True,
        provider_available=True,qualification_input_hash=v.semantic_hash),credential_resolver=lambda:pytest.fail('unknown profile key'))
    monkeypatch.setattr(type(adapter),attribute,changed)
    # Actual class request parameters must retain the exact frozen profile.
    assert not adapter.is_authorized_for_qualification(v)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        adapter.generate(v)


def test_oversized_complete_v3_request_rejects_without_truncation_or_key():
    v=value(1)
    text='Public synthetic oversized text. '*5000
    v=replace(v,evidence=(replace(v.evidence[0],excerpt=text,excerpt_hash=hashlib.sha256(text.encode()).hexdigest()),))
    adapter=d.BigModelGlm47FlashBoundEvidenceDistillationTransport(authorization=d.CloudDistillationAuthorization(
        cloud_enabled=True,provider='zhipu_bigmodel',model='glm-4.7-flash',credential_available=True,
        provider_available=True,qualification_input_hash=v.semantic_hash),credential_resolver=lambda:pytest.fail('oversize key'))
    with pytest.raises(d.CloudDistillationPreDispatchError):
        adapter.generate(v)
    assert v.evidence[0].excerpt==text


def test_v3_qualification_does_not_open_normal_budget_or_execution(tmp_path):
    from youtube_intel.runtime_composition import ProductionDistillationBudget
    support,repo,source,video,eid,service,calls,_=services(tmp_path)
    command,v=service._prospective_cloud_command(source_id=source,video_id=video,evidence_ids=(eid,))
    assert not ProductionDistillationBudget().check(command).allowed
    reserved=service.reserve_distillation_execution(source_id=source,video_id=video,evidence_ids=(eid,))
    support.service_support._permit(service,v)
    service.authorize_reserved_cloud_execution(reserved.execution_id,consent_kind='USER_CONFIRMATION')
    result=service.continue_reserved_distillation(reserved.execution_id)
    assert result.status.value=='WAITING_MODEL' and result.invocation_count==0 and not calls
    assert repo.can_cancel_waiting_model_execution(reserved.execution_id)


def test_v2_frozen_bytes_match_independent_prechange_source_baseline():
    from dataclasses import asdict
    support=_load_module('test_grounded_cloud_prompt_v2')
    v=support._profiled(support.adapter_support._input(),support.V2)
    def digest(item):
        return hashlib.sha256(json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert digest(asdict(v))=='da547a316dfd3af6634ddbe23f9cc339f66a513a14f4be777593af93028f27d2'
    assert digest(d.BigModelGlm47FlashGroundingV2DistillationTransport.profile_projection())=='d0819b95c5f5ca6f4c06d669b14e8e2c3e962ee28ed70164e47841dbf2470316'
    assert hashlib.sha256(d._bigmodel_request_bytes(d.BigModelGlm47FlashGroundingV2DistillationTransport._request(v))).hexdigest()=='462e6ed87d6e0b248df2c835ef98812a9fac0a6062bc41424eaf1023d2e16d87'


def test_legacy_v2_wrong_location_remains_rejected_without_reference_conversion(tmp_path):
    support,repo,source,video,eid,_,_,_=services(tmp_path)
    old=support._variant(repo,d.BigModelGlm47FlashGroundingV2DistillationTransport,[])
    command,v=old._prospective_cloud_command(source_id=source,video_id=video,evidence_ids=(eid,))
    payload={key:item for key,item in output().items() if key!='reference_protocol'}
    evidence=v.evidence[0]
    payload['evidence']=[{'evidence_id':evidence.evidence_id,'start_ms':evidence.start_ms,
        'end_ms':evidence.end_ms+1,'stance':'supporting'}]
    raw=json.dumps(payload)
    with pytest.raises(ValueError,match='evidence support is invalid'):
        old._parse_candidate(raw,command,v)
    assert json.loads(raw)==payload
