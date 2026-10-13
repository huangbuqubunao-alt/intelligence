"""Isolated, frozen source inputs and REAL digest-pinned local model outputs.

Controlled source fixtures are labelled in the corpus. They are not real news or
model outputs. Never enables production eligibility or touches an owner database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.config import LocalScoringSettings
from youtube_intel.distillation import (
    OllamaLocalDistillationTransport,
    PersonalizedDistillationService,
    VerifiedDistillationInput,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.runtime_composition import ProductionDistillationBudget
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    LiveStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
    build_evidence_id,
)

PROJECT = Path(__file__).resolve().parents[1]
CORPUS = PROJECT / "docs/validation/end-to-end-user-readiness/INTELLIGENCE_FROZEN_CORPUS.json"

# Unrelated, synthetic calibration input. It is neither a corpus case nor a
# candidate answer. Its references cannot pass the real-source binding checks.
CALIBRATION_EVIDENCE_ID = "e" * 64
CALIBRATION_CONTEXT = {
    "evidence": [{"evidence_id": CALIBRATION_EVIDENCE_ID,
                  "start_ms": 13000, "end_ms": 24000,
                  "excerpt": "The build maintainer says the preview seems to reduce failed exports. "
                             "They estimate about ten fewer retries in informal use. "
                             "There has not been a controlled comparison."}],
    "focus": ["Desktop software reliability and evaluation"],
    "ignore": [], "personalization": [], "style": "BALANCED",
    "source_display_name": "Desktop build preview discussion",
    "video_title": "Preview reliability observations",
}
CALIBRATION_OUTPUT = {
    "result": "INTELLIGENCE",
    "core_conclusion": "The maintainer in Desktop build preview discussion reports an apparent "
                       "export reliability improvement; the informal observation remains unverified.",
    "user_relevant_information": ["For reliability evaluation, this preliminary source claim "
                                  "suggests a controlled comparison is worth doing."],
    "important_new_information": ["The maintainer says the preview seems to reduce failed exports."],
    "meaningful_details": ["About ten fewer retries is the maintainer's estimate, not a measured result.",
                           "The source explicitly says no controlled comparison has been performed."],
    "filtered_noise": [], "claim_kind": "SYSTEM_INFERENCE",
    "evidence": [{"evidence_id": CALIBRATION_EVIDENCE_ID,
                  "start_ms": 13000, "end_ms": 24000, "stance": "supporting"}],
}


def grounded_wire_schema() -> dict:
    positive = OllamaLocalDistillationTransport._INTELLIGENCE_SCHEMA
    reference = OllamaLocalDistillationTransport._EVIDENCE_REFERENCE_SCHEMA
    grounding = {
        **reference,
        "required": [*reference["required"], "quote"],
        "properties": {**reference["properties"],
                       "quote": {"type": "string", "minLength": 20, "maxLength": 2000}},
    }
    return {"anyOf": [{**positive,
        "required": ["result", "source_grounding", *positive["required"][1:]],
        "properties": {"result": positive["properties"]["result"],
            "source_grounding": {"type": "array", "minItems": 1, "maxItems": 20,
                                 "items": grounding},
            **{k: v for k, v in positive["properties"].items() if k != "result"}},
    }, OllamaLocalDistillationTransport._NO_NEW_INTELLIGENCE_SCHEMA]}


def decode_grounded_wire(raw: str, verified: VerifiedDistillationInput) -> str:
    payload = json.loads(raw)
    if isinstance(payload, dict) and set(payload) == {"result", "evidence"}:
        return raw  # unchanged NO_NEW branch goes through the ordinary parser
    expected = set(OllamaLocalDistillationTransport._INTELLIGENCE_SCHEMA["required"])
    if not isinstance(payload, dict) or set(payload) != expected | {"source_grounding"}:
        raise ValueError("grounded local wire shape invalid")
    grounding = payload["source_grounding"]
    if not isinstance(grounding, list) or not 1 <= len(grounding) <= 20:
        raise ValueError("grounded source references missing")
    verified_items = {e.evidence_id: e for e in verified.evidence}
    grounded_ids = set()
    for item in grounding:
        if not isinstance(item, dict) or set(item) != {"evidence_id", "start_ms", "end_ms", "quote"}:
            raise ValueError("grounded source reference shape invalid")
        eid, quote = item["evidence_id"], item["quote"]
        if not isinstance(eid, str) or eid not in verified_items or eid in grounded_ids:
            raise ValueError("grounded source reference unknown or duplicate")
        original = verified_items[eid]
        if (type(item["start_ms"]) is not int or type(item["end_ms"]) is not int
            or (item["start_ms"], item["end_ms"]) != (original.start_ms, original.end_ms)
            or not isinstance(quote, str) or not 20 <= len(quote) <= 2000
            or quote not in original.excerpt):
            raise ValueError("grounded source quote binding invalid")
        grounded_ids.add(eid)
    supports = payload["evidence"]
    if (not isinstance(supports, list)
        or any(not isinstance(e, dict) or not isinstance(e.get("evidence_id"), str) for e in supports)
        or sorted(e.get("evidence_id", "") for e in supports) != sorted(grounded_ids)):
        raise ValueError("every cited item must have exact source grounding")
    # Representation decoding only. No prose, claim-kind, stance or references
    # are corrected. Raw output remains the ledger/audit input.
    return json.dumps({k: v for k, v in payload.items() if k != "source_grounding"})


class GroundedResearchService(PersonalizedDistillationService):
    def _parse_candidate(self, raw, command, verified_input):
        return super()._parse_candidate(decode_grounded_wire(raw, verified_input), command, verified_input)


def setup(case: dict, root: Path, now: datetime) -> tuple[SQLiteStateRepository, str, str]:
    data = root / "data"
    data.mkdir(parents=True)
    database = root / "state.sqlite3"
    if "public_source_url" in case:
        prior = PROJECT / ".var/end-to-end-user-readiness/runtime"
        with sqlite3.connect(f"{(prior / 'state.sqlite3').as_uri()}?mode=ro", uri=True) as src:
            with sqlite3.connect(database) as dest:
                src.backup(dest)
        shutil.copytree(prior / "data", data, dirs_exist_ok=True)
        repo = SQLiteStateRepository(database)
        repo.bind_source_storage(data)
        video = case.get("public_video_id", "aircAruvnKk")
        sources = repo.list_source_subscriptions()
        source = next(s.source_id for s in sources if s.video_id == video)
        timed = repo.get_verified_timed_transcript(video_id=video)
        if timed is None:
            raise ValueError("real source has no verified timed transcript")
        actual_cues = [dict(start_ms=c.start_ms, end_ms=c.end_ms, text=c.text) for c in timed.cues]
        if actual_cues != case["timed_segments"]:
            raise ValueError("frozen real source changed")
        artifact = repo.latest_artifact(video, ArtifactKind.TRANSCRIPT_CANONICAL)
        if case.get("canonical_sha256") and (
            artifact is None or artifact.content_hash != case["canonical_sha256"]
        ):
            raise ValueError("frozen canonical artifact changed")
        return repo, source, video
    repo = SQLiteStateRepository(database)
    repo.initialize(now=now)
    repo.bind_source_storage(data)
    source = ProductOrchestrationService(repo, now=lambda: now).add_source(
        url="https://www.youtube.com/channel/UC______________________",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    video = "controlled-" + case["id"]
    repo.upsert_video_metadata(VideoMetadata(
        video_id=video, channel_id="UC______________________",
        channel_name="Controlled synthetic source for engineering qualification",
        title=case["title"], description="Controlled AI engineering source, not real news.",
        source_url="https://www.youtube.com/watch?v=" + video, published_at=now,
        duration_seconds=5 * len(case["texts"]), default_language="en",
        available_languages=("en",), live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    ), pipeline_version="controlled-source-readiness-v1", now=now)
    repo.link_source_video(source.source_id, video, discovered_at=now)
    policy = SourcePolicyApplicationService(repo, now=lambda: now)
    policy.update_global(command_id="qualification-policy", initial_history_count=5,
        per_run_max_new_videos=5, focus_rules=("AI",), ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED)
    policy.evaluate_and_record_stage_one(source.source_id, MetadataFilterCandidate(
        video_id=video, title=case["title"], description="Controlled AI engineering source.",
        channel_name="Controlled source", published_at=now, video_type=VideoType.STANDARD))
    relative = "transcripts/canonical.txt"
    payload = "\n".join(case["texts"]).encode()
    (data / "transcripts").mkdir()
    (data / relative).write_bytes(payload)
    artifact = "controlled-canonical-" + case["id"]
    repo.upsert_artifact(ArtifactWrite(artifact_id=artifact, artifact_key=artifact,
        video_id=video, job_id=None, kind=ArtifactKind.TRANSCRIPT_CANONICAL,
        storage_root=StorageRoot.DATA, relative_path=relative,
        content_hash=hashlib.sha256(payload).hexdigest(), provider=None, model=None,
        producer_version="controlled-source-readiness-v1",
        retention_class=RetentionClass.LONG_LIVED, expires_at=None), now=now)
    cues = tuple(TimedTranscriptCueWrite(start_ms=i * 5000, end_ms=(i+1)*5000, text=text)
        for i, text in enumerate(case["texts"]))
    timed = TimedTranscriptWrite.from_cues(video_id=video, canonical_artifact_id=artifact, cues=cues)
    repo.create_timed_transcript(timed, now=now)
    for i, cue in enumerate(cues):
        eid = build_evidence_id(video_id=video, artifact_id=artifact,
            start_ms=cue.start_ms, end_ms=cue.end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL)
        evidence = EvidenceWrite(evidence_id=eid, video_id=video, artifact_id=artifact,
            start_ms=cue.start_ms, end_ms=cue.end_ms, lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL, language="en", availability=EvidenceAvailability.AVAILABLE)
        repo.create_evidence_with_text_binding(evidence, EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence, timed_transcript_id=timed.timed_transcript_id,
            start_cue_index=i, end_cue_index=i+1, excerpt=cue.text), now=now)
    return repo, source.source_id, video


class CapturingTransport(OllamaLocalDistillationTransport):
    def __init__(self, *, settings: LocalScoringSettings, root: Path, reasoning_profile: str = "current") -> None:
        super().__init__(settings=settings)  # production_qualified stays False
        self.root = root
        self.generations = 0
        self.reasoning_profile = reasoning_profile

    def _request(self, path, *, method, body=None):
        if path == "/api/chat":
            if self.reasoning_profile in ("native-thinking", "source-calibration"):
                body = {**body, "think": True}
            if self.reasoning_profile in ("source-calibration", "source-calibration-fast", "native-sampling"):
                system, source = body["messages"]
                body = {**body, "messages": [system,
                    {"role": "user", "content": json.dumps(CALIBRATION_CONTEXT)},
                    {"role": "assistant", "content": json.dumps(CALIBRATION_OUTPUT)},
                    source]}
            if self.reasoning_profile == "native-sampling":
                body = {**body, "options": {**body["options"],
                    "temperature": 0.7, "top_p": 0.8, "top_k": 20,
                    "min_p": 0.0, "seed": 20261013}}
            if self.reasoning_profile == "source-grounding":
                system, source = body["messages"]
                instructions = (
                    " Before composing an admitted judgment, list source_grounding with one exact "
                    "source quote for each cited Evidence item. Quotes are source records, not reasoning, "
                    "and must preserve the source's actual uncertainty. Then write one useful retained "
                    "judgment and its distinct implications and limitations; do not merely summarize. "
                    "Every reporting sentence must remain attributed and qualified. Choose claim_kind "
                    "for the principal retained judgment: PREDICTION means a future outcome, not an "
                    "uncertain report about a past event; a retrospective source report is "
                    "EVIDENCE_BACKED_STATEMENT, and your own clearly labelled interpretation is "
                    "SYSTEM_INFERENCE. Exact quotes do not establish independent verification. "
                    "NO_NEW_INTELLIGENCE remains unchanged when nothing qualifies."
                )
                body = {**body, "format": grounded_wire_schema(), "messages": [
                    {**system, "content": system["content"] + instructions}, source]}
            self.generations += 1
            if self.generations != 1:
                raise RuntimeError("qualification case may dispatch only once")
            (self.root / "request.json").write_text(json.dumps(body, ensure_ascii=False, indent=2))
        response = super()._request(path, method=method, body=body)
        if path == "/api/chat":
            (self.root / "response.json").write_text(json.dumps(response, ensure_ascii=False, indent=2))
        return response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--reasoning-profile", choices=("current", "native-thinking", "source-calibration", "source-calibration-fast", "source-grounding", "native-sampling"), default="current")
    parser.add_argument("--corpus", default=CORPUS.name,
        choices=(CORPUS.name, "INTELLIGENCE_REAL_CORPUS_V2.json"))
    args = parser.parse_args()
    if re.fullmatch(r"[a-z0-9-]{1,64}", args.attempt) is None:
        raise ValueError("invalid attempt identity")
    corpus_path = CORPUS.with_name(args.corpus)
    raw = corpus_path.read_bytes()
    expected = corpus_path.with_suffix(".sha256").read_text().strip()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("frozen corpus changed")
    corpus = json.loads(raw)
    case = next(c for c in corpus["cases"] if c["id"] == args.case)
    root = PROJECT / ".var/end-to-end-user-readiness/intelligence" / args.attempt / args.case
    root.mkdir(parents=True, exist_ok=False)  # prior evidence cannot be overwritten
    now = datetime.now(UTC)
    repo, source, video = setup(case, root, now)
    policy = SourcePolicyApplicationService(repo, now=lambda: now)
    if case.get("focus_rules"):
        policy.update_global(command_id="frozen-case-focus", initial_history_count=5,
            per_run_max_new_videos=5, focus_rules=tuple(case["focus_rules"]),
            ignore_rules=(), distillation_style=DistillationStyle.BALANCED)
    transport = CapturingTransport(settings=LocalScoringSettings(
        model=corpus["model"], expected_model_digest=corpus["digest"]), root=root,
        reasoning_profile=args.reasoning_profile)
    service_type = GroundedResearchService if args.reasoning_profile == "source-grounding" else PersonalizedDistillationService
    service = service_type(repo, policy, transport, ProductionDistillationBudget(),
        now=lambda: datetime.now(UTC), output_language_for_video=lambda _: case["output_language"])
    evidence_ids = repo.list_canonical_coverage_evidence_ids(video_id=video)
    reservation = service.reserve_distillation_execution(source_id=source, video_id=video,
        evidence_ids=evidence_ids, manual_command_id="qualification-" + args.attempt
        if "public_source_url" in case else None)
    result = {"corpus_sha256": expected, "case": case["id"], "evidence_count": len(evidence_ids),
        "execution_id": reservation.execution_id, "production_qualified": False,
        "reasoning_profile": args.reasoning_profile}
    if not args.prepare_only:
        outcome = service.continue_qualification_reserved_distillation(reservation.execution_id)
        repeat = service.continue_qualification_reserved_distillation(reservation.execution_id)
        assert repeat == outcome and transport.generations <= 1
        result.update({"outcome": asdict(outcome), "generations": transport.generations})
    (root / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(json.dumps(result, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
