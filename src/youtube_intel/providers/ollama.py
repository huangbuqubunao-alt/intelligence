"""Strict, offline-testable standard-library Adapter for local Ollama scoring."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import IncompleteRead
from typing import Final, NoReturn, Protocol, cast

from youtube_intel.config import LocalScoringSettings, _validate_loopback_http_base_url
from youtube_intel.domain import (
    AppError,
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityJudgeResponse,
    ContentQualityReason,
    ContentQualityResult,
    ContentQualitySignal,
    ContentQualityStatus,
    ErrorCode,
    ProcessingStage,
    QualityJudgeOperationInput,
    ScoreResult,
    ScoringEvidence,
    ScoringInput,
    ScoringOutputLanguage,
    scoring_reason_matches_output_language,
)
from youtube_intel.scoring import PROMPT_VERSION, SCHEMA_VERSION
from youtube_intel.state import build_provider_request_hash

_PROVIDER_NAME: Final = "ollama"
_TAGS_PATH: Final = "/api/tags"
_GENERATE_PATH: Final = "/api/generate"
_REPAIR_OPERATION: Final = "local-scoring-repair"
_MAX_RESPONSE_BYTES: Final = 1_000_000
_MAX_MODEL_RESPONSE_CHARS: Final = 20_000
_PROMPT_VERSION_MARKER: Final = "prompt_version: scoring-prompt-v2"

_MODEL_RESULT_FIELDS: Final = frozenset(
    {"score", "reason", "topics", "should_summarize", "dimensions"}
)
_SCORE_RESULT_FORMAT: Final[dict[str, object]] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["score", "reason", "topics", "should_summarize"],
    "properties": {
        # Ollama's local grammar supports the structural JSON Schema subset.
        # Pydantic ScoreResult validation below remains the fail-closed owner
        # of all numeric, string, and collection bounds.
        "score": {"type": "integer", "enum": list(range(11))},
        "reason": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {"type": "string"},
        },
        "should_summarize": {"type": "boolean"},
        "dimensions": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "technical": {"type": ["number", "null"]},
                "business": {"type": ["number", "null"]},
                "product": {"type": ["number", "null"]},
                "originality": {"type": ["number", "null"]},
                "practicality": {"type": ["number", "null"]},
                "industry_impact": {"type": ["number", "null"]},
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


class _InvalidLanguageResponse(_InvalidModelResponse):
    """Private marker used to keep wrong-language payloads out of artifacts."""


@dataclass(frozen=True, slots=True)
class _GeneratedResponse:
    response_text: str
    raw_response: str


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


def _raise_sanitized(error: AppError) -> NoReturn:
    """Raise a fresh safe error after sensitive stack frames have been cleared."""

    raise OllamaProviderError(error)


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
            msg = "scoring prompt must declare scoring-prompt-v2"
            raise ValueError(msg)
        self._settings = settings
        self._prompt = prompt
        self._transport = transport
        self._last_raw_response: str | None = None
        self._last_request_hash: str | None = None

    def score(self, scoring_input: ScoringInput) -> ScoreResult:
        """Return one validated score, never exposing untrusted failures."""

        video_id = scoring_input.video.video_id
        request_hash = scoring_input.request_hash
        result: ScoreResult | None = None
        failure: AppError | None = None
        primary_response: _GeneratedResponse | None = None
        repair_response: _GeneratedResponse | None = None
        primary_language_invalid = False
        self._last_raw_response = None
        self._last_request_hash = None
        try:
            try:
                self._verify_expected_model(video_id)
                primary_response = self._generate(
                    prompt=self._render_primary_prompt(scoring_input),
                    video_id=video_id,
                )
                result = self._parse_score_result(
                    primary_response.response_text,
                    request_hash,
                    scoring_input.output_language,
                )
            except _InvalidModelResponse as error:
                primary_language_invalid = isinstance(error, _InvalidLanguageResponse)
                if primary_response is None:
                    failure = AppError(
                        code=ErrorCode.INVALID_RESPONSE,
                        message="Ollama scoring response was invalid",
                        retryable=True,
                        video_id=video_id,
                        stage=ProcessingStage.SCORING,
                    )
                else:
                    repair_response = self._generate(
                        prompt=self._render_repair_prompt(
                            primary_response.response_text,
                            request_hash,
                            scoring_input.output_language,
                        ),
                        video_id=video_id,
                    )
                    try:
                        result = self._parse_score_result(
                            repair_response.response_text,
                            request_hash,
                            scoring_input.output_language,
                        )
                    except _InvalidModelResponse:
                        failure = AppError(
                            code=ErrorCode.INVALID_RESPONSE,
                            message=(
                                "Ollama scoring response remained invalid after one repair"
                            ),
                            retryable=True,
                            video_id=video_id,
                            stage=ProcessingStage.SCORING,
                        )
        except OllamaProviderError as error:
            failure = error.error
        except Exception:
            failure = AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="Ollama scoring failed with an invalid response",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )

        if result is not None:
            if primary_response is not None:
                self._last_raw_response = (
                    primary_response.raw_response
                    if repair_response is None
                    else repair_response.raw_response
                )
                self._last_request_hash = request_hash
                return result
            failure = AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="Ollama scoring returned an invalid response",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )

        if primary_response is not None and not primary_language_invalid:
            self._last_raw_response = primary_response.raw_response
            self._last_request_hash = request_hash
        primary_response = None
        repair_response = None
        result = None
        del scoring_input
        del self
        _raise_sanitized(
            failure
            if failure is not None
            else AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="Ollama scoring returned no result",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        """Return the saved raw model response once for private artifact persistence."""

        if request_hash != self._last_request_hash or self._last_raw_response is None:
            msg = "raw Ollama response is unavailable for the scoring request"
            raise ValueError(msg)
        response = self._last_raw_response
        self._last_raw_response = None
        self._last_request_hash = None
        return response

    def _repair_saved_primary_response(
        self,
        *,
        primary_raw_response: str,
        scoring_input: ScoringInput,
    ) -> ScoreResult:
        """Apply the one permitted repair to a request-bound persisted primary response."""

        video_id = scoring_input.video.video_id
        request_hash = scoring_input.request_hash
        result: ScoreResult | None = None
        failure: AppError | None = None
        repair_response: _GeneratedResponse | None = None
        primary_response_text: str | None = None
        self._last_raw_response = None
        self._last_request_hash = None
        try:
            primary_response_text = self._saved_primary_response_text(
                primary_raw_response
            )
            repair_response = self._generate(
                prompt=self._render_repair_prompt(
                    primary_response_text,
                    request_hash,
                    scoring_input.output_language,
                ),
                video_id=video_id,
            )
            result = self._parse_score_result(
                repair_response.response_text,
                request_hash,
                scoring_input.output_language,
            )
        except _InvalidModelResponse:
            failure = AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="saved Ollama scoring response remained invalid after one repair",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )
        except OllamaProviderError as error:
            failure = error.error
        except Exception:
            failure = AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="saved Ollama scoring response could not be repaired",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )

        if result is not None and repair_response is not None:
            self._last_raw_response = repair_response.raw_response
            self._last_request_hash = request_hash
            return result

        repair_response = None
        result = None
        primary_response_text = None
        del primary_raw_response
        del scoring_input
        del self
        _raise_sanitized(
            failure
            if failure is not None
            else AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="saved Ollama scoring response could not be repaired",
                retryable=True,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )
        )

    @staticmethod
    def _saved_primary_response_text(primary_raw_response: str) -> str:
        invalid_response = False
        try:
            payload: object = json.loads(primary_raw_response)
        except json.JSONDecodeError:
            invalid_response = True
            payload = None
        if invalid_response or not isinstance(payload, Mapping):
            raise _InvalidModelResponse
        response = payload.get("response")
        if not isinstance(response, str) or len(response) > _MAX_MODEL_RESPONSE_CHARS:
            raise _InvalidModelResponse
        return response

    def _verify_expected_model(self, video_id: str) -> None:
        payload, _ = self._request_json(
            urllib.request.Request(
                self._endpoint(_TAGS_PATH),
                headers={"Accept": "application/json"},
                method="GET",
            ),
            video_id=video_id,
        )
        if not isinstance(payload, Mapping):
            self._raise_invalid_tags(video_id)
        models = payload.get("models")
        if not isinstance(models, list):
            self._raise_invalid_tags(video_id)
        for item in models:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            digest = item.get("digest")
            normalized_digest = (
                f"sha256:{digest}"
                if isinstance(digest, str)
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
                else digest
            )
            if (
                name == self._settings.model
                and normalized_digest == self._settings.expected_model_digest
            ):
                return
        raise _safe_error(
            ErrorCode.CONFIG_INVALID,
            "configured Ollama model is missing or has an unexpected digest",
            retryable=False,
            video_id=video_id,
        )

    def _raise_invalid_tags(self, video_id: str) -> NoReturn:
        raise _safe_error(
            ErrorCode.INVALID_RESPONSE,
            "Ollama model preflight returned an invalid response",
            retryable=True,
            video_id=video_id,
        )

    def _generate(self, *, prompt: str, video_id: str) -> _GeneratedResponse:
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
        payload, raw_response = self._request_json(
            urllib.request.Request(
                self._endpoint(_GENERATE_PATH),
                data=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            ),
            video_id=video_id,
        )
        if not isinstance(payload, Mapping):
            raise _InvalidModelResponse
        response = payload.get("response")
        if not isinstance(response, str) or len(response) > _MAX_MODEL_RESPONSE_CHARS:
            raise _InvalidModelResponse
        return _GeneratedResponse(response_text=response, raw_response=raw_response)

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        video_id: str,
    ) -> tuple[object, str]:
        response: _Response | None = None
        failure_code: ErrorCode | None = None
        failure_message = ""
        http_status: int | None = None
        try:
            response = self._transport(request, 300.0)
        except urllib.error.HTTPError as exc:
            http_status = exc.code
            try:
                exc.close()
            except OSError:
                pass
        except (TimeoutError, socket.timeout):
            failure_code = ErrorCode.TRANSIENT_NETWORK
            failure_message = "Ollama request timed out"
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                failure_code = ErrorCode.TRANSIENT_NETWORK
                failure_message = "Ollama request timed out"
            else:
                failure_code = ErrorCode.PROVIDER_UNAVAILABLE
                failure_message = "Ollama local provider is unavailable"
        except Exception:
            failure_code = ErrorCode.PROVIDER_UNAVAILABLE
            failure_message = "Ollama local provider is unavailable"

        if http_status is not None:
            self._raise_http_error(http_status, video_id)
        if failure_code is not None:
            raise _safe_error(
                failure_code,
                failure_message,
                retryable=True,
                video_id=video_id,
            )
        if response is None:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=video_id,
            )

        body: bytes | object | None = None
        read_failed = False
        try:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
        except (IncompleteRead, TimeoutError, socket.timeout, OSError):
            read_failed = True
        except Exception:
            read_failed = True
        finally:
            try:
                response.close()
            except Exception:
                read_failed = True
        if read_failed:
            raise _safe_error(
                ErrorCode.TRANSIENT_NETWORK,
                "Ollama response could not be read completely",
                retryable=True,
                video_id=video_id,
            )
        if not isinstance(body, bytes):
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama returned an invalid API response body",
                retryable=True,
                video_id=video_id,
            )
        if len(body) > _MAX_RESPONSE_BYTES:
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama response exceeded the configured safety limit",
                retryable=True,
                video_id=video_id,
            )
        try:
            decoded = body.decode("utf-8")
            return json.loads(decoded), decoded
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama returned a non-JSON API response",
                retryable=True,
                video_id=video_id,
            )

    def _raise_http_error(self, status: int, video_id: str) -> NoReturn:
        if status == 429:
            raise _safe_error(
                ErrorCode.RATE_LIMITED,
                "Ollama local provider rate limited the request",
                retryable=True,
                video_id=video_id,
            )
        if 500 <= status <= 599:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=video_id,
            )
        if status in {401, 403}:
            raise _safe_error(
                ErrorCode.PERMISSION_DENIED,
                "Ollama local provider denied access",
                retryable=False,
                video_id=video_id,
            )
        raise _safe_error(
            ErrorCode.INVALID_RESPONSE,
            "Ollama returned an invalid HTTP response",
            retryable=False,
            video_id=video_id,
        )

    def _parse_score_result(
        self,
        response_text: str,
        request_hash: str,
        output_language: ScoringOutputLanguage,
    ) -> ScoreResult:
        invalid_json = False
        try:
            parsed: object = json.loads(response_text)
        except json.JSONDecodeError:
            invalid_json = True
            parsed = None
        if invalid_json:
            raise _InvalidModelResponse
        if not isinstance(parsed, dict):
            raise _InvalidModelResponse
        if not set(parsed).issubset(_MODEL_RESULT_FIELDS):
            raise _InvalidModelResponse
        reason = parsed.get("reason")
        if isinstance(reason, str) and not scoring_reason_matches_output_language(
            reason, output_language
        ):
            raise _InvalidLanguageResponse
        candidate: dict[str, object] = dict(parsed)
        candidate.update(
            {
                "schema_version": SCHEMA_VERSION,
                "provider": _PROVIDER_NAME,
                "model": self._settings.model,
                "prompt_version": PROMPT_VERSION,
                "request_hash": request_hash,
                "output_language": output_language,
            }
        )
        invalid_model = False
        try:
            return ScoreResult.model_validate(candidate)
        except ValueError:
            invalid_model = True
        if invalid_model:
            raise _InvalidModelResponse
        raise AssertionError("unreachable validated model response")

    def _render_primary_prompt(self, scoring_input: ScoringInput) -> str:
        return self._prompt.replace(
            "{{OUTPUT_LANGUAGE_INSTRUCTION}}",
            self._output_language_instruction(scoring_input.output_language),
        ).replace(
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
                    "output_language": scoring_input.output_language,
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
        request_hash: str,
        output_language: ScoringOutputLanguage,
    ) -> str:
        repair_hash = build_provider_request_hash(
            operation=_REPAIR_OPERATION,
            normalized_input_hash=request_hash,
            provider=_PROVIDER_NAME,
            model=self._settings.model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
        )
        return (
            "Return only one corrected JSON object that satisfies the supplied JSON schema. "
            + self._output_language_instruction(output_language)
            + " "
            "Do not add commentary. Repair request: "
            + repair_hash
            + "\nInvalid response follows:\n"
            + invalid_response
        )

    @staticmethod
    def _output_language_instruction(
        output_language: ScoringOutputLanguage,
    ) -> str:
        if output_language == "zh-CN":
            return (
                "Write the user-visible reason in Simplified Chinese; English technical "
                "proper nouns may remain English. Keep every JSON schema key in English."
            )
        return (
            "Write the user-visible reason in English. Keep every JSON schema key in English."
        )

    def _endpoint(self, path: str) -> str:
        return self._settings.base_url + path


# ---------------------------------------------------------------------------
# Local Content Quality Judge adapter (TASK-016C Phase C)
# ---------------------------------------------------------------------------

_QUALITY_JUDGE_OPERATION: Final = "local-content-quality-v1"
_QUALITY_POLICY_VERSION: Final = "content-quality-policy-v1"
_QUALITY_PROMPT_VERSION: Final = "content-quality-prompt-v1"
_QUALITY_SCHEMA_VERSION: Final = "content-quality-result-v1"
_QUALITY_JUDGE_PROVIDER: Final = "ollama"

_QUALITY_JUDGE_RESULT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "decision_confidence",
        "grounding_confidence",
        "usefulness_confidence",
        "signals",
        "reason",
        "evidence_ids",
    }
)

_QUALITY_JUDGE_FORMAT: Final[dict[str, object]] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "decision_confidence",
        "grounding_confidence",
        "usefulness_confidence",
        "signals",
        "reason",
        "evidence_ids",
    ],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["PASS", "REJECT", "UNCERTAIN"],
        },
        "decision_confidence": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"],
        },
        "grounding_confidence": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"],
        },
        "usefulness_confidence": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"],
        },
        "signals": {
            "type": "array",
            "items": {"type": "string"},
        },
        "reason": {
            "type": ["string", "null"],
        },
        "evidence_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

_QUALITY_JUDGE_PROMPT: Final[str] = (
    "You are a strict content-quality judge. Evaluate the input and return "
    "ONLY one JSON object that satisfies the supplied JSON schema. "
    "Do not add commentary, diagnostics, or fields outside the schema. "
    "Reference only evidence IDs that are present in the input registry.\n"
)


class OllamaQualityJudgeProvider:
    """Loopback-only local Judge adapter for the content-quality layer.

    The adapter validates the configured model/digest, issues a single
    deterministic generate request, parses the strict response contract, and
    returns a trusted ``ContentQualityResult``.  Any transport, parse, schema,
    model/digest, or evidence-identity failure fails closed as ``UNCERTAIN``.

    This class does not reserve or persist ProviderCalls, write artifacts,
    construct attestations, or perform primary/repair orchestration.
    """

    def __init__(
        self,
        *,
        settings: LocalScoringSettings,
        transport: _Transport = _default_transport,
    ) -> None:
        self._settings = settings
        self._transport = transport

    def judge(
        self,
        operation_input: QualityJudgeOperationInput,
        *,
        content_input: ContentQualityInput | None,
    ) -> ContentQualityResult:
        """Return a trusted content-quality result, or UNCERTAIN on any failure.

        The provider reconstructs both inputs into exact base contract types
        before any transport-visible check so that subclass spoofing or mutated
        instances cannot influence trusted binding validation.
        """

        from youtube_intel.quality import _revalidated_fields

        try:
            trusted_operation = _revalidated_fields(
                QualityJudgeOperationInput,
                operation_input,
            )
            if content_input is None:
                return self._build_uncertain_result(
                    trusted_operation,
                    reason=ContentQualityReason.JUDGE_UNAVAILABLE,
                )
            trusted_content = _revalidated_fields(
                ContentQualityInput,
                content_input,
            )
        except Exception:
            return self._build_uncertain_result(
                operation_input,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        if not self._validate_trusted_binding(trusted_operation):
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        if not self._validate_loopback_settings():
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        if not self._validate_content_input_identity(
            trusted_operation,
            trusted_content,
        ):
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        try:
            model_ok = self._verify_expected_model()
        except Exception:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )
        if not model_ok:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        try:
            response = self._generate(
                trusted_operation,
                content_input=trusted_content,
            )
        except _InvalidModelResponse:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_INVALID_RESPONSE,
            )
        except OllamaProviderError:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )
        except Exception:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_UNAVAILABLE,
            )

        try:
            judge_response = self._parse_judge_response(
                response.response_text,
                evidence_registry=trusted_content.evidence_registry,
            )
        except Exception:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_INVALID_RESPONSE,
            )

        try:
            return self._build_result_from_response(
                trusted_operation,
                judge_response,
            )
        except Exception:
            return self._build_uncertain_result(
                trusted_operation,
                reason=ContentQualityReason.JUDGE_INVALID_RESPONSE,
            )

    def _validate_trusted_binding(
        self,
        operation_input: QualityJudgeOperationInput,
    ) -> bool:
        """Verify the operation input matches the trusted local configuration."""

        return (
            operation_input.judge_provider == _QUALITY_JUDGE_PROVIDER
            and operation_input.judge_model == self._settings.model
            and operation_input.judge_model_digest
            == self._settings.expected_model_digest
            and operation_input.policy_version == _QUALITY_POLICY_VERSION
            and operation_input.prompt_version == _QUALITY_PROMPT_VERSION
            and operation_input.schema_version == _QUALITY_SCHEMA_VERSION
        )

    def _validate_content_input_identity(
        self,
        operation_input: QualityJudgeOperationInput,
        content_input: ContentQualityInput,
    ) -> bool:
        """Verify the supplied payload is the one bound to the operation input."""

        from youtube_intel.quality import build_content_quality_input_hash

        if content_input.candidate_hash != operation_input.candidate_hash:
            return False
        if content_input.scoring_request_hash != operation_input.scoring_request_hash:
            return False
        expected_hash = build_content_quality_input_hash(content_input)
        return expected_hash == operation_input.quality_input_hash

    def _validate_loopback_settings(self) -> bool:
        """Revalidate that the configured endpoint is loopback-only."""

        try:
            _validate_loopback_http_base_url(self._settings.base_url)
        except ValueError:
            return False
        return True

    def _verify_expected_model(self) -> bool:
        request = urllib.request.Request(
            self._endpoint(_TAGS_PATH),
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            payload, _ = self._request_json(request, video_id="quality-judge")
        except Exception:
            return False
        if not isinstance(payload, Mapping):
            return False
        models = payload.get("models")
        if not isinstance(models, list):
            return False
        for item in models:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            digest = item.get("digest")
            normalized_digest = (
                f"sha256:{digest}"
                if isinstance(digest, str)
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
                else digest
            )
            if (
                name == self._settings.model
                and normalized_digest == self._settings.expected_model_digest
            ):
                return True
        return False

    def _generate(
        self,
        operation_input: QualityJudgeOperationInput,
        *,
        content_input: ContentQualityInput,
    ) -> _GeneratedResponse:
        from youtube_intel.quality import build_judge_h1_h2

        h1, _ = build_judge_h1_h2(operation_input)
        payload: dict[str, object] = {
            "judge_identity": h1,
            "quality_input_hash": operation_input.quality_input_hash,
            "language": content_input.output_language,
            "candidate_reason": content_input.reason,
            "candidate_topics": content_input.topics,
            "evidence_registry": [
                {"id": item.evidence_id, "excerpt": item.excerpt}
                for item in content_input.evidence_registry
            ],
        }
        prompt = _QUALITY_JUDGE_PROMPT + json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        body = json.dumps(
            {
                "model": self._settings.model,
                "prompt": prompt,
                "stream": False,
                "format": _QUALITY_JUDGE_FORMAT,
                "think": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": self._settings.max_output_tokens,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            response_payload, raw_response = self._request_json(
                urllib.request.Request(
                    self._endpoint(_GENERATE_PATH),
                    data=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                ),
                video_id="quality-judge",
            )
        except OllamaProviderError as exc:
            if exc.error.code is ErrorCode.INVALID_RESPONSE:
                raise _InvalidModelResponse from exc
            raise
        if not isinstance(response_payload, Mapping):
            raise _InvalidModelResponse
        response = response_payload.get("response")
        if not isinstance(response, str) or len(response) > _MAX_MODEL_RESPONSE_CHARS:
            raise _InvalidModelResponse
        return _GeneratedResponse(response_text=response, raw_response=raw_response)

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        video_id: str,
    ) -> tuple[object, str]:
        response: _Response | None = None
        failure_code: ErrorCode | None = None
        failure_message = ""
        http_status: int | None = None
        try:
            response = self._transport(request, 300.0)
        except urllib.error.HTTPError as exc:
            http_status = exc.code
            try:
                exc.close()
            except OSError:
                pass
        except (TimeoutError, socket.timeout):
            failure_code = ErrorCode.TRANSIENT_NETWORK
            failure_message = "Ollama request timed out"
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                failure_code = ErrorCode.TRANSIENT_NETWORK
                failure_message = "Ollama request timed out"
            else:
                failure_code = ErrorCode.PROVIDER_UNAVAILABLE
                failure_message = "Ollama local provider is unavailable"
        except Exception:
            failure_code = ErrorCode.PROVIDER_UNAVAILABLE
            failure_message = "Ollama local provider is unavailable"

        if http_status is not None:
            self._raise_http_error(http_status, video_id)
        if failure_code is not None:
            raise _safe_error(
                failure_code,
                failure_message,
                retryable=True,
                video_id=video_id,
            )
        if response is None:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=video_id,
            )

        body: bytes | object | None = None
        read_failed = False
        try:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
        except (IncompleteRead, TimeoutError, socket.timeout, OSError):
            read_failed = True
        except Exception:
            read_failed = True
        finally:
            try:
                response.close()
            except Exception:
                read_failed = True
        if read_failed:
            raise _safe_error(
                ErrorCode.TRANSIENT_NETWORK,
                "Ollama response could not be read completely",
                retryable=True,
                video_id=video_id,
            )
        if not isinstance(body, bytes):
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama returned an invalid API response body",
                retryable=True,
                video_id=video_id,
            )
        if len(body) > _MAX_RESPONSE_BYTES:
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama response exceeded the configured safety limit",
                retryable=True,
                video_id=video_id,
            )
        try:
            decoded = body.decode("utf-8")
            return json.loads(decoded), decoded
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _safe_error(
                ErrorCode.INVALID_RESPONSE,
                "Ollama returned a non-JSON API response",
                retryable=True,
                video_id=video_id,
            )

    def _raise_http_error(self, status: int, video_id: str) -> NoReturn:
        if status == 429:
            raise _safe_error(
                ErrorCode.RATE_LIMITED,
                "Ollama local provider rate limited the request",
                retryable=True,
                video_id=video_id,
            )
        if 500 <= status <= 599:
            raise _safe_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "Ollama local provider is unavailable",
                retryable=True,
                video_id=video_id,
            )
        if status in {401, 403}:
            raise _safe_error(
                ErrorCode.PERMISSION_DENIED,
                "Ollama local provider denied access",
                retryable=False,
                video_id=video_id,
            )
        raise _safe_error(
            ErrorCode.INVALID_RESPONSE,
            "Ollama returned an invalid HTTP response",
            retryable=False,
            video_id=video_id,
        )

    def _parse_judge_response(
        self,
        response_text: str,
        *,
        evidence_registry: tuple[ScoringEvidence, ...],
    ) -> ContentQualityJudgeResponse:
        parsed: object = json.loads(response_text)
        if not isinstance(parsed, dict):
            raise _InvalidModelResponse
        if not set(parsed).issubset(_QUALITY_JUDGE_RESULT_FIELDS):
            raise _InvalidModelResponse
        judge_response = ContentQualityJudgeResponse.model_validate(parsed)
        valid_ids = {item.evidence_id for item in evidence_registry}
        for eid in judge_response.evidence_ids:
            if eid not in valid_ids:
                raise _InvalidModelResponse
        return judge_response

    def _build_result_from_response(
        self,
        operation_input: QualityJudgeOperationInput,
        judge_response: ContentQualityJudgeResponse,
    ) -> ContentQualityResult:
        return ContentQualityResult.model_validate(
            {
                "schema_version": _QUALITY_SCHEMA_VERSION,
                "policy_version": _QUALITY_POLICY_VERSION,
                "prompt_version": _QUALITY_PROMPT_VERSION,
                "status": judge_response.status,
                "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
                "decision_confidence": judge_response.decision_confidence,
                "grounding_confidence": judge_response.grounding_confidence,
                "usefulness_confidence": judge_response.usefulness_confidence,
                "signals": judge_response.signals,
                "reason": judge_response.reason,
                "evidence_ids": judge_response.evidence_ids,
                "candidate_hash": operation_input.candidate_hash,
                "quality_input_hash": operation_input.quality_input_hash,
                "scoring_request_hash": operation_input.scoring_request_hash,
                "judge_provider": operation_input.judge_provider,
                "judge_model": operation_input.judge_model,
                "judge_model_digest": operation_input.judge_model_digest,
            }
        )

    def _build_uncertain_result(
        self,
        operation_input: QualityJudgeOperationInput,
        *,
        reason: ContentQualityReason,
    ) -> ContentQualityResult:
        expected_signal = ContentQualitySignal(reason.value)
        return ContentQualityResult.model_validate(
            {
                "schema_version": _QUALITY_SCHEMA_VERSION,
                "policy_version": _QUALITY_POLICY_VERSION,
                "prompt_version": _QUALITY_PROMPT_VERSION,
                "status": ContentQualityStatus.UNCERTAIN,
                "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
                "decision_confidence": ContentQualityConfidence.LOW,
                "grounding_confidence": ContentQualityConfidence.LOW,
                "usefulness_confidence": ContentQualityConfidence.LOW,
                "signals": (expected_signal,),
                "reason": reason,
                "evidence_ids": (),
                "candidate_hash": operation_input.candidate_hash,
                "quality_input_hash": operation_input.quality_input_hash,
                "scoring_request_hash": operation_input.scoring_request_hash,
                "judge_provider": _QUALITY_JUDGE_PROVIDER,
                "judge_model": self._settings.model,
                "judge_model_digest": self._settings.expected_model_digest,
            }
        )

    def _endpoint(self, path: str) -> str:
        return self._settings.base_url + path


__all__ = [
    "OllamaProviderError",
    "OllamaScoringProvider",
    "OllamaQualityJudgeProvider",
]
