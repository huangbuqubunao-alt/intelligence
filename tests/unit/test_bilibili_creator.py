"""Public creator boundary: canonical identity and strict provider payloads."""

import json

import pytest

from youtube_intel.providers.bilibili import BilibiliAdapter, BilibiliError
from youtube_intel.providers.bilibili_creator import normalize_creator


@pytest.mark.parametrize("value", ["123", "00123", "https://space.bilibili.com/123",
    "https://space.bilibili.com/123/", "https://space.bilibili.com/123/video?spm_id_from=abc"])
def test_creator_forms_share_stable_identity(value: str) -> None:
    creator = normalize_creator(value)
    assert creator.mid == "123"
    assert creator.source_id == "bilibili-creator-123"
    assert creator.canonical_url == "https://space.bilibili.com/123"


@pytest.mark.parametrize("value", ["0", "-1", "123.0", "9" * 30,
    "http://space.bilibili.com/123", "https://example.com/123",
    "https://space.bilibili.com.evil/123", "https://space.bilibili.com@127.0.0.1/123",
    "https://space.bilibili.com:443/123", "https://space.bilibili.com/123/other",
    "https://space.bilibili.com/123?url=https://evil.test", "https://space.bilibili.com/%31%32%33",
    "https://www.bilibili.com/video/BV1xx411c7mD", "123\x00", "123\u200b"])
def test_creator_rejects_crawling_and_unsafe_inputs(value: str) -> None:
    with pytest.raises(BilibiliError):
        normalize_creator(value)


def test_public_creator_metadata_and_list() -> None:
    def fetch(url: str, maximum: int) -> bytes:
        if "/card?" in url:
            data = {"card": {"mid": "123", "name": "公开 UP 主"}}
        else:
            data = {"list": {"vlist": [{"bvid": "BV1xx411c7mD", "mid": 123, "created": 1700000000}]},
                    "page": {"pn": 1, "ps": 30, "count": 1}}
        return json.dumps({"code": 0, "data": data}).encode()
    adapter = BilibiliAdapter(fetch=fetch)
    creator = normalize_creator("123")
    assert adapter.fetch_creator(creator).name == "公开 UP 主"
    page = adapter.fetch_creator_page(creator, 1)
    assert page.items[0].bvid == "BV1xx411c7mD"
    assert page.total == 1


@pytest.mark.parametrize("code", [-352, -412, -509])
def test_creator_risk_control_is_terminal_public_failure(code: int) -> None:
    adapter = BilibiliAdapter(fetch=lambda *_: json.dumps({"code": code}).encode())
    with pytest.raises(BilibiliError, match="RISK_CONTROLLED"):
        adapter.fetch_creator(normalize_creator("123"))
