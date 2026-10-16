"""Strict loopback Ollama adapter for the backend-authoritative Summary contract."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext

from youtube_intel.analysis import (
    LOCAL_ANALYSIS_CONTEXT_TOKENS,
    KnownLocalSummaryResponseError,
    require_trusted_evidence_offer,
    summary_draft_request,
)
from youtube_intel.config import LocalAnalysisSettings, _validate_loopback_http_base_url
from youtube_intel.domain import AnalysisInput
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    SummaryDraft,
    SummaryDraftError,
    parse_summary_draft,
)

_MAX_RESPONSE_BYTES = 1_000_000
_PROMPT_VERSION = SUMMARY_DRAFT_PROMPT_VERSION
_QUALIFIED_MODEL = "qwen3:8b"
_QUALIFIED_DIGEST = (
    "sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
)


def _ollama_schema(value: object) -> object:
    """Project the domain schema to Ollama's supported JSON grammar subset."""
    if isinstance(value, Mapping):
        projected = {
            str(key): _ollama_schema(item)
            for key, item in value.items()
            if key not in {"minLength", "maxLength", "minItems", "maxItems"}
        }
        if "enum" in projected:
            projected.setdefault("type", "string")
        return projected
    if isinstance(value, list):
        return [_ollama_schema(item) for item in value]
    return value


class OllamaSummaryProvider:
    """One exact-digest local call returning a backend-authoritative draft.

    The adapter is structurally incapable of asking the model for authoritative
    Evidence: it constrains generation to ``summary-draft-v1``, which has no
    excerpt, offset, or timestamp property, and it parses the response with the
    strict :func:`parse_summary_draft` contract, so an unsupported field is a
    hard failure rather than a discarded value.
    """

    actual_provider = "ollama"

    def __init__(self, *, settings: LocalAnalysisSettings,
        heavy_guard: Callable[[], AbstractContextManager[None]] | None = None) -> None:
        self._settings = settings
        self._heavy_guard = heavy_guard
        self._raw: str | None = None
        self._request_hash: str | None = None

    def preflight(self) -> None:
        """Verify the configured loopback model before a durable dispatch claim."""

        self._preflight()

    def summarize(self, analysis_input: AnalysisInput) -> SummaryDraft:
        if analysis_input.prompt_version != _PROMPT_VERSION:
            raise ValueError("local Summary prompt identity is invalid")
        # Fail closed before transport if the request carries no citation
        # authority; there is no model-authored fallback.
        require_trusted_evidence_offer(analysis_input)
        draft_request = summary_draft_request(analysis_input)
        request = urllib.request.Request(
            self._url("/api/chat"),
            data=json.dumps(
                {
                    "model": self._settings.model,
                    "messages": [
                        {"role": "user", "content": draft_request.user_prompt()}
                    ],
                    "format": _ollama_schema(draft_request.schema),
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": LOCAL_ANALYSIS_CONTEXT_TOKENS,
                        "num_predict": self._settings.max_output_tokens,
                    },
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        response = self._read(request)
        message = response.get("message")
        raw = message.get("content") if isinstance(message, Mapping) else None
        response_length = len(raw) if isinstance(raw, str) else None

        def rejected(reason: str) -> KnownLocalSummaryResponseError:
            return KnownLocalSummaryResponseError(
                reason,
                prompt_eval_count=response.get("prompt_eval_count"),
                eval_count=response.get("eval_count"),
                done=response.get("done"),
                done_reason=response.get("done_reason"),
                response_length=response_length,
            )

        if response.get("done") is False or response.get("done_reason") == "length":
            raise rejected("generation truncated")
        if (
            response.get("model") != self._settings.model
            or not isinstance(raw, str)
            or not raw
        ):
            raise rejected("response envelope is invalid")
        try:
            draft = parse_summary_draft(raw)
        except SummaryDraftError as error:
            raise rejected(f"Summary draft contract rejected: {error}") from None
        self._raw = json.dumps(
            response, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self._request_hash = analysis_input.request_hash
        return draft

    def consume_raw_response(self, *, request_hash: str) -> str:
        if self._request_hash != request_hash or self._raw is None:
            raise ValueError("local Summary response is unavailable")
        raw = self._raw
        self._request_hash = None
        self._raw = None
        return raw

    def _url(self, path: str) -> str:
        base = _validate_loopback_http_base_url(
            self._settings.base_url, field_name="local_analysis.base_url"
        )
        return base + path

    def _read(self, request: urllib.request.Request) -> Mapping[str, object]:
        try:
            with (self._heavy_guard() if self._heavy_guard is not None else nullcontext()), urllib.request.urlopen(request, timeout=300.0) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except (TimeoutError, OSError, urllib.error.URLError):
            raise RuntimeError("local Summary model is unavailable") from None
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise KnownLocalSummaryResponseError("response exceeded its bound")
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise KnownLocalSummaryResponseError("response envelope is invalid") from None
        if not isinstance(value, Mapping):
            raise KnownLocalSummaryResponseError("response envelope is invalid")
        return value

    def _preflight(self) -> None:
        if (self._settings.model, self._settings.expected_model_digest) != (
            _QUALIFIED_MODEL,
            _QUALIFIED_DIGEST,
        ):
            raise ValueError("local Summary route is not qualified")
        request = urllib.request.Request(
            self._url("/api/tags"),
            headers={"Accept": "application/json"},
            method="GET",
        )
        payload = self._read(request)
        models = payload.get("models")
        if not isinstance(models, list) or not any(
            isinstance(item, Mapping)
            and item.get("name") == self._settings.model
            and self._digest(item.get("digest")) == self._settings.expected_model_digest
            for item in models
        ):
            raise ValueError("local Summary model digest does not match configuration")

    @staticmethod
    def _digest(value: object) -> object:
        if (
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
        ):
            return f"sha256:{value}"
        return value


__all__ = ["OllamaSummaryProvider"]
