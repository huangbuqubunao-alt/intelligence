"""Pinned 9B research harness. Preparing a case never contacts a provider.

Real execution requires a separately supplied installation/review/start receipt.
This module is not imported by the product and cannot mint production authority.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import runpy
import shutil
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    DistillationCommand,
    DistillationTransportResult,
    KnownLocalDistillationResponseError,
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
    _Candidate,
    _NoNewCandidate,
)
from youtube_intel.runtime_composition import ProductionDistillationBudget
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.state import ArtifactKind, DistillationStyle, SQLiteStateRepository

PROJECT = Path(__file__).resolve().parents[1]
DOCS = PROJECT / "docs/validation/end-to-end-user-readiness"
V1_PROFILE_ID = "readiness-qwen35-9b-official-nonthinking-v1"
V2_PROFILE_ID = "readiness-qwen35-9b-official-thinking-v2"
V3_PROFILE_ID = "readiness-qwen35-9b-thinking-capacity6144-single-v3"
CAPACITY_BASELINE_ROOT = Path(
    "/Users/hua/Documents/yia-worktrees/readiness-qwen35-thinking-v2"
    "/.var/readiness-qwen35/readiness-qwen35-9b-official-thinking-v2/real-deepthink-en"
)
PROFILE_ID = V1_PROFILE_ID
THINK = False
MODEL = "qwen3.5:9b-q4_K_M"
DIGEST = "sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90"
PROFILE_PATH = DOCS / "QWEN35_RESEARCH_PROFILE_V1.json"
FREEZE_PATH = DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V1.json"
SOURCE_RUNTIME = Path(
    "/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness"
    "/.var/end-to-end-user-readiness/runtime"
)
CASE_IDS = (
    "real-deepthink-en",
    "real-deepthink-zh-cn",
    "no-new-fifteen",
    "source-injection",
)
CORPORA = {
    "INTELLIGENCE_REAL_CORPUS_V2.json": "a7c96ee6b84aee6b8e492348b9f4f190d7c9f6f14241b25e533532bc4dcb82cb",
    "INTELLIGENCE_FROZEN_CORPUS.json": "cededc0061c43029e28a867bbaeab5ae5691c3e6a998997ace855eebb6dd37f3",
}
OPTIONS: dict[str, object] = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
    "repeat_penalty": 1.0,
    "seed": 20261013,
    "num_ctx": 8192,
    "num_predict": 4096,
}
CASE_ROOT = PROJECT / ".var/readiness-qwen35" / PROFILE_ID


def historical_timed_input_projection(value: VerifiedDistillationInput) -> dict[str, object]:
    """Export the exact pre-39 research input; never adapt a new input contract."""
    raw = asdict(value)
    expected = {"source_display_name", "video_id", "video_title", "evidence", "personalization",
        "source_focus_rules", "source_ignore_rules", "distillation_style", "selected_provider", "selected_model",
        "semantic_hash", "output_language", "content_provider", "local_content_context_hash",
        "wire_version", "input_json", "context_json", "local_profile_id", "local_profile_hash"}
    defaults = {"wire_version", "input_json", "context_json", "local_profile_id", "local_profile_hash"}
    if (type(value) is not VerifiedDistillationInput or set(raw) != expected
        or raw["content_provider"] != "YOUTUBE" or raw["local_content_context_hash"] is not None
        or any(raw[key] is not None for key in defaults) or not value.evidence):
        raise ValueError("historical research export requires the original YT timed contract")
    ranges = {"start_offset", "end_offset", "start_line", "end_line", "source_content_hash"}
    original = {"evidence_id", "start_ms", "end_ms", "excerpt", "excerpt_hash", "timed_transcript_id", "timed_transcript_hash"}
    for item in raw["evidence"]:
        if (set(item) != original | ranges | {"locator_type"} or item["locator_type"] != "TIMED_MEDIA"
            or type(item["start_ms"]) is not int or type(item["end_ms"]) is not int
            or any(item[key] is not None for key in ranges)):
            raise ValueError("historical research export cannot discard nondefault locators")
    return {key: tuple({name: item[name] for name in item if name in original} for item in raw["evidence"])
        if key == "evidence" else child for key, child in raw.items() if key not in defaults}


def select_profile(profile: str) -> None:
    """Choose only a fixed research variant; no product runtime uses this module."""
    global PROFILE_ID, THINK, OPTIONS, PROFILE_PATH, FREEZE_PATH, CASE_ROOT
    if profile not in {V1_PROFILE_ID, V2_PROFILE_ID, V3_PROFILE_ID}:
        raise ValueError("research profile is outside the approved scope")
    PROFILE_ID = profile
    THINK = profile in {V2_PROFILE_ID, V3_PROFILE_ID}
    OPTIONS = {**OPTIONS, "temperature": 1.0 if THINK else 0.7,
               "top_p": 0.95 if THINK else 0.8,
               "num_predict": 6144 if profile == V3_PROFILE_ID else 4096}
    version = "V3" if profile == V3_PROFILE_ID else "V2" if THINK else "V1"
    PROFILE_PATH = DOCS / f"QWEN35_RESEARCH_PROFILE_{version}.json"
    FREEZE_PATH = DOCS / f"QWEN35_PRE_OUTPUT_FREEZE_{version}.json"
    CASE_ROOT = PROJECT / ".var/readiness-qwen35" / PROFILE_ID


def require_case_scope(case_id: str) -> None:
    if PROFILE_ID == V3_PROFILE_ID and case_id != CASE_IDS[0]:
        raise ValueError("only the single approved English capacity case is authorized")


def validate_capacity_baseline() -> dict[str, Any]:
    """Read fixed public input/audit hashes; never read the private response."""
    failure = read_object(DOCS / "QWEN35_THINKING_V2_FAILURE.json")
    for name, key in (("request.json", "request_sha256"), ("prepared.json", "prepared_sha256"),
                      ("result.json", "result_sha256")):
        if sha256(CAPACITY_BASELINE_ROOT / name) != failure[key]:
            raise ValueError("original V2 audit evidence changed")
    prepared = read_object(CAPACITY_BASELINE_ROOT / "prepared.json")
    old_freeze = read_object(DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V2.json")
    old_tree = CAPACITY_BASELINE_ROOT.parents[3]
    if (prepared["profile"] != V2_PROFILE_ID or prepared["case"] != CASE_IDS[0]
        or prepared["production_qualified"] is not False
        or sha256(CAPACITY_BASELINE_ROOT / "verified-input.json") != prepared["verified_input_sha256"]
        or prepared["harness_sha256"] != old_freeze["files"]["scripts/qualify_readiness_qwen35_intelligence.py"]
        or sha256(old_tree / "scripts/qualify_readiness_qwen35_intelligence.py") != prepared["harness_sha256"]
        or len(prepared["prepared_data_hashes"]) != 18):
        raise ValueError("original V2 sealed input or harness changed")
    actual = {str(p.relative_to(CAPACITY_BASELINE_ROOT / "data")): sha256(p)
              for p in (CAPACITY_BASELINE_ROOT / "data").rglob("*") if p.is_file()}
    if actual != prepared["prepared_data_hashes"]:
        raise ValueError("original V2 complete DATA changed")
    return prepared


def capacity_expected_request() -> dict[str, Any]:
    validate_capacity_baseline()
    request = read_object(CAPACITY_BASELINE_ROOT / "request.json")
    return {**request, "options": {**request["options"], "num_predict": 6144}}


def capacity_request_projection(value: VerifiedDistillationInput) -> dict[str, Any]:
    """Capture ordinary v5 wire locally; this adapter has no provider operations."""
    class Projection(OllamaLocalDistillationTransport):
        _MODEL = MODEL
        _DIGEST = DIGEST
        body: dict[str, Any]

        def _request(self, path: str, *, method: str, body: Mapping[str, object] | None = None) -> Mapping[str, object]:
            if path != "/api/chat" or method != "POST" or body is None:
                raise ValueError("unexpected offline projection operation")
            self.body = {**body, "think": True, "options": dict(OPTIONS)}
            return {"model": MODEL, "done": True, "message": {"content": "{}"}}
    transport = Projection(settings=LocalScoringSettings(model=MODEL, expected_model_digest=DIGEST))
    transport.generate(value)
    if transport.body != capacity_expected_request():
        raise ValueError("capacity request projection differs beyond num_predict")
    return transport.body


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("research document must be an object")
    return value


def write_once(path: Path, value: object) -> None:
    """Exclusive audit write, durable before returning; never replace evidence."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_profile() -> dict[str, Any]:
    if (
        Path(inspect.getfile(PersonalizedDistillationService)).resolve()
        != (PROJECT / "src/youtube_intel/distillation.py").resolve()
    ):
        raise ValueError(
            "research must import the frozen worktree source via PYTHONPATH=src"
        )
    profile = read_object(PROFILE_PATH)
    if (
        profile.get("profile") != PROFILE_ID
        or profile.get("actual_provider") != "ollama"
        or profile.get("actual_model") != MODEL
        or profile.get("expected_manifest_digest") != DIGEST
        or profile.get("installed_runtime") != "0.40.1"
        or profile.get("production_qualified") is not False
        or profile.get("prompt_version")
        != OllamaLocalDistillationTransport._PROMPT_VERSION
        or profile.get("request_parameters") != {"think": THINK, **OPTIONS}
        or [entry["case"] for entry in profile["case_order"]] != list(CASE_IDS[:1] if PROFILE_ID == V3_PROFILE_ID else CASE_IDS)
    ):
        raise ValueError("frozen research profile changed")
    schema = json.dumps(
        OllamaLocalDistillationTransport._SCHEMA, sort_keys=True, separators=(",", ":")
    )
    if hashlib.sha256(schema.encode()).hexdigest() != profile["schema_sha256"]:
        raise ValueError("ordinary wire schema changed")
    if PROFILE_ID == V2_PROFILE_ID:
        original = read_object(DOCS / "QWEN35_RESEARCH_PROFILE_V1.json")
        if (type(profile["request_parameters"].get("think")) is not bool
            or profile.get("policy") != original["policy"]
            or profile.get("case_order") != original["case_order"]
            or profile.get("legacy_applicability_conflict") != original["legacy_applicability_conflict"]):
            raise ValueError("original input/semantic policy or native thinking type changed")
    if PROFILE_ID == V3_PROFILE_ID:
        original = read_object(DOCS / "QWEN35_RESEARCH_PROFILE_V2.json")
        expected = {"authorized_cases": [CASE_IDS[0]], "maximum_generations": 1,
            "stop_after_any_outcome": True, "request_timeout_seconds": 300,
            "baseline_profile": V2_PROFILE_ID,
            "baseline_request_sha256": read_object(DOCS / "QWEN35_THINKING_V2_FAILURE.json")["request_sha256"]}
        if (json.dumps(profile.get("capacity_single"), sort_keys=True) != json.dumps(expected, sort_keys=True)
            or json.dumps(profile["request_parameters"], sort_keys=True) != json.dumps({"think": True, **OPTIONS}, sort_keys=True)
            or type(profile["request_parameters"].get("think")) is not bool
            or any(profile.get(k) != original[k] for k in (
                "policy", "legacy_applicability_conflict", "representation_adapter",
                "actual_model", "expected_manifest_digest", "installed_runtime", "prompt_version", "schema_sha256"))
            or profile["case_order"] != original["case_order"][:1]):
            raise ValueError("single capacity profile changed original policy or scope")
    return profile


def load_case(case_id: str) -> dict[str, Any]:
    require_case_scope(case_id)
    if case_id not in CASE_IDS:
        raise ValueError("case is outside the frozen four-case research scope")
    entry = next(
        entry for entry in load_profile()["case_order"] if entry["case"] == case_id
    )
    name = entry["corpus"]
    if (
        name not in CORPORA
        or entry["sha256"] != CORPORA[name]
        or sha256(DOCS / name) != CORPORA[name]
    ):
        raise ValueError("original frozen corpus changed")
    return cast(
        dict[str, Any],
        next(c for c in read_object(DOCS / name)["cases"] if c["id"] == case_id),
    )


def validate_freeze() -> dict[str, Any]:
    freeze = read_object(FREEZE_PATH)
    if (
        freeze.get("profile") != PROFILE_ID
        or freeze.get("production_qualified") is not False
    ):
        raise ValueError("invalid research freeze identity")
    files = freeze.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("pre-output code/input hashes missing")
    if PROFILE_ID == V2_PROFILE_ID:
        old = read_object(DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V1.json")
        required = set(old["files"]) | {
            str(path.relative_to(PROJECT)) for path in (PROFILE_PATH,
                DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V1.json", DOCS / "MODEL_REPLACEMENT_INSTALL_RECEIPT.json",
                DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json", DOCS / "QWEN35_THINKING_FOLLOWUP_PROPOSAL.md",
                DOCS / "QWEN35_THINKING_FOLLOWUP_APPROVAL.md")}
        generate_hash = hashlib.sha256(inspect.getsource(OllamaLocalDistillationTransport.generate).encode()).hexdigest()
        if not required <= files.keys() or generate_hash != old["ordinary_v5_generate_sha256"]:
            raise ValueError("complete code/old-policy/runtime freeze or original v5 generate missing")
    if PROFILE_ID == V3_PROFILE_ID:
        old = read_object(DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V2.json")
        required = set(old["files"]) | {str(p.relative_to(PROJECT)) for p in (
            PROFILE_PATH, DOCS / "QWEN35_PRE_OUTPUT_FREEZE_V2.json",
            DOCS / "QWEN35_THINKING_V2_FAILURE.json", DOCS / "QWEN35_CAPACITY_SINGLE_CASE_PROPOSAL.md",
            PROJECT / "tests/unit/test_readiness_qwen35_capacity.py",
            PROJECT / "tasks/TASK-READINESS-QWEN35-CAPACITY-SINGLE.md")}
        original_generate = hashlib.sha256(inspect.getsource(OllamaLocalDistillationTransport.generate).encode()).hexdigest()
        if (not required <= files.keys() or original_generate != old["ordinary_v5_generate_sha256"]
            or freeze.get("ordinary_v5_generate_sha256") != original_generate
            or freeze.get("request_parameters") != {"think": THINK, **OPTIONS}
            or freeze.get("request_timeout_seconds") != 300):
            raise ValueError("complete single capacity freeze missing")
        for relative, expected in old["files"].items():
            if relative != "scripts/qualify_readiness_qwen35_intelligence.py" and files[relative] != expected:
                raise ValueError("original core, policy or contracts changed")
        baseline = validate_capacity_baseline()
        if freeze.get("baseline") != {"prepared_sha256": sha256(CAPACITY_BASELINE_ROOT / "prepared.json"),
            "request_sha256": sha256(CAPACITY_BASELINE_ROOT / "request.json"),
            "verified_input_sha256": baseline["verified_input_sha256"],
            "harness_sha256": baseline["harness_sha256"], "prepared_data_hashes": baseline["prepared_data_hashes"]}:
            raise ValueError("single capacity original sealed snapshot missing")
    for relative, expected in files.items():
        path = PROJECT / relative
        if path.resolve().is_relative_to(PROJECT) is False or sha256(path) != expected:
            raise ValueError("frozen code/input changed")
    return freeze


def validate_execution_permit(path: Path, case_id: str) -> dict[str, Any]:
    """A manual external receipt is a prerequisite, not a production credential."""
    require_case_scope(case_id)
    permit = read_object(path)
    if (
        case_id not in CASE_IDS
        or permit.get("pre_output_review") != "APPROVE"
        or permit.get("root_start_authorized") is not True
        or permit.get("all_installed_blob_hashes_verified") is not True
    ):
        raise ValueError("research execution is not authorized")
    expected = {
        "status": "APPROVED_ISOLATED_GENERATION",
        "case": case_id,
        "pre_output_review": "APPROVE",
        "root_start_authorized": True,
        "installed_manifest_verified": True,
        "all_installed_blob_hashes_verified": True,
        "runtime_parameters_verified": True,
        "installed_runtime": "0.40.1",
        "actual_provider": "ollama",
        "actual_model": MODEL,
        "manifest_digest": DIGEST,
        "profile": PROFILE_ID,
        "production_qualified": False,
        "cloud_authorized": False,
        "harness_sha256": sha256(Path(__file__)),
        "profile_sha256": sha256(PROFILE_PATH),
        "freeze_sha256": sha256(FREEZE_PATH),
        "prepared_sha256": sha256(CASE_ROOT / case_id / "prepared.json"),
    }
    if any(
        type(permit.get(key)) is not type(value) or permit.get(key) != value
        for key, value in expected.items()
    ):
        raise ValueError(
            "research execution is not authorized by the exact review/install/start receipt"
        )
    if (
        type(permit.get("post_install_free_bytes")) is not int
        or permit["post_install_free_bytes"] < 10 * 1024**3
    ):
        raise ValueError("installation free-space receipt is missing")
    validate_freeze()
    load_case(case_id)
    validate_prior_semantic_reviews(case_id, permit.get("prior_semantic_reviews"))
    if PROFILE_ID in {V2_PROFILE_ID, V3_PROFILE_ID}:
        runtime = read_object(DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json")
        v2_expected = {
            "exclusive_heavyweight_execution_confirmed": True,
            "no_unresolved_prior_heavyweight_execution": True,
            "runtime_parameters_verified_meaning": runtime["runtime_parameters_verified_meaning"],
            "runtime_static_provenance_sha256": sha256(DOCS / "QWEN35_RUNTIME_STATIC_PROVENANCE.json"),
            "installation_receipt_sha256": sha256(DOCS / "MODEL_REPLACEMENT_INSTALL_RECEIPT.json"),
        }
        if any(type(permit.get(k)) is not type(v) or permit.get(k) != v for k, v in v2_expected.items()):
            raise ValueError("exact V2 runtime/static support and exclusive execution receipt missing")
    if PROFILE_ID == V3_PROFILE_ID:
        single = {"single_case_only": True, "maximum_generations": 1,
            "authorized_case_ids": [CASE_IDS[0]],
            "request_projection_sha256": sha256(CASE_ROOT / case_id / "request-projection.json"),
            "baseline_request_sha256": sha256(CAPACITY_BASELINE_ROOT / "request.json")}
        if any(type(permit.get(k)) is not type(v) or permit.get(k) != v for k, v in single.items()):
            raise ValueError("exact external single-case request permit missing")
    return permit


def validate_prior_semantic_reviews(case_id: str, prior: object) -> None:
    require_case_scope(case_id)
    if case_id not in CASE_IDS:
        raise ValueError("case is outside the frozen research order")
    required = CASE_IDS[: CASE_IDS.index(case_id)]
    if not isinstance(prior, list) or any(not isinstance(r, dict) for r in prior) or [
        r.get("case") for r in prior
    ] != list(required):
        raise ValueError("prior independent semantic review receipts missing")
    for review in prior:
        result_path = CASE_ROOT / review["case"] / "result.json"
        expected_status = (
            "SUCCEEDED"
            if review["case"].startswith("real-")
            else "SUCCEEDED_NO_NEW_INTELLIGENCE"
        )
        result = read_object(result_path)
        if PROFILE_ID == V2_PROFILE_ID and (
            result.get("profile") != PROFILE_ID or result.get("case") != review["case"]
            or result.get("actual_model") != MODEL or result.get("manifest_digest") != DIGEST
            or result.get("outcome", {}).get("invocation_count") != 1):
            raise ValueError("prior result is not the exact V2 one-call case")
        if (
            review.get("verdict") != "PASS"
            or review.get("result_sha256") != sha256(result_path)
            or result.get("outcome", {}).get("status") != expected_status
            or result.get("production_qualified") is not False
            or result.get("generations") != 1
        ):
            raise ValueError("prior case is not independently semantically accepted")


class Qwen35ResearchTransport(OllamaLocalDistillationTransport):
    """Actual fixed 9B identity; unchanged v5 prompt/schema and no authority grant."""

    _MODEL = MODEL
    _DIGEST = DIGEST
    profile_id = PROFILE_ID

    def __init__(self, *, root: Path, execute_authorized: bool = False) -> None:
        load_profile()
        super().__init__(
            settings=LocalScoringSettings(model=MODEL, expected_model_digest=DIGEST)
        )
        self.profile_id = PROFILE_ID
        self.root = root
        self.execute_authorized = execute_authorized
        self.generations = 0
        self._output_limit_observed = False

    @property
    def available(self) -> bool:
        return self.execute_authorized and super().available

    def generate(self, value: VerifiedDistillationInput) -> DistillationTransportResult:
        if not self.execute_authorized:
            raise RuntimeError("research generation is not authorized")
        if self.profile_id != PROFILE_ID:
            raise ValueError("research transport profile changed before dispatch")
        load_profile()
        if self.generations or (self.root / "generation.started.json").exists():
            raise RuntimeError(
                "research case may dispatch only once, including after restart"
            )
        result = super().generate(value)
        if THINK and self._output_limit_observed:
            raise KnownLocalDistillationResponseError("LOCAL_RESPONSE_TRUNCATED", result)
        return result

    def _request(
        self, path: str, *, method: str, body: Mapping[str, object] | None = None
    ) -> Mapping[str, object]:
        if not self.execute_authorized:
            raise RuntimeError("research provider access is not authorized")
        if path == "/api/chat":
            if (
                body is None
                or body.get("model") != MODEL
                or body.get("format") != self._SCHEMA
            ):
                raise ValueError("research request identity/schema changed")
            body = {**body, "think": THINK, "options": dict(OPTIONS)}
            if PROFILE_ID == V3_PROFILE_ID and body != capacity_expected_request():
                raise ValueError("single capacity request changed before dispatch")
            try:
                write_once(
                    self.root / "generation.started.json",
                    {"profile": PROFILE_ID, "model": MODEL, "manifest": DIGEST},
                )
            except FileExistsError as error:
                raise RuntimeError("research case may dispatch only once") from error
            self.generations += 1
            write_once(self.root / "request.json", body)
        response = super()._request(path, method=method, body=body)
        if path == "/api/chat":
            # Preserve opaque provider raw response. Never inspect/display thinking.
            write_once(self.root / "response.json", response)
            # A known raw output cap is a rejection fact even when the input
            # counter is absent. Keep accounting's paired unknown counts intact.
            outputs = response.get("eval_count")
            self._output_limit_observed = (
                type(outputs) is int and outputs >= cast(int, OPTIONS["num_predict"])
            )
        return response


def decode_marker(
    raw: str,
    command: DistillationCommand,
    value: VerifiedDistillationInput,
    transport: Qwen35ResearchTransport,
) -> str:
    """Only decode the approved representation marker; preserve every claim field."""
    if (
        command.selected_provider != "ollama"
        or value.selected_provider != "ollama"
        or command.selected_model != MODEL
        or value.selected_model != MODEL
        or transport.actual_provider != "ollama"
        or transport.actual_model != MODEL
        or transport._MODEL != MODEL
        or transport._DIGEST != DIGEST
        or transport._settings.expected_model_digest != DIGEST
        or transport.profile_id != PROFILE_ID
        or transport._production_qualified
    ):
        raise ValueError("research marker decoder identity/profile is not authorized")
    payload = json.loads(raw)
    if (
        isinstance(payload, dict)
        and set(payload) == {"result", "evidence"}
        and payload["result"] == "NO_NEW_INTELLIGENCE"
    ):
        return raw  # Ordinary parser alone checks complete unchanged Evidence coverage.
    expected = cast(
        list[str], OllamaLocalDistillationTransport._INTELLIGENCE_SCHEMA["required"]
    )
    if (
        not isinstance(payload, dict)
        or set(payload) != set(expected)
        or payload["result"] != "INTELLIGENCE"
    ):
        raise ValueError("research marker wire shape is invalid")
    return json.dumps(
        {key: value for key, value in payload.items() if key != "result"},
        ensure_ascii=False,
    )


class Qwen35ResearchService(PersonalizedDistillationService):
    def _parse_candidate(
        self,
        raw: str,
        command: DistillationCommand,
        verified_input: VerifiedDistillationInput,
    ) -> _Candidate | _NoNewCandidate:
        if not isinstance(self._transport, Qwen35ResearchTransport):
            raise ValueError(
                "research service requires the exact fixed model transport"
            )
        return super()._parse_candidate(
            decode_marker(raw, command, verified_input, self._transport),
            command,
            verified_input,
        )


def setup_case(
    case: dict[str, Any], root: Path, now: datetime
) -> tuple[SQLiteStateRepository, str, str]:
    if "public_source_url" not in case:
        # Reuse only the existing synthetic input builder, never its transport/calibration.
        setup = cast(
            Callable[
                [dict[str, Any], Path, datetime], tuple[SQLiteStateRepository, str, str]
            ],
            runpy.run_path(
                str(PROJECT / "scripts/qualify_readiness_local_intelligence.py")
            )["setup"],
        )
        return setup(case, root, now)
    database, data = root / "state.sqlite3", root / "data"
    with sqlite3.connect(
        f"{(SOURCE_RUNTIME / 'state.sqlite3').as_uri()}?mode=ro", uri=True
    ) as source:
        with sqlite3.connect(database) as destination:
            source.backup(destination)
    shutil.copytree(SOURCE_RUNTIME / "data", data)
    repository = SQLiteStateRepository(database)
    repository.bind_source_storage(data)
    video = str(case["public_video_id"])
    source_id = next(
        s.source_id
        for s in repository.list_source_subscriptions()
        if s.video_id == video
    )
    timed = repository.get_verified_timed_transcript(video_id=video)
    artifact = repository.latest_artifact(video, ArtifactKind.TRANSCRIPT_CANONICAL)
    if (
        timed is None
        or [dict(start_ms=c.start_ms, end_ms=c.end_ms, text=c.text) for c in timed.cues]
        != case["timed_segments"]
        or artifact is None
        or artifact.content_hash != case["canonical_sha256"]
        or sha256(data / artifact.relative_path) != case["canonical_sha256"]
    ):
        raise ValueError("isolated source no longer matches the frozen real source")
    return repository, source_id, video


def make_service(
    repository: SQLiteStateRepository,
    case: dict[str, Any],
    root: Path,
    *,
    execute: bool = False,
) -> tuple[Qwen35ResearchService, Qwen35ResearchTransport]:
    policy = SourcePolicyApplicationService(repository, now=lambda: datetime.now(UTC))
    transport = Qwen35ResearchTransport(root=root, execute_authorized=execute)
    service = Qwen35ResearchService(
        repository,
        policy,
        transport,
        ProductionDistillationBudget(),
        now=lambda: datetime.now(UTC),
        output_language_for_video=lambda _: str(case["output_language"]),
    )
    return service, transport


def prepare_case(case_id: str, prior_reviews_path: Path | None = None) -> dict[str, Any]:
    require_case_scope(case_id)
    validate_freeze()
    if PROFILE_ID == V2_PROFILE_ID:
        prior_receipt = read_object(prior_reviews_path) if prior_reviews_path else None
        if prior_receipt is not None and (
            prior_receipt.get("profile") != PROFILE_ID
            or prior_receipt.get("harness_sha256") != sha256(Path(__file__))
            or prior_receipt.get("freeze_sha256") != sha256(FREEZE_PATH)
        ):
            raise ValueError("prior preparation review receipt identity changed")
        prior = prior_receipt.get("prior_semantic_reviews") if prior_receipt else []
        validate_prior_semantic_reviews(case_id, prior)
    baseline = validate_capacity_baseline() if PROFILE_ID == V3_PROFILE_ID else None
    if baseline is not None:
        actual = {str(p.relative_to(SOURCE_RUNTIME / "data")): sha256(p)
                  for p in (SOURCE_RUNTIME / "data").rglob("*") if p.is_file()}
        if actual != baseline["prepared_data_hashes"]:
            raise ValueError("isolated source no longer matches all original DATA")
    case = load_case(case_id)
    root = CASE_ROOT / case_id
    root.mkdir(parents=True, exist_ok=False)
    repository, source, video = setup_case(case, root, datetime.now(UTC))
    if case.get("focus_rules"):
        SourcePolicyApplicationService(
            repository, now=lambda: datetime.now(UTC)
        ).update_global(
            command_id="frozen-case-focus",
            initial_history_count=5,
            per_run_max_new_videos=5,
            focus_rules=tuple(case["focus_rules"]),
            ignore_rules=(),
            distillation_style=DistillationStyle.BALANCED,
        )
    service, _ = make_service(repository, case, root)
    evidence = repository.list_canonical_coverage_evidence_ids(video_id=video)
    reservation = service.reserve_distillation_execution(
        source_id=source,
        video_id=video,
        evidence_ids=evidence,
        manual_command_id="qualification-" + PROFILE_ID
        if "public_source_url" in case
        else None,
    )
    execution = repository.get_distillation_execution(reservation.execution_id)
    if execution is None:
        raise ValueError("prepared immutable reservation is missing")
    _, verified = service._reserved_command_from_record(execution)
    write_once(root / "verified-input.json", historical_timed_input_projection(verified))
    record = {
        "case": case_id,
        "profile": PROFILE_ID,
        "actual_model": MODEL,
        "manifest_digest": DIGEST,
        "production_qualified": False,
        "source": source,
        "video": video,
        "evidence_count": len(evidence),
        "execution_id": reservation.execution_id,
        "profile_sha256": sha256(PROFILE_PATH),
        "freeze_sha256": sha256(FREEZE_PATH),
        "harness_sha256": sha256(Path(__file__)),
        "verified_input_sha256": sha256(root / "verified-input.json"),
        "prepared_database_sha256": sha256(root / "state.sqlite3"),
        "prepared_data_hashes": {
            str(p.relative_to(root / "data")): sha256(p)
            for p in sorted((root / "data").rglob("*"))
            if p.is_file()
        },
    }
    if baseline is not None:
        if (record["verified_input_sha256"] != baseline["verified_input_sha256"]
            or record["prepared_data_hashes"] != baseline["prepared_data_hashes"]
            or record["execution_id"] == baseline["execution_id"]):
            raise ValueError("single capacity must preserve original input in a fresh execution")
        write_once(root / "request-projection.json", capacity_request_projection(verified))
        record.update(request_projection_sha256=sha256(root / "request-projection.json"),
            baseline_request_sha256=sha256(CAPACITY_BASELINE_ROOT / "request.json"))
    write_once(root / "prepared.json", record)
    return record


def execute_case(case_id: str, permit_path: Path) -> dict[str, Any]:
    require_case_scope(case_id)
    if PROFILE_ID != V3_PROFILE_ID:
        raise ValueError("the retired V1/V2 experiment cannot be executed again")
    permit = validate_execution_permit(permit_path, case_id)
    root = CASE_ROOT / case_id
    prepared = read_object(root / "prepared.json")
    for key in ("harness_sha256", "profile_sha256", "freeze_sha256"):
        if prepared.get(key) != permit[key]:
            raise ValueError("prepared research identity changed")
    if (
        prepared.get("case") != case_id
        or prepared.get("actual_model") != MODEL
        or prepared.get("production_qualified") is not False
    ):
        raise ValueError("prepared case identity changed")
    if prepared["prepared_database_sha256"] != sha256(root / "state.sqlite3"):
        raise ValueError(
            "prepared database changed; never replay an uncertain execution"
        )
    if prepared["verified_input_sha256"] != sha256(root / "verified-input.json"):
        raise ValueError("frozen verified input changed")
    for relative, expected in prepared["prepared_data_hashes"].items():
        if sha256(root / "data" / relative) != expected:
            raise ValueError("prepared isolated source artifact changed")
    baseline = validate_capacity_baseline()
    actual_data = {str(p.relative_to(root / "data")): sha256(p)
                   for p in (root / "data").rglob("*") if p.is_file()}
    if (prepared.get("profile") != PROFILE_ID or prepared.get("manifest_digest") != DIGEST
        or prepared.get("source") != baseline["source"] or prepared.get("video") != baseline["video"]
        or prepared.get("evidence_count") != baseline["evidence_count"]
        or prepared["verified_input_sha256"] != baseline["verified_input_sha256"]
        or actual_data != baseline["prepared_data_hashes"]
        or prepared["prepared_data_hashes"] != actual_data
        or prepared.get("request_projection_sha256") != permit["request_projection_sha256"]
        or prepared.get("baseline_request_sha256") != permit["baseline_request_sha256"]
        or read_object(root / "request-projection.json") != capacity_expected_request()):
        raise ValueError("single capacity sealed input or projection changed")
    write_once(root / "execution-permit.json", permit)
    repository = SQLiteStateRepository(root / "state.sqlite3")
    repository.bind_source_storage(root / "data")
    service, transport = make_service(
        repository, load_case(case_id), root, execute=True
    )
    outcome = service.continue_qualification_reserved_distillation(
        prepared["execution_id"]
    )
    if transport.generations > 1:
        raise RuntimeError("research continuation is not idempotent")
    result = {
        **prepared,
        "outcome": asdict(outcome),
        "generations": transport.generations,
        "semantic_acceptance": "PENDING_INDEPENDENT_REVIEW",
        "production_qualified": False,
    }
    write_once(root / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=(V3_PROFILE_ID,))
    parser.add_argument("--case", required=True, choices=CASE_IDS[:1])
    parser.add_argument("--prior-reviews", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--execute-with-permit", type=Path)
    args = parser.parse_args()
    select_profile(args.profile)
    result = (
        prepare_case(args.case, args.prior_reviews)
        if args.prepare_only
        else execute_case(args.case, args.execute_with_permit)
    )
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
