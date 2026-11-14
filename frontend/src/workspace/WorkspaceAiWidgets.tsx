import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { ApiRequestError, api, post, put } from "../api/client";
import { pulseCelebration } from "./motion";
import { OpenResearchSource } from "./ResearchTypes";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";

export type VideoAiBrief = {
  video_id: string;
  source_basis?: "TRANSCRIPT" | "METADATA_ONLY";
  headline_zh: string;
  summary_zh: string;
  score: number;
  score_reason_zh: string;
  recommendation_tier: "MUST_WATCH" | "WORTH_SKIMMING" | "SKIP_NOISE";
  content_bucket: "DEEP_DIVE" | "TUTORIAL" | "SHORTS_PROMO";
  is_short_noise: boolean;
  starred?: boolean;
  is_read?: boolean;
  topics_zh: string[];
  topic_cluster_zh: string;
  product_opportunities_zh: string[];
  business_opportunities_zh: string[];
  obsidian_markdown?: string;
};

export type WeeklyAiBrief = {
  brief_id: string;
  week_label: string;
  title_zh: string;
  executive_summary_zh: string;
  core_trends_zh: string[];
  product_opportunities_zh: string[];
  business_opportunities_zh: string[];
  must_watch_picks: {
    video_id: string;
    title: string;
    channel_name: string;
    score: number;
    reason_zh: string;
  }[];
  funnel_stats: {
    total_videos: number;
    distilled_count?: number;
    must_watch_count: number;
    shorts_filtered_count: number;
    local_courses_count?: number;
  };
  obsidian_markdown: string;
  provider: string;
  model: string;
  created_at: string;
};

export type AiResearchCitation = {
  ref_label: string;
  video_id: string;
  video_title: string;
  channel_name: string;
  evidence_id: string;
  start_ms: number | null;
  end_ms: number | null;
  timestamp_label: string;
  excerpt: string;
};

export type AiResearchSession = {
  session_id: string;
  question: string;
  scope_label_zh: string;
  answer_zh: string;
  key_takeaways_zh: string[];
  action_items_zh: string[];
  citations: AiResearchCitation[];
  obsidian_markdown: string;
  provider: string;
  model: string;
  created_at: string;
};

export type ResearchScopeOptions = {
  channels: { key: string; label: string; count: number }[];
  topic_clusters: { name: string; count: number }[];
  videos: {
    video_id: string;
    title: string;
    channel_name: string;
    score: number | null;
    topic_cluster_zh?: string;
  }[];
};

export type TopicAiEvolutionEntry = {
  video_id: string;
  title: string;
  channel_name: string;
  published_at: string;
  score: number;
  recommendation_tier: "MUST_WATCH" | "WORTH_SKIMMING" | "SKIP_NOISE";
  source_basis: "TRANSCRIPT" | "METADATA_ONLY";
  headline_zh: string;
  summary_zh: string;
  product_opportunities_zh: string[];
  business_opportunities_zh: string[];
};

export type TopicAiEvolution = {
  video_count: number;
  must_watch_count: number;
  recent_7d_count: number;
  avg_score: number | null;
  latest_headline_zh: string;
  source_channels: string[];
  obsidian_markdown: string;
  entries: TopicAiEvolutionEntry[];
};

let pendingResearchTopicCluster = "";

export function setPendingResearchTopicCluster(topicName: string): void {
  pendingResearchTopicCluster = topicName.trim();
}

export function consumePendingResearchTopicCluster(): string {
  const next = pendingResearchTopicCluster;
  pendingResearchTopicCluster = "";
  return next;
}

export type WorkspaceAiSettings = {
  active_mode: "local_ollama" | "cloud_byok";
  ollama_base_url: string;
  ollama_model: string;
  ollama_reachable: boolean;
  installed_ollama_models: string[];
  cloud_provider: string;
  cloud_base_url: string;
  cloud_model: string;
  cloud_key_configured: boolean;
};

const isRec = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

const strArr = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x.trim().length > 0) : [];

export function readVideoAiBrief(raw: unknown): VideoAiBrief | null {
  if (!isRec(raw) || typeof raw.headline_zh !== "string" || typeof raw.score !== "number") {
    return null;
  }
  const tier = raw.recommendation_tier;
  const bucket = raw.content_bucket;
  return {
    video_id: typeof raw.video_id === "string" ? raw.video_id : "",
    source_basis: raw.source_basis === "METADATA_ONLY" ? "METADATA_ONLY" : "TRANSCRIPT",
    headline_zh: raw.headline_zh,
    summary_zh: typeof raw.summary_zh === "string" ? raw.summary_zh : "",
    score: raw.score,
    score_reason_zh: typeof raw.score_reason_zh === "string" ? raw.score_reason_zh : "",
    recommendation_tier:
      tier === "MUST_WATCH" || tier === "WORTH_SKIMMING" || tier === "SKIP_NOISE"
        ? tier
        : raw.score >= 8
          ? "MUST_WATCH"
          : raw.score >= 5
            ? "WORTH_SKIMMING"
            : "SKIP_NOISE",
    content_bucket:
      bucket === "DEEP_DIVE" || bucket === "TUTORIAL" || bucket === "SHORTS_PROMO"
        ? bucket
        : "DEEP_DIVE",
    is_short_noise: Boolean(raw.is_short_noise),
    starred: Boolean(raw.starred),
    is_read: Boolean(raw.is_read),
    topics_zh: strArr(raw.topics_zh),
    topic_cluster_zh: typeof raw.topic_cluster_zh === "string" ? raw.topic_cluster_zh : "",
    product_opportunities_zh: strArr(raw.product_opportunities_zh),
    business_opportunities_zh: strArr(raw.business_opportunities_zh),
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : undefined,
  };
}

export function readWeeklyAiBrief(raw: unknown): WeeklyAiBrief | null {
  if (!isRec(raw) || typeof raw.brief_id !== "string" || typeof raw.title_zh !== "string") {
    return null;
  }
  const stats = isRec(raw.funnel_stats) ? raw.funnel_stats : {};
  const picks = Array.isArray(raw.must_watch_picks)
    ? raw.must_watch_picks
        .filter(isRec)
        .map((p) => ({
          video_id: String(p.video_id ?? ""),
          title: String(p.title ?? p.video_id ?? ""),
          channel_name: String(p.channel_name ?? ""),
          score: typeof p.score === "number" ? p.score : 8.5,
          reason_zh: String(p.reason_zh ?? ""),
        }))
        .filter((p) => p.video_id.length > 0)
    : [];
  return {
    brief_id: raw.brief_id,
    week_label: typeof raw.week_label === "string" ? raw.week_label : "",
    title_zh: raw.title_zh,
    executive_summary_zh:
      typeof raw.executive_summary_zh === "string" ? raw.executive_summary_zh : "",
    core_trends_zh: strArr(raw.core_trends_zh),
    product_opportunities_zh: strArr(raw.product_opportunities_zh),
    business_opportunities_zh: strArr(raw.business_opportunities_zh),
    must_watch_picks: picks,
    funnel_stats: {
      total_videos: typeof stats.total_videos === "number" ? stats.total_videos : 0,
      distilled_count: typeof stats.distilled_count === "number" ? stats.distilled_count : undefined,
      must_watch_count: typeof stats.must_watch_count === "number" ? stats.must_watch_count : 0,
      shorts_filtered_count:
        typeof stats.shorts_filtered_count === "number" ? stats.shorts_filtered_count : 0,
      local_courses_count:
        typeof stats.local_courses_count === "number" ? stats.local_courses_count : undefined,
    },
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    provider: typeof raw.provider === "string" ? raw.provider : "ollama",
    model: typeof raw.model === "string" ? raw.model : "qwen3.5:9b",
    created_at: typeof raw.created_at === "string" ? raw.created_at : "",
  };
}

function readAiResearchSession(raw: unknown): AiResearchSession | null {
  if (!isRec(raw) || typeof raw.session_id !== "string" || typeof raw.answer_zh !== "string") {
    return null;
  }
  const citations: AiResearchCitation[] = Array.isArray(raw.citations)
    ? raw.citations
        .filter(isRec)
        .map((c) => ({
          ref_label: String(c.ref_label ?? ""),
          video_id: String(c.video_id ?? ""),
          video_title: String(c.video_title ?? c.video_id ?? ""),
          channel_name: String(c.channel_name ?? ""),
          evidence_id: String(c.evidence_id ?? ""),
          start_ms: typeof c.start_ms === "number" ? c.start_ms : null,
          end_ms: typeof c.end_ms === "number" ? c.end_ms : null,
          timestamp_label: String(c.timestamp_label ?? "00:00"),
          excerpt: String(c.excerpt ?? ""),
        }))
        .filter((c) => c.video_id.length > 0 && c.evidence_id.length > 0)
    : [];
  return {
    session_id: raw.session_id,
    question: typeof raw.question === "string" ? raw.question : "",
    scope_label_zh: typeof raw.scope_label_zh === "string" ? raw.scope_label_zh : "",
    answer_zh: raw.answer_zh,
    key_takeaways_zh: strArr(raw.key_takeaways_zh),
    action_items_zh: strArr(raw.action_items_zh),
    citations,
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    provider: typeof raw.provider === "string" ? raw.provider : "ollama",
    model: typeof raw.model === "string" ? raw.model : "qwen3.5:9b",
    created_at: typeof raw.created_at === "string" ? raw.created_at : "",
  };
}

function readResearchScopeOptions(raw: unknown): ResearchScopeOptions | null {
  if (!isRec(raw)) return null;
  const channels = Array.isArray(raw.channels)
    ? raw.channels
        .filter(isRec)
        .map((ch) => ({
          key: typeof ch.key === "string" ? ch.key.trim() : "",
          label: typeof ch.label === "string" ? ch.label.trim() : "",
          count: typeof ch.count === "number" ? ch.count : 0,
        }))
        .filter((ch) => ch.key.length > 0 && ch.label.length > 0)
    : [];
  const topic_clusters = Array.isArray(raw.topic_clusters)
    ? raw.topic_clusters
        .filter(isRec)
        .map((tc) => ({
          name: typeof tc.name === "string" ? tc.name.trim() : "",
          count: typeof tc.count === "number" ? tc.count : 0,
        }))
        .filter((tc) => tc.name.length > 0)
    : [];
  const videos = Array.isArray(raw.videos)
    ? raw.videos
        .filter(isRec)
        .map((v) => ({
          video_id: typeof v.video_id === "string" ? v.video_id.trim() : "",
          title: typeof v.title === "string" && v.title.trim() ? v.title.trim() : String(v.video_id ?? ""),
          channel_name: typeof v.channel_name === "string" ? v.channel_name.trim() : "",
          score: typeof v.score === "number" ? v.score : null,
          topic_cluster_zh: typeof v.topic_cluster_zh === "string" ? v.topic_cluster_zh : undefined,
        }))
        .filter((v) => v.video_id.length > 0)
    : [];
  return { channels, topic_clusters, videos };
}

export function readTopicAiEvolution(raw: unknown): TopicAiEvolution | null {
  if (!isRec(raw) || typeof raw.video_count !== "number") return null;
  const entries: TopicAiEvolutionEntry[] = Array.isArray(raw.entries)
    ? raw.entries
        .filter(isRec)
        .map((e): TopicAiEvolutionEntry => {
          const score = typeof e.score === "number" ? e.score : 8.0;
          const tier = e.recommendation_tier;
          return {
            video_id: typeof e.video_id === "string" ? e.video_id : "",
            title: typeof e.title === "string" && e.title.trim() ? e.title : String(e.video_id ?? ""),
            channel_name: typeof e.channel_name === "string" ? e.channel_name : "",
            published_at: typeof e.published_at === "string" ? e.published_at : "",
            score,
            recommendation_tier:
              tier === "MUST_WATCH" || tier === "WORTH_SKIMMING" || tier === "SKIP_NOISE"
                ? tier
                : score >= 8
                  ? "MUST_WATCH"
                  : score >= 5
                    ? "WORTH_SKIMMING"
                    : "SKIP_NOISE",
            source_basis: e.source_basis === "METADATA_ONLY" ? "METADATA_ONLY" : "TRANSCRIPT",
            headline_zh: typeof e.headline_zh === "string" ? e.headline_zh : "",
            summary_zh: typeof e.summary_zh === "string" ? e.summary_zh : "",
            product_opportunities_zh: strArr(e.product_opportunities_zh),
            business_opportunities_zh: strArr(e.business_opportunities_zh),
          };
        })
        .filter((e) => e.video_id.length > 0)
    : [];
  return {
    video_count: raw.video_count,
    must_watch_count: typeof raw.must_watch_count === "number" ? raw.must_watch_count : 0,
    recent_7d_count: typeof raw.recent_7d_count === "number" ? raw.recent_7d_count : 0,
    avg_score: typeof raw.avg_score === "number" ? raw.avg_score : null,
    latest_headline_zh: typeof raw.latest_headline_zh === "string" ? raw.latest_headline_zh : "",
    source_channels: strArr(raw.source_channels),
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    entries,
  };
}

export function readWorkspaceAiSettings(raw: unknown): WorkspaceAiSettings | null {
  if (!isRec(raw) || (raw.active_mode !== "local_ollama" && raw.active_mode !== "cloud_byok")) {
    return null;
  }
  return {
    active_mode: raw.active_mode,
    ollama_base_url:
      typeof raw.ollama_base_url === "string" ? raw.ollama_base_url : "http://127.0.0.1:11434",
    ollama_model: typeof raw.ollama_model === "string" ? raw.ollama_model : "qwen3.5:9b",
    ollama_reachable: Boolean(raw.ollama_reachable),
    installed_ollama_models: strArr(raw.installed_ollama_models),
    cloud_provider: typeof raw.cloud_provider === "string" ? raw.cloud_provider : "deepseek",
    cloud_base_url:
      typeof raw.cloud_base_url === "string"
        ? raw.cloud_base_url
        : "https://api.deepseek.com/v1",
    cloud_model: typeof raw.cloud_model === "string" ? raw.cloud_model : "deepseek-chat",
    cloud_key_configured: Boolean(raw.cloud_key_configured),
  };
}

export function downloadObsidianMarkdown(filename: string, markdown: string) {
  if (!markdown || typeof URL === "undefined" || typeof URL.createObjectURL !== "function") return;
  const safeName = filename.endsWith(".md") ? filename : `${filename}.md`;
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = safeName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

function downloadJsonSnapshot(filename: string, payload: unknown) {
  if (typeof URL === "undefined" || typeof URL.createObjectURL !== "function") return;
  const safeName = filename.endsWith(".json") ? filename : `${filename}.json`;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = safeName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export function AiScoreBadge({
  brief,
  compact = false,
}: {
  brief: VideoAiBrief;
  compact?: boolean;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const tierLabel = brief.is_short_noise
    ? zh
      ? "Shorts 短片"
      : "Shorts"
    : brief.recommendation_tier === "MUST_WATCH"
      ? zh
        ? "必看"
        : "Must watch"
      : brief.recommendation_tier === "WORTH_SKIMMING"
        ? zh
          ? "速览"
          : "Skim"
        : zh
          ? "可跳过"
          : "Skip";
  const toneClass = brief.is_short_noise
    ? "ai-score-noise"
    : brief.recommendation_tier === "MUST_WATCH"
      ? "ai-score-high"
      : brief.recommendation_tier === "WORTH_SKIMMING"
        ? "ai-score-mid"
        : "ai-score-noise";
  return (
    <span className={`ai-score-pill tabular-nums ${toneClass}${compact ? " is-compact" : ""}`}>
      <strong>{brief.score.toFixed(1)}</strong>
      <span>· {tierLabel}</span>
    </span>
  );
}

export function WeeklyAiBriefPanel({
  initialBrief,
  onOpenContent,
  onOpenResearch,
}: {
  initialBrief: WeeklyAiBrief | null;
  onOpenContent: (videoId: string) => void;
  onOpenResearch: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [brief, setBrief] = useState<WeeklyAiBrief | null>(initialBrief);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialBrief) setBrief(initialBrief);
  }, [initialBrief]);

  if (!brief) return null;

  const regenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await post<{ weekly_brief?: unknown }>("/workspace-ai/weekly-brief/generate", {});
      const parsed = readWeeklyAiBrief(res.weekly_brief);
      if (parsed) setBrief(parsed);
    } catch {
      setError(zh ? "未能刷新本周情报周报，请检查本机或云端 AI 引擎状态。" : "Could not refresh the weekly AI brief.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel weekly-ai-brief-panel" aria-label={brief.title_zh}>
      <div className="panel-head weekly-ai-brief-head">
        <h2>
          <PhosphorIcon name="sparkle" weight="fill" size={16} className="panel-title-icon" />
          <span>{brief.title_zh}</span>
        </h2>
        <div className="button-row">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onOpenResearch}
          >
            <PhosphorIcon name="magnifying-glass" size={13} />
            {zh ? "跨视频深度问答" : "Cross-video AI Q&A"}
          </button>
          <button
            type="button"
            className="button button-secondary button-small"
            disabled={busy}
            onClick={() => void regenerate()}
          >
            <PhosphorIcon name="lightning" size={13} />
            {busy ? (zh ? "正在生成…" : "Generating…") : zh ? "重新生成周报" : "Regenerate brief"}
          </button>
        </div>
      </div>

      <div className="weekly-funnel-strip tabular-nums">
        <span>
          {zh
            ? `收录 ${brief.funnel_stats.total_videos} 条内容 · 自动折叠 ${brief.funnel_stats.shorts_filtered_count} 条 Shorts 宣传短片 · 精选 ${brief.funnel_stats.must_watch_count} 条必看干货`
            : `${brief.funnel_stats.total_videos} items · ${brief.funnel_stats.shorts_filtered_count} Shorts auto-folded · ${brief.funnel_stats.must_watch_count} must-watch picks`}
        </span>
        {brief.week_label ? <span>{brief.week_label}</span> : null}
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <p className="weekly-exec-summary">{brief.executive_summary_zh}</p>

      <div className="weekly-insight-columns">
        {brief.core_trends_zh.length > 0 ? (
          <div className="weekly-insight-col">
            <h3>{zh ? "核心趋势判断" : "Core trends"}</h3>
            <ul>
              {brief.core_trends_zh.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {brief.product_opportunities_zh.length > 0 ? (
          <div className="weekly-insight-col">
            <h3>{zh ? "AI 产品化启发" : "Product ideas"}</h3>
            <ul>
              {brief.product_opportunities_zh.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {brief.business_opportunities_zh.length > 0 ? (
          <div className="weekly-insight-col">
            <h3>{zh ? "商业变现切口" : "Monetization angles"}</h3>
            <ul>
              {brief.business_opportunities_zh.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {brief.must_watch_picks.length > 0 ? (
        <div className="weekly-picks-block">
          <h3>{zh ? "本周必看精选" : "Must-watch picks"}</h3>
          <div className="weekly-picks-list">
            {brief.must_watch_picks.map((pick) => (
              <button
                key={pick.video_id}
                type="button"
                className="weekly-pick-row"
                onClick={() => onOpenContent(pick.video_id)}
              >
                <div className="weekly-pick-main">
                  <strong>{pick.title}</strong>
                  <p>{pick.reason_zh}</p>
                </div>
                <span className="ai-score-pill ai-score-high tabular-nums">
                  <strong>{pick.score.toFixed(1)}</strong>
                  <span>· {pick.channel_name || (zh ? "来源" : "Source")}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {brief.obsidian_markdown ? (
        <div className="obsidian-export-bar">
          <div className="button-row">
            <button
              type="button"
              className="button button-secondary button-small"
              onClick={(event) => {
                pulseCelebration(event.currentTarget);
                void navigator.clipboard?.writeText(brief.obsidian_markdown);
                setCopied(true);
                setTimeout(() => setCopied(false), 2200);
              }}
            >
              <PhosphorIcon name="file-text" size={13} />
              {copied
                ? zh
                  ? "已复制双链周报"
                  : "Copied wikilinks brief"
                : zh
                  ? "复制双链周报"
                  : "Copy Obsidian brief"}
            </button>
            <button
              type="button"
              className="button button-ghost button-small"
              onClick={() =>
                downloadObsidianMarkdown(
                  `AI情报周报-${brief.week_label || brief.brief_id}.md`,
                  brief.obsidian_markdown,
                )
              }
            >
              {zh ? "下载 .md 周报" : "Download .md"}
            </button>
          </div>
          <details className="obsidian-preview-drawer">
            <summary>{zh ? "预览 Obsidian 双链 Markdown" : "Preview Obsidian Markdown"}</summary>
            <pre className="obsidian-preview-pre">{brief.obsidian_markdown}</pre>
          </details>
        </div>
      ) : null}
    </section>
  );
}

export function WorkspaceVideoAiActions({
  videoId,
  title,
  provider,
  isLocalMedia,
  transcriptAvailable,
  aiBrief,
  obsidianMarkdown,
  onCompleted,
}: {
  videoId: string;
  title: string;
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  isLocalMedia: boolean;
  transcriptAvailable: boolean;
  aiBrief: VideoAiBrief | null;
  obsidianMarkdown?: string;
  onCompleted: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [busyKind, setBusyKind] = useState<"distill" | "transcribe" | "curation" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedObsidian, setCopiedObsidian] = useState(false);

  const mdContent = obsidianMarkdown ?? aiBrief?.obsidian_markdown ?? "";
  const canMetadataPreview =
    !isLocalMedia && !transcriptAvailable && (provider ?? "YOUTUBE") === "YOUTUBE";

  const toggleCuration = async (patchBody: { starred?: boolean; is_read?: boolean }) => {
    if (busyKind !== null) return;
    setBusyKind("curation");
    setError(null);
    try {
      await post(`/workspace-ai/videos/${encodeURIComponent(videoId)}/curation`, patchBody);
      onCompleted();
    } catch {
      setError(zh ? "未能更新阅读与收藏状态，请稍后重试。" : "Could not update reading state.");
    } finally {
      setBusyKind(null);
    }
  };

  const runAction = async (kind: "distill" | "transcribe") => {
    setBusyKind(kind);
    setError(null);
    try {
      await post(`/workspace-ai/videos/${encodeURIComponent(videoId)}/${kind}`, {});
      onCompleted();
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : undefined;
      if (code === "CLOUD_CREDENTIAL_MISSING") {
        setError(zh ? "当前选为云端模式但尚未填写 API Key，请在设置中保存 Key 或切回本机免费 Ollama。" : "Cloud API key is missing in Settings.");
      } else {
        setError(
          kind === "transcribe"
            ? zh
              ? "本地离线语音转写未能完成，请检查本地转写模型与音视频文件。"
              : "Offline local transcription could not complete."
            : zh
              ? "AI 中文提炼未能完成，请检查本机 Ollama 或云端引擎配置。"
              : "AI distillation could not complete.",
        );
      }
    } finally {
      setBusyKind(null);
    }
  };

  return (
    <>
      {isLocalMedia && !transcriptAvailable ? (
        <button
          type="button"
          className="button button-primary button-small"
          disabled={busyKind !== null}
          onClick={(event) => {
            pulseCelebration(event.currentTarget);
            void runAction("transcribe");
          }}
        >
          <PhosphorIcon name="sparkle" size={13} />
          {busyKind === "transcribe"
            ? zh
              ? "正在离线转写并提炼中文洞察…"
              : "Transcribing & distilling…"
            : zh
              ? "离线语音转写并提炼中文洞察"
              : "Transcribe offline & distill Chinese insight"}
        </button>
      ) : null}
      {transcriptAvailable ? (
        <button
          type="button"
          className="button button-primary button-small"
          disabled={busyKind !== null}
          onClick={(event) => {
            pulseCelebration(event.currentTarget);
            void runAction("distill");
          }}
        >
          <PhosphorIcon name="sparkle" size={13} />
          {busyKind === "distill"
            ? zh
              ? "正在提炼中文结论…"
              : "Distilling Chinese summary…"
            : aiBrief
              ? zh
                ? "AI 重新提炼中文总结"
                : "Re-distill AI Chinese brief"
              : zh
                ? "AI 提炼中文总结与洞察"
                : "Distill AI Chinese brief"}
        </button>
      ) : canMetadataPreview ? (
        <button
          type="button"
          className="button button-secondary button-small"
          disabled={busyKind !== null}
          onClick={(event) => {
            pulseCelebration(event.currentTarget);
            void runAction("distill");
          }}
        >
          <PhosphorIcon name="sparkle" size={13} />
          {busyKind === "distill"
            ? zh
              ? "正在生成简介速览…"
              : "Summarizing metadata…"
            : aiBrief
              ? zh
                ? "重新生成简介中文速览"
                : "Refresh metadata preview"
              : zh
                ? "AI 生成简介中文速览"
                : "AI metadata preview"}
        </button>
      ) : null}
      {mdContent ? (
        <>
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void navigator.clipboard?.writeText(mdContent);
              setCopiedObsidian(true);
              setTimeout(() => setCopiedObsidian(false), 2200);
            }}
          >
            <PhosphorIcon name="stack" size={13} />
            {copiedObsidian
              ? zh
                ? "已复制双链笔记"
                : "Copied Obsidian note"
              : zh
                ? "复制双链笔记"
                : "Copy Obsidian wikilinks"}
          </button>
          <button
            type="button"
            className="button button-ghost button-small"
            onClick={() => downloadObsidianMarkdown(title || videoId, mdContent)}
          >
            {zh ? "下载 .md" : "Download .md"}
          </button>
        </>
      ) : null}
      {aiBrief ? (
        <>
          <button
            type="button"
            className={`button button-small ${aiBrief.starred ? "button-saved" : "button-secondary"}`}
            disabled={busyKind !== null}
            aria-pressed={Boolean(aiBrief.starred)}
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void toggleCuration({ starred: !aiBrief.starred });
            }}
          >
            <PhosphorIcon
              name="bookmark-simple"
              weight={aiBrief.starred ? "fill" : "regular"}
              size={13}
            />
            {aiBrief.starred
              ? zh
                ? "已收藏"
                : "Starred"
              : zh
                ? "收藏待看"
                : "Star"}
          </button>
          <button
            type="button"
            className="button button-ghost button-small"
            disabled={busyKind !== null}
            aria-pressed={Boolean(aiBrief.is_read)}
            onClick={() => void toggleCuration({ is_read: !aiBrief.is_read })}
          >
            <PhosphorIcon
              name="check-circle"
              weight={aiBrief.is_read ? "fill" : "regular"}
              size={13}
            />
            {aiBrief.is_read
              ? zh
                ? "已读 · 标未读"
                : "Read · Mark unread"
              : zh
                ? "标记已读"
                : "Mark read"}
          </button>
        </>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

export function WorkspaceVideoAiBriefCard({
  brief,
  obsidianMarkdown,
}: {
  brief: VideoAiBrief | null;
  obsidianMarkdown?: string;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  if (!brief) return null;
  const md = obsidianMarkdown ?? brief.obsidian_markdown ?? "";

  return (
    <div className="video-ai-brief-card">
      <div className="video-ai-brief-top">
        <AiScoreBadge brief={brief} />
        {brief.source_basis === "METADATA_ONLY" ? (
          <span className="ai-basis-pill">
            {zh
              ? "基于标题与官方简介速览（原视频暂无字幕）"
              : "Metadata-only preview (no captions on source)"}
          </span>
        ) : null}
        {brief.topic_cluster_zh ? (
          <span className="ai-topic-tag">[[{brief.topic_cluster_zh}]]</span>
        ) : null}
        {brief.score_reason_zh ? <span className="hint">{brief.score_reason_zh}</span> : null}
      </div>
      <p className="video-ai-headline">{brief.headline_zh}</p>
      {brief.summary_zh && brief.summary_zh.trim() !== brief.headline_zh.trim() ? (
        <p className="summary-copy video-ai-summary-body">{brief.summary_zh}</p>
      ) : null}
      {brief.product_opportunities_zh.length > 0 || brief.business_opportunities_zh.length > 0 ? (
        <div className="weekly-insight-columns video-ai-opp-grid">
          {brief.product_opportunities_zh.length > 0 ? (
            <div className="weekly-insight-col">
              <h3>{zh ? "AI 产品化启发" : "AI product takeaways"}</h3>
              <ul>
                {brief.product_opportunities_zh.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {brief.business_opportunities_zh.length > 0 ? (
            <div className="weekly-insight-col">
              <h3>{zh ? "商业变现与切入机会" : "Monetization opportunities"}</h3>
              <ul>
                {brief.business_opportunities_zh.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      {md ? (
        <details className="obsidian-preview-drawer">
          <summary>{zh ? "预览 Obsidian 双链笔记 ([[wikilinks]])" : "Preview Obsidian [[wikilinks]] note"}</summary>
          <pre className="obsidian-preview-pre">{md}</pre>
        </details>
      ) : null}
    </div>
  );
}

export function TopicObsidianExportBar({
  topicName,
  obsidianMarkdown,
}: {
  topicName: string;
  obsidianMarkdown: string;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [copied, setCopied] = useState(false);
  if (!obsidianMarkdown.trim()) return null;

  return (
    <div className="topic-moc-export-box">
      <div className="button-row">
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={(event) => {
            pulseCelebration(event.currentTarget);
            void navigator.clipboard?.writeText(obsidianMarkdown);
            setCopied(true);
            setTimeout(() => setCopied(false), 2200);
          }}
        >
          <PhosphorIcon name="file-text" size={13} />
          {copied
            ? zh
              ? "已复制专题双链笔记"
              : "Copied Topic MOC"
            : zh
              ? "复制专题双链笔记"
              : "Copy Topic [[wikilinks]]"}
        </button>
        <button
          type="button"
          className="button button-ghost button-small"
          onClick={() => downloadObsidianMarkdown(`专题MOC-${topicName}.md`, obsidianMarkdown)}
        >
          {zh ? "下载专题 .md" : "Download Topic .md"}
        </button>
      </div>
      <details className="obsidian-preview-drawer">
        <summary>
          {zh
            ? "预览专题 MOC 双链笔记 ([[wikilinks]])"
            : "Preview Topic MOC [[wikilinks]] Markdown"}
        </summary>
        <pre className="obsidian-preview-pre">{obsidianMarkdown}</pre>
      </details>
    </div>
  );
}

const FALLBACK_QUESTIONS_ZH = [
  "OpenAI、Greg Isenberg 与本地实战课对 AI Agent 产品落地有什么共识与分歧？",
  "从现有内容库中，适合一人公司切入的高毛利 AI SaaS 方向有哪些？",
  "多模态与智能助理课程里有哪些可以直接复用的产品交互模式？",
];

export function WorkspaceAiResearchPanel({
  onOpen,
  onAiReady,
}: {
  onOpen: OpenResearchSource;
  onAiReady?: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [sessions, setSessions] = useState<AiResearchSession[]>([]);
  const [suggested, setSuggested] = useState<string[]>(FALLBACK_QUESTIONS_ZH);
  const [scopeOptions, setScopeOptions] = useState<ResearchScopeOptions | null>(null);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [selectedTopic, setSelectedTopic] = useState(() => consumePendingResearchTopicCluster());
  const [comparePickerOpen, setComparePickerOpen] = useState(false);
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [activeSession, setActiveSession] = useState<AiResearchSession | null>(null);
  const [questionInput, setQuestionInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    api<{ sessions?: unknown; suggested_questions?: unknown; scope_options?: unknown }>(
      "/workspace-ai/research/sessions",
    )
      .then((res) => {
        if (!alive || !isRec(res)) return;
        if (Array.isArray(res.sessions)) {
          onAiReady?.();
        }
        const parsedSessions = Array.isArray(res.sessions)
          ? res.sessions
              .map(readAiResearchSession)
              .filter((s): s is AiResearchSession => s !== null)
          : [];
        const parsedQuestions = strArr(res.suggested_questions);
        const parsedScopes = readResearchScopeOptions(res.scope_options);
        setSessions(parsedSessions);
        if (parsedSessions.length > 0) setActiveSession(parsedSessions[0]);
        if (parsedQuestions.length > 0) setSuggested(parsedQuestions);
        if (parsedScopes) setScopeOptions(parsedScopes);
      })
      .catch(() => {
        /* Silently keep fallback suggestions when backend is unenriched */
      });
    return () => {
      alive = false;
    };
  }, []);

  const hasActiveScope = Boolean(selectedChannel || selectedTopic || selectedVideoIds.length > 0);

  const toggleComparedVideo = (videoId: string) => {
    setSelectedVideoIds((prev) =>
      prev.includes(videoId)
        ? prev.filter((id) => id !== videoId)
        : prev.length >= 12
          ? prev
          : [...prev, videoId],
    );
  };

  const ask = async (qText: string) => {
    const clean = qText.trim();
    if (!clean || busy) return;
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { question: clean };
      if (selectedVideoIds.length > 0) {
        payload.video_ids = selectedVideoIds;
      } else {
        if (selectedChannel) payload.channel_key = selectedChannel;
        if (selectedTopic) payload.topic_cluster = selectedTopic;
      }
      const res = await post<{ session?: unknown }>("/workspace-ai/research/ask", payload);
      const session = readAiResearchSession(res.session);
      if (!session) throw new Error("INVALID_SESSION");
      setActiveSession(session);
      setSessions((prev) => [session, ...prev.filter((item) => item.session_id !== session.session_id)]);
      setQuestionInput("");
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : undefined;
      setError(
        code === "INSUFFICIENT_MATERIAL"
          ? hasActiveScope
            ? zh
              ? "当前筛选范围内暂无带时间轴字幕的内容，请放宽来源或专题范围后重试。"
              : "No timed transcript content matched the selected scope."
            : zh
              ? "当前资料库尚无带时间轴字幕的内容可供跨视频问答。"
              : "No timed transcript content is available in your library yet."
          : zh
            ? "跨视频 AI 问答未能完成，请检查本机 Ollama 或云端引擎配置。"
            : "Cross-video AI Q&A could not complete.",
      );
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void ask(questionInput);
  };

  const availableTopics = scopeOptions?.topic_clusters ?? [];
  const topicNames = new Set(availableTopics.map((t) => t.name));
  const candidateVideos = (scopeOptions?.videos ?? []).filter((v) => {
    if (selectedChannel && v.channel_name !== selectedChannel && !(selectedChannel === "LOCAL" && v.channel_name === "本地实战课")) {
      return false;
    }
    if (selectedTopic && v.topic_cluster_zh && v.topic_cluster_zh !== selectedTopic) {
      return false;
    }
    return true;
  });

  const showScopeBar = Boolean(
    selectedTopic ||
      (scopeOptions &&
        (scopeOptions.channels.length > 0 ||
          scopeOptions.topic_clusters.length > 0 ||
          scopeOptions.videos.length > 0)),
  );

  return (
    <section
      className="panel ai-research-qa-panel"
      aria-label={zh ? "AI 跨视频深度问答" : "Cross-Video Grounded AI Q&A"}
    >
      <div className="panel-head">
        <h2>
          <PhosphorIcon name="sparkle" weight="fill" size={16} className="panel-title-icon" />
          <span>{zh ? "AI 跨视频深度问答" : "Cross-Video Grounded AI Q&A"}</span>
        </h2>
      </div>
      <p className="hint">
        {zh
          ? "支持全库综合提问，也可限定特定频道、专题或勾选多条视频做头对头观点对比，所有结论均附可点击验证的时间轴原话。"
          : "Synthesize grounded answers across your full library, or scope to a specific source, topic, or multi-video comparison."}
      </p>

      {showScopeBar ? (
        <div className="ai-scope-filter-bar">
          {(scopeOptions?.channels.length ?? 0) > 0 ? (
            <div className="ai-suggested-pills" role="group" aria-label={zh ? "限定来源" : "Filter by source"}>
              <button
                type="button"
                className={`ai-question-chip${!selectedChannel && selectedVideoIds.length === 0 ? " is-active" : ""}`}
                disabled={busy}
                onClick={() => {
                  setSelectedChannel("");
                  setSelectedVideoIds([]);
                }}
              >
                {zh ? "全部来源" : "All sources"}
              </button>
              {scopeOptions?.channels.map((ch) => (
                <button
                  key={ch.key}
                  type="button"
                  className={`ai-question-chip tabular-nums${selectedChannel === ch.key && selectedVideoIds.length === 0 ? " is-active" : ""}`}
                  disabled={busy}
                  onClick={() => {
                    setSelectedVideoIds([]);
                    setSelectedChannel((prev) => (prev === ch.key ? "" : ch.key));
                  }}
                >
                  {`${ch.label} (${ch.count})`}
                </button>
              ))}
            </div>
          ) : null}

          <div className="ai-scope-secondary-row">
            {availableTopics.length > 0 || selectedTopic ? (
              <label className="ai-scope-inline-field">
                <span>{zh ? "限定专题" : "Topic"}</span>
                <select
                  aria-label={zh ? "限定专题" : "Topic scope"}
                  value={selectedTopic}
                  disabled={busy}
                  onChange={(e) => {
                    setSelectedVideoIds([]);
                    setSelectedTopic(e.target.value);
                  }}
                >
                  <option value="">{zh ? "全部专题" : "All topics"}</option>
                  {selectedTopic && !topicNames.has(selectedTopic) ? (
                    <option value={selectedTopic}>{selectedTopic}</option>
                  ) : null}
                  {availableTopics.map((tc) => (
                    <option key={tc.name} value={tc.name}>
                      {`${tc.name} (${tc.count})`}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {(scopeOptions?.videos.length ?? 0) > 0 ? (
              <button
                type="button"
                className={`ai-question-chip tabular-nums${comparePickerOpen || selectedVideoIds.length > 0 ? " is-active" : ""}`}
                disabled={busy}
                onClick={() => setComparePickerOpen((v) => !v)}
              >
                <PhosphorIcon name="funnel" size={12} />
                {" "}
                {selectedVideoIds.length > 0
                  ? zh
                    ? `指定多视频对比 (已选 ${selectedVideoIds.length})`
                    : `Compare videos (${selectedVideoIds.length})`
                  : zh
                    ? "指定多视频对比"
                    : "Compare specific videos"}
              </button>
            ) : null}

            {hasActiveScope ? (
              <button
                type="button"
                className="button button-ghost button-small"
                disabled={busy}
                onClick={() => {
                  setSelectedChannel("");
                  setSelectedTopic("");
                  setSelectedVideoIds([]);
                  setComparePickerOpen(false);
                }}
              >
                {zh ? "重置范围" : "Reset scope"}
              </button>
            ) : null}
          </div>

          {comparePickerOpen && candidateVideos.length > 0 ? (
            <div className="ai-video-compare-picker" role="group" aria-label={zh ? "勾选对比视频" : "Select videos to compare"}>
              {candidateVideos.map((v) => {
                const checked = selectedVideoIds.includes(v.video_id);
                return (
                  <label key={v.video_id} className={`ai-video-compare-option${checked ? " is-checked" : ""}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={busy}
                      onChange={() => toggleComparedVideo(v.video_id)}
                    />
                    <span className="ai-video-compare-title">{v.title}</span>
                    <small className="tabular-nums">
                      {[v.channel_name, v.score !== null ? v.score.toFixed(1) : null].filter(Boolean).join(" · ")}
                    </small>
                  </label>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}

      <form className="ai-research-ask-form" onSubmit={handleSubmit}>
        <input
          type="text"
          aria-label={zh ? "跨视频提问" : "Ask across videos"}
          placeholder={
            zh
              ? "输入你想跨视频对比的产品、技术或商业变现问题…"
              : "Ask a product, technical, or business question across your library…"
          }
          value={questionInput}
          disabled={busy}
          onChange={(e) => setQuestionInput(e.target.value)}
        />
        <button type="submit" className="button button-primary" disabled={busy || !questionInput.trim()}>
          {busy ? (zh ? "正在检索并推演…" : "Synthesizing…") : zh ? "AI 提问" : "Ask AI"}
        </button>
      </form>

      <div className="ai-suggested-pills">
        {suggested.map((q) => (
          <button
            key={q}
            type="button"
            className="ai-question-chip"
            disabled={busy}
            onClick={() => void ask(q)}
          >
            {q}
          </button>
        ))}
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {activeSession ? (
        <div className="ai-qa-answer-box">
          <div className="ai-qa-answer-head">
            <h3>{activeSession.question}</h3>
            {activeSession.scope_label_zh ? (
              <span className="ai-basis-pill">{activeSession.scope_label_zh}</span>
            ) : null}
          </div>
          <p className="summary-copy">{activeSession.answer_zh}</p>

          {activeSession.key_takeaways_zh.length > 0 ? (
            <ul>
              {activeSession.key_takeaways_zh.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          ) : null}

          {activeSession.action_items_zh.length > 0 ? (
            <div className="ai-action-items-block">
              <h4>{zh ? "下一步可执行动作" : "Next actionable steps"}</h4>
              <ul>
                {activeSession.action_items_zh.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {activeSession.citations.length > 0 ? (
            <div className="ai-citations-section">
              <h4>{zh ? "可验证原话时间轴出处（点击直达对应视频与证据）" : "Verified timestamped citations"}</h4>
              <div className="ai-citation-list">
                {activeSession.citations.map((c) => (
                  <button
                    key={`${c.ref_label}:${c.evidence_id}`}
                    type="button"
                    className="ai-citation-card"
                    onClick={() => onOpen("content", c.video_id, c.evidence_id)}
                  >
                    <div className="ai-citation-head tabular-nums">
                      <span className="ai-citation-ref">[{c.ref_label}]</span>
                      <strong>{c.video_title}</strong>
                      <span className="ai-citation-time">{c.timestamp_label}</span>
                    </div>
                    <p>{c.excerpt}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {activeSession.obsidian_markdown ? (
            <div className="button-row">
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={(event) => {
                  pulseCelebration(event.currentTarget);
                  void navigator.clipboard?.writeText(activeSession.obsidian_markdown);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
              >
                <PhosphorIcon name="file-text" size={13} />
                {copied
                  ? zh
                    ? "已复制双链问答"
                    : "Copied"
                  : zh
                    ? "复制双链问答"
                    : "Copy Obsidian Q&A"}
              </button>
              <button
                type="button"
                className="button button-ghost button-small"
                onClick={() =>
                  downloadObsidianMarkdown(
                    `跨视频问答-${activeSession.session_id}`,
                    activeSession.obsidian_markdown,
                  )
                }
              >
                {zh ? "下载 .md" : "Download .md"}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {sessions.length > 1 ? (
        <div className="ai-session-history">
          <h4>{zh ? "历史跨视频问答" : "Recent AI Q&A sessions"}</h4>
          <div className="ai-suggested-pills">
            {sessions.map((s) => (
              <button
                key={s.session_id}
                type="button"
                className={`ai-question-chip${activeSession?.session_id === s.session_id ? " is-active" : ""}`}
                onClick={() => setActiveSession(s)}
              >
                {s.question}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

const CLOUD_PRESETS: Record<string, { label: string; baseUrl: string; model: string }> = {
  deepseek: {
    label: "DeepSeek (OpenAI 兼容)",
    baseUrl: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
  },
  moonshot: {
    label: "Moonshot / Kimi",
    baseUrl: "https://api.moonshot.cn/v1",
    model: "kimi-k2-0905-preview",
  },
  zhipu: {
    label: "智谱 BigModel",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    model: "glm-4-plus",
  },
  openai: {
    label: "OpenAI",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  },
};

export function WorkspaceAiSettingsPanel({
  id,
  initial,
}: {
  id?: string;
  initial?: unknown;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const parsedInitial = readWorkspaceAiSettings(initial);
  const [config, setConfig] = useState<WorkspaceAiSettings | null>(parsedInitial);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportingBackup, setExportingBackup] = useState(false);
  const [restoringBackup, setRestoringBackup] = useState(false);
  const restoreInputRef = useRef<HTMLInputElement | null>(null);
  const [modeDraft, setModeDraft] = useState<"local_ollama" | "cloud_byok">(
    parsedInitial?.active_mode ?? "local_ollama",
  );
  const [ollamaModelDraft, setOllamaModelDraft] = useState(
    parsedInitial?.ollama_model ?? "qwen3.5:9b",
  );
  const [cloudProviderDraft, setCloudProviderDraft] = useState(
    parsedInitial?.cloud_provider ?? "deepseek",
  );
  const [cloudBaseUrlDraft, setCloudBaseUrlDraft] = useState(
    parsedInitial?.cloud_base_url ?? "https://api.deepseek.com/v1",
  );
  const [cloudModelDraft, setCloudModelDraft] = useState(
    parsedInitial?.cloud_model ?? "deepseek-chat",
  );
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const syncDrafts = (next: WorkspaceAiSettings) => {
    setConfig(next);
    setModeDraft(next.active_mode);
    setOllamaModelDraft(next.ollama_model);
    setCloudProviderDraft(next.cloud_provider);
    setCloudBaseUrlDraft(next.cloud_base_url);
    setCloudModelDraft(next.cloud_model);
  };

  const openEditor = async () => {
    setOpen(true);
    setFeedback(null);
    setError(null);
    if (config) return;
    setLoading(true);
    try {
      const res = await api<unknown>("/workspace-ai/settings");
      const parsed = readWorkspaceAiSettings(res);
      if (parsed) syncDrafts(parsed);
    } catch {
      setError(zh ? "未能读取 AI 引擎配置。" : "Could not load AI engine settings.");
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setFeedback(null);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        active_mode: modeDraft,
        ollama_model: ollamaModelDraft.trim() || "qwen3.5:9b",
        cloud_provider: cloudProviderDraft,
        cloud_base_url: cloudBaseUrlDraft.trim(),
        cloud_model: cloudModelDraft.trim(),
      };
      if (apiKeyDraft.trim()) {
        payload.cloud_api_key = apiKeyDraft.trim();
      }
      const res = await put<unknown>("/workspace-ai/settings", payload);
      const parsed = readWorkspaceAiSettings(res);
      if (parsed) syncDrafts(parsed);
      setApiKeyDraft("");
      setFeedback(
        zh
          ? "AI 引擎配置已保存。API Key 仅加密存储于 macOS 钥匙串。"
          : "AI engine configuration saved. Any API key is stored only in macOS Keychain.",
      );
    } catch {
      setError(
        zh
          ? "AI 引擎配置未能保存，请检查本地或 HTTPS 云端地址格式。"
          : "Could not save AI engine settings.",
      );
    } finally {
      setSaving(false);
    }
  };

  const exportBackup = async () => {
    if (exportingBackup) return;
    setExportingBackup(true);
    setFeedback(null);
    setError(null);
    try {
      const snapshot = await api<unknown>("/workspace-ai/backup");
      const dateStamp = new Date().toISOString().slice(0, 10);
      downloadJsonSnapshot(`workspace-ai-backup-${dateStamp}.json`, snapshot);
      setFeedback(
        zh
          ? "已导出 AI 摘要、周报与问答快照（不含任何密钥）。"
          : "Exported AI briefs, weekly digests, and Q&A snapshot (zero secrets).",
      );
    } catch {
      setError(
        zh
          ? "未能导出 AI 知识库快照，请稍后重试。"
          : "Could not export AI knowledge snapshot.",
      );
    } finally {
      setExportingBackup(false);
    }
  };

  const handleRestoreFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || restoringBackup) return;
    setRestoringBackup(true);
    setFeedback(null);
    setError(null);
    try {
      const rawText =
        typeof file.text === "function"
          ? await file.text()
          : await new Promise<string>((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(String(reader.result ?? ""));
              reader.onerror = () => reject(reader.error ?? new Error("READ_FAILED"));
              reader.readAsText(file);
            });
      const parsed: unknown = JSON.parse(rawText);
      if (!isRec(parsed) || parsed.schema_version !== "workspace-ai-backup-v1") {
        throw new Error("INVALID_SNAPSHOT_SCHEMA");
      }
      const res = await post<{ restored?: unknown }>("/workspace-ai/restore", parsed);
      const counts = isRec(res.restored) ? res.restored : {};
      const videoCount =
        typeof counts.briefs === "number"
          ? counts.briefs
          : typeof counts.video_ai_briefs === "number"
            ? counts.video_ai_briefs
            : 0;
      const weeklyCount =
        typeof counts.weekly_briefs === "number"
          ? counts.weekly_briefs
          : typeof counts.weekly_ai_briefs === "number"
            ? counts.weekly_ai_briefs
            : 0;
      const qaCount =
        typeof counts.research_sessions === "number"
          ? counts.research_sessions
          : typeof counts.ai_research_sessions === "number"
            ? counts.ai_research_sessions
            : 0;
      const curationCount =
        typeof counts.curation_states === "number" ? counts.curation_states : 0;
      setFeedback(
        zh
          ? `已恢复 ${videoCount} 条中文摘要、${weeklyCount} 份周报与 ${qaCount} 条跨视频问答记录${curationCount > 0 ? `（含 ${curationCount} 条阅读状态）` : ""}。`
          : `Restored ${videoCount} AI briefs, ${weeklyCount} weekly digests, and ${qaCount} Q&A sessions${curationCount > 0 ? ` (${curationCount} reading states)` : ""}.`,
      );
    } catch {
      setError(
        zh
          ? "未能导入恢复快照，请选择有效的 workspace-ai-backup-v1 .json 文件。"
          : "Could not restore snapshot. Choose a valid workspace-ai-backup-v1 .json file.",
      );
    } finally {
      setRestoringBackup(false);
    }
  };

  const currentSummary =
    config?.active_mode === "cloud_byok"
      ? `${config.cloud_provider} · ${config.cloud_model}${config.cloud_key_configured ? (zh ? "（钥匙串已就绪）" : " (Keychain ready)") : zh ? "（未填 Key）" : " (No key)"}`
      : `Ollama · ${config?.ollama_model ?? "qwen3.5:9b"}（${zh ? "本机免费零成本" : "Free local"}）`;

  return (
    <section
      id={id}
      className="panel"
      aria-label={zh ? "AI 摘要、评分与跨视频问答引擎" : "AI Summary, Scoring & Q&A Engine"}
    >
      <div className="panel-head">
        <h2>
          <PhosphorIcon name="sliders-horizontal" size={16} className="panel-title-icon" />
          <span>{zh ? "AI 摘要、评分与跨视频问答引擎" : "AI Summary, Scoring & Q&A Engine"}</span>
        </h2>
      </div>
      <p>
        {zh ? "当前生效引擎：" : "Active engine: "}
        <strong>{currentSummary}</strong>
      </p>
      <p className="hint">
        {zh
          ? "默认直连本机免费 Ollama 模型完成中文总结、0–10 价值打分、周报与跨视频问答；你也可随时切换自带云端 API Key。"
          : "Runs free on local Ollama by default, with optional BYOK OpenAI-compatible cloud routing."}
      </p>

      <input
        ref={restoreInputRef}
        type="file"
        accept=".json,application/json"
        aria-label={zh ? "导入 AI 知识库快照文件" : "Import AI knowledge snapshot file"}
        hidden
        onChange={(e) => void handleRestoreFile(e)}
      />

      {!open ? (
        <>
          <div className="button-row">
            <button type="button" className="button button-secondary" onClick={() => void openEditor()}>
              {zh ? "配置 AI 摘要与问答引擎" : "Configure AI summary & Q&A engine"}
            </button>
            <button
              type="button"
              className="button button-ghost"
              disabled={exportingBackup || restoringBackup}
              onClick={() => void exportBackup()}
            >
              <PhosphorIcon name="archive" size={13} />
              {exportingBackup
                ? zh
                  ? "正在导出快照…"
                  : "Exporting…"
                : zh
                  ? "导出 AI 知识库快照 (.json)"
                  : "Export AI knowledge snapshot (.json)"}
            </button>
            <button
              type="button"
              className="button button-ghost"
              disabled={exportingBackup || restoringBackup}
              onClick={() => restoreInputRef.current?.click()}
            >
              <PhosphorIcon name="folder-open" size={13} />
              {restoringBackup
                ? zh
                  ? "正在恢复快照…"
                  : "Restoring…"
                : zh
                  ? "导入并恢复快照 (.json)"
                  : "Restore AI snapshot (.json)"}
            </button>
          </div>
          {feedback ? <p role="status">{feedback}</p> : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </>
      ) : (
        <div className="ai-settings-form">
          {loading ? (
            <p role="status">{zh ? "正在读取引擎状态…" : "Loading engine settings…"}</p>
          ) : null}
          <label className="field">
            {zh ? "运行模式" : "Execution mode"}
            <select
              aria-label={zh ? "运行模式" : "Execution mode"}
              value={modeDraft}
              disabled={saving}
              onChange={(e) => setModeDraft(e.target.value as "local_ollama" | "cloud_byok")}
            >
              <option value="local_ollama">
                {zh ? "本机免费 Ollama（零费用 · 数据不出本机）" : "Local free Ollama"}
              </option>
              <option value="cloud_byok">
                {zh ? "自带云端 API Key（BYOK · OpenAI 兼容接口）" : "Cloud BYOK (OpenAI-compatible)"}
              </option>
            </select>
          </label>

          {modeDraft === "local_ollama" ? (
            <label className="field">
              {zh ? "本机 Ollama 模型" : "Local Ollama model"}
              {config && config.installed_ollama_models.length > 0 ? (
                <select
                  aria-label={zh ? "本机 Ollama 模型" : "Local Ollama model"}
                  value={ollamaModelDraft}
                  disabled={saving}
                  onChange={(e) => setOllamaModelDraft(e.target.value)}
                >
                  {config.installed_ollama_models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  aria-label={zh ? "本机 Ollama 模型" : "Local Ollama model"}
                  value={ollamaModelDraft}
                  disabled={saving}
                  onChange={(e) => setOllamaModelDraft(e.target.value)}
                />
              )}
            </label>
          ) : (
            <>
              <label className="field">
                {zh ? "云端服务商预设" : "Cloud provider"}
                <select
                  aria-label={zh ? "云端服务商预设" : "Cloud provider"}
                  value={cloudProviderDraft}
                  disabled={saving}
                  onChange={(e) => {
                    const next = e.target.value;
                    setCloudProviderDraft(next);
                    const preset = CLOUD_PRESETS[next];
                    if (preset) {
                      setCloudBaseUrlDraft(preset.baseUrl);
                      setCloudModelDraft(preset.model);
                    }
                  }}
                >
                  {Object.entries(CLOUD_PRESETS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                {zh ? "HTTPS 接口地址 (Base URL)" : "HTTPS Base URL"}
                <input
                  type="url"
                  aria-label={zh ? "HTTPS 接口地址 (Base URL)" : "HTTPS Base URL"}
                  value={cloudBaseUrlDraft}
                  disabled={saving}
                  onChange={(e) => setCloudBaseUrlDraft(e.target.value)}
                />
              </label>
              <label className="field">
                {zh ? "云端模型名称" : "Cloud model"}
                <input
                  type="text"
                  aria-label={zh ? "云端模型名称" : "Cloud model"}
                  value={cloudModelDraft}
                  disabled={saving}
                  onChange={(e) => setCloudModelDraft(e.target.value)}
                />
              </label>
              <label className="field">
                {zh ? "云端 API Key（仅存 macOS 钥匙串）" : "Cloud API key (macOS Keychain only)"}
                <input
                  type="password"
                  autoComplete="off"
                  aria-label={
                    zh ? "云端 API Key（仅存 macOS 钥匙串）" : "Cloud API key (macOS Keychain only)"
                  }
                  placeholder={
                    config?.cloud_key_configured
                      ? zh
                        ? "钥匙串已保存凭据；留空则保持不变"
                        : "Saved in Keychain; leave blank to keep"
                      : "sk-..."
                  }
                  value={apiKeyDraft}
                  disabled={saving}
                  onChange={(e) => setApiKeyDraft(e.target.value)}
                />
              </label>
            </>
          )}

          <div className="button-row">
            <button
              type="button"
              className="button button-primary"
              disabled={saving}
              onClick={() => void save()}
            >
              {saving ? (zh ? "正在保存…" : "Saving…") : zh ? "保存 AI 引擎配置" : "Save AI engine"}
            </button>
            <button
              type="button"
              className="button button-ghost"
              disabled={saving}
              onClick={() => setOpen(false)}
            >
              {zh ? "收起" : "Close"}
            </button>
          </div>
          {feedback ? <p role="status">{feedback}</p> : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
