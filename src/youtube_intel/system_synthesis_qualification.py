"""Finite reviewed v2 package evidence; neither user DATA nor spending consent.

Only the fixed package loader seals authority. Raw fixtures can validate a record
but cannot qualify a runtime. Resource bytes are excluded from the code binding
so Root can register genuinely reviewed evidence after freezing the final code.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import system_synthesis as synthesis
from . import system_synthesis_profile as profile
from .local_distillation_qualification import sha, strict_object, timestamp

VERSION = "system-synthesis-reviewed-qualification-v1"
SCOPE = "PUBLIC_YOUTUBE_TIMED"
CASE_LANGUAGES = {
    "public-aircAruvnKk-en": "en", "public-aircAruvnKk-zh-CN": "zh-CN",
    "public-IwglW_hIL_g-en": "en", "public-IwglW_hIL_g-zh-CN": "zh-CN",
    "no-new-en": "en", "no-new-zh-CN": "zh-CN",
    "injection-en": "en", "injection-zh-CN": "zh-CN",
}
CODE_FILES = (
    "system_synthesis.py", "system_synthesis_profile.py", "system_synthesis_persistence.py",
    "system_synthesis_qualification.py", "summary_baseline.py", "synthesis_runtime.py",
    "distillation.py", "runtime_composition.py", "cloud_spending_policy.py", "local_api.py",
    "intelligence_read.py", "state.py", "source_policy.py", "source_authority.py",
    "bound_evidence_reference.py", "domain.py", "extractive_summary.py",
    "migrations/044_add_system_synthesis_provenance.sql",
)
_PACKAGE_SEAL = object()


def digest(value: object) -> str:
    return profile.sha(profile.canonical(value))


def qualification_binding() -> dict[str, str]:
    package = resources.files("youtube_intel")
    descriptor = profile.resolve_profile(profile.ATTRIBUTION_PROFILE_ID)
    return {"profile_id": profile.ATTRIBUTION_PROFILE_ID, "scope": SCOPE,
        "provider": profile.PAIR[0], "model": profile.PAIR[1],
        "profile_sha256": digest(descriptor), "policy_id": synthesis.ATTRIBUTION_PROFILE_ID,
        "policy_sha256": digest(synthesis.profile_projection(synthesis.ATTRIBUTION_PROFILE_ID)),
        "code_sha256": digest({name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
            for name in CODE_FILES})}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SemanticReview(_Strict):
    reviewer_id: str = Field(min_length=1, max_length=200)
    case_id: str
    input_sha256: str
    wire_sha256: str
    receipt_sha256: str
    final_sha256: str
    oracle_sha256: str
    outcome: Literal["INTELLIGENCE", "NO_NEW_INTELLIGENCE"]
    verdict: Literal["PASS", "FAIL"]
    reviewed_at: str
    review_sha256: str


class CaseReceipt(_Strict):
    case_id: str
    output_language: Literal["en", "zh-CN"]
    scope: Literal["PUBLIC_YOUTUBE_TIMED"]
    mode: Literal["LIVE_MODEL", "FIXTURE_CONTRACT"]
    source_origin: Literal["PUBLIC_SNAPSHOT", "SYNTHETIC_CONTROL"]
    source_id: str = Field(min_length=1, max_length=512)
    producer_id: str = Field(min_length=1, max_length=200)
    execution_id: str = Field(min_length=1, max_length=1024)
    profile_sha256: str
    code_sha256: str
    freeze_sha256: str
    oracle_sha256: str
    input_sha256: str
    wire_sha256: str
    snapshot_sha256: str
    summary_sha256: str
    evidence_sha256: str
    raw_sha256: str
    final_sha256: str
    receipt_sha256: str
    generation_count: int
    ledger_invocation_count: int
    done_reason: str
    prompt_tokens: int
    output_tokens: int
    outcome: Literal["INTELLIGENCE", "NO_NEW_INTELLIGENCE"]
    completed_at: str
    review: SemanticReview

    def passes(self, binding: dict[str, str], generated: datetime) -> bool:
        review = self.review
        return (self.mode == "LIVE_MODEL" and self.generation_count == self.ledger_invocation_count == 1
            and self.done_reason == "stop" and self.prompt_tokens > 0 and 0 < self.output_tokens < 5888
            and self.profile_sha256 == binding["profile_sha256"] and self.code_sha256 == binding["code_sha256"]
            and all(sha(getattr(self, key)) for key in type(self).model_fields if key.endswith("_sha256"))
            and review.reviewer_id != self.producer_id and review.verdict == "PASS"
            and (review.case_id, review.input_sha256, review.wire_sha256, review.receipt_sha256,
                review.final_sha256, review.oracle_sha256, review.outcome)
            == (self.case_id, self.input_sha256, self.wire_sha256, self.receipt_sha256,
                self.final_sha256, self.oracle_sha256, self.outcome)
            and review.review_sha256 == digest(review.model_dump(exclude={"review_sha256"}))
            and timestamp(self.completed_at) <= timestamp(review.reviewed_at) <= generated)


class QualificationRecord(_Strict):
    version: Literal["system-synthesis-reviewed-qualification-v1"]
    binding: dict[str, str]
    generated_at: str
    freeze_sha256: str
    oracle_sha256: str
    matrix_sha256: str
    cases: list[CaseReceipt]
    record_sha256: str

    def permits(self, profile_id: str, scope: str, language: str, now: datetime) -> bool:
        try:
            generated = timestamp(self.generated_at)
            return (profile_id == profile.ATTRIBUTION_PROFILE_ID and scope == SCOPE and language in {"en", "zh-CN"}
                and now.tzinfo is not None and generated <= now
                and self.binding == qualification_binding()
                and all(sha(h) for h in (self.freeze_sha256, self.oracle_sha256, self.matrix_sha256))
                and self.record_sha256 == digest(self.model_dump(exclude={"record_sha256"}))
                and [(c.case_id, c.output_language) for c in self.cases] == list(CASE_LANGUAGES.items())
                and len({c.execution_id for c in self.cases}) == 8
                and all(c.passes(self.binding, generated) for c in self.cases)
                and all((c.freeze_sha256, c.oracle_sha256) == (self.freeze_sha256, self.oracle_sha256) for c in self.cases)
                and all(timestamp(a.review.reviewed_at) <= timestamp(b.completed_at)
                    for a, b in zip(self.cases, self.cases[1:]))
                and self.matrix_sha256 == digest([{key: c.model_dump()[key] for key in (
                    "case_id", "output_language", "scope", "source_origin", "source_id", "snapshot_sha256",
                    "summary_sha256", "evidence_sha256", "input_sha256", "wire_sha256")} for c in self.cases])
                and self._source_and_outcome_coverage())
        except (ValueError, KeyError, TypeError, OSError, RecursionError):
            return False

    def _source_and_outcome_coverage(self) -> bool:
        for left, right, identity in ((self.cases[0], self.cases[1], "aircAruvnKk"),
            (self.cases[2], self.cases[3], "IwglW_hIL_g")):
            if (left.source_origin != "PUBLIC_SNAPSHOT" or right.source_origin != "PUBLIC_SNAPSHOT"
                or left.source_id != identity or right.source_id != identity
                or (left.snapshot_sha256, left.summary_sha256, left.evidence_sha256)
                != (right.snapshot_sha256, right.summary_sha256, right.evidence_sha256)):
                return False
        return (all(c.source_origin == "SYNTHETIC_CONTROL" and c.outcome == "NO_NEW_INTELLIGENCE"
                    for c in self.cases[4:])
            and all(any(c.outcome == "INTELLIGENCE" and c.output_language == language for c in self.cases[:4])
                    for language in ("en", "zh-CN")))


@dataclass(frozen=True, slots=True, init=False)
class SynthesisQualificationAuthority:
    """Only a package-sealed complete record may support a normal v2 permit."""

    _record: QualificationRecord | None = None
    _seal: object | None = None

    def __init__(self) -> None:
        object.__setattr__(self, "_record", None)
        object.__setattr__(self, "_seal", None)

    def permits(self, profile_id: str, language: str, *, scope: str = SCOPE, now: datetime | None = None) -> bool:
        return (self._seal is _PACKAGE_SEAL and self._record is not None
            and self._record.permits(profile_id, scope, language, now or datetime.now(UTC)))


def read_reviewed_qualifications(raw: bytes | None = None) -> SynthesisQualificationAuthority:
    try:
        package_source = raw is None
        if raw is None:
            path = resources.files("youtube_intel").joinpath("resources/system_synthesis_qualification_v1.json")
            with path.open("rb") as stream:
                raw = stream.read(262145)
        if type(raw) is not bytes or len(raw) > 262144:
            return SynthesisQualificationAuthority()
        value = json.loads(raw, object_pairs_hook=strict_object)
        if (not isinstance(value, dict) or set(value) != {"version", "records"}
            or value["version"] != VERSION or not isinstance(value["records"], list) or len(value["records"]) != 1):
            return SynthesisQualificationAuthority()
        record = QualificationRecord.model_validate(value["records"][0])
        authority = SynthesisQualificationAuthority()
        object.__setattr__(authority, "_record", record)
        if package_source:
            object.__setattr__(authority, "_seal", _PACKAGE_SEAL)
        return authority
    except (ValueError, KeyError, TypeError, OSError, RecursionError):
        return SynthesisQualificationAuthority()
