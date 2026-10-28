"""Pure, explicit request-bound reference representation; no admission authority."""
from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .distillation import VerifiedDistillationInput, VerifiedEvidenceInput

PROFILE_ID = 'bigmodel-glm-4.7-flash-thinking-json-bound-evidence-qualification-v3'
PROTOCOL = 'bound-evidence-reference-v1'
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_CLAIM_FIELDS = frozenset({'core_conclusion','user_relevant_information','important_new_information',
    'meaningful_details','filtered_noise','claim_kind','evidence'})
_CONTRACT = ('This version uses request-bound Evidence references. Every result must include '
    f'reference_protocol exactly {PROTOCOL}. Model output must never contain evidence_id, '
    'start_ms, end_ms, or other location fields. Select only the supplied short ref values. '
    'References select source records; they do not establish that a claim is true. '
    'All other grounding and admission requirements above remain applicable.')
_REPLACEMENTS = (
    ('meaningful_details, filtered_noise, claim_kind, evidence. core_conclusion',
     'meaningful_details, filtered_noise, claim_kind, evidence, reference_protocol. core_conclusion'),
    ('with exact evidence_id, start_ms, end_ms copied from the source payload and stance exactly supporting, contradicting, or conditional.',
     'using exactly ref and stance; ref must be a supplied short reference and stance exactly supporting, contradicting, or conditional.'),
    ('instead return exactly result=NO_NEW_INTELLIGENCE and evidence containing every supplied evidence_id, start_ms, and end_ms once, with no stance or claim fields.',
     f'instead return exactly result=NO_NEW_INTELLIGENCE, reference_protocol={PROTOCOL}, and evidence containing every supplied ref once, with no stance or claim fields.'),
)


def _json(value: object) -> str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def contract_projection() -> dict[str, object]:
    return {'reference_protocol':PROTOCOL,'alias_order':'trusted-start-end-id-order-v1',
        'request_origin_binding':'sha256-full-verified-input-projection-v1',
        'representation_sha256':hashlib.sha256(_json([_CONTRACT,_REPLACEMENTS]).encode()).hexdigest()}


def _ordered_evidence(value: VerifiedDistillationInput) -> tuple[VerifiedEvidenceInput, ...]:
    return tuple(sorted(value.evidence, key=lambda item: (item.start_ms, item.end_ms, item.evidence_id)))


def reference_context(value: VerifiedDistillationInput) -> dict[str, object]:
    from .distillation import (
        VerifiedEvidenceInput,
        _BoundEvidenceVerifiedDistillationInput,
        _cloud_source_allowed,
        verified_distillation_input_projection,
    )
    if (type(value) is not _BoundEvidenceVerifiedDistillationInput or value.cloud_profile_id != PROFILE_ID
        or not _cloud_source_allowed(value) or (value.selected_provider,value.selected_model) != ('zhipu_bigmodel','glm-4.7-flash')
        or re.fullmatch('[0-9a-f]{64}',value.semantic_hash) is None
        or not 1 <= len(value.evidence) <= 20 or len(set(value.evidence_ids)) != len(value.evidence)):
        raise ValueError('bound Evidence input identity is invalid')
    for item in value.evidence:
        if (type(item) is not VerifiedEvidenceInput or item.locator_type != 'TIMED_MEDIA'
            or not isinstance(item.evidence_id,str) or not item.evidence_id.strip() or len(item.evidence_id)>512
            or type(item.start_ms) is not int or type(item.end_ms) is not int
            or not 0 <= item.start_ms < item.end_ms <= 2**63-1
            or not isinstance(item.excerpt,str) or not item.excerpt.strip()
            or hashlib.sha256(item.excerpt.encode('utf-8')).hexdigest() != item.excerpt_hash
            or not isinstance(item.timed_transcript_id,str) or not item.timed_transcript_id.strip()
            or re.fullmatch('[0-9a-f]{64}',item.timed_transcript_hash) is None):
            raise ValueError('bound Evidence is invalid')
    origin=hashlib.sha256(_json(verified_distillation_input_projection(value)).encode('utf-8')).hexdigest()
    return {'request_origin_hash':origin,'reference_protocol':PROTOCOL,
        'evidence':[{'ref':f'E{i+1:02}','excerpt':item.excerpt} for i,item in enumerate(_ordered_evidence(value))]}


def prompt_messages(value: VerifiedDistillationInput, messages: list[dict[str,str]]) -> list[dict[str,str]]:
    """Change only the declared reference representation in fresh v2 messages."""
    context=reference_context(value)
    result=[dict(message) for message in messages]
    for old,new in _REPLACEMENTS:
        if result[0]['content'].count(old)!=1:
            raise ValueError('bound Evidence base contract differs')
        result[0]['content']=result[0]['content'].replace(old,new,1)
    result[0]['content']+='\n'+_CONTRACT
    source=json.loads(result[2]['content'].split('=',1)[1])
    source['evidence']=context['evidence']
    source['reference_protocol']=PROTOCOL
    # The origin hash is backend request provenance, never a model echo burden.
    result[2]['content']='UNTRUSTED_SOURCE_EVIDENCE='+_json(source)
    return result


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str,object]:
    result: dict[str,object]={}
    for key,item in pairs:
        if key in result:
            raise ValueError('duplicate bound response key')
        result[key]=item
    return result


def _reject_constant(_value: str) -> object:
    raise ValueError('nonfinite bound response')


def _text(value: object, maximum: int) -> None:
    if not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value)>maximum:
        raise ValueError('bound response text is invalid')


def normalize_response(raw: str, value: VerifiedDistillationInput, *, request_origin_hash: str) -> str:
    """Resolve only aliases from this request; the original validator still admits."""
    context=reference_context(value)
    if type(request_origin_hash) is not str or request_origin_hash!=context['request_origin_hash']:
        raise ValueError('bound response request origin differs')
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>_MAX_RESPONSE_BYTES:
        raise ValueError('bound response exceeds the existing response bound')
    try:
        payload=json.loads(raw,object_pairs_hook=_strict_object,parse_constant=_reject_constant)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('bound response JSON is invalid') from None
    if not isinstance(payload,dict) or payload.get('reference_protocol')!=PROTOCOL:
        raise ValueError('bound response protocol is invalid')
    no_new=payload.get('result')=='NO_NEW_INTELLIGENCE'
    expected={'reference_protocol','result','evidence'} if no_new else _CLAIM_FIELDS|{'reference_protocol'}
    if set(payload)!=expected:
        raise ValueError('bound response schema is invalid')
    if not no_new:
        _text(payload['core_conclusion'],4000)
        if not isinstance(payload['claim_kind'],str) or payload['claim_kind'] not in {'FACT','EVIDENCE_BACKED_STATEMENT','OPINION','PREDICTION','RUMOR','SYSTEM_INFERENCE'}:
            raise ValueError('bound claim kind is invalid')
        for key in ('user_relevant_information','important_new_information','meaningful_details','filtered_noise'):
            texts=payload[key]
            if not isinstance(texts,list) or len(texts)>20:
                raise ValueError('bound response information is invalid')
            for text in texts:
                _text(text,2000)
    citations=payload['evidence']
    if not isinstance(citations,list) or not 1 <= len(citations) <= len(value.evidence):
        raise ValueError('bound response references are invalid')
    mapping={f'E{i+1:02}':item for i,item in enumerate(_ordered_evidence(value))}
    cited: set[str]=set()
    resolved=[]
    for citation in citations:
        if not isinstance(citation,dict) or set(citation)!=({'ref'} if no_new else {'ref','stance'}):
            raise ValueError('bound response reference schema is invalid')
        ref=citation['ref']
        if not isinstance(ref,str) or ref not in mapping or ref in cited:
            raise ValueError('bound response reference is foreign or duplicate')
        cited.add(ref)
        item=mapping[ref]
        row: dict[str,object]={'evidence_id':item.evidence_id,'start_ms':item.start_ms,'end_ms':item.end_ms}
        if not no_new:
            stance=citation['stance']
            if not isinstance(stance,str) or stance not in {'supporting','contradicting','conditional'}:
                raise ValueError('bound response stance is invalid')
            row['stance']=stance
        resolved.append(row)
    if no_new and cited!=set(mapping):
        raise ValueError('bound NO_NEW Evidence set is incomplete')
    return _json({key:item for key,item in payload.items() if key!='reference_protocol'}|{'evidence':resolved})
