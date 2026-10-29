"""Fixed public Kimi QA diagnostic; never production admission or qualification.

Root alone prepares/reviews/executes. No retries, continuation, alternate models,
SQL writes or environment credentials. One durable reservation burns its reserve
on every outcome. Input-byte + 2048 framing estimate is NOT a billing guarantee.

ADAPT: canonical/write_once and final privacy checks from the accepted public
capsule helpers (repository MIT); independent Kimi wire and outside-Restore once.
"""
from __future__ import annotations

import fcntl
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel.model_settings import MacOSKeychainCredentialStore

ROOT = Path('/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness')
SOURCE = ROOT / '.var/end-to-end-user-readiness/bigmodel-reference-v3-public-zh-20261029'
PACKAGE = Path(__file__).resolve().parents[2] / '.var/kimi-public-diagnostic/package'
# Fixed across copied packages/worktrees; never inside a restorable product root.
LEDGER = ROOT / '.var/end-to-end-user-readiness/kimi-public-20261029-ledger'
MODEL = 'kimi-k3.1-pro'
CASE = 'public-aircAruvnKk-zh-kimi-k3.1-pro'
DATE = '2026-10-29'
MAX_OUTPUT = 6144
MAX_BODY = 2 * 1024 * 1024
SOURCE_HASHES = {
    'request-body.json': 'b876f872eb163d7c2e248d2241a25106ff30d161008a1b8d6345f09e15f4f356',
    'reference-context.json': '98981ad65f74ebeafd8dde1a9c367a665a0ebe58a965cdf79f3c7171c0b455bf',
    'verified-input.json': '709a8d518469d00ec8e9b3e6d943a8b1f7162d147094ac784320328255a2109c',
}
DOCS = {name: Path('/tmp') / name for name in (
    'intelligence-kimi31-model-20261029.txt', 'intelligence-kimi-chat-20261029.txt',
    'intelligence-kimi-pricing-20261029.txt')}
DOC_HASHES = dict(zip(DOCS, (
    '0ed8094de8dedd0ae4dd1912e92c6d385e1a79e83313c1f82686d7943a5d6df1',
    '7a1e692601a4a00628fbbd88c2561df485f2505a933c0841c9015ffaa6bc32c6',
    '921983646fa6f233bbe0a6275bf48c2fa594d124e6377d596986a16aab96569b'), strict=True))
PROFILE = {
    'id': 'qa-kimi-k31-public-bound-reference-v3-20261029', 'model': MODEL,
    'endpoint': 'https://api.moonshot.cn/v1/chat/completions',
    'reasoning_effort': 'low', 'max_completion_tokens': MAX_OUTPUT,
    'stream': False, 'response_format': {'type': 'json_object'},
    'prompt_cache_options': {'mode': 'implicit', 'ttl': '5m'},
    'deadline_seconds': 300, 'retries': 0, 'input_cny_per_million_worst': 26,
    'output_cny_per_million': 68, 'framing_token_assumption': 2048,
    'billing_guarantee': False, 'diagnostic_only': True,
}
THOUGHT = re.compile(r'<\s*/?\s*(?:think|analysis|reasoning)\b|<\|(?:analysis|thinking)|PRIVATE_REASONING_MARKER', re.I)


class Refused(ValueError):
    def __init__(self) -> None:
        super().__init__('diagnostic refused; preserve package and external ledger')


def require(condition: object) -> None:
    if not condition:
        raise Refused()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def parse(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Refused()))
    except (UnicodeError, ValueError, RecursionError):
        raise Refused() from None


def read(path: Path, bound: int = MAX_BODY) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            require(os.fstat(stream.fileno()).st_size <= bound)
            raw = stream.read(bound + 1)
        require(len(raw) <= bound)
        return raw
    except OSError:
        raise Refused() from None


def write_once(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def code_hashes() -> dict[str, str]:
    project = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), *sorted((project / 'src').rglob('*.py'))]
    return {str(path.relative_to(project)): sha(read(path)) for path in paths}


def snapshot() -> tuple[dict[str, bytes], dict[str, Any], bytes]:
    require(datetime.now(UTC).date().isoformat() == DATE)
    files = {name: read(SOURCE / name) for name in SOURCE_HASHES}
    require({name: sha(raw) for name, raw in files.items()} == SOURCE_HASHES)
    documents = {name: read(path) for name, path in DOCS.items()}
    require({name: sha(raw) for name, raw in documents.items()} == DOC_HASHES)
    original = parse(files['request-body.json'])
    messages = original['messages']
    require(isinstance(messages, list) and len(messages) == 3)
    for message in messages:
        require(isinstance(message, dict) and set(message) == {'role', 'content'})
        require(message['role'] in ('system', 'user') and isinstance(message['content'], str))
    wire = canonical({'model': MODEL, 'messages': messages,
                      **{key: PROFILE[key] for key in ('reasoning_effort', 'max_completion_tokens',
                         'stream', 'response_format', 'prompt_cache_options')}})
    input_bound = sum(len(message['content'].encode()) for message in messages) + 2048
    reserve = input_bound * 26 + MAX_OUTPUT * 68
    require(len(wire) <= 32768 and reserve <= 1_000_000)
    frozen = {'case': CASE, 'date': DATE, 'profile': PROFILE, 'source': SOURCE_HASHES,
              'official_documents': DOC_HASHES, 'code': code_hashes(),
              'wire_sha256': sha(wire), 'input_token_bound_assumption': input_bound,
              'reserve_microunits': reserve,
              'origin_sha256': sha(canonical({'target_profile': PROFILE, 'source': SOURCE_HASHES,
                                            'wire_sha256': sha(wire)}))}
    files.update(documents)
    frozen['prepared_sha256'] = sha(canonical(frozen))
    return files, frozen, wire


def prepare() -> dict[str, Any]:
    files, frozen, wire = snapshot()
    PACKAGE.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not PACKAGE.is_symlink())
    for name, raw in {**files, 'request.json': wire, 'prepared.json': canonical(frozen)}.items():
        path = PACKAGE / name
        if path.exists():
            require(read(path) == raw)
        else:
            write_once(path, raw)
    return frozen


def validated() -> tuple[dict[str, Any], bytes]:
    files, frozen, wire = snapshot()
    require(read(PACKAGE / 'prepared.json') == canonical(frozen))
    require(read(PACKAGE / 'request.json') == wire)
    for name, raw in files.items():
        require(read(PACKAGE / name) == raw)
    approval = parse(read(PACKAGE / 'review.json'))
    require(isinstance(approval, dict) and set(approval) == {
        'decision', 'prepared_sha256', 'review_commit', 'reviewer', 'max_calls',
        'total_authorized_microunits', 'expires_at'})
    require(approval['decision'] == 'APPROVE' and approval['reviewer'] == 'Root'
            and approval['prepared_sha256'] == frozen['prepared_sha256']
            and approval['max_calls'] == 1 and approval['total_authorized_microunits'] == 8_000_000
            and re.fullmatch('[0-9a-f]{40}', approval['review_commit']) is not None)
    try:
        expires = datetime.fromisoformat(approval['expires_at'])
        require(expires.utcoffset() is not None and datetime.now(UTC) < expires)
    except (ValueError, TypeError):
        raise Refused() from None
    return frozen, wire


def reservation_path() -> Path:
    return LEDGER / f'{CASE}.reservation.json'


def result_path() -> Path:
    return LEDGER / f'{CASE}.result.json'


def final_path() -> Path:
    return LEDGER / f'{CASE}.public-final.txt'


@contextmanager
def locked() -> Iterator[None]:
    LEDGER.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not LEDGER.is_symlink())
    parent = os.open(LEDGER.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    fd = os.open(LEDGER / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def reserve(frozen: dict[str, Any]) -> None:
    previous = sorted(LEDGER.glob('*.reservation.json'))
    total = 0
    for path in previous:
        value = parse(read(path))
        cost = value['reserve_microunits']
        require(type(cost) is int and 0 < cost <= 1_000_000)
        total += cost
        # No subsequent case after any unreviewed, failed or unknown attempt.
        case = value['case']
        require(isinstance(case, str) and re.fullmatch(r'[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*', case))
        result = parse(read(LEDGER / f'{case}.result.json'))
        semantic = parse(read(LEDGER / f'{case}.semantic-pass.json'))
        require(result['status'] == 'PUBLIC_FINAL_REVIEW_ONLY' and semantic == {
            'decision': 'PASS', 'reviewer': 'Root', 'public_final_sha256': result['public_final_sha256']})
        require(sha(read(LEDGER / f'{case}.public-final.txt')) == result['public_final_sha256'])
    require(len(previous) < 8 and total + frozen['reserve_microunits'] <= 8_000_000)
    write_once(reservation_path(), canonical({
        'case': CASE, 'model': MODEL, 'prepared_sha256': frozen['prepared_sha256'],
        'reserve_microunits': frozen['reserve_microunits'], 'created_at': datetime.now(UTC).isoformat(),
        'bill': 'UNKNOWN', 'replay': 'FORBIDDEN'}))


class QACredentialStore(MacOSKeychainCredentialStore):
    _service = b'com.huangbuqubunao.intelligence.qa.kimi-public-20261029'
    _account = b'api-key'


def http_wire(body: bytes, secret: str) -> tuple[int, bytes]:
    """Exactly one POST; watchdog bounds connect/read including late DNS completion.

    A late connector may finish TLS, but only the caller can send HTTP bytes, and
    it cannot do so after the absolute deadline. Never redirects or retries.
    """
    deadline = time.monotonic() + 300
    connection = http.client.HTTPSConnection('api.moonshot.cn', timeout=300,
                                             context=ssl.create_default_context())
    connection.auto_open = 0  # a deadline-close must never trigger implicit reconnect
    sockets: list[socket.socket] = []
    connected = threading.Event()
    expired = threading.Event()
    errors: list[Exception] = []
    def close() -> None:
        expired.set()
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()
    def connect() -> None:
        try:
            connection.connect()
            if connection.sock is not None:
                sockets.append(connection.sock)
        except Exception as error:
            errors.append(error)
        finally:
            if expired.is_set():
                connection.close()
            connected.set()
    watchdog = threading.Timer(300, close)
    watchdog.daemon = True
    connector = threading.Thread(target=connect, daemon=True)
    watchdog.start()
    connector.start()
    try:
        require(connected.wait(max(0, deadline - time.monotonic())) and not errors
                and not expired.is_set() and time.monotonic() < deadline)
        assert connection.sock is not None
        connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
        connection.request('POST', '/v1/chat/completions', body=body,
                           headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret})
        response = connection.getresponse()
        chunks: list[bytes] = []
        count = 0
        while True:
            require(not expired.is_set() and time.monotonic() < deadline)
            if connection.sock is not None:
                connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
            chunk = response.read1(min(65536, MAX_BODY + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            require(count <= MAX_BODY)
        require(not expired.is_set() and time.monotonic() < deadline)
        return response.status, b''.join(chunks)
    finally:
        expired.set()
        watchdog.cancel()
        connection.close()


def strings(value: Any) -> Iterator[str]:
    stack = [value]
    for _ in range(100_000):
        if not stack:
            return
        item = stack.pop()
        if isinstance(item, str):
            yield item
            # Scan escaped literals even inside a JSON string (including reasoning).
            decoded = re.sub(r'\\u[0-9a-fA-F]{4}', lambda match: chr(int(match[0][2:], 16)), item)
            if decoded != item:
                yield decoded
        elif isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    raise Refused()


class ObservedOutputRejected(Refused):
    def __init__(self, observation: dict[str, Any]) -> None:
        super().__init__()
        self.observation = observation


def safe_observation(value: Any) -> dict[str, Any]:
    """Finite QA observations, never accepted accounting or spending authority.

    Called only AFTER the complete parsed envelope passed all secret checks.
    Unknown keys/text and invalid or unbounded counters are never reflected.
    """
    observation: dict[str, Any] = {}
    if not isinstance(value, dict):
        return observation
    model = value.get('model')
    if isinstance(model, str) and re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', model):
        observation['actual_model'] = model
    choices = value.get('choices')
    if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
        finish = choices[0].get('finish_reason')
        if isinstance(finish, str) and finish in ('stop', 'length', 'tool_calls', 'function_call', 'content_filter', 'error'):
            observation['finish_reason'] = finish
    usage = value.get('usage')
    if isinstance(usage, dict):
        counters: dict[str, int] = {}
        for source, keys in (
            (usage, ('prompt_tokens', 'completion_tokens', 'total_tokens')),
            (usage.get('prompt_tokens_details'), ('cached_tokens', 'cache_write_tokens')),
            (usage.get('completion_tokens_details'), ('reasoning_tokens',)),
        ):
            if isinstance(source, dict):
                for key in keys:
                    number = source.get(key)
                    if type(number) is int and 0 <= number <= 2**31 - 1:
                        counters[key] = number
        if counters:
            observation['usage'] = counters
            observation['usage_validation'] = 'OBSERVED_NOT_ACCEPTED'
    return observation


def decoded(body: bytes, secret: str, frozen: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    require(len(body) <= MAX_BODY)
    value = parse(body)
    # No model/finish/usage observation can escape before full secret checking.
    require(all(secret not in text for text in strings(value)))
    observation = safe_observation(value)
    try:
        observation['failure_reason'] = 'MODEL_IDENTITY_INVALID'
        require(value['model'] == MODEL)
        observation['failure_reason'] = 'ENVELOPE_INVALID'
        choices = value['choices']
        require(isinstance(choices, list) and len(choices) == 1)
        choice = choices[0]
        observation['failure_reason'] = 'FINISH_LENGTH' if choice.get('finish_reason') == 'length' else 'FINISH_REASON_INVALID'
        require(choice['index'] == 0 and choice['finish_reason'] == 'stop')
        observation['failure_reason'] = 'FINAL_INVALID'
        message = choice['message']
        require(message['role'] == 'assistant' and not message.get('tool_calls') and not message.get('function_call'))
        raw = message['content']
        require(isinstance(raw, str) and bool(raw.strip()) and len(raw.encode()) <= MAX_BODY)
        final = parse(raw.encode())
        require(isinstance(final, dict) and all(not THOUGHT.search(text) and secret not in text
                                              for text in strings([raw, final])))
        observation['failure_reason'] = 'USAGE_INVALID'
        usage = value['usage']
        safe: dict[str, Any] = {}
        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            require(type(usage[key]) is int and usage[key] >= 0)
            safe[key] = usage[key]
        observation['failure_reason'] = 'USAGE_OUT_OF_BOUND'
        require(0 < safe['prompt_tokens'] <= frozen['input_token_bound_assumption']
                and 0 < safe['completion_tokens'] <= MAX_OUTPUT
                and safe['total_tokens'] == safe['prompt_tokens'] + safe['completion_tokens'])
        details = usage.get('prompt_tokens_details', {})
        require(isinstance(details, dict))
        for key in ('cached_tokens', 'cache_write_tokens'):
            number = details.get(key, 0)
            require(type(number) is int and number >= 0)
            safe[key] = number
        require(safe['cached_tokens'] + safe['cache_write_tokens'] <= safe['prompt_tokens'])
        reasoning = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)
        require(type(reasoning) is int and 0 <= reasoning <= safe['completion_tokens'])
        safe['reasoning_tokens_included'] = reasoning
        safe['worst_cost_microunits'] = safe['prompt_tokens'] * 26 + safe['completion_tokens'] * 68
        require(safe['worst_cost_microunits'] <= frozen['reserve_microunits'])
        return raw, safe
    except Exception:
        raise ObservedOutputRejected(observation) from None


def execute(*, credential: Callable[[], str | None] | None = None,
            wire: Callable[[bytes, str], tuple[int, bytes]] = http_wire) -> dict[str, Any]:
    frozen, body = validated()
    with locked():
        if reservation_path().exists():
            if result_path().exists():
                result: dict[str, Any] = parse(read(result_path()))
                return result
            recovered = {'case': CASE, 'status': 'RESERVED_UNKNOWN_STOP', 'actual_bill': 'UNKNOWN'}
            write_once(result_path(), canonical(recovered))
            return recovered
        reserve(frozen)  # durable fsync BEFORE any credential resolution or send
        result = {'case': CASE, 'model': MODEL, 'status': 'UNKNOWN_STOP', 'actual_bill': 'UNKNOWN',
                  'reserve_microunits': frozen['reserve_microunits'], 'send_attempted': False}
        try:
            validated()  # package/source/code/approval cannot drift after reservation
            secret = (credential or QACredentialStore().get)()
            require(isinstance(secret, str) and bool(secret) and '\r' not in secret and '\n' not in secret)
            assert isinstance(secret, str)
            validated()  # a key callback cannot replace the frozen outgoing body
            result['send_attempted'] = True
            status, response = wire(body, secret)
            require(type(status) is int and 100 <= status <= 599 and len(response) <= MAX_BODY)
            result.update(http_status=status, response_body_sha256=sha(response))
            if status != 200:
                result['status'] = 'HTTP_ERROR_STOP'
            else:
                raw, usage = decoded(response, secret, frozen)
                write_once(final_path(), raw.encode())
                result.update(status='PUBLIC_FINAL_REVIEW_ONLY', public_final_sha256=sha(raw.encode()),
                              actual_model=MODEL, finish_reason='stop', usage=usage, semantic='NOT_REVIEWED')
        except ObservedOutputRejected as error:
            result.update(error.observation, status='OUTPUT_REJECTED_STOP')
        except Exception:
            # Never serialize exception text, provider messages, credentials or reasoning.
            result['status'] = 'UNKNOWN_STOP' if result['send_attempted'] else 'PRE_SEND_STOP'
        write_once(result_path(), canonical(result))
        return result


def main() -> int:
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'execute'))
        result = prepare() if sys.argv[1] == 'prepare' else execute()
        # Output only safe finite status/hash; never body/header/key/reasoning.
        print(json.dumps({'status': result.get('status', 'PREPARED'),
                          'prepared_sha256': result.get('prepared_sha256')}))
        return 0 if result.get('status', 'PREPARED') in ('PREPARED', 'PUBLIC_FINAL_REVIEW_ONLY') else 1
    except Exception:
        print('diagnostic refused; preserve package and external ledger', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
