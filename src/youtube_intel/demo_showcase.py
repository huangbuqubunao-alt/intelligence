"""Isolated, zero-config public showcase runtime for evaluation & demos.

Seeds deterministic YouTube, Bilibili, and local Markdown content with verified
transcripts, Chinese/English Workspace AI insights, Weekly Brief, Topic
Evolution, and offline Cross-Video Grounded Q&A inside ``.var/demo-showcase``
without reading real user data, credentials, or external networks.
"""

from __future__ import annotations

import json
import re
import shutil
import signal
import threading
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import FrameType
from typing import Any, Final, cast

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.operations import ExitCode
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.providers.bilibili import (
    BilibiliAdapter,
    BilibiliIdentity,
    BilibiliMetadata,
    CaptionAcquisition,
    parse_captions,
)
from youtube_intel.runtime_composition import (
    LocalSourceRunRuntime,
    build_local_source_run_runtime,
)
from youtube_intel.source_authority import sha256, write_managed
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

_DEMO_MARKER: Final[str] = ".demo-showcase-v1.json"
_DEMO_OWNER: Final[str] = "youtube-intel-demo-showcase"
_DEMO_OWNED_ENTRIES: Final[frozenset[str]] = frozenset(
    {
        _DEMO_MARKER,
        "state.sqlite3",
        "state.sqlite3-wal",
        "state.sqlite3-shm",
        ".workspace-ai",
        "config",
        "data",
        "logs",
        "templates",
        "vault",
    }
)
_DEMO_BASE_NOW: Final[datetime] = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
_TOPIC_AGENT: Final[str] = "AI Agent 工程架构"
_TOPIC_SOLO: Final[str] = "一人公司与 AI 产品化"


def default_demo_root(project_root: Path) -> Path:
    """Return the isolated runtime directory for the public showcase demo."""

    return project_root.resolve() / ".var" / "demo-showcase"


def _has_valid_demo_marker(demo_dir: Path) -> bool:
    """Return True only when ``demo_dir`` holds a valid showcase ownership marker."""

    marker = demo_dir / _DEMO_MARKER
    if not marker.exists() or marker.is_symlink() or not marker.is_file():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    return data.get("demo_owner") == _DEMO_OWNER or (
        data.get("version") == 1 and isinstance(data.get("seeded_items"), list)
    )


def _clean_demo_owned_entries(demo_dir: Path) -> None:
    """Remove only known showcase-owned paths inside ``demo_dir``."""

    for entry_name in _DEMO_OWNED_ENTRIES:
        target = demo_dir / entry_name
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)


class _DemoSecretStore:
    """In-memory credential stub ensuring demo runs never touch Keychain or env."""

    def get(self) -> str | None:
        return None

    def load(self) -> str | None:
        return None

    def save(self, value: str) -> None:
        del value

    def delete(self) -> None:
        return None


class _DemoBilibiliAdapter(BilibiliAdapter):
    """Offline Bilibili adapter returning fixed public educational metadata & cues."""

    def __init__(self, *, now: datetime) -> None:
        super().__init__(fetch=lambda *_args: b"{}")
        self._now = now

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        return BilibiliMetadata(
            identity=identity,
            cid=91002341,
            title="本地优先知识库与反幻觉证据链实战架构（B站技术公开课）",
            uploader_id="88012345",
            uploader_name="极客架构演示室（Demo）",
            published_at=self._now - timedelta(hours=18),
            duration=1320.0,
            acquired_at=self._now,
        )

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        raw_payload = json.dumps(
            {
                "body": [
                    {
                        "from": 0.0,
                        "to": 16.0,
                        "content": "很多 AI 总结工具最大的问题不是模型不够聪明，而是没有可回溯的原始证据时间轴。",
                    },
                    {
                        "from": 16.0,
                        "to": 34.0,
                        "content": "在本地 SQLite 中先把字幕原文和内容哈希锁死，再让大模型提炼观点并绑定引用编号，才能做到零幻觉审计。",
                    },
                    {
                        "from": 34.0,
                        "to": 52.0,
                        "content": "同时支持 B 站技术长视频与 YouTube 频道混合沉淀，可以直接导出成 Obsidian 双链笔记长期复用。",
                    },
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        transcript = parse_captions(
            raw_payload,
            language="zh-Hans",
            duration=metadata.duration,
        )
        return CaptionAcquisition(
            status="READY",
            transcript=transcript,
            subtitle_id="1001",
            language_name="中文（精选字幕）",
            source_url="https://aisubtitle.hdslb.com/bfs/subtitle/demo_arch_3.json",
        )


@dataclass(frozen=True, slots=True)
class _DemoVideoSpec:
    video_id: str
    title: str
    channel_id: str
    channel_name: str
    duration_seconds: int
    published_offset_hours: int
    cues: tuple[TimedTranscriptCueWrite, ...]


_YOUTUBE_DEMO_VIDEOS: Final[tuple[_DemoVideoSpec, ...]] = (
    _DemoVideoSpec(
        video_id="vidDemoAgt1",
        title="Deterministic State Machines for Production AI Agents",
        channel_id="UC_DEMO_OAI_111111111111",
        channel_name="Atlas Agent Lab (Demo)",
        duration_seconds=2040,
        published_offset_hours=6,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=18000,
                text="Production agents fail when side effects run inside unstructured chat loops instead of explicit state machines.",
            ),
            TimedTranscriptCueWrite(
                start_ms=18000,
                end_ms=42000,
                text="Every external tool call needs bounded schemas, fail-closed validation, and durable checkpoints on SQLite.",
            ),
            TimedTranscriptCueWrite(
                start_ms=42000,
                end_ms=70000,
                text="Separating deterministic ingestion from optional model inference guarantees reproducible recovery after crashes.",
            ),
        ),
    ),
    _DemoVideoSpec(
        video_id="vidDemoSol2",
        title="Building High-Margin Local-First AI Tools Solo Builders Love",
        channel_id="UC_DEMO_LAB_222222222222",
        channel_name="Local-First Foundry (Demo)",
        duration_seconds=1680,
        published_offset_hours=12,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=18000,
                text="Zero-marginal-cost onboarding starts by supporting free local Ollama models alongside user-controlled BYOK keys.",
            ),
            TimedTranscriptCueWrite(
                start_ms=18000,
                end_ms=39000,
                text="Solo builders win retention when insights export directly to Markdown knowledge graphs like Obsidian wikilinks.",
            ),
            TimedTranscriptCueWrite(
                start_ms=39000,
                end_ms=62000,
                text="Honest failure reporting beats fabricated summaries whenever a video lacks captions or a speech model is absent.",
            ),
        ),
    ),
    _DemoVideoSpec(
        video_id="vidDemoEvl4",
        title="Closing the Eval Loop: Citations Over Blind Summarization",
        channel_id="UC_DEMO_OAI_111111111111",
        channel_name="Atlas Agent Lab (Demo)",
        duration_seconds=1560,
        published_offset_hours=24,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=19000,
                text="Cross-video research Q&A must verify every citation anchor against real transcript ranges before rendering answers.",
            ),
            TimedTranscriptCueWrite(
                start_ms=19000,
                end_ms=41000,
                text="Folding sub-3-minute promotional shorts prevents feed noise from crowding out deep engineering briefings.",
            ),
        ),
    ),
    _DemoVideoSpec(
        video_id="vidDemoSh05",
        title="New Model Teaser in 42 Seconds! #shorts",
        channel_id="UC_DEMO_LAB_222222222222",
        channel_name="Local-First Foundry (Demo)",
        duration_seconds=42,
        published_offset_hours=30,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=12000,
                text="Quick teaser announcement for next week's keynote event—subscribe for updates!",
            ),
        ),
    ),
)

_LOCAL_MD_BYTES: Final[bytes] = (
    b"# Local-First AI Product Notes\n\n"
    b"Why auditable evidence pipelines outperform black-box summary wrappers:\n\n"
    b"1. Persist source hashes and verbatim excerpts before calling any model.\n"
    b"2. Let users switch seamlessly between zero-cost local Ollama and BYOK cloud endpoints.\n"
    b"3. Surface honest degradation instead of hallucinating on missing captions.\n"
    b"4. Export evergreen knowledge directly to Obsidian with [[wikilinks]].\n"
)


_DEMO_EN_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "does",
        "did",
        "have",
        "has",
        "had",
        "been",
        "will",
        "would",
        "could",
        "are",
        "is",
        "in",
        "of",
        "to",
        "on",
        "at",
        "by",
        "from",
        "this",
        "that",
        "these",
        "those",
        "can",
        "should",
        "about",
        "into",
        "your",
        "our",
        "their",
        "between",
        "versus",
        "point",
        "points",
        "value",
        "values",
        "level",
        "rate",
        "type",
        "kind",
        "part",
        "main",
        "most",
        "many",
        "much",
        "some",
        "demo",
        "showcase",
        "video",
        "videos",
        "channel",
        "channels",
        "content",
        "corpus",
        "material",
        "materials",
        "mention",
        "mentioned",
        "mentions",
        "exact",
        "were",
        "was",
        "benchmark",
        "benchmarked",
        "measured",
        "report",
        "reported",
        "compare",
        "explain",
        "describe",
        "extract",
        "core",
        "methodology",
        "evidence",
        "actionable",
        "steps",
        "step",
        "counter-intuitive",
        "counter",
        "intuitive",
        "claims",
        "claim",
        "metrics",
        "metric",
        "pitfalls",
        "pitfall",
        "appear",
        "practical",
        "selected",
        "consensus",
        "disagreements",
        "disagreement",
        "evolution",
        "across",
        "synthesize",
        "top",
        "product",
        "products",
        "opportunities",
        "opportunity",
        "grounded",
        "key",
        "boundary",
        "conditions",
        "condition",
        "monetization",
        "prerequisites",
        "prerequisite",
        "emerge",
        "cases",
        "case",
        "creators",
        "creator",
        "highest-conviction",
        "highest",
        "conviction",
        "implementation",
        "paths",
        "path",
        "engineering",
        "business",
        "highlighted",
        "summarize",
        "summary",
        "recurring",
        "themes",
        "theme",
        "shifts",
        "shift",
        "reusable",
        "actions",
        "action",
        "recommend",
        "recommended",
        "conclusions",
        "conclusion",
        "emphasize",
        "insights",
        "insight",
        "priority",
        "items",
        "item",
        "my",
        "starred",
        "complement",
        "challenge",
        "each",
        "other",
        "tech",
        "vs",
        "or",
        "do",
        "best",
        "love",
        "useful",
        "helpful",
        "important",
        "valuable",
        "effective",
        "necessary",
        "needed",
        "matter",
        "matters",
        "benefit",
        "benefits",
        "advantage",
        "advantages",
        "purpose",
        "role",
        "work",
        "works",
        "good",
        "avoid",
        "avoiding",
        "prevent",
        "preventing",
        "ignoring",
        "ignore",
        "skipping",
        "skip",
        "difference",
        "differences",
        "ensure",
        "ensuring",
        "keep",
        "keeping",
        "maintain",
        "maintaining",
    }
)
_DEMO_ZH_PARTICLES_RE: Final[re.Pattern[str]] = re.compile(
    r"[的了是在有和与及于把被给为要能都就也还又很最从向到让使]+"
)
_DEMO_ZH_STOP_BIGRAMS: Final[frozenset[str]] = frozenset(
    {
        "什么",
        "怎么",
        "如何",
        "为什",
        "哪些",
        "可以",
        "有没",
        "没有",
        "请问",
        "是否",
        "关于",
        "以及",
        "或者",
        "应该",
        "实测",
        "数值",
        "目前",
        "当前",
        "问题",
        "内容",
        "材料",
        "视频",
        "资料",
        "比较",
        "一下",
        "进行",
        "一个",
        "这些",
        "那些",
        "真的",
        "到底",
        "究竟",
        "这份",
        "这个",
        "在线",
        "知识",
        "识库",
        "展示",
        "示里",
        "里提",
        "提到",
        "分别",
        "样例",
        "示例",
        "这里",
        "里面",
        "给出",
        "介绍",
        "总结",
        "对比",
    }
)
_DEMO_CORPUS_META_PHRASES: Final[tuple[str, ...]] = (
    "当前内容库",
    "当前资料库",
    "核心方法论",
    "共识与关键分歧",
    "共识与分歧",
    "核心观点",
    "核心共识",
    "核心判断",
    "核心洞察",
    "落地建议",
    "可落地步骤",
    "可落地结论",
    "避坑指南",
    "避坑警示",
    "避坑建议",
    "落地路径",
    "行动清单",
    "实操动作",
    "边界条件",
    "产品切入点",
    "反直觉",
    "直接复用",
    "互补与碰撞",
    "高分内容",
    "高频避坑",
    "避坑点",
    "切入机会",
    "总结全部",
    "全部来源",
    "帮我总结",
    "总结一下",
    "概括一下",
    "summarize",
    "key takeaways",
    "synthesize",
    "extract the core",
    "compare core",
    "actionable steps",
    "priority action",
    "practical pitfalls",
    "core methodology",
    "core claims",
    "recurring themes",
    "monetization",
    "complement or challenge",
)


_DEMO_BILINGUAL_EQUIVALENTS: Final[tuple[tuple[str, ...], ...]] = (
    ("状态机", "state", "machine", "machines"),
    ("架构", "architecture", "pipeline", "pipelines", "state", "machine", "machines"),
    ("确定性", "deterministic"),
    ("工具", "tool", "tools"),
    ("调用", "call", "calls"),
    ("约束", "bounded", "schema", "schemas", "fail-closed"),
    ("崩溃", "crash", "crashes", "recovery"),
    ("证据", "evidence", "grounded"),
    ("验证", "可验证", "verify", "verified", "validation", "auditable"),
    ("引用", "citation", "citations", "anchor", "anchors"),
    ("溯源", "追溯", "可追溯", "citation", "citations", "transcript", "verify", "verified", "auditable"),
    ("本地", "local", "local-first"),
    ("模型", "model", "models", "ollama"),
    ("一人公司", "solo", "builder", "builders"),
    ("留存", "高留存", "retention"),
    ("高毛利", "high-margin", "margin"),
    ("工作流", "workflow", "workflows"),
    ("生产", "生产级", "production"),
    ("字幕", "caption", "captions", "transcript"),
    ("双链", "wikilink", "wikilinks", "obsidian"),
    ("短片", "shorts", "3-minute", "teaser"),
    ("噪音", "noise"),
    ("总结", "summary", "summarization", "summaries"),
    ("幻觉", "hallucinat", "fabricated"),
)


_DEMO_UNSUPPORTED_ATTR_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:多少钱|价格多少|售价|收费标准|怎么收费|收费|定价|年费|月费|订阅费|成本多少|"
    r"市值|估值|融资(?:额|轮次)?|融了多少|年营收|收入多少|股价|温度多少|气温|海拔|"
    r"多少(?:亿|万|美元|美金|块钱|人民币|元|度|公里|克|斤)|几(?:美元|美金|块钱|元)|"
    r"\bhow\s+much\s+(?:does|is|are|do|did|will)\b|"
    r"\b(?:price|cost|pricing|fee|subscription\s+fee|monthly\s+fee|annual\s+fee)\s+(?:of|for)\b|"
    r"\bwhat(?:'s|\s+is)\s+the\s+(?:price|cost|pricing|fee|valuation|market\s+cap|revenue|funding|stock\s+price|temperature|weather)\b|"
    r"\bhow\s+expensive\b|\bfunding\s+round\b|\bstock\s+price\b|\bmarket\s+cap\b|\bannual\s+revenue\b|"
    r"\b\d+(?:\.\d+)?\s*(?:usd|dollars?|cny|rmb)\b)",
    re.IGNORECASE,
)
_DEMO_AVOIDANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:(?:避免|防止|防范|杜绝|以免|别|不要|不让)\s*(?:直接|盲目|无意)?(?:忽略|跳过|漏掉|遗漏|抛弃|摒弃|取消)|"
    r"\b(?:avoid|prevent|stop|not\s+to)\s+(?:ignoring|skipping|dropping|omitting|missing|losing)\b)",
    re.IGNORECASE,
)
_DEMO_NEGATION_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:不需要|不用|不必|无需|为什么不|为什么不用|为什么不要|取消|跳过|忽略|摒弃|抛弃|"
    r"(?:don't|do\s+not|doesn't|does\s+not|we\s+don't|no)\s+need(?:\s+for)?|"
    r"without\s+(?:requiring|using|any)|"
    r"why\s+(?:skip|ignore|drop|abandon|discard|remove)\b|"
    r"skip(?:ping)?\s+(?:evidence|citations?|state\s+machines?)|"
    r"ignor(?:e|ing)\s+(?:evidence|citations?))",
    re.IGNORECASE,
)
_DEMO_CORE_ANCHOR_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:证据|引用|状态机|哈希|核验|检查点|evidence|citation|citations|state\s+machine)",
    re.IGNORECASE,
)


def _demo_extract_concepts(question_text: str) -> tuple[list[str], list[str]]:
    q_lower = unicodedata.normalize("NFKC", question_text).lower()
    en_tokens = [
        tok
        for tok in re.findall(r"[a-z][a-z0-9_-]{1,}", q_lower)
        if tok not in _DEMO_EN_STOPWORDS and len(tok) >= 2
    ]
    zh_clean = re.sub(
        r"(?:避免忽略|防止忽略|避免遗漏|防止遗漏|避免跳过|防止跳过|避免|防止|防范|杜绝|以免|有用|重要|价值|意义|优势|必要性|"
        r"是什么意思|是什么含义|什么含义|什么意思|的意思|指什么|含义是|解释一下|解释下|请帮我|帮我|概括一下|总结一下|讲了什么|说了什么|谈了什么|介绍一下|为什么|怎么|如何|怎样|哪些|有些|什么|是否|可以|能否|请问|对比|比较|总结|围绕|结合|打造|适合|实测|数值|目前|当前内容库|当前资料库|当前|问题|内容|材料|视频|资料|进行|一下|之间|方面|关于|以及|或者|应该|真的|到底|究竟|这份|这个|这些|那些|这\s*\d*\s*篇(?:指定)?|这篇(?:指定)?|指定|在线|知识库|展示|提到|分别|样例|示例|这里|里面|给出|介绍|共性|主要共识|关键共识|核心共识|共识与关键分歧|共识与分歧|核心观点上|核心观点|观点上|观点|核心方法论|核心判断|核心洞察|核心|方法论|分歧|共识|实践|要点|结论|工作流|方案|原理|作用|好处|原因|需要|基于|不同|跨来源|各来源|各自|来源|主要|关键|已沉淀|沉淀|梳理|高分|提炼|值得|最值得|优先落地|优先|可落地步骤|可落地结论|可落地|落地建议|落地路径|落地|产品化|产品设计|产品切入点|切入机会|产品机会|切入点|机会|方向|工程落地|工程实践|工程|原话|指出|高频主题|高频|避坑指南|避坑警示|避坑建议|避坑点|避坑|边界条件|边界|条件|前置|假设|要用|这两个专题|两个专题|专题下|专题|综合|可执行|建议|指南|关联|反直觉判断|反直觉结论|反直觉|数据指标|警示|代表性|实战案例|实战避坑|实战|案例|横向|演进脉络|脉络|时间轴原话|时间轴|立即执行|实操动作|揭示|容易踩坑|踩坑|误区|商业化前提|商业化|商业验证|商业判断|商业变现|变现动作|前提|判断变化|判断|创作者|最具确定性|最具|路径|近期|主题|变化|可直接复用|直接复用|可复用|复用|设计|动作|重点强调|强调|我收藏|收藏|高价值|洞察|行动清单|清单|技术路线|路线|互补与碰撞|互补|碰撞|论据|步骤|提出|会不会)",
        " ",
        unicodedata.normalize("NFKC", question_text),
    )
    zh_clean = _DEMO_ZH_PARTICLES_RE.sub(" ", zh_clean)
    zh_phrases = [
        run
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", zh_clean)
        if run not in _DEMO_ZH_STOP_BIGRAMS
    ]
    return en_tokens, zh_phrases


def _demo_zh_token_supported(token: str, evidence_hay: str) -> bool:
    if token in evidence_hay:
        return True
    for group in _DEMO_BILINGUAL_EQUIVALENTS:
        if any(token == g or (len(token) >= 2 and token in g and not g.isascii()) for g in group):
            if any(alt in evidence_hay for alt in group):
                return True
    return False


def _demo_concept_supported(concept: str, evidence_hay: str, evidence_en_stems: set[str]) -> bool:
    if concept.isascii():
        if concept in evidence_en_stems or concept in evidence_hay:
            return True
        if len(concept) > 3 and concept.endswith("s") and concept[:-1] in evidence_en_stems:
            return True
        for group in _DEMO_BILINGUAL_EQUIVALENTS:
            if concept in group and any(alt in evidence_hay for alt in group):
                return True
        return False
    # Chinese concept phrase
    if _demo_zh_token_supported(concept, evidence_hay):
        return True
    if len(concept) < 3:
        return False
    # Exact character-coverage check across 2..4 char spans: every substantive character
    # must be covered by a term supported in evidence_hay or bilingual equivalents.
    n = len(concept)
    covered = [False] * n
    for i in range(n):
        for span_len in (4, 3, 2):
            if i + span_len <= n:
                span = concept[i : i + span_len]
                if span not in _DEMO_ZH_STOP_BIGRAMS and _demo_zh_token_supported(
                    span, evidence_hay
                ):
                    for k in range(i, i + span_len):
                        covered[k] = True
    harmless_chars = set("可的性级化链型中各及组")
    for idx, ch in enumerate(concept):
        if not covered[idx] and ch not in harmless_chars:
            return False
    return any(covered)


def _demo_question_has_evidence_support(question_text: str, user_prompt: str) -> bool:
    """Reject unsupported attributes, inverted premises, and off-topic questions."""
    q_norm = unicodedata.normalize("NFKC", question_text).strip()
    if _DEMO_UNSUPPORTED_ATTR_RE.search(q_norm):
        return False
    q_for_negation = _DEMO_AVOIDANCE_RE.sub(" ", q_norm)
    if _DEMO_NEGATION_RE.search(q_for_negation) and _DEMO_CORE_ANCHOR_RE.search(q_norm):
        return False

    cand_match = re.search(
        r"<untrusted_evidence_candidates>(.*?)</untrusted_evidence_candidates>",
        user_prompt,
        re.DOTALL,
    )
    evidence_hay = (cand_match.group(1) if cand_match else user_prompt).lower()
    scope_match = re.search(r"当前检索范围[：:]\s*([^\n]+)", user_prompt)
    if scope_match:
        evidence_hay = f"{evidence_hay}\n{scope_match.group(1).lower()}"
    evidence_en_words = set(re.findall(r"[a-z][a-z0-9_-]{1,}", evidence_hay))
    evidence_en_stems = evidence_en_words | {
        w[:-1] for w in evidence_en_words if len(w) > 3 and w.endswith("s")
    }

    en_tokens, zh_phrases = _demo_extract_concepts(question_text)
    concepts = en_tokens + zh_phrases
    matched: list[str] = []
    unmatched: list[str] = []
    for concept in concepts:
        if _demo_concept_supported(concept, evidence_hay, evidence_en_stems):
            matched.append(concept)
        else:
            unmatched.append(concept)

    is_corpus_meta = any(
        phrase in question_text.lower() or phrase in question_text
        for phrase in _DEMO_CORPUS_META_PHRASES
    )
    if is_corpus_meta and len(unmatched) == 0:
        return True

    if not matched or unmatched:
        return False
    return True


def _demo_score_candidate(desc: str, en_tokens: list[str], zh_phrases: list[str]) -> int:
    low = desc.lower()
    words = set(re.findall(r"[a-z][a-z0-9_-]{1,}", low))
    stems = words | {w[:-1] for w in words if len(w) > 3 and w.endswith("s")}
    return sum(
        1 for c in (en_tokens + zh_phrases) if _demo_concept_supported(c, low, stems)
    )


class _DemoShowcaseCompleter:
    """Offline deterministic responder supporting curated seeds and live judge Q&A."""

    def __call__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "WEEKLY_BRIEF_SCHEMA" in system_prompt:
            return (
                {
                    "title_zh": "《本周 AI 工程与产品实战情报周报（Demo 精选）》",
                    "executive_summary_zh": (
                        "综合 YouTube、B 站公开课与本地设计文档，本周高价值信号集中在两点："
                        "（1）用确定性状态机与可追溯证据引用解决 Agent 工程可靠性；"
                        "（2）个人开发者通过“本机 Ollama 零成本 + BYOK 云端隔离 + Obsidian 知识沉淀”构建高留存垂直工具。"
                    ),
                    "top_shifts_zh": [
                        {
                            "title_zh": "从黑盒摘要转向“原话时间戳证据 + 可审计引用链”",
                            "detail_zh": "核心结论先落盘源码/字幕哈希并绑定 [E1]..[En] 证据锚点，杜绝无来源瞎编。",
                            "topic_name": _TOPIC_AGENT,
                        },
                        {
                            "title_zh": "本地免费模型降低冷启动门槛，BYOK 守住隐私与成本底线",
                            "detail_zh": "日常总结跑在本机 Ollama，按需切换自带 API Key，无静默扣费或数据外泄。",
                            "topic_name": _TOPIC_SOLO,
                        },
                    ],
                    "product_opportunities_zh": [
                        "为研究者打造跨 YouTube / B 站 / 本地 Markdown 的统一证据知识库",
                        "自动折叠 <180 秒宣发短片噪音，将精力聚焦在高信噪比深度长内容",
                    ],
                    "business_monetization_zh": [
                        "开源本地单机核心 + 团队协作/Obsidian 自动化工作流商业授权",
                    ],
                },
                provider,
                model,
            )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            matches = re.findall(r"\[(E\d+)\]\s*([^\n]+)", user_prompt)
            all_refs: list[tuple[str, str]] = []
            seen_refs: set[str] = set()
            for ref_id, desc in matches:
                if ref_id not in seen_refs:
                    seen_refs.add(ref_id)
                    all_refs.append((ref_id, desc.strip()[:220]))

            q_match = re.search(r"用户(?:研究)?问题[：:]\s*(.+)", user_prompt)
            question_text = q_match.group(1).strip() if q_match else "当前所选资料的核心洞察"
            supported = bool(all_refs) and _demo_question_has_evidence_support(
                question_text, user_prompt
            )
            if supported:
                en_toks, zh_phrs = _demo_extract_concepts(question_text)
                scored_refs = sorted(
                    all_refs,
                    key=lambda item: _demo_score_candidate(item[1], en_toks, zh_phrs),
                    reverse=True,
                )
                matched_refs = [
                    r
                    for r in scored_refs
                    if _demo_score_candidate(r[1], en_toks, zh_phrs) > 0
                ]
                if not matched_refs:
                    matched_refs = scored_refs[:3]
                else:
                    matched_refs = matched_refs[:3]

                answer_parts: list[str] = []
                takeaways: list[str] = []
                for ref_id, desc in matched_refs:
                    low_desc = desc.lower()
                    if any(k in low_desc for k in ("state machine", "deterministic", "状态机")):
                        answer_parts.append(
                            f"生产级 AI 工作流应以确定性状态机收敛外部副作用与工具契约 [{ref_id}]"
                        )
                        takeaways.append(f"以确定性状态机和 SQLite 断点管理外部工具副作用 [{ref_id}]")
                    elif any(k in low_desc for k in ("ollama", "byok", "solo", "local")):
                        answer_parts.append(
                            f"通过本机免费 Ollama 搭配受控 BYOK 与 Obsidian 双链沉淀提升留存 [{ref_id}]"
                        )
                        takeaways.append(f"本机 Ollama 零边际成本搭配 BYOK 隔离与 Obsidian 导出 [{ref_id}]")
                    elif any(k in low_desc for k in ("citation", "evidence", "transcript", "证据", "字幕")):
                        answer_parts.append(
                            f"将提炼结论与原始字幕哈希、时间轴/偏移证据绑定以防幻觉 [{ref_id}]"
                        )
                        takeaways.append(f"先持久化原文哈希与证据边界，再输出带引用结论 [{ref_id}]")
                    else:
                        snippet_m = re.search(r"原话摘录[：:]\s*(.+)$", desc)
                        clean_snip = (snippet_m.group(1) if snippet_m else desc).strip()[:90]
                        answer_parts.append(f"依据原文记录「{clean_snip}」[{ref_id}]")
                        takeaways.append(f"依据 [{ref_id}] 原文记录核验关键事实")

                ref_tags = "、".join(f"[{r}]" for r, _ in matched_refs)
                lead_ref = matched_refs[0][0]
                topic_ref = re.sub(r"[。！？!?；;\n]+", "、", question_text).strip("、")
                answer_zh = (
                    f"【离线合成样例回放】围绕「{topic_ref}」（{ref_tags}），结合当前资料库已验证证据："
                    + "；".join(answer_parts)
                    + "。"
                )
                citations = [
                    {"ref": ref_id, "note_zh": f"关联原始证据：{desc[:100]}"}
                    for ref_id, desc in matched_refs
                ]
                dedup_takeaways = list(dict.fromkeys(takeaways))[:4]
                actions = [
                    f"点击下方证据引用（[{lead_ref}] 等）直接跳转到原视频/文档对应片段核验原文",
                    f"基于 [{lead_ref}] 等关联证据点击「导出 Obsidian 双链笔记」将跨视频结论沉淀至个人知识库",
                ]
                refusal_reason_zh = ""
                refs = matched_refs
            else:
                refs = all_refs[:3]
                refusal_reason_zh = (
                    "当前离线样例资料库中的可核验字幕与本地笔记未包含与该问题直接相关的原文证据，"
                    "依据 Fail-Closed 反幻觉策略拒绝作答；下方「相关片段」仅作库内检索参考，不作为结论依据。"
                    if refs
                    else "当前限定范围内暂无匹配的带时间轴字幕或本地文本文档片段。"
                )
                answer_zh = (
                    f"【离线合成样例回放 · 证据不足拒答】当前样例资料库中未找到可直接支撑「{question_text}」的原文证据。"
                )
                citations = []
                dedup_takeaways = []
                actions = []
            return (
                {
                    "answerable": supported,
                    "refusal_reason_zh": refusal_reason_zh,
                    "answer_zh": answer_zh,
                    "key_takeaways_zh": dedup_takeaways,
                    "action_items_zh": actions,
                    "citations": citations,
                },
                "demo-replay",
                "synthetic-showcase-v1",
            )

        # Content / video / local text distillation payloads
        if "vidDemoSh05" in user_prompt or "duration_seconds: 42" in user_prompt:
            return (
                {
                    "headline_zh": "42 秒模型预热宣发短片（自动识别并折叠降噪）",
                    "summary_zh": "该内容为 42 秒发布预告短片，不含技术架构或可执行方法论，已自动归类至 Shorts 噪音抽屉。",
                    "score": 2.6,
                    "score_reason_zh": "短时宣传预热视频，信息密度低，不占用核心干货流。",
                    "recommendation_tier": "SKIP_NOISE",
                    "content_bucket": "SHORTS_PROMO",
                    "topics_zh": ["模型资讯短片"],
                    "topic_cluster_zh": _TOPIC_AGENT,
                    "core_points": [{"text_zh": "预告下周发布会，无技术细节", "cue_window_index": 0}],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": ["订阅催更口播与预告短片"],
                },
                provider,
                model,
            )

        if "vidDemoSol2" in user_prompt or "Solo Builders" in user_prompt:
            return (
                {
                    "headline_zh": "一人公司 AI 产品实战：本地优先架构与零边际成本洞察漏斗",
                    "summary_zh": (
                        "系统阐述如何依靠本机 Ollama 免费推理降低用户冷启动阻力，配合 BYOK 隔离与 "
                        "Obsidian [[wikilinks]] 导出打造不可替代的知识工作流，并在无字幕时坚持诚实降级。"
                    ),
                    "score": 9.1,
                    "score_reason_zh": "兼具冷启动策略、成本架构与真实产品留存洞察。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["本地优先架构", "BYOK 商业模式"],
                    "topic_cluster_zh": _TOPIC_SOLO,
                    "core_points": [
                        {"text_zh": "支持本地免费 Ollama 与 BYOK 双轨消除获客费用墙", "cue_window_index": 0},
                        {"text_zh": "直接输出可复用 Obsidian 双链资产提高迁移壁垒", "cue_window_index": 1},
                        {"text_zh": "缺字幕或缺模型时诚实提示，避免幻觉摧毁用户信任", "cue_window_index": 2},
                    ],
                    "product_opportunities_zh": ["面向创作者与独立开发者的跨平台情报沉淀工作台"],
                    "business_opportunities_zh": ["开源单机免费 + 团队协同与专业工作流插件收费"],
                    "filtered_noise_zh": ["课程营销暖场寒暄"],
                },
                provider,
                model,
            )

        if "BV1DemoArch3" in user_prompt or "本地优先知识库与反幻觉证据链实战架构" in user_prompt:
            return (
                {
                    "headline_zh": "多源知识工作台实战：从 B 站与长视频字幕构建零幻觉证据链",
                    "summary_zh": (
                        "演示如何将 B 站公开课字幕与 YouTube 技术访谈纳入同一套哈希锁定与时间戳证据体系，"
                        "让每一句中文结论都能一键回溯原话语境。"
                    ),
                    "score": 8.9,
                    "score_reason_zh": "贴合国内多平台技术学习与可审计知识管理真实刚需。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "TUTORIAL",
                    "topics_zh": ["B站技术课程", "反幻觉证据链"],
                    "topic_cluster_zh": _TOPIC_AGENT,
                    "core_points": [
                        {"text_zh": "没有可回溯原话时间轴的摘要极易隐藏模型幻觉", "cue_window_index": 0},
                        {"text_zh": "先在 SQLite 锁定字幕哈希再绑定引用编号确保可审计性", "cue_window_index": 1},
                        {"text_zh": "打通 B 站 + YouTube + Obsidian 实现中英文双语知识复用", "cue_window_index": 2},
                    ],
                    "product_opportunities_zh": ["中英混排多源课程的证据对照与双语导读卡片"],
                    "business_opportunities_zh": ["面向高校科研组与咨询团队的私有知识库部署方案"],
                    "filtered_noise_zh": ["片头一键三连口播"],
                },
                provider,
                model,
            )

        if "vidDemoEvl4" in user_prompt or "Closing the Eval Loop" in user_prompt:
            return (
                {
                    "headline_zh": "告别 AI 瞎编：用可回溯时间戳引用替代黑盒摘要总结",
                    "summary_zh": (
                        "说明跨视频问答为何必须先在后端校验 [E1]..[En] 证据边界并折叠短视频噪音，"
                        "从而在工程架构层切断伪造引用的可能。"
                    ),
                    "score": 8.7,
                    "score_reason_zh": "给出清晰的引用校验规则与信噪比过滤基准。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["引用校验", "评测闭环"],
                    "topic_cluster_zh": _TOPIC_AGENT,
                    "core_points": [
                        {"text_zh": "跨视频回答中的每个引用必须在输出前校验真实字幕范围", "cue_window_index": 0},
                        {"text_zh": "自动折叠低于 180 秒的宣发短片避免污染长视频洞察流", "cue_window_index": 1},
                    ],
                    "product_opportunities_zh": ["带引用合法性红线拦截的跨文档研究助理"],
                    "business_opportunities_zh": ["行业研报辅助核查工具"],
                    "filtered_noise_zh": ["赞助商插播广告"],
                },
                provider,
                model,
            )

        if "demo-architecture-notes.md" in user_prompt or "auditable evidence pipelines" in user_prompt:
            return (
                {
                    "headline_zh": "离线笔记精炼：为什么时间轴证据与无幻觉降级决定工具留存率",
                    "summary_zh": (
                        "沉淀个人研发架构笔记：先持久化原文哈希、再按本地 Ollama / BYOK 路由提炼洞察，"
                        "并在缺字幕/缺语音模型时拒绝编造内容，最终输出 Obsidian 双链文档。"
                    ),
                    "score": 8.6,
                    "score_reason_zh": "结构紧凑、原则明确，直接验证本地 Markdown 免时间戳直出链路。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "TUTORIAL",
                    "topics_zh": ["架构笔记", "本地知识库"],
                    "topic_cluster_zh": _TOPIC_SOLO,
                    "core_points": [
                        {"text_zh": "调用任何大模型前先保存源码哈希与原文切片", "section_index": 2},
                        {"text_zh": "支持零成本本地 Ollama 与按需云端 BYOK 无缝切换", "section_index": 3},
                    ],
                    "product_opportunities_zh": ["本地 Markdown 笔记与视频证据库统一索引"],
                    "business_opportunities_zh": ["知识工作者的个人数字图书馆会员"],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )

        return (
            {
                "headline_zh": "生产级 AI Agent 核心架构：确定性状态机与可审计工具边界",
                "summary_zh": (
                    "深入剖析为何把副作用操作放进自由对话循环容易崩溃，并给出“SQLite 检查点 + "
                    "Schema 边界校验 + 数据抓取与推理彻底解耦”的生产级参考设计。"
                ),
                "score": 9.4,
                "score_reason_zh": "一线生产环境 Agent 状态机与错误恢复设计的浓缩指南。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["状态机编排", "工具契约"],
                "topic_cluster_zh": _TOPIC_AGENT,
                "core_points": [
                    {"text_zh": "用显式状态机替代无约束对话循环管理外部副作用", "cue_window_index": 0},
                    {"text_zh": "所有工具调用必须具备参数 Schema、Fail-Closed 拦截与持久化断点", "cue_window_index": 1},
                    {"text_zh": "解耦确定性内容抓取与可选模型推理，保障崩溃后幂等恢复", "cue_window_index": 2},
                ],
                "product_opportunities_zh": ["自带操作审计日志与断点恢复能力的本地 Agent 工作台"],
                "business_opportunities_zh": ["高可靠企业研发内部自动化助手"],
                "filtered_noise_zh": ["直播开场调试片段"],
            },
            provider,
            model,
        )


@dataclass(frozen=True, slots=True)
class DemoShowcaseRuntime:
    """Running/prepared state of an isolated public showcase demo instance."""

    root: Path
    database: Path
    data_root: Path
    composition: LocalSourceRunRuntime
    hub: WorkspaceIntelligenceHub
    fast_app: FastReadApiApplication
    seeded_videos: int


def _load_demo_config(project_root: Path, demo_root: Path) -> AppConfig:
    demo_settings = demo_root / "config" / "settings.yaml"
    demo_channels = demo_root / "config" / "channels.yaml"
    demo_settings.parent.mkdir(parents=True, exist_ok=True)
    if not demo_settings.is_file():
        candidate_settings = project_root / "config" / "settings.example.yaml"
        if not candidate_settings.is_file():
            candidate_settings = Path(__file__).resolve().parents[2] / "config" / "settings.example.yaml"
        raw_text = candidate_settings.read_text(encoding="utf-8")
        out_lines = [
            f"  vault_root: {demo_root / 'vault'}"
            if line.strip().startswith("vault_root:")
            else line
            for line in raw_text.splitlines()
        ]
        demo_settings.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    if not demo_channels.is_file():
        candidate_channels = project_root / "config" / "channels.example.yaml"
        if not candidate_channels.is_file():
            candidate_channels = Path(__file__).resolve().parents[2] / "config" / "channels.example.yaml"
        channels_txt = candidate_channels.read_text(encoding="utf-8").replace(
            "enabled: true", "enabled: false"
        )
        demo_channels.write_text(channels_txt, encoding="utf-8")
    values = load_settings(demo_settings).model_dump()
    values["storage"]["vault_root"] = str(demo_root / "vault")
    values["general"]["output_language"] = "zh-CN"
    return AppConfig(channels=(), settings=AppSettings.model_validate(values))


def _seed_youtube_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    spec: _DemoVideoSpec,
    base_now: datetime,
) -> None:
    published_at = base_now - timedelta(hours=spec.published_offset_hours)
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=spec.video_id,
            channel_id=spec.channel_id,
            channel_name=spec.channel_name,
            title=spec.title,
            description=f"Curated demo content: {spec.title}",
            source_url=f"https://www.youtube.com/watch?v={spec.video_id}",
            published_at=published_at,
            duration_seconds=spec.duration_seconds,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=published_at,
    )
    repo.advance_pipeline(
        spec.video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=published_at,
    )
    repo.advance_pipeline(
        spec.video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=published_at,
    )
    canonical_text = "\n".join(c.text for c in spec.cues).encode("utf-8")
    rel = f"transcripts/canonical/{spec.video_id}.txt"
    write_managed(data_root, rel, canonical_text)
    art_id = f"canonical:{spec.video_id}"
    repo.upsert_artifact(
        ArtifactWrite(
            artifact_id=art_id,
            artifact_key=art_id,
            video_id=spec.video_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=rel,
            content_hash=sha256(canonical_text),
            provider="youtube",
            model=None,
            producer_version="v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=published_at,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=spec.video_id,
        canonical_artifact_id=art_id,
        cues=spec.cues,
    )
    repo.create_timed_transcript(timed, now=published_at)
    for idx, cue in enumerate(spec.cues):
        ev = EvidenceWrite(
            evidence_id=build_evidence_id(
                video_id=spec.video_id,
                artifact_id=art_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
            ),
            video_id=spec.video_id,
            artifact_id=art_id,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        )
        repo.create_evidence_with_text_binding(
            ev,
            EvidenceTextBindingWrite.from_timed_transcript(
                evidence=ev,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=idx,
                end_cue_index=idx + 1,
                excerpt=cue.text,
            ),
            now=published_at,
        )
    ExtractiveSummaryService(repo, data_root).create(spec.video_id, now=published_at)
    repo.link_source_video(
        source_id=source_id,
        video_id=spec.video_id,
        discovered_at=published_at,
    )


def prepare_demo_showcase(
    project_root: Path,
    *,
    demo_root: Path | None = None,
    reset: bool = False,
) -> DemoShowcaseRuntime:
    """Create or load an isolated, zero-network showcase workspace ready for evaluation."""

    resolved_project = project_root.resolve()
    resolved_demo = (demo_root or default_demo_root(resolved_project)).resolve()
    if resolved_demo in {resolved_project, resolved_project / ".var", resolved_project / ".var" / "owner"}:
        raise ValueError("Refusing to use protected workspace path as demo root")
    if resolved_demo.is_symlink() or (resolved_demo.exists() and not resolved_demo.is_dir()):
        raise ValueError("Refusing to use non-directory or symlink path as demo root")

    marker = resolved_demo / _DEMO_MARKER
    db_path = resolved_demo / "state.sqlite3"
    sidecar_path = resolved_demo / ".workspace-ai" / "hub.sqlite3"
    has_marker = _has_valid_demo_marker(resolved_demo)
    already_seeded = has_marker and db_path.is_file() and sidecar_path.is_file()

    if reset:
        if resolved_demo.exists() and any(resolved_demo.iterdir()):
            if not has_marker:
                raise ValueError(
                    "Refusing to reset non-empty directory without a valid demo showcase marker; original files were preserved."
                )
            _clean_demo_owned_entries(resolved_demo)
    elif not already_seeded:
        if resolved_demo.exists() and any(resolved_demo.iterdir()):
            if has_marker:
                raise ValueError(
                    "Demo showcase workspace is incomplete or corrupted; original files were preserved. Re-run with --reset to rebuild owned demo files."
                )
            raise ValueError(
                "Refusing to initialize demo showcase in a non-empty directory without a demo marker; original files were preserved."
            )

    if reset or not already_seeded:
        for sub in ("data", "logs", "templates", "vault"):
            (resolved_demo / sub).mkdir(parents=True, exist_ok=True)

    config = _load_demo_config(resolved_project, resolved_demo)
    data_root = resolved_demo / "data"

    # Use an advancing clock starting before demo videos during source setup
    # so enrolled observations satisfy published_at > followed_at invariants,
    # then a live UTC clock once interactive queries begin.
    live_mode = already_seeded and not reset
    seed_base = _DEMO_BASE_NOW - timedelta(days=3)
    seed_tick = [0]

    def runtime_now() -> datetime:
        if live_mode:
            return datetime.now(UTC)
        seed_tick[0] += 1
        return seed_base + timedelta(minutes=seed_tick[0] * 10)

    composition = build_local_source_run_runtime(
        config=config,
        project_root=resolved_demo,
        database=db_path,
        credential_store=_DemoSecretStore(),
        bigmodel_credential_store=_DemoSecretStore(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=runtime_now,
    )
    composition.application._runtime_mode = "PUBLIC_DEMO"
    composition.application._demo_data = True

    completer = _DemoShowcaseCompleter()
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=data_root,
        project_root=resolved_demo,
        byok_credential_store=_DemoSecretStore(),
        llm_completer=completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=runtime_now,
    )

    if reset or not already_seeded:
        repo = composition.repository
        oai_ch = "UC_DEMO_OAI_111111111111"
        lab_ch = "UC_DEMO_LAB_222222222222"
        src_oai = composition.product.add_source(
            url=f"https://www.youtube.com/channel/{oai_ch}",
            processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
        )
        src_lab = composition.product.add_source(
            url=f"https://www.youtube.com/channel/{lab_ch}",
            processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
        )
        observed_iso = (_DEMO_BASE_NOW + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with repo._connect() as conn:
            conn.execute(
                "UPDATE source_subscriptions SET display_name = ? WHERE source_id = ?",
                ("Atlas Agent Lab (Demo)", src_oai.source_id),
            )
            conn.execute(
                "UPDATE source_subscriptions SET display_name = ? WHERE source_id = ?",
                ("Local-First Foundry (Demo)", src_lab.source_id),
            )
            for src_item in (src_oai, src_lab):
                followed_iso = src_item.created_at.astimezone(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                conn.execute(
                    "INSERT INTO source_tracking_state "
                    "(source_id, contract, followed_at, baseline_at, verified_at, latest_published_at, next_page, coverage, health, next_check_at) "
                    "VALUES (?, 'source-tracking-v1', ?, ?, ?, ?, 1, 'COMPLETE', 'HEALTHY', ?)",
                    (
                        src_item.source_id,
                        followed_iso,
                        observed_iso,
                        observed_iso,
                        (_DEMO_BASE_NOW - timedelta(hours=6)).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        "2026-11-30T00:00:00Z",
                    ),
                )
            conn.commit()

        source_for_channel = {
            oai_ch: src_oai.source_id,
            lab_ch: src_lab.source_id,
        }
        obs_rows: list[tuple[object, ...]] = []
        for spec in _YOUTUBE_DEMO_VIDEOS:
            sid = source_for_channel[spec.channel_id]
            _seed_youtube_video(
                repo,
                data_root,
                source_id=sid,
                spec=spec,
                base_now=_DEMO_BASE_NOW,
            )
            pub_str = (_DEMO_BASE_NOW - timedelta(hours=spec.published_offset_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            obs_rows.append(
                (sid, spec.video_id, pub_str, observed_iso, 0, "ENROLLED", spec.video_id, None)
            )
        with repo._connect() as conn:
            conn.executemany(
                "INSERT INTO source_observations "
                "(source_id, canonical_identity, published_at, observed_at, baseline, enrollment, content_id, error_code) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                obs_rows,
            )
            conn.commit()

        seed_base = _DEMO_BASE_NOW
        seed_tick[0] = 0

        # Import an authentic Bilibili educational video via BilibiliContentProvider
        bili_provider = BilibiliContentProvider(
            repo,
            data_root,
            adapter=_DemoBilibiliAdapter(now=_DEMO_BASE_NOW - timedelta(hours=16)),
            now=lambda: _DEMO_BASE_NOW - timedelta(hours=16),
        )
        bili_res = bili_provider.import_input("https://www.bilibili.com/video/BV1DemoArch3/")

        # Import a verified local Markdown engineering note
        md_code, md_payload = composition.application.handle(
            "POST",
            "/api/v1/local/imports?filename=demo-architecture-notes.md",
            _LOCAL_MD_BYTES,
        )
        if md_code != 201:
            raise RuntimeError(f"Unexpected local import failure: {md_payload}")
        md_info = cast(dict[str, Any], md_payload["import"])
        md_id = str(md_info["content_id"])

        all_ids = [*(spec.video_id for spec in _YOUTUBE_DEMO_VIDEOS), bili_res.content_id, md_id]
        for vid in all_ids:
            hub.distill_video(vid)

        hub.generate_weekly_brief()
        for topic in repo.list_topics():
            if topic.name in {_TOPIC_AGENT, _TOPIC_SOLO}:
                repo.set_topic_pinned(
                    topic_id=topic.topic_id, pinned=True, now=runtime_now()
                )

        hub.ask_research_question(
            {"question": "为什么生产级 AI Agent 要用状态机约束工具调用？对比各来源实践共识。"}
        )
        hub.ask_research_question(
            {"question": "如何围绕本地模型与可验证证据链打造适合一人公司的高留存 AI 工具？"}
        )

        marker.write_text(
            json.dumps(
                {"version": 1, "demo_owner": _DEMO_OWNER, "seeded_items": all_ids},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        readiness = composition.backup_restore.readiness()
        if not readiness.get("ready"):
            raise RuntimeError(f"Demo showcase DB not backup-ready: {readiness}")

    live_mode = True
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    video_count = len(composition.repository.list_videos(limit=100))
    return DemoShowcaseRuntime(
        root=resolved_demo,
        database=db_path,
        data_root=data_root,
        composition=composition,
        hub=hub,
        fast_app=fast_app,
        seeded_videos=video_count,
    )


def serve_demo_showcase(
    project_root: Path,
    *,
    port: int = 8765,
    demo_root: Path | None = None,
    reset: bool = False,
    web_dir: Path | None = None,
    serve_web: bool = True,
) -> ExitCode:
    """Prepare the showcase dataset and serve UI + API cleanly on one loopback port."""

    if port < 1024 or port > 65535:
        return ExitCode.USAGE_OR_CONFIGURATION

    runtime = prepare_demo_showcase(project_root, demo_root=demo_root, reset=reset)

    static_dir: Path | None = None
    if serve_web:
        candidate = (web_dir or (project_root.resolve() / "frontend" / "dist")).resolve()
        if (candidate / "index.html").is_file():
            static_dir = candidate
        else:
            print(
                f"NOTE: Built frontend bundle not found at {candidate}. "
                "Run `cd frontend && npm ci && npm run build` for single-port UI, or use Vite dev server.",
                flush=True,
            )

    server = serve_loopback(
        cast(LocalApiApplication, runtime.fast_app),
        port=port,
        static_dir=static_dir,
    )

    def request_stop(signum: int, frame: FrameType | None) -> None:
        del signum, frame
        threading.Thread(target=server.shutdown, daemon=True).start()

    previous_handlers = (
        {
            sig: signal.signal(sig, request_stop)
            for sig in (signal.SIGTERM, signal.SIGINT)
        }
        if threading.current_thread() is threading.main_thread()
        else {}
    )

    ui_line = (
        f"Web UI & API ready at http://127.0.0.1:{port}/"
        if static_dir is not None
        else f"API ready at http://127.0.0.1:{port}/api/v1/system (static UI disabled)"
    )
    print(
        f"[youtube-intel demo] Public Beta showcase running ({runtime.seeded_videos} curated items)\n"
        f"  {ui_line}\n"
        f"  Isolated runtime root: {runtime.root}\n"
        "  Press Ctrl+C to stop.",
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
    return ExitCode.OK


__all__ = [
    "DemoShowcaseRuntime",
    "default_demo_root",
    "prepare_demo_showcase",
    "serve_demo_showcase",
]
