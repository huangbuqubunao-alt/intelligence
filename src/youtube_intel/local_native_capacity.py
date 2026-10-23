"""Pure current-runtime native token accounting; this grants no execution.

DERIVED_FROM_PINNED_SOURCE, not an official two-message test golden:
Ollama 2476d5ead197abe04629651028f83d48dc75d2b2/model/renderers/qwen35.go
(system/user TrimSpace and think=true suffix), server/prompt.go (Go renderer),
and llm/llama_server.go (separate schema grammar, add_special/parse_special).
The caller must establish that exact installed Go-rendered GGUF path, empty
model messages/system, actual native tokenizer/slot and stable host/lease.
Only the existing LocalCapacitySession may turn its own observations into ready
state. Caller-supplied witnesses, token counts or hashes are never capabilities.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from youtube_intel.local_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID as SHORT_CURRENT,
)
from youtube_intel.local_distillation_profile import canonical, digest, resolve_profile
from youtube_intel.long_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID as LONG_CURRENT,
)
from youtube_intel.long_distillation_profile import resolve_long_profile

# Go unicode.IsSpace/strings.TrimSpace; Python str.strip also removes C0
# U+001C..U+001F, which the pinned renderer preserves. Do not use it here.
_GO_SPACE = "\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
_KEYS = {"model", "messages", "format", "stream", "think", "options", "truncate", "shift"}


def render_qwen35_prompt(request: Mapping[str, Any]) -> str:
    """Render only the pinned pure-text system+user native-thinking shape."""
    messages = request.get("messages")
    if (set(request) != _KEYS or request["think"] is not True
        or request["stream"] is not False or request["truncate"] is not False
        or request["shift"] is not False or type(messages) is not list or len(messages) != 2
        or any(type(message) is not dict or set(message) != {"role", "content"}
            or message["role"] != role or type(message["content"]) is not str
            for message, role in zip(messages, ("system", "user")))):
        raise ValueError("unsupported current native renderer request shape")
    prompt = "".join(
        "<|im_start|>" + message["role"] + "\n" + message["content"].strip(_GO_SPACE) + "<|im_end|>\n"
        for message in messages
    ) + "<|im_start|>assistant\n<think>\n"
    if len(prompt.encode("utf-8", errors="strict")) > 8_000_000:
        raise ValueError("native rendered prompt exceeds its byte bound")
    return prompt


def current_descriptor(profile_id: str) -> dict[str, Any]:
    """Finite options identity only; not qualification or runtime authority."""
    if type(profile_id) is str and profile_id == SHORT_CURRENT:
        profile = resolve_profile(SHORT_CURRENT)
        return dict(profile_id=profile_id, model=profile.model, model_digest=profile.model_digest,
            runtime=profile.runtime, options=profile.options(), max_request_bytes=profile.max_request_bytes)
    if type(profile_id) is str and profile_id == LONG_CURRENT:
        return dict(json.loads(resolve_long_profile(LONG_CURRENT).profile_wire))
    raise ValueError("unknown current native capacity profile")


@dataclass(frozen=True, slots=True)
class NativeCapacityWitness:
    profile_id: str
    request_hash: str
    rendered_hash: str
    schema_hash: str
    token_sequence_hash: str
    input_tokens: int
    context_tokens: int
    predict_tokens: int


def native_capacity_witness(
    request: Mapping[str, Any], *, profile_id: str,
    native_tokens: Mapping[str, Any], actual_slot_context: int,
) -> NativeCapacityWitness:
    """Check a complete native token sequence against actual finite C and P.

    N+P+2<=C proves capacity-triggered shifting/truncation is unreachable for
    this fixed plain-text single completion. It does not claim the hidden
    context_shift flag is false, nor prove that supplied observations are real.
    Session IO, exact builder/proof equality and host binding are mandatory.
    """
    profile = current_descriptor(profile_id)
    if (request.get("model") != profile["model"]
        or canonical(request.get("options")) != canonical(profile["options"])
        or type(request.get("format")) is not dict or not request["format"]
        or len(canonical(request)) > profile["max_request_bytes"]):
        raise ValueError("current native model/options/schema or byte bound differs")
    prompt = render_qwen35_prompt(request)
    context, predict = profile["options"]["num_ctx"], profile["options"]["num_predict"]
    tokens = native_tokens.get("tokens")
    if (type(actual_slot_context) is not int or actual_slot_context != context
        or set(native_tokens) != {"tokens"} or type(tokens) is not list or not tokens
        or any(type(token) is not int or not 0 <= token <= 2**31 - 1 for token in tokens)
        or len(tokens) + predict + 2 > actual_slot_context):
        raise ValueError("native token sequence or actual slot capacity differs")
    return NativeCapacityWitness(profile_id, digest(request), hashlib.sha256(prompt.encode()).hexdigest(),
        digest(request["format"]), digest(tokens), len(tokens), context, predict)
