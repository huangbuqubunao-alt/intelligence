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
PROFILE_ID = "readiness-qwen35-9b-official-nonthinking-v1"
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
        or profile.get("request_parameters") != {"think": False, **OPTIONS}
        or [entry["case"] for entry in profile["case_order"]] != list(CASE_IDS)
    ):
        raise ValueError("frozen research profile changed")
    schema = json.dumps(
        OllamaLocalDistillationTransport._SCHEMA, sort_keys=True, separators=(",", ":")
    )
    if hashlib.sha256(schema.encode()).hexdigest() != profile["schema_sha256"]:
        raise ValueError("ordinary wire schema changed")
    return profile


def load_case(case_id: str) -> dict[str, Any]:
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
    for relative, expected in files.items():
        path = PROJECT / relative
        if path.resolve().is_relative_to(PROJECT) is False or sha256(path) != expected:
            raise ValueError("frozen code/input changed")
    return freeze


def validate_execution_permit(path: Path, case_id: str) -> dict[str, Any]:
    """A manual external receipt is a prerequisite, not a production credential."""
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
    prior = permit.get("prior_semantic_reviews")
    required = CASE_IDS[: CASE_IDS.index(case_id)]
    if not isinstance(prior, list) or [
        r.get("case") for r in prior if isinstance(r, dict)
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
        if (
            review.get("verdict") != "PASS"
            or review.get("result_sha256") != sha256(result_path)
            or result.get("outcome", {}).get("status") != expected_status
            or result.get("production_qualified") is not False
            or result.get("generations") != 1
        ):
            raise ValueError("prior case is not independently semantically accepted")
    return permit


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
        self.root = root
        self.execute_authorized = execute_authorized
        self.generations = 0

    @property
    def available(self) -> bool:
        return self.execute_authorized and super().available

    def generate(self, value: VerifiedDistillationInput) -> DistillationTransportResult:
        if not self.execute_authorized:
            raise RuntimeError("research generation is not authorized")
        if self.generations or (self.root / "generation.started.json").exists():
            raise RuntimeError(
                "research case may dispatch only once, including after restart"
            )
        return super().generate(value)

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
            body = {**body, "think": False, "options": dict(OPTIONS)}
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


def prepare_case(case_id: str) -> dict[str, Any]:
    validate_freeze()
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
    write_once(root / "verified-input.json", asdict(verified))
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
    write_once(root / "prepared.json", record)
    return record


def execute_case(case_id: str, permit_path: Path) -> dict[str, Any]:
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
    write_once(root / "execution-permit.json", permit)
    repository = SQLiteStateRepository(root / "state.sqlite3")
    repository.bind_source_storage(root / "data")
    service, transport = make_service(
        repository, load_case(case_id), root, execute=True
    )
    outcome = service.continue_qualification_reserved_distillation(
        prepared["execution_id"]
    )
    repeat = service.continue_qualification_reserved_distillation(
        prepared["execution_id"]
    )
    if repeat != outcome or transport.generations > 1:
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
    parser.add_argument("--case", required=True, choices=CASE_IDS)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--execute-with-permit", type=Path)
    args = parser.parse_args()
    result = (
        prepare_case(args.case)
        if args.prepare_only
        else execute_case(args.case, args.execute_with_permit)
    )
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
