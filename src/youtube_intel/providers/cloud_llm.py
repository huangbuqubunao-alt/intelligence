"""Isolated, offline-testable OpenAI Responses adapter.

The OpenAI SDK is intentionally absent from this process.  The default transport
starts a short-lived child with an empty allow-list environment; it imports the
SDK before receiving a credential through stdin.  Tests replace that boundary
with a pure Fake transport.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Final, Protocol, cast

from pydantic import ValidationError

from youtube_intel.analysis import _analysis_schema, _canonical_json, _request_parts
from youtube_intel.domain import (
    AnalysisInput,
    AnalysisResult,
    AppError,
    ErrorCode,
    EvidenceSource,
    ProcessingStage,
)

_PROVIDER: Final = "openai"
_TIMEOUT_SECONDS: Final = 120
_CHILD_ENV: Final = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUTF8": "1",
}
_CHILD_PROGRAM: Final = r'''
import json
import sys
from openai import OpenAI
print(json.dumps({"kind": "ready"}), flush=True)
message = json.loads(sys.stdin.readline())
credential = message.pop("credential")
max_retries = message.pop("max_retries")
timeout = message.pop("timeout")
client = OpenAI(api_key=credential, max_retries=max_retries, timeout=timeout)
response = client.responses.create(**message)
usage = getattr(response, "usage", None)
print(json.dumps({
    "output_text": getattr(response, "output_text", None),
    "refusal": bool(getattr(response, "refusal", None)),
    "input_tokens": None if usage is None else getattr(usage, "input_tokens", None),
    "output_tokens": None if usage is None else getattr(usage, "output_tokens", None),
}), flush=True)
'''


class CloudProviderError(Exception):
    """Safe named provider error without server bodies, credentials, or paths."""

    def __init__(self, error: AppError, *, refusal: bool = False) -> None:
        super().__init__(error.message)
        self.error = error
        self.refusal = refusal


class _Transport(Protocol):
    def __call__(self, request: dict[str, object], credential: str) -> dict[str, object]: ...


def _safe_error(
    code: ErrorCode,
    message: str,
    *,
    video_id: str,
    retryable: bool,
    refusal: bool = False,
) -> CloudProviderError:
    return CloudProviderError(
        AppError(code=code, message=message, retryable=retryable, video_id=video_id, stage=ProcessingStage.ANALYSIS),
        refusal=refusal,
    )


def _isolated_transport(request: dict[str, object], credential: str) -> dict[str, object]:
    """Run the SDK in a no-inherited-environment child and exchange JSON over pipes."""

    process = subprocess.Popen(
        [sys.executable, "-c", _CHILD_PROGRAM],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=dict(_CHILD_ENV),
    )
    try:
        if process.stdout is None or process.stdin is None:
            raise RuntimeError("isolated OpenAI child has no pipes")
        ready = json.loads(process.stdout.readline())
        if ready != {"kind": "ready"}:
            raise RuntimeError("isolated OpenAI child failed to import SDK")
        process.stdin.write(_canonical_json({**request, "credential": credential}) + "\n")
        process.stdin.flush()
        response_line = process.stdout.readline()
        if process.wait(timeout=_TIMEOUT_SECONDS) != 0:
            raise RuntimeError("isolated OpenAI child failed")
        response = json.loads(response_line)
        if not isinstance(response, dict):
            raise RuntimeError("isolated OpenAI child returned invalid response")
        return cast(dict[str, object], response)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise TimeoutError from exc
    finally:
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()


def _request(analysis_input: AnalysisInput, *, model: str, max_output_tokens: int) -> dict[str, object]:
    parts = _request_parts(analysis_input.payload)
    return {
        "model": model,
        "input": [
            {"role": "system", "content": parts.system},
            {"role": "developer", "content": parts.developer},
            {"role": "user", "content": parts.payload_json},
        ],
        "text": {"format": {"type": "json_schema", "name": "analysis_result", "strict": True, "schema": _analysis_schema()}},
        "store": False,
        "truncation": "disabled",
        "max_output_tokens": max_output_tokens,
        "max_retries": 0,
        "timeout": _TIMEOUT_SECONDS,
    }


class OpenAIResponsesProvider:
    """One-request strict Structured Outputs provider with an injected transport seam."""

    def __init__(self, *, model: str, max_output_tokens: int = 4_000, transport: _Transport = _isolated_transport) -> None:
        if not model.strip() or not 256 <= max_output_tokens <= 8_000:
            msg = "cloud model or output token limit is invalid"
            raise ValueError(msg)
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._transport = transport
        self._last_raw_response: str | None = None
        self._last_request_hash: str | None = None

    def summarize(self, analysis_input: AnalysisInput) -> AnalysisResult:
        """The public provider protocol cannot supply credentials; fail closed."""

        raise _safe_error(ErrorCode.PERMISSION_DENIED, "cloud credential was not provided", video_id=analysis_input.payload.video_id, retryable=False)

    def summarize_with_credential(self, analysis_input: AnalysisInput, credential: str) -> AnalysisResult:
        if not credential:
            raise _safe_error(ErrorCode.PERMISSION_DENIED, "cloud credential was not provided", video_id=analysis_input.payload.video_id, retryable=False)
        try:
            response = self._transport(_request(analysis_input, model=self._model, max_output_tokens=self._max_output_tokens), credential)
        except TimeoutError:
            raise _safe_error(ErrorCode.TRANSIENT_NETWORK, "cloud analysis request timed out", video_id=analysis_input.payload.video_id, retryable=True) from None
        except Exception:
            raise _safe_error(ErrorCode.TRANSIENT_NETWORK, "cloud analysis transport failed", video_id=analysis_input.payload.video_id, retryable=True) from None
        if response.get("refusal") is True:
            raise _safe_error(ErrorCode.PERMISSION_DENIED, "cloud analysis request was refused", video_id=analysis_input.payload.video_id, retryable=False, refusal=True)
        error = response.get("error")
        if isinstance(error, dict):
            status = error.get("status")
            if status == 429:
                raise _safe_error(ErrorCode.RATE_LIMITED, "cloud analysis rate limited", video_id=analysis_input.payload.video_id, retryable=True)
            if isinstance(status, int) and 500 <= status <= 599:
                raise _safe_error(ErrorCode.PROVIDER_UNAVAILABLE, "cloud analysis provider unavailable", video_id=analysis_input.payload.video_id, retryable=True)
            if status in {401, 403}:
                raise _safe_error(ErrorCode.PERMISSION_DENIED, "cloud analysis permission denied", video_id=analysis_input.payload.video_id, retryable=False)
            raise _safe_error(ErrorCode.INVALID_RESPONSE, "cloud analysis returned an invalid response", video_id=analysis_input.payload.video_id, retryable=True)
        raw_content = response.get("output_text")
        if not isinstance(raw_content, dict):
            raise _safe_error(ErrorCode.INVALID_RESPONSE, "cloud analysis returned an invalid response", video_id=analysis_input.payload.video_id, retryable=True)
        try:
            result = AnalysisResult.model_validate({**raw_content, "provider": _PROVIDER, "model": self._model, "request_hash": analysis_input.request_hash})
            self._validate_grounding(result, analysis_input)
        except (ValidationError, ValueError, TypeError):
            raise _safe_error(ErrorCode.INVALID_RESPONSE, "cloud analysis response failed validation", video_id=analysis_input.payload.video_id, retryable=True) from None
        self._last_raw_response = _canonical_json(response)
        self._last_request_hash = analysis_input.request_hash
        return result

    def consume_raw_response(self, *, request_hash: str) -> str:
        if self._last_request_hash != request_hash or self._last_raw_response is None:
            raise ValueError("cloud response is unavailable for this request")
        value = self._last_raw_response
        self._last_raw_response = None
        self._last_request_hash = None
        return value

    @staticmethod
    def _validate_grounding(result: AnalysisResult, analysis_input: AnalysisInput) -> None:
        payload = analysis_input.payload
        allowed = {
            EvidenceSource.TITLE: payload.title,
            EvidenceSource.CHANNEL_NAME: payload.channel_name,
            EvidenceSource.DESCRIPTION: payload.description,
            EvidenceSource.TRANSCRIPT_SAMPLE: payload.transcript_sample,
        }
        for evidence in result.evidence:
            source = allowed[evidence.source]
            if evidence.excerpt not in source:
                raise ValueError("analysis evidence is not grounded in the outbound payload")


__all__ = ["CloudProviderError", "OpenAIResponsesProvider"]
