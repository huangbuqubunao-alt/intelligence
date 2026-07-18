"""Strict, offline-testable standard-library Adapter for local Ollama scoring."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Final, NoReturn, Protocol, cast

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    AppError,
    ErrorCode,
    ProcessingStage,
    ScoreResult,
    ScoringInput,
)
from youtube_intel.scoring import PROMPT_VERSION, SCHEMA_VERSION
from youtube_intel.state import build_provider_request_hash

_PROVIDER_NAME: Final = "ollama"
_TAGS_PATH: Final = "/api/tags"
_GENERATE_PATH: Final = "/api/generate"
_REPAIR_OPERATION: Final = "local-scoring-repair"
_MAX_RESPONSE_BYTES: Final = 1_000_000
_MAX_MODEL_RESPONSE_CHARS: Final = 20_000
_PROMPT_VERSION_MARKER: Final = "prompt_version: scoring-prompt-v1"

_MODEL_RESULT_FIELDS: Final = frozenset(
    {"score", "reason", "topics", "should_summarize", "dimensions"}
)
_SCORE_RESULT_FORMAT: Final[dict[str, object]] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["score", "reason", "topics", "should_summarize"],
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 10},
        "reason": {"type": "string", "minLength": 1, "maxLength": 2000},
        "topics": {
            "type": "array",
            "minItems": 1,
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 80},
        },
        "should_summarize": {"type": "boolean"},
        "dimensions": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "technical": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                "business": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                "product": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                "originality": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                "practicality": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
                "industry_impact": {"type": ["number", "null"], "minimum": 0, "maximum": 10},
            },
        },
    },
}


class _Response(Protocol):
    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


_Transport = Callable[[urllib.request.Request, float], _Response]


class OllamaProviderError(Exception):
    """Adapter-local exception carrying only a safe, named application error."""

    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error


class _InvalidModelResponse(Exception):
    """Private parse marker; response content is never exposed in errors or logs."""


def _default_transport(request: urllib.request.Request, timeout: float) -> _Response:
    return cast(_Response, urllib.request.urlopen(request, timeout=timeout))  # noqa: S310


def _safe_error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool,
    video_id: str,
) -> OllamaProviderError:
    return OllamaProviderError(
        AppError(
            code=code,
            message=message,
            retryable=retryable,
            video_id=video_id,
            stage=ProcessingStage.SCORING,
        )
    )


class OllamaScoringProvider:
    """Score through a loopback-only ``urllib`` transport with one repair attempt."""

    def __init__(
        self,
        *,
        settings: LocalScoringSettings,
        prompt: str,
        transport: _Transport = _default_transport,
    ) -> None:
        if _PROMPT_VERSION_MARKER not in prompt:
            msg = "scoring prompt must declare scoring-prompt-v1"
            raise ValueError(msg)
        self._settings = settings
        self._prompt = prompt
        self._transport = transport

    def score(self, scoring_input: ScoringInput) -> ScoreResult:
        self._verify_expected_model(scoring_input)
        primary_response = self._generate(
            prompt=self._render_primary_prompt(scoring_input),
            scoring_input=scoring_input,
        )
        try:
            return self._parse_score_result(primary_response, scoring_input)
        except _InvalidModelResponse:
            repair_response = self._generate(
                prompt=self._render_repair_prompt(primary_response, scoring_input),
                scoring_input=scoring_input,
            )
            try:
                return self._parse_score_result(repair_response, scoring_input)
            except _InvalidModelResponse as exc:
                raise _safe_error(
                    ErrorCode.INVALID_RESPONSE,
                    "Ollama scoring response remained invalid after one repair",
                    retryable=True,
                    video_id=scoring_input.video.video_id,
                ) from exc

    def _verify_expected_model(self, scoring_input: ScoringInput) -> None:
        payload = self._request_json(
            urllib.request.Request(
                self._endpoint(_TAGS_PATH),
                headers={"Accept": "application/json"},
                method="GET",
            ),
            scoring_input=scoring_input,
        )
        if not isinstance(payload, Mapping):
            self._raise_invalid_tags(scoring_input)
        models = payload.get("models")
        if not isinstance(models, list):
            self._raise_invalid_tags(scoring_input)
        for item in models:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            digest = item.get("digest")
            if name == self._settings.model and digest == self._settings.expected_model_digest:
                return
        raise _safe_error(
            ErrorCode.CONFIG_INVALID,
            "configured Ollama model is missing or has an unexpected digest",
            retryable=False,
            video_id=scoring_input.video.video_id,
        )

    def _raise_invalid_tags(self, scoring_input: ScoringInput) -> NoReturn:
        raise _safe_error(
            ErrorCode.INVALID_RESPONSE,
            "Ollama model preflight returned an invalid response",
            retryable=True,
            video_id=scoring_input.video.video_id,
        )

    def _generate(self, *, prompt: str, scoring_input: ScoringInput) -> str:
        body = json.dumps(
            {
                "model": self._settings.model,
                "prompt": prompt,
                "stream": False,
                "format": _SCORE_RESULT_FORMAT,
                "think": False,
                "options": {
                    "temperature": self._settings.temperature,
                    "num_predict": self._settings.max_output_tokens,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        payload = self._request_json(
            urllib.request.Request(
                self._endpoint(_GENERATE_PATH),
                data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            ),
            scoring_input=scoring_input,
        )
        if not isinstance(payload, Mapping):
            raise _InvalidModelResponse
        response = payload.get("response")
        if not isinstance(response, str) or len(response) > _MAX_MODEL_RESPONSE_CHARS:
            raise _InvalidModelResponse
        return response

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        scoring_input: ScoringInput,
    ) -> object:
        try:
            response = self._transport(request, 300.0)
        except urllib.error.HTTPError as exc:
            try:
                exc.close()
            except OSError:
                pass
            self._raise_http_error(exc.code, scoring_input)
        except (TimeoutError, socket.timeout):
            raise _safe_error(
                ErrorCode.TRANSIENT_NETWORK,
                "Ollama request timed out",
                retryable=True,
                video_id=scoring_input.video.video_id,
            ) from None
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise _safe_error(
                    ErrorCode.TRANSIENT_NETWORK,
                    "Ollama request timed out",
                    retryable=True,
                    video_id=scoring_input.video.video_id,
                ) from None
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=scoring_input.video.video_id,
            ) from None
        except OSError:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=scoring_input.video.video_id,
            ) from None

        try:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
        except (TimeoutError, socket.timeout, OSError):
            raise _safe_error(
                ErrorCode.TRANSIENT_NETWORK,
                "Ollama response could not be read completely",
                retryable=True,
                video_id=scoring_input.video.video_id,
            ) from None
        finally:
            response.close()
        if len(body) > _MAX_RESPONSE_BYTES:
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama response exceeded the configured safety limit",
                retryable=True,
                video_id=scoring_input.video.video_id,
            )
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama returned a non-JSON API response",
                retryable=True,
                video_id=scoring_input.video.video_id,
            ) from None

    def _raise_http_error(self, status: int, scoring_input: ScoringInput) -> NoReturn:
        if status == 429:
            raise _safe_error(
                ErrorCode.RATE_LIMITED,
                "Ollama local provider rate limited the request",
                retryable=True,
                video_id=scoring_input.video.video_id,
            )
        if 500 <= status <= 599:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=scoring_input.video.video_id,
            )
        if status in {401, 403}:
            raise _safe_error(
                ErrorCode.PERMISSION_DENIED,
                "Ollama local provider denied access",
                retryable=False,
                video_id=scoring_input.video.video_id,
            )
        raise _safe_error(
            ErrorCode.INVALID_RESPONSE,
            "Ollama returned an invalid HTTP response",
            retryable=False,
            video_id=scoring_input.video.video_id,
        )

    def _parse_score_result(
        self,
        response_text: str,
        scoring_input: ScoringInput,
    ) -> ScoreResult:
        try:
            parsed: object = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise _InvalidModelResponse from exc
        if not isinstance(parsed, dict):
            raise _InvalidModelResponse
        if not set(parsed).issubset(_MODEL_RESULT_FIELDS):
            raise _InvalidModelResponse
        candidate: dict[str, object] = dict(parsed)
        candidate.update(
            {
                "schema_version": SCHEMA_VERSION,
                "provider": _PROVIDER_NAME,
                "model": self._settings.model,
                "prompt_version": PROMPT_VERSION,
                "request_hash": scoring_input.request_hash,
            }
        )
        try:
            return ScoreResult.model_validate(candidate)
        except ValueError as exc:
            raise _InvalidModelResponse from exc

    def _render_primary_prompt(self, scoring_input: ScoringInput) -> str:
        return self._prompt.replace(
            "{{SCORING_INPUT_JSON}}",
            json.dumps(
                {
                    "video_id": scoring_input.video.video_id,
                    "title": scoring_input.video.title,
                    "channel_name": scoring_input.video.channel_name,
                    "published_at": scoring_input.video.published_at.isoformat(),
                    "duration_seconds": scoring_input.video.duration_seconds,
                    "default_language": scoring_input.video.default_language,
                    "language": scoring_input.language,
                    "description": scoring_input.video.description[
                        : self._settings.max_description_chars
                    ],
                    "transcript_sample": {
                        "head": scoring_input.sample.head,
                        "body": scoring_input.sample.body,
                        "tail": scoring_input.sample.tail,
                    },
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )

    def _render_repair_prompt(
        self,
        invalid_response: str,
        scoring_input: ScoringInput,
    ) -> str:
        repair_hash = build_provider_request_hash(
            operation=_REPAIR_OPERATION,
            normalized_input_hash=scoring_input.request_hash,
            provider=_PROVIDER_NAME,
            model=self._settings.model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
        )
        return (
            "Return only one corrected JSON object that satisfies the supplied JSON schema. "
            "Do not add commentary. Repair request: "
            + repair_hash
            + "\nInvalid response follows:\n"
            + invalid_response
        )

    def _endpoint(self, path: str) -> str:
        return self._settings.base_url + path


__all__ = ["OllamaProviderError", "OllamaScoringProvider"]
