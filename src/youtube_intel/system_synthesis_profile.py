"""Finite transport identity and conservative price bound; grants no eligibility."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from . import system_synthesis as synthesis
from .system_synthesis import SystemSynthesisRequest

PROFILE_ID: Final = "moonshot-k31-system-synthesis-v1-20261029"
ATTRIBUTION_PROFILE_ID: Final = "moonshot-k31-system-synthesis-v2-attribution-20261105"
SOURCE_LEVEL_PROFILE_ID: Final = "moonshot-k31-system-synthesis-v3-source-level-20261106"
PROFILE_IDS: Final = (PROFILE_ID, ATTRIBUTION_PROFILE_ID, SOURCE_LEVEL_PROFILE_ID)
PAIR: Final = ("moonshot", "kimi-k3.1-pro")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def policy_id(profile_id: str) -> str:
    if profile_id == PROFILE_ID:
        return synthesis.PROFILE_ID
    if profile_id == ATTRIBUTION_PROFILE_ID:
        return synthesis.ATTRIBUTION_PROFILE_ID
    if profile_id == SOURCE_LEVEL_PROFILE_ID:
        return synthesis.SOURCE_LEVEL_PROFILE_ID
    raise ValueError("Unknown system synthesis transport profile")


def resolve_profile(profile_id: str) -> dict[str, Any]:
    if profile_id == SOURCE_LEVEL_PROFILE_ID:
        policy = synthesis.profile_projection(synthesis.SOURCE_LEVEL_PROFILE_ID)
        return {**resolve_profile(PROFILE_ID), "id": profile_id,
            "policy_id": synthesis.SOURCE_LEVEL_PROFILE_ID, "policy_sha256": sha(canonical(policy))}
    if profile_id == ATTRIBUTION_PROFILE_ID:
        policy = synthesis.profile_projection(synthesis.ATTRIBUTION_PROFILE_ID)
        return {**resolve_profile(PROFILE_ID), "id": profile_id,
            "policy_id": synthesis.ATTRIBUTION_PROFILE_ID, "policy_sha256": sha(canonical(policy))}
    if profile_id != PROFILE_ID:
        raise ValueError("Unknown system synthesis transport profile")
    return {
        "id": PROFILE_ID,
        "provider": PAIR[0],
        "model": PAIR[1],
        "endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "reasoning_effort": "low",
        "max_completion_tokens": 5888,
        "stream": False,
        "response_format": {"type": "json_object"},
        "prompt_cache_options": {"mode": "implicit", "ttl": "5m"},
        "deadline_seconds": 300,
        "retries": 0,
        "max_request_bytes": 32768,
        "max_response_bytes": 2 * 1024 * 1024,
        "framing_token_assumption": 2048,
        "input_microcny_per_token_worst": 26,
        "output_microcny_per_token": 68,
        "billing_guarantee": False,
        "qualified": False,
        "normal_spending_authorized": False,
        "price_date": "2026-10-29",
        "official_document_sha256": [
            "0ed8094de8dedd0ae4dd1912e92c6d385e1a79e83313c1f82686d7943a5d6df1",
            "7a1e692601a4a00628fbbd88c2561df485f2505a933c0841c9015ffaa6bc32c6",
            "921983646fa6f233bbe0a6275bf48c2fa594d124e6377d596986a16aab96569b",
        ],
    }


def provider_wire(request: SystemSynthesisRequest, profile_id: str = PROFILE_ID) -> tuple[str, int]:
    profile = resolve_profile(profile_id)
    if type(request) is not SystemSynthesisRequest or request.profile_id != policy_id(profile_id):
        raise ValueError("System synthesis transport/policy mixture")
    synthesis._request(request)
    messages = json.loads(request.wire_json)["messages"]
    wire = canonical(
        {
            "model": profile["model"],
            "messages": messages,
            **{
                key: profile[key]
                for key in (
                    "reasoning_effort",
                    "max_completion_tokens",
                    "stream",
                    "response_format",
                    "prompt_cache_options",
                )
            },
        }
    )
    if len(wire.encode()) > profile["max_request_bytes"]:
        raise ValueError("System synthesis request exceeds fixed byte bound")
    reserve = (sum(len(m["content"].encode()) for m in messages) + profile["framing_token_assumption"]) * 26 + 5888 * 68
    return wire, reserve
