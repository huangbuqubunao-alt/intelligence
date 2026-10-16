"""Pinned real 0.40.1 manifest metadata, never a model/qualification fixture."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from youtube_intel import local_model_capacity as capacity

PARENT = b'{"schemaVersion":2,"mediaType":"application/vnd.docker.distribution.manifest.v2+json","config":{"mediaType":"application/vnd.docker.container.image.v1+json","digest":"sha256:08f9698c1116d2ba3d2c1751f6e98919823e13bb28ff5eb7451c7bc9b40907c5","size":177},"layers":[{"mediaType":"application/vnd.ollama.image.projector","digest":"sha256:f836f08f921193f4d6b6a6952dba0a6fb116759d26a757bcb395d570d73976ca","size":921704832,"from":"mmproj.gguf"},{"mediaType":"application/vnd.ollama.image.model","digest":"sha256:02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d","size":5629109120,"from":"model.gguf"},{"mediaType":"application/vnd.ollama.image.template","digest":"sha256:b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315","size":13},{"mediaType":"application/vnd.ollama.image.license","digest":"sha256:50cbab8a892c5f2993b8c7351a99182507472def3b1374558308605d99b86b32","size":11343},{"mediaType":"application/vnd.ollama.image.params","digest":"sha256:9371364b27a52acac9d87f88bd93c9db1174d8d6ec57f6888925cdc1788871ff","size":65}],"runner":"llamacpp","format":"gguf"}'
PARENT_SHA = "56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90"
WRAPPER_SHA = "7dd7bb310c1f18ad132c7fd72e73d4f6cff2e916c596a818701d2a1269037c7f"


def _encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def wrapper_bytes():
    wrapper = json.loads(PARENT)
    wrapper["layers"].append(
        {
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "digest": "sha256:" + PARENT_SHA,
            "size": 1088,
        }
    )
    return _encode(wrapper)


def _paths(tmp_path):
    wrapper, parent = tmp_path / "wrapper", tmp_path / "parent"
    wrapper.write_bytes(wrapper_bytes())
    parent.write_bytes(PARENT)
    return wrapper, parent


def test_real_fixed_wrapper_references_original_manifest_without_changing_model_digest(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: pytest.fail("zero model HTTP")
    )
    wrapper, parent = _paths(tmp_path)
    assert len(PARENT) == 1088 and hashlib.sha256(PARENT).hexdigest() == PARENT_SHA
    assert (
        len(wrapper_bytes()) == 1252
        and hashlib.sha256(wrapper_bytes()).hexdigest() == WRAPPER_SHA
    )
    assert (
        capacity.resolve_profile(capacity.PROFILE_ID).model_digest
        == "sha256:" + PARENT_SHA
    )
    capacity._verify_model_manifests(wrapper, parent)


@pytest.mark.parametrize(
    "damage",
    [
        "wrapper-hash",
        "parent-hash",
        "parent-missing",
        "layer-added",
        "layer-removed",
        "layer-duplicate",
        "parent-duplicate",
        "layer-order",
        "from",
        "media-type",
        "size",
        "parent-link",
        "runner",
        "format",
        "unknown",
        "duplicate-json",
        "non-json",
        "deep-json",
        "oversized",
    ],
)
def test_any_unapproved_manifest_or_relation_closes(damage, tmp_path):
    wrapper, parent = _paths(tmp_path)
    value = deepcopy(json.loads(wrapper_bytes()))
    if damage == "wrapper-hash":
        wrapper.write_bytes(wrapper_bytes() + b" ")
    elif damage == "parent-hash":
        parent.write_bytes(PARENT[:-1] + b" ")
    elif damage == "parent-missing":
        parent.rename(tmp_path / "removed-parent")
    elif damage == "layer-added":
        value["layers"].append(
            {"mediaType": "unknown", "digest": "sha256:" + "a" * 64, "size": 1}
        )
    elif damage == "layer-removed":
        value["layers"].pop(0)
    elif damage == "layer-duplicate":
        value["layers"][1] = value["layers"][0]
    elif damage == "parent-duplicate":
        value["layers"].append(value["layers"][-1])
    elif damage == "layer-order":
        value["layers"][0], value["layers"][1] = value["layers"][1], value["layers"][0]
    elif damage == "from":
        value["layers"][0]["from"] = "other.gguf"
    elif damage == "media-type":
        value["layers"][0]["mediaType"] = "application/vnd.ollama.image.model"
    elif damage == "size":
        value["layers"][0]["size"] += 1
    elif damage == "parent-link":
        value["layers"][-1]["digest"] = "sha256:" + "a" * 64
    elif damage in {"runner", "format", "unknown"}:
        value[damage] = "unexpected"
    elif damage == "duplicate-json":
        wrapper.write_bytes(
            wrapper_bytes().replace(
                b'{"schemaVersion":2,', b'{"schemaVersion":2,"schemaVersion":2,'
            )
        )
    elif damage == "non-json":
        wrapper.write_bytes(b"x" * 1252)
    elif damage == "deep-json":
        wrapper.write_bytes(b"[" * 626 + b"]" * 626)
    elif damage == "oversized":
        wrapper.write_bytes(wrapper_bytes() + b"x" * 1024)
    if damage in {
        "layer-added",
        "layer-removed",
        "layer-duplicate",
        "parent-duplicate",
        "layer-order",
        "from",
        "media-type",
        "size",
        "parent-link",
        "runner",
        "format",
        "unknown",
    }:
        wrapper.write_bytes(_encode(value))
    with pytest.raises((capacity.CapacityUnavailable, OSError)):
        capacity._verify_model_manifests(wrapper, parent)


def fixture_installation(tmp_path, monkeypatch):
    """Tiny byte-verified payloads; a shape fixture, not real host authority."""
    from dataclasses import replace
    from types import SimpleNamespace

    home, root = tmp_path / "home", tmp_path / "runtime"
    root.mkdir()
    cache = home / ".ollama/models"
    wrapper = cache / "manifests/registry.ollama.ai/library/qwen3.5/9b-q4_K_M"
    wrapper.parent.mkdir(parents=True)
    blobs = cache / "blobs"
    blobs.mkdir()
    value = json.loads(PARENT)
    payloads = {}
    for index, descriptor in enumerate([value["config"], *value["layers"]]):
        raw = ("bounded fixture payload " + str(index)).encode()
        blob_hash = hashlib.sha256(raw).hexdigest()
        payloads[blob_hash] = len(raw)
        (blobs / ("sha256-" + blob_hash)).write_bytes(raw)
        descriptor.update(digest="sha256:" + blob_hash, size=len(raw))
    parent_raw = _encode(value)
    parent_hash = hashlib.sha256(parent_raw).hexdigest()
    parent = blobs / ("sha256-" + parent_hash)
    parent.write_bytes(parent_raw)
    value["layers"].append(
        {
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "digest": "sha256:" + parent_hash,
            "size": len(parent_raw),
        }
    )
    wrapper_raw = _encode(value)
    wrapper.write_bytes(wrapper_raw)
    reference = cache / "manifests-v2/ollama.com/library/qwen3.5/9b-q4_K_M"
    reference.parent.mkdir(parents=True)
    reference.symlink_to("../../../../blobs/sha256-" + parent_hash)
    binary = root / "ollama"
    binary.write_bytes(b"fixture runtime")
    binary_hash = capacity.file_hash(binary)
    profile = replace(
        capacity.resolve_profile(capacity.PROFILE_ID),
        model_digest="sha256:" + parent_hash,
    )
    monkeypatch.setattr(capacity.Path, "home", classmethod(lambda _: home))
    monkeypatch.setattr(capacity, "ROOT", root)
    monkeypatch.setattr(capacity, "BINARIES", {"ollama": binary_hash})
    monkeypatch.setattr(capacity, "BLOBS", payloads)
    monkeypatch.setattr(capacity, "resolve_profile", lambda _: profile)
    monkeypatch.setattr(capacity, "_PARENT_MANIFEST_BYTES", len(parent_raw))
    monkeypatch.setattr(capacity, "_WRAPPER_MANIFEST_BYTES", len(wrapper_raw))
    monkeypatch.setattr(
        capacity, "_WRAPPER_SHA256", hashlib.sha256(wrapper_raw).hexdigest()
    )
    monkeypatch.setattr(
        capacity.shutil, "disk_usage", lambda _: SimpleNamespace(free=20 * capacity.GIB)
    )
    monkeypatch.setattr(capacity, "available_memory_bytes", lambda: 10 * capacity.GIB)
    monkeypatch.setattr(
        capacity,
        "processes",
        lambda name: (
            f"77 Thu Oct 01 00:00:00 2026 {root / 'ollama'} serve"
            if name == "ollama"
            else ""
        ),
    )
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: pytest.fail("zero model HTTP")
    )
    return (
        wrapper,
        parent,
        reference,
        binary,
        tuple(blobs / ("sha256-" + h) for h in payloads),
    )


@pytest.mark.parametrize("index", range(6))
def test_each_payload_requires_its_actual_bytes(index, tmp_path, monkeypatch):
    _, _, _, _, payloads = fixture_installation(tmp_path, monkeypatch)
    raw = payloads[index].read_bytes()
    payloads[index].write_bytes(b"x" * len(raw))
    with pytest.raises(capacity.CapacityUnavailable, match="model blob differs"):
        capacity.observe_host(data_root=tmp_path, loaded=False)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "regular",
        "wrong-target",
        "same-target-replacement",
        "parent-replaced-during-hash",
        "parent-content-during-hash",
        "wrapper-during-hash",
        "reference-during-hash",
    ],
)
def test_reference_parent_and_wrapper_identity_changes_close(
    damage, tmp_path, monkeypatch
):
    wrapper, parent, reference, binary, _ = fixture_installation(tmp_path, monkeypatch)
    if damage in {"missing", "regular", "wrong-target"}:
        reference.rename(reference.parent / "original-link")
        if damage == "regular":
            reference.write_bytes(parent.read_bytes())
        elif damage == "wrong-target":
            reference.symlink_to("../../../../blobs/sha256-" + "a" * 64)
    elif damage == "same-target-replacement":
        observation = capacity.observe_host(data_root=tmp_path, loaded=False)
        original = reference.readlink()
        reference.rename(reference.parent / "original-link")
        reference.symlink_to(original)
        assert not observation.is_current()
        return
    else:
        original_hash = capacity.file_hash

        def changed(path, **kwargs):
            value = original_hash(path, **kwargs)
            if path == binary:
                if damage == "parent-replaced-during-hash":
                    replacement = parent.parent / "replacement"
                    replacement.write_bytes(parent.read_bytes())
                    replacement.replace(parent)
                elif damage == "parent-content-during-hash":
                    parent.write_bytes(b"x" * parent.stat().st_size)
                elif damage == "wrapper-during-hash":
                    wrapper.write_bytes(b"x" * wrapper.stat().st_size)
                elif damage == "reference-during-hash":
                    original = reference.readlink()
                    reference.rename(reference.parent / "original-link")
                    reference.symlink_to(original)
            return value

        monkeypatch.setattr(capacity, "file_hash", changed)
    with pytest.raises((capacity.CapacityUnavailable, OSError)):
        capacity.observe_host(data_root=tmp_path, loaded=False)


def test_hashing_cannot_approve_a_different_file_then_restore_original_identity(
    tmp_path, monkeypatch
):
    from contextlib import contextmanager

    _, _, _, _, payloads = fixture_installation(tmp_path, monkeypatch)
    payload = payloads[1]
    approved = payload.read_bytes()
    payload.write_bytes(b"x" * len(approved))
    substitute = payload.parent / "approved-substitute"
    substitute.write_bytes(approved)
    original_path = payload.parent / "unapproved-original"
    original_open = capacity.Path.open
    swapped = []

    @contextmanager
    def transient_approved_file():
        payload.rename(original_path)
        substitute.replace(payload)
        try:
            with original_open(payload, "rb") as stream:
                yield stream
        finally:
            payload.rename(substitute)
            original_path.replace(payload)

    def open_file(path, *args, **kwargs):
        if path == payload and not swapped:
            swapped.append(True)
            return transient_approved_file()
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(capacity.Path, "open", open_file)
    with pytest.raises(capacity.CapacityUnavailable):
        capacity.observe_host(data_root=tmp_path, loaded=False)


@pytest.mark.parametrize(
    "damage",
    [
        "from",
        "media",
        "order",
        "extra-layer",
        "unknown-field",
        "runner",
        "schema-type",
        "size-type",
        "duplicate-json",
    ],
)
def test_structural_validation_is_independent_of_the_fixed_byte_hash(
    tmp_path, monkeypatch, damage
):
    wrapper, parent = _paths(tmp_path)
    value = json.loads(wrapper.read_bytes())
    if damage == "from":
        value["layers"][0]["from"] = "other.gguf"
    elif damage == "media":
        value["config"]["mediaType"] = "unexpected"
    elif damage == "order":
        value["layers"][0], value["layers"][1] = value["layers"][1], value["layers"][0]
    elif damage == "extra-layer":
        value["layers"].append(value["layers"][0])
    elif damage == "unknown-field":
        value["context"] = "not permitted"
    elif damage == "runner":
        value["runner"] = "mlx"
    elif damage == "schema-type":
        value["schemaVersion"] = 2.0
    elif damage == "size-type":
        value["layers"][0]["size"] = True
    raw = _encode(value)
    if damage == "duplicate-json":
        raw = raw.replace(
            b'{"schemaVersion":2,', b'{"schemaVersion":2,"schemaVersion":2,'
        )
    wrapper.write_bytes(raw)
    # Isolate the independent structural gate; production's byte allowlist is
    # immutable source, not a caller setting. This fixture grants no authority.
    monkeypatch.setattr(capacity, "_WRAPPER_MANIFEST_BYTES", len(raw))
    monkeypatch.setattr(capacity, "_WRAPPER_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(capacity.CapacityUnavailable):
        capacity._verify_model_manifests(wrapper, parent)
