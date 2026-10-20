"""Production-builder preparation and reviewed once-only local execution.

Default CLI is describe-only. No corpus, source snapshot, capacity proof,
execution permit, or qualification is supplied by this implementation.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel import local_model_capacity as model_capacity
from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
    build_local_distillation_request,
    local_profile_for_scope,
    local_profile_projection,
    verified_distillation_input_projection,
)
from youtube_intel.local_distillation_profile import (
    PROFILE_ID,
    SCOPES,
    canonical,
    digest,
    resolve_profile,
)
from youtube_intel.local_distillation_qualification import (
    CASE_LANGUAGES,
    CaseReceipt,
    LocalExecutionPermit,
    SourceManifest,
    case_scope,
    qualification_binding,
    sha,
    strict_object,
)
from youtube_intel.runtime_composition import ProductionDistillationBudget
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.state import SQLiteStateRepository


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            result.update(chunk)
    return result.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("review document exceeds bounds")
    value = json.loads(raw, object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise ValueError("review document must be an object")
    return value


def write_once(path: Path, value: object) -> None:
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def describe() -> dict[str, object]:
    return {"version": "local-grounding-harness-v1", "profile_id": PROFILE_ID,
        "profiles": {scope: local_profile_for_scope(PROFILE_ID, scope) for scope in SCOPES},
        "production_qualified": False, "execution_authority": "NONE", "real_model_calls": 0,
        "freeze_status": "UNFROZEN_PENDING_CORE_AND_UI_ACCEPTANCE",
        "capacity_status": "REQUIRES_CURRENT_HOST_LOAD_ONLY_AND_SLOT_PREFLIGHT",
        "workspace_contract": "PRIVATE_SIBLING_<audit_name>.workspace/state.sqlite3_AND_data",
        "workspace_execution": "NO_GUI_API_OR_OTHER_BACKUP_PROCESS_ON_THIS_DATABASE",
        "case_order": CASE_LANGUAGES}


def request_projection(value: VerifiedDistillationInput) -> dict[str, object]:
    request = build_local_distillation_request(value)
    return {"request": request, "request_hash": digest(request),
        "binding": qualification_binding(local_profile_projection(value)),
        "input_hash": value.semantic_hash,
        "context_hash": value.local_content_context_hash or digest(request["messages"])}


def data_manifest(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("prepared DATA must not contain symlinks")
        if path.is_file():
            result[str(path.relative_to(root))] = file_hash(path)
    return result


def owned_workspace(audit_root: Path, case_id: str, database: Path, data_root: Path) -> dict[str, object]:
    """Dedicated private once workspace only; never an arbitrary application DB.

    This is an ownership/admission check, not qualification or a cross-process
    Backup lock. Freeze must additionally exclude GUI/API/Backup on this root.
    """
    if case_id not in {case for cases in CASE_LANGUAGES.values() for case in cases}:
        raise ValueError("unknown isolated workspace case")
    audit = audit_root.expanduser().absolute()
    root = audit.parent / (audit.name + ".workspace")
    database, data_root = database.expanduser().absolute(), data_root.expanduser().absolute()
    if database != root / "state.sqlite3" or data_root != root / "data":
        raise ValueError("once execution requires its dedicated sibling workspace")
    if any(path.resolve() != path for path in (audit, root, database, data_root)):
        raise ValueError("once workspace must not use symlink paths")
    stat = root.stat()
    db_stat, data_stat = database.stat(), data_root.stat()
    if (not root.is_dir() or not database.is_file() or not data_root.is_dir()
        or any(s.st_uid != os.geteuid() for s in (stat, db_stat, data_stat))
        or stat.st_mode & 0o077 or db_stat.st_nlink != 1
        or (root / ".intelligence-backup-restore/restore-state.json").exists()):
        raise ValueError("once workspace ownership or restore state is unsafe")
    result = subprocess.run(["/usr/sbin/lsof", "-nP", "-t", "--", str(database)],
        capture_output=True, text=True, timeout=5, check=False)
    pids = result.stdout.split()
    if (result.returncode not in (0, 1) or result.stderr.strip()
        or (result.returncode == 1 and pids) or (result.returncode == 0 and not pids)
        or any(not pid.isdecimal() or int(pid) != os.getpid() for pid in pids)):
        raise ValueError("another or unknown process holds the once database")
    return {"root": str(root), "case_id": case_id, "root_device": stat.st_dev,
        "root_inode": stat.st_ino, "database_device": db_stat.st_dev,
        "database_inode": db_stat.st_ino, "data_device": data_stat.st_dev,
        "data_inode": data_stat.st_ino}


def prepare_case(service: PersonalizedDistillationService, *, case_id: str, source_id: str,
    video_id: str, audit_root: Path, data_root: Path, database: Path) -> dict[str, object]:
    """Use the ordinary reservation and exact production input, with zero IO to Ollama."""
    ownership = owned_workspace(audit_root, case_id, database, data_root)
    if (service._repository._database_path.resolve() != database.resolve()
        or service._repository._source_data_root != data_root.resolve()):
        raise ValueError("preparation service is not bound to the isolated workspace")
    reservation = service.reserve_distillation_execution(source_id=source_id, video_id=video_id,
        evidence_ids=service._repository.list_canonical_coverage_evidence_ids(video_id),
        manual_command_id="grounding-" + case_id)
    record = service._repository.get_distillation_execution(reservation.execution_id)
    if record is None:
        raise ValueError("prepared reservation is missing")
    _, value = service._reserved_command_from_record(record)
    projection = request_projection(value)
    scope = str(local_profile_projection(value)["scope"])
    cases = CASE_LANGUAGES["YT_TIMED" if scope == "YT_TIMED" else "LOCAL"]
    if cases.get(case_id) != value.output_language or case_scope(case_id) != scope:
        raise ValueError("case scope/language is outside the fixed order")
    result = {"version": "local-grounding-prepared-v1", "case_id": case_id,
        "execution_id": reservation.execution_id, "source_id": source_id, "video_id": video_id,
        "workspace_ownership": ownership,
        "output_language": value.output_language, **projection,
        "verified_input": verified_distillation_input_projection(value),
        "database": str(database.resolve()), "database_hash": file_hash(database),
        "data_root": str(data_root.resolve()), "data_hashes": data_manifest(data_root),
        "harness_hash": file_hash(Path(__file__)), "production_qualified": False}
    audit_root.mkdir(parents=True, exist_ok=False)
    write_once(audit_root / "prepared.json", result)
    return result


def validate_execution_package(audit_root: Path, permit_path: Path, freeze_path: Path) -> tuple[dict[str, Any], LocalExecutionPermit, dict[str, Any]]:
    prepared, freeze = read_object(audit_root / "prepared.json"), read_object(freeze_path)
    if owned_workspace(audit_root, prepared["case_id"], Path(prepared["database"]), Path(prepared["data_root"])) != prepared.get("workspace_ownership"):
        raise ValueError("once workspace ownership changed")
    permit = LocalExecutionPermit.model_validate(read_object(permit_path))
    binding = prepared["binding"]
    current = qualification_binding(local_profile_for_scope(PROFILE_ID, binding["scope"]))
    if (freeze.get("version") != "local-grounding-freeze-v1" or freeze.get("status") != "PRE_OUTPUT_REVIEWED"
        or freeze.get("profile_id") != PROFILE_ID or prepared.get("production_qualified") is not False
        or prepared.get("harness_hash") != file_hash(Path(__file__)) or permit.harness_hash != file_hash(Path(__file__))
        or permit.freeze_hash != file_hash(freeze_path) or binding != current or permit.binding != current
        or permit.case_id != prepared["case_id"] or permit.execution_id != prepared["execution_id"]
        or permit.input_hash != prepared["input_hash"] or permit.context_hash != prepared["context_hash"]
        or permit.request_hash != digest(prepared["request"]) or permit.request_hash != prepared["request_hash"]
        or freeze.get("prepared_case_hashes", {}).get(permit.case_id) != file_hash(audit_root / "prepared.json")
        or not permit.matches(local_profile_for_scope(PROFILE_ID, binding["scope"]),
            prepared["input_hash"], prepared["request_hash"], prepared["output_language"])):
        raise ValueError("execution package is unreviewed, stale, or mismatched")
    cases = CASE_LANGUAGES["YT_TIMED" if binding["scope"] == "YT_TIMED" else "LOCAL"]
    if freeze.get("case_order") != list(cases) or set(freeze.get("prepared_case_hashes", {})) != set(cases):
        raise ValueError("complete independently frozen cases are missing")
    if (set(freeze.get("prepared_case_paths", {})) != set(cases)
        or set(freeze.get("source_manifest_paths", {})) != set(cases)
        or set(freeze.get("source_manifest_hashes", {})) != set(cases)):
        raise ValueError("complete prepared/source manifests are missing")
    frozen_sources = {}
    for case_id, language in cases.items():
        path = Path(freeze["prepared_case_paths"][case_id])
        entry = read_object(path)
        source = SourceManifest.model_validate(read_object(Path(freeze["source_manifest_paths"][case_id])))
        if (file_hash(path) != freeze["prepared_case_hashes"][case_id]
            or entry.get("case_id") != case_id or entry.get("output_language") != language
            or entry.get("binding") != qualification_binding(local_profile_for_scope(PROFILE_ID, case_scope(case_id)))
            or entry.get("harness_hash") != permit.harness_hash or entry.get("production_qualified") is not False
            or source.source_id != entry.get("source_id")
            or (source.input_hash, source.context_hash, source.request_hash)
            != (entry.get("input_hash"), entry.get("context_hash"), entry.get("request_hash"))
            or digest(source.model_dump()) != freeze["source_manifest_hashes"][case_id]
            or (case_id.startswith("holdout-") and (not source.unseen_for_profile
                or source.origin != "PUBLIC_SNAPSHOT" or source.selector_id == freeze.get("producer_id")))
            or (case_id.startswith("local-") and source.origin != "LOCAL_SNAPSHOT")):
            raise ValueError("a frozen source/input/profile is mismatched or lacks required provenance")
        frozen_sources[case_id] = source
    if binding["scope"] == "YT_TIMED":
        a, b = frozen_sources["holdout-a-en"], frozen_sources["holdout-b-en"]
        if (a.source_id == b.source_id or a.snapshot_hash == b.snapshot_hash
            or (a.source_id, a.snapshot_hash) != (frozen_sources["holdout-a-zh"].source_id, frozen_sources["holdout-a-zh"].snapshot_hash)
            or (b.source_id, b.snapshot_hash) != (frozen_sources["holdout-b-zh"].source_id, frozen_sources["holdout-b-zh"].snapshot_hash)):
            raise ValueError("independent distinct holdout source pairs are missing")
    for scope in {case_scope(case_id) for case_id in cases}:
        if freeze.get("bindings", {}).get(scope) != qualification_binding(local_profile_for_scope(PROFILE_ID, scope)):
            raise ValueError("complete production profile bindings are missing")
    prior = freeze.get("prior_receipt_paths", {})
    for index, case_id in enumerate(list(cases)[:list(cases).index(permit.case_id)]):
        receipt_path = Path(prior[case_id])
        receipt = CaseReceipt.model_validate(read_object(receipt_path))
        if (receipt.case_id != case_id or not receipt.passes(datetime.now(UTC))
            or file_hash(receipt_path) != permit.prior_review_hashes[index]
            or receipt.freeze_hash != permit.freeze_hash or receipt.harness_hash != permit.harness_hash):
            raise ValueError("a prior case lacks independent protocol and semantic PASS")
    if file_hash(Path(prepared["database"])) != prepared["database_hash"] or data_manifest(Path(prepared["data_root"])) != prepared["data_hashes"]:
        raise ValueError("prepared database or complete DATA changed")
    return prepared, permit, freeze


def available_memory_bytes() -> int:
    result = subprocess.run(["/usr/bin/vm_stat"], check=True, capture_output=True, text=True, timeout=5)
    page = re.search(r"page size of (\d+) bytes", result.stdout)
    if page is None:
        raise ValueError("available memory observation is unavailable")
    pages = sum(int(match.group(1)) for key in ("Pages free", "Pages inactive", "Pages speculative")
        if (match := re.search(rf"{key}:\s+(\d+)\.", result.stdout)) is not None)
    return int(page.group(1)) * pages


def verify_resources(audit_root: Path, freeze: Mapping[str, Any], permit: LocalExecutionPermit) -> None:
    runtime_path, capacity_path = Path(freeze["runtime_proof_path"]), Path(freeze["capacity_proof_paths"][permit.case_id])
    runtime, capacity = read_object(runtime_path), read_object(capacity_path)
    profile = resolve_profile(PROFILE_ID)
    prepared = read_object(audit_root / "prepared.json")
    # Independently supplied proof files cannot bypass the compiled production
    # capacity algorithm. Frozen proof files never substitute for the current
    # production host/load-only/slot preflight before the generation claim.
    bound = profile.complete_input_token_upper_bound(prepared["request"])
    if file_hash(runtime_path) != permit.runtime_proof_hash or file_hash(capacity_path) != permit.capacity_proof_hash:
        raise ValueError("runtime or complete-input capacity proof changed")
    if (capacity.get("status") != "INDEPENDENTLY_VERIFIED" or capacity.get("request_hash") != permit.request_hash
        or capacity.get("model_digest") != profile.model_digest or capacity.get("num_ctx") != 16384
        or type(capacity.get("complete_prompt_token_upper_bound")) is not int
        or capacity["complete_prompt_token_upper_bound"] != bound
        or not 0 < bound <= 16384 - 6144 - 1 or capacity.get("num_predict") != 6144
        or capacity.get("capacity_contract") != "qwen35-byte-vocabulary-chat-system-user-88-plus2-v1"
        or capacity.get("max_request_bytes") != 12288 or capacity.get("max_content_bytes") != 8192
        or capacity.get("full_input_preserved") is not True
        or capacity.get("method") != "QWEN35_COMPLETE_BYTE_VOCABULARY_UPPER_BOUND"
        or not isinstance(capacity.get("template_hash"), str) or not sha(capacity["template_hash"])
        or not isinstance(capacity.get("tokenizer_hash"), str) or not sha(capacity["tokenizer_hash"])
        or capacity.get("code_hash") != permit.binding["code_hash"]
        or capacity.get("profile_hash") != permit.binding["profile_hash"]
        or not capacity.get("reviewer_id") or capacity.get("reviewer_id") == capacity.get("producer_id")):
        raise ValueError("actual complete-input/tokenizer/template capacity is unverified")
    cache = Path(runtime["model_cache_root"])
    if runtime.get("runtime") != profile.runtime or cache.resolve() != (Path.home() / ".ollama/models").resolve():
        raise ValueError("installed runtime or model cache differs")
    # The legacy wrapper hash is not the API model identity. Reuse production's
    # pinned wrapper/parent/reference, every payload and binary, and fd identity.
    model_capacity.verify_installed_model_bytes(cache)
    total = sum(model_capacity.BLOBS.values())
    minimum_memory = runtime.get("required_available_memory_bytes")
    if (type(minimum_memory) is not int or minimum_memory < total + 2 * 1024**3
        or shutil.disk_usage(audit_root).free < 10 * 1024**3 or available_memory_bytes() < minimum_memory):
        raise ValueError("free disk or available memory is below the model resource budget")


def execute_case(audit_root: Path, permit_path: Path, freeze_path: Path) -> dict[str, object]:
    prepared, permit, freeze = validate_execution_package(audit_root, permit_path, freeze_path)
    profile = resolve_profile(PROFILE_ID)
    def claim(value: VerifiedDistillationInput, request: Mapping[str, object]) -> None:
        if owned_workspace(audit_root, permit.case_id, Path(prepared["database"]), Path(prepared["data_root"])) != prepared["workspace_ownership"]:
            raise ValueError("once workspace ownership changed before claim")
        if request != prepared["request"] or value.semantic_hash != prepared["input_hash"]:
            raise ValueError("production request differs from independently prepared bytes")
        write_once(audit_root / "dispatch.armed.json", {"permit_hash": permit.permit_hash,
            "request_hash": digest(request), "execution_id": permit.execution_id,
            "status": "ARMED", "generation_post_proven": False})
    transport = OllamaLocalDistillationTransport(settings=LocalScoringSettings(model=profile.model,
        expected_model_digest=profile.model_digest), local_profile_id=PROFILE_ID,
        qualification_permit=permit, before_dispatch=claim)
    repository = SQLiteStateRepository(Path(prepared["database"]))
    repository.bind_source_storage(Path(prepared["data_root"]))
    def now() -> datetime:
        return datetime.now(UTC)
    service = PersonalizedDistillationService(repository, SourcePolicyApplicationService(repository, now=now),
        transport, ProductionDistillationBudget(), now=now,
        output_language_for_video=lambda _: prepared["output_language"])
    with (audit_root.parent / "generation.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_resources(audit_root, freeze, permit)
        source = SourceManifest.model_validate(read_object(Path(freeze["source_manifest_paths"][permit.case_id])))
        if (digest(source.model_dump()) != permit.source_manifest_hash
            or (source.input_hash, source.context_hash, source.request_hash)
            != (permit.input_hash, permit.context_hash, permit.request_hash)
            or source.source_id != prepared["source_id"]
            or any(not sha(h) for h in (source.snapshot_hash, source.summary_hash, source.evidence_hash, source.policy_hash))
            or (permit.case_id.startswith("holdout-") and (not source.unseen_for_profile
                or source.origin != "PUBLIC_SNAPSHOT" or source.selector_id == freeze.get("producer_id")))
            or (permit.case_id.startswith("local-") and source.origin != "LOCAL_SNAPSHOT")):
            raise ValueError("independently frozen source manifest changed")
        outcome = service.continue_qualification_reserved_distillation(permit.execution_id)
        result = {"version": "local-grounding-result-v1", "case_id": permit.case_id,
            "execution_id": permit.execution_id, "outcome": asdict(outcome),
            "permit_hash": permit.permit_hash, "request_hash": permit.request_hash,
            "semantic_acceptance": "PENDING_INDEPENDENT_REVIEW", "production_qualified": False,
            "public_final": getattr(transport, "last_grounding_final", None),
            "generation_post_attempted_locally": transport.last_grounding_post_attempted,
            "opaque_raw_hash": getattr(transport, "last_grounding_raw_hash", None),
            "local_response_error": transport.last_grounding_response_error,
            "completion": getattr(transport, "last_grounding_completion", None)}
        # No QualificationRecord is emitted; an independent reviewer must bind
        # actual once/ledger/public-final evidence into a separate receipt.
        write_once(audit_root / "result.json", result)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--audit-root", type=Path)
    parser.add_argument("--permit", type=Path)
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(canonical(describe()).decode())
    elif args.audit_root is None or args.permit is None or args.freeze is None:
        parser.error("execution requires all reviewed audit/permit/freeze paths")
    else:
        print(canonical(execute_case(args.audit_root, args.permit, args.freeze)).decode())


if __name__ == "__main__":
    main()
