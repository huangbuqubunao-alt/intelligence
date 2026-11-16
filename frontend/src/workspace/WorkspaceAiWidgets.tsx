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
  start_ms: number | null;
  end_ms: number | null;
  timestamp_label: string;
  excerpt: string;
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
  scope_label_zh: string;
  video_count?: number;
  scope?: AiResearchSessionScope;
  pinned: boolean;
  answer_zh: string;
  key_takeaways_zh: string[];
  action_items_zh: string[];
  citations: AiResearchCitation[];
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

export type TopicAiEvolution = {
  video_count: number;
  must_watch_count: number;
  unread_count: number;
  recent_7d_count: number;
  avg_score: number | null;
  latest_headline_zh: string;
  synthesis_zh: string;
  independence_summary_zh: string;
  top_opportunities_zh: string[];
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
let pendingTopicClusterName = "";
let pendingIntelligenceTopicId = "";
let pendingResearchVideoIds: string[] = [];

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
  return {
    session_id: raw.session_id,
    question: typeof raw.question === "string" ? raw.question : "",
    scope_label_zh: typeof raw.scope_label_zh === "string" ? raw.scope_label_zh : "",
    ...(typeof raw.video_count === "number" ? { video_count: raw.video_count } : {}),
    ...(scope ? { scope } : {}),
    pinned,
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
  return {
    video_count: raw.video_count,
    must_watch_count: typeof raw.must_watch_count === "number" ? raw.must_watch_count : 0,
    unread_count: typeof raw.unread_count === "number" ? raw.unread_count : 0,
    recent_7d_count: typeof raw.recent_7d_count === "number" ? raw.recent_7d_count : 0,
    avg_score: typeof raw.avg_score === "number" ? raw.avg_score : null,
    latest_headline_zh: typeof raw.latest_headline_zh === "string" ? raw.latest_headline_zh : "",
    synthesis_zh: typeof raw.synthesis_zh === "string" ? raw.synthesis_zh : "",
    independence_summary_zh:
      typeof raw.independence_summary_zh === "string" ? raw.independence_summary_zh : "",
    top_opportunities_zh: strArr(raw.top_opportunities_zh),
    source_channels: strArr(raw.source_channels),
    channel_breakdown,
    related_topics,
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
    <span className={`ai-score-pill tabular-nums ${toneClass}${compact ? " is-compact" : ""}`}>
      <strong>{brief.score.toFixed(1)}</strong>
      <span>· {tierLabel}</span>
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
  aiBrief,
  obsidianMarkdown,
  nextUnreadVideo,
  onAdvanceToVideo,
  onBack,
  onCompleted,
}: {
  videoId: string;
  title: string;
  channelName?: string | null;
  sourceUrl?: string | null;
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  isLocalMedia: boolean;
  transcriptAvailable: boolean;
  aiBrief: VideoAiBrief | null;
  obsidianMarkdown?: string;
  nextUnreadVideo?: {
    videoId: string;
    title: string;
    remainingCount: number;
    scoped?: boolean;
  } | null;
  onAdvanceToVideo?: (nextId: string) => void;
  onBack?: () => void;
  onCompleted: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [busyKind, setBusyKind] = useState<"distill" | "transcribe" | "curation" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedObsidian, setCopiedObsidian] = useState(false);
  const [copiedPlainBrief, setCopiedPlainBrief] = useState(false);

  useEffect(() => {
    setCopiedObsidian(false);
    setCopiedPlainBrief(false);
  }, [videoId]);

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

  const markReadAndAdvance = async () => {
    if (busyKind !== null || !nextUnreadVideo || !onAdvanceToVideo) return;
    setBusyKind("curation");
    setError(null);
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
          {nextUnreadVideo && onAdvanceToVideo ? (
            <button
              type="button"
              className="button button-secondary button-small tabular-nums"
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
          <span className="kb-shortcut-hint" aria-hidden="true">
            {zh ? "快捷键：S 收藏 · E 已读下一篇 · U 返回" : "Keys: S star · E read/next · U back"}
          </span>
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
              [[{brief.topic_cluster_zh}]]
            </button>
          ) : (
            <span className="ai-topic-tag">[[{brief.topic_cluster_zh}]]</span>
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
  "OpenAI、Greg Isenberg 与本地实战课对 AI Agent 产品落地有什么共识与分歧？",
  "从现有内容库中，适合一人公司切入的高毛利 AI SaaS 方向有哪些？",
  "多模态与智能助理课程里有哪些可以直接复用的产品交互模式？",
];

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
          const cleanQuote = stripWiki((c.excerpt ?? "").replace(/\s+/g, " ").trim());
          return cleanQuote
            ? `- [${c.ref_label}] ${titlePart}${metaPart}："${cleanQuote}"`
            : `- [${c.ref_label}] ${titlePart}${metaPart}`;
        }),
      ].join("\n"),
    );
  }
  return lines.join("\n\n");
}

export function WorkspaceAiResearchPanel({
  onOpen,
  onAiReady,
  handoffSeq,
}: {
  onOpen: OpenResearchSource;
  onAiReady?: () => void;
  handoffSeq?: number;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [sessions, setSessions] = useState<AiResearchSession[]>([]);
  const [suggested, setSuggested] = useState<string[]>(FALLBACK_QUESTIONS_ZH);
  const [scopeOptions, setScopeOptions] = useState<ResearchScopeOptions | null>(null);
  const [selectedChannel, setSelectedChannel] = useState(() => consumePendingResearchChannel());
  const [selectedTopic, setSelectedTopic] = useState(() => consumePendingResearchTopicCluster());
  const [starredOnly, setStarredOnly] = useState(() => consumePendingResearchStarredOnly());
  const pendingSessionIdRef = useRef<string>(consumePendingResearchSessionId());
  const initialPendingVideosRef = useRef<string[] | null>(null);
  if (initialPendingVideosRef.current === null) {
    initialPendingVideosRef.current = consumePendingResearchVideoIds();
  }
  const [comparePickerOpen, setComparePickerOpen] = useState(
    () => (initialPendingVideosRef.current?.length ?? 0) > 0,
  );
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>(
    () => initialPendingVideosRef.current ?? [],
  );
  const [compareSelectedOnly, setCompareSelectedOnly] = useState(
    () => (initialPendingVideosRef.current?.length ?? 0) > 0,
  );
  const [compareSearch, setCompareSearch] = useState("");
  const [activeSession, setActiveSession] = useState<AiResearchSession | null>(null);
  const [questionInput, setQuestionInput] = useState("");
  const [sessionSearch, setSessionSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionMutatingId, setSessionMutatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedPlain, setCopiedPlain] = useState(false);
  const questionInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setCopied(false);
    setCopiedPlain(false);
  }, [activeSession?.session_id]);

  useEffect(() => {
    const nextSid = consumePendingResearchSessionId();
    if (nextSid) {
      pendingSessionIdRef.current = nextSid;
      const matched = sessions.find((s) => s.session_id === nextSid);
      if (matched) {
        setActiveSession(matched);
        pendingSessionIdRef.current = "";
      }
    }
    const nextVids = consumePendingResearchVideoIds();
    if (nextVids.length > 0) {
      setStarredOnly(false);
      setSelectedChannel("");
      setSelectedTopic("");
      setSelectedVideoIds(nextVids);
      setComparePickerOpen(true);
      setCompareSelectedOnly(true);
      setCompareSearch("");
      queueMicrotask(() => questionInputRef.current?.focus());
    } else if ((initialPendingVideosRef.current?.length ?? 0) > 0) {
      initialPendingVideosRef.current = [];
      queueMicrotask(() => questionInputRef.current?.focus());
    }
    const nextCh = consumePendingResearchChannel();
    if (nextCh) setSelectedChannel(nextCh);
    const nextTp = consumePendingResearchTopicCluster();
    if (nextTp) setSelectedTopic(nextTp);
    if (consumePendingResearchStarredOnly()) setStarredOnly(true);
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
          pendingSessionIdRef.current = "";
          const matched = wantedId
            ? parsedSessions.find((s) => s.session_id === wantedId)
            : undefined;
          setActiveSession(matched ?? parsedSessions[0]);
        }
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

  const hasActiveScope = Boolean(
    starredOnly || selectedChannel || selectedTopic || selectedVideoIds.length > 0,
  );

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
        if (starredOnly) payload.starred_only = true;
        if (selectedChannel) payload.channel_key = selectedChannel;
        if (selectedTopic) payload.topic_cluster = selectedTopic;
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
      setStarredOnly(Boolean(activeScopeMeta.starred_only));
      setSelectedChannel(activeScopeMeta.channel_key ?? "");
      setSelectedTopic(activeScopeMeta.topic_cluster ?? "");
      setSelectedVideoIds(activeExplicitVideoIds);
      setComparePickerOpen(activeExplicitVideoIds.length > 0);
    } else if (activeCitedVideoIds.length > 0) {
      setStarredOnly(false);
      setSelectedChannel("");
      setSelectedTopic("");
      setSelectedVideoIds(activeCitedVideoIds.slice(0, 12));
      setComparePickerOpen(true);
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
                  aria-pressed={selectedChannel === ch.key && selectedVideoIds.length === 0}
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
            {starredOnly || (scopeOptions?.starred_count ?? 0) > 0 ? (
              <button
                type="button"
                className={`ai-question-chip tabular-nums${starredOnly && selectedVideoIds.length === 0 ? " is-active" : ""}`}
                aria-pressed={starredOnly && selectedVideoIds.length === 0}
                disabled={busy}
                onClick={() => {
                  setSelectedVideoIds([]);
                  setStarredOnly((prev) => !prev);
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
                  setStarredOnly(false);
                  setSelectedChannel("");
                  setSelectedTopic("");
                  setSelectedVideoIds([]);
                  setComparePickerOpen(false);
                  setCompareSelectedOnly(false);
                  setCompareSearch("");
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
                const hay = `${v.title} ${v.channel_name} ${v.topic_cluster_zh}`.toLowerCase();
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

      <form className="ai-research-ask-form" onSubmit={handleSubmit}>
        <input
          ref={questionInputRef}
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
  const [exportingObsidianZip, setExportingObsidianZip] = useState(false);
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
                  : "Export Obsidian Vault (.zip)"}
            </button>
            <button
              type="button"
              className="button button-ghost"
              disabled={exportingBackup || exportingObsidianZip || restoringBackup}
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
