"""ADR-028 tests for explicitly provisioned local o200k tokenizer data."""

from __future__ import annotations

import hashlib
import os
import socket
from pathlib import Path

import pytest

from youtube_intel import analysis

_CANONICAL_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
_GOLDEN_VECTORS = {
    "The quick brown fox jumps over the lazy dog.": [
        976, 4853, 19705, 68347, 65613, 1072, 290, 29082, 6446, 13,
    ],
    "你好，世界。人工智能正在改变软件工程。": [
        177519, 979, 28428, 788, 47243, 60319, 70104, 182793, 9941, 58542, 788,
    ],
    "English 中文 العربية हिन्दी русский español": [28881, 83711, 33968, 191681, 172163, 50208],
    "Launch 🚀✨ — family 👨‍👩‍👧‍👦": [
        35423, 169883, 222, 97375, 2733, 3502, 61138, 101, 2524, 28823, 102,
        2524, 28823, 100, 2524, 28823, 99,
    ],
    '"quotes", (brackets) [square] {brace}; 123.45?!': [
        1, 136724, 672, 350, 1697, 42290, 8, 723, 79029, 60, 354, 102116,
        22532, 220, 7633, 13, 2548, 25309,
    ],
}


def _asset_path(data_root: Path) -> Path:
    target = data_root / "tokenizers" / analysis.O200K_BASE_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def test_distribution_source_tree_has_no_o200k_resource() -> None:
    assert not analysis.PACKAGED_O200K_RESOURCE.exists()


def test_missing_asset_fails_closed_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("tokenizer provisioning must never trigger network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)

    with pytest.raises(analysis.LocalTokenizerResourceError, match="missing"):
        analysis.load_provisioned_o200k_encoding(tmp_path)

    assert analysis.tokenizer_resource_status(tmp_path) == "MISSING"


def test_valid_explicit_asset_is_admitted_only_against_the_fixed_hash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A minimal, non-canonical BPE fixture proves the admission boundary. The
    # production constant is asserted first and only the test seam is changed.
    assert analysis.O200K_BASE_SHA256 == _CANONICAL_SHA256
    fixture = b"YQ== 0\nYg== 1\n"
    target = _asset_path(tmp_path)
    target.write_bytes(fixture)
    monkeypatch.setattr(analysis, "O200K_BASE_SHA256", hashlib.sha256(fixture).hexdigest())
    monkeypatch.setattr(analysis, "O200K_BASE_SIZE", len(fixture))

    encoding = analysis.load_provisioned_o200k_encoding(tmp_path)

    assert encoding.name == "o200k_base-local"
    assert analysis.tokenizer_resource_status(tmp_path) == "READY"


def test_wrong_hash_and_symlink_are_rejected_without_path_leakage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = _asset_path(tmp_path)
    wrong_contents = b"not the canonical o200k data"
    target.write_bytes(wrong_contents)
    monkeypatch.setattr(analysis, "O200K_BASE_SIZE", len(wrong_contents))

    with pytest.raises(analysis.LocalTokenizerResourceError, match="invalid") as mismatch:
        analysis.load_provisioned_o200k_encoding(tmp_path)
    assert str(tmp_path) not in str(mismatch.value)

    target.unlink()
    external = tmp_path / "external.tiktoken"
    external.write_bytes(b"not the canonical o200k data")
    target.symlink_to(external)
    with pytest.raises(analysis.LocalTokenizerResourceError, match="unsafe"):
        analysis.load_provisioned_o200k_encoding(tmp_path)
    assert analysis.tokenizer_resource_status(tmp_path) == "INVALID"


def test_symlinked_tokenizer_directory_is_rejected(
    tmp_path: Path,
) -> None:
    external_directory = tmp_path / "external-tokenizers"
    external_directory.mkdir()
    (tmp_path / "tokenizers").symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(analysis.LocalTokenizerResourceError, match="unsafe"):
        analysis.load_provisioned_o200k_encoding(tmp_path)


def test_missing_nofollow_support_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _asset_path(tmp_path).write_bytes(b"not a canonical asset")
    monkeypatch.delattr(analysis.os, "O_NOFOLLOW", raising=False)

    with pytest.raises(analysis.LocalTokenizerResourceError, match="unsafe"):
        analysis.load_provisioned_o200k_encoding(tmp_path)


def test_correct_hash_but_malformed_asset_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = b"not a valid tiktoken rank table\n"
    target = _asset_path(tmp_path)
    target.write_bytes(fixture)
    monkeypatch.setattr(analysis, "O200K_BASE_SIZE", len(fixture))
    monkeypatch.setattr(analysis, "O200K_BASE_SHA256", hashlib.sha256(fixture).hexdigest())

    with pytest.raises(analysis.LocalTokenizerResourceError, match="invalid"):
        analysis.load_provisioned_o200k_encoding(tmp_path)


def test_external_provisioned_canonical_asset_preserves_golden_token_ids() -> None:
    asset = os.environ.get("YOUTUBE_INTEL_O200K_TEST_ASSET")
    if asset is None:
        pytest.skip("requires an explicitly provisioned canonical o200k asset")

    root = Path(asset).resolve().parent.parent
    target = _asset_path(root)
    if target != Path(asset).resolve():
        raise AssertionError("test asset must be at data_dir/tokenizers/o200k_base.tiktoken")
    encoding = analysis.load_provisioned_o200k_encoding(root)
    for text, expected_ids in _GOLDEN_VECTORS.items():
        assert encoding.encode(text, disallowed_special=()) == expected_ids
    assert len(encoding.encode(("abc " * 1024) + "终", disallowed_special=())) == 1026
