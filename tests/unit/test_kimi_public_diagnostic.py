"""Self-contained synthetic QA capsule tests; no actual source/key/network."""
from __future__ import annotations

import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any, cast

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    monkeypatch.setattr(socket, 'create_connection', lambda *_args, **_kwargs: pytest.fail('real network'))


@pytest.fixture
def qa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    path = Path(__file__).resolve().parents[2] / 'scripts/validation/kimi_public_diagnostic.py'
    spec = importlib.util.spec_from_file_location('kimi_qa', path)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class Clock:
        current = datetime(2026, 10, 29, 12, tzinfo=UTC)

        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return cls.current.astimezone(tz) if tz is not None else cls.current.replace(tzinfo=None)

        @staticmethod
        def fromisoformat(value: str) -> datetime:
            return datetime.fromisoformat(value)

    monkeypatch.setattr(module, 'datetime', Clock)
    monkeypatch.setattr(module.QACredentialStore, 'get', lambda *_: pytest.fail('Native credential access'))
    module.SOURCE = tmp_path / 'source'
    module.PACKAGE = tmp_path / 'package'
    module.LEDGER = tmp_path / 'outside-restore-ledger'
    module.SOURCE.mkdir()
    values = {
        'request-body.json': {'model': 'glm-4.7-flash', 'messages': [
            {'role': 'system', 'content': 'Return JSON with bound-evidence-reference-v1.'},
            {'role': 'user', 'content': 'Synthetic public facts only.'},
            {'role': 'user', 'content': 'Original public summary focus.'}]},
        'reference-context.json': {'public': True, 'reference_protocol': 'bound-evidence-reference-v1'},
        'verified-input.json': {'video_id': 'aircAruvnKk', 'output_language': 'zh'},
    }
    for name, value in values.items():
        (module.SOURCE / name).write_bytes(module.canonical(value))
    module.SOURCE_HASHES = {name: module.sha((module.SOURCE / name).read_bytes()) for name in values}
    module.DOCS = {'official.txt': tmp_path / 'official.txt'}
    module.DOCS['official.txt'].write_text('Synthetic official snapshot for offline test.')
    module.DOC_HASHES = {'official.txt': module.sha(module.DOCS['official.txt'].read_bytes())}
    return module


def approve(qa: Any) -> dict[str, Any]:
    prepared = qa.prepare()
    qa.write_once(qa.PACKAGE / 'review.json', qa.canonical({
        'decision': 'APPROVE', 'prepared_sha256': prepared['prepared_sha256'],
        'review_commit': 'a' * 40, 'reviewer': 'Root', 'max_calls': 1,
        'total_authorized_microunits': 8_000_000,
        'expires_at': (qa.datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
    }))
    return cast(dict[str, Any], prepared)


def envelope(qa: Any, *, final: str = '{ "reference_protocol": "bound-evidence-reference-v1", "claims": [] }',
             reasoning: str = 'Private analysis must never persist.', model: str | None = None,
             finish: str = 'stop', usage: dict[str, Any] | None = None) -> bytes:
    return cast(bytes, qa.canonical({'model': model or qa.MODEL, 'choices': [{
        'index': 0, 'finish_reason': finish,
        'message': {'role': 'assistant', 'content': final, 'reasoning_content': reasoning}}],
        'usage': usage or {'prompt_tokens': 12, 'completion_tokens': 14, 'total_tokens': 26,
                          'completion_tokens_details': {'reasoning_tokens': 10}}}))


def test_prepare_is_pure_and_wire_contract(qa: Any) -> None:
    before = {p.name: p.read_bytes() for p in qa.SOURCE.iterdir()}
    prepared = qa.prepare()
    wire = json.loads((qa.PACKAGE / 'request.json').read_bytes())
    original = json.loads(before['request-body.json'])
    assert wire['messages'] == original['messages']
    assert wire['model'] == 'kimi-k3.1-pro'
    assert wire['max_completion_tokens'] == 6144 and wire['reasoning_effort'] == 'low'
    assert wire['prompt_cache_options'] == {'mode': 'implicit', 'ttl': '5m'}
    assert not {'max_tokens', 'tools', 'temperature', 'top_p'} & wire.keys()
    assert prepared['reserve_microunits'] <= 1_000_000
    assert not qa.LEDGER.exists()
    assert before == {p.name: p.read_bytes() for p in qa.SOURCE.iterdir()}


def test_exact_raw_no_reasoning_or_sql_writes_and_no_replay(qa: Any, tmp_path: Path) -> None:
    approve(qa)
    sentinel = tmp_path / 'owner.sqlite'
    sentinel.write_bytes(b'never open this database')
    calls: list[str] = []
    raw = '{ "reference_protocol": "bound-evidence-reference-v1", "claims": [] }'
    def key() -> str:
        assert qa.reservation_path().is_file()  # durable authority precedes key
        calls.append('key')
        return 'synthetic-secret'
    def wire(body: bytes, secret: str) -> tuple[int, bytes]:
        assert secret == 'synthetic-secret' and json.loads(body)['model'] == qa.MODEL
        calls.append('wire')
        return 200, envelope(qa, final=raw)
    result = qa.execute(credential=key, wire=wire)
    assert result['status'] == 'PUBLIC_FINAL_REVIEW_ONLY'
    assert result['actual_bill'] == 'UNKNOWN'
    assert result['usage']['completion_tokens'] == 14  # includes reasoning; no double count
    assert qa.final_path().read_bytes() == raw.encode()
    assert b'Private analysis' not in b''.join(p.read_bytes() for p in qa.LEDGER.rglob('*') if p.is_file())
    assert qa.execute(credential=key, wire=wire) == result
    assert calls == ['key', 'wire'] and sentinel.read_bytes() == b'never open this database'


def test_concurrent_once_and_crash_reservation_no_replay(qa: Any) -> None:
    approve(qa)
    calls: list[int] = []
    def wire(body: bytes, secret: str) -> tuple[int, bytes]:
        calls.append(1)
        return 200, envelope(qa)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: qa.execute(credential=lambda: 'synthetic', wire=wire), range(2)))
    assert len(calls) == 1 and results[0] == results[1]
    qa.result_path().unlink()  # simulate lost finalization after durable reservation
    qa.final_path().unlink()
    result = qa.execute(credential=lambda: pytest.fail('replayed key'), wire=wire)
    assert result['status'] == 'RESERVED_UNKNOWN_STOP' and len(calls) == 1
    assert json.loads(qa.result_path().read_bytes()) == result


@pytest.mark.parametrize('change', ['source', 'request', 'profile', 'review', 'expired'])
def test_tamper_or_missing_review_refuses_before_key(qa: Any, change: str) -> None:
    approve(qa)
    if change == 'source':
        (qa.SOURCE / 'verified-input.json').write_text('{}')
    elif change == 'review':
        (qa.PACKAGE / 'review.json').unlink()
    elif change == 'expired':
        path = qa.PACKAGE / 'review.json'
        review = json.loads(path.read_bytes())
        review['expires_at'] = '2000-01-01T00:00:00+00:00'
        path.write_bytes(qa.canonical(review))
    else:
        (qa.PACKAGE / ('request.json' if change == 'request' else 'prepared.json')).write_text('{}')
    with pytest.raises(qa.Refused):
        qa.execute(credential=lambda: pytest.fail('key'), wire=lambda *_: pytest.fail('wire'))
    assert not qa.reservation_path().exists()


@pytest.mark.parametrize('size', [25_000, 40_000])
def test_over_budget_or_size_refused_without_key(qa: Any, size: int) -> None:
    path = qa.SOURCE / 'request-body.json'
    original = json.loads(path.read_bytes())
    original['messages'][0]['content'] = 'x' * size
    path.write_bytes(qa.canonical(original))
    qa.SOURCE_HASHES[path.name] = qa.sha(path.read_bytes())
    with pytest.raises(qa.Refused):
        qa.prepare()
    assert not qa.LEDGER.exists()


@pytest.mark.parametrize('bad', ['wrong_model', 'length', 'malformed', 'http429', 'usage', 'timeout', 'thought', 'bad_final',
                                 'literal_final', 'escaped_final', 'literal_reasoning', 'escaped_reasoning'])
def test_failed_response_stops_once_and_keeps_no_private_text(qa: Any, bad: str) -> None:
    approve(qa)
    secret = 'synthetic-private-key'
    calls: list[int] = []
    def wire(body: bytes, key: str) -> tuple[int, bytes]:
        calls.append(1)
        if bad == 'timeout':
            raise TimeoutError(secret)
        if bad == 'http429':
            return 429, qa.canonical({'error': {'message': secret}})
        if bad == 'malformed':
            return 200, b'{'
        kwargs: dict[str, Any] = {}
        if bad == 'wrong_model':
            kwargs['model'] = 'kimi-k2.6'
        if bad == 'length':
            kwargs['finish'] = 'length'
            kwargs['usage'] = {'prompt_tokens': 12, 'completion_tokens': 6144, 'total_tokens': 6156,
                               'completion_tokens_details': {'reasoning_tokens': 6000}}
        if bad == 'usage':
            kwargs['usage'] = {'prompt_tokens': 1, 'completion_tokens': 6145, 'total_tokens': 6146}
        if bad == 'thought':
            kwargs['final'] = '{"x":"<think>private</think>"}'
        if bad == 'bad_final':
            kwargs['final'] = '{"incomplete":'
        if bad.startswith(('literal_', 'escaped_')):
            value = secret if bad.startswith('literal') else ''.join('\\u%04x' % ord(c) for c in secret)
            kwargs['final' if bad.endswith('final') else 'reasoning'] = '{"x":"' + value + '"}'
        return 200, envelope(qa, **kwargs)
    result = qa.execute(credential=lambda: secret, wire=wire)
    assert result['status'].endswith('_STOP') and not qa.final_path().exists()
    assert qa.execute(credential=lambda: pytest.fail('replayed key'), wire=wire) == result
    stored = b''.join(p.read_bytes() for p in qa.LEDGER.rglob('*') if p.is_file())
    assert secret.encode() not in stored and b'Private analysis' not in stored
    assert len(calls) == 1 and result['actual_bill'] == 'UNKNOWN'
    if bad in ('length', 'usage', 'wrong_model', 'thought', 'bad_final'):
        assert result['status'] == 'OUTPUT_REJECTED_STOP'
        assert result['actual_model'] == ('kimi-k2.6' if bad == 'wrong_model' else qa.MODEL)
        assert result['finish_reason'] == ('length' if bad == 'length' else 'stop')
        assert result['usage']['completion_tokens'] == (6145 if bad == 'usage' else 6144 if bad == 'length' else 14)
        assert result['usage_validation'] == 'OBSERVED_NOT_ACCEPTED'
        if bad == 'length':
            assert result['usage']['reasoning_tokens'] == 6000
        assert result['failure_reason'] in {
            'FINISH_LENGTH', 'USAGE_OUT_OF_BOUND', 'MODEL_IDENTITY_INVALID', 'FINAL_INVALID'}
    if bad in ('malformed', 'timeout'):
        assert result['status'] == 'UNKNOWN_STOP'
    if bad.startswith(('literal_', 'escaped_')):
        assert result['status'] == 'UNKNOWN_STOP'
        assert not {'actual_model', 'finish_reason', 'usage', 'failure_reason'} & result.keys()


def test_copy_package_path_still_uses_external_once(qa: Any, tmp_path: Path) -> None:
    import shutil
    approve(qa)
    calls: list[int] = []
    def wire(body: bytes, key: str) -> tuple[int, bytes]:
        calls.append(1)
        return 429, b'{}'
    first = qa.execute(credential=lambda: 'synthetic', wire=wire)
    copied = tmp_path / 'copied-package'
    shutil.copytree(qa.PACKAGE, copied)
    qa.PACKAGE = copied
    assert qa.execute(credential=lambda: pytest.fail('key replay'), wire=wire) == first
    assert len(calls) == 1


@pytest.mark.parametrize('prior', ['unreviewed', 'failed', 'eight_reserved', 'bad_cost'])
def test_external_budget_and_prior_semantic_gate(qa: Any, prior: str) -> None:
    approve(qa)
    qa.LEDGER.mkdir()
    count = 8 if prior == 'eight_reserved' else 1
    for index in range(count):
        case = f'previous-{index}'
        cost = -1 if prior == 'bad_cost' else 1_000_000
        qa.write_once(qa.LEDGER / f'{case}.reservation.json', qa.canonical({
            'case': case, 'reserve_microunits': cost}))
        if prior == 'unreviewed':
            continue
        raw = b'{}'
        qa.write_once(qa.LEDGER / f'{case}.public-final.txt', raw)
        qa.write_once(qa.LEDGER / f'{case}.result.json', qa.canonical({
            'status': 'HTTP_ERROR_STOP' if prior == 'failed' else 'PUBLIC_FINAL_REVIEW_ONLY',
            'public_final_sha256': qa.sha(raw)}))
        qa.write_once(qa.LEDGER / f'{case}.semantic-pass.json', qa.canonical({
            'decision': 'PASS', 'reviewer': 'Root', 'public_final_sha256': qa.sha(raw)}))
    with pytest.raises(qa.Refused):
        qa.execute(credential=lambda: pytest.fail('key'), wire=lambda *_: pytest.fail('wire'))
    assert not qa.reservation_path().exists()


def test_post_reservation_tamper_stops_before_wire(qa: Any) -> None:
    approve(qa)
    def key() -> str:
        (qa.PACKAGE / 'request.json').write_text('{}')
        return 'synthetic'
    result = qa.execute(credential=key, wire=lambda *_: pytest.fail('wire'))
    assert result['status'] == 'PRE_SEND_STOP' and result['send_attempted'] is False
    assert qa.reservation_path().is_file() and not qa.final_path().exists()


def test_missing_key_burns_reserve_and_cannot_replay(qa: Any) -> None:
    approve(qa)
    result = qa.execute(credential=lambda: None, wire=lambda *_: pytest.fail('wire'))
    assert result['status'] == 'PRE_SEND_STOP'
    assert qa.execute(credential=lambda: pytest.fail('key replay'), wire=lambda *_: pytest.fail('wire')) == result


def test_decoder_missing_identity_duplicate_json_and_body_bound(qa: Any) -> None:
    prepared = approve(qa)
    good = json.loads(envelope(qa))
    del good['model']
    for body in (qa.canonical(good), b'{"model":"a","model":"b"}', b' ' * (qa.MAX_BODY + 1)):
        with pytest.raises((qa.Refused, KeyError)):
            qa.decoded(body, 'synthetic', prepared)


def test_fixture_denies_real_native_and_network(qa: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    monkeypatch.setattr(socket, 'create_connection', lambda *_args, **_kwargs: pytest.fail('network'))
    monkeypatch.setattr(qa.QACredentialStore, 'get', lambda *_: pytest.fail('Native'))
    approve(qa)
    assert qa.execute(credential=lambda: 'synthetic', wire=lambda *_: (200, envelope(qa)))['status'] == 'PUBLIC_FINAL_REVIEW_ONLY'


@pytest.mark.parametrize('status,oversize', [(302, False), (200, True)])
def test_fixed_http_wire_no_redirect_or_retry_bounded_tls(qa: Any, monkeypatch: pytest.MonkeyPatch,
                                                         status: int, oversize: bool) -> None:
    calls: list[tuple[Any, ...]] = []
    context = object()
    class Socket:
        def settimeout(self, timeout: float) -> None:
            assert 0 < timeout <= 300
        def shutdown(self, how: int) -> None:
            pass
    class Response:
        def __init__(self) -> None:
            self.status = status
            self.remaining = qa.MAX_BODY + 1 if oversize else 2
        def read1(self, amount: int) -> bytes:
            count = min(amount, self.remaining)
            self.remaining -= count
            return b'x' * count
    class Connection:
        def __init__(self, host: str, *, timeout: int, context: object) -> None:
            calls.append(('connect-config', host, timeout, context))
            self.sock: Socket | None = Socket()
            self.auto_open = 1
        def connect(self) -> None:
            calls.append(('TLS',))
        def request(self, method: str, path: str, *, body: bytes, headers: dict[str, str]) -> None:
            assert self.auto_open == 0
            calls.append(('request', method, path, body))
        def getresponse(self) -> Response:
            return Response()
        def close(self) -> None:
            self.sock = None
    monkeypatch.setattr(qa.ssl, 'create_default_context', lambda: context)
    monkeypatch.setattr(qa.http.client, 'HTTPSConnection', Connection)
    if oversize:
        with pytest.raises(qa.Refused):
            qa.http_wire(b'{}', 'synthetic')
    else:
        assert qa.http_wire(b'{}', 'synthetic') == (302, b'xx')
    assert calls[0] == ('connect-config', 'api.moonshot.cn', 300, context)
    assert [item for item in calls if item[0] == 'request'] == [('request', 'POST', '/v1/chat/completions', b'{}')]


def test_real_dotted_previous_case_pass_can_reserve_next(qa: Any) -> None:
    prepared = approve(qa)
    previous = qa.CASE
    assert previous == 'public-aircAruvnKk-zh-kimi-k3.1-pro'
    qa.LEDGER.mkdir()
    raw = b'{"original_public_final":true}'
    for suffix, value in {
        'reservation.json': {'case': previous, 'reserve_microunits': 952118},
        'result.json': {'status': 'PUBLIC_FINAL_REVIEW_ONLY', 'public_final_sha256': qa.sha(raw)},
        'semantic-pass.json': {'decision': 'PASS', 'reviewer': 'Root', 'public_final_sha256': qa.sha(raw)},
    }.items():
        qa.write_once(qa.LEDGER / f'{previous}.{suffix}', qa.canonical(value))
    qa.write_once(qa.LEDGER / f'{previous}.public-final.txt', raw)
    qa.CASE = 'fixed-next-public-case'
    with qa.locked():
        qa.reserve(prepared)
    assert json.loads(qa.reservation_path().read_bytes())['case'] == qa.CASE


@pytest.mark.parametrize('case', ['.', '..', '.hidden', '../escape', 'a/b', 'a\\b', 'a..b', 'a.'])
def test_prior_case_path_components_are_rejected(qa: Any, case: str) -> None:
    prepared = approve(qa)
    qa.LEDGER.mkdir()
    qa.write_once(qa.LEDGER / 'previous.reservation.json', qa.canonical({
        'case': case, 'reserve_microunits': 1}))
    with qa.locked(), pytest.raises(qa.Refused):
        qa.reserve(prepared)
    assert not qa.reservation_path().exists()


@pytest.mark.parametrize('field', ['model', 'finish', 'extra_usage'])
def test_secret_envelope_denied_before_any_metadata_observation(qa: Any, field: str) -> None:
    approve(qa)
    secret = 'synthetic-private-key'
    value = json.loads(envelope(qa, finish='length'))
    if field == 'model':
        value['model'] = secret
    elif field == 'finish':
        value['choices'][0]['finish_reason'] = secret
    else:
        value['usage']['untrusted_message'] = secret
    result = qa.execute(credential=lambda: secret, wire=lambda *_: (200, qa.canonical(value)))
    assert result['status'] == 'UNKNOWN_STOP'
    assert not {'actual_model', 'finish_reason', 'usage', 'failure_reason'} & result.keys()
    assert not qa.final_path().exists()
    assert secret not in qa.result_path().read_text()


def test_fixed_clock_next_day_refuses_prepare_and_execute_before_key(qa: Any) -> None:
    assert qa.datetime.now(UTC) == datetime(2026, 10, 29, 12, tzinfo=UTC)
    approve(qa)
    review = json.loads((qa.PACKAGE / 'review.json').read_bytes())
    assert review['expires_at'] == '2026-10-29T12:10:00+00:00'
    qa.datetime.current += timedelta(days=1)
    assert qa.datetime.now(UTC).date().isoformat() == '2026-10-30'
    assert qa.DATE == '2026-10-29'
    with pytest.raises(qa.Refused):
        qa.prepare()
    with pytest.raises(qa.Refused):
        qa.execute(credential=lambda: pytest.fail('next-day key'), wire=lambda *_: pytest.fail('next-day wire'))
    assert not qa.LEDGER.exists()
