"""Narrow public creator contracts. Offsets are traversal, not watermarks."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

from youtube_intel.providers.bilibili import (
    BilibiliError,
    _api_data,
    _number,
    _text,
    normalize_input,
)

PAGE_SIZE = 30


@dataclass(frozen=True)
class CreatorIdentity:
    mid: str

    @property
    def source_id(self) -> str:
        return "bilibili-creator-" + self.mid

    @property
    def canonical_url(self) -> str:
        return "https://space.bilibili.com/" + self.mid


@dataclass(frozen=True)
class CreatorMetadata:
    identity: CreatorIdentity
    name: str


@dataclass(frozen=True)
class CreatorVideo:
    bvid: str
    published_at: datetime


@dataclass(frozen=True)
class CreatorPage:
    items: tuple[CreatorVideo, ...]
    total: int


def normalize_creator(value: str) -> CreatorIdentity:
    if not isinstance(value, str) or not 0 < len(value) <= 2048 or any(
        unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value
    ):
        raise BilibiliError("INVALID_INPUT")
    raw = value.strip()
    try:
        if not re.fullmatch(r"[0-9]{1,20}", raw):
            url = urlsplit(raw)
            if url.scheme != "https" or url.netloc.lower() != "space.bilibili.com":
                raise ValueError()
            match = re.fullmatch(r"/([0-9]{1,20})(?:/|/video/?)?", url.path)
            if match is None or url.fragment:
                raise ValueError()
            query = parse_qs(url.query, keep_blank_values=True, max_num_fields=10)
            if set(query) - {"spm_id_from", "from", "share_source", "share_medium", "share_plat", "share_session_id"}:
                raise ValueError()
            raw = match[1]
        mid = int(raw)
        if not 0 < mid <= 2**63 - 1:
            raise ValueError()
        return CreatorIdentity(str(mid))
    except ValueError:
        raise BilibiliError("INVALID_INPUT") from None


def _creator_data(payload: bytes) -> dict[str, Any]:
    # Classify public risk responses without adding any bypass or retry path.
    from youtube_intel.providers.bilibili import MAX_METADATA, _strict_json
    document = _strict_json(payload, MAX_METADATA, "METADATA_FAILED")
    if type(document.get("code")) is int and document["code"] in {-352, -412, -509}:
        raise BilibiliError("RISK_CONTROLLED")
    return _api_data(payload)


def parse_creator(payload: bytes, identity: CreatorIdentity) -> CreatorMetadata:
    data = _creator_data(payload)
    try:
        card = data["card"]
        mid = card["mid"]
        if type(mid) not in {int, str} or str(mid) != identity.mid:
            raise ValueError()
        name = _text(card["name"], 200)
        if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in name):
            raise ValueError()
        return CreatorMetadata(identity, name)
    except (KeyError, TypeError, ValueError):
        raise BilibiliError("METADATA_FAILED") from None


def parse_creator_page(payload: bytes, identity: CreatorIdentity, page: int) -> CreatorPage:
    data = _creator_data(payload)
    try:
        entries = data["list"]["vlist"]
        info = data["page"]
        if not isinstance(entries, list) or len(entries) > PAGE_SIZE or (
            type(info["pn"]) is not int or info["pn"] != page
            or type(info["ps"]) is not int or info["ps"] != PAGE_SIZE
            or type(info["count"]) is not int or not 0 <= info["count"] <= 1000000
        ):
            raise ValueError()
        if len(entries) != min(PAGE_SIZE, max(0, info["count"] - (page - 1) * PAGE_SIZE)):
            raise ValueError()
        items = []
        for entry in entries:
            if type(entry["mid"]) is not int or str(entry["mid"]) != identity.mid:
                raise ValueError()
            identity_video = normalize_input(entry["bvid"])
            stamp = _number(entry["created"], 0, time.time() + 86400)
            items.append(CreatorVideo(identity_video.bvid, datetime.fromtimestamp(stamp, UTC)))
        if len({item.bvid for item in items}) != len(items):
            raise ValueError()
        return CreatorPage(tuple(items), info["count"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise BilibiliError("METADATA_FAILED") from None
