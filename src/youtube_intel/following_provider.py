"""Small provider seam; persistence and lifecycle belong to the shared tracker."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.providers.bilibili import CREATOR_FOLLOWING_AVAILABLE, BilibiliError
from youtube_intel.providers.bilibili_creator import PAGE_SIZE, normalize_creator


class TrackingError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SourceIdentity:
    provider: str
    kind: str
    channel_id: str
    source_id: str
    canonical_url: str
    name: str


@dataclass(frozen=True)
class Candidate:
    identity: str
    published_at: datetime


@dataclass(frozen=True)
class Enumeration:
    name: str
    items: tuple[Candidate, ...]
    complete: bool
    next_page: int


class FollowingProvider(Protocol):
    provider: str
    def resolve(self, value: str) -> SourceIdentity: ...
    def enumerate(self, identity: SourceIdentity, *, initial: bool, next_page: int,
                  known: tuple[Candidate, ...], verified_at: datetime | None) -> Enumeration: ...
    def enroll(self, identity: str, *, channel_id: str, source_id: str,
               followed_at: datetime) -> str: ...


class BilibiliFollowingProvider:
    provider = 'BILIBILI'
    available = CREATOR_FOLLOWING_AVAILABLE

    def __init__(self, publisher: BilibiliContentProvider) -> None:
        self.publisher = publisher

    def resolve(self, value: str) -> SourceIdentity:
        identity = normalize_creator(value)
        metadata = self.publisher.adapter.fetch_creator(identity)
        return SourceIdentity(self.provider, 'CREATOR', identity.mid,
                              identity.source_id, identity.canonical_url, metadata.name)

    def enumerate(self, identity: SourceIdentity, *, initial: bool, next_page: int,
                  known: tuple[Candidate, ...], verified_at: datetime | None) -> Enumeration:
        creator = normalize_creator(identity.channel_id)
        metadata = self.publisher.adapter.fetch_creator(creator)
        pages = [1] if initial else ([1, 2, 3] if next_page == 1 else [1, next_page, next_page + 1])
        items: dict[str, Candidate] = {}
        total: int | None = None
        overlap = False
        complete = False
        deadline = time.monotonic() + 180
        last_page = 1
        for number in pages:
            if time.monotonic() >= deadline:
                raise BilibiliError('NETWORK_UNAVAILABLE')
            page = self.publisher.adapter.fetch_creator_page(creator, number)
            if total is not None and total != page.total:
                raise BilibiliError('METADATA_FAILED')
            total = page.total
            last_page = number
            for item in page.items:
                previous = items.get(item.bvid)
                if previous is not None and previous.published_at != item.published_at:
                    raise BilibiliError('METADATA_FAILED')
                overlap = overlap or previous is not None
                items[item.bvid] = Candidate(item.bvid, item.published_at)
            if initial or number * PAGE_SIZE >= total:
                complete = initial or (next_page == 1 and not overlap)
                break
        next_offset = 1 if complete or last_page * PAGE_SIZE >= (total or 0) else min(last_page + 1, 33333)
        return Enumeration(metadata.name, tuple(items.values()), complete, next_offset)

    def enroll(self, identity: str, *, channel_id: str, source_id: str,
               followed_at: datetime) -> str:
        return self.publisher.import_input(identity, expected_uploader=channel_id,
                 following_source_id=source_id, published_after=followed_at).content_id
