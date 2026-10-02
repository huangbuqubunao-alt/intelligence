"""Deterministic five-role Obsidian projection of verified durable authority."""

import hashlib
import json

from youtube_intel.deep_analysis_contracts import dacs1_sha256
from youtube_intel.deep_analysis_persistence import (
    VerifiedPersistedDeepAnalysisRead,
    require_trusted_note_eligibility,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.note_v2 import _timing, build_note_v2
from youtube_intel.notes import (
    NoteRenderingError,
    RenderedVideoNote,
    _safe_inline,
    _template,
    build_video_note_filename,
)
from youtube_intel.state import format_utc_datetime

_ROLES = (
    ("CORE_CONCLUSION", "Core conclusion", "核心结论"),
    ("KEY_EVIDENCE", "Key evidence", "关键证据"),
    ("UNCERTAINTY", "Uncertainty", "不确定性"),
    ("RELEVANCE_TO_USER", "Relevance to you", "对我的意义"),
    ("NEXT_QUESTION", "Next question", "下一步追问"),
)


def deep_analysis_note_identity(
    *, content_identity: str, output_language: str, knowledge_content_schema_identity: str
) -> str:
    # Content identity is canonical video_identity, not the generated
    # KnowledgeContent payload digest exposed by the historical read adapter.
    return dacs1_sha256({
        "schema_version": "deep-analysis-obsidian-semantic-key-v1",
        "content_identity": content_identity,
        "output_language": output_language,
        "knowledge_content_schema_identity": knowledge_content_schema_identity,
    })


def render_deep_analysis_note(source: VerifiedPersistedDeepAnalysisRead, *, title: str) -> RenderedVideoNote:
    if not verify_persisted_deep_analysis_read(source):
        raise NoteRenderingError("Deep Analysis requires a verified persisted read")
    require_trusted_note_eligibility(source)
    if source.durable_result is None:
        raise NoteRenderingError("Deep Analysis requires native durable authority")
    # Reuse the trusted Note gate and its exact verified-original Evidence
    # resolver. No prompt candidate registry is ever rendered.
    note = build_note_v2(source)
    language = source.durable_result.output_language
    schema = source.request_projection.knowledge_content_schema_identity
    identity = deep_analysis_note_identity(
        content_identity=source.canonical_input.video_identity,
        output_language=language,
        knowledge_content_schema_identity=schema,
    )
    frontmatter = {
        "type": "deep-analysis",
        "producer": "youtube-intel",
        "schema_version": "deep-analysis-obsidian-v1",
        "note_identity": identity,
        "content_identity": source.canonical_input.video_identity,
        "video_id": source.canonical_input.video_identity,
        "output_language": language,
        "knowledge_content_schema_identity": schema,
        "result_identity": source.result_identity,
        "knowledge_content_identity": source.content_identity,
        "generated_at": format_utc_datetime(source.created_at),
        "validated_at": format_utc_datetime(source.validated_at),
        "evidence_schema_version": source.durable_result.schema_version,
        "validation_policy_identity": source.validation_policy.identity,
    }
    evidence_label = "证据" if language == "zh-CN" else "Evidence"
    sections = tuple({
        "title": chinese if language == "zh-CN" else english,
        "claims": tuple({
            "text": _safe_inline(claim.text),
            "citations": evidence_label + ": " + ", ".join(claim.evidence_refs),
            "uncertain": claim.language_validation == "UNCERTAIN",
        } for claim in source.durable_result.claims if claim.role == role),
    } for role, english, chinese in _ROLES)
    content = _template(("templates", "deep-analysis.md")).render(
        frontmatter="\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()),
        title=_safe_inline(title),
        sections=sections,
        evidence_title="原始证据" if language == "zh-CN" else "Original evidence",
        evidence=tuple({
            "id": reference.evidence_id,
            "excerpt": _safe_inline(reference.excerpt),
            "timing": _timing(reference).strip(),
        } for reference in note.evidence_references),
        language_notice="输出语言尚未完全核验。" if language == "zh-CN" else "Output language could not be fully verified.",
        user_title="我的思考" if language == "zh-CN" else "My thoughts",
    ).rstrip() + "\n"
    if len(content.encode()) > 1 << 20:
        raise NoteRenderingError("rendered managed note exceeds the resource limit")
    safe_title = build_video_note_filename(title, "deep-analysis").removesuffix("--deep-analysis.md")
    return RenderedVideoNote(
        relative_path=f"Deep Analysis/{safe_title}--{identity}.md",
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
