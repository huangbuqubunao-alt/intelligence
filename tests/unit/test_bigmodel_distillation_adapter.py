"""Offline BigModel protocol fixtures, never provider or quality qualification."""

import hashlib
import json
from dataclasses import replace

import pytest

from youtube_intel import distillation as d

SECRET = "synthetic-bigmodel-secret"
REASONING = "private reasoning must not survive projection"


def _input(language="en"):
    return d.VerifiedDistillationInput(
        source_display_name="Public fixture",
        video_id="public-video",
        video_title="Fixture",
        evidence=(
            d.VerifiedEvidenceInput(
                "evidence-1",
                0,
                1000,
                "Exact public excerpt",
                "a" * 64,
                "timed-1",
                "b" * 64,
            ),
        ),
        personalization=("Task preference",),
        source_focus_rules=("focus",),
        source_ignore_rules=("ignore",),
        distillation_style="brief",
        selected_provider="zhipu_bigmodel",
        selected_model="glm-4.7-flash",
        semantic_hash="c" * 64,
        output_language=language,
    )


def _envelope():
    # Official BigModel response has no required OpenAI/Moonshot `object` member.
    return {
        "id": "offline",
        "model": "glm-4.7-flash",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"result":"NO_NEW_INTELLIGENCE"}',
                    "reasoning_content": REASONING,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 301,
            "completion_tokens": 77,
            "total_tokens": 378,
            "prompt_tokens_details": {"cached_tokens": 100},
        },
    }


def _transport(*, value=None, auth=None, calls=None, credential=SECRET):
    calls = [] if calls is None else calls

    def wire(request, key, timeout, retries):
        calls.append((request, key, timeout, retries))
        if isinstance(value, Exception):
            raise value
        return d._BigModelWireResponse(
            200, json.dumps(value if value is not None else _envelope()).encode()
        )

    return d.BigModelGlm47FlashDistillationTransport(
        authorization=auth
        or d.CloudDistillationAuthorization(
            cloud_enabled=True,
            provider="zhipu_bigmodel",
            model="glm-4.7-flash",
            credential_available=True,
            provider_available=True,
            qualification_input_hash=_input().semantic_hash,
        ),
        credential_resolver=lambda: credential,
        wire_transport=wire,
    )


@pytest.mark.parametrize("language", ["en", "zh-CN"])
def test_fixed_profile_preserves_all_shared_prompt_text_and_exact_evidence(language):
    request = d.BigModelGlm47FlashDistillationTransport._request(_input(language))
    assert request == {
        "endpoint_identity": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4.7-flash",
        "messages": d._distillation_prompt_messages(
            _input(language), task_role="system"
        ),
        "stream": False,
        "thinking": {"type": "enabled"},
        "max_tokens": 16384,
        "temperature": 1.0,
        "response_format": {"type": "json_object"},
        "max_retries": 0,
    }
    assert SECRET not in str(request)
    assert (
        hashlib.sha256(d._bigmodel_request_bytes(request)).hexdigest()
        == {
            "en": "012ef86eae4e73affb58cbc11e264603c59d70f97068d1aafead3541653723aa",
            "zh-CN": "a9fc99051d607d57dd93f4d1c6fbcc61269ad70fc9af7dc28ebd065fa66952b4",
        }[language]
    )
    calls = []
    result = _transport(calls=calls).generate(_input(language))
    assert len(calls) == 1 and calls[0][2:] == (300.0, 0)
    assert (result.actual_provider, result.actual_model) == (
        "zhipu_bigmodel",
        "glm-4.7-flash",
    )
    assert (result.input_tokens, result.output_tokens, result.cost_microunits) == (
        301,
        77,
        None,
    )
    assert REASONING not in repr(result) and SECRET not in repr(result)


@pytest.mark.parametrize(
    "change",
    ["provider", "model", "hash", "disabled", "calls", "boolean-calls", "normal"],
)
def test_denied_permission_resolves_no_credential_and_calls_no_wire(change):
    fields = dict(
        cloud_enabled=True,
        provider="zhipu_bigmodel",
        model="glm-4.7-flash",
        credential_available=True,
        provider_available=True,
        qualification_input_hash="c" * 64,
    )
    if change == "provider":
        fields["provider"] = "moonshot"
    if change == "model":
        fields["model"] = "glm-4.7-flashx"
    if change == "hash":
        fields["qualification_input_hash"] = "d" * 64
    if change == "disabled":
        fields["cloud_enabled"] = False
    if change == "calls":
        fields["qualification_max_calls"] = 2
    if change == "boolean-calls":
        fields["qualification_max_calls"] = True
    auth = d.CloudDistillationAuthorization(**fields)
    if change == "normal":
        eligibility = d.M12QualifiedCloudProductionAuthorizationAuthority.resolve(
            provider="zhipu_bigmodel",
            model="glm-4.7-flash",
            capability_scope=d.DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
            available=True,
        )
        assert not eligibility.qualified and not eligibility.production_eligible
        auth = d.CloudDistillationAuthorization.for_normal_production(
            eligibility=eligibility, cloud_enabled=True, credential_available=True
        )
    calls = []
    transport = _transport(auth=auth, calls=calls)
    transport._credential_resolver = lambda: pytest.fail(
        "denial must precede credential lookup"
    )
    assert not transport.is_authorized_for_normal_production(_input())
    with pytest.raises(d.CloudDistillationPreDispatchError):
        transport.generate(_input())
    assert calls == []


@pytest.mark.parametrize(
    "provider,video",
    [
        ("LOCAL", "public-video"),
        ("BILIBILI", "public-video"),
        ("YOUTUBE", "local-" + "a" * 64),
    ],
)
def test_private_or_unsupported_source_is_denied_before_credential(provider, video):
    value = replace(_input(), content_provider=provider, video_id=video)
    transport = _transport()
    transport._credential_resolver = lambda: pytest.fail(
        "source denial must precede credential"
    )
    with pytest.raises(d.CloudDistillationPreDispatchError):
        transport.generate(value)
    with pytest.raises(d.CloudDistillationPreDispatchError):
        transport._request(value)


@pytest.mark.parametrize(
    "credential", ["", "bad\nheader", "bad\rheader", "bad space", "密钥", None]
)
def test_invalid_credentials_never_reach_wire(credential):
    calls = []
    with pytest.raises(d.CloudDistillationPreDispatchError):
        _transport(calls=calls, credential=credential).generate(_input())
    assert calls == []


def test_request_bound_is_utf8_and_does_not_truncate_evidence():
    value = replace(
        _input(), evidence=(replace(_input().evidence[0], excerpt="字" * 45000),)
    )
    calls = []
    with pytest.raises(d.CloudDistillationPreDispatchError):
        _transport(calls=calls).generate(value)
    assert calls == []


@pytest.mark.parametrize(
    "case",
    [
        "missing-model",
        "wrong-model",
        "nonstring-model",
        "multi",
        "role",
        "tool",
        "audio",
        "empty",
        "length",
        "finish",
        "content-json",
        "duplicate-json",
        "usage-bool",
        "usage-negative",
        "usage-float",
        "usage-cache",
        "usage-total",
    ],
)
def test_malformed_identity_terminal_content_and_usage_are_known_safe_failures(case):
    value = _envelope()
    choice = value["choices"][0]
    message = choice["message"]
    if case == "missing-model":
        value.pop("model")
    if case == "wrong-model":
        value["model"] = SECRET + REASONING
    if case == "nonstring-model":
        value["model"] = 7
    if case == "multi":
        value["choices"].append(choice.copy())
    if case == "role":
        message["role"] = "tool"
    if case == "tool":
        message["tool_calls"] = [{"function": {"arguments": REASONING}}]
    if case == "audio":
        message["audio"] = {"data": REASONING}
    if case == "empty":
        message["content"] = " "
    if case == "length":
        choice["finish_reason"] = "length"
    if case == "finish":
        choice["finish_reason"] = "tool_calls"
    if case == "content-json":
        message["content"] = "not JSON"
    if case == "duplicate-json":
        message["content"] = '{"result":1,"result":2}'
    if case == "usage-bool":
        value["usage"]["prompt_tokens"] = True
    if case == "usage-negative":
        value["usage"]["completion_tokens"] = -1
    if case == "usage-float":
        value["usage"]["completion_tokens"] = 1.2
    if case == "usage-cache":
        value["usage"]["prompt_tokens_details"]["cached_tokens"] = False
    if case == "usage-total":
        value["usage"]["total_tokens"] = 1
    calls = []
    with pytest.raises(d.KnownCloudDistillationResponseError) as raised:
        _transport(value=value, calls=calls).generate(_input())
    assert len(calls) == 1
    assert SECRET not in str(raised.value) and REASONING not in repr(
        raised.value.result
    )
    if raised.value.result is not None:
        assert raised.value.result.raw == ""


def test_missing_usage_remains_unknown_not_zero_or_public_token_count():
    value = _envelope()
    value.pop("usage")
    result = _transport(value=value).generate(_input())
    assert (
        result.input_tokens is None
        and result.output_tokens is None
        and result.cost_microunits is None
    )


class _Socket:
    def __init__(self):
        self.timeouts = []
        self.shutdowns = []

    def settimeout(self, value):
        self.timeouts.append(value)

    def shutdown(self, value):
        self.shutdowns.append(value)


class _Connection:
    def __init__(self, payload, status=200):
        self.sock = _Socket()
        self.payload = payload
        self.status = status
        self.requests = []
        self.closed = 0
        self.reads = 0
        self.failure = None

    def connect(self):
        pass

    def request(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        if self.failure:
            raise self.failure

    def getresponse(self):
        return self

    def read1(self, size):
        self.reads += 1
        chunk, self.payload = self.payload[:size], self.payload[size:]
        return chunk

    def close(self):
        self.closed += 1


def _fake_connection(monkeypatch, connection):
    prepared = []

    def create(host, *, timeout, context):
        prepared.append((host, timeout, context))
        return connection

    monkeypatch.setattr(d, "HTTPSConnection", create)
    return prepared


def _send():
    return d._bigmodel_chat_completions_http_transport(
        d.BigModelGlm47FlashDistillationTransport._request(_input()), SECRET, 300.0, 0
    )


def test_native_wire_uses_fixed_host_path_standard_tls_bearer_header_and_bounded_reads(
    monkeypatch,
):
    import ssl

    connection = _Connection(json.dumps(_envelope()).encode())
    prepared = _fake_connection(monkeypatch, connection)
    response = _send()
    host, timeout, context = prepared[0]
    assert host == "open.bigmodel.cn" and timeout == 300.0
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    args, kwargs = connection.requests[0]
    assert args == ("POST", "/api/paas/v4/chat/completions")
    assert kwargs["headers"]["Authorization"] == "Bearer " + SECRET
    assert SECRET.encode() not in kwargs["body"]
    body = json.loads(kwargs["body"])
    assert "endpoint_identity" not in body and "max_retries" not in body
    assert len(connection.requests) == 1 and connection.closed
    assert response.http_status == 200 and REASONING not in repr(response)
    assert all(0 < value <= 300 for value in connection.sock.timeouts)


@pytest.mark.parametrize("status", [301, 307, 401, 429, 500, 202])
def test_native_wire_never_follows_redirects_or_retries_known_or_async_responses(
    monkeypatch, status
):
    connection = _Connection(SECRET.encode(), status)
    _fake_connection(monkeypatch, connection)
    error = (
        d.AmbiguousCloudDistillationResponseError
        if status == 202
        else d.KnownCloudDistillationResponseError
    )
    with pytest.raises(error) as raised:
        _send()
    assert raised.value.http_status == status
    assert len(connection.requests) == 1 and connection.reads == 0 and connection.closed
    assert SECRET not in str(raised.value)


@pytest.mark.parametrize(
    "failure", [TimeoutError(SECRET), ConnectionResetError(SECRET)]
)
def test_post_started_failure_is_ambiguous_with_no_replay_or_secret(
    monkeypatch, failure
):
    connection = _Connection(b"")
    connection.failure = failure
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.AmbiguousCloudDistillationResponseError) as raised:
        _send()
    assert len(connection.requests) == 1 and connection.closed
    assert SECRET not in str(raised.value)


def test_absolute_read_deadline_cannot_be_extended_by_successful_small_reads(
    monkeypatch,
):
    now = [0.0]
    monkeypatch.setattr(d.time, "monotonic", lambda: now[0])
    connection = _Connection(b"x" * 100)

    def drip(size):
        now[0] += 150.1
        return b"x"

    connection.read1 = drip
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.AmbiguousCloudDistillationResponseError) as raised:
        _send()
    assert raised.value.http_status == 200 and now[0] < 451
    assert len(connection.requests) == 1 and connection.closed


def test_watchdog_interrupts_stalled_headers_and_does_not_expose_error_body(
    monkeypatch,
):
    timers = []

    class Timer:
        def __init__(self, timeout, callback):
            assert timeout == 300.0
            self.callback = callback
            self.cancelled = False
            timers.append(self)

        def start(self):
            pass

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(d.threading, "Timer", Timer)
    connection = _Connection(b"")

    def headers():
        timers[0].callback()
        return connection

    connection.getresponse = headers
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.AmbiguousCloudDistillationResponseError):
        _send()
    assert connection.sock.shutdowns and connection.closed and timers[0].cancelled


def test_response_byte_limit_rejects_without_parsing_private_body(monkeypatch):
    connection = _Connection(
        b"x" * (d.BigModelGlm47FlashDistillationTransport._MAX_RESPONSE_BYTES + 1)
    )
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.KnownCloudDistillationResponseError):
        _send()
    assert (
        connection.closed and connection.reads <= 33 and len(connection.requests) == 1
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint_identity", "https://other.invalid/"),
        ("tools", []),
        ("stream", True),
        ("model", "glm-4.7-flashx"),
        ("max_retries", 1),
    ],
)
def test_native_policy_rejects_mutated_projection_before_connection(
    monkeypatch, field, value
):
    monkeypatch.setattr(
        d,
        "HTTPSConnection",
        lambda *a, **k: pytest.fail("must reject before connection"),
    )
    request = d.BigModelGlm47FlashDistillationTransport._request(_input())
    request[field] = value
    with pytest.raises(d.CloudDistillationPreDispatchError):
        d._bigmodel_chat_completions_http_transport(request, SECRET, 300.0, 0)


def test_connect_failure_is_known_before_any_http_bytes_and_cannot_reconnect(
    monkeypatch,
):
    connection = _Connection(b"")

    def refused():
        raise ConnectionRefusedError(SECRET)

    connection.connect = refused
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.CloudDistillationPreDispatchError) as raised:
        _send()
    assert connection.requests == [] and connection.auto_open == 0 and connection.closed
    assert SECRET not in str(raised.value)


def test_dns_deadline_returns_without_post_even_when_resolver_finishes_later(
    monkeypatch,
):
    import threading

    release = threading.Event()
    finished = threading.Event()
    connection = _Connection(b"")

    def delayed_connect():
        release.wait(2)
        finished.set()

    connection.connect = delayed_connect
    _fake_connection(monkeypatch, connection)
    monkeypatch.setattr(
        d.BigModelGlm47FlashDistillationTransport, "_TIMEOUT_SECONDS", 0.02
    )
    with pytest.raises(d.CloudDistillationPreDispatchError):
        d._bigmodel_chat_completions_http_transport(
            d.BigModelGlm47FlashDistillationTransport._request(_input()),
            SECRET,
            0.02,
            0,
        )
    assert connection.requests == []
    release.set()
    assert finished.wait(1)
    assert connection.requests == [] and connection.closed


def test_incomplete_declared_body_is_ambiguous_even_if_prefix_is_valid_json(
    monkeypatch,
):
    connection = _Connection(json.dumps(_envelope()).encode())
    connection.length = 5000
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.AmbiguousCloudDistillationResponseError) as raised:
        _send()
    assert raised.value.http_status == 200 and len(connection.requests) == 1


def test_watchdog_keeps_authority_over_detached_response_socket(monkeypatch):
    timers = []

    class Timer:
        def __init__(self, timeout, callback):
            self.callback = callback
            timers.append(self)

        def start(self):
            pass

        def cancel(self):
            pass

    monkeypatch.setattr(d.threading, "Timer", Timer)
    connection = _Connection(b"")
    original_socket = connection.sock

    def detached_headers():
        connection.sock = None
        return connection

    def delayed_read(size):
        timers[0].callback()
        return b""

    connection.getresponse = detached_headers
    connection.read1 = delayed_read
    _fake_connection(monkeypatch, connection)
    with pytest.raises(d.AmbiguousCloudDistillationResponseError):
        _send()
    assert (
        original_socket.shutdowns
        and connection.closed
        and len(connection.requests) == 1
    )


@pytest.mark.parametrize(
    "body",
    [
        b"{",
        b"\xff",
        b"[]",
        b'{"model":"glm-4.7-flash","model":"other"}',
        b"x" * (2 * 1024 * 1024 + 1),
    ],
)
def test_malformed_response_bytes_cannot_expose_private_output(body):
    with pytest.raises(d.KnownCloudDistillationResponseError) as raised:
        d.BigModelGlm47FlashDistillationTransport._decode(
            d._BigModelWireResponse(200, body), 1
        )
    assert raised.value.result is None
