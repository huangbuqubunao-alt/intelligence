"""Reviewed package authority for one local profile; fixtures never qualify it.

Resource registration changes data only. Its bytes are deliberately excluded
from the execution code fingerprint. Historical input proofs do not use this
time-sensitive authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from importlib import resources
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from youtube_intel.local_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID as SHORT_CURRENT,
)
from youtube_intel.local_distillation_profile import PROFILE_ID, digest

LONG_CURRENT = "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.6-v2"
# Lazy long resolver below avoids distillation/projection import cycles.

VERSION = "local-distillation-qualification-v1"
CASE_LANGUAGES = {
    "YT_TIMED": {"real-deepthink-en": "en", "real-deepthink-zh-cn": "zh-CN",
        "no-new-fifteen": "zh-CN", "source-injection": "en",
        "holdout-a-en": "en", "holdout-a-zh": "zh-CN", "holdout-b-en": "en",
        "holdout-b-zh": "zh-CN", "holdout-no-new": "en", "holdout-injection": "zh-CN"},
    "LOCAL": {"local-timed-en": "en", "local-timed-zh": "zh-CN",
        "local-txt-en": "en", "local-txt-zh": "zh-CN", "local-md-en": "en",
        "local-md-zh": "zh-CN", "local-no-new": "en", "local-injection": "zh-CN"},
}
CODE_FILES = ("distillation.py", "local_distillation_profile.py", "local_distillation_qualification.py", "local_model_capacity.py",
    "providers/ollama_analysis.py", "providers/ollama_evidence_translation.py",
    "local_transcription_jobs.py", "backup_restore.py",
    "intelligence_read.py", "runtime_composition.py", "state.py", "source_policy.py",
    "source_authority.py", "extractive_summary.py", "domain.py",
    "migrations/039_add_local_text_input_proofs.sql",
    "long_distillation_persistence.py", "distillation_cancellation.py", "local_api.py", "processing_orchestrator.py", "long_grounding_codec.py", "long_grounding_projection.py",
    "long_distillation_profile.py", "long_card_canonical.py", "long_distillation_execution.py", "local_native_capacity.py",
    "local_intelligence_settings.py", "local_intelligence_catalog.py", "model_settings.py", "cli.py",
    "migrations/041_add_long_distillation_provenance.sql")
_PACKAGE_AUTHORITY_SEAL = object()


def qualification_projection(profile_id: str, scope: str) -> dict[str, object]:
    """Only reviewed finite identities; long binds its base schema/codec contract."""
    from youtube_intel.distillation import local_profile_for_scope
    from youtube_intel.long_distillation_profile import resolve_long_profile
    if scope not in {"YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"}:
        raise ValueError("unknown qualification scope")
    if profile_id in {PROFILE_ID, SHORT_CURRENT}:
        return local_profile_for_scope(profile_id, scope)
    if profile_id == LONG_CURRENT and scope == "YT_TIMED":
        descriptor = json.loads(resolve_long_profile(profile_id).profile_wire)
        return {**descriptor, "local_profile_id": profile_id, "digest": descriptor["model_digest"],
            "schema": descriptor["base_schema"], "input_contract": descriptor["schema_contract"]}
    raise ValueError("unknown qualification profile/scope")


def qualification_cases(projection: Mapping[str, object]) -> dict[str, str]:
    profile_id, scope = str(projection["local_profile_id"]), str(projection["scope"])
    if dict(projection) != qualification_projection(profile_id, scope):
        raise ValueError("qualification projection differs from finite contract")
    cases = dict(CASE_LANGUAGES["YT_TIMED" if scope == "YT_TIMED" else "LOCAL"])
    if profile_id == LONG_CURRENT:
        cases.update({"long-full-en": "en", "long-full-zh": "zh-CN"})
    return cases


def case_outcome(case_id: str) -> str:
    """Substantive positives cannot be substituted with a successful NO_NEW call."""
    return "NO_NEW" if case_id in {"no-new-fifteen", "source-injection", "holdout-no-new",
        "holdout-injection", "local-no-new", "local-injection"} else "INTELLIGENCE"


def case_scope(case_id: str, *, profile_id: str = PROFILE_ID) -> str:
    if profile_id == LONG_CURRENT and case_id in {"long-full-en", "long-full-zh"}:
        return "YT_TIMED"
    if case_id in CASE_LANGUAGES["YT_TIMED"]:
        return "YT_TIMED"
    if case_id in CASE_LANGUAGES["LOCAL"]:
        return "LOCAL_TIMED" if case_id.startswith("local-timed-") else "LOCAL_TEXT"
    raise ValueError("case is outside the fixed local profile scope")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("duplicate qualification key")
        value[key] = child
    return value


def sha(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{64}", value) is not None


def timestamp(value: str) -> datetime:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None or date.utcoffset() != timedelta(0):
        raise ValueError("qualification timestamp requires UTC")
    return date


def qualification_binding(projection: Mapping[str, object]) -> dict[str, str]:
    package = resources.files("youtube_intel")
    return {"profile_id": str(projection["local_profile_id"]), "profile_hash": digest(projection),
        "scope": str(projection["scope"]), "model": str(projection["model"]),
        "model_digest": str(projection["digest"]), "runtime": str(projection["runtime"]),
        "schema_hash": digest(projection["schema"]), "input_contract": str(projection["input_contract"]),
        "code_hash": digest({name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest() for name in CODE_FILES})}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SemanticReview(_Strict):
    reviewer_id: str = Field(min_length=1, max_length=200)
    case_id: str
    input_hash: str
    request_hash: str
    final_hash: str
    verdict: Literal["PASS", "FAIL"]
    reviewed_at: str
    review_hash: str
    outcome: Literal["INTELLIGENCE", "NO_NEW"] | None = None


class SourceManifest(_Strict):
    origin: Literal["PUBLIC_SNAPSHOT", "LOCAL_SNAPSHOT", "SYNTHETIC_CONTROL"]
    source_id: str = Field(min_length=1, max_length=512)
    snapshot_hash: str
    summary_hash: str
    evidence_hash: str
    policy_hash: str
    input_hash: str
    context_hash: str
    request_hash: str
    unseen_for_profile: bool
    selector_id: str = Field(min_length=1, max_length=200)
    evidence_count: int | None = None
    cue_count: int | None = None


class CaseReceipt(_Strict):
    case_id: str
    output_language: Literal["en", "zh-CN"]
    scope: Literal["YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"]
    mode: Literal["LIVE_MODEL", "FIXTURE_CONTRACT"]
    producer_id: str = Field(min_length=1, max_length=200)
    execution_id: str = Field(min_length=1, max_length=1024)
    input_hash: str
    context_hash: str
    request_hash: str
    profile_hash: str
    code_hash: str
    freeze_hash: str
    harness_hash: str
    model_digest: str
    runtime: str
    permit_hash: str
    source_manifest_hash: str
    source_manifest: SourceManifest
    capacity_proof_hash: str
    runtime_proof_hash: str
    raw_hash: str
    final_hash: str
    generation_count: int
    ledger_invocation_count: int
    done: bool
    done_reason: str
    prompt_tokens: int
    output_tokens: int
    completed_at: str
    review: SemanticReview
    receipt_hash: str
    outcome: Literal["INTELLIGENCE", "NO_NEW"] | None = None

    def passes(self, generated_at: datetime, profile_id: str = PROFILE_ID) -> bool:
        projection = qualification_projection(profile_id, self.scope)
        binding = qualification_binding(projection)
        options = projection["options"]
        if not isinstance(options, dict):
            return False
        current = profile_id in {SHORT_CURRENT, LONG_CURRENT}
        review = self.review
        source = self.source_manifest
        hashes = (self.input_hash, self.context_hash, self.request_hash, self.permit_hash,
            self.source_manifest_hash, self.capacity_proof_hash, self.runtime_proof_hash,
            self.raw_hash, self.final_hash, review.input_hash, review.request_hash, review.final_hash)
        return (self.mode == "LIVE_MODEL" and all(sha(h) for h in hashes)
            and self.profile_hash == binding["profile_hash"] and self.code_hash == binding["code_hash"]
            and self.model_digest == binding["model_digest"] and self.runtime == binding["runtime"]
            and self.source_manifest_hash == digest(source.model_dump(exclude_unset=True))
            and all(sha(h) for h in (source.snapshot_hash, source.summary_hash, source.evidence_hash, source.policy_hash))
            and (source.input_hash, source.context_hash, source.request_hash) == (self.input_hash, self.context_hash, self.request_hash)
            and (not self.case_id.startswith("holdout-") or (source.unseen_for_profile
                and source.selector_id != self.producer_id and source.origin == "PUBLIC_SNAPSHOT"))
            and (not self.case_id.startswith("local-") or source.origin == "LOCAL_SNAPSHOT")
            and self.generation_count == self.ledger_invocation_count == 1 and self.done is True
            and self.done_reason == "stop" and 0 < self.prompt_tokens
            and (self.prompt_tokens + int(options["num_predict"]) + 2 <= int(options["num_ctx"])
                if current else self.prompt_tokens <= 8192 + 88 + 2)
            and 0 < self.output_tokens < int(options["num_predict"])
            and (not current or self.outcome == review.outcome == case_outcome(self.case_id))
            and review.reviewer_id != self.producer_id and review.verdict == "PASS"
            and (review.case_id, review.input_hash, review.request_hash, review.final_hash)
            == (self.case_id, self.input_hash, self.request_hash, self.final_hash)
            and timestamp(self.completed_at) <= timestamp(review.reviewed_at) <= generated_at
            and review.review_hash == digest(review.model_dump(exclude={"review_hash"}, exclude_unset=True))
            and self.receipt_hash == digest(self.model_dump(exclude={"receipt_hash"}, exclude_unset=True)))


class QualificationRecord(_Strict):
    version: Literal["local-distillation-qualification-v1"]
    binding: dict[str, str]
    generated_at: str
    expires_at: str
    freeze_hash: str
    harness_hash: str
    case_manifest_hash: str
    cases: list[CaseReceipt]
    record_hash: str

    def permits(self, projection: Mapping[str, object], language: str, now: datetime) -> bool:
        try:
            generated, expiry = timestamp(self.generated_at), timestamp(self.expires_at)
            scope = str(projection["scope"])
            expected = qualification_cases(projection)
            actual = [(c.case_id, c.output_language) for c in self.cases]
            return (now.tzinfo is not None and generated <= now < expiry
                and timedelta(0) < expiry - generated <= timedelta(days=30)
                and scope in {"YT_TIMED", "LOCAL_TIMED", "LOCAL_TEXT"}
                and self.binding == qualification_binding(projection)
                and self.binding["profile_id"] in {PROFILE_ID, SHORT_CURRENT, LONG_CURRENT} and language in {"en", "zh-CN"}
                and all(sha(h) for h in (self.freeze_hash, self.harness_hash, self.case_manifest_hash))
                and self.record_hash == digest(self.model_dump(exclude={"record_hash"}, exclude_unset=True))
                and actual == list(expected.items())
                and len({c.execution_id for c in self.cases}) == len(actual)
                and all(c.passes(generated, self.binding["profile_id"]) for c in self.cases)
                and (self.binding["profile_id"] != LONG_CURRENT or self._full_source_pair())
                and all(timestamp(a.review.reviewed_at) <= timestamp(b.completed_at)
                    for a, b in zip(self.cases, self.cases[1:]))
                and all((c.freeze_hash, c.harness_hash) == (self.freeze_hash, self.harness_hash) for c in self.cases)
                and self.case_manifest_hash == digest([{key: c.model_dump()[key] for key in (
                    "case_id", "output_language", "scope", "input_hash", "context_hash", "request_hash", "source_manifest_hash")}
                    for c in self.cases])
                and (scope != "YT_TIMED" or self._distinct_holdouts())
                and all(c.scope == ("YT_TIMED" if scope == "YT_TIMED" else
                    "LOCAL_TIMED" if c.case_id.startswith("local-timed-") else "LOCAL_TEXT") for c in self.cases))
        except (ValueError, KeyError, TypeError, OSError):
            return False

    def _full_source_pair(self) -> bool:
        left, right = self.cases[-2].source_manifest, self.cases[-1].source_manifest
        return (left.origin == right.origin == "PUBLIC_SNAPSHOT"
            and left.source_id == right.source_id == "0eMzc-WnBfQ"
            and left.evidence_count == right.evidence_count == 114
            and left.cue_count == right.cue_count == 2406
            and left.snapshot_hash == right.snapshot_hash)

    def _distinct_holdouts(self) -> bool:
        values = {c.case_id: c.source_manifest for c in self.cases}
        a, b = values["holdout-a-en"], values["holdout-b-en"]
        return (a.source_id != b.source_id and a.snapshot_hash != b.snapshot_hash
            and (a.source_id, a.snapshot_hash) == (values["holdout-a-zh"].source_id, values["holdout-a-zh"].snapshot_hash)
            and (b.source_id, b.snapshot_hash) == (values["holdout-b-zh"].source_id, values["holdout-b-zh"].snapshot_hash))


class LocalQualificationAuthority:
    def __init__(self) -> None:
        self._records: tuple[QualificationRecord, ...] = ()
        self._seal: object | None = None

    def permits(self, projection: Mapping[str, object], language: str, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        matches = [r for r in self._records if (r.binding.get("profile_id"), r.binding.get("scope"))
            == (projection.get("local_profile_id"), projection.get("scope"))]
        # Multiple registrations are ambiguous; never pick the most flattering.
        return self._seal is _PACKAGE_AUTHORITY_SEAL and len(matches) == 1 and matches[0].permits(projection, language, current)

    def scope_status(self, projection: Mapping[str, object], language: str, *, now: datetime | None = None) -> dict[str, object]:
        return {"profile_id": projection["local_profile_id"], "model": projection["model"],
            "scope": projection["scope"], "output_language": language,
            "status": "QUALIFIED" if self.permits(projection, language, now=now) else "NOT_QUALIFIED"}

    def states(self, *, now: datetime | None = None) -> tuple[dict[str, object], ...]:
        # A state projection is descriptive only; eligibility still requires
        # permits() against the complete current production profile binding.
        current = now or datetime.now(UTC)
        result: list[dict[str, object]] = []
        for record in self._records:
            try:
                expired = timestamp(record.expires_at) <= current
            except ValueError:
                expired = True
            result.append({"profile_id": record.binding.get("profile_id"), "scope": record.binding.get("scope"),
                "output_languages": ("en", "zh-CN"), "status": "REQUIRES_CURRENT_BINDING", "expired": expired})
        return tuple(result)


def read_reviewed_qualifications(raw: bytes | None = None) -> LocalQualificationAuthority:
    try:
        package_source = raw is None
        if raw is None:
            path = resources.files("youtube_intel").joinpath("resources/local_distillation_qualification_v1.json")
            with path.open("rb") as stream:
                raw = stream.read(262145)
        if len(raw) > 262144:
            return LocalQualificationAuthority()
        value = json.loads(raw, object_pairs_hook=strict_object)
        if (not isinstance(value, dict) or set(value) != {"version", "records"} or value["version"] != VERSION
            or not isinstance(value["records"], list) or len(value["records"]) > 4):
            return LocalQualificationAuthority()
        authority = LocalQualificationAuthority()
        authority._records = tuple(QualificationRecord.model_validate(r) for r in value["records"])
        pairs = [(r.binding["profile_id"], r.binding["scope"]) for r in authority._records]
        if len(set(pairs)) != len(pairs):
            return LocalQualificationAuthority()
        for profile_id, scope in pairs:
            qualification_projection(profile_id, scope)
        # Test/caller-supplied bytes can exercise validation, never mint live
        # production authority. Only the reviewed fixed package resource can.
        if package_source:
            authority._seal = _PACKAGE_AUTHORITY_SEAL
        return authority
    except (ValueError, KeyError, TypeError, OSError, RecursionError):
        return LocalQualificationAuthority()


class LocalExecutionPermit(_Strict):
    """A root-reviewed, frozen, single-case permit; no ordinary factory creates it."""
    version: Literal["local-grounding-once-permit-v1"]
    case_id: str
    execution_id: str
    input_hash: str
    context_hash: str
    request_hash: str
    binding: dict[str, str]
    source_manifest_hash: str
    capacity_proof_hash: str
    runtime_proof_hash: str
    harness_hash: str
    freeze_hash: str
    issued_at: str
    expires_at: str
    prior_review_hashes: list[str]
    permit_hash: str

    def matches(self, projection: Mapping[str, object], input_hash: str, request_hash: str, language: str) -> bool:
        try:
            scope = str(projection["scope"])
            expected = qualification_cases(projection)
            order = list(expected)
            issued, expires = timestamp(self.issued_at), timestamp(self.expires_at)
            return (case_scope(self.case_id, profile_id=str(projection["local_profile_id"])) == scope and self.binding == qualification_binding(projection) and input_hash == self.input_hash
                and request_hash == self.request_hash and expected.get(self.case_id) == language
                and self.permit_hash == digest(self.model_dump(exclude={"permit_hash"}))
                and issued <= datetime.now(UTC) < expires and timedelta(0) < expires - issued <= timedelta(hours=1)
                and len(self.prior_review_hashes) == order.index(self.case_id)
                and all(sha(h) for h in [self.input_hash, self.context_hash, self.request_hash, self.source_manifest_hash,
                    self.capacity_proof_hash, self.runtime_proof_hash, self.harness_hash, self.freeze_hash, *self.prior_review_hashes]))
        except (ValueError, KeyError, TypeError, OSError):
            return False
