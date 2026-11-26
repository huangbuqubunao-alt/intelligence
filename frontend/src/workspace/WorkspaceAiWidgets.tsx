import { ChangeEvent, FormEvent, ReactNode, useEffect, useRef, useState } from "react";
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

export type WeeklyBriefHistoryItem = {
  brief_id: string;
  title_zh: string;
  created_at: string;
  must_watch_count: number;
  distilled_count?: number;
  total_videos: number;
};

export type WeeklyBriefFreshness = {
  is_archive: boolean;
  is_stale: boolean;
  new_videos_count: number;
  new_must_watch_count: number;
  new_titles: string[];
};

export type WeeklyBriefDelta = {
  previous_brief_id: string;
  previous_created_at: string;
  previous_title_zh: string;
  total_videos_delta: number;
  distilled_delta: number;
  must_watch_delta: number;
  new_picks: {
    video_id: string;
    title: string;
    channel_name: string;
    score: number;
    headline_zh: string;
  }[];
  new_shifts_zh: string[];
  new_opportunities_zh: string[];
  summary_zh: string;
};

export type ObsidianBundleScope = "must_watch" | "all" | "starred";

export type ObsidianVaultBundleResult = {
  filename: string;
  scope: ObsidianBundleScope;
  totalFiles: number;
  videoNotes: number;
  topicMocs: number;
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
  freshness?: WeeklyBriefFreshness;
  delta?: WeeklyBriefDelta;
  obsidian_markdown: string;
  provider: string;
  model: string;
  created_at: string;
  history?: WeeklyBriefHistoryItem[];
};

export type AiResearchCitation = {
  ref_label: string;
  video_id: string;
  video_title: string;
  channel_name: string;
  evidence_id: string;
  locator_type?: string;
  paragraph_index?: number | null;
  start_offset?: number | null;
  end_offset?: number | null;
  start_ms: number | null;
  end_ms: number | null;
  timestamp_label: string;
  source_url?: string | null;
  citation_url?: string | null;
  excerpt: string;
  verified?: boolean;
};

export type AiResearchCoveredSource = {
  video_id: string;
  title: string;
  provider: string;
  channel_name: string;
  locator_type: string;
};

export type AiResearchSessionScope = {
  starred_only?: boolean;
  channel_key?: string | null;
  provider_filter?: string | null;
  topic_cluster?: string | null;
  video_ids?: string[] | null;
};

export type AiResearchSession = {
  session_id: string;
  question: string;
  answer_status?: "GROUNDED" | "REFUSED_INSUFFICIENT_EVIDENCE" | "NEEDS_REVERIFICATION" | string;
  source_integrity_status?: "VERIFIED" | "NEEDS_REVERIFICATION" | "REFUSED" | string;
  fact_verification_state?: string;
  contains_heuristic_claims?: boolean;
  action_items_advisory?: boolean;
  verification_status?: string;
  verified_citation_count?: number;
  refused?: boolean;
  refusal_reason_zh?: string;
  scope_label_zh: string;
  video_count?: number;
  covered_sources?: AiResearchCoveredSource[];
  covered_source_count?: number;
  scope?: AiResearchSessionScope;
  pinned: boolean;
  answer_zh: string;
  key_takeaways_zh: string[];
  action_items_zh: string[];
  citations: AiResearchCitation[];
  related_excerpts?: AiResearchCitation[];
  obsidian_markdown: string;
  provider: string;
  model: string;
  created_at: string;
};

export type SourceAiSignal = {
  source_id: string;
  channel_key: string;
  channel_label: string;
  total_videos: number;
  distilled_count: number;
  long_form_count: number;
  shorts_count: number;
  must_watch_count: number;
  worth_skimming_count: number;
  unread_long_count: number;
  avg_long_score: number | null;
  signal_rate_pct: number | null;
};

export type ResearchScopeOptions = {
  starred_count: number;
  candidate_source_count?: number;
  channels: { key: string; label: string; count: number }[];
  topic_clusters: { name: string; count: number }[];
  videos: {
    video_id: string;
    title: string;
    channel_name: string;
    channel_key?: string;
    score: number | null;
    starred?: boolean;
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

export type TopicRelatedSummary = {
  topic_id: string;
  name: string;
  video_count: number;
  must_watch_count: number;
  avg_score: number;
  shared_sources: string[];
};

export type TopicChannelBreakdownItem = {
  channel_key: string;
  channel_label: string;
  video_count: number;
  must_watch_count: number;
  unread_count: number;
};

export type TopicSourcePerspective = {
  channel_name: string;
  video_id: string;
  title: string;
  headline_zh: string;
  angle_zh: string;
  score: number;
};

export type TopicAiEvolution = {
  video_count: number;
  must_watch_count: number;
  unread_count: number;
  recent_7d_count: number;
  avg_score: number | null;
  latest_headline_zh: string;
  latest_published_at: string;
  synthesis_zh: string;
  independence_summary_zh: string;
  top_opportunities_zh: string[];
  source_perspectives?: TopicSourcePerspective[];
  source_channels: string[];
  channel_breakdown: TopicChannelBreakdownItem[];
  related_topics: TopicRelatedSummary[];
  obsidian_markdown: string;
  entries: TopicAiEvolutionEntry[];
};

let pendingResearchTopicCluster = "";
let pendingResearchStarredOnly = false;
let pendingResearchChannel = "";
let pendingResearchSessionId = "";
let pendingContentChannel = "";
let pendingContentTopic = "";
let pendingContentBucket = "";
let pendingTopicClusterName = "";
let pendingIntelligenceTopicId = "";
let pendingResearchVideoIds: string[] = [];
let pendingResearchDraftQuestion = "";

export function setPendingResearchTopicCluster(topicName: string): void {
  pendingResearchTopicCluster = topicName.trim();
}

export function consumePendingResearchTopicCluster(): string {
  const next = pendingResearchTopicCluster;
  pendingResearchTopicCluster = "";
  return next;
}

export function setPendingResearchStarredOnly(enabled: boolean): void {
  pendingResearchStarredOnly = Boolean(enabled);
}

export function consumePendingResearchStarredOnly(): boolean {
  const next = pendingResearchStarredOnly;
  pendingResearchStarredOnly = false;
  return next;
}

export function setPendingResearchChannel(channelKey: string): void {
  pendingResearchChannel = channelKey.trim();
}

export function consumePendingResearchChannel(): string {
  const next = pendingResearchChannel;
  pendingResearchChannel = "";
  return next;
}

export function setPendingResearchSessionId(sessionId: string): void {
  pendingResearchSessionId = sessionId.trim();
}

export function consumePendingResearchSessionId(): string {
  const next = pendingResearchSessionId;
  pendingResearchSessionId = "";
  return next;
}

export function setPendingContentChannel(channelKey: string): void {
  pendingContentChannel = channelKey.trim();
}

export function consumePendingContentChannel(): string {
  const next = pendingContentChannel;
  pendingContentChannel = "";
  return next;
}

export function setPendingContentTopic(topicName: string): void {
  pendingContentTopic = topicName.trim();
}

export function consumePendingContentTopic(): string {
  const next = pendingContentTopic;
  pendingContentTopic = "";
  return next;
}

export function setPendingContentBucket(
  bucket: "" | "ALL" | "UNREAD" | "MUST_WATCH" | "STARRED" | "TUTORIAL" | "SHORTS",
): void {
  pendingContentBucket = bucket;
}

export function consumePendingContentBucket():
  | ""
  | "ALL"
  | "UNREAD"
  | "MUST_WATCH"
  | "STARRED"
  | "TUTORIAL"
  | "SHORTS" {
  const next = pendingContentBucket as
    | ""
    | "ALL"
    | "UNREAD"
    | "MUST_WATCH"
    | "STARRED"
    | "TUTORIAL"
    | "SHORTS";
  pendingContentBucket = "";
  return next;
}

export function setPendingTopicClusterName(topicName: string): void {
  pendingTopicClusterName = topicName.trim();
}

export function consumePendingTopicClusterName(): string {
  const next = pendingTopicClusterName;
  pendingTopicClusterName = "";
  return next;
}

export function setPendingIntelligenceTopicId(topicId: string): void {
  pendingIntelligenceTopicId = topicId.trim();
}

export function consumePendingIntelligenceTopicId(): string {
  const next = pendingIntelligenceTopicId;
  pendingIntelligenceTopicId = "";
  return next;
}

export function setPendingResearchVideoIds(videoIds: string[]): void {
  pendingResearchVideoIds = Array.from(
    new Set(videoIds.map((id) => id.trim()).filter(Boolean)),
  ).slice(0, 12);
}

export function consumePendingResearchVideoIds(): string[] {
  const next = pendingResearchVideoIds;
  pendingResearchVideoIds = [];
  return next;
}

export function setPendingResearchDraftQuestion(question: string): void {
  pendingResearchDraftQuestion = question.trim();
}

export function consumePendingResearchDraftQuestion(): string {
  const next = pendingResearchDraftQuestion;
  pendingResearchDraftQuestion = "";
  return next;
}

export type CuratedOllamaModel = {
  id: string;
  label: string;
  tier: string;
  size_label: string;
  ram_label_zh: string;
  ram_label_en: string;
  supports_vision: boolean;
  summary_zh: string;
  summary_en: string;
};

export type CuratedWhisperModel = {
  id: string;
  slug: string;
  label: string;
  tier: string;
  size_label: string;
  summary_zh: string;
  summary_en: string;
};

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
  local_mlx_Whisper_ready?: boolean;
  active_whisper_slug?: string | null;
  curated_ollama_models?: CuratedOllamaModel[];
  curated_whisper_models?: CuratedWhisperModel[];
};

export type WorkspaceAiTranscribeJob = {
  status: "RUNNING" | "READY" | "FAILED";
  stage: "TRANSCRIBING" | "DISTILLING" | "READY" | "FAILED";
  started_at: string;
  updated_at: string;
  error_code: string | null;
};

export type WorkspaceAiCapabilities = {
  ready: boolean;
  transcriber_ready: boolean;
  transcribe_job: WorkspaceAiTranscribeJob | null;
  visual_analysis_eligible?: boolean;
  ffmpeg_available?: boolean;
};

export type VideoVisualKeyframe = {
  frame_index: number;
  frame_id: string;
  filename: string;
  obsidian_asset_name?: string;
  timestamp_ms: number;
  timestamp_label: string;
  selection_reason: string;
  frame_kind: string;
  has_visual_info: boolean;
  title_zh: string;
  visual_detail_zh: string;
  transcript_fusion_zh: string;
  nearby_transcript: string;
  image_url: string;
  image_available: boolean;
};

export type VideoVisualAnalysis = {
  video_id: string;
  visual_summary_zh: string;
  visual_takeaways_zh: string[];
  frames: VideoVisualKeyframe[];
  frame_count: number;
  informative_frame_count: number;
  provider: string;
  model: string;
  updated_at: string;
};

const isRec = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

const strArr = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x.trim().length > 0) : [];

function parseIsoTimestampMs(value?: string | null): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function contentEffectiveTimeMs(item: {
  provider?: string | null;
  imported_at?: string | null;
  published_at?: string | null;
  last_updated?: string | null;
}): number {
  const raw =
    (item.provider ?? "YOUTUBE") === "BILIBILI"
      ? item.published_at ?? item.last_updated
      : item.imported_at ?? item.published_at ?? item.last_updated;
  return parseIsoTimestampMs(raw) || parseIsoTimestampMs(item.last_updated);
}

export function compareContentNewestFirst(
  a: {
    video_id: string;
    provider?: string | null;
    imported_at?: string | null;
    published_at?: string | null;
    last_updated?: string | null;
  },
  b: {
    video_id: string;
    provider?: string | null;
    imported_at?: string | null;
    published_at?: string | null;
    last_updated?: string | null;
  },
): number {
  const diff = contentEffectiveTimeMs(b) - contentEffectiveTimeMs(a);
  if (diff !== 0) return diff;
  const updDiff = parseIsoTimestampMs(b.last_updated) - parseIsoTimestampMs(a.last_updated);
  if (updDiff !== 0) return updDiff;
  return a.video_id.localeCompare(b.video_id);
}

export function isEffectiveVideoShortNoise(
  item: {
    provider?: string | null;
    duration_seconds?: number | null;
  },
  brief?: {
    is_short_noise?: boolean;
    content_bucket?: string;
  } | null,
): boolean {
  if (typeof item.duration_seconds === "number" && item.duration_seconds > 180) {
    return false;
  }
  if (brief) {
    return Boolean(brief.is_short_noise || brief.content_bucket === "SHORTS_PROMO");
  }
  return (item.provider ?? "YOUTUBE") === "YOUTUBE" && (item.duration_seconds ?? 9999) <= 95;
}

export function readVideoAiBrief(
  raw: unknown,
  durationSeconds?: number | null,
): VideoAiBrief | null {
  if (!isRec(raw) || typeof raw.headline_zh !== "string" || typeof raw.score !== "number") {
    return null;
  }
  const tier = raw.recommendation_tier;
  const bucket = raw.content_bucket;
  const longFormGuard = typeof durationSeconds === "number" && durationSeconds > 180;
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
        ? longFormGuard && bucket === "SHORTS_PROMO"
          ? "DEEP_DIVE"
          : bucket
        : "DEEP_DIVE",
    is_short_noise: longFormGuard ? false : Boolean(raw.is_short_noise),
    starred: Boolean(raw.starred),
    is_read: Boolean(raw.is_read),
    topics_zh: strArr(raw.topics_zh),
    topic_cluster_zh: typeof raw.topic_cluster_zh === "string" ? raw.topic_cluster_zh : "",
    product_opportunities_zh: strArr(raw.product_opportunities_zh),
    business_opportunities_zh: strArr(raw.business_opportunities_zh),
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : undefined,
  };
}

function readWeeklyHistoryList(raw: unknown): WeeklyBriefHistoryItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(isRec)
    .map((h) => ({
      brief_id: typeof h.brief_id === "string" ? h.brief_id : "",
      title_zh: typeof h.title_zh === "string" ? h.title_zh : "",
      created_at: typeof h.created_at === "string" ? h.created_at : "",
      must_watch_count: typeof h.must_watch_count === "number" ? h.must_watch_count : 0,
      distilled_count: typeof h.distilled_count === "number" ? h.distilled_count : undefined,
      total_videos: typeof h.total_videos === "number" ? h.total_videos : 0,
    }))
    .filter((h) => h.brief_id.length > 0);
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
  const history = readWeeklyHistoryList(raw.history);
  const rawFreshness = isRec(raw.freshness) ? raw.freshness : null;
  const freshness: WeeklyBriefFreshness | undefined = rawFreshness
    ? {
        is_archive: Boolean(rawFreshness.is_archive),
        is_stale: Boolean(rawFreshness.is_stale),
        new_videos_count:
          typeof rawFreshness.new_videos_count === "number" ? rawFreshness.new_videos_count : 0,
        new_must_watch_count:
          typeof rawFreshness.new_must_watch_count === "number"
            ? rawFreshness.new_must_watch_count
            : 0,
        new_titles: strArr(rawFreshness.new_titles),
      }
    : undefined;
  const rawDelta =
    isRec(raw.delta) && typeof raw.delta.previous_brief_id === "string"
      ? raw.delta
      : null;
  const delta: WeeklyBriefDelta | undefined = rawDelta
    ? {
        previous_brief_id: String(rawDelta.previous_brief_id),
        previous_created_at:
          typeof rawDelta.previous_created_at === "string" ? rawDelta.previous_created_at : "",
        previous_title_zh:
          typeof rawDelta.previous_title_zh === "string" ? rawDelta.previous_title_zh : "",
        total_videos_delta:
          typeof rawDelta.total_videos_delta === "number" ? rawDelta.total_videos_delta : 0,
        distilled_delta:
          typeof rawDelta.distilled_delta === "number" ? rawDelta.distilled_delta : 0,
        must_watch_delta:
          typeof rawDelta.must_watch_delta === "number" ? rawDelta.must_watch_delta : 0,
        new_picks: Array.isArray(rawDelta.new_picks)
          ? rawDelta.new_picks
              .filter(isRec)
              .map((np) => ({
                video_id: String(np.video_id ?? ""),
                title: String(np.title ?? np.video_id ?? ""),
                channel_name: String(np.channel_name ?? ""),
                score: typeof np.score === "number" ? np.score : 8.5,
                headline_zh: String(np.headline_zh ?? ""),
              }))
              .filter((np) => np.video_id.length > 0)
          : [],
        new_shifts_zh: strArr(rawDelta.new_shifts_zh),
        new_opportunities_zh: strArr(rawDelta.new_opportunities_zh),
        summary_zh: typeof rawDelta.summary_zh === "string" ? rawDelta.summary_zh : "",
      }
    : undefined;
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
    ...(freshness ? { freshness } : {}),
    ...(delta ? { delta } : {}),
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    provider: typeof raw.provider === "string" ? raw.provider : "ollama",
    model: typeof raw.model === "string" ? raw.model : "qwen3.5:9b",
    created_at: typeof raw.created_at === "string" ? raw.created_at : "",
    ...(history.length > 0 ? { history } : {}),
  };
}

export function readSourceAiSignalMap(raw: unknown): Record<string, SourceAiSignal> {
  if (!isRec(raw)) return {};
  const out: Record<string, SourceAiSignal> = {};
  for (const [sid, entry] of Object.entries(raw)) {
    if (!isRec(entry) || typeof entry.total_videos !== "number") continue;
    out[sid] = {
      source_id: typeof entry.source_id === "string" && entry.source_id.trim() ? entry.source_id : sid,
      channel_key: typeof entry.channel_key === "string" ? entry.channel_key : "",
      channel_label: typeof entry.channel_label === "string" ? entry.channel_label : "",
      total_videos: entry.total_videos,
      distilled_count: typeof entry.distilled_count === "number" ? entry.distilled_count : 0,
      long_form_count: typeof entry.long_form_count === "number" ? entry.long_form_count : 0,
      shorts_count: typeof entry.shorts_count === "number" ? entry.shorts_count : 0,
      must_watch_count: typeof entry.must_watch_count === "number" ? entry.must_watch_count : 0,
      worth_skimming_count: typeof entry.worth_skimming_count === "number" ? entry.worth_skimming_count : 0,
      unread_long_count: typeof entry.unread_long_count === "number" ? entry.unread_long_count : 0,
      avg_long_score: typeof entry.avg_long_score === "number" ? entry.avg_long_score : null,
      signal_rate_pct: typeof entry.signal_rate_pct === "number" ? entry.signal_rate_pct : null,
    };
  }
  return out;
}

function parseCitationArray(raw: unknown): AiResearchCitation[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(isRec)
    .map((c) => {
      const locatorType =
        typeof c.locator_type === "string" && c.locator_type.trim()
          ? c.locator_type.trim()
          : undefined;
      const paragraphIndex =
        typeof c.paragraph_index === "number" ? c.paragraph_index : null;
      const startOffset =
        typeof c.start_offset === "number" ? c.start_offset : null;
      const endOffset =
        typeof c.end_offset === "number" ? c.end_offset : null;
      const rawLabel =
        typeof c.timestamp_label === "string" ? c.timestamp_label.trim() : "";
      const timestampLabel =
        rawLabel.length > 0
          ? rawLabel
          : locatorType === "TEXT_RANGE"
            ? paragraphIndex !== null
              ? `P${paragraphIndex}`
              : "原文段落"
            : "00:00";
      const safeHttps = (v: unknown): string | null =>
        typeof v === "string" && v.trim().toLowerCase().startsWith("https://")
          ? v.trim()
          : null;
      return {
        ref_label: String(c.ref_label ?? ""),
        video_id: String(c.video_id ?? ""),
        video_title: String(c.video_title ?? c.video_id ?? ""),
        channel_name: String(c.channel_name ?? ""),
        evidence_id: String(c.evidence_id ?? ""),
        locator_type: locatorType,
        paragraph_index: paragraphIndex,
        start_offset: startOffset,
        end_offset: endOffset,
        start_ms: typeof c.start_ms === "number" ? c.start_ms : null,
        end_ms: typeof c.end_ms === "number" ? c.end_ms : null,
        timestamp_label: timestampLabel,
        source_url: safeHttps(c.source_url),
        citation_url: safeHttps(c.citation_url),
        excerpt: String(c.excerpt ?? ""),
      };
    })
    .filter((c) => c.video_id.length > 0 && c.evidence_id.length > 0);
}

function readAiResearchSession(raw: unknown): AiResearchSession | null {
  if (!isRec(raw) || typeof raw.session_id !== "string" || typeof raw.answer_zh !== "string") {
    return null;
  }
  const citations = parseCitationArray(raw.citations);
  const relatedExcerpts = parseCitationArray(raw.related_excerpts);
  const rawCovered = Array.isArray(raw.covered_sources)
    ? raw.covered_sources
    : isRec(raw.scope) && Array.isArray(raw.scope.covered_sources)
      ? raw.scope.covered_sources
      : [];
  const coveredSources: AiResearchCoveredSource[] = rawCovered
    .filter(isRec)
    .map((src) => ({
      video_id: String(src.video_id ?? "").trim(),
      title: String(src.title ?? src.video_id ?? "").trim(),
      provider: String(src.provider ?? "YOUTUBE").trim(),
      channel_name: String(src.channel_name ?? "").trim(),
      locator_type: String(src.locator_type ?? "TIME_RANGE").trim(),
    }))
    .filter((src) => src.video_id.length > 0);
  const coveredSourceCount =
    typeof raw.covered_source_count === "number"
      ? raw.covered_source_count
      : isRec(raw.scope) && typeof raw.scope.covered_source_count === "number"
        ? raw.scope.covered_source_count
        : coveredSources.length;
  let scope: AiResearchSessionScope | undefined;
  if (isRec(raw.scope)) {
    const rawVids = strArr(raw.scope.video_ids);
    scope = {
      starred_only: typeof raw.scope.starred_only === "boolean" ? raw.scope.starred_only : undefined,
      channel_key:
        typeof raw.scope.channel_key === "string" && raw.scope.channel_key.trim()
          ? raw.scope.channel_key.trim()
          : null,
      provider_filter:
        typeof raw.scope.provider_filter === "string" && raw.scope.provider_filter.trim()
          ? raw.scope.provider_filter.trim()
          : null,
      topic_cluster:
        typeof raw.scope.topic_cluster === "string" && raw.scope.topic_cluster.trim()
          ? raw.scope.topic_cluster.trim()
          : null,
      video_ids: rawVids.length > 0 ? rawVids : null,
    };
  }
  const pinned =
    typeof raw.pinned === "boolean"
      ? raw.pinned
      : Boolean(isRec(raw.scope) && raw.scope.pinned === true);
  const refused =
    typeof raw.refused === "boolean"
      ? raw.refused
      : raw.answer_status === "REFUSED_INSUFFICIENT_EVIDENCE" ||
        Boolean(isRec(raw.scope) && raw.scope.refused === true);
  const answerStatus =
    typeof raw.answer_status === "string" && raw.answer_status.trim()
      ? raw.answer_status
      : refused
        ? "REFUSED_INSUFFICIENT_EVIDENCE"
        : "GROUNDED";
  const refusalReason =
    typeof raw.refusal_reason_zh === "string"
      ? raw.refusal_reason_zh
      : isRec(raw.scope) && typeof raw.scope.refusal_reason_zh === "string"
        ? raw.scope.refusal_reason_zh
        : "";
  return {
    session_id: raw.session_id,
    question: typeof raw.question === "string" ? raw.question : "",
    answer_status: answerStatus,
    ...(typeof raw.source_integrity_status === "string"
      ? { source_integrity_status: raw.source_integrity_status }
      : {}),
    ...(typeof raw.fact_verification_state === "string"
      ? { fact_verification_state: raw.fact_verification_state }
      : {}),
    ...(typeof raw.contains_heuristic_claims === "boolean"
      ? { contains_heuristic_claims: raw.contains_heuristic_claims }
      : {}),
    ...(typeof raw.action_items_advisory === "boolean"
      ? { action_items_advisory: raw.action_items_advisory }
      : {}),
    refused,
    refusal_reason_zh: refusalReason,
    scope_label_zh: typeof raw.scope_label_zh === "string" ? raw.scope_label_zh : "",
    ...(typeof raw.video_count === "number" ? { video_count: raw.video_count } : {}),
    ...(coveredSources.length > 0
      ? { covered_sources: coveredSources, covered_source_count: coveredSourceCount }
      : {}),
    ...(scope ? { scope } : {}),
    pinned,
    answer_zh: raw.answer_zh,
    key_takeaways_zh: strArr(raw.key_takeaways_zh),
    action_items_zh: strArr(raw.action_items_zh),
    citations,
    ...(relatedExcerpts.length > 0 ? { related_excerpts: relatedExcerpts } : {}),
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    provider: typeof raw.provider === "string" ? raw.provider : "ollama",
    model: typeof raw.model === "string" ? raw.model : "qwen3.5:9b",
    created_at: typeof raw.created_at === "string" ? raw.created_at : "",
  };
}

function sortResearchSessions(list: AiResearchSession[]): AiResearchSession[] {
  return [...list].sort(
    (a, b) =>
      Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)) ||
      b.created_at.localeCompare(a.created_at),
  );
}

function readResearchScopeOptions(raw: unknown): ResearchScopeOptions | null {
  if (!isRec(raw)) return null;
  const channels = Array.isArray(raw.channels)
    ? raw.channels
        .filter(isRec)
        .map((ch) => ({
          key: typeof ch.key === "string" ? ch.key.trim() : "",
          label: typeof ch.label === "string" ? ch.label.trim() : "",
          count:
            typeof ch.count === "number"
              ? ch.count
              : typeof ch.video_count === "number"
                ? ch.video_count
                : 0,
        }))
        .filter((ch) => ch.key.length > 0 && ch.label.length > 0)
    : [];
  const topic_clusters = Array.isArray(raw.topic_clusters)
    ? raw.topic_clusters
        .filter(isRec)
        .map((tc) => ({
          name: typeof tc.name === "string" ? tc.name.trim() : "",
          count:
            typeof tc.count === "number"
              ? tc.count
              : typeof tc.video_count === "number"
                ? tc.video_count
                : 0,
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
          channel_key: typeof v.channel_key === "string" ? v.channel_key.trim() : undefined,
          score: typeof v.score === "number" ? v.score : null,
          starred: typeof v.starred === "boolean" ? v.starred : undefined,
          topic_cluster_zh: typeof v.topic_cluster_zh === "string" ? v.topic_cluster_zh : undefined,
        }))
        .filter((v) => v.video_id.length > 0)
    : [];
  const starred_count =
    typeof raw.starred_count === "number"
      ? raw.starred_count
      : videos.filter((v) => Boolean(v.starred)).length;
  return { starred_count, channels, topic_clusters, videos };
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
  const related_topics: TopicRelatedSummary[] = Array.isArray(raw.related_topics)
    ? raw.related_topics
        .filter(isRec)
        .map((rt) => ({
          topic_id: typeof rt.topic_id === "string" ? rt.topic_id : "",
          name: typeof rt.name === "string" ? rt.name : "",
          video_count: typeof rt.video_count === "number" ? rt.video_count : 0,
          must_watch_count: typeof rt.must_watch_count === "number" ? rt.must_watch_count : 0,
          avg_score: typeof rt.avg_score === "number" ? rt.avg_score : 0,
          shared_sources: strArr(rt.shared_sources),
        }))
        .filter((rt) => rt.topic_id.length > 0 && rt.name.length > 0)
    : [];
  const channel_breakdown: TopicChannelBreakdownItem[] = Array.isArray(raw.channel_breakdown)
    ? raw.channel_breakdown
        .filter(isRec)
        .map((ch) => ({
          channel_key: typeof ch.channel_key === "string" ? ch.channel_key.trim() : "",
          channel_label:
            typeof ch.channel_label === "string" && ch.channel_label.trim()
              ? ch.channel_label.trim()
              : typeof ch.channel_key === "string"
                ? ch.channel_key.trim()
                : "",
          video_count: typeof ch.video_count === "number" ? ch.video_count : 0,
          must_watch_count: typeof ch.must_watch_count === "number" ? ch.must_watch_count : 0,
          unread_count: typeof ch.unread_count === "number" ? ch.unread_count : 0,
        }))
        .filter((ch) => ch.channel_key.length > 0 && ch.video_count > 0)
    : [];
  const source_perspectives: TopicSourcePerspective[] = Array.isArray(raw.source_perspectives)
    ? raw.source_perspectives
        .filter(isRec)
        .map((p) => ({
          channel_name: typeof p.channel_name === "string" ? p.channel_name : "",
          video_id: typeof p.video_id === "string" ? p.video_id : "",
          title: typeof p.title === "string" ? p.title : "",
          headline_zh: typeof p.headline_zh === "string" ? p.headline_zh : "",
          angle_zh: typeof p.angle_zh === "string" ? p.angle_zh : "",
          score: typeof p.score === "number" ? p.score : 0,
        }))
        .filter((p) => p.channel_name.length > 0 && (p.angle_zh.length > 0 || p.headline_zh.length > 0))
    : [];
  return {
    video_count: raw.video_count,
    must_watch_count: typeof raw.must_watch_count === "number" ? raw.must_watch_count : 0,
    unread_count: typeof raw.unread_count === "number" ? raw.unread_count : 0,
    recent_7d_count: typeof raw.recent_7d_count === "number" ? raw.recent_7d_count : 0,
    avg_score: typeof raw.avg_score === "number" ? raw.avg_score : null,
    latest_headline_zh: typeof raw.latest_headline_zh === "string" ? raw.latest_headline_zh : "",
    latest_published_at:
      typeof raw.latest_published_at === "string"
        ? raw.latest_published_at
        : (entries[0]?.published_at ?? ""),
    synthesis_zh: typeof raw.synthesis_zh === "string" ? raw.synthesis_zh : "",
    independence_summary_zh:
      typeof raw.independence_summary_zh === "string" ? raw.independence_summary_zh : "",
    top_opportunities_zh: strArr(raw.top_opportunities_zh),
    source_perspectives,
    source_channels: strArr(raw.source_channels),
    channel_breakdown,
    related_topics,
    obsidian_markdown: typeof raw.obsidian_markdown === "string" ? raw.obsidian_markdown : "",
    entries,
  };
}

export function readWorkspaceAiTranscribeJob(raw: unknown): WorkspaceAiTranscribeJob | null {
  if (!isRec(raw)) return null;
  const status = raw.status;
  if (status !== "RUNNING" && status !== "READY" && status !== "FAILED") {
    return null;
  }
  const stage = raw.stage;
  return {
    status,
    stage:
      stage === "TRANSCRIBING" || stage === "DISTILLING" || stage === "READY" || stage === "FAILED"
        ? stage
        : status === "RUNNING"
          ? "TRANSCRIBING"
          : status,
    started_at: typeof raw.started_at === "string" ? raw.started_at : "",
    updated_at: typeof raw.updated_at === "string" ? raw.updated_at : "",
    error_code: typeof raw.error_code === "string" ? raw.error_code : null,
  };
}

export function readWorkspaceAiCapabilities(raw: unknown): WorkspaceAiCapabilities | null {
  if (!isRec(raw)) return null;
  return {
    ready: Boolean(raw.ready),
    transcriber_ready: Boolean(raw.transcriber_ready),
    transcribe_job: readWorkspaceAiTranscribeJob(raw.transcribe_job),
    ...(typeof raw.visual_analysis_eligible === "boolean"
      ? { visual_analysis_eligible: raw.visual_analysis_eligible }
      : {}),
    ...(typeof raw.ffmpeg_available === "boolean"
      ? { ffmpeg_available: raw.ffmpeg_available }
      : {}),
  };
}

export function readVideoVisualAnalysis(raw: unknown): VideoVisualAnalysis | null {
  if (!isRec(raw) || typeof raw.video_id !== "string" || !Array.isArray(raw.frames)) {
    return null;
  }
  const frames: VideoVisualKeyframe[] = raw.frames
    .filter(isRec)
    .map((f, idx) => ({
      frame_index: typeof f.frame_index === "number" ? f.frame_index : idx + 1,
      frame_id: typeof f.frame_id === "string" ? f.frame_id : `f-${idx + 1}`,
      filename: typeof f.filename === "string" ? f.filename : "",
      obsidian_asset_name:
        typeof f.obsidian_asset_name === "string" ? f.obsidian_asset_name : undefined,
      timestamp_ms: typeof f.timestamp_ms === "number" ? f.timestamp_ms : 0,
      timestamp_label: typeof f.timestamp_label === "string" ? f.timestamp_label : "00:00",
      selection_reason: typeof f.selection_reason === "string" ? f.selection_reason : "UNIFORM",
      frame_kind: typeof f.frame_kind === "string" ? f.frame_kind : "OTHER",
      has_visual_info: typeof f.has_visual_info === "boolean" ? f.has_visual_info : true,
      title_zh: typeof f.title_zh === "string" ? f.title_zh : "",
      visual_detail_zh: typeof f.visual_detail_zh === "string" ? f.visual_detail_zh : "",
      transcript_fusion_zh:
        typeof f.transcript_fusion_zh === "string" ? f.transcript_fusion_zh : "",
      nearby_transcript: typeof f.nearby_transcript === "string" ? f.nearby_transcript : "",
      image_url: typeof f.image_url === "string" ? f.image_url : "",
      image_available: typeof f.image_available === "boolean" ? f.image_available : Boolean(f.image_url),
    }))
    .filter((f) => f.image_url.length > 0);
  return {
    video_id: raw.video_id,
    visual_summary_zh: typeof raw.visual_summary_zh === "string" ? raw.visual_summary_zh : "",
    visual_takeaways_zh: strArr(raw.visual_takeaways_zh),
    frames,
    frame_count: typeof raw.frame_count === "number" ? raw.frame_count : frames.length,
    informative_frame_count:
      typeof raw.informative_frame_count === "number"
        ? raw.informative_frame_count
        : frames.filter((f) => f.has_visual_info).length,
    provider: typeof raw.provider === "string" ? raw.provider : "ollama",
    model: typeof raw.model === "string" ? raw.model : "",
    updated_at: typeof raw.updated_at === "string" ? raw.updated_at : "",
  };
}

function readCuratedOllamaList(raw: unknown): CuratedOllamaModel[] {
  if (!Array.isArray(raw)) return [];
  const out: CuratedOllamaModel[] = [];
  for (const item of raw) {
    if (!isRec(item) || typeof item.id !== "string") continue;
    out.push({
      id: item.id,
      label: typeof item.label === "string" ? item.label : item.id,
      tier: typeof item.tier === "string" ? item.tier : "balanced",
      size_label: typeof item.size_label === "string" ? item.size_label : "",
      ram_label_zh: typeof item.ram_label_zh === "string" ? item.ram_label_zh : "",
      ram_label_en: typeof item.ram_label_en === "string" ? item.ram_label_en : "",
      supports_vision: Boolean(item.supports_vision),
      summary_zh: typeof item.summary_zh === "string" ? item.summary_zh : "",
      summary_en: typeof item.summary_en === "string" ? item.summary_en : "",
    });
  }
  return out;
}

function readCuratedWhisperList(raw: unknown): CuratedWhisperModel[] {
  if (!Array.isArray(raw)) return [];
  const out: CuratedWhisperModel[] = [];
  for (const item of raw) {
    if (!isRec(item) || typeof item.id !== "string" || typeof item.slug !== "string") continue;
    out.push({
      id: item.id,
      slug: item.slug,
      label: typeof item.label === "string" ? item.label : item.id,
      tier: typeof item.tier === "string" ? item.tier : "balanced",
      size_label: typeof item.size_label === "string" ? item.size_label : "",
      summary_zh: typeof item.summary_zh === "string" ? item.summary_zh : "",
      summary_en: typeof item.summary_en === "string" ? item.summary_en : "",
    });
  }
  return out;
}

export function readWorkspaceAiSettings(raw: unknown): WorkspaceAiSettings | null {
  if (!isRec(raw) || (raw.active_mode !== "local_ollama" && raw.active_mode !== "cloud_byok")) {
    return null;
  }
  const curatedOllama = readCuratedOllamaList(raw.curated_ollama_models);
  const curatedWhisper = readCuratedWhisperList(raw.curated_whisper_models);
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
    ...(typeof raw.local_mlx_Whisper_ready === "boolean"
      ? { local_mlx_Whisper_ready: raw.local_mlx_Whisper_ready }
      : {}),
    ...(typeof raw.active_whisper_slug === "string"
      ? { active_whisper_slug: raw.active_whisper_slug }
      : {}),
    ...(curatedOllama.length > 0 ? { curated_ollama_models: curatedOllama } : {}),
    ...(curatedWhisper.length > 0 ? { curated_whisper_models: curatedWhisper } : {}),
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

export function isKeyboardShortcutBlocked(event: KeyboardEvent): boolean {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) {
    return true;
  }
  if (
    typeof document !== "undefined" &&
    document.querySelector("dialog[open], [aria-modal='true']") !== null
  ) {
    return true;
  }
  const isEditable = (node: EventTarget | null): boolean => {
    if (!(node instanceof HTMLElement)) return false;
    if (node.isContentEditable) return true;
    return (
      node.closest("input, textarea, select, [contenteditable='true'], [role='combobox']") !== null
    );
  };
  return (
    isEditable(event.target) ||
    (typeof document !== "undefined" && isEditable(document.activeElement))
  );
}

export function downloadBase64ZipArchive(filename: string, archiveBase64: string): void {
  if (!archiveBase64 || typeof URL === "undefined" || typeof URL.createObjectURL !== "function") {
    return;
  }
  const safeName = filename.endsWith(".zip") ? filename : `${filename}.zip`;
  let buffer: ArrayBuffer;
  try {
    const binary = atob(archiveBase64);
    buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
  } catch {
    return;
  }
  const blob = new Blob([buffer], { type: "application/zip" });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = safeName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export async function exportObsidianVaultBundle(
  scope: ObsidianBundleScope = "must_watch",
): Promise<ObsidianVaultBundleResult> {
  const res = await api<{
    filename?: unknown;
    scope?: unknown;
    counts?: unknown;
    archive_base64?: unknown;
  }>(`/workspace-ai/obsidian-bundle?scope=${encodeURIComponent(scope)}`);
  const counts = isRec(res.counts) ? res.counts : {};
  const totalFiles = typeof counts.total_files === "number" ? counts.total_files : 0;
  const videoNotes = typeof counts.video_notes === "number" ? counts.video_notes : 0;
  const topicMocs = typeof counts.topic_mocs === "number" ? counts.topic_mocs : 0;
  const dateStamp = new Date().toISOString().slice(0, 10);
  const filename =
    typeof res.filename === "string" && res.filename.trim()
      ? res.filename.trim()
      : `Obsidian-AI情报知识库-${scope}-${dateStamp}.zip`;
  if (typeof res.archive_base64 === "string" && res.archive_base64.length > 0) {
    downloadBase64ZipArchive(filename, res.archive_base64);
  }
  return {
    filename,
    scope,
    totalFiles,
    videoNotes,
    topicMocs,
  };
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
    <span
      className={`ai-score-pill tabular-nums ${toneClass}${compact ? " is-compact" : ""}`}
      title={
        zh
          ? "AI 优先级排序分，用于决定推荐浏览顺序；不等同于原文事实核验结论"
          : "AI priority ranking score for triage; not a factual grounding verification"
      }
    >
      <strong>{brief.score.toFixed(1)}</strong>
      <span>· {tierLabel}</span>
      {!compact ? (
        <small className="ai-score-posture">
          {zh ? "排序分" : "Priority"}
        </small>
      ) : null}
    </span>
  );
}

export function formatPlainTextWeeklyBrief(
  brief: WeeklyAiBrief,
  zh: boolean,
): string {
  const stripWiki = (text: string) =>
    text.replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target: string, alias?: string) => (alias ?? target).trim(),
    );
  const lines: string[] = [];
  const weekSuffix = brief.week_label?.trim()
    ? zh
      ? `（${brief.week_label.trim()}）`
      : ` (${brief.week_label.trim()})`
    : "";
  lines.push(
    zh
      ? `【AI 情报周报】${stripWiki(brief.title_zh.trim())}${weekSuffix}`
      : `[Weekly AI Brief] ${stripWiki(brief.title_zh.trim())}${weekSuffix}`,
  );
  lines.push(
    zh
      ? `统计范围：收录 ${brief.funnel_stats.total_videos} 条内容 · 自动折叠 ${brief.funnel_stats.shorts_filtered_count} 条短片 · 精选 ${brief.funnel_stats.must_watch_count} 条必看干货`
      : `Scope: ${brief.funnel_stats.total_videos} items · ${brief.funnel_stats.shorts_filtered_count} Shorts folded · ${brief.funnel_stats.must_watch_count} must-watch picks`,
  );
  if (brief.executive_summary_zh.trim()) {
    lines.push(
      zh
        ? `核心综述：\n${stripWiki(brief.executive_summary_zh.trim())}`
        : `Executive summary:\n${stripWiki(brief.executive_summary_zh.trim())}`,
    );
  }
  if (brief.core_trends_zh.length > 0) {
    lines.push(
      [
        zh ? "核心趋势判断：" : "Core trends:",
        ...brief.core_trends_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (brief.product_opportunities_zh.length > 0) {
    lines.push(
      [
        zh ? "AI 产品化启发：" : "Product takeaways:",
        ...brief.product_opportunities_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (brief.business_opportunities_zh.length > 0) {
    lines.push(
      [
        zh ? "商业变现切口：" : "Monetization angles:",
        ...brief.business_opportunities_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (brief.must_watch_picks.length > 0) {
    lines.push(
      [
        zh ? "本周必看精选：" : "Must-watch picks:",
        ...brief.must_watch_picks.map((pick, idx) => {
          const titlePart = zh
            ? `《${stripWiki(pick.title.trim())}》`
            : `"${stripWiki(pick.title.trim())}"`;
          const meta = [
            pick.channel_name?.trim() ? stripWiki(pick.channel_name.trim()) : "",
            `${pick.score.toFixed(1)}/10`,
          ]
            .filter(Boolean)
            .join(" · ");
          const reason = stripWiki(pick.reason_zh.trim());
          return reason
            ? `${idx + 1}. ${titlePart}（${meta}）：${reason}`
            : `${idx + 1}. ${titlePart}（${meta}）`;
        }),
      ].join("\n"),
    );
  }
  return lines.join("\n\n");
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
  const [historyList, setHistoryList] = useState<WeeklyBriefHistoryItem[]>(
    initialBrief?.history ?? [],
  );
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copiedPlain, setCopiedPlain] = useState(false);
  const [bundleScope, setBundleScope] = useState<ObsidianBundleScope>("must_watch");
  const [exportingBundle, setExportingBundle] = useState(false);
  const [bundleStatus, setBundleStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCopied(false);
    setCopiedPlain(false);
  }, [brief?.brief_id]);

  useEffect(() => {
    if (initialBrief) {
      setBrief(initialBrief);
      if (initialBrief.history?.length) {
        setHistoryList(initialBrief.history);
      }
    }
  }, [initialBrief]);

  if (!brief) return null;

  const effectiveHistory = historyList.length > 0 ? historyList : brief.history ?? [];

  const switchSnapshot = async (nextId: string) => {
    if (!nextId || nextId === brief.brief_id || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api<{ weekly_brief?: unknown; history?: unknown }>(
        `/workspace-ai/weekly-brief?brief_id=${encodeURIComponent(nextId)}`,
      );
      const parsed = readWeeklyAiBrief(res.weekly_brief);
      const nextHist = readWeeklyHistoryList(res.history);
      if (parsed) {
        setBrief(parsed);
        const resolvedHist = nextHist.length ? nextHist : parsed.history ?? [];
        if (resolvedHist.length) setHistoryList(resolvedHist);
      }
    } catch {
      setError(zh ? "未能加载所选历史周报期次。" : "Could not load selected weekly brief snapshot.");
    } finally {
      setBusy(false);
    }
  };

  const regenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await post<{ weekly_brief?: unknown; history?: unknown }>(
        "/workspace-ai/weekly-brief/generate",
        {},
      );
      const parsed = readWeeklyAiBrief(res.weekly_brief);
      const nextHist = readWeeklyHistoryList(res.history);
      if (parsed) {
        setBrief(parsed);
        const resolvedHist = nextHist.length ? nextHist : parsed.history ?? [];
        if (resolvedHist.length) setHistoryList(resolvedHist);
      }
    } catch {
      setError(zh ? "未能刷新本周情报周报，请检查本机或云端 AI 引擎状态。" : "Could not refresh the weekly AI brief.");
    } finally {
      setBusy(false);
    }
  };

  const handleExportBundle = async () => {
    if (exportingBundle) return;
    setExportingBundle(true);
    setBundleStatus(null);
    setError(null);
    try {
      const out = await exportObsidianVaultBundle(bundleScope);
      setBundleStatus(
        zh
          ? `已导出 Obsidian 双链知识库包（共 ${out.totalFiles} 篇 .md 笔记，含总览 MOC、专题演化与双链互引）`
          : `Exported Obsidian Vault bundle (${out.totalFiles} interlinked .md notes)`,
      );
    } catch {
      setError(
        zh
          ? "未能导出 Obsidian 知识库包，请稍后重试。"
          : "Could not export Obsidian Vault bundle.",
      );
    } finally {
      setExportingBundle(false);
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
          {effectiveHistory.length > 1 ? (
            <select
              className="weekly-history-select tabular-nums"
              aria-label={zh ? "切换历史周报期次" : "Select weekly brief snapshot"}
              value={brief.brief_id}
              disabled={busy}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                void switchSnapshot(event.target.value)
              }
            >
              {effectiveHistory.map((item, idx) => {
                const shortDate = item.created_at ? item.created_at.slice(0, 10) : `#${idx + 1}`;
                return (
                  <option key={item.brief_id} value={item.brief_id}>
                    {idx === 0
                      ? zh
                        ? `最新 · ${shortDate}（${item.must_watch_count} 必看）`
                        : `Latest · ${shortDate} (${item.must_watch_count} must-watch)`
                      : zh
                        ? `存档 · ${shortDate}（${item.must_watch_count} 必看）`
                        : `Archive · ${shortDate} (${item.must_watch_count} must-watch)`}
                  </option>
                );
              })}
            </select>
          ) : null}
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
        </span>{" "}
        {brief.week_label ? <span>{brief.week_label}</span> : null}
      </div>

      {brief.delta && brief.delta.summary_zh ? (
        <div
          className="weekly-delta-strip tabular-nums"
          role="region"
          aria-label={zh ? "较上期周报演进对比" : "Changes since previous brief"}
        >
          <div className="weekly-delta-summary">
            <strong>{brief.delta.summary_zh}</strong>
            {brief.delta.previous_created_at ? (
              <span>
                {zh
                  ? `对比上期 ${brief.delta.previous_created_at.slice(0, 10)}`
                  : `vs. ${brief.delta.previous_created_at.slice(0, 10)}`}
              </span>
            ) : null}
          </div>
          {brief.delta.new_picks.length > 0 ? (
            <div className="weekly-delta-picks">
              <span className="weekly-delta-picks-label">
                {zh ? "本期新上榜：" : "New picks:"}
              </span>
              {brief.delta.new_picks.slice(0, 3).map((pick) => (
                <button
                  key={pick.video_id}
                  type="button"
                  className="weekly-delta-pick-chip"
                  onClick={() => onOpenContent(pick.video_id)}
                >
                  <span>{pick.title}</span>
                  <small>{pick.score.toFixed(1)}</small>
                </button>
              ))}
            </div>
          ) : null}
          {brief.delta.new_shifts_zh.length > 0 ? (
            <div className="weekly-delta-picks weekly-delta-shifts">
              <span className="weekly-delta-picks-label">
                {zh ? "本期新风向：" : "New shifts:"}
              </span>
              {brief.delta.new_shifts_zh.slice(0, 3).map((shift, idx) => (
                <span key={`shift:${idx}`} className="weekly-delta-shift-pill">
                  {shift}
                </span>
              ))}
            </div>
          ) : brief.delta.new_opportunities_zh.length > 0 ? (
            <div className="weekly-delta-picks weekly-delta-shifts">
              <span className="weekly-delta-picks-label">
                {zh ? "本期新切口：" : "New opportunities:"}
              </span>
              {brief.delta.new_opportunities_zh.slice(0, 3).map((opp, idx) => (
                <span key={`opp:${idx}`} className="weekly-delta-shift-pill">
                  {opp}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {brief.freshness?.is_stale &&
      !brief.freshness.is_archive &&
      brief.freshness.new_videos_count > 0 ? (
        <div
          className="weekly-freshness-banner tabular-nums"
          role="region"
          aria-label={zh ? "周报增量更新提示" : "Weekly brief freshness notice"}
        >
          <div className="weekly-freshness-copy">
            <strong>
              {zh
                ? `自上次生成周报以来新增 ${brief.freshness.new_videos_count} 篇干货${brief.freshness.new_must_watch_count > 0 ? `（含 ${brief.freshness.new_must_watch_count} 篇必看）` : ""}`
                : `${brief.freshness.new_videos_count} new distilled videos since this brief${brief.freshness.new_must_watch_count > 0 ? ` (${brief.freshness.new_must_watch_count} must-watch)` : ""}`}
            </strong>
            {brief.freshness.new_titles.length > 0 ? (
              <span>
                {zh ? "最新提炼：" : "Latest: "}
                {brief.freshness.new_titles.slice(0, 2).join(" · ")}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            className="button button-primary button-small"
            disabled={busy}
            onClick={() => void regenerate()}
          >
            <PhosphorIcon name="lightning" size={13} />
            {busy
              ? zh
                ? "正在刷新…"
                : "Refreshing…"
              : zh
                ? "立即纳入刷新周报"
                : "Refresh brief with new items"}
          </button>
        </div>
      ) : null}

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

      <div className="obsidian-export-bar">
        <div className="button-row">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void navigator.clipboard?.writeText(
                formatPlainTextWeeklyBrief(brief, zh),
              );
              setCopiedPlain(true);
              setTimeout(() => setCopiedPlain(false), 2200);
            }}
          >
            <PhosphorIcon name="quotes" size={13} />
            {copiedPlain
              ? zh
                ? "已复制纯文本周报"
                : "Copied plain-text brief"
              : zh
                ? "复制纯文本周报"
                : "Copy plain-text brief"}
          </button>
          {brief.obsidian_markdown ? (
            <>
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
            </>
          ) : null}
          <select
            className="weekly-history-select obsidian-scope-select"
            aria-label={zh ? "Obsidian 知识库包导出范围" : "Obsidian Vault bundle scope"}
            value={bundleScope}
            disabled={exportingBundle}
            onChange={(event: ChangeEvent<HTMLSelectElement>) =>
              setBundleScope(event.target.value as ObsidianBundleScope)
            }
          >
            <option value="must_watch">{zh ? "必看精选（推荐）" : "Must-watch (recommended)"}</option>
            <option value="all">{zh ? "全部干货" : "All distilled notes"}</option>
            <option value="starred">{zh ? "已收藏清单" : "Starred only"}</option>
          </select>
          <button
            type="button"
            className="button button-secondary button-small"
            disabled={exportingBundle}
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void handleExportBundle();
            }}
          >
            <PhosphorIcon name="archive" size={13} />
            {exportingBundle
              ? zh
                ? "正在打包…"
                : "Bundling…"
              : zh
                ? "导出 Obsidian 知识库包 (.zip)"
                : "Export Obsidian Vault (.zip)"}
          </button>
        </div>
        {bundleStatus ? (
          <p className="obsidian-bundle-status tabular-nums" role="status">
            {bundleStatus}
          </p>
        ) : null}
        {brief.obsidian_markdown ? (
          <details className="obsidian-preview-drawer">
            <summary>{zh ? "预览 Obsidian 双链 Markdown" : "Preview Obsidian Markdown"}</summary>
            <pre className="obsidian-preview-pre">{brief.obsidian_markdown}</pre>
          </details>
        ) : null}
      </div>
    </section>
  );
}

export function formatPlainTextVideoBrief(
  brief: VideoAiBrief,
  title: string,
  opts?: { channelName?: string | null; sourceUrl?: string | null; zh?: boolean },
): string {
  const zh = opts?.zh ?? true;
  const stripWiki = (text: string) =>
    text.replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target: string, alias?: string) => (alias ?? target).trim(),
    );
  const cleanTitle = stripWiki(title.trim());
  const lines: string[] = [];
  lines.push(
    zh
      ? `【视频深度摘要】《${cleanTitle}》`
      : `[Video AI Brief] "${cleanTitle}"`,
  );
  const metaParts = [
    opts?.channelName?.trim()
      ? zh
        ? `来源：${stripWiki(opts.channelName.trim())}`
        : `Source: ${stripWiki(opts.channelName.trim())}`
      : "",
    zh
      ? `评分：${brief.score.toFixed(1)}/10`
      : `Score: ${brief.score.toFixed(1)}/10`,
    brief.topic_cluster_zh?.trim()
      ? zh
        ? `专题：${stripWiki(brief.topic_cluster_zh.trim())}`
        : `Topic: ${stripWiki(brief.topic_cluster_zh.trim())}`
      : "",
  ].filter(Boolean);
  if (metaParts.length > 0) {
    lines.push(metaParts.join(" · "));
  }
  if (brief.headline_zh.trim()) {
    lines.push(
      zh
        ? `核心结论：\n${stripWiki(brief.headline_zh.trim())}`
        : `Key takeaway:\n${stripWiki(brief.headline_zh.trim())}`,
    );
  }
  if (
    brief.summary_zh.trim() &&
    brief.summary_zh.trim() !== brief.headline_zh.trim()
  ) {
    lines.push(
      zh
        ? `深度提炼：\n${stripWiki(brief.summary_zh.trim())}`
        : `Summary:\n${stripWiki(brief.summary_zh.trim())}`,
    );
  }
  if (brief.product_opportunities_zh.length > 0) {
    lines.push(
      [
        zh ? "AI 产品化启发：" : "Product takeaways:",
        ...brief.product_opportunities_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (brief.business_opportunities_zh.length > 0) {
    lines.push(
      [
        zh ? "商业变现与切入机会：" : "Monetization opportunities:",
        ...brief.business_opportunities_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (opts?.sourceUrl?.trim()) {
    lines.push(
      zh
        ? `原视频：${opts.sourceUrl.trim()}`
        : `Video URL: ${opts.sourceUrl.trim()}`,
    );
  }
  return lines.join("\n\n");
}

export function WorkspaceVideoAiActions({
  videoId,
  title,
  channelName,
  sourceUrl,
  provider,
  isLocalMedia,
  transcriptAvailable,
  transcriberReady,
  aiBrief,
  obsidianMarkdown,
  initialTranscribeJob,
  actionRequest,
  onTranscribeStateChange,
  nextUnreadVideo,
  onAdvanceToVideo,
  onBack,
  sourceLinkNode,
  legacyCopyNode,
  onCompleted,
}: {
  videoId: string;
  title: string;
  channelName?: string | null;
  sourceUrl?: string | null;
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  isLocalMedia: boolean;
  transcriptAvailable: boolean;
  transcriberReady?: boolean;
  aiBrief: VideoAiBrief | null;
  obsidianMarkdown?: string;
  initialTranscribeJob?: WorkspaceAiTranscribeJob | null;
  actionRequest?: { nonce: number; kind: "transcribe" | "distill" } | null;
  onTranscribeStateChange?: (running: boolean, stage?: string) => void;
  nextUnreadVideo?: {
    videoId: string;
    title: string;
    remainingCount: number;
    scoped?: boolean;
  } | null;
  onAdvanceToVideo?: (nextId: string) => void;
  onBack?: () => void;
  sourceLinkNode?: ReactNode;
  legacyCopyNode?: ReactNode;
  onCompleted: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [busyKind, setBusyKind] = useState<"distill" | "transcribe" | "curation" | null>(null);
  const [transcribeStage, setTranscribeStage] = useState<string>("TRANSCRIBING");
  const [error, setError] = useState<string | null>(null);
  const [errorAction, setErrorAction] = useState<{ label: string; href: string } | null>(null);
  const [copiedObsidian, setCopiedObsidian] = useState(false);
  const [copiedPlainBrief, setCopiedPlainBrief] = useState(false);
  const aliveRef = useRef(true);
  const pollingVideoRef = useRef<string | null>(null);
  const handledNonceRef = useRef<number>(0);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      pollingVideoRef.current = null;
    };
  }, []);

  useEffect(() => {
    setCopiedObsidian(false);
    setCopiedPlainBrief(false);
    setError(null);
    setErrorAction(null);
    pollingVideoRef.current = null;
  }, [videoId]);

  const mdContent = obsidianMarkdown ?? aiBrief?.obsidian_markdown ?? "";
  const canMetadataPreview =
    !isLocalMedia && !transcriptAvailable && (provider ?? "YOUTUBE") === "YOUTUBE";

  const toggleCuration = async (patchBody: { starred?: boolean; is_read?: boolean }) => {
    if (busyKind !== null) return;
    setBusyKind("curation");
    setError(null);
    setErrorAction(null);
    try {
      await post(`/workspace-ai/videos/${encodeURIComponent(videoId)}/curation`, patchBody);
      onCompleted();
    } catch {
      setError(zh ? "未能更新阅读与收藏状态，请稍后重试。" : "Could not update reading state.");
    } finally {
      setBusyKind(null);
    }
  };

  const markReadAndAdvance = async () => {
    if (busyKind !== null || !nextUnreadVideo || !onAdvanceToVideo) return;
    setBusyKind("curation");
    setError(null);
    setErrorAction(null);
    try {
      if (!aiBrief?.is_read) {
        await post(`/workspace-ai/videos/${encodeURIComponent(videoId)}/curation`, {
          is_read: true,
        });
      }
      onCompleted();
      onAdvanceToVideo(nextUnreadVideo.videoId);
    } catch {
      setError(
        zh ? "未能更新阅读状态并跳转下一篇，请稍后重试。" : "Could not mark read and open next item.",
      );
    } finally {
      setBusyKind(null);
    }
  };

  const shortcutRef = useRef({
    aiBrief,
    nextUnreadVideo,
    onAdvanceToVideo,
    onBack,
    toggleCuration,
    markReadAndAdvance,
  });
  shortcutRef.current = {
    aiBrief,
    nextUnreadVideo,
    onAdvanceToVideo,
    onBack,
    toggleCuration,
    markReadAndAdvance,
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isKeyboardShortcutBlocked(event)) return;
      const cur = shortcutRef.current;
      const key = event.key.toLowerCase();
      if (key === "s" && cur.aiBrief) {
        event.preventDefault();
        void cur.toggleCuration({ starred: !cur.aiBrief.starred });
      } else if (key === "e" && cur.aiBrief) {
        event.preventDefault();
        if (cur.nextUnreadVideo && cur.onAdvanceToVideo) {
          void cur.markReadAndAdvance();
        } else {
          void cur.toggleCuration({ is_read: !cur.aiBrief.is_read });
        }
      } else if ((key === "u" || event.key === "[") && cur.onBack) {
        event.preventDefault();
        cur.onBack();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const pollAsyncTranscribeUntilSettled = async (targetId: string, startStage?: string) => {
    if (pollingVideoRef.current === targetId) return;
    pollingVideoRef.current = targetId;
    const pollDelayMs =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent) ? 80 : 2500;
    let curStage = startStage || "TRANSCRIBING";
    setBusyKind("transcribe");
    setTranscribeStage(curStage);
    onTranscribeStateChange?.(true, curStage);
    try {
      while (aliveRef.current && pollingVideoRef.current === targetId) {
        await new Promise((resolve) => setTimeout(resolve, pollDelayMs));
        if (!aliveRef.current || pollingVideoRef.current !== targetId) return;
        const pollRes = await api<{ job?: unknown }>(
          `/workspace-ai/videos/${encodeURIComponent(targetId)}/transcribe-status`,
        );
        const job = readWorkspaceAiTranscribeJob(pollRes.job);
        if (!job) {
          break;
        }
        if (job.status === "RUNNING") {
          if (job.stage !== curStage) {
            curStage = job.stage;
            setTranscribeStage(curStage);
            onTranscribeStateChange?.(true, curStage);
          }
          continue;
        }
        if (job.status === "READY") {
          pollingVideoRef.current = null;
          setBusyKind(null);
          onTranscribeStateChange?.(false, "READY");
          onCompleted();
          return;
        }
        pollingVideoRef.current = null;
        setBusyKind(null);
        onTranscribeStateChange?.(false, "FAILED");
        if (job.error_code === "CLOUD_CREDENTIAL_MISSING") {
          setError(
            zh
              ? "当前选为云端模式但尚未填写 API Key，请在设置中保存 Key 或切回本机免费 Ollama。"
              : "Cloud API key is missing in Settings.",
          );
          setErrorAction({
            label: zh ? "前往模型设置 →" : "Open model settings →",
            href: "#Settings",
          });
        } else if (job.error_code === "TRANSCRIBER_UNAVAILABLE") {
          setError(
            zh
              ? "未检测到本机离线语音转写模型，请先前往设置配置。"
              : "Local offline transcription model is not configured.",
          );
          setErrorAction({
            label: zh ? "先设置本地转写 →" : "Set up local transcription →",
            href: "#Settings/transcription",
          });
        } else {
          setError(
            zh
              ? "本地离线语音转写未能完成，请检查本地转写模型与音视频文件。"
              : "Offline local transcription could not complete.",
          );
          setErrorAction({
            label: zh ? "查看转写设置 →" : "Transcription settings →",
            href: "#Settings/transcription",
          });
        }
        return;
      }
    } catch {
      if (aliveRef.current && pollingVideoRef.current === targetId) {
        setError(
          zh
            ? "转写进度读取中断，后台仍在继续处理，请稍后刷新页面查看。"
            : "Transcription status check interrupted; reload shortly.",
        );
      }
    } finally {
      if (pollingVideoRef.current === targetId) {
        pollingVideoRef.current = null;
      }
      if (aliveRef.current) {
        setBusyKind(null);
        onTranscribeStateChange?.(false);
      }
    }
  };

  useEffect(() => {
    if (
      isLocalMedia &&
      !transcriptAvailable &&
      initialTranscribeJob?.status === "RUNNING" &&
      pollingVideoRef.current !== videoId
    ) {
      void pollAsyncTranscribeUntilSettled(videoId, initialTranscribeJob.stage);
    }
  }, [videoId, isLocalMedia, transcriptAvailable, initialTranscribeJob?.status]);

  const runAction = async (kind: "distill" | "transcribe") => {
    if (busyKind !== null) return;
    setBusyKind(kind);
    setError(null);
    setErrorAction(null);
    if (kind === "transcribe") {
      setTranscribeStage("TRANSCRIBING");
      onTranscribeStateChange?.(true, "TRANSCRIBING");
    }
    try {
      const res = await post<{ transcription_status?: string; stage?: string }>(
        `/workspace-ai/videos/${encodeURIComponent(videoId)}/${kind}`,
        kind === "transcribe" ? { async: true } : {},
      );
      if (kind === "transcribe" && res?.transcription_status === "RUNNING") {
        await pollAsyncTranscribeUntilSettled(videoId, res.stage);
        return;
      }
      if (kind === "transcribe") {
        onTranscribeStateChange?.(false, "READY");
      }
      setBusyKind(null);
      onCompleted();
    } catch (err) {
      if (kind === "transcribe") {
        onTranscribeStateChange?.(false, "FAILED");
      }
      setBusyKind(null);
      const code = err instanceof ApiRequestError ? err.code : undefined;
      const rawServerMsg =
        err instanceof ApiRequestError
          ? (err.technicalMessage || err.message || "").trim()
          : "";
      const meaningfulServerMsg =
        rawServerMsg &&
        rawServerMsg !== "Request failed" &&
        rawServerMsg !== "The local service rejected this request." &&
        !/^HTTP \d+/i.test(rawServerMsg)
          ? rawServerMsg
          : "";
      if (code === "CLOUD_CREDENTIAL_MISSING") {
        setError(
          zh
            ? "当前选为云端模式但尚未填写 API Key，请在设置中保存 Key 或切回本机免费 Ollama。"
            : "Cloud API key is missing in Settings.",
        );
        setErrorAction({
          label: zh ? "前往模型设置 →" : "Open model settings →",
          href: "#Settings",
        });
      } else if (code === "TRANSCRIBER_UNAVAILABLE") {
        setError(
          meaningfulServerMsg ||
            (zh
              ? "未检测到本机离线语音转写模型，请先前往设置配置。"
              : "Local offline transcription model is not configured."),
        );
        setErrorAction({
          label: zh ? "先设置本地转写 →" : "Set up local transcription →",
          href: "#Settings/transcription",
        });
      } else if (code === "TRANSCRIPT_REQUIRED") {
        setError(
          meaningfulServerMsg ||
            (zh
              ? "当前内容尚未生成可用字幕，无法直接提炼。"
              : "A transcript is required before distilling."),
        );
        setErrorAction(
          isLocalMedia
            ? {
                label: zh ? "先设置本地转写 →" : "Set up local transcription →",
                href: "#Settings/transcription",
              }
            : null,
        );
      } else if (code === "LOCAL_SOURCE_UNTRUSTED" || code === "LOCAL_NOT_MEDIA") {
        setError(
          meaningfulServerMsg ||
            (zh ? "当前本地内容暂不支持此操作。" : "This local item cannot run this action."),
        );
        setErrorAction(null);
      } else {
        const fallback =
          kind === "transcribe"
            ? zh
              ? "本地离线语音转写未能完成，请检查本地转写模型与音视频文件。"
              : "Offline local transcription could not complete."
            : zh
              ? "AI 中文提炼未能完成，请检查本机 Ollama 或云端引擎配置。"
              : "AI distillation could not complete.";
        setError(meaningfulServerMsg || fallback);
        setErrorAction(
          kind === "transcribe"
            ? {
                label: zh ? "查看转写设置 →" : "Transcription settings →",
                href: "#Settings/transcription",
              }
            : !meaningfulServerMsg || /ollama|model|模型|cloud|云端/i.test(`${code ?? ""} ${meaningfulServerMsg}`)
              ? {
                  label: zh ? "前往模型设置 →" : "Open model settings →",
                  href: "#Settings",
                }
              : null,
        );
      }
    }
  };

  useEffect(() => {
    if (!actionRequest || actionRequest.nonce === handledNonceRef.current) return;
    handledNonceRef.current = actionRequest.nonce;
    void runAction(actionRequest.kind);
  }, [actionRequest]);

  const transcribeActionNode =
    isLocalMedia && !transcriptAvailable ? (
      transcriberReady === false && busyKind === null ? (
        <a className="button button-secondary button-small" href="#Settings/transcription">
          <PhosphorIcon name="sparkle" size={13} />
          {zh ? "先设置本地转写 →" : "Set up local transcription →"}
        </a>
      ) : (
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
            ? transcribeStage === "DISTILLING"
              ? zh
                ? "语音听写完成，正在提炼中文洞察…"
                : "Distilling Chinese insight…"
              : zh
                ? "正在离线转写语音（长视频约需数分钟）…"
                : "Transcribing & distilling…"
            : zh
              ? "离线语音转写并提炼中文洞察"
              : "Transcribe offline & distill Chinese insight"}
        </button>
      )
    ) : null;

  const distillActionNode = transcriptAvailable ? (
    <button
      type="button"
      className={`button button-small ${aiBrief ? "button-ghost" : "button-primary"}`}
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
          : "Distilling AI summary…"
        : aiBrief
          ? zh
            ? "AI 重新提炼中文总结"
            : "Re-distill AI brief"
          : zh
            ? "AI 提炼中文总结与洞察"
            : "Distill AI brief"}
    </button>
  ) : canMetadataPreview ? (
    <button
      type="button"
      className={`button button-small ${aiBrief ? "button-ghost" : "button-secondary"}`}
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
  ) : null;

  const hasExportGroup = Boolean(mdContent || aiBrief || legacyCopyNode);
  const hasSecondaryFooter = Boolean(sourceLinkNode || (aiBrief && distillActionNode));

  return (
    <>
      <div className="reader-action-primary">
        <div className="reader-action-flow">
          {!aiBrief ? (
            <>
              {transcribeActionNode}
              {distillActionNode}
            </>
          ) : (
            <>
              {transcribeActionNode}
              {nextUnreadVideo && onAdvanceToVideo ? (
                <button
                  type="button"
                  className="button button-primary button-small tabular-nums"
                  disabled={busyKind !== null}
                  aria-label={zh ? "标已读并看下一篇" : "Mark read & open next unread"}
                  title={
                    nextUnreadVideo.scoped
                      ? zh
                        ? `本筛选下一篇未读：${nextUnreadVideo.title}`
                        : `Next unread in filter: ${nextUnreadVideo.title}`
                      : zh
                        ? `下一篇未读：${nextUnreadVideo.title}`
                        : `Next unread: ${nextUnreadVideo.title}`
                  }
                  onClick={(event) => {
                    pulseCelebration(event.currentTarget);
                    void markReadAndAdvance();
                  }}
                >
                  <PhosphorIcon name="caret-right" size={13} />
                  {nextUnreadVideo.scoped
                    ? zh
                      ? `标已读并看下一篇 (本筛选 ${nextUnreadVideo.remainingCount})`
                      : `Mark read & next (${nextUnreadVideo.remainingCount} in filter)`
                    : zh
                      ? `标已读并看下一篇 (${nextUnreadVideo.remainingCount})`
                      : `Mark read & next (${nextUnreadVideo.remainingCount})`}
                </button>
              ) : null}
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
          )}
        </div>
        {hasExportGroup ? (
          <div className="reader-export-group">
            {legacyCopyNode}
            {mdContent ? (
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
            ) : null}
            {aiBrief ? (
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={(event) => {
                  pulseCelebration(event.currentTarget);
                  void navigator.clipboard?.writeText(
                    formatPlainTextVideoBrief(aiBrief, title || videoId, {
                      channelName,
                      sourceUrl,
                      zh,
                    }),
                  );
                  setCopiedPlainBrief(true);
                  setTimeout(() => setCopiedPlainBrief(false), 2200);
                }}
              >
                <PhosphorIcon name="quotes" size={13} />
                {copiedPlainBrief
                  ? zh
                    ? "已复制纯文本摘要"
                    : "Copied plain-text summary"
                  : zh
                    ? "复制纯文本摘要"
                    : "Copy plain-text summary"}
              </button>
            ) : null}
            {mdContent ? (
              <button
                type="button"
                className="button button-ghost button-small"
                onClick={() => downloadObsidianMarkdown(title || videoId, mdContent)}
              >
                {zh ? "下载 .md" : "Download .md"}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
      {hasSecondaryFooter ? (
        <div className="reader-action-secondary">
          {sourceLinkNode}
          {aiBrief ? distillActionNode : null}
          {aiBrief ? (
            <span className="kb-shortcut-hint" aria-hidden="true">
              {zh ? "快捷键：S 收藏 · E 已读下一篇 · U 返回" : "Keys: S star · E read/next · U back"}
            </span>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          <span>{error}</span>
          {errorAction ? (
            <>
              {" "}
              <a className="source-link" href={errorAction.href}>
                {errorAction.label}
              </a>
            </>
          ) : null}
        </p>
      ) : null}
    </>
  );
}

export function WorkspaceVideoAiBriefCard({
  brief,
  obsidianMarkdown,
  onSelectTopicCluster,
}: {
  brief: VideoAiBrief | null;
  obsidianMarkdown?: string;
  onSelectTopicCluster?: (topicCluster: string) => void;
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
          onSelectTopicCluster ? (
            <button
              type="button"
              className="ai-topic-tag ai-topic-tag-btn"
              title={zh ? `查看专题脉络：${brief.topic_cluster_zh}` : `Open Topic: ${brief.topic_cluster_zh}`}
              onClick={() => onSelectTopicCluster(brief.topic_cluster_zh)}
            >
              {brief.topic_cluster_zh}
            </button>
          ) : (
            <span className="ai-topic-tag">{brief.topic_cluster_zh}</span>
          )
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

const FRAME_KIND_LABELS: Record<string, { zh: string; en: string }> = {
  SLIDE: { zh: "PPT", en: "Slide" },
  CHART: { zh: "图表", en: "Chart" },
  CODE: { zh: "代码", en: "Code" },
  DEMO: { zh: "演示", en: "Demo" },
  ARCHITECTURE: { zh: "架构图", en: "Diagram" },
  SPEAKER: { zh: "讲者", en: "Speaker" },
  OTHER: { zh: "画面", en: "Frame" },
};

export function WorkspaceVisualKeyframePanel({
  videoId,
  isLocalVideo,
  ffmpegAvailable,
  visualAnalysis,
  onCompleted,
}: {
  videoId: string;
  isLocalVideo: boolean;
  ffmpegAvailable?: boolean;
  visualAnalysis: VideoVisualAnalysis | null;
  onCompleted: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [localAnalysis, setLocalAnalysis] = useState<VideoVisualAnalysis | null>(
    visualAnalysis,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorAction, setErrorAction] = useState<{ label: string; href: string } | null>(
    null,
  );
  const [informativeOnly, setInformativeOnly] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const lightboxRef = useRef<HTMLDivElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const prevActiveIndexRef = useRef<number | null>(null);

  const analysisKey = visualAnalysis
    ? `${visualAnalysis.video_id}|${visualAnalysis.updated_at}|${visualAnalysis.frame_count}`
    : "";

  useEffect(() => {
    setLocalAnalysis(visualAnalysis);
  }, [visualAnalysis]);

  useEffect(() => {
    setError(null);
    setErrorAction(null);
    setActiveIndex(null);
    setInformativeOnly(false);
  }, [videoId, analysisKey]);

  const analysis = localAnalysis ?? visualAnalysis;
  const allFrames = analysis?.frames ?? [];
  const hasSpeakerFrames = allFrames.some((f) => !f.has_visual_info);
  const hasInformativeFrames = allFrames.some((f) => f.has_visual_info);
  const canToggleFilter = hasSpeakerFrames && hasInformativeFrames;
  const visibleFrames =
    informativeOnly && canToggleFilter
      ? allFrames.filter((f) => f.has_visual_info)
      : allFrames;

  useEffect(() => {
    const prev = prevActiveIndexRef.current;
    prevActiveIndexRef.current = activeIndex;
    if (prev === null && activeIndex !== null) {
      if (
        returnFocusRef.current === null &&
        typeof document !== "undefined" &&
        document.activeElement instanceof HTMLElement
      ) {
        returnFocusRef.current = document.activeElement;
      }
      closeBtnRef.current?.focus();
    } else if (prev !== null && activeIndex === null) {
      returnFocusRef.current?.focus();
      returnFocusRef.current = null;
    }
  }, [activeIndex]);

  useEffect(() => {
    if (activeIndex === null) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        setActiveIndex(null);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        setActiveIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : prev));
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setActiveIndex((prev) =>
          prev !== null && prev < visibleFrames.length - 1 ? prev + 1 : prev,
        );
      } else if (event.key === "Tab" && lightboxRef.current) {
        const focusables = Array.from(
          lightboxRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])',
          ),
        );
        if (focusables.length === 0) {
          event.preventDefault();
          lightboxRef.current.focus();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        if (event.shiftKey) {
          if (active === first || !lightboxRef.current.contains(active)) {
            event.preventDefault();
            last.focus();
          }
        } else if (active === last || !lightboxRef.current.contains(active)) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [activeIndex, visibleFrames.length]);

  if (!isLocalVideo && !analysis) {
    return null;
  }

  const runVisualAnalysis = async () => {
    if (busy || ffmpegAvailable === false) return;
    setBusy(true);
    setError(null);
    setErrorAction(null);
    try {
      const res = await post<{ analysis?: unknown }>(
        `/workspace-ai/videos/${encodeURIComponent(videoId)}/visual-analysis`,
        {},
      );
      const parsed = readVideoVisualAnalysis(res?.analysis);
      if (parsed) {
        setLocalAnalysis(parsed);
      }
      onCompleted();
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : undefined;
      const serverMsg =
        err instanceof ApiRequestError
          ? (err.technicalMessage || err.message || "").trim()
          : "";
      if (code === "LOCAL_VISION_MODEL_UNSUPPORTED") {
        setError(
          serverMsg ||
            (zh
              ? "当前本机模型暂不支持图片视觉解读，请在设置中切换至支持视觉的模型（如 gemma3:4b 或 qwen3.5:9b）。"
              : "Current local Ollama model does not support vision inputs. Switch to a vision model such as gemma3:4b or qwen3.5:9b in Settings."),
        );
        setErrorAction({
          label: zh ? "前往模型设置切换视觉模型 →" : "Switch vision model in Settings →",
          href: "#Settings",
        });
      } else if (
        code === "CLOUD_DAILY_BUDGET_EXCEEDED" ||
        code === "CLOUD_ENDPOINT_REAUTH_REQUIRED" ||
        code === "CLOUD_CREDENTIAL_MISSING"
      ) {
        setError(
          serverMsg ||
            (zh
              ? "云端视觉分析已受预算或安全凭据门禁阻断，请先检查设置。"
              : "Cloud vision call blocked by budget or credential safety guard."),
        );
        setErrorAction({
          label: zh ? "查看引擎与预算设置 →" : "Open engine & budget settings →",
          href: "#Settings",
        });
      } else if (code === "VISUAL_FFMPEG_UNAVAILABLE") {
        setError(
          serverMsg ||
            (zh
              ? "未检测到系统 ffmpeg，请安装 ffmpeg 后再试。"
              : "Trusted ffmpeg executable was not found."),
        );
        setErrorAction(null);
      } else {
        setError(
          serverMsg ||
            (zh
              ? "关键画面与视觉融合分析未完成，请确认模型服务运行正常后重试。"
              : "Could not complete visual keyframe analysis."),
        );
        setErrorAction({
          label: zh ? "前往模型设置 →" : "Open model settings →",
          href: "#Settings",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const activeFrame =
    activeIndex !== null && activeIndex >= 0 && activeIndex < visibleFrames.length
      ? visibleFrames[activeIndex]
      : null;

  const packHref = `/api/v1/workspace-ai/videos/${encodeURIComponent(videoId)}/visual-pack.zip`;

  return (
    <section
      className="visual-keyframe-panel"
      aria-label={zh ? "关键画面与字幕融合分析" : "Visual Keyframe & Transcript Fusion"}
    >
      {!analysis ? (
        <div className="visual-keyframe-idle">
          <div className="visual-keyframe-idle-copy">
            <h3 className="visual-keyframe-heading">
              {zh ? "关键画面与字幕融合分析" : "Key Video Frames & Transcript Fusion"}
            </h3>
            <p className="visual-keyframe-subcopy">
              {ffmpegAvailable === false
                ? zh
                  ? "未检测到本机 ffmpeg，安装 ffmpeg 后即可按场景切换自动提取 PPT/架构图关键帧。"
                  : "Install ffmpeg to enable scene-change keyframe extraction."
                : zh
                  ? "仅针对当前视频按需抽帧并去重，结合原话字幕识别 PPT、图表与架构细节（零后台静默扣费）。"
                  : "On-demand scene keyframe extraction fused with spoken transcript context (zero background spend)."}
            </p>
          </div>
          <div className="visual-keyframe-actions">
            <button
              type="button"
              className="button button-secondary button-small"
              disabled={busy || ffmpegAvailable === false}
              onClick={(event) => {
                pulseCelebration(event.currentTarget);
                void runVisualAnalysis();
              }}
            >
              <PhosphorIcon name="sparkle" size={13} />
              {busy
                ? zh
                  ? "正在提取关键画面并融合解读…"
                  : "Extracting frames & analyzing…"
                : zh
                  ? "结合画面分析关键帧"
                  : "Analyze key frames"}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="visual-keyframe-header">
            <div className="visual-keyframe-title-row">
              <h3 className="visual-keyframe-heading">
                {zh ? "关键画面与字幕融合解读" : "Key Frames & Visual Insights"}
              </h3>
              <span className="visual-keyframe-meta-pill">
                {zh
                  ? `${analysis.frame_count} 帧 · ${analysis.informative_frame_count} 帧含 PPT/图表`
                  : `${analysis.frame_count} frames · ${analysis.informative_frame_count} visual`}
              </span>
              {analysis.model ? (
                <span className="ai-topic-tag">
                  {analysis.provider}/{analysis.model}
                </span>
              ) : null}
            </div>
            <div className="visual-keyframe-actions">
              {canToggleFilter ? (
                <button
                  type="button"
                  className="button button-ghost button-small"
                  aria-pressed={informativeOnly}
                  onClick={() => {
                    setActiveIndex(null);
                    setInformativeOnly((prev) => !prev);
                  }}
                >
                  {informativeOnly
                    ? zh
                      ? "显示全部帧"
                      : "Show all frames"
                    : zh
                      ? "仅看含 PPT/图表帧"
                      : "Slides & charts only"}
                </button>
              ) : null}
              <a
                className="button button-secondary button-small"
                href={packHref}
                download
              >
                <PhosphorIcon name="stack" size={13} />
                {zh ? "下载带图笔记包 (.zip)" : "Download visual pack (.zip)"}
              </a>
              <button
                type="button"
                className="button button-ghost button-small"
                disabled={busy || ffmpegAvailable === false}
                onClick={() => void runVisualAnalysis()}
              >
                {busy
                  ? zh
                    ? "正在提取关键画面并融合解读…"
                    : "Re-analyzing frames…"
                  : zh
                    ? "重新分析画面"
                    : "Re-analyze frames"}
              </button>
            </div>
          </div>

          <div className="visual-keyframe-summary">
            <p className="visual-keyframe-summary-text">{analysis.visual_summary_zh}</p>
            {analysis.visual_takeaways_zh.length > 0 ? (
              <ul className="visual-keyframe-takeaways">
                {analysis.visual_takeaways_zh.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>

          <div className="visual-keyframe-grid">
            {visibleFrames.map((frame, idx) => {
              const kindEntry = FRAME_KIND_LABELS[frame.frame_kind] ?? FRAME_KIND_LABELS.OTHER;
              const kindLabel = zh ? kindEntry.zh : kindEntry.en;
              return (
                <button
                  key={frame.frame_id}
                  type="button"
                  className="visual-keyframe-card"
                  onClick={(e) => {
                    returnFocusRef.current = e.currentTarget;
                    setActiveIndex(idx);
                  }}
                >
                  <div className="visual-keyframe-thumb-wrap">
                    <img
                      className="visual-keyframe-thumb"
                      src={frame.image_url}
                      alt={`${frame.timestamp_label} ${frame.title_zh}`}
                      loading="lazy"
                    />
                    <span className="visual-keyframe-timecode">{frame.timestamp_label}</span>
                    <span className="visual-keyframe-kind-badge">{kindLabel}</span>
                  </div>
                  <div className="visual-keyframe-card-body">
                    <p className="visual-keyframe-card-title">{frame.title_zh}</p>
                    <p className="visual-keyframe-card-detail">{frame.visual_detail_zh}</p>
                    {frame.transcript_fusion_zh ? (
                      <p className="visual-keyframe-card-fusion">
                        {frame.transcript_fusion_zh}
                      </p>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}

      {error ? (
        <p className="form-error" role="alert">
          <span>{error}</span>
          {errorAction ? (
            <>
              {" "}
              <a className="source-link" href={errorAction.href}>
                {errorAction.label}
              </a>
            </>
          ) : null}
        </p>
      ) : null}

      {activeFrame !== null && activeIndex !== null ? (
        <div
          className="visual-keyframe-lightbox-backdrop"
          onClick={() => setActiveIndex(null)}
        >
          <div
            ref={lightboxRef}
            tabIndex={-1}
            className="visual-keyframe-lightbox"
            role="dialog"
            aria-modal="true"
            aria-labelledby="visual-lightbox-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="visual-keyframe-lightbox-head">
              <h4 id="visual-lightbox-title" className="visual-keyframe-lightbox-title">
                [{activeFrame.timestamp_label}] {activeFrame.title_zh}
              </h4>
              <button
                ref={closeBtnRef}
                type="button"
                className="button button-ghost button-small"
                onClick={() => setActiveIndex(null)}
              >
                {zh ? "关闭 (Esc)" : "Close (Esc)"}
              </button>
            </div>
            <img
              className="visual-keyframe-lightbox-img"
              src={activeFrame.image_url}
              alt={`${activeFrame.timestamp_label} ${activeFrame.title_zh}`}
            />
            <div className="visual-keyframe-lightbox-meta">
              <p className="visual-keyframe-card-detail">
                <strong>{zh ? "画面信息：" : "Visual: "}</strong>
                {activeFrame.visual_detail_zh}
              </p>
              {activeFrame.transcript_fusion_zh ? (
                <p className="visual-keyframe-card-detail">
                  <strong>{zh ? "音画融合：" : "Transcript fusion: "}</strong>
                  {activeFrame.transcript_fusion_zh}
                </p>
              ) : null}
              {activeFrame.nearby_transcript ? (
                <p className="visual-keyframe-card-fusion">
                  <strong>{zh ? "附近原话字幕：" : "Nearby transcript: "}</strong>
                  {activeFrame.nearby_transcript}
                </p>
              ) : null}
            </div>
            <div className="visual-keyframe-lightbox-nav">
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={activeIndex <= 0}
                onClick={() =>
                  setActiveIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : prev))
                }
              >
                {zh ? "← 上一帧" : "← Previous"}
              </button>
              <span className="visual-keyframe-meta-pill">
                {activeIndex + 1} / {visibleFrames.length}
              </span>
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={activeIndex >= visibleFrames.length - 1}
                onClick={() =>
                  setActiveIndex((prev) =>
                    prev !== null && prev < visibleFrames.length - 1 ? prev + 1 : prev,
                  )
                }
              >
                {zh ? "下一帧 →" : "Next →"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function formatPlainTextTopicBrief(
  topicName: string,
  evo: TopicAiEvolution,
  zh: boolean,
): string {
  const stripWiki = (text: string) =>
    text.replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target: string, alias?: string) => (alias ?? target).trim(),
    );
  const lines: string[] = [];
  lines.push(
    zh
      ? `【专题脉络总览】${stripWiki(topicName.trim())}`
      : `[Topic Synthesis] ${stripWiki(topicName.trim())}`,
  );
  const statParts = [
    zh ? `${evo.video_count} 篇相关内容` : `${evo.video_count} items`,
    zh ? `${evo.must_watch_count} 篇必看干货` : `${evo.must_watch_count} must-watch`,
    evo.avg_score !== null
      ? zh
        ? `平均评分 ${evo.avg_score.toFixed(1)}/10`
        : `Avg ${evo.avg_score.toFixed(1)}/10`
      : "",
    evo.source_channels.length > 0
      ? zh
        ? `来源：${evo.source_channels.join("、")}`
        : `Sources: ${evo.source_channels.join(", ")}`
      : "",
  ].filter(Boolean);
  lines.push(
    zh ? `聚合规模：${statParts.join(" · ")}` : `Coverage: ${statParts.join(" · ")}`,
  );
  const synthesisText = stripWiki(
    (evo.synthesis_zh || evo.latest_headline_zh || "").trim(),
  );
  if (synthesisText) {
    lines.push(
      zh
        ? `核心共识与脉络：\n${synthesisText}`
        : `Synthesis:\n${synthesisText}`,
    );
  }
  if (evo.top_opportunities_zh.length > 0) {
    lines.push(
      [
        zh ? "高优产品与变现切口：" : "Top opportunities:",
        ...evo.top_opportunities_zh.map((opp) => `• ${stripWiki(opp.trim())}`),
      ].join("\n"),
    );
  }
  if (evo.entries.length > 0) {
    lines.push(
      [
        zh ? "代表性收录内容：" : "Key entries:",
        ...evo.entries.slice(0, 8).map((entry, idx) => {
          const titlePart = zh
            ? `《${stripWiki(entry.title.trim())}》`
            : `"${stripWiki(entry.title.trim())}"`;
          const meta = [
            entry.channel_name?.trim() ? stripWiki(entry.channel_name.trim()) : "",
            `${entry.score.toFixed(1)}/10`,
          ]
            .filter(Boolean)
            .join(" · ");
          const headline = stripWiki(entry.headline_zh.trim());
          return headline
            ? `${idx + 1}. ${titlePart}（${meta}）：${headline}`
            : `${idx + 1}. ${titlePart}（${meta}）`;
        }),
      ].join("\n"),
    );
  }
  return lines.join("\n\n");
}

export function TopicObsidianExportBar({
  topicName,
  obsidianMarkdown,
  evolution,
}: {
  topicName: string;
  obsidianMarkdown: string;
  evolution?: TopicAiEvolution | null;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [copied, setCopied] = useState(false);
  const [copiedPlain, setCopiedPlain] = useState(false);

  useEffect(() => {
    setCopied(false);
    setCopiedPlain(false);
  }, [topicName]);

  if (!obsidianMarkdown.trim() && !evolution) return null;

  return (
    <div className="topic-moc-export-box">
      <div className="button-row">
        {evolution ? (
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void navigator.clipboard?.writeText(
                formatPlainTextTopicBrief(topicName, evolution, zh),
              );
              setCopiedPlain(true);
              setTimeout(() => setCopiedPlain(false), 2200);
            }}
          >
            <PhosphorIcon name="quotes" size={13} />
            {copiedPlain
              ? zh
                ? "已复制纯文本专题提纲"
                : "Copied plain-text outline"
              : zh
                ? "复制纯文本专题提纲"
                : "Copy plain-text outline"}
          </button>
        ) : null}
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
  "基于当前内容库，不同来源在核心方法论上有哪些主要共识与关键分歧？",
  "从已沉淀的高分内容中，提炼最值得优先落地的 3 个产品方向或工程实践是什么？",
  "跨来源原话指出了哪些高频避坑点、边界条件或前置假设？",
];

const FALLBACK_QUESTIONS_EN = [
  "What are the main points of consensus and disagreement across sources in my library?",
  "What are the top 3 actionable product or engineering takeaways from my highest-rated items?",
  "Which common pitfalls or boundary conditions appear across multiple sources?",
];

function buildDynamicFallbackQuestions(
  scopes: ResearchScopeOptions | null,
  zh: boolean,
): string[] {
  const defaults = zh ? FALLBACK_QUESTIONS_ZH : FALLBACK_QUESTIONS_EN;
  if (!scopes) return defaults;
  const out: string[] = [];
  if (scopes.channels.length >= 2) {
    out.push(
      zh
        ? `${scopes.channels[0].label} 与 ${scopes.channels[1].label} 在核心观点上有哪些共识与分歧？`
        : `How do ${scopes.channels[0].label} and ${scopes.channels[1].label} agree or differ in key conclusions?`,
    );
  } else if (scopes.channels.length === 1) {
    out.push(
      zh
        ? `梳理 ${scopes.channels[0].label} 已沉淀内容中的核心方法论与可落地结论`
        : `Summarize the core methodology and actionable takeaways from ${scopes.channels[0].label}`,
    );
  }
  if (scopes.topic_clusters.length >= 1) {
    out.push(
      zh
        ? `围绕「${scopes.topic_clusters[0].name}」专题，综合各来源给出落地建议与避坑指南`
        : `Synthesize practical takeaways and pitfalls across sources in "${scopes.topic_clusters[0].name}"`,
    );
  }
  for (const q of defaults) {
    if (out.length >= 3) break;
    if (!out.includes(q)) out.push(q);
  }
  return out;
}

export function formatPlainTextResearchBrief(
  session: AiResearchSession,
  zh: boolean,
): string {
  const stripWiki = (text: string) =>
    text.replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target: string, alias?: string) => (alias ?? target).trim(),
    );
  const lines: string[] = [];
  lines.push(
    zh
      ? `【跨视频深度问答】${stripWiki(session.question.trim())}`
      : `[Cross-Video Q&A] ${stripWiki(session.question.trim())}`,
  );
  if (session.scope_label_zh?.trim()) {
    lines.push(
      zh
        ? `检索范围：${stripWiki(session.scope_label_zh.trim())}`
        : `Scope: ${stripWiki(session.scope_label_zh.trim())}`,
    );
  }
  if (session.answer_zh.trim()) {
    lines.push(
      zh
        ? `核心结论：\n${stripWiki(session.answer_zh.trim())}`
        : `Answer:\n${stripWiki(session.answer_zh.trim())}`,
    );
  }
  if (session.key_takeaways_zh.length > 0) {
    lines.push(
      [
        zh ? "关键要点：" : "Key takeaways:",
        ...session.key_takeaways_zh.map((item) => `• ${stripWiki(item.trim())}`),
      ].join("\n"),
    );
  }
  if (session.action_items_zh.length > 0) {
    lines.push(
      [
        zh ? "可执行动作：" : "Action items:",
        ...session.action_items_zh.map(
          (item, idx) => `${idx + 1}. ${stripWiki(item.trim())}`,
        ),
      ].join("\n"),
    );
  }
  if (session.citations.length > 0) {
    lines.push(
      [
        zh ? "原话时间轴出处：" : "Verified citations:",
        ...session.citations.map((c) => {
          const meta = [c.channel_name?.trim(), c.timestamp_label?.trim()]
            .filter(Boolean)
            .join(" · ");
          const titlePart = zh
            ? `《${stripWiki(c.video_title.trim())}》`
            : `"${stripWiki(c.video_title.trim())}"`;
          const metaPart = meta ? (zh ? `（${meta}）` : ` (${meta})`) : "";
          const urlPart = c.citation_url?.trim() ? ` (${c.citation_url.trim()})` : "";
          const cleanQuote = stripWiki((c.excerpt ?? "").replace(/\s+/g, " ").trim());
          return cleanQuote
            ? `- [${c.ref_label}] ${titlePart}${metaPart}${urlPart}："${cleanQuote}"`
            : `- [${c.ref_label}] ${titlePart}${metaPart}${urlPart}`;
        }),
      ].join("\n"),
    );
  }
  return lines.join("\n\n");
}

export function WorkspaceAiResearchPanel({
  onOpen,
  onAiReady,
  onOpenImport,
  handoffSeq,
}: {
  onOpen: OpenResearchSource;
  onAiReady?: () => void;
  onOpenImport?: () => void;
  handoffSeq?: number;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [sessions, setSessions] = useState<AiResearchSession[]>([]);
  const [suggested, setSuggested] = useState<string[]>(() =>
    zh ? FALLBACK_QUESTIONS_ZH : FALLBACK_QUESTIONS_EN,
  );
  const [scopeOptions, setScopeOptions] = useState<ResearchScopeOptions | null>(null);
  const [scopeLoaded, setScopeLoaded] = useState(false);
  const initialPendingRef = useRef<{
    videoIds: string[];
    topic: string;
    channel: string;
    starredOnly: boolean;
    draftQuestion: string;
  } | null>(null);
  if (initialPendingRef.current === null) {
    const rawVids = consumePendingResearchVideoIds();
    const rawTopic = consumePendingResearchTopicCluster();
    const rawChannel = consumePendingResearchChannel();
    const rawStarred = consumePendingResearchStarredOnly();
    const rawDraft = consumePendingResearchDraftQuestion();
    if (rawVids.length > 0) {
      initialPendingRef.current = { videoIds: rawVids, topic: "", channel: "", starredOnly: false, draftQuestion: rawDraft };
    } else if (rawTopic) {
      initialPendingRef.current = { videoIds: [], topic: rawTopic, channel: "", starredOnly: false, draftQuestion: rawDraft };
    } else if (rawChannel) {
      initialPendingRef.current = { videoIds: [], topic: "", channel: rawChannel, starredOnly: false, draftQuestion: rawDraft };
    } else {
      initialPendingRef.current = { videoIds: [], topic: "", channel: "", starredOnly: rawStarred, draftQuestion: rawDraft };
    }
  }
  const [selectedChannel, setSelectedChannel] = useState(
    () => initialPendingRef.current?.channel ?? "",
  );
  const [selectedTopic, setSelectedTopic] = useState(
    () => initialPendingRef.current?.topic ?? "",
  );
  const [starredOnly, setStarredOnly] = useState(
    () => initialPendingRef.current?.starredOnly ?? false,
  );
  const pendingSessionIdRef = useRef<string>("");
  const hasInitialVideosHandoffRef = useRef<boolean>(
    (initialPendingRef.current?.videoIds.length ?? 0) > 0 ||
      Boolean(initialPendingRef.current?.draftQuestion),
  );
  const [comparePickerOpen, setComparePickerOpen] = useState(
    () => (initialPendingRef.current?.videoIds.length ?? 0) > 0,
  );
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>(
    () => initialPendingRef.current?.videoIds ?? [],
  );
  const [compareSelectedOnly, setCompareSelectedOnly] = useState(
    () => (initialPendingRef.current?.videoIds.length ?? 0) > 0,
  );
  const [compareSearch, setCompareSearch] = useState("");
  const [activeSession, setActiveSession] = useState<AiResearchSession | null>(null);
  const [questionInput, setQuestionInput] = useState(
    () => initialPendingRef.current?.draftQuestion ?? "",
  );
  const [followUpNotice, setFollowUpNotice] = useState<string | null>(null);
  const [sessionSearch, setSessionSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionMutatingId, setSessionMutatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedPlain, setCopiedPlain] = useState(false);
  const questionInputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const el = questionInputRef.current;
    if (!el) return;
    el.style.height = "auto";
    if (el.scrollHeight > 0) {
      el.style.height = `${Math.min(el.scrollHeight, 116)}px`;
    }
  }, [questionInput]);

  useEffect(() => {
    setCopied(false);
    setCopiedPlain(false);
  }, [activeSession?.session_id]);

  const resetCompareUi = () => {
    setComparePickerOpen(false);
    setCompareSelectedOnly(false);
    setCompareSearch("");
  };

  const applyVideoCompareScope = (ids: string[]) => {
    setStarredOnly(false);
    setSelectedChannel("");
    setSelectedTopic("");
    setSelectedVideoIds(ids);
    setComparePickerOpen(true);
    setCompareSelectedOnly(true);
    setCompareSearch("");
    queueMicrotask(() => questionInputRef.current?.focus());
  };

  const applyChannelScope = (channelKey: string) => {
    setSelectedVideoIds([]);
    setSelectedTopic("");
    setStarredOnly(false);
    resetCompareUi();
    setSelectedChannel(channelKey);
    queueMicrotask(() => questionInputRef.current?.focus());
  };

  const applyTopicScope = (topicCluster: string) => {
    setSelectedVideoIds([]);
    setSelectedChannel("");
    setStarredOnly(false);
    resetCompareUi();
    setSelectedTopic(topicCluster);
    queueMicrotask(() => questionInputRef.current?.focus());
  };

  const applyStarredScope = (enabled: boolean) => {
    setSelectedVideoIds([]);
    setSelectedChannel("");
    setSelectedTopic("");
    resetCompareUi();
    setStarredOnly(enabled);
    queueMicrotask(() => questionInputRef.current?.focus());
  };

  const resetAllScopes = () => {
    setStarredOnly(false);
    setSelectedChannel("");
    setSelectedTopic("");
    setSelectedVideoIds([]);
    resetCompareUi();
  };

  useEffect(() => {
    const nextSid = consumePendingResearchSessionId();
    if (nextSid) {
      pendingSessionIdRef.current = nextSid;
    }
    const wantedSid = pendingSessionIdRef.current;
    if (wantedSid && sessions.length > 0) {
      const matched = sessions.find((s) => s.session_id === wantedSid);
      if (matched) {
        setActiveSession(matched);
        pendingSessionIdRef.current = "";
      }
    }
    const nextVids = consumePendingResearchVideoIds();
    const nextCh = consumePendingResearchChannel();
    const nextTp = consumePendingResearchTopicCluster();
    const nextStarred = consumePendingResearchStarredOnly();
    const nextDraft = consumePendingResearchDraftQuestion();
    if (nextDraft) {
      setQuestionInput(nextDraft);
      setFollowUpNotice(
        zh
          ? "已锁定对比来源并填入预设问题，可直接按 Enter 发送或自由微调。"
          : "Comparison scope locked & prompt filled — edit or press Enter to ask.",
      );
    }
    if (nextVids.length > 0) {
      applyVideoCompareScope(nextVids);
    } else if (nextTp) {
      applyTopicScope(nextTp);
    } else if (nextCh) {
      applyChannelScope(nextCh);
    } else if (nextStarred) {
      applyStarredScope(true);
    } else if (nextDraft || hasInitialVideosHandoffRef.current) {
      hasInitialVideosHandoffRef.current = false;
      queueMicrotask(() => questionInputRef.current?.focus());
    }
  }, [handoffSeq, sessions]);

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
        if (parsedSessions.length > 0) {
          const wantedId = pendingSessionIdRef.current;
          const matched = wantedId
            ? parsedSessions.find((s) => s.session_id === wantedId)
            : undefined;
          if (matched) {
            pendingSessionIdRef.current = "";
          }
          setActiveSession((prev) => matched ?? prev ?? parsedSessions[0]);
        }
        if (parsedScopes) {
          setScopeOptions(parsedScopes);
          setScopeLoaded(true);
        }
        if (parsedQuestions.length > 0) {
          setSuggested(parsedQuestions);
        } else {
          setSuggested(buildDynamicFallbackQuestions(parsedScopes, zh));
        }
      })
      .catch(() => {
        /* Silently keep fallback suggestions when backend is unenriched */
      });
    return () => {
      alive = false;
    };
  }, []);

  const hasActiveScope = Boolean(
    starredOnly || selectedChannel || selectedTopic || selectedVideoIds.length > 0,
  );

  const toggleComparedVideo = (videoId: string) => {
    setSelectedVideoIds((prev) => {
      if (prev.includes(videoId)) {
        return prev.filter((id) => id !== videoId);
      }
      if (prev.length >= 12) return prev;
      setSelectedChannel("");
      setSelectedTopic("");
      setStarredOnly(false);
      return [...prev, videoId];
    });
  };

  const ask = async (qText: string, options?: { clearScope?: boolean }) => {
    const clean = qText.trim();
    if (!clean || busy) return;
    const expandAll = Boolean(options?.clearScope);
    if (expandAll) {
      resetAllScopes();
    }
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { question: clean };
      if (!expandAll) {
        if (selectedVideoIds.length > 0) {
          payload.video_ids = selectedVideoIds;
        } else {
          if (starredOnly) payload.starred_only = true;
          if (selectedChannel) payload.channel_key = selectedChannel;
          if (selectedTopic) payload.topic_cluster = selectedTopic;
        }
      }
      const res = await post<{ session?: unknown }>("/workspace-ai/research/ask", payload);
      const session = readAiResearchSession(res.session);
      if (!session) throw new Error("INVALID_SESSION");
      setActiveSession(session);
      setSessions((prev) =>
        sortResearchSessions([
          session,
          ...prev.filter((item) => item.session_id !== session.session_id),
        ]),
      );
      setQuestionInput("");
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : undefined;
      setError(
        code === "NO_GROUNDED_CONTENT" || code === "INSUFFICIENT_MATERIAL"
          ? starredOnly
            ? zh
              ? "当前已收藏清单中暂无带时间轴字幕的内容，请先在「内容」中收藏至少 1 篇深度视频，或取消「仅限已收藏」筛选。"
              : "No timed transcript content in your starred shortlist yet."
            : hasActiveScope
              ? zh
                ? "当前筛选范围内暂无带时间轴字幕的内容，请放宽来源或专题范围后重试。"
                : "No timed transcript content matched the selected scope."
              : zh
                ? "当前资料库尚无已转写视频或已核验本地文本文档（.md / .txt）可供跨来源溯源问答。"
                : "No transcribed videos or verified local text notes (.md / .txt) are available in your library yet."
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

  const togglePinSession = async (target: AiResearchSession) => {
    if (sessionMutatingId !== null) return;
    setSessionMutatingId(target.session_id);
    setError(null);
    try {
      const res = await post<{ session?: unknown }>(
        `/workspace-ai/research/sessions/${encodeURIComponent(target.session_id)}/pin`,
        { pinned: !target.pinned },
      );
      const updated =
        readAiResearchSession(res.session) ?? { ...target, pinned: !target.pinned };
      setSessions((prev) =>
        sortResearchSessions(
          prev.map((s) => (s.session_id === updated.session_id ? updated : s)),
        ),
      );
      setActiveSession((prev) =>
        prev && prev.session_id === updated.session_id ? updated : prev,
      );
    } catch {
      setError(
        zh ? "未能更新问答置顶状态，请稍后重试。" : "Could not update Q&A pin state.",
      );
    } finally {
      setSessionMutatingId(null);
    }
  };

  const deleteSession = async (target: AiResearchSession) => {
    if (sessionMutatingId !== null) return;
    setSessionMutatingId(target.session_id);
    setError(null);
    try {
      await post(
        `/workspace-ai/research/sessions/${encodeURIComponent(target.session_id)}/delete`,
        {},
      );
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.session_id !== target.session_id);
        setActiveSession((cur) =>
          cur && cur.session_id === target.session_id ? (remaining[0] ?? null) : cur,
        );
        return remaining;
      });
    } catch {
      setError(
        zh ? "未能删除该条问答记录，请稍后重试。" : "Could not delete Q&A session.",
      );
    } finally {
      setSessionMutatingId(null);
    }
  };

  const availableTopics = scopeOptions?.topic_clusters ?? [];
  const topicNames = new Set(availableTopics.map((t) => t.name));
  const candidateVideos = (scopeOptions?.videos ?? []).filter((v) => {
    if (starredOnly && v.starred === false) {
      return false;
    }
    if (selectedChannel) {
      const matchesKey = v.channel_key ? v.channel_key === selectedChannel : false;
      const matchesLabel =
        v.channel_name === selectedChannel ||
        (selectedChannel === "LOCAL" && v.channel_name === "本地实战课");
      if (!matchesKey && !matchesLabel) {
        return false;
      }
    }
    if (selectedTopic && v.topic_cluster_zh && v.topic_cluster_zh !== selectedTopic) {
      return false;
    }
    return true;
  });

  const isEmptyLibrary = Boolean(
    scopeLoaded &&
      scopeOptions !== null &&
      sessions.length === 0 &&
      scopeOptions.videos.length === 0 &&
      scopeOptions.channels.length === 0,
  );

  const showScopeBar = Boolean(
    starredOnly ||
      selectedChannel ||
      selectedTopic ||
      selectedVideoIds.length > 0 ||
      (scopeOptions &&
        (scopeOptions.starred_count > 0 ||
          scopeOptions.channels.length > 0 ||
          scopeOptions.topic_clusters.length > 0 ||
          scopeOptions.videos.length > 0)),
  );

  const activeScopeMeta = activeSession?.scope;
  const activeExplicitVideoIds = activeScopeMeta?.video_ids?.filter(Boolean) ?? [];
  const hasExplicitActiveScope = Boolean(
    activeScopeMeta &&
      (activeScopeMeta.starred_only ||
        activeScopeMeta.channel_key ||
        activeScopeMeta.topic_cluster ||
        activeExplicitVideoIds.length > 0),
  );
  const activeCitedVideoIds = Array.from(
    new Set((activeSession?.citations ?? []).map((c) => c.video_id).filter(Boolean)),
  );
  const canFollowUpActiveSession = Boolean(
    activeSession && (hasExplicitActiveScope || activeCitedVideoIds.length > 0),
  );

  const applyActiveSessionFollowUp = () => {
    if (!activeSession) return;
    if (hasExplicitActiveScope && activeScopeMeta) {
      if (activeExplicitVideoIds.length > 0) {
        applyVideoCompareScope(activeExplicitVideoIds);
      } else if (activeScopeMeta.topic_cluster) {
        applyTopicScope(activeScopeMeta.topic_cluster);
      } else if (activeScopeMeta.channel_key) {
        applyChannelScope(activeScopeMeta.channel_key);
      } else if (activeScopeMeta.starred_only) {
        applyStarredScope(true);
      } else {
        resetAllScopes();
      }
    } else if (activeCitedVideoIds.length > 0) {
      applyVideoCompareScope(activeCitedVideoIds.slice(0, 12));
    }
    questionInputRef.current?.focus();
  };

  const trimmedHistoryQuery = sessionSearch.trim().toLowerCase();
  const filteredSessions = trimmedHistoryQuery
    ? sessions.filter((s) => {
        const citeText = s.citations
          .map((c) => `${c.video_title} ${c.channel_name}`)
          .join(" ");
        return `${s.question} ${s.scope_label_zh} ${s.answer_zh} ${citeText}`
          .toLowerCase()
          .includes(trimmedHistoryQuery);
      })
    : sessions;

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
                aria-pressed={!selectedChannel && selectedVideoIds.length === 0}
                disabled={busy}
                onClick={() => {
                  applyChannelScope("");
                }}
              >
                {zh ? "全部来源" : "All sources"}
              </button>
              {scopeOptions?.channels.map((ch) => (
                <button
                  key={ch.key}
                  type="button"
                  className={`ai-question-chip tabular-nums${selectedChannel === ch.key && selectedVideoIds.length === 0 ? " is-active" : ""}`}
                  aria-pressed={selectedChannel === ch.key && selectedVideoIds.length === 0}
                  disabled={busy}
                  onClick={() => {
                    applyChannelScope(selectedChannel === ch.key ? "" : ch.key);
                  }}
                >
                  {`${ch.label} (${ch.count})`}
                </button>
              ))}
            </div>
          ) : null}

          <div className="ai-scope-secondary-row">
            {starredOnly || (scopeOptions?.starred_count ?? 0) > 0 ? (
              <button
                type="button"
                className={`ai-question-chip tabular-nums${starredOnly && selectedVideoIds.length === 0 ? " is-active" : ""}`}
                aria-pressed={starredOnly && selectedVideoIds.length === 0}
                disabled={busy}
                onClick={() => {
                  applyStarredScope(!starredOnly);
                }}
              >
                <PhosphorIcon
                  name="bookmark-simple"
                  weight={starredOnly ? "fill" : "regular"}
                  size={12}
                />
                {" "}
                {zh
                  ? `仅限已收藏 (${scopeOptions?.starred_count ?? 0})`
                  : `Starred only (${scopeOptions?.starred_count ?? 0})`}
              </button>
            ) : null}

            {availableTopics.length > 0 || selectedTopic ? (
              <label className="ai-scope-inline-field">
                <span>{zh ? "限定专题" : "Topic"}</span>
                <select
                  aria-label={zh ? "限定专题" : "Topic scope"}
                  value={selectedTopic}
                  disabled={busy}
                  onChange={(e) => {
                    applyTopicScope(e.target.value);
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

            {(scopeOptions?.videos.length ?? 0) > 0 || selectedVideoIds.length > 0 ? (
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
                  resetAllScopes();
                }}
              >
                {zh ? "重置范围" : "Reset scope"}
              </button>
            ) : null}
          </div>

          {comparePickerOpen && candidateVideos.length > 0 ? (() => {
            const effectiveSelectedOnly =
              compareSelectedOnly &&
              selectedVideoIds.length > 0 &&
              candidateVideos.some((v) => selectedVideoIds.includes(v.video_id));
            const trimmedCompareQuery = compareSearch.trim().toLowerCase();
            const visibleCompareVideos = candidateVideos.filter((v) => {
              if (effectiveSelectedOnly && !selectedVideoIds.includes(v.video_id)) {
                return false;
              }
              if (trimmedCompareQuery) {
                const hay = `${v.title ?? ""} ${v.channel_name ?? ""} ${v.topic_cluster_zh ?? ""}`.toLowerCase();
                if (!hay.includes(trimmedCompareQuery)) return false;
              }
              return true;
            });
            return (
              <div
                className="ai-video-compare-picker"
                role="group"
                aria-label={zh ? "勾选对比视频" : "Select videos to compare"}
              >
                {candidateVideos.length > 5 || selectedVideoIds.length > 0 ? (
                  <div className="ai-compare-picker-toolbar">
                    {candidateVideos.length > 5 ? (
                      <input
                        type="search"
                        className="ai-compare-search-input"
                        aria-label={zh ? "搜索候选对比视频" : "Filter candidate videos"}
                        placeholder={
                          zh ? "搜索候选视频标题或频道…" : "Filter candidate videos…"
                        }
                        value={compareSearch}
                        disabled={busy}
                        onChange={(e) => setCompareSearch(e.target.value)}
                      />
                    ) : null}
                    {selectedVideoIds.length > 0 ? (
                      <button
                        type="button"
                        className={`ai-question-chip tabular-nums${effectiveSelectedOnly ? " is-active" : ""}`}
                        aria-pressed={effectiveSelectedOnly}
                        disabled={busy}
                        onClick={() => setCompareSelectedOnly((prev) => !prev)}
                      >
                        {zh
                          ? `仅看已选 (${selectedVideoIds.length})`
                          : `Selected only (${selectedVideoIds.length})`}
                      </button>
                    ) : null}
                    {effectiveSelectedOnly &&
                    candidateVideos.length > visibleCompareVideos.length ? (
                      <button
                        type="button"
                        className="button button-ghost button-small tabular-nums"
                        disabled={busy}
                        onClick={() => setCompareSelectedOnly(false)}
                      >
                        {zh
                          ? `显示全部候选 (${candidateVideos.length})`
                          : `Show all (${candidateVideos.length})`}
                      </button>
                    ) : null}
                  </div>
                ) : null}
                <div className="ai-video-compare-list">
                  {visibleCompareVideos.length > 0 ? (
                    visibleCompareVideos.map((v) => {
                      const checked = selectedVideoIds.includes(v.video_id);
                      return (
                        <label
                          key={v.video_id}
                          className={`ai-video-compare-option${checked ? " is-checked" : ""}`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={busy}
                            onChange={() => toggleComparedVideo(v.video_id)}
                          />
                          <span className="ai-video-compare-title">{v.title}</span>
                          <small className="tabular-nums">
                            {[
                              v.channel_name,
                              v.score !== null ? v.score.toFixed(1) : null,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </small>
                        </label>
                      );
                    })
                  ) : (
                    <p className="hint ai-compare-empty-hint">
                      {zh ? "没有匹配当前搜索词的候选视频。" : "No matching candidate videos."}
                    </p>
                  )}
                </div>
              </div>
            );
          })() : null}
        </div>
      ) : null}

      {selectedVideoIds.length > 0 ? (
        <div
          className="ai-locked-videos-strip tabular-nums"
          role="status"
          aria-live="polite"
        >
          <span>
            {zh
              ? `已锁定 ${selectedVideoIds.length} 篇指定源视频进行跨视频原话对比提问`
              : `Scoped to ${selectedVideoIds.length} selected videos for grounded Q&A`}
          </span>
          <button
            type="button"
            className="button button-ghost button-small"
            disabled={busy}
            onClick={() => {
              setSelectedVideoIds([]);
              setComparePickerOpen(false);
              setCompareSelectedOnly(false);
              setCompareSearch("");
            }}
          >
            {zh ? "清空指定视频" : "Clear selected videos"}
          </button>
        </div>
      ) : null}

      {!isEmptyLibrary ? (
        <div className="ai-active-scope-readout tabular-nums" role="status">
          <PhosphorIcon name="funnel" size={12} />
          <span>
            {selectedVideoIds.length > 0
              ? zh
                ? `当前提问范围：已勾选 ${selectedVideoIds.length} 篇对比内容`
                : `Active scope: ${selectedVideoIds.length} selected items`
              : [
                  selectedChannel
                    ? `${zh ? "来源" : "Source"}「${scopeOptions?.channels.find((c) => c.key === selectedChannel)?.label ?? (selectedChannel === "LOCAL" && zh ? "本地实战课" : selectedChannel)}」`
                    : null,
                  selectedTopic
                    ? `${zh ? "专题" : "Topic"}「${selectedTopic}」`
                    : null,
                  starredOnly
                    ? zh
                      ? "仅限已收藏"
                      : "Starred only"
                    : null,
                ].filter(Boolean).length > 0
                ? `${zh ? "当前提问范围：" : "Active scope: "}${[
                    selectedChannel
                      ? `${zh ? "来源" : "Source"}「${scopeOptions?.channels.find((c) => c.key === selectedChannel)?.label ?? (selectedChannel === "LOCAL" && zh ? "本地实战课" : selectedChannel)}」`
                      : null,
                    selectedTopic
                      ? `${zh ? "专题" : "Topic"}「${selectedTopic}」`
                      : null,
                    starredOnly
                      ? zh
                        ? "仅限已收藏"
                        : "Starred only"
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}`
                : zh
                  ? `当前提问范围：候选资料 ${scopeOptions?.videos.length ?? 0} 篇（提问时将实时核验原文）`
                  : `Active scope: Candidate sources (${scopeOptions?.videos.length ?? 0} items · live verified on ask)`}
          </span>
        </div>
      ) : null}

      {followUpNotice ? (
        <p className="ai-followup-toast" role="status" aria-live="polite">
          {followUpNotice}
        </p>
      ) : null}

      <form className="ai-research-ask-form" onSubmit={handleSubmit}>
        <div className="ai-research-input-wrap">
          <textarea
            ref={questionInputRef}
            rows={1}
            className="ai-research-textarea"
            aria-label={zh ? "跨视频提问" : "Ask across videos"}
            placeholder={
              zh
                ? "输入你想跨视频对比的产品、技术或商业变现问题（Enter 提问 · Shift+Enter 换行）…"
                : "Ask a product, technical, or business question across your library…"
            }
            value={questionInput}
            disabled={busy || isEmptyLibrary}
            onChange={(e) => {
              setQuestionInput(e.target.value);
              if (followUpNotice) setFollowUpNotice(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (!isEmptyLibrary) {
                  setFollowUpNotice(null);
                  void ask(questionInput);
                }
              }
            }}
          />
          {questionInput.length > 0 && !busy ? (
            <button
              type="button"
              className="ai-research-clear-btn"
              aria-label={zh ? "清空提问草稿" : "Clear question draft"}
              title={zh ? "清空输入内容" : "Clear input"}
              onClick={() => {
                setQuestionInput("");
                setFollowUpNotice(null);
                questionInputRef.current?.focus();
              }}
            >
              {zh ? "清空" : "Clear"}
            </button>
          ) : null}
        </div>
        <button type="submit" className="button button-primary" disabled={busy || isEmptyLibrary || !questionInput.trim()}>
          {busy ? (zh ? "正在检索并推演…" : "Synthesizing…") : zh ? "AI 提问" : "Ask AI"}
        </button>
      </form>

      {isEmptyLibrary ? (
        <div className="research-empty-library-guide" role="status">
          <p>
            {zh
              ? "资料库尚无可核验材料。导入至少 1 条 YouTube / B 站视频或本地 .md / .txt / 音视频文件后，即可开启跨来源溯源问答与对比。"
              : "No verifiable materials in your library yet. Import a YouTube/Bilibili video or a local .md/.txt/media file to unlock cross-source grounded Q&A."}
          </p>
          {onOpenImport ? (
            <button type="button" className="button button-primary" onClick={onOpenImport}>
              {zh ? "导入视频或本地笔记" : "Import video or local note"}
            </button>
          ) : null}
        </div>
      ) : (
      <div className="ai-suggested-pills">
        {(() => {
          const activeSuggestedQuestions = (() => {
            if (selectedVideoIds.length > 0) {
              const matched = (scopeOptions?.videos ?? []).filter((v) =>
                selectedVideoIds.includes(v.video_id),
              );
              if (selectedVideoIds.length === 1) {
                const singleTitle = matched[0]?.title?.trim();
                if (singleTitle) {
                  return zh
                    ? [
                        `围绕《${singleTitle}》提炼最核心的方法论、关键论据与可落地步骤`,
                        `《${singleTitle}》提出了哪些反直觉判断、数据指标与避坑警示？`,
                      ]
                    : [
                        `Extract the core methodology, evidence, and actionable steps from "${singleTitle}"`,
                        `What counter-intuitive claims, metrics, and pitfalls appear in "${singleTitle}"?`,
                      ];
                }
                return zh
                  ? [
                      "提炼这篇指定视频最核心的方法论、关键论据与可落地步骤",
                      "这篇指定视频提出了哪些反直觉判断与实战避坑警示？",
                    ]
                  : [
                      "Extract the core methodology, evidence, and actionable steps from this selected video",
                      "What counter-intuitive claims and practical pitfalls appear in this selected video?",
                    ];
              }
              const uniqChannels = Array.from(
                new Set(matched.map((v) => (v.channel_name ?? "").trim()).filter(Boolean)),
              );
              const uniqTopics = Array.from(
                new Set(matched.map((v) => (v.topic_cluster_zh ?? "").trim()).filter(Boolean)),
              );
              const channelTag =
                uniqChannels.length === 1
                  ? `（${uniqChannels[0]}）`
                  : uniqChannels.length > 1
                    ? `（${uniqChannels.slice(0, 3).join(" vs ")}）`
                    : "";
              const topicTag = uniqTopics.length === 1 ? `在「${uniqTopics[0]}」上` : "";
              return zh
                ? [
                    `横向对比这 ${selectedVideoIds.length} 篇指定视频${channelTag}${topicTag}的核心共识、观点分歧与演进脉络`,
                    `综合这 ${selectedVideoIds.length} 篇视频的时间轴原话，提炼最值得立即执行的 3 个实操动作与产品切入点`,
                    `这 ${selectedVideoIds.length} 篇视频揭示了哪些容易踩坑的误区、边界条件或商业化前提？`,
                  ]
                : [
                    `Compare core consensus, disagreements, and evolution across these ${selectedVideoIds.length} selected videos`,
                    `Synthesize the top 3 actionable steps and product opportunities grounded in these ${selectedVideoIds.length} videos`,
                    `What key pitfalls, boundary conditions, or monetization prerequisites emerge across these ${selectedVideoIds.length} videos?`,
                  ];
            }
            if (selectedTopic) {
              const chLabel = selectedChannel
                ? scopeOptions?.channels.find((c) => c.key === selectedChannel)?.label ??
                  (selectedChannel === "LOCAL" && zh ? "本地实战课" : selectedChannel)
                : "";
              return zh
                ? [
                    chLabel
                      ? `${chLabel} 在「${selectedTopic}」专题下有哪些核心判断与代表性实战案例？`
                      : `围绕「${selectedTopic}」专题，不同创作者的核心共识与关键分歧是什么？`,
                    `综合「${selectedTopic}」专题原话，提炼最具确定性的落地路径与产品机会`,
                    `「${selectedTopic}」专题在工程落地或商业验证中有哪些高频避坑点？`,
                  ]
                : [
                    chLabel
                      ? `What are ${chLabel}'s core claims and practical cases in "${selectedTopic}"?`
                      : `What are the key consensus and disagreements across creators on "${selectedTopic}"?`,
                    `Synthesize the highest-conviction implementation paths and product opportunities in "${selectedTopic}"`,
                    `What are the top engineering or business pitfalls highlighted in "${selectedTopic}"?`,
                  ];
            }
            if (selectedChannel) {
              const chLabel =
                scopeOptions?.channels.find((c) => c.key === selectedChannel)?.label ??
                (selectedChannel === "LOCAL" && zh ? "本地实战课" : selectedChannel);
              return zh
                ? [
                    `总结 ${chLabel} 近期内容的核心方法论、高频主题与关键判断变化`,
                    `${chLabel} 提出了哪些可直接复用的产品设计、工程实践或商业变现动作？`,
                    `${chLabel} 重点强调了哪些反直觉结论与实战避坑建议？`,
                  ]
                : [
                    `Summarize ${chLabel}'s core methodology, recurring themes, and key shifts`,
                    `What reusable product, engineering, or monetization actions does ${chLabel} recommend?`,
                    `What counter-intuitive conclusions and practical pitfalls does ${chLabel} emphasize?`,
                  ];
            }
            if (starredOnly) {
              return zh
                ? [
                    "综合我收藏的高价值视频，提炼最值得优先落地的核心洞察与行动清单",
                    "我收藏的这些视频在技术路线与商业判断上有哪些互补与碰撞？",
                  ]
                : [
                    "Synthesize top insights and priority action items across my starred videos",
                    "How do my starred videos complement or challenge each other on tech and business?",
                  ];
            }
            return suggested;
          })();
          return activeSuggestedQuestions.map((q, idx) => (
            <div key={q} className="ai-suggested-pill-pair">
              <button
                type="button"
                className="ai-question-chip ai-question-chip-paired"
                disabled={busy}
                onClick={() => void ask(q)}
              >
                {q}
              </button>
              <button
                type="button"
                className="ai-question-fill-btn"
                disabled={busy}
                aria-label={
                  zh ? `填入推荐问题 ${idx + 1} 编辑` : `Edit suggested question ${idx + 1}`
                }
                title={
                  zh ? "填入提问框微调后再提问" : "Fill into input box to edit before asking"
                }
                onClick={() => {
                  setQuestionInput(q);
                  queueMicrotask(() => {
                    const el = questionInputRef.current;
                    if (el) {
                      el.focus();
                      const len = q.length;
                      el.setSelectionRange?.(len, len);
                    }
                  });
                }}
              >
                {zh ? "填入" : "Edit"}
              </button>
            </div>
          ));
        })()}
      </div>
      )}

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {activeSession ? (
        <div className="ai-qa-answer-box">
          <div className="ai-qa-answer-head">
            <h3>{activeSession.question}</h3>
            {activeSession.provider === "demo-replay" ? (
              <span className="ai-basis-pill">
                {zh ? "离线合成样例回放" : "Offline synthetic replay"}
              </span>
            ) : null}
            {activeSession.refused ? (
              <span className="status status-warning">
                {zh ? "证据不足 · 已诚实拒答" : "Refused · Insufficient Evidence"}
              </span>
            ) : activeSession.answer_status === "NEEDS_REVERIFICATION" ? (
              <span className="status status-warning">
                {zh ? "恢复记录 · 出处待核验" : "Restored · Source Needs Re-verification"}
              </span>
            ) : (
              <>
                {activeSession.source_integrity_status === "VERIFIED" ? (
                  <span className="ai-basis-pill">
                    {zh ? "出处已核验" : "Source verified"}
                  </span>
                ) : activeSession.source_integrity_status === "NEEDS_REVERIFICATION" ? (
                  <span className="status status-warning">
                    {zh ? "出处待核验" : "Source needs re-verification"}
                  </span>
                ) : activeSession.source_integrity_status === "REFUSED" ? (
                  <span className="status status-warning">
                    {zh ? "已拒答" : "Refused"}
                  </span>
                ) : (
                  <span className="status status-warning">
                    {zh ? "出处状态未知 · 请核对原文" : "Source status unknown"}
                  </span>
                )}
                {activeSession.fact_verification_state === "SUPPORTED" ? (
                  <span className="ai-basis-pill">
                    {zh ? "结论已受证据支持" : "Claims supported"}
                  </span>
                ) : activeSession.fact_verification_state === "PARTIAL_PRUNED_HEURISTIC" ||
                  (activeSession.fact_verification_state === "PARTIAL_PRUNED" &&
                    activeSession.contains_heuristic_claims === true) ? (
                  <>
                    <span className="ai-basis-pill">
                      {zh ? "部分未支持内容已裁剪" : "Unsupported parts pruned"}
                    </span>
                    <span className="status status-warning">
                      {zh ? "启发式相关 · 请核对原文" : "Heuristic match · Verify source"}
                    </span>
                  </>
                ) : activeSession.fact_verification_state === "PARTIAL_PRUNED" ? (
                  <span className="ai-basis-pill">
                    {zh ? "部分未支持内容已裁剪" : "Unsupported parts pruned"}
                  </span>
                ) : activeSession.fact_verification_state === "HEURISTIC_ONLY" ? (
                  <span className="status status-warning">
                    {zh ? "启发式相关 · 请核对原文" : "Heuristic match · Verify source"}
                  </span>
                ) : activeSession.fact_verification_state === "UNSUPPORTED_CLAIM_UNVERIFIED" ? (
                  <span className="status status-warning">
                    {zh ? "结论尚待核验" : "Claims unverified"}
                  </span>
                ) : activeSession.fact_verification_state === "NEEDS_REVERIFICATION" ? (
                  <span className="status status-warning">
                    {zh ? "需要重新核验" : "Needs re-verification"}
                  </span>
                ) : activeSession.fact_verification_state === "CITATION_FACT_CONFLICT" ||
                  activeSession.fact_verification_state === "NO_VERIFIED_CITATIONS" ? (
                  <span className="status status-warning">
                    {zh ? "事实核验未通过" : "Fact verification failed"}
                  </span>
                ) : (
                  <span className="status status-warning">
                    {zh ? "核验状态未知 · 请核对原文" : "Verification status unknown"}
                  </span>
                )}
              </>
            )}
            {activeSession.scope_label_zh ? (
              <span className="ai-basis-pill">{activeSession.scope_label_zh}</span>
            ) : null}
            <span className="ai-basis-pill tabular-nums">
              {zh
                ? `有效引用 ${activeSession.verified_citation_count ?? activeSession.citations.filter((c) => c.verified !== false).length} 条 · 覆盖来源 ${activeSession.covered_source_count ?? activeSession.covered_sources?.length ?? 0} 篇`
                : `Verified ${activeSession.verified_citation_count ?? activeSession.citations.filter((c) => c.verified !== false).length} citations · ${activeSession.covered_source_count ?? activeSession.covered_sources?.length ?? 0} sources`}
            </span>
          </div>
          {!activeSession.refused ? (
            <p className="ai-qa-trust-note">
              {activeSession.fact_verification_state === "SUPPORTED"
                ? zh
                  ? "以下回答仅依据你已选中的原文与时间轴生成，点击任意引用即可直达原片核对。"
                  : "Answer grounded strictly in your selected excerpts and timestamps; click any citation to verify."
                : activeSession.fact_verification_state === "PARTIAL_PRUNED_HEURISTIC" ||
                    activeSession.fact_verification_state === "PARTIAL_PRUNED" ||
                    activeSession.fact_verification_state === "HEURISTIC_ONLY"
                  ? zh
                    ? "已自动过滤无原文依据的推测；标注「启发式相关」的表述建议点击下方引用核对原话。"
                    : "Unverified speculation was removed; click any timestamp below to check heuristic statements against the source."
                  : zh
                    ? "建议点击下方原始引用核对细节，所有来源均保留可追溯锚点。"
                    : "Verify details with the timestamped excerpts below; all sources stay traceable."}
            </p>
          ) : null}
          {(activeSession.covered_sources?.length ?? 0) > 0 ? (
            <div
              className="ai-covered-sources-strip"
              role="group"
              aria-label={zh ? "本次检索覆盖的可核验材料" : "Covered verifiable sources"}
            >
              <span className="ai-covered-sources-label tabular-nums">
                {zh
                  ? `本次检索覆盖 ${activeSession.covered_source_count ?? activeSession.covered_sources?.length ?? 0} 份可核验材料：`
                  : `Searched ${activeSession.covered_source_count ?? activeSession.covered_sources?.length ?? 0} verifiable sources:`}
              </span>
              {(activeSession.covered_sources ?? []).slice(0, 6).map((src) => (
                <button
                  key={`cov:${src.video_id}`}
                  type="button"
                  className="ai-covered-source-chip"
                  onClick={() => onOpen("content", src.video_id)}
                  title={src.title}
                >
                  <span>{src.title}</span>
                  {src.locator_type === "TEXT_RANGE" ? (
                    <small>{zh ? "文档" : "Doc"}</small>
                  ) : null}
                </button>
              ))}
              {(activeSession.covered_sources?.length ?? 0) > 6 ? (
                <span className="ai-basis-pill is-compact tabular-nums">
                  {`+${(activeSession.covered_sources?.length ?? 0) - 6}`}
                </span>
              ) : null}
            </div>
          ) : null}
          {activeSession.refused ? (
            <div className="semantic-state state-warning" role="status">
              <p>{activeSession.answer_zh}</p>
              {hasActiveScope ||
              (activeSession.scope_label_zh && !/全部/.test(activeSession.scope_label_zh)) ? (
                <div className="ai-refusal-recovery">
                  <p className="hint">
                    {zh
                      ? `当前仅在限定范围（${activeSession.scope_label_zh || "已选来源"}）内检索；该范围内暂无直接原文支撑，因此未强行编造回答。`
                      : `Searched only within your active filter (${activeSession.scope_label_zh || "selected scope"}); no direct supporting excerpt was found there, so no answer was fabricated.`}
                  </p>
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    disabled={busy}
                    onClick={() => void ask(activeSession.question, { clearScope: true })}
                  >
                    {zh ? "扩大到全部来源重新提问" : "Retry across all sources"}
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="summary-copy">{activeSession.answer_zh}</p>
          )}

          {activeSession.key_takeaways_zh.length > 0 ? (
            <ul>
              {activeSession.key_takeaways_zh.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          ) : null}

          {activeSession.action_items_zh.length > 0 ? (
            <div className="ai-action-items-block">
              <h4>
                {zh ? "下一步可执行动作" : "Next actionable steps"}
                <span className="ai-basis-pill is-compact" style={{ marginLeft: "0.5rem" }}>
                  {zh ? "AI 推断建议（非原文事实）" : "AI advisory (not verbatim source fact)"}
                </span>
              </h4>
              <ul>
                {activeSession.action_items_zh.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {activeSession.citations.length > 0 ? (
            <div className="ai-citations-section">
              <h4>
                {activeSession.citations.some((c) => c.locator_type === "TEXT_RANGE")
                  ? zh
                    ? "可验证原话出处（时间戳 / 段落定位，点击直达原文）"
                    : "Verified citations (timestamps / paragraphs)"
                  : zh
                    ? "可验证原话时间轴出处（点击直达对应视频与证据）"
                    : "Verified timestamped citations"}
              </h4>
              <div className="ai-citation-list">
                {activeSession.citations.map((c) => (
                  <div key={`${c.ref_label}:${c.evidence_id}`} className="ai-citation-row">
                    <button
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
                    {c.citation_url ? (
                      <a
                        className="ai-citation-ext-link tabular-nums"
                        href={c.citation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={
                          zh
                            ? `跳转原片 ${c.timestamp_label}`
                            : `Open source at ${c.timestamp_label}`
                        }
                      >
                        {zh ? `原片 ${c.timestamp_label} ↗` : `Source ${c.timestamp_label} ↗`}
                      </a>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {activeSession.refused && (activeSession.related_excerpts?.length ?? 0) > 0 ? (
            <div className="ai-citations-section ai-related-excerpts-section">
              <h4>
                {zh
                  ? "相关原始片段（仅供参考查阅，未作为支持结论的引用）"
                  : "Related source excerpts (inspection only — not supporting citations)"}
              </h4>
              <div className="ai-citation-list">
                {activeSession.related_excerpts?.map((c) => (
                  <div key={`rel:${c.ref_label}:${c.evidence_id}`} className="ai-citation-row">
                    <button
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
                    {c.citation_url ? (
                      <a
                        className="ai-citation-ext-link tabular-nums"
                        href={c.citation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={
                          zh
                            ? `跳转原片 ${c.timestamp_label}`
                            : `Open source at ${c.timestamp_label}`
                        }
                      >
                        {zh ? `原片 ${c.timestamp_label} ↗` : `Source ${c.timestamp_label} ↗`}
                      </a>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {!activeSession.refused && canFollowUpActiveSession ? (
            <div
              className="ai-followup-strip"
              role="group"
              aria-label={zh ? "同范围继续深挖" : "Follow-up angles (same scope)"}
            >
              <span className="ai-followup-label">
                {zh ? "同范围继续深挖：" : "Follow-up angles (same scope):"}
              </span>
              {(zh
                ? [
                    "对比不同来源的核心分歧与边界条件",
                    "提炼最值得立即落地的 3 个执行步骤",
                    "哪些结论仅由单一来源提及、需要进一步验证？",
                  ]
                : [
                    "Compare core disagreements and boundary conditions across sources",
                    "Extract the top 3 concrete implementation steps",
                    "Which claims come from only a single source and need verification?",
                  ]
              ).map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="ai-followup-chip"
                  disabled={busy}
                  onClick={() => {
                    applyActiveSessionFollowUp();
                    setQuestionInput(prompt);
                    setFollowUpNotice(
                      zh
                        ? "已锁定当前来源范围并填入追问，可微调后按 Enter 发送。"
                        : "Scope locked & follow-up filled — edit or press Enter to ask.",
                    );
                    queueMicrotask(() => {
                      const el = questionInputRef.current;
                      if (el) {
                        el.focus();
                        el.setSelectionRange?.(prompt.length, prompt.length);
                      }
                    });
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}

          <div className="button-row">
            {canFollowUpActiveSession ? (
              <button
                type="button"
                className="button button-secondary button-small tabular-nums"
                onClick={applyActiveSessionFollowUp}
              >
                <PhosphorIcon name="sparkle" size={13} />
                {hasExplicitActiveScope
                  ? zh
                    ? "同范围继续追问"
                    : "Follow up in this scope"
                  : zh
                    ? `围绕引用视频追问 (${activeCitedVideoIds.length})`
                    : `Follow up on cited videos (${activeCitedVideoIds.length})`}
              </button>
            ) : null}
            <button
              type="button"
              className="button button-secondary button-small"
              onClick={(event) => {
                pulseCelebration(event.currentTarget);
                void navigator.clipboard?.writeText(
                  formatPlainTextResearchBrief(activeSession, zh),
                );
                setCopiedPlain(true);
                setTimeout(() => setCopiedPlain(false), 2000);
              }}
            >
              <PhosphorIcon name="quotes" size={13} />
              {copiedPlain
                ? zh
                  ? "已复制纯文本提纲"
                  : "Copied plain-text brief"
                : zh
                  ? "复制纯文本提纲"
                  : "Copy plain-text brief"}
            </button>
            {activeSession.obsidian_markdown ? (
              <>
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
              </>
            ) : null}
            <button
              type="button"
              className={`button button-small ${activeSession.pinned ? "button-saved" : "button-ghost"}`}
              disabled={sessionMutatingId !== null}
              aria-pressed={Boolean(activeSession.pinned)}
              onClick={(event) => {
                pulseCelebration(event.currentTarget);
                void togglePinSession(activeSession);
              }}
            >
              <PhosphorIcon
                name="push-pin"
                weight={activeSession.pinned ? "fill" : "regular"}
                size={13}
              />
              {activeSession.pinned
                ? zh
                  ? "已置顶 · 取消"
                  : "Pinned · Unpin"
                : zh
                  ? "置顶问答"
                  : "Pin Q&A"}
            </button>
            <button
              type="button"
              className="button button-ghost button-small"
              disabled={sessionMutatingId !== null}
              onClick={() => void deleteSession(activeSession)}
            >
              <PhosphorIcon name="trash" size={13} />
              {zh ? "删除问答" : "Delete Q&A"}
            </button>
          </div>
        </div>
      ) : null}

      {sessions.length >= 1 ? (
        <div className="ai-session-history">
          <div className="ai-session-history-head">
            <h4>{zh ? "历史跨视频问答" : "Recent AI Q&A sessions"}</h4>
            {sessions.length >= 3 ? (
              <input
                type="search"
                className="ai-session-search-input"
                aria-label={zh ? "筛选历史问答" : "Filter Q&A history"}
                placeholder={zh ? "筛选历史问题或频道…" : "Filter past Q&A…"}
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
              />
            ) : null}
          </div>
          {filteredSessions.length > 0 ? (
            <div className="ai-suggested-pills">
              {filteredSessions.map((s) => {
                const vCount =
                  s.video_count && s.video_count > 0
                    ? s.video_count
                    : new Set(s.citations.map((c) => c.video_id)).size;
                const baseLabel =
                  vCount > 0
                    ? zh
                      ? `${s.question} · ${vCount} 篇`
                      : `${s.question} · ${vCount} videos`
                    : s.question;
                const chipLabel = s.pinned
                  ? `${zh ? "[置顶] " : "[Pinned] "}${baseLabel}`
                  : baseLabel;
                return (
                  <button
                    key={s.session_id}
                    type="button"
                    className={`ai-question-chip tabular-nums${activeSession?.session_id === s.session_id ? " is-active" : ""}`}
                    onClick={() => setActiveSession(s)}
                  >
                    {s.pinned ? (
                      <PhosphorIcon
                        name="push-pin"
                        weight="fill"
                        size={11}
                        className="ai-qa-chip-pin-icon"
                      />
                    ) : null}
                    {chipLabel}
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="hint">
              {zh ? "没有匹配的历史问答记录。" : "No matching past Q&A sessions."}
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}

const DEFAULT_CURATED_OLLAMA: CuratedOllamaModel[] = [
  {
    id: "qwen3.5:9b",
    label: "qwen3.5:9b",
    tier: "recommended",
    size_label: "~6.6 GB",
    ram_label_zh: "16GB+ 内存",
    ram_label_en: "16GB+ RAM",
    supports_vision: true,
    summary_zh: "首选：中文摘要与有据问答最稳，支持关键帧画面解读",
    summary_en: "Recommended: best synthesis, grounded Q&A, and vision",
  },
  {
    id: "qwen3.5:4b",
    label: "qwen3.5:4b",
    tier: "lightweight",
    size_label: "~3.4 GB",
    ram_label_zh: "8GB 内存",
    ram_label_en: "8GB RAM",
    supports_vision: true,
    summary_zh: "轻量：体积小下载快，8GB 内存流畅运行",
    summary_en: "Lightweight: fast download for 8GB RAM Macs",
  },
  {
    id: "qwen2.5:7b",
    label: "qwen2.5:7b",
    tier: "balanced",
    size_label: "~4.7 GB",
    ram_label_zh: "12GB+ 内存",
    ram_label_en: "12GB+ RAM",
    supports_vision: false,
    summary_zh: "均衡：经典纯文本模型",
    summary_en: "Balanced: steady text-only model",
  },
];

const DEFAULT_CURATED_WHISPER: CuratedWhisperModel[] = [
  {
    id: "mlx-community/whisper-large-v3-turbo",
    slug: "whisper-large-v3-turbo",
    label: "Whisper Large V3 Turbo",
    tier: "recommended",
    size_label: "~1.6 GB",
    summary_zh: "首选：中英双语混合转写准确度最高",
    summary_en: "Recommended: highest bilingual accuracy",
  },
  {
    id: "mlx-community/whisper-small-mlx",
    slug: "whisper-small-mlx",
    label: "Whisper Small (轻量版)",
    tier: "lightweight",
    size_label: "~480 MB",
    summary_zh: "小体积快速下载：适合 8GB 内存或较慢网络",
    summary_en: "Compact ~480 MB: quick download for lighter setups",
  },
];

type CloudPresetSpec = {
  label: string;
  labelEn: string;
  backendProvider: "deepseek" | "zhipu" | "moonshot" | "dashscope" | "openai_compatible";
  baseUrl: string;
  model: string;
  consoleUrl?: string;
  directCn: boolean;
};

const CLOUD_PRESETS: Record<string, CloudPresetSpec> = {
  deepseek: {
    label: "DeepSeek（国内直连 · 首选）",
    labelEn: "DeepSeek (CN Direct · Recommended)",
    backendProvider: "deepseek",
    baseUrl: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
    consoleUrl: "https://platform.deepseek.com/api_keys",
    directCn: true,
  },
  zhipu: {
    label: "智谱 BigModel（国内直连）",
    labelEn: "Zhipu BigModel (CN Direct)",
    backendProvider: "zhipu",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    model: "glm-4-plus",
    consoleUrl: "https://open.bigmodel.cn/usercenter/apikeys",
    directCn: true,
  },
  moonshot: {
    label: "Moonshot / Kimi（国内直连）",
    labelEn: "Moonshot / Kimi (CN Direct)",
    backendProvider: "moonshot",
    baseUrl: "https://api.moonshot.cn/v1",
    model: "kimi-k2-0905-preview",
    consoleUrl: "https://platform.moonshot.cn/console/api-keys",
    directCn: true,
  },
  dashscope: {
    label: "阿里云百炼 / 通义千问（国内直连）",
    labelEn: "Aliyun DashScope / Qwen (CN Direct)",
    backendProvider: "dashscope",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: "qwen-plus",
    consoleUrl: "https://bailian.console.aliyun.com/?apiKey=1",
    directCn: true,
  },
  openai: {
    label: "OpenAI（海外接口 · 需代理）",
    labelEn: "OpenAI (Global · Proxy may be needed)",
    backendProvider: "openai_compatible",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
    consoleUrl: "https://platform.openai.com/api-keys",
    directCn: false,
  },
  openai_compatible: {
    label: "其他 OpenAI 兼容接口（自定义地址）",
    labelEn: "Other OpenAI-compatible (Custom URL)",
    backendProvider: "openai_compatible",
    baseUrl: "",
    model: "",
    directCn: false,
  },
};

type PullProgress = {
  state: string;
  model: string;
  status_text: string;
  completed_bytes: number;
  total_bytes: number;
  percent: number;
  error: string | null;
};

type WhisperDownloadProgress = {
  state: string;
  model_id: string;
  slug: string;
  mirror: string;
  mirror_used: string;
  current_file: string;
  completed_files: number;
  total_files: number;
  percent: number;
  error: string | null;
};

export function WorkspaceAiSettingsPanel({
  id,
  initial,
  onConfigChange,
}: {
  id?: string;
  initial?: unknown;
  onConfigChange?: (next: WorkspaceAiSettings) => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const parsedInitial = readWorkspaceAiSettings(initial);
  const [config, setConfig] = useState<WorkspaceAiSettings | null>(parsedInitial);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingCloud, setTestingCloud] = useState(false);
  const [cloudTestResult, setCloudTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [pullStatus, setPullStatus] = useState<PullProgress | null>(null);
  const [exportingBackup, setExportingBackup] = useState(false);
  const [exportingObsidianZip, setExportingObsidianZip] = useState(false);
  const [restoringBackup, setRestoringBackup] = useState(false);
  const restoreInputRef = useRef<HTMLInputElement | null>(null);
  const sectionRef = useRef<HTMLElement | null>(null);
  const dirtyRef = useRef(false);
  const [modeDraft, setModeDraft] = useState<"local_ollama" | "cloud_byok">(
    parsedInitial?.active_mode ?? "local_ollama",
  );
  const [ollamaModelDraft, setOllamaModelDraft] = useState(
    parsedInitial?.ollama_model ?? "qwen3.5:9b",
  );
  const [cloudPresetDraft, setCloudPresetDraft] = useState<string>(
    parsedInitial?.cloud_provider && CLOUD_PRESETS[parsedInitial.cloud_provider]
      ? parsedInitial.cloud_provider
      : "deepseek",
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

  const syncDrafts = (next: WorkspaceAiSettings, forceDrafts = true) => {
    setConfig(next);
    if (!forceDrafts && dirtyRef.current) return;
    setModeDraft(next.active_mode);
    setOllamaModelDraft(next.ollama_model);
    const matchingPreset = Object.entries(CLOUD_PRESETS).find(
      ([, spec]) => spec.backendProvider === next.cloud_provider && spec.baseUrl === next.cloud_base_url,
    )?.[0] ?? (CLOUD_PRESETS[next.cloud_provider] ? next.cloud_provider : "openai_compatible");
    setCloudPresetDraft(matchingPreset);
    setCloudProviderDraft(next.cloud_provider);
    setCloudBaseUrlDraft(next.cloud_base_url);
    setCloudModelDraft(next.cloud_model);
  };

  const refreshLiveConfig = async () => {
    setLoading(true);
    try {
      const res = await api<unknown>("/workspace-ai/settings");
      const parsed = readWorkspaceAiSettings(res);
      if (parsed) {
        syncDrafts(parsed, false);
        onConfigChange?.(parsed);
      }
    } catch {
      setError(zh ? "未能读取 AI 引擎配置。" : "Could not load AI engine settings.");
    } finally {
      setLoading(false);
    }
  };

  const openEditor = async () => {
    dirtyRef.current = false;
    setOpen(true);
    setFeedback(null);
    setError(null);
    setCloudTestResult(null);
    await refreshLiveConfig();
  };

  useEffect(() => {
    const syncModelsHash = () => {
      if (location.hash.startsWith("#Settings/models")) {
        void openEditor();
        setTimeout(() => {
          sectionRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
        }, 30);
      }
    };
    syncModelsHash();
    window.addEventListener("hashchange", syncModelsHash);
    return () => window.removeEventListener("hashchange", syncModelsHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!pullStatus || pullStatus.state !== "pulling") return;
    let active = true;
    const timer = setTimeout(async () => {
      try {
        const next = await api<PullProgress>("/workspace-ai/ollama/pull-status");
        if (!active) return;
        setPullStatus(next);
        if (next.state === "succeeded") {
          setFeedback(
            zh
              ? `已下载并自动启用本地模型：${next.model}`
              : `Downloaded and enabled local model: ${next.model}`,
          );
          await refreshLiveConfig();
        } else if (next.state === "failed" && next.error) {
          setError(next.error);
        }
      } catch {
        // retry on next tick
      }
    }, 700);
    return () => {
      active = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pullStatus]);

  const startOllamaPull = async (modelId: string) => {
    setFeedback(null);
    setError(null);
    try {
      const res = await post<PullProgress>("/workspace-ai/ollama/pull", { model: modelId });
      setPullStatus(res);
    } catch (reason) {
      setError(
        reason instanceof ApiRequestError
          ? reason.message
          : zh
            ? "无法启动 Ollama 模型下载，请确认 Ollama 已打开。"
            : "Could not start Ollama model download.",
      );
    }
  };

  const selectAndSaveOllamaModel = async (modelId: string) => {
    setOllamaModelDraft(modelId);
    setModeDraft("local_ollama");
    setSaving(true);
    setFeedback(null);
    setError(null);
    try {
      const res = await put<unknown>("/workspace-ai/settings", {
        active_mode: "local_ollama",
        ollama_model: modelId,
      });
      const parsed = readWorkspaceAiSettings(res);
      if (parsed) {
        dirtyRef.current = false;
        syncDrafts(parsed);
        onConfigChange?.(parsed);
      }
      setFeedback(
        zh ? `已切换并保存本地模型：${modelId}` : `Switched active local model to ${modelId}.`,
      );
    } catch {
      setError(zh ? "切换模型未能保存。" : "Could not save local model choice.");
    } finally {
      setSaving(false);
    }
  };

  const testCloud = async () => {
    if (testingCloud) return;
    setTestingCloud(true);
    setCloudTestResult(null);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        cloud_base_url: cloudBaseUrlDraft.trim(),
      };
      if (apiKeyDraft.trim()) payload.cloud_api_key = apiKeyDraft.trim();
      const res = await post<{ ok?: boolean; message?: string }>("/workspace-ai/test-cloud", payload);
      setCloudTestResult({
        ok: Boolean(res?.ok),
        message:
          typeof res?.message === "string" && res.message
            ? res.message
            : res?.ok
              ? zh
                ? "连接测试通过！"
                : "Connection verified."
              : zh
                ? "连接测试未通过，请检查 Key 或地址。"
                : "Connection check failed.",
      });
    } catch {
      setCloudTestResult({
        ok: false,
        message: zh
          ? "HTTPS 接口地址格式有误或受安全策略拦截。"
          : "Invalid HTTPS endpoint URL.",
      });
    } finally {
      setTestingCloud(false);
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
      if (parsed) {
        dirtyRef.current = false;
        syncDrafts(parsed);
        onConfigChange?.(parsed);
      }
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

  const exportObsidianZipFromSettings = async () => {
    if (exportingObsidianZip) return;
    setExportingObsidianZip(true);
    setFeedback(null);
    setError(null);
    try {
      const out = await exportObsidianVaultBundle("all");
      setFeedback(
        zh
          ? `已导出 Obsidian 双链知识库包（共 ${out.totalFiles} 篇 .md 笔记，不含任何密钥）。`
          : `Exported Obsidian Vault bundle (${out.totalFiles} interlinked .md notes, zero secrets).`,
      );
    } catch {
      setError(
        zh
          ? "未能导出 Obsidian 知识库包，请稍后重试。"
          : "Could not export Obsidian Vault bundle.",
      );
    } finally {
      setExportingObsidianZip(false);
    }
  };

  const handleRestoreFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || restoringBackup) return;
    if (typeof file.size === "number" && file.size > 64 * 1024 * 1024) {
      setFeedback(null);
      setError(
        zh
          ? "快照文件超过 64 MiB 安全上限，无法导入。"
          : "Backup snapshot exceeds the 64 MiB safety limit.",
      );
      return;
    }
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
      const res = await post<{
        restored?: unknown;
        missing_visual_images?: unknown;
        warnings?: unknown;
      }>("/workspace-ai/restore", parsed);
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
      const visualImagesCount =
        typeof counts.visual_images === "number" ? counts.visual_images : 0;
      const missingVisualCount =
        typeof res.missing_visual_images === "number" ? res.missing_visual_images : 0;
      const serverWarnings = Array.isArray(res.warnings)
        ? res.warnings.filter((w): w is string => typeof w === "string" && w.trim().length > 0)
        : [];
      const extraParts: string[] = [];
      if (curationCount > 0) {
        extraParts.push(zh ? `${curationCount} 条阅读状态` : `${curationCount} reading states`);
      }
      if (visualImagesCount > 0) {
        extraParts.push(zh ? `${visualImagesCount} 张关键帧图片` : `${visualImagesCount} keyframe images`);
      }
      const extraLabel =
        extraParts.length > 0
          ? zh
            ? `（含 ${extraParts.join("、")}）`
            : ` (${extraParts.join(", ")})`
          : "";
      const warningNote =
        serverWarnings.length > 0
          ? ` ${serverWarnings[0]}`
          : missingVisualCount > 0
            ? zh
              ? ` 注意：旧版快照缺少 ${missingVisualCount} 张关键帧图片。`
              : ` Note: ${missingVisualCount} keyframe images are missing from this metadata-only snapshot.`
            : "";
      setFeedback(
        (zh
          ? `已恢复 ${videoCount} 条中文摘要、${weeklyCount} 份周报与 ${qaCount} 条跨视频问答记录${extraLabel}。`
          : `Restored ${videoCount} AI briefs, ${weeklyCount} weekly digests, and ${qaCount} Q&A sessions${extraLabel}.`) +
          warningNote,
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

  const curatedOllama =
    config?.curated_ollama_models && config.curated_ollama_models.length > 0
      ? config.curated_ollama_models
      : DEFAULT_CURATED_OLLAMA;
  const installedModels = config?.installed_ollama_models ?? [];
  const activePresetSpec = CLOUD_PRESETS[cloudPresetDraft];

  return (
    <section
      ref={sectionRef}
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
        {zh ? "当前引擎：" : "Active: "}
        <strong>{currentSummary}</strong>
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
        <div className="button-row">
          <button type="button" className="button button-primary" onClick={() => void openEditor()}>
            {zh ? "配置 AI 摘要与问答引擎" : "Configure AI summary & Q&A engine"}
          </button>
        </div>
      ) : (
        <div className="ai-settings-form">
          {loading ? (
            <p role="status">{zh ? "正在检测本机模型状态…" : "Checking local model status…"}</p>
          ) : null}
          <label className="field">
            {zh ? "运行模式" : "Execution mode"}
            <select
              aria-label={zh ? "运行模式" : "Execution mode"}
              value={modeDraft}
              disabled={saving}
              onChange={(e) => {
                dirtyRef.current = true;
                setModeDraft(e.target.value as "local_ollama" | "cloud_byok");
              }}
            >
              <option value="local_ollama">
                {zh ? "本机免费 Ollama（零费用 · 数据不出本机）" : "Local free Ollama"}
              </option>
              <option value="cloud_byok">
                {zh ? "云端 API Key（按量付费 · 免装本地模型）" : "Cloud BYOK (OpenAI-compatible)"}
              </option>
            </select>
          </label>

          {modeDraft === "local_ollama" ? (
            <>
              <div className="curated-status-bar">
                <span className="hint">
                  {config?.ollama_reachable
                    ? zh
                      ? `✅ Ollama 运行中 · 已检测到 ${installedModels.length} 个模型`
                      : `✅ Ollama running · ${installedModels.length} installed`
                    : zh
                      ? "⚪ 未检测到本机 Ollama"
                      : "⚪ Local Ollama offline"}
                </span>
                <div className="button-row">
                  {!config?.ollama_reachable ? (
                    <a
                      className="button button-ghost button-small"
                      href="https://ollama.com/download"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {zh ? "安装 Ollama ↗" : "Install Ollama ↗"}
                    </a>
                  ) : null}
                  <button
                    type="button"
                    className="button button-ghost button-small"
                    disabled={loading}
                    onClick={() => void refreshLiveConfig()}
                  >
                    {zh ? "重新检测" : "Refresh"}
                  </button>
                  <button
                    type="button"
                    className="button button-ghost button-small"
                    onClick={() => {
                      dirtyRef.current = true;
                      setModeDraft("cloud_byok");
                    }}
                  >
                    {zh ? "改用国内云端 Key ›" : "Use Cloud Key ›"}
                  </button>
                </div>
              </div>

              <label className="field">
                {zh ? "本机 Ollama 模型" : "Local Ollama model"}
                {installedModels.length > 0 ? (
                  <select
                    aria-label={zh ? "本机 Ollama 模型" : "Local Ollama model"}
                    value={
                      installedModels.includes(ollamaModelDraft)
                        ? ollamaModelDraft
                        : installedModels[0]
                    }
                    disabled={saving}
                    onChange={(e) => {
                      dirtyRef.current = true;
                      setOllamaModelDraft(e.target.value);
                    }}
                  >
                    {installedModels.map((m) => (
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
                    onChange={(e) => {
                      dirtyRef.current = true;
                      setOllamaModelDraft(e.target.value);
                    }}
                  />
                )}
              </label>

              <div className="curated-model-grid" aria-label={zh ? "精选推荐模型" : "Curated Ollama models"}>
                <strong className="curated-section-title">
                  {zh ? "精选本地模型（免挑参数 · 点一下载或选用）" : "Curated models (one-click download)"}
                </strong>
                {curatedOllama.map((item) => {
                  const isInstalled = installedModels.some(
                    (m) => m === item.id || m.startsWith(`${item.id}-`),
                  );
                  const isPullingThis = pullStatus?.state === "pulling" && pullStatus.model === item.id;
                  const isSelected = ollamaModelDraft === item.id && config?.active_mode === "local_ollama";
                  return (
                    <div key={item.id} className="curated-model-row">
                      <div className="curated-model-info">
                        <div className="curated-model-head">
                          <strong>{item.label}</strong>
                          <span className="curated-pill">
                            {item.tier === "recommended"
                              ? zh
                                ? "推荐"
                                : "Recommended"
                              : item.tier === "lightweight"
                                ? zh
                                  ? "轻量"
                                  : "Fast"
                                : zh
                                  ? "均衡"
                                  : "Balanced"}
                          </span>
                          <span className="hint tabular-nums">
                            {item.size_label} · {zh ? item.ram_label_zh : item.ram_label_en}
                          </span>
                        </div>
                        <span className="hint">{zh ? item.summary_zh : item.summary_en}</span>
                      </div>
                      <div>
                        {isInstalled ? (
                          <button
                            type="button"
                            className={`button button-small ${isSelected ? "button-ghost" : "button-secondary"}`}
                            disabled={saving || isSelected}
                            onClick={() => void selectAndSaveOllamaModel(item.id)}
                          >
                            {isSelected ? (zh ? "当前使用中" : "Active") : zh ? "选用并保存" : "Use model"}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="button button-secondary button-small"
                            disabled={pullStatus?.state === "pulling"}
                            onClick={() => void startOllamaPull(item.id)}
                          >
                            {isPullingThis
                              ? zh
                                ? `下载中 ${pullStatus?.percent ?? 0}%`
                                : `Pulling ${pullStatus?.percent ?? 0}%`
                              : zh
                                ? "一键下载并启用"
                                : "Download & enable"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {pullStatus && pullStatus.state === "pulling" ? (
                <div className="download-progress-wrap" role="status" aria-live="polite">
                  <div className="download-progress-head">
                    <span>
                      {pullStatus.model} · {pullStatus.status_text}
                    </span>
                    <span className="tabular-nums">{pullStatus.percent}%</span>
                  </div>
                  <div className="download-progress-bar">
                    <span style={{ width: `${pullStatus.percent}%` }} />
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <ol className="cloud-guide-steps" aria-label={zh ? "3 步配置云端模型" : "3-step cloud setup"}>
                <li>{zh ? "1. 打开官网注册" : "1. Sign in provider"}</li>
                <li>{zh ? "2. 复制 API Key" : "2. Copy API key"}</li>
                <li>{zh ? "3. 粘贴测试并保存" : "3. Paste, test & save"}</li>
              </ol>

              <label className="field">
                {zh ? "云端服务商预设" : "Cloud provider"}
                <select
                  aria-label={zh ? "云端服务商预设" : "Cloud provider"}
                  value={cloudPresetDraft}
                  disabled={saving}
                  onChange={(e) => {
                    dirtyRef.current = true;
                    const nextKey = e.target.value;
                    setCloudPresetDraft(nextKey);
                    setCloudTestResult(null);
                    const preset = CLOUD_PRESETS[nextKey];
                    if (preset) {
                      setCloudProviderDraft(preset.backendProvider);
                      if (preset.baseUrl) setCloudBaseUrlDraft(preset.baseUrl);
                      if (preset.model) setCloudModelDraft(preset.model);
                    }
                  }}
                >
                  {Object.entries(CLOUD_PRESETS).map(([k, v]) => (
                    <option key={k} value={k}>
                      {zh ? v.label : v.labelEn}
                    </option>
                  ))}
                </select>
              </label>

              {activePresetSpec?.consoleUrl ? (
                <p className="cloud-console-link-row">
                  <a
                    className="button button-ghost button-small"
                    href={activePresetSpec.consoleUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {zh ? "去官网获取 API Key ↗" : "Open provider console ↗"}
                  </a>
                  <span className="hint">
                    {zh
                      ? `默认模型：${cloudModelDraft || activePresetSpec.model}`
                      : `Model: ${cloudModelDraft || activePresetSpec.model}`}
                  </span>
                </p>
              ) : null}

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
                  onChange={(e) => {
                    dirtyRef.current = true;
                    setApiKeyDraft(e.target.value);
                  }}
                />
              </label>

              <details
                className="cloud-advanced-details"
                open={cloudPresetDraft === "openai_compatible"}
              >
                <summary>
                  {zh ? "高级：自定义接口地址与模型名" : "Advanced: Base URL & custom model"}
                </summary>
                <label className="field">
                  {zh ? "HTTPS 接口地址 (Base URL)" : "HTTPS Base URL"}
                  <input
                    type="url"
                    aria-label={zh ? "HTTPS 接口地址 (Base URL)" : "HTTPS Base URL"}
                    value={cloudBaseUrlDraft}
                    disabled={saving}
                    onChange={(e) => {
                      dirtyRef.current = true;
                      setCloudBaseUrlDraft(e.target.value);
                    }}
                  />
                </label>
                <label className="field">
                  {zh ? "云端模型名称" : "Cloud model"}
                  <input
                    type="text"
                    aria-label={zh ? "云端模型名称" : "Cloud model"}
                    value={cloudModelDraft}
                    disabled={saving}
                    onChange={(e) => {
                      dirtyRef.current = true;
                      setCloudModelDraft(e.target.value);
                    }}
                  />
                </label>
              </details>

              {cloudTestResult ? (
                <p
                  role="status"
                  className={cloudTestResult.ok ? "semantic-state state-neutral" : "form-error"}
                >
                  {cloudTestResult.message}
                </p>
              ) : null}
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
            {modeDraft === "cloud_byok" ? (
              <button
                type="button"
                className="button button-secondary"
                disabled={saving || testingCloud}
                onClick={() => void testCloud()}
              >
                {testingCloud ? (zh ? "正在测试…" : "Testing…") : zh ? "测试连接" : "Test connection"}
              </button>
            ) : null}
            <button
              type="button"
              className="button button-ghost"
              disabled={saving}
              onClick={() => setOpen(false)}
            >
              {zh ? "收起" : "Close"}
            </button>
          </div>
        </div>
      )}
      {feedback ? <p role="status">{feedback}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <div
        className="settings-vault-backup-strip"
        role="group"
        aria-label={zh ? "知识库导出与快照" : "Vault export & snapshots"}
      >
        <p className="settings-vault-backup-label">
          {zh ? "知识库导出与快照" : "Vault export & snapshots"}
        </p>
        <div className="button-row">
          <button
            type="button"
            className="button button-secondary button-small"
            disabled={exportingBackup || exportingObsidianZip || restoringBackup}
            onClick={() => void exportObsidianZipFromSettings()}
          >
            <PhosphorIcon name="stack" size={13} />
            {exportingObsidianZip
              ? zh
                ? "正在打包 Obsidian…"
                : "Bundling Obsidian…"
              : zh
                ? "导出 Obsidian 知识库包 (.zip)"
                : "Export Obsidian (.zip)"}
          </button>
          <button
            type="button"
            className="button button-ghost button-small"
            disabled={exportingBackup || exportingObsidianZip || restoringBackup}
            onClick={() => void exportBackup()}
          >
            <PhosphorIcon name="archive" size={13} />
            {exportingBackup
              ? zh
                ? "正在导出…"
                : "Exporting…"
              : zh
                ? "导出 AI 知识库快照 (.json)"
                : "Export snapshot (.json)"}
          </button>
          <button
            type="button"
            className="button button-ghost button-small"
            disabled={exportingBackup || restoringBackup}
            onClick={() => restoreInputRef.current?.click()}
          >
            <PhosphorIcon name="folder-open" size={13} />
            {restoringBackup
              ? zh
                ? "正在恢复…"
                : "Restoring…"
              : zh
                ? "导入并恢复快照 (.json)"
                : "Restore (.json)"}
          </button>
        </div>
      </div>
    </section>
  );
}

export function WhisperQuickDownloadPanel({
  ready,
  activeSlug,
  catalog,
  onReady,
}: {
  ready?: boolean;
  activeSlug?: string | null;
  catalog?: CuratedWhisperModel[];
  onReady?: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const panelRef = useRef<HTMLElement | null>(null);
  const [mirror, setMirror] = useState<"auto" | "cn_mirror" | "official">("auto");
  const [status, setStatus] = useState<WhisperDownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [doneMsg, setDoneMsg] = useState<string | null>(null);

  useEffect(() => {
    const syncScroll = () => {
      if (location.hash.startsWith("#Settings/transcription")) {
        setTimeout(() => {
          panelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
        }, 30);
      }
    };
    syncScroll();
    window.addEventListener("hashchange", syncScroll);
    return () => window.removeEventListener("hashchange", syncScroll);
  }, []);

  useEffect(() => {
    if (!status || !["downloading", "verifying"].includes(status.state)) return;
    let active = true;
    const timer = setTimeout(async () => {
      try {
        const next = await api<WhisperDownloadProgress>("/workspace-ai/whisper/download-status");
        if (!active) return;
        setStatus(next);
        if (next.state === "succeeded") {
          setDoneMsg(
            zh
              ? `✅ 已下载并自动配置 ${next.slug}，现在可直接转写无字幕本地音视频。`
              : `✅ Downloaded and configured ${next.slug}. Ready for offline transcription.`,
          );
          onReady?.();
        } else if (next.state === "failed" && next.error) {
          setError(next.error);
        }
      } catch {
        // retry on next poll
      }
    }, 800);
    return () => {
      active = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const startDownload = async (modelId: string) => {
    setError(null);
    setDoneMsg(null);
    try {
      const next = await post<WhisperDownloadProgress>("/workspace-ai/whisper/download", {
        model_id: modelId,
        mirror,
      });
      setStatus(next);
    } catch (reason) {
      setError(
        reason instanceof ApiRequestError
          ? reason.message
          : zh
            ? "无法启动语音模型下载，请检查网络后重试。"
            : "Could not start Whisper model download.",
      );
    }
  };

  const models = catalog && catalog.length > 0 ? catalog : DEFAULT_CURATED_WHISPER;
  const isBusy = Boolean(status && ["downloading", "verifying"].includes(status.state));

  return (
    <section
      ref={panelRef}
      id="settings-whisper-download"
      className="panel"
      aria-label={zh ? "本地语音转写模型（可选）" : "Local Speech Transcription Model (Optional)"}
    >
      <div className="panel-head">
        <h2>
          <PhosphorIcon name="lightning" size={16} className="panel-title-icon" />
          <span>{zh ? "本地语音转写模型（可选）" : "Local Speech Model (Optional)"}</span>
        </h2>
        <span className={`curated-state-badge ${ready ? "is-ready" : ""}`}>
          {ready
            ? zh
              ? `✅ 已就绪${activeSlug ? ` · ${activeSlug}` : ""}`
              : `✅ Ready${activeSlug ? ` · ${activeSlug}` : ""}`
            : zh
              ? "未安装（仅无字幕本地音视频需要）"
              : "Not installed (only for uncaptioned local media)"}
        </span>
      </div>
      <p className="hint">
        {zh
          ? "仅导入无字幕的本地音频/视频时需要；有字幕的视频与 TXT/MD 笔记无需安装。模型只存于本机。"
          : "Only needed to transcribe uncaptioned local audio/video. Captioned videos & text notes work without it."}
      </p>

      <label className="field">
        {zh ? "下载线路（国内网络免 VPN 推荐镜像）" : "Download source"}
        <select
          aria-label={zh ? "语音模型下载线路" : "Whisper download mirror"}
          value={mirror}
          disabled={isBusy}
          onChange={(e) => setMirror(e.target.value as "auto" | "cn_mirror" | "official")}
        >
          <option value="auto">
            {zh ? "自动（国内镜像优先，无 VPN 推荐）" : "Auto (CN mirror first)"}
          </option>
          <option value="cn_mirror">
            {zh ? "国内高速镜像 (hf-mirror.com)" : "Mainland China Mirror (hf-mirror.com)"}
          </option>
          <option value="official">
            {zh ? "HuggingFace 官方源（需海外网络）" : "HuggingFace Official"}
          </option>
        </select>
      </label>

      <div className="curated-model-grid">
        {models.map((item) => {
          const isCurrent = Boolean(ready && activeSlug === item.slug);
          const isThisDownloading = isBusy && status?.model_id === item.id;
          return (
            <div key={item.id} className="curated-model-row">
              <div className="curated-model-info">
                <div className="curated-model-head">
                  <strong>{item.label}</strong>
                  <span className="curated-pill">
                    {item.tier === "recommended"
                      ? zh
                        ? "推荐"
                        : "Recommended"
                      : zh
                        ? "轻量"
                        : "Fast"}
                  </span>
                  <span className="hint tabular-nums">{item.size_label}</span>
                </div>
                <span className="hint">{zh ? item.summary_zh : item.summary_en}</span>
              </div>
              <button
                type="button"
                className={`button button-small ${isCurrent ? "button-secondary" : "button-primary"}`}
                disabled={isBusy}
                onClick={() => void startDownload(item.id)}
              >
                {isThisDownloading
                  ? zh
                    ? `下载中 ${status?.percent ?? 0}%`
                    : `Downloading ${status?.percent ?? 0}%`
                  : isCurrent
                    ? zh
                      ? "已就绪 · 重新下载"
                      : "Ready · Re-download"
                    : zh
                      ? "一键下载并自动配置"
                      : "One-click download & configure"}
              </button>
            </div>
          );
        })}
      </div>

      {isBusy && status ? (
        <div className="download-progress-wrap" role="status" aria-live="polite">
          <div className="download-progress-head">
            <span>
              {status.current_file || (zh ? "正在准备下载…" : "Preparing download…")}
              {status.total_files > 0
                ? ` (${status.completed_files}/${status.total_files})`
                : ""}
            </span>
            <span className="tabular-nums">{status.percent}%</span>
          </div>
          <div className="download-progress-bar">
            <span style={{ width: `${status.percent}%` }} />
          </div>
        </div>
      ) : null}

      {doneMsg ? <p role="status">{doneMsg}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

type YouTubeAuthStatus = {
  enabled: boolean;
  global_enabled?: boolean;
  scope?: "global" | "single_video" | "disabled";
  active_single_video_grants?: number;
  auth_mode: "disabled" | "browser" | "cookie_file";
  browser_name: string;
  supported_browsers: string[];
  cookie_configured: boolean;
  daily_limit: number;
  used_today: number;
  cooldown_seconds: number;
  circuit_open: boolean;
};

const DEFAULT_AUTH_BROWSERS = ["chrome", "firefox", "edge", "brave", "safari", "vivaldi", "chromium"];

function readYouTubeAuthReturnHash(): string | null {
  const target = new URLSearchParams(location.hash.split("?")[1] ?? "").get("return");
  return target &&
    /^#Content\/[^/?#]+(?:\/Evidence\/[^/?#]+)?$/.test(target) &&
    !/[\p{Cc}\p{Cs}]/u.test(target)
    ? target
    : null;
}

export function YouTubeAuthSettingsPanel() {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const panelRef = useRef<HTMLElement | null>(null);
  const cookieFileRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<YouTubeAuthStatus | null>(null);
  const [mode, setMode] = useState<"disabled" | "browser" | "cookie_file">("disabled");
  const [browser, setBrowser] = useState("chrome");
  const [cookiesTxt, setCookiesTxt] = useState("");
  const [dailyLimit, setDailyLimit] = useState(20);
  const [saving, setSaving] = useState(false);
  const [confirmRevokeAll, setConfirmRevokeAll] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deepLinked, setDeepLinked] = useState(false);
  const [returnHash, setReturnHash] = useState<string | null>(() => readYouTubeAuthReturnHash());

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await api<Partial<YouTubeAuthStatus>>("/workspace-ai/youtube-auth");
        if (!active || !res || typeof res.auth_mode !== "string") return;
        const parsed: YouTubeAuthStatus = {
          enabled: Boolean(res.enabled),
          global_enabled: Boolean(res.global_enabled ?? res.enabled),
          scope: res.scope,
          active_single_video_grants:
            typeof res.active_single_video_grants === "number"
              ? res.active_single_video_grants
              : 0,
          auth_mode:
            res.auth_mode === "browser" || res.auth_mode === "cookie_file"
              ? res.auth_mode
              : "disabled",
          browser_name: typeof res.browser_name === "string" ? res.browser_name : "",
          supported_browsers: Array.isArray(res.supported_browsers) && res.supported_browsers.length
            ? res.supported_browsers
            : DEFAULT_AUTH_BROWSERS,
          cookie_configured: Boolean(res.cookie_configured),
          daily_limit: typeof res.daily_limit === "number" ? res.daily_limit : 20,
          used_today: typeof res.used_today === "number" ? res.used_today : 0,
          cooldown_seconds: typeof res.cooldown_seconds === "number" ? res.cooldown_seconds : 15,
          circuit_open: Boolean(res.circuit_open),
        };
        setStatus(parsed);
        setMode(parsed.auth_mode);
        if (parsed.browser_name) setBrowser(parsed.browser_name);
        setDailyLimit(parsed.daily_limit);
      } catch {
        // tolerate absent mock endpoint cleanly
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const syncScroll = () => {
      setReturnHash(readYouTubeAuthReturnHash());
      if (location.hash.startsWith("#Settings/youtube-auth")) {
        setDeepLinked(true);
        const scrollToPanel = () => {
          panelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
          panelRef.current?.focus?.({ preventScroll: true });
        };
        const t1 = setTimeout(scrollToPanel, 40);
        const t2 = setTimeout(scrollToPanel, 180);
        return () => {
          clearTimeout(t1);
          clearTimeout(t2);
        };
      }
      setDeepLinked(false);
      return undefined;
    };
    let cleanupScroll = syncScroll();
    const onHash = () => {
      cleanupScroll?.();
      cleanupScroll = syncScroll();
    };
    window.addEventListener("hashchange", onHash);
    return () => {
      cleanupScroll?.();
      window.removeEventListener("hashchange", onHash);
    };
  }, []);

  const saveAuth = async () => {
    setSaving(true);
    setFeedback(null);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        enabled: mode !== "disabled",
        auth_mode: mode,
        daily_limit: dailyLimit,
      };
      if (mode === "browser") payload.browser_name = browser;
      if (mode === "cookie_file" && cookiesTxt.trim()) payload.cookies_txt = cookiesTxt;
      const res = await put<YouTubeAuthStatus>("/workspace-ai/youtube-auth", payload);
      setStatus(res);
      setCookiesTxt("");
      setFeedback(
        mode === "disabled"
          ? zh
            ? "已切回默认纯免登模式。"
            : "Switched back to anonymous-only mode."
          : zh
            ? "已保存 YouTube 兜底授权（仅在免登失败时按需启用）。"
            : "YouTube fallback authorization saved (used only when anonymous fetch is blocked).",
      );
    } catch (reason) {
      setError(
        reason instanceof ApiRequestError
          ? reason.message
          : zh
            ? "保存授权失败，请核对格式后重试。"
            : "Could not save YouTube fallback authorization.",
      );
    } finally {
      setSaving(false);
    }
  };

  const disconnectGlobal = async () => {
    setSaving(true);
    setFeedback(null);
    setError(null);
    try {
      const res = await post<YouTubeAuthStatus>("/workspace-ai/youtube-auth/disconnect", {
        scope: "global",
      });
      setStatus(res);
      setMode("disabled");
      setCookiesTxt("");
      setConfirmRevokeAll(false);
      setFeedback(
        zh
          ? "已断开全局备用授权并清除全局 Cookie（未影响进行中或未到期的单视频临时授权）。"
          : "Global fallback disconnected and global cookies purged.",
      );
    } catch {
      setError(zh ? "断开全局授权失败，请重试。" : "Could not disconnect global fallback.");
    } finally {
      setSaving(false);
    }
  };

  const revokeAll = async () => {
    setSaving(true);
    setFeedback(null);
    setError(null);
    try {
      const res = await post<YouTubeAuthStatus>("/workspace-ai/youtube-auth/disconnect", {
        scope: "all",
        confirm_all: true,
      });
      setStatus(res);
      setMode("disabled");
      setCookiesTxt("");
      setConfirmRevokeAll(false);
      setFeedback(
        zh
          ? "已撤销全部授权（含全局备用与所有待使用单视频授权）并清除已存凭据。"
          : "All global and single-video authorizations revoked and credentials purged.",
      );
    } catch {
      setError(zh ? "撤销全部授权失败，请重试。" : "Could not revoke all authorizations.");
    } finally {
      setSaving(false);
    }
  };

  const browsers = status?.supported_browsers ?? DEFAULT_AUTH_BROWSERS;
  const statusLabel = status?.enabled
    ? status.auth_mode === "browser"
      ? zh
        ? `已授权 · 本机 ${status.browser_name}（今日已用 ${status.used_today}/${status.daily_limit}）`
        : `Authorized · ${status.browser_name} (${status.used_today}/${status.daily_limit} today)`
      : zh
        ? `已授权 · Cookies 凭据（今日已用 ${status.used_today}/${status.daily_limit}）`
        : `Authorized · Cookies (${status.used_today}/${status.daily_limit} today)`
    : zh
      ? "未启用（仅免登录直采 · 默认推荐）"
      : "Disabled (anonymous-first only · default)";

  return (
    <section
      ref={panelRef}
      id="settings-youtube-auth"
      tabIndex={-1}
      className={`panel youtube-auth-card${deepLinked ? " is-deep-link-target" : ""}`}
      aria-label={zh ? "YouTube 采集登录兜底（按需）" : "YouTube Auth Fallback (On Demand)"}
    >
      <div className="panel-head">
        <h2>
          <PhosphorIcon name="shield-check" size={16} className="panel-title-icon" />
          <span>{zh ? "YouTube 采集登录兜底（按需）" : "YouTube Auth Fallback (On Demand)"}</span>
        </h2>
        <span className={`curated-state-badge ${status?.enabled ? "is-ready" : ""}`}>
          {statusLabel}
        </span>
      </div>
      <p className="hint">
        {zh
          ? "默认优先免登录直采以保护账号安全；仅当 YouTube 明确要求验证时才动用授权，内置单日限额与 30 分钟熔断保护。"
          : "Anonymous-first by default to protect your account. Authorized fallback runs only when YouTube demands sign-in, with daily caps and 30-min circuit breaker."}
      </p>

      {status?.circuit_open ? (
        <p className="form-error" role="status">
          {zh
            ? "⚠️ 触发账号保护熔断（上次请求被限流或要求验证），30 分钟内已自动暂停登录兜底，需等待冷却结束后自动恢复（重新保存或断开不会提前解除熔断）。"
            : "⚠️ Account protection circuit breaker active (30 min pause after rate-limit/auth rejection; auto-recovers after cooldown)."}
        </p>
      ) : null}
      {(status?.active_single_video_grants ?? 0) > 0 ? (
        <p className="hint" role="status">
          {zh
            ? `当前另有 ${status?.active_single_video_grants} 条临时单视频授权生效中（各自独立隔离凭据，不开启全局授权）。`
            : `${status?.active_single_video_grants} isolated single-video grant(s) currently active (global fallback stays disabled).`}
        </p>
      ) : null}

      <div className="youtube-auth-controls">
        <label className="field">
          {zh ? "兜底方式" : "Fallback mode"}
          <select
            aria-label={zh ? "YouTube 兜底方式" : "YouTube fallback mode"}
            value={mode}
            disabled={saving}
            onChange={(e) => setMode(e.target.value as "disabled" | "browser" | "cookie_file")}
          >
            <option value="disabled">{zh ? "不启用（仅免登录直采）" : "Disabled (anonymous only)"}</option>
            <option value="browser">
              {zh ? "授权读取本机已登录浏览器（如 Chrome）" : "Use signed-in local browser"}
            </option>
            <option value="cookie_file">
              {zh ? "导入 cookies.txt（仅加密存钥匙串）" : "Import cookies.txt (Keychain only)"}
            </option>
          </select>
        </label>

        {mode === "browser" ? (
          <>
            <label className="field">
              {zh ? "选择已登录 YouTube 的浏览器" : "Browser"}
              <select
                aria-label={zh ? "选择已登录 YouTube 的浏览器" : "Authorized browser"}
                value={browser}
                disabled={saving}
                onChange={(e) => setBrowser(e.target.value)}
              >
                {browsers.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </label>
            <p className="hint">
              {zh
                ? "首次触发 Chrome 等浏览器兜底时，macOS 可能弹窗询问“允许访问钥匙串以解密 Cookie”，点击“允许”即可。"
                : "macOS may prompt once for Keychain access to read encrypted browser cookies."}
            </p>
          </>
        ) : null}

        {mode === "cookie_file" ? (
          <div className="cookie-import-box">
            <input
              ref={cookieFileRef}
              type="file"
              accept=".txt,text/plain"
              hidden
              onChange={async (e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                setCookiesTxt(await file.text());
              }}
            />
            <div className="button-row">
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={() => cookieFileRef.current?.click()}
              >
                {zh ? "选择 cookies.txt 文件…" : "Choose cookies.txt…"}
              </button>
              <span className="hint">
                {status?.cookie_configured
                  ? zh
                    ? "钥匙串中已有 Cookie（不覆盖可留空）"
                    : "Cookies already stored in Keychain"
                  : zh
                    ? "使用浏览器扩展导出 Netscape 格式 cookies.txt"
                    : "Netscape format cookies.txt"}
              </span>
            </div>
            <label className="field">
              {zh ? "或直接粘贴 cookies.txt 内容" : "Or paste Netscape cookies.txt"}
              <textarea
                aria-label={zh ? "YouTube cookies.txt 内容" : "YouTube cookies.txt content"}
                rows={3}
                value={cookiesTxt}
                placeholder="# Netscape HTTP Cookie File..."
                disabled={saving}
                onChange={(e) => setCookiesTxt(e.target.value)}
              />
            </label>
          </div>
        ) : null}

        {mode !== "disabled" ? (
          <label className="field">
            {zh ? "每日登录兜底上限（保护账号风控）" : "Daily auth fallback cap"}
            <select
              aria-label={zh ? "每日登录兜底上限" : "Daily fallback cap"}
              value={dailyLimit}
              disabled={saving}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
            >
              <option value={5}>{zh ? "5 次 / 天（保守）" : "5 / day (Conservative)"}</option>
              <option value={20}>{zh ? "20 次 / 天（推荐）" : "20 / day (Recommended)"}</option>
              <option value={50}>{zh ? "50 次 / 天（上限）" : "50 / day (Max)"}</option>
            </select>
          </label>
        ) : null}
      </div>

      <div className="button-row">
        <button
          type="button"
          className="button button-primary"
          disabled={saving}
          onClick={() => void saveAuth()}
        >
          {saving ? (zh ? "正在保存…" : "Saving…") : zh ? "保存授权设置" : "Save authorization"}
        </button>
        {returnHash ? (
          <a
            className={feedback ? "button button-primary" : "button button-ghost"}
            href={returnHash}
          >
            {zh ? "返回原视频继续获取 ›" : "Back to video & retry ›"}
          </a>
        ) : null}
        {(status?.enabled || status?.cookie_configured) ? (
          <button
            type="button"
            className="button button-ghost"
            disabled={saving}
            onClick={() => void disconnectGlobal()}
          >
            {zh ? "断开全局备用授权" : "Disconnect global fallback"}
          </button>
        ) : null}
        {((status?.active_single_video_grants ?? 0) > 0 ||
          status?.enabled ||
          status?.cookie_configured) ? (
          confirmRevokeAll ? (
            <>
              <button
                type="button"
                className="button button-danger button-small"
                disabled={saving}
                onClick={() => void revokeAll()}
              >
                {zh ? "确认撤销全部授权" : "Confirm revoke all"}
              </button>
              <button
                type="button"
                className="button button-ghost button-small"
                disabled={saving}
                onClick={() => setConfirmRevokeAll(false)}
              >
                {zh ? "取消" : "Cancel"}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="button button-ghost"
              disabled={saving}
              onClick={() => setConfirmRevokeAll(true)}
            >
              {zh ? "撤销全部授权（含临时单视频）" : "Revoke all authorizations"}
            </button>
          )
        ) : null}
      </div>
      {feedback ? <p role="status">{feedback}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
