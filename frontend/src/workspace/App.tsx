import { AddEntry } from "./AddEntry";
import { TrackedContentRetry, readTrackedRetry, trackedRetryActive } from "./TrackedContentRetry";
import { validFollowingDetailRead, validFollowingSourceRead } from "./CreatorFollowing";
import { InterestRulesEditor, interestRuleValues, ruleDrafts, validInterestRule, type InterestRuleDraft, CreatorFollowForm, CreatorFollowingDetail, FollowCreatorFromContent, Tracking, trackingCopy, useCreatorFollowingCapability } from "./CreatorFollowing";
import { BilibiliImport, BilibiliCaptionStatus, bilibiliStatus } from "./BilibiliImport";
import { LocalImport, localStatus, localImportErrors } from "./LocalImport";
import { NativeImportActivity } from "./NativeLocalImport";
import { LocalTranscription, transcriptionCopy } from "./LocalTranscription";
import { TranscriptionSetup } from "./TranscriptionSetup";
import { LocalIntelligenceSetup } from "./LocalIntelligenceSetup";
import { ChangeEvent, createContext, FormEvent, ReactNode, Suspense, lazy, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { ApiRequestError, api, patch, post, put, uploadZip } from "../api/client";
import {
  buildMarkdownVideoNote,
  cleanCaptionText,
  cleanTimedSegments,
  cleanTranslatedCaptionText,
  dedupeSummaryPoints,
} from "./captionClean";
import { ModelSettings } from "./ModelSettings";
import { formatMicroCny } from "./CloudSpendingSettings";
import { Logo } from "./Logo";
import { BookmarkSparkIcon, DistillOrbitIcon, NavIcon, prefersReducedMotion, pulseCelebration, readCurrentLogicalHash, runViewTransition, scheduleSafeHashUpdate, VerifiedSealIcon } from "./motion";
import { FirstRunOnboarding, completeOnboarding, onboardingCompleted } from "./Onboarding";
import { DeltaTarget, KnowledgeDelta } from "./KnowledgeDelta";
import { Research } from "./Research";
import type { CommandPaletteAction } from "./ui/CommandPalette";

const LazyCommandPalette = lazy(() =>
  import("./ui/CommandPalette").then((m) => ({ default: m.CommandPalette })),
);
const preloadCommandPalette = () => {
  void import("./ui/CommandPalette");
};
import { PhosphorIcon, PhosphorIconName } from "./ui/phosphorIcons";
import { UiThemeProvider, useUiTheme } from "./ui/theme";
import { savedLanguage, UiLanguageProvider, useUiLanguage } from "./uiLanguage";
import {
  AiScoreBadge,
  consumePendingContentChannel,
  consumePendingContentTopic,
  consumePendingIntelligenceTopicId,
  consumePendingTopicClusterName,
  exportObsidianVaultBundle,
  isKeyboardShortcutBlocked,
  readSourceAiSignalMap,
  readTopicAiEvolution,
  readVideoAiBrief,
  readWeeklyAiBrief,
  readWorkspaceAiCapabilities,
  readWorkspaceAiSettings,
  setPendingContentChannel,
  setPendingContentTopic,
  setPendingIntelligenceTopicId,
  setPendingResearchChannel,
  setPendingResearchSessionId,
  setPendingResearchStarredOnly,
  setPendingResearchTopicCluster,
  setPendingResearchVideoIds,
  setPendingTopicClusterName,
  TopicObsidianExportBar,
  VideoAiBrief,
  WeeklyAiBriefPanel,
  WorkspaceAiSettingsPanel,
  WorkspaceVideoAiActions,
  WorkspaceVideoAiBriefCard,
  compareContentNewestFirst,
} from "./WorkspaceAiWidgets";

type Page =
  | "Home"
  | "Following"
  | "Content"
  | "Intelligence"
  | "Topics"
  | "Research"
  | "Settings";
type SourcePolicyModes = { focus: "INHERIT" | "OVERRIDE"; ignore: "INHERIT" | "OVERRIDE"; style: "INHERIT" | "OVERRIDE" };
type EvidenceDisplayMode = "译文" | "双语" | "原文";
type Intelligence = {
  status: string;
  trusted: boolean;
  code?: string;
  intelligence_id?: string;
  claim_kind?: string;
  state?: string;
  effective_published_at?: string | null;
  linked_topics?: { topic_id: string; name: string }[];
  card?: {
    core_conclusion: string;
    user_relevant_information: string[];
    important_new_information: string[];
    meaningful_details: string[];
    source_id: string;
    source_display_name: string | null;
    source_url: string | null;
    video_id: string;
    video_title: string | null;
    original_video_url: string | null;
    evidence_links: {
      evidence_id: string;
      artifact_id: string;
      start_ms: number | null;
      end_ms: number | null;
      locator_type?: "TEXT_RANGE" | "TIMED_MEDIA" | null;
      start_line?: number | null;
      end_line?: number | null;
      language: string;
      lineage_kind: string;
      role: string;
      original_excerpt: string | null;
      translated_excerpt: string | null;
      translated_language: string | null;
      translation_target_language?: "zh-CN" | "en";
      stance: "supporting" | "contradicting" | "conditional" | null;
    }[];
  };
};
type Saved = {
  intelligence_id: string;
  saved_at: string;
  intelligence: Intelligence;
};
type Topic = {
  topic_id: string;
  name: string;
  pinned: boolean;
  lifecycle: string;
  current_state: string;
  independence: string;
  ai_evolution?: unknown;
  contributions: {
    intelligence_id: string;
    claim_kind: string;
    state: string;
    available: boolean;
    evidence_ids: string[];
  }[];
  timeline: {
    event_id: string;
    event_kind: string;
    state: string;
    created_at: string;
  }[];
  relations: { related_topic_id: string; related_topic_name?: string }[];
};
type Source = {
  source_type?: string;
  tracking_parent_source_ids?: string[];
  tracking?: Tracking | null;
  insight_count?: number;
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  source_id: string;
  display_name: string | null;
  friendly_name?: string | null;
  channel_id?: string | null;
  video_id?: string | null;
  canonical_url: string;
  enabled: boolean;
  processing_policy: string;
  last_error: { code: string } | null;
};
type SourceRun = {
  run_id: string;
  state: string;
  attention_reason: string | null;
  trigger: string;
  updated_at: string;
  source_id?: string;
  source_type?: string;
  video_id?: string | null;
  source_label?: string | null;
};
type SourcePolicy = {
  source_policy_revision_id?: string | null;
  initial_history_count: number;
  per_run_max_new_videos: number;
  focus_rules: string[];
  ignore_rules: string[];
  distillation_style: string;
};
type Schedule = {
  schedule_id: string;
  frequency: string;
  weekday?: number | null;
  local_time: string | null;
  timezone?: string;
  enabled: boolean;
};
type Preference = {
  preference_id: string;
  horizon: string;
  provenance: string;
  statement: string;
  expires_at: string | null;
};
type ResourceUsage = {
  execution_id: string;
  reason: string;
  actual_provider: string | null;
  actual_model: string | null;
  status: string;
  invocation_count: number;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_microunits: number | null;
  duration_ms: number | null;
  budget_state: string;
};
type ContentItem = {
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  work_kind?: string;
  source_id?: string;
  retry_allowed?: boolean;
  tracked_content_retry?: unknown;
  caption_timing_status?: string;
  summary_preparation_status?: string;
  processing_job?: { status: string; stage: string; retry_at: string | null; error_code: string | null } | null;
  filename?: string;
  media_kind?: string;
  format?: string;
  imported_at?: string;
  source_language?: string | null;
  duration_seconds?: number | null;
  ai_brief?: unknown;
  video_id: string;
  channel_id: string;
  channel_name: string;
  title: string | null;
  source_url: string | null;
  published_at: string;
  processing_status: string;
  last_updated: string;
};
type ContentDetail = {
  local_intelligence?: unknown;
  obsidian_markdown?: string;
  workspace_ai_capabilities?: unknown;
  video: ContentItem;
  pending_synthesis_executions?: { execution_id: string; updated_at: string; can_cancel: boolean; selected_provider?: string }[];
  waiting_model_executions?: { execution_id: string; updated_at: string; can_cancel: boolean; selected_provider?: string }[];
  cloud_intelligence_available?: boolean;
  manual_intelligence_eligible?: boolean;
  transcript: {
    timed_segments?: { start_ms: number; end_ms: number; text: string }[];
    status: string;
    text?: string;
    reason?: string;
    created_at?: string;
  };
  note: {
    v1?: { status: string; code?: string };
    v2?: {
      status: string;
      code?: string;
      note_identity?: string;
      result_identity?: string;
      language?: string;
      method?: string;
      summary?: string | null;
      core_points?: string[];
      timestamped_key_points?: {
        text: string;
        start_seconds: number;
        end_seconds: number;
        evidence_ids: string[];
      }[];
      evidence_references?: {
        evidence_id: string;
        source: string;
        excerpt: string;
        start_seconds: number | null;
        end_seconds: number | null;
      }[];
    };
  };
  intelligence_result: {
    selected_provider?: string;
    can_cancel?: boolean;
    cloud_http429_code?: string;
    status: string;
    execution_id: string | null;
    has_new_intelligence: boolean | null;
    intelligence_id: string | null;
    revision_id: string | null;
    updated_at: string | null;
  };
  history: {
    timestamp: string;
    type?: string;
    status: string;
    summary: string;
    code?: string | null;
    context?: { stage?: string };
  }[];
};
type LocalScope = "YT_TIMED" | "LOCAL_TIMED" | "LOCAL_TEXT";
type LocalBinding = { provider: string; model: string; profile_id: string | null };
type LocalScopeStatus = { scope: LocalScope; output_language: "en" | "zh-CN"; model: string; profile_id: string; status: "QUALIFIED" | "NOT_QUALIFIED" };
type LocalMatrix = { status: "KNOWN"; model: string; profile_id: string; runtime_binding: LocalBinding | null; scopes: LocalScopeStatus[] };
type ContentLocalCapability = { video_id: string; scope: LocalScope; output_language: "en" | "zh-CN"; model: string; profile_id: string;
  runtime_binding: LocalBinding; qualification_status: "QUALIFIED" | "NOT_QUALIFIED";
  request_state: "WAITING_MODEL" | "ELIGIBLE_FOR_ADMISSION" | "UNKNOWN" | "CONFIGURATION_REQUIRED"; reason: string };
const localObject = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const localText = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const localScope = (value: unknown): value is LocalScope => value === "YT_TIMED" || value === "LOCAL_TIMED" || value === "LOCAL_TEXT";
const localBinding = (value: unknown): value is LocalBinding => localObject(value) && localText(value.provider) && localText(value.model)
  && (value.profile_id === null || localText(value.profile_id));
function readLocalMatrix(value: unknown): LocalMatrix | null {
  if (!localObject(value) || value.status !== "KNOWN" || !localText(value.model) || !localText(value.profile_id)
      || !(value.runtime_binding === null || localBinding(value.runtime_binding)) || !Array.isArray(value.scopes) || value.scopes.length !== 6) return null;
  const pairs = new Set<string>();
  for (const row of value.scopes) {
    if (!localObject(row) || !localScope(row.scope) || !["en", "zh-CN"].includes(row.output_language as string)
        || row.model !== value.model || row.profile_id !== value.profile_id || !["QUALIFIED", "NOT_QUALIFIED"].includes(row.status as string)) return null;
    pairs.add(`${row.scope}/${row.output_language}`);
  }
  return pairs.size === 6 ? value as LocalMatrix : null;
}
function readContentLocal(value: unknown, video: ContentItem, id: string): ContentLocalCapability | null {
  if (!localObject(value) || value.video_id !== id || !localScope(value.scope) || !["en", "zh-CN"].includes(value.output_language as string)
      || !localText(value.model) || !localText(value.profile_id) || !localBinding(value.runtime_binding)
      || !["QUALIFIED", "NOT_QUALIFIED"].includes(value.qualification_status as string)) return null;
  if (video.provider === "YOUTUBE" ? value.scope !== "YT_TIMED" : video.provider !== "LOCAL" || value.scope === "YT_TIMED"
      || (video.media_kind === "TEXT" && value.scope !== "LOCAL_TEXT") || (["AUDIO", "VIDEO"].includes(video.media_kind ?? "") && value.scope !== "LOCAL_TIMED")) return null;
  const matches = value.runtime_binding.provider === "ollama" && value.runtime_binding.model === value.model
    && (value.runtime_binding.profile_id === value.profile_id || value.scope === "YT_TIMED"
      && ((value.profile_id === "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.6-v2"
        && value.runtime_binding.profile_id === "local-grounding-qwen35-9b-runtime-0.40.6-v3")
        || (value.profile_id === "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.9-v3"
        && value.runtime_binding.profile_id === "local-grounding-qwen35-9b-runtime-0.40.9-v4")));
  const consistent = value.request_state === "CONFIGURATION_REQUIRED" && value.reason === "MODEL_CONFIGURATION_REQUIRED" || (value.qualification_status === "NOT_QUALIFIED"
    ? value.request_state === "WAITING_MODEL" && value.reason === "NOT_QUALIFIED"
    : (value.request_state === "ELIGIBLE_FOR_ADMISSION" && matches && value.reason === "ADMISSION_CHECKS_REQUIRED")
      || (value.request_state === "WAITING_MODEL" && (value.reason === "ROUTE_REINITIALIZATION_REQUIRED" && !matches || value.reason === "MODEL_UNAVAILABLE" && matches))
      || (value.request_state === "UNKNOWN" && matches && value.reason === "RESOURCE_STATUS_UNKNOWN"));
  return consistent ? value as ContentLocalCapability : null;
}
const localScopeLabel = (scope: LocalScope) => ({ YT_TIMED: "YouTube timed captions", LOCAL_TIMED: "Local audio/video", LOCAL_TEXT: "Local text documents" })[scope];
const localLanguageLabel = (language: "en" | "zh-CN") => language === "en" ? "English" : "中文";
function LocalIntelligencePresentation({ matrix, content, onReload }: { matrix?: unknown; content?: ContentLocalCapability | null; onReload: () => void }) {
  const { t } = useUiLanguage();
  const known = readLocalMatrix(matrix);
  const label = content !== undefined ? "Local Intelligence for this Content" : "Local Intelligence qualification";
  return <section role="region" aria-label={t(label)} className={content !== undefined ? "local-route-compact" : undefined}>
    {known ? <>
      <p>{t("Target local Intelligence model")}: {known.model}</p>
      <ul>{known.scopes.map(row => <li key={`${row.scope}/${row.output_language}`}>{t(localScopeLabel(row.scope))} · {localLanguageLabel(row.output_language)} · {t(row.status === "QUALIFIED" ? "Quality verification passed" : "Quality verification not passed")}</li>)}</ul>
      <details><summary>{t("Verification profile")}</summary><p className="hint">{known.profile_id}</p></details>
    </> : content ? <>
      <div className="local-route-chips">
        <span>{t("Target local Intelligence model")}: {content.model}</span>
        <span>{t(localScopeLabel(content.scope))} · {localLanguageLabel(content.output_language)}</span>
        <span>{t("Current execution route")}: {content.runtime_binding.model}</span>
        <a className="source-link" href="#Settings">{t("Open model settings")}</a>
      </div>
      <p className="hint">{t(({ MODEL_CONFIGURATION_REQUIRED: "Configure the local Intelligence model in Settings before requesting extraction. No task will be created with the current route.", NOT_QUALIFIED: "This source type and output language have not passed local Intelligence quality verification. A request will wait without running a model.",
        ROUTE_REINITIALIZATION_REQUIRED: "The verified model does not match the current route. Restart the local service to reinitialize it; extraction will wait.",
        MODEL_UNAVAILABLE: "The qualified model is unavailable. A request will wait; check local model setup.",
        RESOURCE_STATUS_UNKNOWN: "Local model resource status is unknown. Read the status again before requesting extraction.",
        ADMISSION_CHECKS_REQUIRED: "Qualified for this source and output language. Admission checks still apply." } as Record<string, string>)[content.reason])}</p>
    </> : <p role="status">{t("Local Intelligence status is unknown. Read the status again before requesting extraction.")}</p>}
    {(!known && !content || content?.request_state === "UNKNOWN") && <button type="button" className="button button-secondary" onClick={onReload}>{t("Retry local Intelligence status")}</button>}
    {content !== undefined && !content && <a href="#Settings">{t("Open model settings")}</a>}
  </section>;
}
type DeepAnalysisRole = {
  role: string;
  text: string;
  point_kind: string;
  confidence: string;
  evidence_ids?: string[];
  language_validation?: "VALID" | "UNCERTAIN";
};
const DEEP_ANALYSIS_ROLE_ORDER = [
  "CORE_CONCLUSION",
  "KEY_EVIDENCE",
  "UNCERTAINTY",
  "RELEVANCE_TO_USER",
  "NEXT_QUESTION",
] as const;
type DeepAnalysisPayload = {
  content_id: string;
  result_identity: string;
  content_identity: string;
  output_language: string;
  generated_at: string;
  evidence_citation_status: string;
  roles: DeepAnalysisRole[];
};
type DeepAnalysisRouteState = {
  route_id: string; provider_id: string; model_id: string;
  configured: boolean; credential_configured: boolean; reachability: string;
  contract_capable: boolean; qualification_status: string; production_eligible: boolean;
};
type DeepAnalysisPreflight = {
  execution_id: string; route_id: string; provider_id: string; model_id: string;
  credential_configured: boolean; qualification_status: string; data_egress_mode: string;
  cost: { state: "KNOWN" | "ESTIMATED" | "FREE" | "UNKNOWN"; hard_monetary_cap: boolean; input_characters: number };
};
type DeepAnalysisState = {
  status: {
    availability: string;
    reason_code: string | null;
    reason: string | null;
    route_id: string | null;
    model_id: string | null;
    provider_id: string | null;
    qualified: boolean;
    consent_required: boolean;
    production_eligible?: boolean;
    routes?: DeepAnalysisRouteState[];
  };
  result: DeepAnalysisPayload | null;
};
type DeepAnalysisEnvelope = {
  deep_analysis: DeepAnalysisState;
};
type ContentEvidence = {
  provider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
  locator_type?: "TIMED_MEDIA" | "TEXT_RANGE";
  start_line?: number | null;
  end_line?: number | null;
  evidence_id: string;
  artifact_id: string;
  lineage_kind: string;
  role: string;
  source_language: string;
  language: string;
  original_excerpt: string;
  translated_excerpt: string | null;
  translated_language: "zh-CN" | "en" | null;
  translation_target_language: "zh-CN" | "en";
  translation_status: string;
  start_ms: number | null;
  end_ms: number | null;
  created_at: string | null;
  source_url: string | null;
};

const pages: Page[] = [
  "Home",
  "Following",
  "Content",
  "Intelligence",
  "Topics",
  "Settings",
];
const subtitles: Record<Page, string> = {
  Home: "What changed across the knowledge you follow.",
  Following: "Choose what Intelligence should keep watching.",
  Content: "Read ingested content, transcript state, and processing history.",
  Intelligence: "Revisable, evidence-linked judgments worth tracking.",
  Topics: "Current understanding built from related Intelligence.",
  Research: "Inspect a question within selected local library Content.",
  Settings: "Language, interests, processing, and your data.",
};
const commandId = () =>
  `ui:${Date.now()}:${Math.random().toString(36).slice(2)}`;
const INITIAL_HISTORY = [0, 1, 3, 5, 10];
const PER_RUN_LIMIT = [1, 3, 5, 10];
const STYLES = [[
  "BALANCED",
  "Balanced",
  "A useful mix of product, technical, and trend context.",
], [
  "TECHNICAL_DETAIL_FIRST",
  "Technical",
  "Lead with implementation details and trade-offs.",
], [
  "PRODUCT_CASE_FIRST",
  "Product case",
  "Lead with product implications and use cases.",
], [
  "TREND_OPINION_FIRST",
  "Trend and opinion",
  "Lead with the wider trend and attributed viewpoints.",
]] as const;

function initialContentTarget(): string | null {
  const match = /^#Content\/([^/]+)(?:\/Evidence\/[^/]+)?$/.exec(location.hash);
  if (!match) return null;
  try { const value = decodeURIComponent(match[1]); return value && value.length <= 256 && !/[\p{Cc}\p{Cs}]/u.test(value) ? value : null; } catch { return null; }
}

function initialEvidenceTarget(): string | null {
  if (!initialContentTarget()) return null;
  const match = /^#Content\/[^/]+\/Evidence\/([^/]+)$/.exec(location.hash);
  if (!match) return null;
  try {
    const value = decodeURIComponent(match[1]);
    return value && value.length <= 512 && !/[\p{Cc}\p{Cs}]/u.test(value) ? value : null;
  } catch { return null; }
}

function initialPage(): Page {
  const raw = location.hash.slice(1);
  if (/^Settings\/models\/(?:bigmodel|moonshot)(?:\?[^#]+)?$/.test(raw)) return "Settings";
  if (/^Settings\/transcription(?:\/[^/]+)?$/.test(raw)) return "Settings";
  if (raw.startsWith("Content/")) return "Content";
  if (/^Research(?:\/[a-f0-9]{64}(?:\/history\/[a-f0-9]{64}|\/diff\/[a-f0-9]{64}\/[a-f0-9]{64})?)?$/.test(raw)) return "Research";
  const legacy: Record<string, Page> = {
    Dashboard: "Home",
    Sources: "Following",
    Investigations: "Home",
  };
  const candidate = legacy[raw] ?? raw;
  return pages.includes(candidate as Page) ? candidate as Page : "Home";
}

type RemoteSwrStore = {
  cache: Map<string, unknown>;
  inflight: Map<string, Promise<unknown>>;
};

const RemoteSwrContext = createContext<RemoteSwrStore | null>(null);

function useRemote<T>(
  path: string,
  refresh = 0,
  validate?: (value: unknown) => boolean,
  retainOnRefresh = false,
  swr = false,
) {
  const swrStore = useContext(RemoteSwrContext);
  const readSwrCache = (targetPath: string): T | null => {
    if (!swr || !swrStore || !swrStore.cache.has(targetPath)) return null;
    const cached = swrStore.cache.get(targetPath);
    if (validate && !validate(cached)) return null;
    return cached as T;
  };
  const [readRevision, setReadRevision] = useState(0);
  const requestPath = useRef(path);
  const [reading, setReading] = useState(true);
  const [data, setData] = useState<T | null>(() => readSwrCache(path));
  const [error, setError] = useState<string | null>(null);
  // Keep the stable machine code so failures can be localized by code instead of
  // rendering backend English prose.
  const [errorCode, setErrorCode] = useState<string | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    const samePath = requestPath.current === path;
    requestPath.current = path;
    setReading(true);
    const cached = readSwrCache(path);
    if (cached !== null && (!samePath || data === null)) {
      setData(cached);
    } else if (!retainOnRefresh || !samePath) {
      setData(null);
    }
    if (!retainOnRefresh || !samePath || (!data && cached === null)) {
      setError(null); setErrorCode(undefined);
    }
    const loadPromise: Promise<T> = (() => {
      if (swr && swrStore) {
        const existing = swrStore.inflight.get(path) as Promise<T> | undefined;
        if (existing) return existing;
        const created = api<T>(path);
        swrStore.inflight.set(path, created);
        created.finally(() => {
          if (swrStore.inflight.get(path) === created) {
            swrStore.inflight.delete(path);
          }
        }).catch(() => {});
        return created;
      }
      return api<T>(path);
    })();
    loadPromise.then((value) => {
      if (!alive) return;
      if (validate && !validate(value)) {
        throw new ApiRequestError({ code: "READ_RESPONSE_INVALID", message: "The policy response could not be read." });
      }
      if (swr && swrStore) {
        swrStore.cache.set(path, value);
      }
      setData(value); setError(null); setErrorCode(undefined);
    }).catch((reason: Error) => {
      if (swr && swrStore) {
        swrStore.cache.delete(path);
      }
      if (!alive) return;
      setError(reason.message);
      setErrorCode(reason instanceof ApiRequestError ? reason.code : undefined);
    }).finally(() => { if (alive) setReading(false); });
    return () => {
      alive = false;
    };
  }, [path, refresh, readRevision, validate, retainOnRefresh, swr, swrStore]);
  // A path change must never expose another resource's retained snapshot,
  // including the render before the new effect has cleared it.
  const currentPath = !retainOnRefresh || requestPath.current === path;
  const fallbackSwr = !currentPath ? readSwrCache(path) : null;
  return {
    data: currentPath ? data : fallbackSwr,
    error: currentPath ? error : null,
    errorCode: currentPath ? errorCode : undefined,
    reading,
    reload: () => setReadRevision(value => value + 1),
  };
}
function statusLabel(value: string) {
  const labels: Record<string, string> = {
    FETCHING: "Getting content…",
    READING_CAPTIONS: "Reading captions…",
    ORGANIZING: "Organizing content…",
    ORGANIZED: "Completed",
    RETRY_PENDING: "Will retry later",
    RETRY_REQUIRED: "Retry needed",
    WAITING_CONTENT: "Waiting for organized Content",
    WAITING_MODEL: "Waiting for a qualified Intelligence model",
    WAITING_BUDGET: "Waiting for approved resources",
    SUCCEEDED_NO_NEW_INTELLIGENCE: "Completed with no new Intelligence",
    REJECTED_EVIDENCE: "Needs source verification",
    REJECTED_OUTPUT: "Result did not qualify",
    REJECTED_INELIGIBLE: "Not eligible for analysis",
    AVAILABLE: "Available",
    UNAVAILABLE: "Unavailable",
    ENABLED: "Monitoring on",
    DISABLED: "Monitoring off",
    BLOCKED: "Unavailable",
    NEEDS_ATTENTION: "Needs attention",
    SUCCEEDED: "Completed",
    NOT_PROCESSED: "Not processed",
    PENDING: "Waiting",
    RUNNING: "Running",
    NOT_RELEVANT: "Skipped",
    DEGRADED: "Some support is unavailable",
    UNKNOWN: "Not enough reliable information yet",
    UNRESOLVED: "Sources still disagree",
    DISPUTED: "Sources disagree",
    UPDATED: "Updated",
    INVALIDATED: "No longer considered valid",
    OVERTURNED: "Superseded by newer evidence",
    CURRENT_NOT_ACTIVE: "No longer current",
    MODEL_UNAVAILABLE: "Analysis paused",
    EXPLICIT: "Explicit",
    DERIVED: "Derived",
    TEMPORARY: "Temporary",
    TEMPORARY_FOCUS: "Temporary",
    UNQUALIFIED: "Not ready",
    SCHEMA_INVALID: "Not ready",
    ADMITTED: "Approved",
    AMBIGUOUS: "Confirmation needed",
    CORRECTED: "Corrected",
    PINNED: "Pinned",
    ACTIVE: "Active",
    VERIFIED: "Verified",
    SKIPPED: "Skipped",
    DISCOVERED: "Discovered",
    METADATA_READY: "Metadata ready",
    DEFERRED: "Deferred",
    TRANSCRIPT_READY: "Organizing content…",
    SCORED: "Scored",
    LOW_VALUE_READY: "Low-value content",
    ANALYSIS_READY: "Analysis ready",
    NOTE_WRITTEN: "Summary ready",
    COMPLETE: "Complete",
    SKIPPED_DURATION_LIMIT: "Skipped: duration limit",
    QUEUED: "Queued",
    WAITING: "Waiting",
    PARTIAL: "Partially complete",
    COMPLETED: "Completed",
    FAILED: "Failed",
    FAILED_FINAL: "Failed",
    FAILED_RETRYABLE: "Retry pending",
    CANCELLED: "Cancelled",
    SOURCE_CHECK_FAILED: "Source check failed",
    UNCERTAIN: "Needs a relevance decision",
  };
  return labels[value] ??
    value.replaceAll("_", " ").toLowerCase().replace(
      /^./,
      (letter) => letter.toUpperCase(),
    );
}
/**
 * `value` decides the tone and is looked up as an enum. `label` is for text that
 * is already a sentence: without it, a ready-made phrase would be de-CamelCased
 * and lowercased into something the user never sees in any other language.
 */
function Status({ value, label }: { value: string; label?: string }) {
  const { t } = useUiLanguage();
  const upper = value.toUpperCase();
  const tone =
    /AVAILABLE|ENABLED|SUCCEEDED|VERIFIED|ACTIVE|ADMITTED/.test(upper) &&
      !/UNAVAILABLE/.test(upper)
      ? "success"
      : /BLOCKED|ATTENTION|UNAVAILABLE|DEGRADED|UNRESOLVED|SKIPPED|AMBIGUOUS|UNQUALIFIED|INVALID/
          .test(upper)
      ? "warning"
      : "neutral";
  return <span className={`status status-${tone}`}>{label ? t(label) : t(statusLabel(value))}</span>;
}
/**
 * Bilibili and Local Content states carry their own wording, so each is
 * projected through its own copy.  The enum decides the tone and the resolved
 * label is the only text shown — the same contract Creator Following already
 * uses, and the reason a backend sentence is never de-CamelCased into a
 * language the user did not choose.
 */
function contentStatus(provider: string | undefined, status: string, label?: string) {
  return {
    value: status,
    label:
      label ??
      (provider === "LOCAL"
        ? localStatus(status)
        : provider === "BILIBILI"
          ? bilibiliStatus(status)
          : undefined),
  };
}
function Panel({ title, id, icon, className, actions, children }: {
  title: string;
  id?: string;
  icon?: PhosphorIconName;
  className?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useUiLanguage();
  return (
    <section id={id} className={`panel${className ? ` ${className}` : ""}`}>
      <div className="panel-heading">
        <div className="panel-heading-title">
          {icon && <PhosphorIcon name={icon} size={16} className="panel-heading-icon" />}
          <h2>{t(title)}</h2>
        </div>
        {actions && <div className="panel-heading-actions">{actions}</div>}
      </div>
      {children}
    </section>
  );
}
function Empty({ children }: { children: ReactNode }) {
  const { t } = useUiLanguage();
  return <div className="empty-state">{typeof children === "string" ? t(children) : children}</div>;
}
function ErrorState(
  { error, code, hideRawMessage, deepAnalysisSurface, onReload }: {
    error: string;
    code?: string;
    /** Hide raw backend prose; used by normal Deep Analysis product UI. */
    hideRawMessage?: boolean;
    /** Scope Deep Analysis-specific INTERNAL_ERROR copy to Deep Analysis surfaces only. */
    deepAnalysisSurface?: boolean;
    /** Retry this failed GET loader only; never replay a user command. */
    onReload?: () => void;
  },
) {
  const { language, t } = useUiLanguage();
  const readReload = onReload && <button type="button" className="button button-secondary" onClick={onReload}>{t("Reload page data")}</button>;
  // These are browser transport failures, rather than service error prose.
  if (["Failed to fetch", "Load failed", "NetworkError when attempting to fetch resource."].includes(error)) {
    return <div className="semantic-state state-danger" role="alert">
      <p>{t("The local service is disconnected. Reopen Intelligence, then retry when the connection returns.")}</p>
      {onReload && <button type="button" className="button button-secondary" onClick={onReload}>{t("Retry")}</button>}
    </div>;
  }
  if (
    code === "READ_SERVICE_UNAVAILABLE" ||
    code === "READ_RESPONSE_INVALID" ||
    (code === "INTERNAL_ERROR" && !deepAnalysisSurface)
  ) {
    return <div className="semantic-state state-danger" role="alert">
      <p>{t(code === "READ_RESPONSE_INVALID"
        ? "The page could not be loaded because the local service returned an unreadable response. Reload this page to try reading it again."
        : "The local service is temporarily unavailable. Wait for it to recover, then reload this page.")}</p>
      {readReload}
    </div>;
  }
  // When a stable machine code is known, localized copy is the product text.
  // Localizing never relies on matching arbitrary English strings.
  const localized = code ? localizedApiErrorCopy(code) : undefined;
  if (localized) {
    // Normal product UI shows localized copy only. The backend message stays on
    // the error object, in logs, and in debug instrumentation.
    return (
      <div className="semantic-state state-danger">
        <Status value="Blocked" />
        <p>{t(localized)}</p>
        {readReload}
      </div>
    );
  }
  if (hideRawMessage) {
    return (
      <div className="semantic-state state-danger">
        <Status value="Blocked" />
        <p>{t("The operation could not be completed.")}</p>
        {readReload}
      </div>
    );
  }
  return (
    <div className="semantic-state state-danger">
      <Status value="Blocked" />
      {language === "zh-CN" ? <p>{t("The operation could not be completed.")}</p> : null}
      <p>{error}</p>
      {readReload}
    </div>
  );
}

/** Stable API error codes that have localized product copy. */
function localizedApiErrorCopy(code: string): string | undefined {
  const known: Record<string, string> = {
    DEEP_ANALYSIS_NOT_QUALIFIED:
      "Deep Analysis could not run because no model is currently qualified for it.",
    DEEP_ANALYSIS_CLOUD_CONSENT_REQUIRED:
      "This route would send bounded data to a cloud provider and needs your explicit consent for this run.",
    DEEP_ANALYSIS_EVIDENCE_UNAVAILABLE:
      "This Content has no trusted timed transcript Evidence, so Deep Analysis cannot cite anything durably.",
    DEEP_ANALYSIS_CONTENT_UNAVAILABLE: "This Content is not available.",
    DEEP_ANALYSIS_SCORING_UNAVAILABLE:
      "Deep Analysis needs a verified scoring read for this Content. It is unavailable right now.",
    DEEP_ANALYSIS_FAILED:
      "Deep Analysis did not produce a trusted result. No partial or invented result is shown.",
    DEEP_ANALYSIS_UNAVAILABLE: "Deep Analysis is unavailable right now.",
    INTERNAL_ERROR:
      "Deep Analysis could not complete because the local service failed. No result was produced.",
  };
  return known[code];
}
function humanDate(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(savedLanguage(), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
function Claim({ kind }: { kind: string }) {
  const labels: Record<string, string> = {
    FACT: "Fact",
    EVIDENCE_BACKED_STATEMENT: "Supported statement",
    OPINION: "Attributed opinion",
    PREDICTION: "Prediction",
    RUMOR: "Unconfirmed rumor",
    SYSTEM_INFERENCE: "System inference",
  };
  return <Status value={kind} label={labels[kind] ?? kind} />;
}
export function intelligenceValidationCopy(state: string) {
  return ({
    NEW:
      "New Intelligence. It has not reached a confirmed validation state yet.",
    PENDING_CONFIRMATION:
      "Still needs validation. Review the cited Evidence before relying on it.",
    CONFIRMED: "Current trusted state: confirmed.",
    DISPUTED:
      "Still needs validation. Conflicting Evidence or interpretation remains unresolved.",
    UPDATED:
      "Updated. This is the current revision; older revisions are historical.",
  } as Record<string, string>)[state] ?? "Validation state is unavailable.";
}
export function intelligenceResultCopy(status: string, cloudCode?: string, selectedProvider?: string, canCancel?: boolean) {
  if (status === "WAITING_MODEL" && selectedProvider === "zhipu_bigmodel") {
    return "This cloud task is waiting for execution prerequisites. Check the BigModel API key or network in Settings."
      + (canCancel === true
        ? " This cloud execution has not started. You can safely cancel this task."
        : " Cancellation safety has not been verified.");
  }
  if (status === "REJECTED_OUTPUT") {
    const hint = ({
      "1113": "BigModel reported an account balance restriction. Check your provider account; no Intelligence was generated and this task will not retry automatically.",
      "1302": "BigModel reported a request rate limit. Wait before starting a new explicitly authorized task; this task will not retry automatically.",
      "1305": "BigModel reported service congestion. Wait before starting a new explicitly authorized task; this task will not retry automatically.",
      "1308": "BigModel reported an account quota limit. Check the available quota in your provider account; this task will not retry automatically.",
      "1315": "BigModel reported an incompatible API key type. Check the standard API key in Settings; this task will not retry automatically.",
    } as Record<string, string>)[cloudCode ?? ""];
    if (hint && ["1113", "1302", "1305", "1308", "1315"].includes(cloudCode ?? "")) return hint;
  }
  return ({
    CANCELLED: "Extraction cancelled. No Intelligence was generated by this task. Original Content, transcript, Summary and Evidence are preserved.",
    WAITING: "Analysis is waiting for interest rules or another prerequisite. Organized Content remains available.",
    DEFERRED: "Analysis is waiting for interest rules or another prerequisite. Organized Content remains available.",
    NEEDS_ATTENTION: "Analysis needs attention. Review the Content processing history and retry when ready.",
    FAILED: "Analysis needs attention. Review the Content processing history and retry when ready.",
    NOT_PROCESSED: "This Content has not been processed for Intelligence yet.",
    PENDING: "Analysis has not reached a trusted terminal result.",
    WAITING_CONTENT: "Intelligence is waiting for readable Content and trusted source references.",
    WAITING_MODEL: "The current local model cannot reliably create high-quality Intelligence. Your Summary and original Evidence remain available. Cloud Intelligence requires a separate review and explicit authorization.",
    WAITING_BUDGET: "Analysis is waiting for approved budget or resources. Review Settings and the Content processing history.",
    REJECTED_INELIGIBLE: "This Content was not eligible for this Intelligence run. Review the Content processing history for the recorded reason.",
    REJECTED_EVIDENCE: "Analysis could not proceed with trusted Evidence. Check the transcript and original source; no Evidence was invented.",
    REJECTED_OUTPUT: "The generated result did not pass the trusted output checks. Review the Summary and Evidence; no Intelligence was admitted.",
    AMBIGUOUS: "The external processing outcome could not be confirmed safely. It will not be retried automatically, avoiding duplicate paid work.",
    SUCCEEDED: "Analysis completed and admitted new Intelligence.",
    SUCCEEDED_NO_NEW_INTELLIGENCE:
      "Analysis complete — no new Intelligence. The Content and relevant Evidence were checked, and nothing reached the threshold for adding new Intelligence. Existing Intelligence is unchanged.",
  } as Record<string, string>)[status] ??
    "The current Intelligence processing result is unavailable.";
}
function intelligenceStateLabel(state?: string) {
  return ({
    NEW: "New",
    PENDING_CONFIRMATION: "Pending confirmation",
    CONFIRMED: "Confirmed",
    DISPUTED: "Disputed",
    UPDATED: "Updated",
  } as Record<string, string>)[state ?? ""] ?? "Validation state unavailable";
}
function filterReason(reason?: string) {
  return ({
    NO_FOCUS_RULES: "No focus words were set, so this video's relevance could not be decided. It remains unprocessed. Add focus words in this Following's configuration for future checks.",
    IGNORE_RULE_MATCH: "Excluded by your ignore rules.",
    FOCUS_MATCH: "Matched your focus.",
    FOCUS_MISMATCH: "Outside your current focus.",
    NOT_RELEVANT: "Not relevant enough under this Source’s current policy.",
  } as Record<string, string>)[reason ?? ""] ??
    "This video was skipped under this Source’s current policy.";
}
function attentionCopy(reason: string | null) {
  return ({
    MODEL_UNAVAILABLE: [
      "Video analysis is paused.",
      "Your Sources and existing Intelligence are unchanged.",
      "Check Settings for current model availability.",
    ],
    BUDGET_BLOCKED: [
      "This run reached its budget limit.",
      "Your existing Intelligence is unchanged.",
      "Review your usage before the next run.",
    ],
    AMBIGUOUS_EXTERNAL_OUTCOME: [
      "An external result could not be confirmed.",
      "It will not be repeated automatically, so duplicate work or spending is avoided.",
      "Review the Source status; there is no Retry action for this result.",
    ],
    USER_DECISION_REQUIRED: [
      "Your decision is required.",
      "Existing Intelligence remains available.",
      "Review the Source configuration to choose the next step.",
    ],
    EXECUTION_CONDITION_UNRESOLVED: [
      "This run needs a relevance or execution decision.",
      "Your existing Intelligence is unchanged.",
      "Review the Source details to decide what should happen next.",
    ],
  } as Record<string, [string, string, string]>)[reason ?? ""] ??
    [
      "This Source needs attention.",
      "Existing Intelligence remains safe.",
      "Review the Source details for the available next step.",
    ];
}

function sourceLabel(source: Source) {
  const handle = /\/(@[^/]+)/.exec(source.canonical_url)?.[1];
  return source.friendly_name || source.display_name || handle || source.channel_id || source.video_id || source.canonical_url;
}
/**
 * What this Source is actually doing. A capability the service has withdrawn is
 * never described as "monitoring", because the word would be a claim the
 * product cannot keep.
 */
function sourceSummary(source: Source, creatorFollowingWithdrawn: boolean) {
  if (source.provider === "LOCAL") return "Explicit imports only";
  if (source.source_type === "CHANNEL" && !source.tracking) return "Legacy channel needs attention. Re-add explicitly to establish tracking; its history is preserved.";
  // A creator is a creator whatever provider it belongs to, so this is checked
  // before the manual-video wording below.
  if (source.tracking || source.source_type === "CREATOR") {
    if (source.provider === "BILIBILI" && creatorFollowingWithdrawn) return "Continuous creator tracking is currently unavailable";
    return source.enabled ? "Monitoring new videos" : "Monitoring is paused";
  }
  if (source.provider === "BILIBILI" || source.source_type === "VIDEO_URL") return "Manually imported video";
  return source.enabled ? "Monitoring new videos" : "Monitoring is paused";
}
function timestamp(value: number) {
  const seconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}
function timestampRange(start: number | null, end: number | null) {
  if (start === null) return "Timestamp unavailable";
  return end === null
    ? timestamp(start)
    : `${timestamp(start)}–${timestamp(end)}`;
}
function textLineRange(start: number | null | undefined, end: number | null | undefined, t: (text: string) => string) {
  return Number.isInteger(start) && Number.isInteger(end) && start! >= 1 && end! >= start!
    ? `${t("Lines")} ${start}–${end}` : t("Text position unavailable");
}
function videoAt(url: string, start: number | null) {
  if (start === null) return url;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if (
      host === "youtu.be" || host === "youtube.com" ||
      host.endsWith(".youtube.com")
    ) {
      parsed.searchParams.set("t", String(Math.max(0, Math.floor(start / 1000))));
      return parsed.toString();
    }
  } catch {
    return url;
  }
  return url;
}
function evidenceLineageLabel(value: string) {
  return ({
    ORIGINAL_TRANSCRIPT: "Original transcript",
    TRANSLATION: "Translation lineage",
    EXTRACTION: "Extracted evidence",
  } as Record<string, string>)[value] ?? "Recorded provenance";
}
function evidenceRoleLabel(value: string) {
  return ({
    PRIMARY_ORIGINAL: "Primary original",
    INDEPENDENT_VERIFICATION: "Independent verification",
    ANALYSIS_COMMENTARY: "Analysis commentary",
    SECONDARY_RELAY: "Secondary relay",
  } as Record<string, string>)[value] ?? "Recorded source role";
}
function stanceLabel(
  value: "supporting" | "contradicting" | "conditional" | null,
) {
  if (value === "supporting") return "Supporting";
  if (value === "contradicting") return "Contradicting";
  if (value === "conditional") return "Conditional";
  return "Relation not determined";
}

export function ScoringTab(
  { scoring }: {
    scoring: { status: string; reason?: string; code?: string } | null;
    error: string | null;
  },
) {
  if (!scoring || scoring.status !== "AVAILABLE") {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>
          {scoring?.reason ??
            "No verified scoring result is available for this video."}
        </p>
      </div>
    );
  }
  return (
    <div className="semantic-state">
      <Status value="VERIFIED" />
    </div>
  );
}

function evidenceSourceMatchesTarget(
  sourceLanguage: string | null | undefined,
  targetLanguage: string,
): boolean {
  const source = (sourceLanguage ?? "").trim().replace(/_/g, "-").toLowerCase();
  if (targetLanguage === "en") return source === "en" || source.startsWith("en-");
  if (targetLanguage === "zh-CN") {
    return ["zh-cn", "zh-hans", "zh-hans-cn"].includes(source);
  }
  return false;
}

function CaptionCleanBar({
  collapsedCount,
  showVerbatim,
  onToggle,
}: {
  collapsedCount: number;
  showVerbatim: boolean;
  onToggle: () => void;
}) {
  const { t } = useUiLanguage();
  if (collapsedCount <= 0) return null;
  return (
    <div className="caption-clean-bar">
      <span className="hint">{t("Duplicate rolling caption lines merged for clean reading.")}</span>
      <button type="button" className="button button-ghost button-small" onClick={onToggle}>
        {t(showVerbatim ? "Show clean reading" : "Show verbatim lines")}
      </button>
    </div>
  );
}

function Evidence(
  { item, onOpenContent }: {
    item: Intelligence;
    onOpenContent?: (videoId: string, evidenceId?: string) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const [selectedMode, setSelectedMode] = useState<EvidenceDisplayMode | null>(null);
  const [showVerbatim, setShowVerbatim] = useState(false);
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [createdTranslations, setCreatedTranslations] = useState<Record<
    string,
    { excerpt: string; language: "zh-CN" | "en" }
  >>({});
  const card = item.card;
  const links = card?.evidence_links ?? [];
  if (!card || !links.length) return null;
  const collapsedTotal = links.reduce(
    (sum, link) => sum + (link.original_excerpt ? cleanCaptionText(link.original_excerpt).collapsedCount : 0),
    0,
  );
  const hasPreferredTranslation = links.some((link) => {
    const localTranslation = createdTranslations[link.evidence_id];
    const target = link.translation_target_language
      ?? localTranslation?.language
      ?? link.translated_language;
    return Boolean(
      (localTranslation?.excerpt ?? link.translated_excerpt)
      && target
      && (localTranslation?.language ?? link.translated_language) === target
      && !evidenceSourceMatchesTarget(link.language, target),
    );
  });
  const mode = selectedMode ?? (hasPreferredTranslation ? "译文" : "原文");
  const generateTranslation = async (evidenceId: string) => {
    if (!item.intelligence_id) return;
    setTranslationBusy(true);
    setTranslationError(null);
    try {
      const result = await post<{
        evidence_id: string;
        translated_excerpt: string | null;
        translated_language: "zh-CN" | "en" | null;
        translation_target_language: "zh-CN" | "en";
      }>(
        `/intelligence/${encodeURIComponent(item.intelligence_id)}/evidence/${encodeURIComponent(evidenceId)}/translation`,
        {},
      );
      const translatedExcerpt = result.translated_excerpt;
      const translatedLanguage = result.translated_language;
      if (
        result.evidence_id !== evidenceId
        || !translatedExcerpt
        || translatedLanguage !== result.translation_target_language
      ) {
        throw new Error("The local translation response is incomplete.");
      }
      setCreatedTranslations((current) => ({
        ...current,
        [evidenceId]: {
          excerpt: translatedExcerpt,
          language: translatedLanguage,
        },
      }));
      setSelectedMode("译文");
    } catch {
      setTranslationError("Could not create a verified local translation. Original Evidence is still available.");
    } finally {
      setTranslationBusy(false);
    }
  };
  return (
    <details className="evidence-block evidence-trace">
      <summary>{t("Evidence and source")}</summary>
      <div className="evidence-origin">
        <div>
          <span>{t("Source")}</span>
          <strong>{card.source_display_name || t("Source name unavailable")}</strong>
          {!card.source_display_name && <small>{card.source_id} · {card.video_id}</small>}
          {card.source_url
            ? <a href={card.source_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
            : null}
        </div>
        <div>
          <span>{t("Content")}</span>
          <strong>{card.video_title || card.video_id}</strong>
        </div>
      </div>
      <CaptionCleanBar
        collapsedCount={collapsedTotal}
        showVerbatim={showVerbatim}
        onToggle={() => setShowVerbatim(current => !current)}
      />
      <div className="evidence-trace-list">
        {links.map((link) => (
          <article className="evidence-item evidence-trace-item" key={link.evidence_id}>
            <div className="reading-meta">
              <Status value={stanceLabel(link.stance)} />
              <span>{t("Source language")}: {link.language}</span>
            </div>
            {(() => {
              const localTranslation = createdTranslations[link.evidence_id];
              const translatedExcerpt = localTranslation?.excerpt
                ?? link.translated_excerpt;
              const translatedLanguage = localTranslation?.language
                ?? link.translated_language;
              const target = link.translation_target_language
                ?? translatedLanguage
                ?? "zh-CN";
              const translationAvailable = Boolean(
                translatedExcerpt
                && translatedLanguage === target
                && !evidenceSourceMatchesTarget(link.language, target),
              );
              const sourceMatchesTarget = evidenceSourceMatchesTarget(
                link.language,
                target,
              );
              const showTranslation = mode !== "原文";
              const showOriginal = mode !== "译文" || !translationAvailable;
              return (
                <>
                  <div className="segmented evidence-display-modes" role="group" aria-label={t("Evidence presentation mode")}>
                    {(["译文", "双语", "原文"] as const).map((option) => (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={mode === option}
                        className={mode === option ? "active" : ""}
                        onClick={() => setSelectedMode(option)}
                      >
                        {language === "en" ? ({ "译文": "Translation", "双语": "Bilingual", "原文": "Original" } as const)[option] : option}
                      </button>
                    ))}
                  </div>
                  {showTranslation
                    ? (
                      <div>
                        <strong>{t("Translation")} · {target}</strong>
                        {translationAvailable
                          ? <blockquote>{showVerbatim ? translatedExcerpt : cleanTranslatedCaptionText(translatedExcerpt!)}</blockquote>
                          : sourceMatchesTarget
                          ? <p className="hint">{t("Original Evidence already matches the requested output language.")}</p>
                          : (
                            <>
                              <p className="hint">{t("Translation unavailable. Original Evidence remains authoritative.")}</p>
                              {item.intelligence_id && link.original_excerpt && !translationBusy
                                ? (
                                  <button
                                    type="button"
                                    className="button button-secondary button-small"
                                    onClick={() => void generateTranslation(link.evidence_id)}
                                  >
                                    {t("Generate translation")}
                                  </button>
                                )
                                : null}
                            </>
                          )}
                        {translationBusy
                          ? <p className="hint" role="status">{t("Generating a local translation…")}</p>
                          : null}
                        {translationError
                          ? <p className="hint" role="alert">{t(translationError)}</p>
                          : null}
                      </div>
                    )
                    : null}
                  {showOriginal
                    ? (
                      <div>
                        <strong>{t("Original · authoritative source")} · {link.language}</strong>
                        {link.original_excerpt
                          ? <blockquote>{showVerbatim ? link.original_excerpt : cleanCaptionText(link.original_excerpt).text}</blockquote>
                          : (
                            <p className="hint">
                              {t("Source excerpt unavailable for this historical Evidence. It is not reconstructed or guessed.")}
                            </p>
                          )}
                      </div>
                    )
                    : null}
                  {mode === "原文" && !translationAvailable && !sourceMatchesTarget
                    ? <p className="hint">{t("Translation unavailable.")}</p>
                    : null}
                </>
              );
            })()}
            <div>
              <strong>{t("Source position")}</strong>
              <p>{link.locator_type === "TEXT_RANGE"
                ? textLineRange(link.start_line, link.end_line, t) : timestampRange(link.start_ms, link.end_ms)}</p>
            </div>
            <div>
              <strong>{t("Provenance")}</strong>
              <p>{t(evidenceLineageLabel(link.lineage_kind))} · {t(evidenceRoleLabel(link.role))}</p>
              <small>{link.artifact_id}</small>
            </div>
            <div className="evidence-actions">
              {onOpenContent
                ? (
                  <button
                    className="button button-secondary button-small"
                    onClick={() => onOpenContent(card.video_id, link.evidence_id)}
                  >
                    {t("Open Content")}
                  </button>
                )
                : null}
              {card.original_video_url
                ? (
                  <a
                    className="button button-ghost button-small evidence-source-link"
                    href={videoAt(card.original_video_url, link.start_ms)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t(link.start_ms === null ? "Open original" : "Open original at timestamp")}
                  </a>
                )
                : null}
            </div>
          </article>
        ))}
      </div>
      <p className="hint">
        {t("Supporting, contradicting, and conditional describe this Evidence only in relation to this specific Intelligence revision. Missing relations are shown as undetermined rather than inferred.")}
      </p>
    </details>
  );
}
export function formatPlainTextIntelligenceCard(item: Intelligence, zh: boolean): string {
  const card = item.card;
  if (!card) return "";
  const lines: string[] = [];
  lines.push(
    zh
      ? `【验证洞察】${card.core_conclusion}`
      : `[Verified Insight] ${card.core_conclusion}`,
  );
  const sourceLabelText = [
    card.source_display_name?.trim(),
    card.video_title?.trim()
      ? zh
        ? `《${card.video_title.trim()}》`
        : `"${card.video_title.trim()}"`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
  if (sourceLabelText) {
    lines.push(zh ? `来源：${sourceLabelText}` : `Source: ${sourceLabelText}`);
  }
  const topicNames = (item.linked_topics ?? [])
    .map((tp) => tp.name.trim())
    .filter(Boolean);
  if (topicNames.length > 0) {
    lines.push(
      zh
        ? `关联专题：${topicNames.join("、")}`
        : `Linked Topics: ${topicNames.join(", ")}`,
    );
  }
  if (card.user_relevant_information.length > 0) {
    lines.push(
      zh
        ? `核心价值：${card.user_relevant_information.join(" ")}`
        : `Why this matters: ${card.user_relevant_information.join(" ")}`,
    );
  }
  if (card.important_new_information.length > 0) {
    lines.push(
      zh
        ? `新增信号：${card.important_new_information.join(" ")}`
        : `What is new: ${card.important_new_information.join(" ")}`,
    );
  }
  if (card.meaningful_details?.length) {
    lines.push(
      [
        zh ? "关键细节：" : "Key details:",
        ...card.meaningful_details.map((d) => `• ${d}`),
      ].join("\n"),
    );
  }
  const quoteLinks = (card.evidence_links ?? []).filter((link) =>
    Boolean(link.translated_excerpt?.trim() || link.original_excerpt?.trim()),
  );
  if (quoteLinks.length > 0) {
    lines.push(
      [
        zh ? "原话证据出处：" : "Verified quotes:",
        ...quoteLinks.slice(0, 3).map((link) => {
          const rangeLabel =
            link.locator_type === "TEXT_RANGE"
              ? `L${link.start_line ?? "?"}-${link.end_line ?? "?"}`
              : timestampRange(link.start_ms, link.end_ms);
          const excerpt = (
            (zh && link.translated_excerpt?.trim()) ||
            link.original_excerpt?.trim() ||
            ""
          ).replace(/\s+/g, " ");
          return `- [${rangeLabel}] "${excerpt}"`;
        }),
      ].join("\n"),
    );
  }
  if (card.original_video_url) {
    lines.push(
      zh
        ? `原视频：${card.original_video_url}`
        : `Video URL: ${card.original_video_url}`,
    );
  }
  return lines.join("\n\n");
}

export function formatPlainTextIntelligenceDigest(
  items: Intelligence[],
  zh: boolean,
  kind: "filtered" | "saved" = "filtered",
): string {
  const valid = items.filter(
    (it) => it.status === "AVAILABLE" && Boolean(it.card),
  );
  if (valid.length === 0) return "";
  const heading =
    kind === "saved"
      ? zh
        ? `【已收藏洞察合集】（共 ${valid.length} 条）`
        : `[Saved Insights Digest] (${valid.length} items)`
      : zh
        ? `【已验证洞察合集】（共 ${valid.length} 条）`
        : `[Verified Insights Digest] (${valid.length} items)`;
  const blocks = valid.map((item, idx) => {
    const raw = formatPlainTextIntelligenceCard(item, zh);
    return zh
      ? raw.replace(
          /^【验证洞察】/,
          `【验证洞察 ${idx + 1}/${valid.length}】`,
        )
      : raw.replace(
          /^\[Verified Insight\]/,
          `[Verified Insight ${idx + 1}/${valid.length}]`,
        );
  });
  return [heading, ...blocks].join("\n\n");
}

function stripPlainWikilinks(text: string): string {
  return text.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, target: string, alias?: string) =>
    (alias ?? target).trim(),
  );
}

export function formatPlainTextContentDigest(
  entries: { item: ContentItem; brief: VideoAiBrief }[],
  language: "zh-CN" | "en",
): string {
  if (!entries.length) return "";
  const zh = language === "zh-CN";
  const heading = zh
    ? `【内容库精选摘要合集（共 ${entries.length} 篇）】`
    : `[Content AI Summary Digest] (${entries.length} items)`;
  const blocks = entries.map(({ item, brief }, idx) => {
    const chLabel = contentItemChannelKeyAndLabel(item, language).label;
    const title = stripPlainWikilinks((item.title ?? item.video_id).trim());
    const topicClean = stripPlainWikilinks((brief.topic_cluster_zh ?? "").trim());
    const metaParts = [
      chLabel,
      zh ? `评分 ${brief.score.toFixed(1)}` : `Score ${brief.score.toFixed(1)}`,
      topicClean || null,
    ].filter(Boolean);
    const lines: string[] = [
      zh
        ? `[${idx + 1}] 《${title}》（${metaParts.join(" · ")}）`
        : `[${idx + 1}] "${title}" (${metaParts.join(" · ")})`,
    ];
    const cleanHeadline = stripPlainWikilinks((brief.headline_zh ?? "").trim());
    if (cleanHeadline) {
      lines.push(`${zh ? "核心结论：" : "Key takeaway: "}${cleanHeadline}`);
    }
    const cleanSummary = stripPlainWikilinks((brief.summary_zh ?? "").trim());
    if (cleanSummary && cleanSummary !== cleanHeadline) {
      lines.push(`${zh ? "摘要：" : "Summary: "}${cleanSummary}`);
    }
    const bullets = [
      ...(brief.product_opportunities_zh ?? []),
      ...(brief.business_opportunities_zh ?? []),
    ]
      .map((pt) => stripPlainWikilinks(pt.trim()))
      .filter((pt) => Boolean(pt) && pt !== cleanHeadline)
      .slice(0, 2);
    for (const pt of bullets) {
      lines.push(`- ${pt}`);
    }
    if (item.source_url && /^https?:\/\//i.test(item.source_url)) {
      lines.push(`${zh ? "原视频：" : "Video URL: "}${item.source_url}`);
    }
    return lines.join("\n");
  });
  return [heading, ...blocks].join("\n\n");
}

function IntelligenceCard(
  { item, saved, onSaved, onOpenContent, onOpenTopic }: {
    item: Intelligence;
    saved: boolean;
    onSaved: () => void;
    onOpenContent?: (videoId: string, evidenceId?: string) => void;
    onOpenTopic?: (topicId: string) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [busy, setBusy] = useState(false);
  const [copiedCard, setCopiedCard] = useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);
  const [showTopicForm, setShowTopicForm] = useState(false);
  const [topicName, setTopicName] = useState(item.card?.video_title ?? "");
  const [topicBusy, setTopicBusy] = useState(false);
  const [topicError, setTopicError] = useState<string | null>(null);
  const [createdTopic, setCreatedTopic] = useState<string | null>(null);
  const toggle = async () => {
    setBusy(true);
    const willSave = !saved;
    try {
      await post(
        saved ? "/saved-intelligence/unsave" : "/saved-intelligence/save",
        { intelligence_id: item.intelligence_id },
      );
      if (willSave) pulseCelebration(saveBtnRef.current);
      onSaved();
    } finally {
      setBusy(false);
    }
  };
  if (item.status !== "AVAILABLE" || !item.card) {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>{t("This Intelligence is not available as current information.")}</p>
      </div>
    );
  }
  const card = item.card;
  const linkedTopics = item.linked_topics ?? [];
  return (
    <article className={`panel intelligence-card${saved ? " is-saved-card" : ""}`}>
      {linkedTopics.length > 0 ? (
        <div
          className="intel-card-topics-row"
          aria-label={zh ? "关联专题" : "Linked Topics"}
        >
          {linkedTopics.map((tp) =>
            onOpenTopic ? (
              <button
                key={tp.topic_id}
                type="button"
                className="ai-topic-tag ai-topic-tag-btn"
                onClick={() => onOpenTopic(tp.topic_id)}
              >
                {`[[${tp.name}]]`}
              </button>
            ) : (
              <span key={tp.topic_id} className="ai-topic-tag">
                {`[[${tp.name}]]`}
              </span>
            ),
          )}
        </div>
      ) : null}
      <header className="intelligence-conclusion">
        <h2>{card.core_conclusion}</h2>
      </header>
      <section className="intelligence-section">
        <h3>{t("Why this matters")}</h3>
        <p>{card.user_relevant_information.join(" ")}</p>
      </section>
      {card.important_new_information.length
        ? (
          <section className="intelligence-section">
            <h3>{t("What is new")}</h3>
            <p>{card.important_new_information.join(" ")}</p>
          </section>
        )
        : null}
      {card.meaningful_details?.length
        ? (
          <section className="intelligence-section">
            <h3>{t("Important details")}</h3>
            <ul>
              {card.meaningful_details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </section>
        )
        : null}
      <div className="reading-meta" aria-label={t("Claim type and current state")}>
        <Claim kind={item.claim_kind ?? "SYSTEM_INFERENCE"} />
        <Status value={intelligenceStateLabel(item.state)} />
        {item.effective_published_at ? (
          <span className="tabular-nums">{humanDate(item.effective_published_at)}</span>
        ) : null}
      </div>
      <section className="intelligence-section">
        <h3>{t("Validation posture")}</h3>
        <p>{t(intelligenceValidationCopy(item.state ?? ""))}</p>
        <p className="hint">
          {t("This is a validation posture, not a numeric confidence score.")}
        </p>
      </section>
      <Evidence item={item} onOpenContent={onOpenContent} />
      <div className="button-row">
        <button
          ref={saveBtnRef}
          className={`button ${saved ? "button-saved" : "button-secondary"}`}
          disabled={busy}
          onClick={toggle}
        >
          <BookmarkSparkIcon saved={saved} />
          {t(busy ? "Saving…" : saved ? "Unsave" : "Save")}
        </button>
        <button
          type="button"
          className="button button-secondary"
          onClick={(event) => {
            pulseCelebration(event.currentTarget);
            void navigator.clipboard?.writeText(
              formatPlainTextIntelligenceCard(item, zh),
            );
            setCopiedCard(true);
            setTimeout(() => setCopiedCard(false), 2000);
          }}
        >
          <PhosphorIcon name="file-text" size={14} />
          {copiedCard
            ? zh
              ? "已复制洞察卡片"
              : "Copied insight card"
            : zh
              ? "复制洞察卡片"
              : "Copy insight card"}
        </button>
      </div>
      {item.intelligence_id && !createdTopic
        ? (
          <div className="intelligence-section">
            <button type="button" className="button button-secondary"
              onClick={() => setShowTopicForm((current) => !current)}>
              {t("Add to a Topic")}
            </button>
            {showTopicForm
              ? (
                <form onSubmit={async (event) => {
                  event.preventDefault();
                  if (!topicName.trim() || !item.intelligence_id) return;
                  setTopicBusy(true);
                  setTopicError(null);
                  try {
                    const created = await post<{ topic: Topic }>("/topics", {
                      command_id: `from-intelligence:${item.intelligence_id}`,
                      name: topicName.trim(),
                    });
                    await post(`/topics/${created.topic.topic_id}/associations`, {
                      intelligence_id: item.intelligence_id,
                      association_kind: "NEW_INFORMATION",
                    });
                    setCreatedTopic(created.topic.name);
                  } catch (reason) {
                    setTopicError((reason as Error).message);
                  } finally {
                    setTopicBusy(false);
                  }
                }}>
                  <label className="field">{t("Topic name")}
                    <input value={topicName} maxLength={120} required
                      onChange={(event) => setTopicName(event.target.value)} />
                  </label>
                  <button type="submit" className="button button-primary" disabled={topicBusy}>
                    {t(topicBusy ? "Adding…" : "Create Topic and link Intelligence")}
                  </button>
                  {topicError && <p className="form-error" role="alert">{topicError}</p>}
                </form>
              )
              : null}
          </div>
        )
        : null}
      {createdTopic && <p className="hint">{t("Linked to Topic")}: {createdTopic}</p>}
    </article>
  );
}

export function App() {
  const swrStoreRef = useRef<RemoteSwrStore | null>(null);
  if (swrStoreRef.current === null) {
    swrStoreRef.current = { cache: new Map(), inflight: new Map() };
  }
  return (
    <RemoteSwrContext.Provider value={swrStoreRef.current}>
      <UiLanguageProvider><UiThemeProvider><Workspace /></UiThemeProvider></UiLanguageProvider>
    </RemoteSwrContext.Provider>
  );
}

type ContentFilterSnapshot = {
  searchQuery: string;
  providerFilter: "ALL" | "YOUTUBE" | "BILIBILI" | "LOCAL";
  bucketFilter: "ALL" | "UNREAD" | "MUST_WATCH" | "STARRED" | "TUTORIAL" | "SHORTS";
  topicFilter: string;
  channelFilter: string;
};

type IntelFilterSnapshot = {
  view: "Current" | "Saved";
  intelSearch: string;
  intelSourceFilter: string;
  intelTopicFilter: string;
  currentPage?: number;
  savedPage?: number;
  pageSize?: 10 | 20;
};

function Workspace() {
  const swrStore = useContext(RemoteSwrContext);
  const { language, setLanguage, t } = useUiLanguage();
  const { theme, toggleTheme } = useUiTheme();
  const [page, setPage] = useState<Page>(initialPage);
  const prefetchNavPage = useCallback(
    (target: Page) => {
      if (!swrStore || target === page) return;
      const pathsByPage: Partial<Record<Page, string[]>> = {
        Home: ["/dashboard"],
        Following: ["/sources"],
        Content: ["/videos"],
        Topics: ["/topics"],
        Intelligence: ["/intelligence", "/saved-intelligence"],
      };
      for (const targetPath of pathsByPage[target] ?? []) {
        if (swrStore.cache.has(targetPath) || swrStore.inflight.has(targetPath)) continue;
        const req = api<unknown>(targetPath);
        swrStore.inflight.set(targetPath, req);
        req
          .then((val) => {
            swrStore.cache.set(targetPath, val);
          })
          .catch(() => {})
          .finally(() => {
            if (swrStore.inflight.get(targetPath) === req) {
              swrStore.inflight.delete(targetPath);
            }
          });
      }
    },
    [page, swrStore],
  );
  const [refresh, setRefresh] = useState(0);
  const [intelListResetSeq, setIntelListResetSeq] = useState(0);
  // Add lives above refreshed/navigated pages: file chooser focus must not unmount it.
  const [addProvider, setAddProvider] = useState<"YOUTUBE" | "LOCAL" | null>(null);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [imported, setImported] = useState(false);
  const [contentTarget, setContentTarget] = useState<string | null>(initialContentTarget);
  // Tracks the hash produced by in-app navigation so the hashchange listener
  // can tell programmatic navigation apart from user navigation (browser
  // back/forward or editing the address bar). Stored WITH the leading "#"
  // because location.hash always includes it (e.g. "#Settings"); storing the
  // bare page name would never match and every programmatic navigation would
  // be misclassified as user navigation (clearing the import notice).
  const programmaticHash = useRef<string | null>(null);
  useEffect(() => {
    const onHashChange = (event: HashChangeEvent) => {
      // Rapid assignments queue separate events. Only the current URL may
      // consume our navigation marker or reset the current view.
      if (event.newURL && new URL(event.newURL).hash !== location.hash) return;
      if (programmaticHash.current === location.hash) {
        programmaticHash.current = null;
        return;
      }
      programmaticHash.current = null;
      const target = initialContentTarget();
      if (target) {
        setImported(false);
        setResearchEvidence(initialEvidenceTarget());
        setPage("Content"); setContentTarget(target); setDeltaTarget(null); setResearchReturn(null);
        return;
      }
      const next = initialPage();
      setImported(false);
      setResearchReturn(null); setResearchEvidence(null);
      setContentTarget(null); setDeltaTarget(null);
      setPage(next);
    };
    const onPopState = () => onHashChange(new HashChangeEvent("hashchange"));
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("popstate", onPopState);
    };
  }, []);
  const [deltaTarget, setDeltaTarget] = useState<DeltaTarget | null>(null);
  const [handoffSeq, setHandoffSeq] = useState(0);
  const [researchReturn, setResearchReturn] = useState<string | null>(null);
  const [researchOriginPage, setResearchOriginPage] = useState<Exclude<Page, "Research"> | null>(null);
  const latestContentFilterRef = useRef<ContentFilterSnapshot | null>(null);
  const latestIntelFilterRef = useRef<IntelFilterSnapshot | null>(null);
  const latestTopicIdRef = useRef<string | null>(null);
  const capturedOriginSnapshotRef = useRef<{
    content: ContentFilterSnapshot | null;
    intel: IntelFilterSnapshot | null;
    topicId: string | null;
  }>({ content: null, intel: null, topicId: null });
  const pendingOriginRestoreRef = useRef<{
    content: ContentFilterSnapshot | null;
    intel: IntelFilterSnapshot | null;
    topicId: string | null;
  } | null>(null);
  const [researchEvidence, setResearchEvidence] = useState<string | null>(initialEvidenceTarget);
  useEffect(() => {
    if (page !== "Content" || !researchEvidence) return;
    const focusEvidence = () => {
      const element = document.getElementById(`content-evidence-${encodeURIComponent(researchEvidence)}`);
      if (!element || element.dataset.contentId !== contentTarget) return false;
      element.scrollIntoView({ block: "center" });
      element.setAttribute("tabindex", "-1"); element.focus({ preventScroll: true });
      return true;
    };
    if (focusEvidence()) return;
    const observer = new MutationObserver(() => { if (focusEvidence()) observer.disconnect(); });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [page, contentTarget, researchEvidence]);
  const changeHash = (hash: string) => {
    const next = `#${hash}`;
    // A no-op emits no event. Preserve a marker for an already queued real
    // assignment, but never create one for a no-op.
    if (readCurrentLogicalHash() === next) return;
    scheduleSafeHashUpdate(next, {
      emitHashChange: true,
      onBeforeWrite: (fullHash) => {
        programmaticHash.current = fullHash;
      },
    });
  };
  const navigate = (next: Page) => {
    changeHash(next);
    runViewTransition(() => {
      if (next === "Research" && page !== "Research") {
        setResearchOriginPage(page);
        capturedOriginSnapshotRef.current = {
          content:
            page === "Content" && latestContentFilterRef.current
              ? { ...latestContentFilterRef.current }
              : null,
          intel:
            page === "Intelligence" && latestIntelFilterRef.current
              ? { ...latestIntelFilterRef.current }
              : null,
          topicId: page === "Topics" ? latestTopicIdRef.current : null,
        };
      }
      setImported(false);
      setResearchReturn(null); setResearchEvidence(null);
      setContentTarget(null);
      setDeltaTarget(null);
      if (next === "Intelligence") {
        setIntelListResetSeq((value) => value + 1);
      }
      setPage(next);
    });
  };
  const openContent = (videoId: string, evidenceId?: string) => {
    changeHash(`Content/${encodeURIComponent(videoId)}${evidenceId ? `/Evidence/${encodeURIComponent(evidenceId)}` : ""}`);
    runViewTransition(() => {
      setDeltaTarget(null);
      setContentTarget(videoId);
      setResearchEvidence(evidenceId ?? null);
      setPage("Content");
    });
  };
  const openDelta = (target: DeltaTarget) => {
    const destinations: Record<DeltaTarget["kind"], Page> = {
      content: "Content", intelligence: "Intelligence", topic: "Topics", source: "Following",
    };
    changeHash(target.kind === "content" ? `Content/${encodeURIComponent(target.id)}` : destinations[target.kind]);
    runViewTransition(() => {
      setDeltaTarget(target);
      setContentTarget(target.kind === "content" ? target.id : null);
      setPage(destinations[target.kind]);
    });
  };
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCmdkOpen(current => !current);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
  const staticCommands: CommandPaletteAction[] = [
    { id: "nav:Home", group: "navigation", label: t("Home"), subtitle: t(subtitles.Home), icon: "house", aliases: ["home", "首页"], onSelect: () => navigate("Home") },
    { id: "nav:Following", group: "navigation", label: t("Following"), subtitle: t(subtitles.Following), icon: "rss", aliases: ["following", "sources", "关注"], onSelect: () => navigate("Following") },
    { id: "nav:Content", group: "navigation", label: t("Content"), subtitle: t(subtitles.Content), icon: "play-circle", aliases: ["content", "videos", "内容", "视频"], onSelect: () => navigate("Content") },
    { id: "nav:Intelligence", group: "navigation", label: t("Intelligence"), subtitle: t(subtitles.Intelligence), icon: "sparkle", aliases: ["intelligence", "insights", "洞察"], onSelect: () => navigate("Intelligence") },
    { id: "nav:Topics", group: "navigation", label: t("Topics"), subtitle: t(subtitles.Topics), icon: "stack", aliases: ["topics", "主题"], onSelect: () => navigate("Topics") },
    { id: "nav:Research", group: "navigation", label: t("Research"), subtitle: t(subtitles.Research), icon: "quotes", aliases: ["research", "研究", "qa", "问答", "跨视频"], onSelect: () => navigate("Research") },
    { id: "nav:Settings", group: "navigation", label: t("Settings"), subtitle: t(subtitles.Settings), icon: "sliders-horizontal", aliases: ["settings", "设置", "model", "budget"], onSelect: () => navigate("Settings") },
    { id: "act:ai-qa", group: "actions", label: language === "zh-CN" ? "AI 跨视频深度问答" : "Ask cross-video AI Q&A", icon: "sparkle", aliases: ["qa", "ask", "ai", "问答", "跨视频", "提问"], onSelect: () => navigate("Research") },
    { id: "act:export-obsidian-zip", group: "actions", label: language === "zh-CN" ? "导出 Obsidian 双链知识库包 (.zip)" : "Export Obsidian Vault bundle (.zip)", icon: "archive", aliases: ["obsidian", "vault", "zip", "wikilinks", "双链", "导出", "知识库"], onSelect: () => { void exportObsidianVaultBundle("must_watch"); } },
    { id: "act:add-video", group: "actions", label: t("Add video or follow channel"), icon: "plus", aliases: ["add", "import", "youtube", "bilibili", "导入", "添加"], onSelect: () => setAddProvider("YOUTUBE") },
    { id: "act:add-local", group: "actions", label: t("Import local file"), icon: "file-text", aliases: ["local", "file", "本地文件", "转写"], onSelect: () => setAddProvider("LOCAL") },
    { id: "act:theme", group: "actions", label: t(theme === "dark" ? "Switch to Warm Paper Light theme" : "Switch to Obsidian Dark theme"), icon: theme === "dark" ? "sun" : "moon", aliases: ["theme", "dark", "light", "主题", "浅色", "深色"], onSelect: toggleTheme },
    { id: "act:lang", group: "actions", label: t(language === "zh-CN" ? "Switch interface to English" : "Switch interface to Chinese"), icon: "translate", aliases: ["language", "english", "chinese", "中文", "语言"], onSelect: () => setLanguage(language === "zh-CN" ? "en" : "zh-CN") },
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo className="brand-logo" />
          <div>
            <strong>{t("Intelligence")}</strong>
            <small>{t("Local-first workspace")}</small>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label={t("Primary navigation")}>
          {pages.map((item) => {
            const isActive = page === item;
            return (
              <button
                type="button"
                key={item}
                className={`nav-item ${isActive ? "active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                onMouseEnter={() => prefetchNavPage(item)}
                onFocus={event => {
                  const nav = event.currentTarget.parentElement;
                  if (nav && nav.scrollWidth > nav.clientWidth) {
                    event.currentTarget.scrollIntoView({ block: "nearest", inline: "nearest" });
                  }
                }}
                onClick={() => navigate(item)}
              >
                <NavIcon name={item} active={isActive} />
                {t(item)}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-foot"><span className="service-dot" aria-hidden="true" />{t("Evidence stays reachable")}</div>
      </aside>
      <main className="workspace-main">
        <header className="page-header">
          <div>
            <h1>{t(page)}</h1>
            <p className="page-subtitle">{t(subtitles[page])}</p>
          </div>
          {researchReturn && page !== "Research" && <button className="button button-secondary" onClick={() => {
            const target = researchReturn; navigate("Research"); scheduleSafeHashUpdate(target, { emitHashChange: true });
          }}>{t("Back to Research")}</button>}
          {page === "Research" && researchOriginPage !== null && (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => {
                pendingOriginRestoreRef.current = {
                  ...capturedOriginSnapshotRef.current,
                };
                navigate(researchOriginPage);
              }}
            >
              {language === "zh-CN"
                ? `返回来源：${t(researchOriginPage)}`
                : `Return to ${t(researchOriginPage)}`}
            </button>
          )}
        </header>
        <NativeImportActivity onOpen={openContent} errors={localImportErrors} routeKey={`${page}/${contentTarget ?? ""}`} modalOpen={addProvider !== null} />
        {page === "Research" && <Research handoffSeq={handoffSeq} onOpen={(kind, id, evidenceId) => {
          const returnTo = readCurrentLogicalHash().slice(1);
          if (kind === "content") { openContent(id, evidenceId); }
          else openDelta({ kind: "intelligence", id });
          setResearchReturn(returnTo);
        }} />}
        {page === "Home" && (
          <div className="dashboard-stack">
            <KnowledgeDelta refresh={refresh} onOpen={openDelta} />
            <Dashboard
              refresh={refresh}
              navigate={navigate}
              openContent={openContent}
              onOpenTopic={id => openDelta({ kind: "topic", id })}
            />
          </div>
        )}
        {page === "Following" && (
          <Sources
            refresh={refresh}
            onRefresh={() => setRefresh((value) => value + 1)}
            targetSourceId={deltaTarget?.kind === "source" ? deltaTarget.id : null}
            onAdd={setAddProvider}
            onBrowseChannelContent={(channelKey) => {
              setPendingContentChannel(channelKey);
              setPendingContentTopic("ALL");
              setHandoffSeq((value) => value + 1);
              navigate("Content");
            }}
            onAskChannelResearch={(channelKey) => {
              setPendingResearchChannel(channelKey);
              setHandoffSeq((value) => value + 1);
              navigate("Research");
            }}
          />
        )}
        {page === "Content" && (
          <>
            {imported && <p role="status" aria-live="polite">{t("File imported. Its processing status appears below.")}</p>}
            <ContentPage
              refresh={refresh}
              handoffSeq={handoffSeq}
              targetVideoId={contentTarget}
              highlightedEvidenceId={researchEvidence}
              latestFilterRef={latestContentFilterRef}
              consumeOriginRestore={() => {
                const snap = pendingOriginRestoreRef.current?.content ?? null;
                if (pendingOriginRestoreRef.current) {
                  pendingOriginRestoreRef.current.content = null;
                }
                return snap;
              }}
              onOpen={openContent}
              onClose={() => navigate("Content")}
              onAdd={() => setAddProvider("YOUTUBE")}
              onAddLocal={() => setAddProvider("LOCAL")}
              onAskStarredResearch={() => {
                setPendingResearchStarredOnly(true);
                setHandoffSeq((value) => value + 1);
                navigate("Research");
              }}
              onAskFilteredResearch={(videoIds) => {
                setPendingResearchVideoIds(videoIds);
                setHandoffSeq((value) => value + 1);
                navigate("Research");
              }}
              onSelectTopicCluster={(clusterName) => {
                setPendingTopicClusterName(clusterName);
                setHandoffSeq((value) => value + 1);
                navigate("Topics");
              }}
            />
          </>
        )}
        {page === "Intelligence" && (
          deltaTarget?.kind === "intelligence"
            ? (
              <IntelligenceDetail
                id={deltaTarget.id}
                openContent={openContent}
                onOpenTopic={id => openDelta({ kind: "topic", id })}
                onBack={() => navigate("Intelligence")}
              />
            )
            : (
              <IntelligencePage
                refresh={refresh}
                handoffSeq={handoffSeq}
                listResetSeq={intelListResetSeq}
                latestFilterRef={latestIntelFilterRef}
                consumeOriginRestore={() => {
                  const snap = pendingOriginRestoreRef.current?.intel ?? null;
                  if (pendingOriginRestoreRef.current) {
                    pendingOriginRestoreRef.current.intel = null;
                  }
                  return snap;
                }}
                openContent={openContent}
                onOpenTopic={id => openDelta({ kind: "topic", id })}
                openResearch={() => navigate("Research")}
                onAskFilteredResearch={(videoIds) => {
                  setPendingResearchVideoIds(videoIds);
                  setHandoffSeq((value) => value + 1);
                  navigate("Research");
                }}
              />
            )
        )}
        {page === "Topics" && (
          <Topics
            refresh={refresh}
            handoffSeq={handoffSeq}
            targetTopicId={deltaTarget?.kind === "topic" ? deltaTarget.id : null}
            latestSelectedRef={latestTopicIdRef}
            consumeOriginRestore={() => {
              const tid = pendingOriginRestoreRef.current?.topicId ?? null;
              if (pendingOriginRestoreRef.current) {
                pendingOriginRestoreRef.current.topicId = null;
              }
              return tid;
            }}
            onOpenContent={(id) => openContent(id)}
            onAskTopicResearch={(topicName) => {
              setPendingResearchTopicCluster(topicName);
              setHandoffSeq((value) => value + 1);
              navigate("Research");
            }}
            onBrowseTopicContent={(topicName, channelKey) => {
              setPendingContentTopic(topicName);
              setPendingContentChannel(channelKey ?? "ALL");
              setHandoffSeq((value) => value + 1);
              navigate("Content");
            }}
            onBrowseTopicIntelligence={(topicId) => {
              setPendingIntelligenceTopicId(topicId);
              setHandoffSeq((value) => value + 1);
              navigate("Intelligence");
            }}
          />
        )}
        {page === "Settings" && <Settings refresh={refresh} />}
      </main>
      <div className="workspace-utility-dock" role="region" aria-label={t("Quick actions")}>
        <button
          type="button"
          className="utility-import-btn"
          aria-label={t("Quick import")}
          title={t("Add video or follow channel")}
          onClick={event => {
            pulseCelebration(event.currentTarget);
            setAddProvider("YOUTUBE");
          }}
        >
          <PhosphorIcon name="plus" size={14} />
          <span className="utility-import-label">{language === "zh-CN" ? "导入" : "Import"}</span>
        </button>
        <button
          type="button"
          className={`utility-qa-btn${page === "Research" ? " is-active" : ""}`}
          aria-current={page === "Research" ? "page" : undefined}
          aria-label={language === "zh-CN" ? "AI 跨视频问答" : "Cross-video AI Q&A"}
          title={language === "zh-CN" ? "跨视频检索时间轴原话并生成中文解答" : "Ask grounded questions across your video library"}
          onClick={event => {
            pulseCelebration(event.currentTarget);
            navigate("Research");
          }}
        >
          <PhosphorIcon name="sparkle" weight={page === "Research" ? "fill" : "regular"} size={15} />
          <span className="utility-qa-label">{language === "zh-CN" ? "AI 跨视频问答" : "AI Q&A"}</span>
        </button>
        <button
          type="button"
          className="utility-cmdk-btn"
          aria-label={`${t("Search or jump")} (⌘K)`}
          onMouseEnter={preloadCommandPalette}
          onFocus={preloadCommandPalette}
          onClick={() => setCmdkOpen(true)}
        >
          <PhosphorIcon name="magnifying-glass" size={15} />
          <span className="utility-cmdk-label">{t("Search or jump")}</span>
          <kbd className="cmdk-kbd" aria-hidden="true">⌘K</kbd>
        </button>
        <button
          type="button"
          className="utility-theme-btn"
          aria-label={t(theme === "dark" ? "Switch to Warm Paper Light theme" : "Switch to Obsidian Dark theme")}
          title={t(theme === "dark" ? "Switch to Warm Paper Light theme" : "Switch to Obsidian Dark theme")}
          onClick={event => {
            pulseCelebration(event.currentTarget);
            toggleTheme();
          }}
        >
          <PhosphorIcon name={theme === "dark" ? "sun" : "moon"} size={15} className="theme-toggle-glyph" key={theme} />
          <span className="utility-theme-label">{t(theme === "dark" ? "Paper Light" : "Obsidian Dark")}</span>
        </button>
      </div>
      {cmdkOpen ? (
        <Suspense fallback={null}>
          <LazyCommandPalette
            open={cmdkOpen}
            onClose={() => setCmdkOpen(false)}
            staticActions={staticCommands}
            onOpenContent={id => openContent(id)}
            onOpenIntelligence={id => openDelta({ kind: "intelligence", id })}
            onOpenTopic={id => openDelta({ kind: "topic", id })}
            onOpenResearchSession={sessionId => {
              setPendingResearchSessionId(sessionId);
              setHandoffSeq(value => value + 1);
              navigate("Research");
            }}
            onFilterContentByChannel={channelKey => {
              setPendingContentChannel(channelKey);
              setPendingContentTopic("ALL");
              setHandoffSeq(value => value + 1);
              navigate("Content");
            }}
            onFilterContentByTopic={topicCluster => {
              setPendingContentTopic(topicCluster);
              setPendingContentChannel("ALL");
              setHandoffSeq(value => value + 1);
              navigate("Content");
            }}
          />
        </Suspense>
      ) : null}
      {addProvider !== null && <AddEntry initialLocal={addProvider === "LOCAL"} onClose={() => setAddProvider(null)} onSaved={() => { setAddProvider(null); setRefresh(value => value + 1); }} onImported={id => {
        setAddProvider(null); setRefresh(value => value + 1); setImported(true); openContent(id);
      }} />}
    </div>
  );
}
function sortIntelligenceNewestFirst(items: Intelligence[]): Intelligence[] {
  if (!items.some((item) => Boolean(item.effective_published_at))) {
    return items;
  }
  return [...items].sort((a, b) => {
    const msA = a.effective_published_at ? Date.parse(a.effective_published_at) : NaN;
    const msB = b.effective_published_at ? Date.parse(b.effective_published_at) : NaN;
    const valA = Number.isFinite(msA) ? msA : 0;
    const valB = Number.isFinite(msB) ? msB : 0;
    if (valB !== valA) return valB - valA;
    return (b.intelligence_id ?? "").localeCompare(a.intelligence_id ?? "");
  });
}

function sortTopicsNewestFirst(topics: Topic[]): Topic[] {
  if (!topics.some((tp) => Boolean(readTopicAiEvolution(tp.ai_evolution)?.latest_published_at))) {
    return topics;
  }
  return [...topics].sort((a, b) => {
    const pinDiff = (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0);
    if (pinDiff !== 0) return pinDiff;
    const ta = readTopicAiEvolution(a.ai_evolution)?.latest_published_at ?? "";
    const tb = readTopicAiEvolution(b.ai_evolution)?.latest_published_at ?? "";
    const msA = ta ? Date.parse(ta) : NaN;
    const msB = tb ? Date.parse(tb) : NaN;
    const valA = Number.isFinite(msA) ? msA : 0;
    const valB = Number.isFinite(msB) ? msB : 0;
    if (valB !== valA) return valB - valA;
    const cntA = readTopicAiEvolution(a.ai_evolution)?.video_count ?? 0;
    const cntB = readTopicAiEvolution(b.ai_evolution)?.video_count ?? 0;
    return cntB - cntA;
  });
}

function Dashboard(
  { refresh, navigate, openContent, onOpenTopic }: {
    refresh: number;
    navigate: (page: Page) => void;
    openContent: (videoId: string, evidenceId?: string) => void;
    onOpenTopic: (topicId: string) => void;
  },
) {
  const { t } = useUiLanguage();
  const { data, error, errorCode, reload } = useRemote<
    {
      intelligence?: Intelligence[];
      saved_intelligence_ids?: string[];
      pinned_topics?: Topic[];
      weekly_v1?: unknown[];
      needs_attention?: SourceRun[];
      operations?: { source_count?: number };
      workspace_weekly_brief?: unknown;
    }
  >("/dashboard", refresh, undefined, true, true);
  const [onboardingDone, setOnboardingDone] = useState(onboardingCompleted);
  const finishOnboarding = () => { completeOnboarding(); setOnboardingDone(true); };
  if (error) return <ErrorState error={error} code={errorCode} onReload={reload} />;
  if (!data) return <Empty>Loading Home…</Empty>;
  const intelligence = sortIntelligenceNewestFirst(
      (data.intelligence ?? []).filter((item) => item.status === "AVAILABLE" && item.trusted),
    ),
    savedIdSet = new Set(Array.isArray(data.saved_intelligence_ids) ? data.saved_intelligence_ids : []),
    attention = data.needs_attention ?? [],
    topics = sortTopicsNewestFirst(data.pinned_topics ?? []),
    weeklyBrief = readWeeklyAiBrief(data.workspace_weekly_brief),
    hasWeeklyHistory = (data.weekly_v1 ?? []).length > 0 || weeklyBrief !== null;
  const isFreshLibrary = data.operations?.source_count === 0 &&
    !intelligence.length && !topics.length && !hasWeeklyHistory && !attention.length;
  if (isFreshLibrary && !onboardingDone) {
    return <FirstRunOnboarding onSkip={finishOnboarding} onAddFollowing={() => { finishOnboarding(); navigate("Following"); }} />;
  }
  if (!intelligence.length && !topics.length && !attention.length && !weeklyBrief) {
    return (
      <div className="dashboard-stack">
        <Panel title="No important new intelligence yet." icon="sparkle">
          <p>
            {t((data.operations?.source_count ?? 0) > 0
              ? "Open Following to check your saved sources or add something new. Content is organized first; generating Intelligence is optional."
              : "Paste a YouTube or Bilibili video link, follow a YouTube channel, or import a local file.")}
          </p>
          <button
            className="button button-primary"
            onClick={() => navigate("Following")}
          >
            {t((data.operations?.source_count ?? 0) > 0 ? "Review Following" : "Add Source")}
          </button>
        </Panel>
      </div>
    );
  }
  return (
    <div className="home-workbench-grid">
      <div className="home-primary-col">
        <WeeklyAiBriefPanel
          initialBrief={weeklyBrief}
          onOpenContent={(id) => openContent(id)}
          onOpenResearch={() => navigate("Research")}
        />
        <Panel title="What matters now" icon="sparkle">
          {intelligence.length
            ? intelligence.map((item) => (
              <IntelligenceCard
                key={item.intelligence_id ?? item.code}
                item={item}
                saved={Boolean(item.intelligence_id && savedIdSet.has(item.intelligence_id))}
                onSaved={reload}
                onOpenContent={openContent}
                onOpenTopic={onOpenTopic}
              />
            ))
            : <Empty>No important new intelligence yet.</Empty>}
          <button
            className="button button-ghost"
            onClick={() => navigate("Intelligence")}
          >
            {t("See all Intelligence")}
          </button>
        </Panel>
      </div>
      <div className="home-side-rail">
        <Panel title="Pinned Topics" icon="stack">
          {topics.length
            ? (
              <div className="pinned-topic-list">
                {topics.map((topic) => {
                  const evo = readTopicAiEvolution(topic.ai_evolution);
                  return (
                    <button
                      type="button"
                      className="pinned-topic-pill"
                      key={topic.topic_id}
                      onClick={() => onOpenTopic(topic.topic_id)}
                    >
                      <PhosphorIcon name="stack" weight="fill" size={14} className="pinned-topic-icon" />
                      <span className="pinned-topic-copy tabular-nums">
                        <strong>{topic.name}</strong>
                        {" · "}
                        {evo && evo.video_count > 0
                          ? t("Home") === "首页"
                            ? `${evo.video_count} 篇 · ${evo.must_watch_count} 必看`
                            : `${evo.video_count} items · ${evo.must_watch_count} must-watch`
                          : t(statusLabel(topic.current_state))}
                      </span>
                      <PhosphorIcon name="caret-right" size={13} className="pinned-topic-arrow" />
                    </button>
                  );
                })}
              </div>
            )
            : <Empty>No pinned Topics yet.</Empty>}
        </Panel>
        {attention.length
          ? (
            <Panel title="Needs Attention" icon="warning-circle">
              {attention.map((run) => (
                <Attention
                  key={run.run_id}
                  run={run}
                  onOpenContent={openContent}
                  onOpenFollowing={() => navigate("Following")}
                />
              ))}
            </Panel>
          )
          : null}
      </div>
    </div>
  );
}
function Attention({
  run,
  onOpenContent,
  onOpenFollowing,
}: {
  run: SourceRun;
  onOpenContent?: (videoId: string) => void;
  onOpenFollowing?: () => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [title, safety, action] = attentionCopy(run.attention_reason);
  return (
    <article className="semantic-state state-blocked">
      <strong>{t(title)}</strong>
      {run.source_label ? (
        <p className="hint">
          <strong>{run.source_label}</strong>
        </p>
      ) : null}
      <p>{t(safety)}</p>
      <p>{t(action)}</p>
      {run.video_id && onOpenContent ? (
        <div className="button-row">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={() => onOpenContent(run.video_id!)}
          >
            {zh ? "查看处理方式" : "View details"}
          </button>
        </div>
      ) : run.source_id && onOpenFollowing ? (
        <div className="button-row">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onOpenFollowing}
          >
            {zh ? "查看关注列表" : "Review Following"}
          </button>
        </div>
      ) : null}
    </article>
  );
}
function IntelligenceDetail({ id, openContent, onOpenTopic, onBack }: {
  id: string;
  openContent: (videoId: string, evidenceId?: string) => void;
  onOpenTopic?: (topicId: string) => void;
  onBack: () => void;
}) {
  const { t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const detail = useRemote<{ intelligence: Intelligence }>(`/intelligence/${id}`, revision);
  const savedList = useRemote<{ saved: Saved[] }>("/saved-intelligence", revision);
  const isSaved = Boolean(
    detail.data?.intelligence.intelligence_id &&
      (savedList.data?.saved ?? []).some(
        (entry) => entry.intelligence_id === detail.data?.intelligence.intelligence_id,
      ),
  );
  return <>
    <button type="button" className="button button-ghost" onClick={onBack}>{t("Back to Intelligence")}</button>
    {detail.error ? <ErrorState error={detail.error} code={detail.errorCode} onReload={detail.reload} hideRawMessage />
      : !detail.data ? <Empty>Loading verified Intelligence…</Empty>
      : <IntelligenceCard item={detail.data.intelligence} saved={isSaved}
          onSaved={() => setRevision(value => value + 1)} onOpenContent={openContent} onOpenTopic={onOpenTopic} />}
  </>;
}
function getIntelligenceRowKey(item: Intelligence, fallbackIndex: number): string {
  return (
    item.intelligence_id ||
    item.code ||
    `${item.card?.video_id ?? "intel"}:${item.card?.core_conclusion ?? fallbackIndex}`
  );
}

function scrollWorkspaceToTop() {
  if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent)) {
    return;
  }
  if (typeof window !== "undefined" && typeof window.scrollTo === "function") {
    window.scrollTo({ top: 0, behavior: "auto" });
  }
  if (typeof document !== "undefined") {
    const main = document.querySelector(".workspace-main");
    if (main && typeof main.scrollTo === "function") {
      main.scrollTo({ top: 0, behavior: "auto" });
    }
  }
}

function buildPageNumberTokens(
  currentPage: number,
  totalPages: number,
): (number | "ellipsis-start" | "ellipsis-end")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, idx) => idx + 1);
  }
  const tokens: (number | "ellipsis-start" | "ellipsis-end")[] = [1];
  const windowStart = Math.max(2, currentPage - 1);
  const windowEnd = Math.min(totalPages - 1, currentPage + 1);
  if (windowStart > 2) tokens.push("ellipsis-start");
  for (let p = windowStart; p <= windowEnd; p += 1) {
    tokens.push(p);
  }
  if (windowEnd < totalPages - 1) tokens.push("ellipsis-end");
  tokens.push(totalPages);
  return tokens;
}

function IntelPaginationBar({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  zh,
  onPageChange,
  onPageSizeChange,
}: {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: 10 | 20;
  zh: boolean;
  onPageChange: (nextPage: number) => void;
  onPageSizeChange: (nextSize: 10 | 20) => void;
}) {
  if (totalItems <= 0 || (totalPages <= 1 && pageSize === 10 && totalItems < 6)) {
    return null;
  }
  const pageTokens = buildPageNumberTokens(currentPage, totalPages);
  return (
    <nav
      className="intel-pagination-bar tabular-nums"
      aria-label={zh ? "洞察分页导航" : "Intelligence pagination"}
    >
      <div className="intel-pagination-summary">
        <span>
          {zh
            ? `第 ${currentPage} / ${totalPages} 页 · 共 ${totalItems} 条洞察`
            : `Page ${currentPage} of ${totalPages} · ${totalItems} insights`}
        </span>
        {totalItems > 10 || pageSize !== 10 ? (
          <div
            className="intel-page-size-group"
            role="group"
            aria-label={zh ? "每页显示条数" : "Items per page"}
          >
            {([10, 20] as const).map((size) => (
              <button
                key={size}
                type="button"
                aria-pressed={pageSize === size}
                className={`intel-page-size-btn${pageSize === size ? " is-active" : ""}`}
                onClick={() => {
                  if (pageSize !== size) onPageSizeChange(size);
                }}
              >
                {zh ? `${size} 条/页` : `${size} / page`}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      {totalPages > 1 ? (
        <div className="intel-pagination-controls">
          <button
            type="button"
            className="button button-secondary button-small"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            {zh ? "上一页" : "Previous"}
          </button>
          <div className="intel-pagination-pages">
            {pageTokens.map((token) =>
              typeof token === "number" ? (
                <button
                  key={token}
                  type="button"
                  aria-label={zh ? `第 ${token} 页` : `Page ${token}`}
                  aria-current={token === currentPage ? "page" : undefined}
                  className={`intel-page-btn${token === currentPage ? " is-active" : ""}`}
                  onClick={() => onPageChange(token)}
                >
                  {token}
                </button>
              ) : (
                <span key={token} className="intel-page-ellipsis" aria-hidden="true">
                  …
                </span>
              ),
            )}
          </div>
          <button
            type="button"
            className="button button-secondary button-small"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            {zh ? "下一页" : "Next"}
          </button>
        </div>
      ) : null}
    </nav>
  );
}

function IntelligenceListRow({
  item,
  saved,
  onSaved,
  onOpenDetail,
  onOpenTopic,
}: {
  item: Intelligence;
  saved: boolean;
  onSaved: () => void;
  onOpenDetail: () => void;
  onOpenTopic?: (topicId: string) => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [busy, setBusy] = useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);
  const toggleSave = async () => {
    if (!item.intelligence_id) return;
    setBusy(true);
    const willSave = !saved;
    try {
      await post(
        saved ? "/saved-intelligence/unsave" : "/saved-intelligence/save",
        { intelligence_id: item.intelligence_id },
      );
      if (willSave) pulseCelebration(saveBtnRef.current);
      onSaved();
    } finally {
      setBusy(false);
    }
  };
  if (item.status !== "AVAILABLE" || !item.card) {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>{t("This Intelligence is not available as current information.")}</p>
      </div>
    );
  }
  const card = item.card;
  const linkedTopics = item.linked_topics ?? [];
  const summaryPreview = (
    card.user_relevant_information.find((line) => line.trim().length > 0) ??
    card.important_new_information.find((line) => line.trim().length > 0) ??
    ""
  ).trim();
  const rawSourceName = card.source_display_name?.trim() ?? "";
  const sourceLabel = rawSourceName
    ? t(rawSourceName)
    : card.video_title?.trim() || card.source_id;
  const evidenceCount = card.evidence_links?.length ?? 0;

  return (
    <article
      className={`intel-list-row${saved ? " is-saved-row" : ""}`}
      onClick={(event) => {
        const target = event.target as HTMLElement | null;
        if (target?.closest("button, a, input, select, summary, details")) return;
        onOpenDetail();
      }}
    >
      <div className="intel-row-header">
        <h2 className="intel-row-title">
          <button
            type="button"
            className="intel-row-title-btn"
            onClick={onOpenDetail}
          >
            {card.core_conclusion}
          </button>
        </h2>
        <div className="intel-row-actions">
          {item.intelligence_id ? (
            <button
              ref={saveBtnRef}
              type="button"
              className={`button button-small ${saved ? "button-saved" : "button-secondary"}`}
              disabled={busy}
              onClick={(event) => {
                event.stopPropagation();
                void toggleSave();
              }}
            >
              <BookmarkSparkIcon saved={saved} />
              {t(busy ? "Saving…" : saved ? "Unsave" : "Save")}
            </button>
          ) : null}
          <button
            type="button"
            className="intel-row-open-btn"
            aria-label={
              zh
                ? `查看详情：${card.core_conclusion}`
                : `View details: ${card.core_conclusion}`
            }
            onClick={(event) => {
              event.stopPropagation();
              onOpenDetail();
            }}
          >
            <span>{zh ? "查看详情" : "View details"}</span>
            <PhosphorIcon name="caret-right" size={13} />
          </button>
        </div>
      </div>
      {summaryPreview ? (
        <p className="intel-row-summary">{summaryPreview}</p>
      ) : null}
      <div className="intel-row-meta">
        <span className="intel-row-source">{sourceLabel}</span>
        {item.effective_published_at ? (
          <span className="intel-row-date tabular-nums">
            {humanDate(item.effective_published_at)}
          </span>
        ) : null}
        {linkedTopics.map((tp) =>
          onOpenTopic ? (
            <button
              key={tp.topic_id}
              type="button"
              className="ai-topic-tag ai-topic-tag-btn"
              onClick={(event) => {
                event.stopPropagation();
                onOpenTopic(tp.topic_id);
              }}
            >
              {`[[${tp.name}]]`}
            </button>
          ) : (
            <span key={tp.topic_id} className="ai-topic-tag">
              {`[[${tp.name}]]`}
            </span>
          ),
        )}
        <span
          className="intel-row-badges"
          aria-label={t("Claim type and current state")}
        >
          <Claim kind={item.claim_kind ?? "SYSTEM_INFERENCE"} />
          <Status value={intelligenceStateLabel(item.state)} />
        </span>
        {evidenceCount > 0 ? (
          <span className="intel-row-evidence-count tabular-nums">
            <PhosphorIcon name="quotes" size={12} />
            {zh
              ? `${evidenceCount} 处原片证据`
              : `${evidenceCount} ${evidenceCount === 1 ? "evidence quote" : "evidence quotes"}`}
          </span>
        ) : null}
      </div>
    </article>
  );
}

function SavedDetailFallbackCard({
  intelligenceId,
  revision,
  saved,
  onSaved,
  onOpenContent,
  onOpenTopic,
}: {
  intelligenceId: string;
  revision: number;
  saved: boolean;
  onSaved: () => void;
  onOpenContent: (videoId: string, evidenceId?: string) => void;
  onOpenTopic?: (topicId: string) => void;
}) {
  const detail = useRemote<{ intelligence: Intelligence }>(
    `/intelligence/${intelligenceId}`,
    revision,
    undefined,
    true,
    true,
  );
  if (detail.error) {
    return (
      <ErrorState
        error={detail.error}
        code={detail.errorCode}
        onReload={detail.reload}
      />
    );
  }
  if (!detail.data) return <Empty>Loading current saved Intelligence…</Empty>;
  return (
    <IntelligenceCard
      item={detail.data.intelligence}
      saved={saved}
      onSaved={onSaved}
      onOpenContent={openContentPassthrough(onOpenContent)}
      onOpenTopic={onOpenTopic}
    />
  );
}

function openContentPassthrough(
  fn: (videoId: string, evidenceId?: string) => void,
) {
  return fn;
}

function IntelligencePage(
  {
    refresh,
    handoffSeq,
    listResetSeq,
    latestFilterRef,
    consumeOriginRestore,
    openContent,
    onOpenTopic,
    openResearch,
    onAskFilteredResearch,
  }: {
    refresh: number;
    handoffSeq?: number;
    listResetSeq?: number;
    latestFilterRef?: { current: IntelFilterSnapshot | null };
    consumeOriginRestore?: () => IntelFilterSnapshot | null;
    openContent: (videoId: string, evidenceId?: string) => void;
    onOpenTopic?: (topicId: string) => void;
    openResearch: () => void;
    onAskFilteredResearch?: (videoIds: string[]) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const restoredIntelRef = useRef<IntelFilterSnapshot | null | undefined>(undefined);
  if (restoredIntelRef.current === undefined) {
    restoredIntelRef.current = consumeOriginRestore?.() ?? null;
  }
  const [view, setView] = useState<"Current" | "Saved">(
    () => restoredIntelRef.current?.view ?? "Current",
  );
  const [revision, setRevision] = useState(0);
  const [intelSearch, setIntelSearch] = useState(
    () => restoredIntelRef.current?.intelSearch ?? "",
  );
  const [intelSourceFilter, setIntelSourceFilter] = useState<string>(
    () => restoredIntelRef.current?.intelSourceFilter ?? "ALL",
  );
  const [intelTopicFilter, setIntelTopicFilter] = useState<string>(
    () =>
      consumePendingIntelligenceTopicId() ||
      restoredIntelRef.current?.intelTopicFilter ||
      "ALL",
  );
  const [pageSize, setPageSize] = useState<10 | 20>(
    () => restoredIntelRef.current?.pageSize ?? 10,
  );
  const [currentPage, setCurrentPage] = useState<number>(
    () => restoredIntelRef.current?.currentPage ?? 1,
  );
  const [savedPage, setSavedPage] = useState<number>(
    () => restoredIntelRef.current?.savedPage ?? 1,
  );
  const [selectedDetail, setSelectedDetail] = useState<{
    key: string;
    item: Intelligence;
  } | null>(null);
  const prevListResetSeqRef = useRef(listResetSeq);
  useEffect(() => {
    if (prevListResetSeqRef.current !== listResetSeq) {
      prevListResetSeqRef.current = listResetSeq;
      setSelectedDetail(null);
    }
  }, [listResetSeq]);
  if (latestFilterRef) {
    latestFilterRef.current = {
      view,
      intelSearch,
      intelSourceFilter,
      intelTopicFilter,
      currentPage,
      savedPage,
      pageSize,
    };
  }
  const [copiedFilteredDigest, setCopiedFilteredDigest] = useState(false);
  const [copiedSavedDigest, setCopiedSavedDigest] = useState(false);
  useEffect(() => {
    const nextTopicId = consumePendingIntelligenceTopicId();
    if (nextTopicId) {
      setView("Current");
      setIntelTopicFilter(nextTopicId);
      setCurrentPage(1);
      setSelectedDetail(null);
    }
  }, [handoffSeq]);
  const current = useRemote<{ intelligence: Intelligence[]; activity?: { video_id: string; title: string; status: string; cloud_http429_code?: string; selected_provider?: string; can_cancel?: boolean }[] }>(
    "/intelligence",
    refresh + revision,
    undefined,
    true,
    true,
  );
  const saved = useRemote<{ saved: Saved[] }>(
    "/saved-intelligence",
    refresh + revision,
    undefined,
    true,
    true,
  );
  const source = view === "Current"
    ? current
    : saved;
  const currentAvailable = useMemo(
    () =>
      sortIntelligenceNewestFirst(
        (current.data?.intelligence ?? []).filter(
          (item) => item.status === "AVAILABLE" && item.trusted,
        ),
      ),
    [current.data?.intelligence],
  );
  const currentById = useMemo(() => {
    const map = new Map<string, Intelligence>();
    for (const item of currentAvailable) {
      if (item.intelligence_id) map.set(item.intelligence_id, item);
    }
    return map;
  }, [currentAvailable]);
  const allKnownSources = useMemo(() => {
    const set = new Set<string>();
    for (const item of currentAvailable) {
      const name = item.card?.source_display_name?.trim();
      if (name) set.add(name);
    }
    return set;
  }, [currentAvailable]);
  const allKnownTopics = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of currentAvailable) {
      for (const tp of item.linked_topics ?? []) {
        if (!map.has(tp.topic_id)) map.set(tp.topic_id, tp.name);
      }
    }
    return map;
  }, [currentAvailable]);
  const effectiveIntelSource =
    intelSourceFilter === "ALL" || allKnownSources.has(intelSourceFilter)
      ? intelSourceFilter
      : "ALL";
  const effectiveIntelTopic =
    intelTopicFilter === "ALL" || allKnownTopics.has(intelTopicFilter)
      ? intelTopicFilter
      : "ALL";
  const matchesIntelQuery = useCallback(
    (item: Intelligence, q: string) => {
      if (!q) return true;
      const rawSrc = item.card?.source_display_name?.trim() ?? "";
      const haystack = [
        item.card?.core_conclusion,
        item.card?.video_title,
        rawSrc,
        rawSrc ? t(rawSrc) : "",
        ...(item.linked_topics ?? []).map((tp) => tp.name),
        ...(item.card?.user_relevant_information ?? []),
        ...(item.card?.important_new_information ?? []),
        ...(item.card?.meaningful_details ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    },
    [t],
  );
  const sourceBaseAvailable = useMemo(() => {
    const q = intelSearch.trim().toLowerCase();
    return currentAvailable.filter((item) => {
      if (
        effectiveIntelTopic !== "ALL" &&
        !(item.linked_topics ?? []).some((tp) => tp.topic_id === effectiveIntelTopic)
      ) {
        return false;
      }
      return matchesIntelQuery(item, q);
    });
  }, [currentAvailable, effectiveIntelTopic, intelSearch, matchesIntelQuery]);
  const topicBaseAvailable = useMemo(() => {
    const q = intelSearch.trim().toLowerCase();
    return currentAvailable.filter((item) => {
      if (
        effectiveIntelSource !== "ALL" &&
        (item.card?.source_display_name?.trim() ?? "") !== effectiveIntelSource
      ) {
        return false;
      }
      return matchesIntelQuery(item, q);
    });
  }, [currentAvailable, effectiveIntelSource, intelSearch, matchesIntelQuery]);
  const intelSources = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of sourceBaseAvailable) {
      const name = item.card?.source_display_name?.trim();
      if (name) counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    if (effectiveIntelSource !== "ALL" && !counts.has(effectiveIntelSource)) {
      counts.set(effectiveIntelSource, 0);
    }
    return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
  }, [sourceBaseAvailable, effectiveIntelSource]);
  const intelTopics = useMemo(() => {
    const byId = new Map<string, { topic_id: string; name: string; count: number }>();
    for (const item of topicBaseAvailable) {
      for (const tp of item.linked_topics ?? []) {
        const existing = byId.get(tp.topic_id);
        if (existing) {
          existing.count += 1;
        } else {
          byId.set(tp.topic_id, { topic_id: tp.topic_id, name: tp.name, count: 1 });
        }
      }
    }
    if (effectiveIntelTopic !== "ALL" && !byId.has(effectiveIntelTopic)) {
      const knownName = allKnownTopics.get(effectiveIntelTopic);
      if (knownName) {
        byId.set(effectiveIntelTopic, {
          topic_id: effectiveIntelTopic,
          name: knownName,
          count: 0,
        });
      }
    }
    return Array.from(byId.values()).sort(
      (a, b) => b.count - a.count || a.name.localeCompare(b.name),
    );
  }, [topicBaseAvailable, effectiveIntelTopic, allKnownTopics]);
  const filteredAvailable = useMemo(() => {
    if (effectiveIntelSource === "ALL") return sourceBaseAvailable;
    return sourceBaseAvailable.filter(
      (item) => (item.card?.source_display_name?.trim() ?? "") === effectiveIntelSource,
    );
  }, [sourceBaseAvailable, effectiveIntelSource]);
  const filteredVideoIds = useMemo(
    () =>
      Array.from(
        new Set(
          filteredAvailable
            .map((item) => item.card?.video_id?.trim())
            .filter((id): id is string => Boolean(id)),
        ),
      ).slice(0, 12),
    [filteredAvailable],
  );
  const hasActiveIntelFilter =
    effectiveIntelTopic !== "ALL" ||
    effectiveIntelSource !== "ALL" ||
    intelSearch.trim().length > 0;
  const savedIdSet = useMemo(
    () => new Set((saved.data?.saved ?? []).map((entry) => entry.intelligence_id)),
    [saved.data?.saved],
  );

  const currentTotalPages = Math.max(1, Math.ceil(filteredAvailable.length / pageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), currentTotalPages);
  const pagedCurrentAvailable = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredAvailable.slice(start, start + pageSize);
  }, [filteredAvailable, safeCurrentPage, pageSize]);

  const savedEntries = saved.data?.saved ?? [];
  const savedTotalPages = Math.max(1, Math.ceil(savedEntries.length / pageSize));
  const safeSavedPage = Math.min(Math.max(1, savedPage), savedTotalPages);
  const pagedSavedEntries = useMemo(() => {
    const start = (safeSavedPage - 1) * pageSize;
    return savedEntries.slice(start, start + pageSize);
  }, [savedEntries, safeSavedPage, pageSize]);

  const detailList = useMemo(() => {
    if (view === "Current") {
      return filteredAvailable.map((it, idx) => ({
        key: getIntelligenceRowKey(it, idx),
        item: it,
      }));
    }
    return savedEntries
      .filter((entry) => entry.intelligence.status === "AVAILABLE")
      .map((entry, idx) => {
        const resolved = currentById.get(entry.intelligence_id) ?? entry.intelligence;
        return {
          key: entry.intelligence_id || getIntelligenceRowKey(resolved, idx),
          item: resolved,
        };
      });
  }, [view, filteredAvailable, savedEntries, currentById]);

  const handleBackToList = useCallback(() => {
    runViewTransition(() => {
      setSelectedDetail(null);
    });
    scrollWorkspaceToTop();
  }, []);

  useEffect(() => {
    if (!selectedDetail) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isKeyboardShortcutBlocked(event)) {
        event.preventDefault();
        handleBackToList();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedDetail, handleBackToList]);

  const researchEntry = <div className="button-row"><button type="button" className="button button-secondary" onClick={openResearch}>{t("Research")}</button></div>;
  if (source.error) return <>{researchEntry}<ErrorState error={source.error} code={source.errorCode} onReload={source.reload} /></>;

  if (selectedDetail) {
    const detailIndex = detailList.findIndex((entry) => entry.key === selectedDetail.key);
    const activeDetailItem =
      (detailIndex >= 0 ? detailList[detailIndex].item : null) ??
      (selectedDetail.item.intelligence_id
        ? currentById.get(selectedDetail.item.intelligence_id)
        : undefined) ??
      selectedDetail.item;
    const activeTotalPages = view === "Current" ? currentTotalPages : savedTotalPages;
    const activePage = view === "Current" ? safeCurrentPage : safeSavedPage;
    const backLabel =
      activeTotalPages > 1
        ? zh
          ? `返回洞察列表（第 ${activePage} 页）`
          : `Back to Intelligence list (Page ${activePage})`
        : zh
          ? "返回洞察列表"
          : "Back to Intelligence list";
    const isActiveSaved = Boolean(
      activeDetailItem.intelligence_id &&
        savedIdSet.has(activeDetailItem.intelligence_id),
    );
    const stepDetail = (delta: -1 | 1) => {
      if (detailIndex < 0) return;
      const nextIdx = detailIndex + delta;
      if (nextIdx < 0 || nextIdx >= detailList.length) return;
      const nextEntry = detailList[nextIdx];
      runViewTransition(() => {
        setSelectedDetail(nextEntry);
        if (view === "Current") {
          setCurrentPage(Math.floor(nextIdx / pageSize) + 1);
        } else {
          const fullSavedIdx = savedEntries.findIndex(
            (s) => s.intelligence_id === nextEntry.item.intelligence_id,
          );
          setSavedPage(
            Math.floor((fullSavedIdx >= 0 ? fullSavedIdx : nextIdx) / pageSize) + 1,
          );
        }
      });
      scrollWorkspaceToTop();
    };

    return (
      <div className="intel-detail-view">
        <div className="intel-detail-nav-bar">
          <button
            type="button"
            className="button button-secondary intel-detail-back-btn"
            onClick={handleBackToList}
          >
            <PhosphorIcon name="arrow-left" size={14} />
            <span>{backLabel}</span>
          </button>
          {detailIndex >= 0 && detailList.length > 1 ? (
            <div
              className="intel-detail-stepper tabular-nums"
              role="group"
              aria-label={zh ? "切换相邻洞察" : "Navigate adjacent insights"}
            >
              <span className="intel-detail-stepper-pos">
                {zh
                  ? `第 ${detailIndex + 1} / ${detailList.length} 条`
                  : `${detailIndex + 1} of ${detailList.length}`}
              </span>
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={detailIndex <= 0}
                onClick={() => stepDetail(-1)}
              >
                {zh ? "上一条" : "Previous"}
              </button>
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={detailIndex >= detailList.length - 1}
                onClick={() => stepDetail(1)}
              >
                {zh ? "下一条" : "Next"}
              </button>
            </div>
          ) : null}
        </div>
        {!activeDetailItem.card && activeDetailItem.intelligence_id ? (
          <SavedDetailFallbackCard
            intelligenceId={activeDetailItem.intelligence_id}
            revision={revision}
            saved={isActiveSaved}
            onSaved={() => setRevision((value) => value + 1)}
            onOpenContent={openContent}
            onOpenTopic={onOpenTopic}
          />
        ) : (
          <IntelligenceCard
            key={selectedDetail.key}
            item={activeDetailItem}
            saved={isActiveSaved}
            onSaved={() => setRevision((value) => value + 1)}
            onOpenContent={openContent}
            onOpenTopic={onOpenTopic}
          />
        )}
      </div>
    );
  }

  return (
    <>
      {researchEntry}
      <div className="segmented">
        {(["Current", "Saved"] as const).map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={view === item}
            className={view === item ? "active" : ""}
            onClick={() => {
              setView(item);
              setSelectedDetail(null);
            }}
          >
            {t(item)}
          </button>
        ))}
      </div>
      {view === "Current" && (currentAvailable.length >= 4 || allKnownTopics.size > 0) ? (
        <div className="intel-filter-toolbar">
          <div className="intel-filter-top-row">
            <input
              type="search"
              className="intel-search-input"
              aria-label={
                zh
                  ? "搜索洞察结论或视频标题"
                  : "Search Intelligence conclusions or video titles"
              }
              placeholder={
                zh
                  ? "搜索洞察结论、关键要点或视频标题…"
                  : "Search conclusions, key points, or video titles…"
              }
              value={intelSearch}
              onChange={(event) => {
                setIntelSearch(event.target.value);
                setCurrentPage(1);
              }}
            />
            {allKnownTopics.size > 0 ? (
              <select
                className="content-topic-select tabular-nums"
                aria-label={zh ? "按专题筛选洞察" : "Filter Intelligence by topic"}
                value={effectiveIntelTopic}
                onChange={(event) => {
                  setIntelTopicFilter(event.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="ALL">
                  {zh ? "全部专题" : "All topics"}
                </option>
                {intelTopics.map((tp) => (
                  <option key={tp.topic_id} value={tp.topic_id}>
                    {`${tp.name} (${tp.count})`}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
          {allKnownSources.size > 1 && intelSources.length > 0 ? (
            <div
              className="ai-suggested-pills tabular-nums"
              role="group"
              aria-label={zh ? "按来源筛选洞察" : "Filter Intelligence by source"}
            >
              <button
                type="button"
                className={`ai-question-chip${effectiveIntelSource === "ALL" ? " is-active" : ""}`}
                aria-pressed={effectiveIntelSource === "ALL"}
                onClick={() => {
                  setIntelSourceFilter("ALL");
                  setCurrentPage(1);
                }}
              >
                {zh ? `全部 (${sourceBaseAvailable.length})` : `All (${sourceBaseAvailable.length})`}
              </button>
              {intelSources.map((src) => (
                <button
                  key={src.name}
                  type="button"
                  className={`ai-question-chip${effectiveIntelSource === src.name ? " is-active" : ""}`}
                  aria-pressed={effectiveIntelSource === src.name}
                  onClick={() => {
                    setIntelSourceFilter(src.name);
                    setCurrentPage(1);
                  }}
                >
                  {`${t(src.name)} (${src.count})`}
                </button>
              ))}
            </div>
          ) : null}
          {hasActiveIntelFilter && filteredAvailable.length > 0 ? (
            <div
              className="intel-active-filter-bar tabular-nums"
              role="status"
              aria-live="polite"
            >
              <span>
                {zh
                  ? `当前筛选命中 ${filteredAvailable.length} / ${currentAvailable.length} 张验证洞察`
                  : `Showing ${filteredAvailable.length} of ${currentAvailable.length} verified insights`}
              </span>
              <div className="intel-filter-bar-actions">
                {filteredVideoIds.length > 0 && onAskFilteredResearch ? (
                  <button
                    type="button"
                    className="button button-primary button-small"
                    onClick={(event) => {
                      pulseCelebration(event.currentTarget);
                      onAskFilteredResearch(filteredVideoIds);
                    }}
                  >
                    <PhosphorIcon name="sparkle" size={13} />
                    {zh
                      ? `围绕当前洞察追问 (${filteredVideoIds.length})`
                      : `Ask AI on filtered (${filteredVideoIds.length})`}
                  </button>
                ) : null}
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={(event) => {
                    pulseCelebration(event.currentTarget);
                    void navigator.clipboard?.writeText(
                      formatPlainTextIntelligenceDigest(filteredAvailable, zh, "filtered"),
                    );
                    setCopiedFilteredDigest(true);
                    setTimeout(() => setCopiedFilteredDigest(false), 2200);
                  }}
                >
                  <PhosphorIcon name="quotes" size={13} />
                  {copiedFilteredDigest
                    ? zh
                      ? "已复制筛选洞察"
                      : "Copied filtered insights"
                    : zh
                      ? `复制当前筛选洞察 (${filteredAvailable.length})`
                      : `Copy filtered insights (${filteredAvailable.length})`}
                </button>
                <button
                  type="button"
                  className="button button-ghost button-small"
                  onClick={() => {
                    setIntelSearch("");
                    setIntelSourceFilter("ALL");
                    setIntelTopicFilter("ALL");
                    setCurrentPage(1);
                  }}
                >
                  {zh ? "重置筛选" : "Reset filters"}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
      {view === "Current" && current.data?.activity?.length ? <Panel title="Analysis activity">
        {current.data.activity.map(item => <article className="metadata-row" key={`${item.video_id}:${item.status}`}>
          <div><strong>{item.title}</strong><p>{t(intelligenceResultCopy(item.status, item.cloud_http429_code, item.selected_provider, item.can_cancel))}</p>
            {item.status === "WAITING_MODEL" && item.selected_provider === "zhipu_bigmodel" && <a className="source-link" href={`#Settings/models/bigmodel?return=${encodeURIComponent(`#Content/${item.video_id}`)}`}>{t("Settings")}</a>}
            <button className="button button-secondary" onClick={() => openContent(item.video_id)}>{t("Open Content")}</button></div>
        </article>)}
      </Panel> : null}
      {view === "Current" && (!current.data
        ? <Empty>Loading verified Intelligence…</Empty>
        : currentAvailable.length
        ? filteredAvailable.length
          ? (
            <>
              <div className="intel-list-surface">
                {pagedCurrentAvailable.map((item, localIdx) => {
                  const globalIdx = (safeCurrentPage - 1) * pageSize + localIdx;
                  const rowKey = getIntelligenceRowKey(item, globalIdx);
                  return (
                    <IntelligenceListRow
                      key={rowKey}
                      item={item}
                      saved={Boolean(
                        item.intelligence_id && savedIdSet.has(item.intelligence_id),
                      )}
                      onSaved={() => setRevision((value) => value + 1)}
                      onOpenDetail={() => {
                        runViewTransition(() => {
                          setSelectedDetail({ key: rowKey, item });
                        });
                        scrollWorkspaceToTop();
                      }}
                      onOpenTopic={onOpenTopic}
                    />
                  );
                })}
              </div>
              <IntelPaginationBar
                currentPage={safeCurrentPage}
                totalPages={currentTotalPages}
                totalItems={filteredAvailable.length}
                pageSize={pageSize}
                zh={zh}
                onPageChange={(next) => {
                  setCurrentPage(next);
                  scrollWorkspaceToTop();
                }}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setCurrentPage(1);
                  scrollWorkspaceToTop();
                }}
              />
            </>
          )
          : (
            <Panel title={zh ? "未找到匹配的洞察卡片" : "No matching Intelligence cards"}>
              <p className="hint">
                {zh
                  ? "当前搜索词、专题或来源筛选下暂无匹配项。"
                  : "No verified Intelligence cards match your current search, topic, or source filter."}
              </p>
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={() => {
                  setIntelSearch("");
                  setIntelSourceFilter("ALL");
                  setIntelTopicFilter("ALL");
                  setCurrentPage(1);
                }}
              >
                {zh ? "清除筛选" : "Clear filters"}
              </button>
            </Panel>
          )
        : current.data.activity?.length ? null : <Empty>No verified Intelligence yet.</Empty>)}
      {view === "Saved" && (!saved.data
        ? <Empty>Loading saved Intelligence…</Empty>
        : savedEntries.length
        ? (() => {
          const availableSavedItems = savedEntries
            .map((entry) => currentById.get(entry.intelligence_id) ?? entry.intelligence)
            .filter((it) => it.status === "AVAILABLE" && Boolean(it.card));
          const savedVideoIds = Array.from(
            new Set(
              availableSavedItems
                .map((it) => it.card?.video_id?.trim())
                .filter((id): id is string => Boolean(id)),
            ),
          ).slice(0, 12);
          return (
            <>
              {availableSavedItems.length > 0 ? (
                <div className="intel-saved-digest-bar tabular-nums">
                  <span>
                    {zh
                      ? `已收藏 ${availableSavedItems.length} 张可用验证洞察`
                      : `${availableSavedItems.length} saved verified insights`}
                  </span>
                  <div className="intel-filter-bar-actions">
                    {savedVideoIds.length > 0 && onAskFilteredResearch ? (
                      <button
                        type="button"
                        className="button button-primary button-small"
                        onClick={(event) => {
                          pulseCelebration(event.currentTarget);
                          onAskFilteredResearch(savedVideoIds);
                        }}
                      >
                        <PhosphorIcon name="sparkle" size={13} />
                        {zh
                          ? `围绕收藏洞察追问 (${savedVideoIds.length})`
                          : `Ask AI on saved (${savedVideoIds.length})`}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="button button-secondary button-small"
                      onClick={(event) => {
                        pulseCelebration(event.currentTarget);
                        void navigator.clipboard?.writeText(
                          formatPlainTextIntelligenceDigest(
                            availableSavedItems,
                            zh,
                            "saved",
                          ),
                        );
                        setCopiedSavedDigest(true);
                        setTimeout(() => setCopiedSavedDigest(false), 2200);
                      }}
                    >
                      <PhosphorIcon name="quotes" size={13} />
                      {copiedSavedDigest
                        ? zh
                          ? "已复制收藏合集"
                          : "Copied saved digest"
                        : zh
                          ? `复制已收藏洞察合集 (${availableSavedItems.length})`
                          : `Copy saved digest (${availableSavedItems.length})`}
                    </button>
                  </div>
                </div>
              ) : null}
              <div className="intel-list-surface">
                {pagedSavedEntries.map((entry, localIdx) => {
                  if (entry.intelligence.status !== "AVAILABLE") {
                    return (
                      <div
                        key={entry.intelligence_id}
                        className="semantic-state state-neutral intel-saved-unavailable-row"
                      >
                        <Status value="UNAVAILABLE" />
                        <p>
                          {t("This saved item is no longer available as current Intelligence. Its saved reference remains until you choose Unsave.")}
                        </p>
                        <button
                          type="button"
                          className="button button-secondary button-small"
                          onClick={async () => {
                            await post("/saved-intelligence/unsave", {
                              intelligence_id: entry.intelligence_id,
                            });
                            setRevision((value) => value + 1);
                          }}
                        >
                          {t("Unsave")}
                        </button>
                      </div>
                    );
                  }
                  const resolvedItem =
                    currentById.get(entry.intelligence_id) ?? entry.intelligence;
                  const rowKey =
                    entry.intelligence_id ||
                    getIntelligenceRowKey(
                      resolvedItem,
                      (safeSavedPage - 1) * pageSize + localIdx,
                    );
                  return (
                    <IntelligenceListRow
                      key={rowKey}
                      item={resolvedItem}
                      saved
                      onSaved={() => setRevision((value) => value + 1)}
                      onOpenDetail={() => {
                        runViewTransition(() => {
                          setSelectedDetail({ key: rowKey, item: resolvedItem });
                        });
                        scrollWorkspaceToTop();
                      }}
                      onOpenTopic={onOpenTopic}
                    />
                  );
                })}
              </div>
              <IntelPaginationBar
                currentPage={safeSavedPage}
                totalPages={savedTotalPages}
                totalItems={savedEntries.length}
                pageSize={pageSize}
                zh={zh}
                onPageChange={(next) => {
                  setSavedPage(next);
                  scrollWorkspaceToTop();
                }}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setSavedPage(1);
                  scrollWorkspaceToTop();
                }}
              />
            </>
          );
        })()
        : <Empty>No saved Intelligence.</Empty>)}
    </>
  );
}
function contentItemChannelKeyAndLabel(
  item: ContentItem,
  language: "zh-CN" | "en",
): { key: string; label: string } {
  const rawName = (item.channel_name ?? "").trim();
  const provider = (item.provider ?? "YOUTUBE").trim().toUpperCase();
  if (
    provider === "LOCAL" &&
    (!rawName || rawName.toLowerCase() === "local" || rawName.toLowerCase() === "local library")
  ) {
    return { key: "LOCAL", label: language === "zh-CN" ? "本地实战课" : "Local" };
  }
  if (rawName) {
    return { key: rawName, label: rawName };
  }
  return { key: provider, label: provider };
}
function ContentPage(
  {
    refresh,
    handoffSeq,
    targetVideoId,
    highlightedEvidenceId,
    latestFilterRef,
    consumeOriginRestore,
    onOpen,
    onClose,
    onAdd,
    onAddLocal,
    onAskStarredResearch,
    onAskFilteredResearch,
    onSelectTopicCluster,
  }: {
    refresh: number;
    handoffSeq?: number;
    targetVideoId?: string | null;
    highlightedEvidenceId?: string | null;
    latestFilterRef?: { current: ContentFilterSnapshot | null };
    consumeOriginRestore?: () => ContentFilterSnapshot | null;
    onOpen: (id: string) => void;
    onClose: () => void;
    onAdd: () => void;
    onAddLocal?: () => void;
    onAskStarredResearch?: () => void;
    onAskFilteredResearch?: (videoIds: string[]) => void;
    onSelectTopicCluster?: (clusterName: string) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const restoredContentRef = useRef<ContentFilterSnapshot | null | undefined>(undefined);
  if (restoredContentRef.current === undefined) {
    restoredContentRef.current = consumeOriginRestore?.() ?? null;
  }
  const [searchQuery, setSearchQuery] = useState(
    () => restoredContentRef.current?.searchQuery ?? "",
  );
  const [providerFilter, setProviderFilter] = useState<"ALL" | "YOUTUBE" | "BILIBILI" | "LOCAL">(
    () => restoredContentRef.current?.providerFilter ?? "ALL",
  );
  const [bucketFilter, setBucketFilter] = useState<
    "ALL" | "UNREAD" | "MUST_WATCH" | "STARRED" | "TUTORIAL" | "SHORTS"
  >(() => restoredContentRef.current?.bucketFilter ?? "ALL");
  const [topicFilter, setTopicFilter] = useState<string>(
    () => consumePendingContentTopic() || restoredContentRef.current?.topicFilter || "ALL",
  );
  const [channelFilter, setChannelFilter] = useState<string>(
    () => consumePendingContentChannel() || restoredContentRef.current?.channelFilter || "ALL",
  );
  const [contentSortMode, setContentSortMode] = useState<"newest" | "score">("newest");
  if (latestFilterRef) {
    latestFilterRef.current = {
      searchQuery,
      providerFilter,
      bucketFilter,
      topicFilter,
      channelFilter,
    };
  }
  useEffect(() => {
    const nextChannel = consumePendingContentChannel();
    if (nextChannel) setChannelFilter(nextChannel);
    const nextTopic = consumePendingContentTopic();
    if (nextTopic) setTopicFilter(nextTopic);
  }, [handoffSeq]);
  const [kbActiveId, setKbActiveId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const kbContextRef = useRef<{
    isListActive: boolean;
    primaryIds: string[];
    activeId: string | null;
    briefMap: Map<string, VideoAiBrief>;
    toggleRowCuration: (
      videoId: string,
      patchBody: { starred?: boolean; is_read?: boolean },
    ) => Promise<void>;
    onOpen: (id: string) => void;
  }>({
    isListActive: false,
    primaryIds: [],
    activeId: null,
    briefMap: new Map(),
    toggleRowCuration: async () => {},
    onOpen,
  });
  const [curationBusyId, setCurationBusyId] = useState<string | null>(null);
  const [batchCurationBusy, setBatchCurationBusy] = useState(false);
  const [lastBatchReadIds, setLastBatchReadIds] = useState<string[]>([]);
  const [copiedContentDigest, setCopiedContentDigest] = useState(false);
  useEffect(() => {
    setCopiedContentDigest(false);
  }, [searchQuery, providerFilter, bucketFilter, topicFilter, channelFilter]);
  const [aiSyncState, setAiSyncState] = useState<{
    running: boolean;
    processedCount: number;
    error: string | null;
  } | null>(null);
  const [batchState, setBatchState] = useState<{
    running: boolean;
    done: number;
    total: number;
    succeeded: number;
    failed: number;
    currentTitle: string | null;
  } | null>(null);
  const batchStopRef = useRef(false);
  const batchCommandsRef = useRef(new Map<string, string>());
  useEffect(() => () => { batchStopRef.current = true; }, []);
  const list = useRemote<{ videos: ContentItem[] }>("/videos", refresh + revision, undefined, true, true);
  useEffect(() => {
    if (
      targetVideoId ||
      batchState?.running ||
      !list.data?.videos?.some(
        (item) =>
          trackedRetryActive(item.tracked_content_retry, item.video_id) ||
          ["WAITING", "FETCHING", "READING_CAPTIONS", "ORGANIZING", "TRANSCRIPT_READY", "RETRY_PENDING", "RUNNING", "PENDING"].includes(item.processing_status),
      )
    ) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [list.data, targetVideoId, batchState?.running]);
  kbContextRef.current.isListActive = false;
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const ctx = kbContextRef.current;
      if (!ctx.isListActive) return;
      if (isKeyboardShortcutBlocked(event)) return;
      if (event.key === "/") {
        if (searchInputRef.current) {
          event.preventDefault();
          searchInputRef.current.focus();
          searchInputRef.current.select?.();
        }
        return;
      }
      if (ctx.primaryIds.length === 0) return;
      const currentIdx = ctx.activeId ? ctx.primaryIds.indexOf(ctx.activeId) : 0;
      const resolvedIdx = currentIdx >= 0 ? currentIdx : 0;
      const currentId = ctx.primaryIds[resolvedIdx];
      const key = event.key.toLowerCase();
      if (key === "j" || key === "k") {
        event.preventDefault();
        if (
          document.activeElement instanceof HTMLElement &&
          document.activeElement !== document.body
        ) {
          document.activeElement.blur();
        }
        const nextIdx =
          key === "j"
            ? Math.min(ctx.primaryIds.length - 1, resolvedIdx + 1)
            : Math.max(0, resolvedIdx - 1);
        const nextId = ctx.primaryIds[nextIdx];
        setKbActiveId(nextId);
        const safeSelectorId =
          typeof CSS !== "undefined" && typeof CSS.escape === "function"
            ? CSS.escape(nextId)
            : nextId.replace(/"/g, '\\"');
        const rowEl = document.querySelector(`[data-kb-video-id="${safeSelectorId}"]`);
        rowEl?.scrollIntoView?.({ block: "nearest" });
      } else if (key === "s" && currentId) {
        const brief = ctx.briefMap.get(currentId);
        if (!brief) return;
        event.preventDefault();
        void ctx.toggleRowCuration(currentId, { starred: !brief.starred });
      } else if (key === "e" && currentId) {
        const brief = ctx.briefMap.get(currentId);
        if (!brief) return;
        event.preventDefault();
        void ctx.toggleRowCuration(currentId, { is_read: !brief.is_read });
      } else if (event.key === "Enter" && currentId) {
        const interactiveFocused =
          (event.target instanceof HTMLElement &&
            event.target.closest("button, a, summary, details, [role='button']")) ||
          (document.activeElement instanceof HTMLElement &&
            document.activeElement !== document.body &&
            document.activeElement.closest("button, a, summary, details, [role='button']"));
        if (interactiveFocused) return;
        event.preventDefault();
        ctx.onOpen(currentId);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
  if (list.error) return <ErrorState error={list.error} code={list.errorCode} onReload={list.reload} />;
  if (!list.data) return <Empty>Loading Content…</Empty>;
  if (targetVideoId) {
    const rawVideos = Array.isArray(list.data.videos) ? list.data.videos : [];
    const trimmedQuery = searchQuery.trim().toLowerCase();
    const isScopedQueue =
      providerFilter !== "ALL" ||
      channelFilter !== "ALL" ||
      topicFilter !== "ALL" ||
      (bucketFilter !== "ALL" && bucketFilter !== "UNREAD" && bucketFilter !== "SHORTS") ||
      trimmedQuery.length > 0;
    const filterParts: string[] = [];
    if (topicFilter !== "ALL") filterParts.push(topicFilter);
    if (channelFilter !== "ALL") {
      const matchedCh = rawVideos.find(
        (v) => contentItemChannelKeyAndLabel(v, language).key === channelFilter,
      );
      filterParts.push(
        matchedCh
          ? contentItemChannelKeyAndLabel(matchedCh, language).label
          : channelFilter === "LOCAL"
            ? language === "zh-CN"
              ? "本地实战课"
              : "Local courses"
            : channelFilter,
      );
    }
    if (providerFilter !== "ALL") {
      filterParts.push(
        providerFilter === "LOCAL"
          ? t("Local")
          : providerFilter === "BILIBILI"
            ? t("Bilibili")
            : "YouTube",
      );
    }
    if (bucketFilter === "MUST_WATCH") {
      filterParts.push(language === "zh-CN" ? "必看干货" : "Must-watch");
    } else if (bucketFilter === "STARRED") {
      filterParts.push(language === "zh-CN" ? "已收藏" : "Starred");
    } else if (bucketFilter === "TUTORIAL") {
      filterParts.push(language === "zh-CN" ? "教程拆解" : "Tutorials");
    } else if (bucketFilter === "UNREAD") {
      filterParts.push(language === "zh-CN" ? "仅未读" : "Unread only");
    }
    if (searchQuery.trim()) {
      filterParts.push(`“${searchQuery.trim()}”`);
    }
    const activeFilterSummary = filterParts.length > 0 ? filterParts.join(" · ") : null;

    const unreadCandidates = rawVideos
      .filter((item) => {
        if (item.work_kind || item.video_id === targetVideoId) return false;
        const brief = readVideoAiBrief(item.ai_brief, item.duration_seconds);
        if (!brief || brief.is_short_noise || brief.is_read) return false;
        if (!isScopedQueue) return true;
        const itemProvider = item.provider ?? "YOUTUBE";
        if (providerFilter !== "ALL" && itemProvider !== providerFilter) return false;
        if (
          channelFilter !== "ALL" &&
          contentItemChannelKeyAndLabel(item, language).key !== channelFilter
        ) {
          return false;
        }
        if (topicFilter !== "ALL" && brief.topic_cluster_zh.trim() !== topicFilter) {
          return false;
        }
        if (bucketFilter === "MUST_WATCH" && brief.recommendation_tier !== "MUST_WATCH") {
          return false;
        }
        if (bucketFilter === "STARRED" && !brief.starred) {
          return false;
        }
        if (bucketFilter === "TUTORIAL" && brief.content_bucket !== "TUTORIAL") {
          return false;
        }
        if (trimmedQuery) {
          const haystack =
            `${item.title ?? ""} ${item.channel_name ?? ""} ${item.video_id} ${brief.headline_zh} ${brief.topic_cluster_zh}`.toLowerCase();
          if (!haystack.includes(trimmedQuery)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (contentSortMode === "score") {
          const sa = readVideoAiBrief(a.ai_brief, a.duration_seconds)?.score ?? 0;
          const sb = readVideoAiBrief(b.ai_brief, b.duration_seconds)?.score ?? 0;
          if (sb !== sa) return sb - sa;
        }
        const timeOrder = compareContentNewestFirst(a, b);
        if (timeOrder !== 0) return timeOrder;
        const sa = readVideoAiBrief(a.ai_brief, a.duration_seconds)?.score ?? 0;
        const sb = readVideoAiBrief(b.ai_brief, b.duration_seconds)?.score ?? 0;
        return sb - sa;
      });
    const nextUnread = unreadCandidates[0]
      ? {
          videoId: unreadCandidates[0].video_id,
          title: unreadCandidates[0].title ?? unreadCandidates[0].video_id,
          remainingCount: unreadCandidates.length,
          scoped: isScopedQueue,
        }
      : null;
    return (
      <ContentDetailPanel
        key={targetVideoId}
        id={targetVideoId}
        highlightedEvidenceId={highlightedEvidenceId}
        onClose={onClose}
        onAddLocal={onAddLocal}
        activeFilterSummary={activeFilterSummary}
        nextUnreadVideo={nextUnread}
        onAdvanceToVideo={(nextId) => {
          setRevision((value) => value + 1);
          onOpen(nextId);
        }}
        onListChanged={() => setRevision((value) => value + 1)}
        onSelectTopicCluster={onSelectTopicCluster}
      />
    );
  }
  const videos = list.data.videos;
  const isManualPendingImport = (item: ContentItem) =>
    item.work_kind === "DURABLE_CONTENT_IDENTITY" &&
    Boolean(item.source_id && !item.source_id.startsWith("youtube-channel-"));
  const manualPendingVideos = [...videos.filter(isManualPendingImport)].sort(
    compareContentNewestFirst,
  );
  const removeManualPendingImport = async (sourceId: string) => {
    setBatchCurationBusy(true);
    try {
      await patch(`/sources/${sourceId}`, { enabled: false });
      setRevision((value) => value + 1);
    } catch {
      /* Preserve current list when request cannot reach local API. */
    } finally {
      setBatchCurationBusy(false);
    }
  };
  const retryableVideos = videos.filter(
    (item) =>
      (item.provider ?? "YOUTUBE") === "YOUTUBE" &&
      readTrackedRetry(item.tracked_content_retry, item.video_id)?.retry_allowed === true,
  );
  const runBatchCaptionRecovery = async (targets: ContentItem[]) => {
    if (!targets.length || batchState?.running) return;
    batchStopRef.current = false;
    let succeededCount = 0;
    let failedCount = 0;
    setBatchState({
      running: true,
      done: 0,
      total: targets.length,
      succeeded: 0,
      failed: 0,
      currentTitle: targets[0]?.title ?? targets[0]?.video_id ?? null,
    });
    for (let idx = 0; idx < targets.length; idx += 1) {
      if (batchStopRef.current) break;
      const item = targets[idx];
      setBatchState({
        running: true,
        done: idx,
        total: targets.length,
        succeeded: succeededCount,
        failed: failedCount,
        currentTitle: item.title ?? item.video_id,
      });
      try {
        const statusResp = await api<{ tracked_content_retry?: unknown }>(
          `/content/${encodeURIComponent(item.video_id)}/retry`,
        );
        const freshStatus = readTrackedRetry(
          statusResp.tracked_content_retry ?? item.tracked_content_retry,
          item.video_id,
        );
        const expectedJobId =
          freshStatus?.expected_job_id ??
          readTrackedRetry(item.tracked_content_retry, item.video_id)?.expected_job_id ??
          null;
        if (!expectedJobId || freshStatus?.retry_allowed === false) {
          if (freshStatus?.request?.state === "SUCCEEDED") {
            succeededCount += 1;
          }
          continue;
        }
        const cmdKey = `${item.video_id}:${expectedJobId}`;
        let cmd = batchCommandsRef.current.get(cmdKey);
        if (!cmd) {
          cmd = `batch:${Date.now()}:${Math.random().toString(36).slice(2)}`;
          batchCommandsRef.current.set(cmdKey, cmd);
        }
        await post<{ tracked_content_retry?: unknown }>(
          `/content/${encodeURIComponent(item.video_id)}/retry`,
          { expected_job_id: expectedJobId, command_id: cmd },
        );
        let settledState = "QUEUED";
        for (let poll = 0; poll < 120 && !batchStopRef.current; poll += 1) {
          await new Promise((resolve) => setTimeout(resolve, 400));
          if (batchStopRef.current) break;
          const polled = await api<{ tracked_content_retry?: unknown }>(
            `/content/${encodeURIComponent(item.video_id)}/retry`,
          );
          const parsed = readTrackedRetry(polled.tracked_content_retry, item.video_id);
          const reqState = parsed?.request?.state;
          if (reqState && !["QUEUED", "ACQUIRING", "FINALIZING"].includes(reqState)) {
            settledState = reqState;
            break;
          }
        }
        if (settledState === "SUCCEEDED") {
          succeededCount += 1;
        } else if (!batchStopRef.current) {
          failedCount += 1;
        }
        if (!batchStopRef.current) {
          setRevision((value) => value + 1);
        }
      } catch {
        failedCount += 1;
      }
    }
    if (!batchStopRef.current) {
      setRevision((value) => value + 1);
    }
    setBatchState((prev) =>
      prev
        ? {
            ...prev,
            running: false,
            done: batchStopRef.current ? prev.done : targets.length,
            succeeded: succeededCount,
            failed: failedCount,
            currentTitle: null,
          }
        : null,
    );
  };
  const hasMultiProviders = new Set(videos.map(v => v.provider ?? "YOUTUBE")).size > 1;
  const briefByVideoId = new Map<string, VideoAiBrief>();
  for (const item of videos) {
    const parsed = readVideoAiBrief(item.ai_brief, item.duration_seconds);
    if (parsed) briefByVideoId.set(item.video_id, parsed);
  }
  const hasAiBriefs = briefByVideoId.size > 0;
  const pendingAiSyncVideos = hasAiBriefs
    ? videos.filter(item => {
        if (item.work_kind) return false;
        const brief = briefByVideoId.get(item.video_id) ?? null;
        if (!brief) {
          return (item.provider ?? "YOUTUBE") === "YOUTUBE"
            ? Boolean(item.title?.trim()) &&
                ["READY", "ORGANIZED", "METADATA_READY"].includes(item.processing_status)
            : item.processing_status === "READY";
        }
        return (
          brief.source_basis === "METADATA_ONLY" &&
          (item.caption_timing_status === "AVAILABLE" ||
            ["READY", "ORGANIZED"].includes(item.processing_status))
        );
      })
    : [];
  const runPendingAiSync = async () => {
    if (aiSyncState?.running) return;
    setAiSyncState({ running: true, processedCount: 0, error: null });
    try {
      const res = await post<{ processed_count?: number }>("/workspace-ai/sync-pending", {
        limit: Math.max(10, pendingAiSyncVideos.length),
      });
      setAiSyncState({
        running: false,
        processedCount: typeof res.processed_count === "number" ? res.processed_count : pendingAiSyncVideos.length,
        error: null,
      });
      setRevision(value => value + 1);
    } catch {
      setAiSyncState({
        running: false,
        processedCount: 0,
        error:
          language === "zh-CN"
            ? "未能完成增量中文摘要同步，请检查本机 Ollama 或云端引擎连接。"
            : "Could not sync pending Chinese AI briefs.",
      });
    }
  };
  const toggleRowCuration = async (
    videoId: string,
    patchBody: { starred?: boolean; is_read?: boolean },
  ) => {
    if (curationBusyId !== null || batchCurationBusy) return;
    setCurationBusyId(videoId);
    try {
      await post(`/workspace-ai/videos/${encodeURIComponent(videoId)}/curation`, patchBody);
      setRevision((value) => value + 1);
    } catch {
      /* Preserve existing view on transient network failure */
    } finally {
      setCurationBusyId(null);
    }
  };
  const markVisibleUnreadAsRead = async (targetIds: string[]) => {
    if (!targetIds.length || batchCurationBusy || curationBusyId !== null) return;
    setBatchCurationBusy(true);
    try {
      await post("/workspace-ai/curation/batch", {
        video_ids: targetIds,
        is_read: true,
      });
      setLastBatchReadIds(targetIds);
      setRevision((value) => value + 1);
    } catch {
      /* Preserve existing view on transient network failure */
    } finally {
      setBatchCurationBusy(false);
    }
  };
  const undoLastBatchRead = async () => {
    if (!lastBatchReadIds.length || batchCurationBusy) return;
    const idsToRestore = [...lastBatchReadIds];
    setBatchCurationBusy(true);
    try {
      await post("/workspace-ai/curation/batch", {
        video_ids: idsToRestore,
        is_read: false,
      });
      setLastBatchReadIds([]);
      setRevision((value) => value + 1);
    } catch {
      /* Preserve undo banner if network call failed */
    } finally {
      setBatchCurationBusy(false);
    }
  };
  const trimmedSearch = searchQuery.trim().toLowerCase();
  const isAutoFoldedItem = (item: ContentItem) =>
    Boolean(
      briefByVideoId.get(item.video_id)?.is_short_noise ||
        item.work_kind === "DURABLE_CONTENT_IDENTITY",
    );
  const matchesContentSearch = (item: ContentItem, brief: VideoAiBrief | null) => {
    if (!trimmedSearch) return true;
    const ch = contentItemChannelKeyAndLabel(item, language);
    const haystack = `${item.title ?? ""} ${item.channel_name ?? ""} ${ch.label} ${item.video_id} ${brief?.headline_zh ?? ""} ${brief?.topic_cluster_zh ?? ""}`.toLowerCase();
    return haystack.includes(trimmedSearch);
  };
  const matchesContentBucket = (item: ContentItem, brief: VideoAiBrief | null) => {
    const itemProvider = item.provider ?? "YOUTUBE";
    if (bucketFilter === "UNREAD") {
      if (item.work_kind === "DURABLE_CONTENT_IDENTITY") return false;
      if (!brief || brief.is_short_noise || brief.is_read) return false;
    } else if (bucketFilter === "MUST_WATCH") {
      if (!brief || brief.is_short_noise || brief.recommendation_tier !== "MUST_WATCH") return false;
    } else if (bucketFilter === "STARRED") {
      if (!brief || !brief.starred) return false;
    } else if (bucketFilter === "TUTORIAL") {
      if (!brief || brief.content_bucket !== "TUTORIAL") return false;
    } else if (bucketFilter === "SHORTS") {
      const isShort = brief
        ? brief.is_short_noise || brief.content_bucket === "SHORTS_PROMO"
        : itemProvider === "YOUTUBE" && (item.duration_seconds ?? 9999) <= 95;
      if (!isShort) return false;
    }
    return true;
  };
  const allChannelKeys = new Set<string>();
  const allTopicClusters = new Set<string>();
  for (const item of videos) {
    if (item.work_kind === "DURABLE_CONTENT_IDENTITY") continue;
    allChannelKeys.add(contentItemChannelKeyAndLabel(item, language).key);
    const b = briefByVideoId.get(item.video_id);
    if (b && !b.is_short_noise && b.topic_cluster_zh.trim()) {
      allTopicClusters.add(b.topic_cluster_zh.trim());
    }
  }
  const channelCountMap = new Map<string, { label: string; count: number }>();
  for (const item of videos) {
    const itemProvider = item.provider ?? "YOUTUBE";
    if (providerFilter !== "ALL" && itemProvider !== providerFilter) continue;
    if (item.work_kind === "DURABLE_CONTENT_IDENTITY") continue;
    const b = briefByVideoId.get(item.video_id) ?? null;
    if (hasAiBriefs && bucketFilter !== "SHORTS") {
      if (!b || b.is_short_noise) continue;
      if (topicFilter !== "ALL" && b.topic_cluster_zh.trim() !== topicFilter) continue;
    } else if (!hasAiBriefs && itemProvider === "YOUTUBE" && (item.duration_seconds ?? 9999) <= 95) {
      continue;
    }
    if (!matchesContentBucket(item, b) || !matchesContentSearch(item, b)) continue;
    const ch = contentItemChannelKeyAndLabel(item, language);
    const prev = channelCountMap.get(ch.key);
    channelCountMap.set(ch.key, { label: ch.label, count: (prev?.count ?? 0) + 1 });
  }
  const channelOptionEntries = Array.from(channelCountMap.entries()).sort(
    (a, b) => b[1].count - a[1].count || a[1].label.localeCompare(b[1].label),
  );
  const topicCountMap = new Map<string, number>();
  for (const item of videos) {
    const itemProvider = item.provider ?? "YOUTUBE";
    if (providerFilter !== "ALL" && itemProvider !== providerFilter) continue;
    if (
      channelFilter !== "ALL" &&
      contentItemChannelKeyAndLabel(item, language).key !== channelFilter
    ) {
      continue;
    }
    if (item.work_kind === "DURABLE_CONTENT_IDENTITY") continue;
    const b = briefByVideoId.get(item.video_id) ?? null;
    if (!b || b.is_short_noise || !b.topic_cluster_zh.trim()) continue;
    if (!matchesContentBucket(item, b) || !matchesContentSearch(item, b)) continue;
    const cluster = b.topic_cluster_zh.trim();
    topicCountMap.set(cluster, (topicCountMap.get(cluster) ?? 0) + 1);
  }
  const topicClusterCounts = Array.from(topicCountMap.entries()).sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
  );
  const providerAndTopicVideos = videos.filter((item) => {
    const itemProvider = item.provider ?? "YOUTUBE";
    if (providerFilter !== "ALL" && itemProvider !== providerFilter) return false;
    if (
      channelFilter !== "ALL" &&
      contentItemChannelKeyAndLabel(item, language).key !== channelFilter
    ) {
      return false;
    }
    if (topicFilter !== "ALL") {
      const b = briefByVideoId.get(item.video_id);
      if (!b || b.topic_cluster_zh.trim() !== topicFilter) return false;
    }
    return matchesContentSearch(item, briefByVideoId.get(item.video_id) ?? null);
  });
  const bucketCounts: Record<
    "ALL" | "UNREAD" | "MUST_WATCH" | "STARRED" | "TUTORIAL" | "SHORTS",
    number
  > = {
    ALL: providerAndTopicVideos.filter((item) => !isAutoFoldedItem(item)).length,
    UNREAD: providerAndTopicVideos.filter((item) => {
      if (item.work_kind === "DURABLE_CONTENT_IDENTITY") return false;
      const b = briefByVideoId.get(item.video_id);
      return Boolean(b && !b.is_short_noise && !b.is_read);
    }).length,
    MUST_WATCH: providerAndTopicVideos.filter((item) => {
      const b = briefByVideoId.get(item.video_id);
      return Boolean(b && !b.is_short_noise && b.recommendation_tier === "MUST_WATCH");
    }).length,
    STARRED: providerAndTopicVideos.filter((item) =>
      Boolean(briefByVideoId.get(item.video_id)?.starred),
    ).length,
    TUTORIAL: providerAndTopicVideos.filter(
      (item) => briefByVideoId.get(item.video_id)?.content_bucket === "TUTORIAL",
    ).length,
    SHORTS: providerAndTopicVideos.filter((item) => {
      const b = briefByVideoId.get(item.video_id);
      const p = item.provider ?? "YOUTUBE";
      return b
        ? b.is_short_noise || b.content_bucket === "SHORTS_PROMO"
        : p === "YOUTUBE" && (item.duration_seconds ?? 9999) <= 95;
    }).length,
  };
  const filteredVideos = providerAndTopicVideos.filter((item) =>
    matchesContentBucket(item, briefByVideoId.get(item.video_id) ?? null),
  );
  const sortedFilteredVideos = [...filteredVideos].sort((a, b) => {
    if (contentSortMode === "score" && hasAiBriefs) {
      const scoreDiff =
        (briefByVideoId.get(b.video_id)?.score ?? -1) -
        (briefByVideoId.get(a.video_id)?.score ?? -1);
      if (scoreDiff !== 0) return scoreDiff;
    }
    const timeOrder = compareContentNewestFirst(a, b);
    if (timeOrder !== 0) return timeOrder;
    return (
      (briefByVideoId.get(b.video_id)?.score ?? -1) -
      (briefByVideoId.get(a.video_id)?.score ?? -1)
    );
  });
  const shouldFoldShorts = hasAiBriefs && bucketFilter === "ALL" && !trimmedSearch;
  const primaryVideos = shouldFoldShorts
    ? sortedFilteredVideos.filter((item) => !isAutoFoldedItem(item))
    : sortedFilteredVideos;
  const primaryIds = primaryVideos.map((v) => v.video_id);
  const unreadInViewIds = primaryVideos
    .filter((item) => {
      if (item.work_kind) return false;
      const b = briefByVideoId.get(item.video_id);
      return Boolean(b && !b.is_short_noise && !b.is_read);
    })
    .map((item) => item.video_id);
  const totalStarredCount = Array.from(briefByVideoId.values()).filter((b) =>
    Boolean(b.starred && !b.is_short_noise),
  ).length;
  const hasActiveContentFilter = Boolean(
    trimmedSearch ||
      channelFilter !== "ALL" ||
      topicFilter !== "ALL" ||
      providerFilter !== "ALL" ||
      bucketFilter !== "ALL",
  );
  const hasCustomResearchScope = Boolean(
    trimmedSearch ||
      channelFilter !== "ALL" ||
      topicFilter !== "ALL" ||
      providerFilter !== "ALL" ||
      (bucketFilter !== "ALL" && bucketFilter !== "STARRED" && bucketFilter !== "SHORTS"),
  );
  const filteredQuestionVideoIds = Array.from(
    new Set(
      primaryVideos
        .filter(
          (item) =>
            !item.work_kind && !briefByVideoId.get(item.video_id)?.is_short_noise,
        )
        .map((item) => item.video_id),
    ),
  ).slice(0, 12);
  const totalLongFormCount = videos.filter((item) => !isAutoFoldedItem(item)).length;
  const digestEntries = primaryVideos
    .flatMap((item) => {
      const b = briefByVideoId.get(item.video_id);
      return !item.work_kind && b ? [{ item, brief: b }] : [];
    })
    .slice(0, 20);
  const resetAllContentFilters = () => {
    setSearchQuery("");
    setBucketFilter("ALL");
    setChannelFilter("ALL");
    setTopicFilter("ALL");
    setProviderFilter("ALL");
  };
  const effectiveKbActiveId =
    kbActiveId && primaryIds.includes(kbActiveId) ? kbActiveId : (primaryIds[0] ?? null);
  kbContextRef.current = {
    isListActive: videos.length > 0,
    primaryIds,
    activeId: effectiveKbActiveId,
    briefMap: briefByVideoId,
    toggleRowCuration,
    onOpen,
  };
  const foldedShorts = shouldFoldShorts
    ? sortedFilteredVideos.filter(isAutoFoldedItem)
    : [];
  const foldedPlaceholderCount = foldedShorts.filter(
    item => item.work_kind === "DURABLE_CONTENT_IDENTITY",
  ).length;
  const foldedShortClipCount = foldedShorts.length - foldedPlaceholderCount;
  const renderContentRow = (item: ContentItem) => {
    const brief = briefByVideoId.get(item.video_id) ?? null;
    const isKbActive = effectiveKbActiveId === item.video_id;
    const isMetadataOnlyYoutube =
      brief?.source_basis === "METADATA_ONLY" &&
      (item.provider ?? "YOUTUBE") === "YOUTUBE" &&
      ["FAILED", "FAILED_FINAL", "FAILED_RETRYABLE", "RETRY_REQUIRED", "METADATA_READY"].includes(
        item.processing_status,
      );
    const rowStatus = isMetadataOnlyYoutube
      ? {
          value: "METADATA_READY",
          label: language === "zh-CN" ? "无原生字幕" : "No native captions",
        }
      : contentStatus(item.provider, item.processing_status);
    const hasShell = hasAiBriefs && Boolean(brief) && !item.work_kind;
    const rowButton = (
      <button
        type="button"
        className={`list-row content-media-row${brief?.is_read ? " is-read-row" : ""}${!hasShell && isKbActive ? " is-kb-active" : ""}`}
        key={hasShell ? undefined : item.video_id}
        data-kb-video-id={hasShell ? undefined : item.video_id}
        data-kb-active={!hasShell && isKbActive ? "true" : undefined}
        onClick={() => onOpen(item.video_id)}
      >
        <span className="content-media-lead">
          <span className={`provider-glyph provider-${(item.provider ?? "YOUTUBE").toLowerCase()}`} aria-hidden="true">
            <PhosphorIcon
              name={item.provider === "LOCAL" ? "file-text" : item.provider === "BILIBILI" ? "television" : "youtube-logo"}
              size={16}
            />
          </span>
          <span className="content-media-copy">
            <strong>{item.title ?? item.video_id}</strong>
            {brief ? (
              <span className="content-ai-headline">{brief.headline_zh}</span>
            ) : item.work_kind === "DURABLE_CONTENT_IDENTITY" ? (
              <span className="content-ai-headline">
                {item.processing_status === "NEEDS_ATTENTION"
                  ? language === "zh-CN"
                    ? "暂未获取到视频信息（受 YouTube 匿名访问验证限制）· 点击查看解决办法"
                    : "Video details blocked by YouTube anonymous check · Click for options"
                  : language === "zh-CN"
                    ? "正在连接来源获取视频标题、简介与字幕…"
                    : "Fetching video metadata and captions…"}
              </span>
            ) : null}
            <small>
              {[
                item.provider === "LOCAL"
                  ? t("Local")
                  : item.provider === "BILIBILI"
                    ? `${t("Bilibili")}${item.channel_name ? ` · ${item.channel_name}` : ""}`
                    : item.channel_name,
                humanDate(
                  item.provider === "BILIBILI"
                    ? item.published_at ?? item.last_updated
                    : item.imported_at ?? item.published_at ?? item.last_updated,
                ),
                item.duration_seconds != null ? formatHumanDuration(item.duration_seconds) : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </small>
          </span>
        </span>
        <span className="content-row-trailing">
          {brief?.source_basis === "METADATA_ONLY" && !brief.is_short_noise ? (
            <span className="ai-basis-pill is-compact">
              {language === "zh-CN" ? "简介速览" : "Metadata"}
            </span>
          ) : null}
          {brief ? <AiScoreBadge brief={brief} compact /> : null}
          <Status {...rowStatus} />
        </span>
      </button>
    );
    if (!hasShell || !brief) {
      return rowButton;
    }
    const zh = language === "zh-CN";
    const rowBusy = curationBusyId === item.video_id;
    return (
      <div
        className={`content-row-shell${brief.is_read ? " is-read-shell" : ""}${isKbActive ? " is-kb-active" : ""}`}
        key={item.video_id}
        data-kb-video-id={item.video_id}
        data-kb-active={isKbActive ? "true" : undefined}
        onMouseEnter={() => setKbActiveId(item.video_id)}
      >
        {rowButton}
        <div
          className="content-curation-inline"
          role="group"
          aria-label={zh ? "阅读与收藏" : "Reading controls"}
        >
          <button
            type="button"
            className={`curation-pill-btn${brief.starred ? " is-active" : ""}`}
            disabled={rowBusy}
            aria-pressed={Boolean(brief.starred)}
            aria-label={
              brief.starred
                ? zh
                  ? "已收藏 · 取消"
                  : "Starred · Remove"
                : zh
                  ? "收藏待看"
                  : "Star for later"
            }
            onClick={(event) => {
              pulseCelebration(event.currentTarget);
              void toggleRowCuration(item.video_id, { starred: !brief.starred });
            }}
          >
            <PhosphorIcon
              name="bookmark-simple"
              weight={brief.starred ? "fill" : "regular"}
              size={13}
            />
            <span>{brief.starred ? (zh ? "已收藏" : "Starred") : zh ? "收藏" : "Star"}</span>
          </button>
          <button
            type="button"
            className={`curation-pill-btn${brief.is_read ? " is-read-active" : ""}`}
            disabled={rowBusy}
            aria-pressed={Boolean(brief.is_read)}
            aria-label={
              brief.is_read
                ? zh
                  ? "已读 · 标未读"
                  : "Read · Mark unread"
                : zh
                  ? "标记已读"
                  : "Mark read"
            }
            onClick={() => void toggleRowCuration(item.video_id, { is_read: !brief.is_read })}
          >
            <PhosphorIcon
              name="check-circle"
              weight={brief.is_read ? "fill" : "regular"}
              size={13}
            />
            <span>{brief.is_read ? (zh ? "已读" : "Read") : zh ? "标已读" : "Read"}</span>
          </button>
        </div>
      </div>
    );
  };
  return videos.length
    ? (
      <div className="content-library-shell">
        {manualPendingVideos.length > 0 &&
        bucketFilter === "ALL" &&
        (providerFilter === "ALL" || providerFilter === "YOUTUBE") ? (
          <section
            className="caption-recovery-banner"
            role="region"
            aria-label={language === "zh-CN" ? "手动导入视频状态" : "Manual video imports"}
          >
            <div className="caption-recovery-copy">
              <strong>
                {language === "zh-CN"
                  ? `你有 ${manualPendingVideos.length} 条手动添加的视频尚未完成拉取`
                  : `${manualPendingVideos.length} manually added YouTube link(s) need attention or are loading`}
              </strong>
              <ul className="manual-pending-list" style={{ margin: "0.5rem 0 0", paddingLeft: "1.1rem", display: "grid", gap: "0.5rem" }}>
                {manualPendingVideos.map((pendingItem) => (
                  <li key={pendingItem.video_id} style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
                    <span>
                      <strong>{language === "zh-CN" ? `YouTube 视频 · ${pendingItem.video_id}` : `YouTube · ${pendingItem.video_id}`}</strong>{" "}
                      <span className="hint">
                        {pendingItem.processing_status === "NEEDS_ATTENTION"
                          ? language === "zh-CN"
                            ? "需要处理（受 YouTube 匿名访问/机器人验证限制）"
                            : "Needs attention (YouTube anonymous check blocked)"
                          : language === "zh-CN"
                            ? "正在获取视频信息…"
                            : "Fetching video details…"}
                      </span>
                    </span>
                    <span className="button-row" style={{ margin: 0 }}>
                      <button
                        type="button"
                        className="button button-secondary button-small"
                        onClick={() => onOpen(pendingItem.video_id)}
                      >
                        {language === "zh-CN" ? "查看处理方式" : "View options"}
                      </button>
                      {pendingItem.source_id ? (
                        <button
                          type="button"
                          className="button button-ghost button-small"
                          disabled={batchCurationBusy}
                          onClick={() => void removeManualPendingImport(pendingItem.source_id!)}
                        >
                          {language === "zh-CN" ? "移除记录" : "Remove"}
                        </button>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}
        {(retryableVideos.length > 0 || batchState !== null) && (
          <section className="caption-recovery-banner" role="region" aria-label={t("Recover failed captions")}>
            <div className="caption-recovery-copy">
              <strong>
                {batchState?.running
                  ? `${t("Recovering captions")} (${batchState.done + 1} / ${batchState.total})`
                  : retryableVideos.length > 0
                    ? `${t("Recover failed captions")} · ${retryableVideos.length}`
                    : t("Caption recovery finished")}
              </strong>
              <p>
                {batchState?.running
                  ? `${batchState.currentTitle ?? ""}`
                  : retryableVideos.length > 0
                    ? t("Earlier checks could not read native captions for these followed videos. Re-read captions now to prepare Summaries and verified source references.")
                    : `${t("Organized")}: ${batchState?.succeeded ?? 0}${batchState?.failed ? ` · ${t("Needs attention")}: ${batchState.failed}` : ""}`}
              </p>
            </div>
            <div className="button-row">
              {batchState?.running ? (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => {
                    batchStopRef.current = true;
                  }}
                >
                  {t("Stop")}
                </button>
              ) : retryableVideos.length > 0 ? (
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => void runBatchCaptionRecovery(retryableVideos)}
                >
                  {t("Retry all failed captions")} ({retryableVideos.length})
                </button>
              ) : (
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => setBatchState(null)}
                >
                  {t("Dismiss")}
                </button>
              )}
            </div>
          </section>
        )}
        {(pendingAiSyncVideos.length > 0 || aiSyncState !== null) && (
          <section
            className="ai-sync-pending-strip"
            role="region"
            aria-label={language === "zh-CN" ? "增量 AI 摘要同步" : "Incremental AI brief sync"}
          >
            <div className="caption-recovery-copy">
              <strong>
                {aiSyncState?.running
                  ? language === "zh-CN"
                    ? "正在增量生成中文摘要与评分…"
                    : "Syncing Chinese AI briefs…"
                  : pendingAiSyncVideos.length > 0
                    ? language === "zh-CN"
                      ? `发现 ${pendingAiSyncVideos.length} 条新内容待生成中文摘要与评分`
                      : `${pendingAiSyncVideos.length} new items awaiting Chinese AI brief`
                    : language === "zh-CN"
                      ? `已完成 ${aiSyncState?.processedCount ?? 0} 条内容的中文摘要同步`
                      : `Synced ${aiSyncState?.processedCount ?? 0} Chinese AI briefs`}
              </strong>
              {aiSyncState?.error ? (
                <p className="form-error" role="alert">
                  {aiSyncState.error}
                </p>
              ) : (
                <p>
                  {language === "zh-CN"
                    ? "有字幕视频提炼完整洞察，暂未开放字幕视频将诚实生成基于官方简介的中文速览。"
                    : "Transcript-backed items get full grounded insights; captionless items receive an honest metadata preview."}
                </p>
              )}
            </div>
            <div className="button-row">
              {pendingAiSyncVideos.length > 0 ? (
                <button
                  type="button"
                  className="button button-primary button-small"
                  disabled={aiSyncState?.running === true}
                  onClick={() => void runPendingAiSync()}
                >
                  <PhosphorIcon name="sparkle" size={13} />
                  {aiSyncState?.running
                    ? language === "zh-CN"
                      ? "同步中…"
                      : "Syncing…"
                    : language === "zh-CN"
                      ? `一键同步中文摘要 (${pendingAiSyncVideos.length})`
                      : `Sync AI briefs (${pendingAiSyncVideos.length})`}
                </button>
              ) : (
                <button
                  type="button"
                  className="button button-ghost button-small"
                  onClick={() => setAiSyncState(null)}
                >
                  {t("Dismiss")}
                </button>
              )}
            </div>
          </section>
        )}
        <div className="library-filter-bar">
          <div className="search-field-wrap">
            <PhosphorIcon name="magnifying-glass" size={15} className="search-field-icon" />
            <input
              ref={searchInputRef}
              type="search"
              aria-label={t("Search Content library")}
              placeholder={t("Filter by title or channel…")}
              value={searchQuery}
              onChange={event => setSearchQuery(event.target.value)}
            />
          </div>
          {hasAiBriefs && (
            <div
              className="segmented library-bucket-chips"
              role="group"
              aria-label={language === "zh-CN" ? "内容价值分流" : "Value filter"}
            >
              {(
                [
                  ["ALL", language === "zh-CN" ? "全部" : "All"],
                  ["UNREAD", language === "zh-CN" ? "未读干货" : "Unread"],
                  ["MUST_WATCH", language === "zh-CN" ? "必看长视频" : "Must-watch"],
                  ["STARRED", language === "zh-CN" ? "已收藏" : "Starred"],
                  ["TUTORIAL", language === "zh-CN" ? "实操教程" : "Tutorials"],
                  ["SHORTS", language === "zh-CN" ? "Shorts 短片" : "Shorts"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  aria-label={label}
                  aria-pressed={bucketFilter === key}
                  className={bucketFilter === key ? "active" : ""}
                  onClick={() => setBucketFilter(key)}
                >
                  <span>{label}</span>
                  <span className="bucket-count-badge tabular-nums" aria-hidden="true">
                    {bucketCounts[key]}
                  </span>
                </button>
              ))}
            </div>
          )}
          {hasAiBriefs && (allChannelKeys.size > 1 || channelFilter !== "ALL") && (
            <select
              className="content-topic-select tabular-nums"
              aria-label={language === "zh-CN" ? "按频道筛选" : "Filter by channel"}
              value={channelFilter}
              onChange={(event) => setChannelFilter(event.target.value)}
            >
              <option value="ALL">
                {language === "zh-CN" ? "全部频道" : "All channels"}
              </option>
              {channelFilter !== "ALL" && !channelCountMap.has(channelFilter) ? (
                <option value={channelFilter}>
                  {channelFilter === "LOCAL" && language === "zh-CN" ? "本地实战课" : channelFilter} (0)
                </option>
              ) : null}
              {channelOptionEntries.map(([chKey, info]) => (
                <option key={chKey} value={chKey}>
                  {info.label} ({info.count})
                </option>
              ))}
            </select>
          )}
          {hasAiBriefs && (allTopicClusters.size > 1 || topicFilter !== "ALL") && (
            <select
              className="content-topic-select tabular-nums"
              aria-label={language === "zh-CN" ? "按专题筛选内容" : "Filter Content by topic"}
              value={topicFilter}
              onChange={(event) => setTopicFilter(event.target.value)}
            >
              <option value="ALL">
                {language === "zh-CN" ? "全部专题" : "All topics"}
              </option>
              {topicFilter !== "ALL" && !topicCountMap.has(topicFilter) ? (
                <option value={topicFilter}>
                  {topicFilter} (0)
                </option>
              ) : null}
              {topicClusterCounts.map(([clusterName, count]) => (
                <option key={clusterName} value={clusterName}>
                  {clusterName} ({count})
                </option>
              ))}
            </select>
          )}
          {hasMultiProviders && (
            <div className="segmented library-provider-chips" role="group" aria-label={t("All sources")}>
              {([
                ["ALL", t("All sources")],
                ["YOUTUBE", "YouTube"],
                ["BILIBILI", t("Bilibili")],
                ["LOCAL", t("Local")],
              ] as const)
                .filter(([key]) => key === "ALL" || videos.some(v => (v.provider ?? "YOUTUBE") === key))
                .map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={providerFilter === key}
                    className={providerFilter === key ? "active" : ""}
                    onClick={() => setProviderFilter(key)}
                  >
                    {label}
                  </button>
                ))}
            </div>
          )}
          {hasAiBriefs && (
            <div
              className="segmented library-sort-chips"
              role="group"
              aria-label={language === "zh-CN" ? "排序方式" : "Sort order"}
            >
              {(
                [
                  ["newest", language === "zh-CN" ? "最新优先" : "Newest first"],
                  ["score", language === "zh-CN" ? "高分优先" : "Top score"],
                ] as const
              ).map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={contentSortMode === mode}
                  className={contentSortMode === mode ? "active" : ""}
                  onClick={() => setContentSortMode(mode)}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          {hasAiBriefs && primaryVideos.length > 0 && (
            <span className="kb-shortcut-hint" aria-hidden="true">
              {language === "zh-CN"
                ? "快捷键：/ 搜索 · J/K 选行 · Enter 阅读 · S 收藏 · E 已读"
                : "Keys: / search · J/K move · Enter open · S star · E read"}
            </span>
          )}
          {hasAiBriefs &&
          ((onAskFilteredResearch &&
            hasCustomResearchScope &&
            filteredQuestionVideoIds.length > 0) ||
            (onAskStarredResearch && totalStarredCount > 0) ||
            (bucketFilter !== "SHORTS" && unreadInViewIds.length > 0) ||
            (hasActiveContentFilter && filteredVideos.length > 0)) ? (
            <div className="library-batch-actions tabular-nums">
              {onAskFilteredResearch &&
              hasCustomResearchScope &&
              filteredQuestionVideoIds.length > 0 ? (
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => onAskFilteredResearch(filteredQuestionVideoIds)}
                >
                  <PhosphorIcon name="sparkle" size={13} />
                  {language === "zh-CN"
                    ? `围绕当前筛选视频追问 (${filteredQuestionVideoIds.length})`
                    : `Ask Q&A on filtered (${filteredQuestionVideoIds.length})`}
                </button>
              ) : null}
              {onAskStarredResearch && totalStarredCount > 0 ? (
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={onAskStarredResearch}
                >
                  <PhosphorIcon name="sparkle" size={13} />
                  {language === "zh-CN"
                    ? `针对已收藏提问 (${totalStarredCount})`
                    : `Ask Q&A on starred (${totalStarredCount})`}
                </button>
              ) : null}
              {bucketFilter !== "SHORTS" && unreadInViewIds.length > 0 ? (
                <button
                  type="button"
                  className="button button-ghost button-small"
                  disabled={batchCurationBusy}
                  onClick={() => void markVisibleUnreadAsRead(unreadInViewIds)}
                >
                  <PhosphorIcon name="check-circle" size={13} />
                  {language === "zh-CN"
                    ? `当前列表标已读 (${unreadInViewIds.length})`
                    : `Mark view read (${unreadInViewIds.length})`}
                </button>
              ) : null}
              {hasActiveContentFilter && filteredVideos.length > 0 ? (
                <button
                  type="button"
                  className="button button-ghost button-small"
                  onClick={resetAllContentFilters}
                >
                  {language === "zh-CN" ? "重置筛选" : "Reset filters"}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
        {hasAiBriefs && hasActiveContentFilter && primaryVideos.length > 0 ? (
          <div
            className="content-active-filter-bar tabular-nums"
            role="status"
            aria-live="polite"
          >
            <span>
              {bucketFilter === "SHORTS"
                ? language === "zh-CN"
                  ? `当前筛选命中 ${primaryVideos.length} 条 Shorts 短片`
                  : `Showing ${primaryVideos.length} Shorts clips`
                : language === "zh-CN"
                  ? `当前筛选命中 ${primaryVideos.length} / ${totalLongFormCount} 篇长视频`
                  : `Showing ${primaryVideos.length} of ${totalLongFormCount} long-form videos`}
            </span>
            {digestEntries.length > 0 ? (
              <div className="intel-filter-bar-actions">
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={(event) => {
                    pulseCelebration(event.currentTarget);
                    void navigator.clipboard?.writeText(
                      formatPlainTextContentDigest(digestEntries, language),
                    );
                    setCopiedContentDigest(true);
                    setTimeout(() => setCopiedContentDigest(false), 2200);
                  }}
                >
                  <PhosphorIcon name="quotes" size={13} />
                  {copiedContentDigest
                    ? language === "zh-CN"
                      ? "已复制摘要合集"
                      : "Copied summary digest"
                    : language === "zh-CN"
                      ? `复制当前筛选摘要合集 (${digestEntries.length})`
                      : `Copy filtered summaries (${digestEntries.length})`}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        {lastBatchReadIds.length > 0 ? (
          <div className="curation-undo-strip tabular-nums" role="status" aria-live="polite">
            <span>
              {language === "zh-CN"
                ? `已将 ${lastBatchReadIds.length} 篇内容标记为已读`
                : `Marked ${lastBatchReadIds.length} items as read`}
            </span>
            <div className="button-row">
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={batchCurationBusy}
                onClick={() => void undoLastBatchRead()}
              >
                {language === "zh-CN" ? "撤销" : "Undo"}
              </button>
              <button
                type="button"
                className="button button-ghost button-small"
                disabled={batchCurationBusy}
                onClick={() => setLastBatchReadIds([])}
              >
                {t("Dismiss")}
              </button>
            </div>
          </div>
        ) : null}
        {filteredVideos.length ? (
          <>
            {primaryVideos.length > 0 ? (
              <div className="compact-list content-media-list">
                {primaryVideos.map(renderContentRow)}
              </div>
            ) : null}
            {foldedShorts.length > 0 ? (
              <details className="shorts-fold-drawer">
                <summary className="tabular-nums">
                  <PhosphorIcon name="funnel" size={14} />
                  <span>
                    {language === "zh-CN"
                      ? foldedPlaceholderCount > 0 && foldedShortClipCount > 0
                        ? `已自动折叠 ${foldedShortClipCount} 条 Shorts 宣传短片与 ${foldedPlaceholderCount} 条未开播/占位链接（点击展开查看）`
                        : foldedPlaceholderCount > 0
                          ? `已自动折叠 ${foldedPlaceholderCount} 条未开播/原始链接占位项（点击展开查看）`
                          : `已自动折叠 ${foldedShorts.length} 条 Shorts 宣传短片（点击展开查看）`
                      : foldedPlaceholderCount > 0 && foldedShortClipCount > 0
                        ? `${foldedShortClipCount} Shorts clips and ${foldedPlaceholderCount} placeholder links auto-folded (click to expand)`
                        : foldedPlaceholderCount > 0
                          ? `${foldedPlaceholderCount} placeholder links auto-folded (click to expand)`
                          : `${foldedShorts.length} Shorts promo clips auto-folded (click to expand)`}
                  </span>
                </summary>
                <div className="compact-list content-media-list shorts-folded-list">
                  {foldedShorts.map(renderContentRow)}
                </div>
              </details>
            ) : null}
          </>
        ) : (
          <Empty>
            <p>{t("No Content matches your current search or filter.")}</p>
            <button
              type="button"
              className="button button-secondary"
              onClick={() => {
                setSearchQuery("");
                setProviderFilter("ALL");
                setBucketFilter("ALL");
                setTopicFilter("ALL");
                setChannelFilter("ALL");
              }}
            >
              {t("Clear filter")}
            </button>
          </Empty>
        )}
      </div>
    )
    : (
      <Empty>
        <p>{t("No Content yet. Add a video link, follow a YouTube channel, or import a local file.")}</p>
        <button type="button" className="button button-primary" onClick={onAdd}>{t("Add content")}</button>
      </Empty>
    );
}
type CloudReview = {
  profile_id: string; execution_id: string; review_hash: string; provider: string; model: string; source_id: string;
  expires_at: string; output_language: string; cost_status: string; readiness: unknown;
  evidence: { evidence_id: string; excerpt: string }[];
  context: { personalization: string[]; focus: string[]; ignore: string[]; style: string | null };
  outputLimit: number | null; raw: Record<string, unknown>;
};
function readCloudReview(value: unknown, id: string): CloudReview | null {
  const strings = (items: unknown): items is string[] => Array.isArray(items) && items.length <= 100 && items.every(item => typeof item === "string");
  if (!localObject(value) || value.video_id !== id
    || ![value.execution_id, value.provider, value.model, value.source_id].every(localText)
    || typeof value.review_hash !== "string" || !/^[a-f0-9]{64}$/.test(value.review_hash)
    || typeof value.verified_input_hash !== "string" || !/^[a-f0-9]{64}$/.test(value.verified_input_hash)
    || typeof value.expires_at !== "string" || !Number.isFinite(Date.parse(value.expires_at))
    || !["en", "zh-CN"].includes(String(value.output_language)) || !localText(value.cost_status)
    || !strings(value.evidence_ids) || !value.evidence_ids.length || value.evidence_ids.length > 20
    || !localObject(value.outgoing_data) || !(value.outgoing_request === null || localObject(value.outgoing_request))) return null;
  const data = value.outgoing_data, request = value.outgoing_request;
  const evidence = data.evidence, evidenceIds = value.evidence_ids;
  const outputLimit = request === null ? null : request.max_tokens ?? request.max_output_tokens ?? request.max_completion_tokens;
  if (!Array.isArray(evidence) || evidence.length !== value.evidence_ids.length
    || !evidence.every(item => localObject(item) && localText(item.evidence_id) && typeof item.excerpt === "string")
    || evidence.some((item, index) => item.evidence_id !== evidenceIds[index])
    || data.video_id !== id || data.output_language !== value.output_language
    || !strings(data.personalization) || !strings(data.source_focus_rules) || !strings(data.source_ignore_rules)
    || !(data.distillation_style === null || typeof data.distillation_style === "string")
    || (request !== null && (request.model !== value.model || typeof outputLimit !== "number" || !Number.isSafeInteger(outputLimit) || outputLimit <= 0))) return null;
  return { profile_id: typeof value.profile_id === "string" ? value.profile_id : "legacy", execution_id: String(value.execution_id), review_hash: value.review_hash, provider: String(value.provider),
    model: String(value.model), source_id: String(value.source_id), expires_at: value.expires_at,
    output_language: String(value.output_language), cost_status: value.cost_status, readiness: value.readiness,
    evidence: evidence.map(item => ({ evidence_id: String(item.evidence_id), excerpt: String(item.excerpt) })),
    context: { personalization: data.personalization, focus: data.source_focus_rules, ignore: data.source_ignore_rules, style: data.distillation_style },
    outputLimit: typeof outputLimit === "number" ? outputLimit : null, raw: { outgoing_data: data, outgoing_request: request, spending: value.spending } };
}
const cloudBlockerCopy: Record<string, string> = {
  CREDENTIAL_REQUIRED: "Configure a cloud credential in Settings before confirming.",
  MODEL_UNQUALIFIED: "This model has not qualified for this Intelligence task.",
  MODEL_UNAVAILABLE: "The selected cloud model is currently unavailable.",
  CLOUD_SPENDING_POLICY_REQUIRED: "A backend spending policy is required before cloud execution.",
  CLOUD_EXECUTION_DISABLED: "Cloud execution is disabled in this environment. Reviewing or configuring a model does not enable paid requests.",
  CLOUD_PER_REQUEST_CAP_EXCEEDED: "This request exceeds the per-request reservation cap. Review spending settings before proceeding.",
  CLOUD_BUDGET_EXHAUSTED: "The cumulative reservation budget is exhausted. Held and unknown charges remain counted.",
  CLOUD_REQUEST_COUNT_EXHAUSTED: "The cumulative request limit is reached. Changing a limit does not erase earlier reservations.",
  CLOUD_PRICE_ACCEPTANCE_REQUIRED: "Review and accept the current profile and price reference in spending settings.",
  CLOUD_POLICY_CHANGED_REVIEW_REQUIRED: "Spending settings changed after this review. Prepare a new review before confirming.",
  CLOUD_EXECUTION_REPLAY_BLOCKED: "This exact request was already reserved or attempted. Check its history; it will not be sent again.",
  CLOUD_PRECLAIM_ABORTED: "This request stopped safely before execution. No model was called; its original record is kept.",
  CLOUD_JOURNAL_HISTORY_MISSING: "Retained spending history is missing. Cloud execution is blocked; restore its machine-local history before continuing.",
  CLOUD_JOURNAL_UNAVAILABLE: "Spending history could not be verified. Cloud execution remains blocked.",
  CLOUD_JOURNAL_CORRUPT: "Spending history could not be verified. Cloud execution remains blocked.",
  CLOUD_JOURNAL_UNSAFE: "Spending history could not be verified. Cloud execution remains blocked.",
  CLOUD_JOURNAL_FULL: "The retained spending journal is full. Cloud execution is blocked until its history is safely maintained.",
  INPUT_NOT_SUPPORTED: "The selected model does not support this input or output language.",
  EXECUTION_ALREADY_EXISTS: "An execution already exists for this request. Check its current state before continuing.",
};
function cloudProfileOptionLabel(
  profile: { profile_id: string; provider: string; model: string; qualified: boolean },
  t: (text: string) => string,
) {
  const detail = profile.profile_id === "moonshot-k31-system-synthesis-v2-attribution-20261105"
    ? ` · ${t("Explicit speaker attribution policy")}`
    : profile.profile_id === "moonshot-k31-system-synthesis-v5-judgment-stream-20261112"
      ? ` · ${t("Judgment beyond the complete Summary")}`
      : profile.profile_id === "moonshot-k31-system-synthesis-v4-readable-summary-20261107"
        ? ` · ${t("Complete Summary comparison")}`
        : profile.profile_id === "moonshot-k31-system-synthesis-v3-source-level-20261106"
          ? ` · ${t("Source-level attribution")}`
          : "";
  return `${profile.provider} · ${profile.model}${detail}${profile.qualified ? "" : ` · ${t("Not qualified")}`}`;
}

function CloudIntelligencePreview({ id, manual, executionKey, onSettled }: { id: string; manual: boolean; executionKey: string; onSettled: () => void }) {
  const { t } = useUiLanguage();
  const profiles = useRemote<{ profiles: { profile_id: string; provider: string; model: string; adapter_available: boolean; qualified: boolean }[] }>("/cloud-intelligence/profiles");
  const [selectedProfile, setSelectedProfile] = useState("legacy");
  const userChoseProfile = useRef(false);
  const [open, setOpen] = useState(false), [review, setReview] = useState<CloudReview | null>(null);
  const [busy, setBusy] = useState(false), [confirming, setConfirming] = useState(false), [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null), [clock, setClock] = useState(Date.now);
  const requestGeneration = useRef(0), busyRef = useRef(false), manualCommand = useRef(commandId());
  const previousExecution = useRef(executionKey);
  useEffect(() => {
    const list = profiles.data?.profiles;
    if (userChoseProfile.current || !Array.isArray(list) || !list.length) return;
    const preferred = list.find(item => item.qualified) ?? list[0];
    if (preferred && preferred.profile_id !== selectedProfile) {
      setSelectedProfile(preferred.profile_id);
    }
  }, [profiles.data]);
  useEffect(() => {
    if (!confirming) {
      setElapsedSeconds(0);
      return;
    }
    const timer = window.setInterval(() => {
      setElapsedSeconds(value => value + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [confirming]);
  const clear = () => {
    requestGeneration.current += 1; busyRef.current = false;
    setOpen(false); setReview(null); setBusy(false); setConfirming(false); setError(null); setMessage(null);
  };
  useEffect(() => {
    if (previousExecution.current === executionKey) return;
    previousExecution.current = executionKey;
    clear(); manualCommand.current = commandId();
  }, [executionKey]);
  useEffect(() => {
    const leave = (event: HashChangeEvent) => {
      if (event.newURL && new URL(event.newURL).hash !== location.hash) return;
      clear();
    };
    window.addEventListener("hashchange", leave);
    return () => { requestGeneration.current += 1; window.removeEventListener("hashchange", leave); };
  }, [id]);
  useEffect(() => {
    if (!review) return;
    const timer = setTimeout(() => setClock(Date.now()), Math.min(2_147_483_647, Math.max(0, Date.parse(review.expires_at) - Date.now())));
    return () => clearTimeout(timer);
  }, [review]);
  const readiness = review?.readiness;
  const readinessValid = localObject(readiness) && typeof readiness.can_confirm === "boolean"
    && Array.isArray(readiness.blockers) && readiness.blockers.every(item => typeof item === "string")
    && localText(readiness.budget_state);
  const blockers: string[] = readinessValid ? readiness.blockers as string[] : [];
  const expired = review !== null && Date.parse(review.expires_at) <= clock;
  const canConfirm = Boolean(review && readinessValid && readiness.can_confirm === true && blockers.length === 0 && review.outputLimit !== null && !expired && !busy);
  const outgoingRequest = review?.raw.outgoing_request;
  const spending = review?.raw.spending;
  const reserveEstimate = localObject(spending) && typeof spending.reserve_microunits === "number"
    && Number.isSafeInteger(spending.reserve_microunits) && spending.reserve_microunits > 0 ? spending.reserve_microunits : null;
  const includesSummary = ["moonshot-k31-system-synthesis-v1-20261029", "moonshot-k31-system-synthesis-v2-attribution-20261105",
    "moonshot-k31-system-synthesis-v3-source-level-20261106", "moonshot-k31-system-synthesis-v4-readable-summary-20261107",
    "moonshot-k31-system-synthesis-v5-judgment-stream-20261112"].includes(review?.profile_id ?? "")
    && localObject(outgoingRequest) && Array.isArray(outgoingRequest.messages)
    && outgoingRequest.messages.some(item => localObject(item) && typeof item.content === "string"
      && item.content.startsWith("UNTRUSTED_CURRENT_SUMMARY_BASELINE="));
  const prepare = async () => {
    if (busyRef.current) return;
    const generation = ++requestGeneration.current;
    busyRef.current = true; setBusy(true); setReview(null); setMessage(null); setError(null);
    try {
      const response = await post<{ review?: unknown }>(`/videos/${id}/cloud-intelligence/review`, manual ? { command_id: manualCommand.current, ...(selectedProfile === "legacy" ? {} : { profile_id: selectedProfile }) } : {});
      if (generation !== requestGeneration.current) return;
      const current = readCloudReview(response.review, id);
      if (!current || current.profile_id !== selectedProfile) throw new Error("INVALID_REVIEW");
      setClock(Date.now()); setReview(current);
    } catch {
      if (generation === requestGeneration.current) setError("The cloud review could not be verified. Keep reading this Content, then prepare a new review or check model settings.");
    } finally {
      if (generation === requestGeneration.current) { busyRef.current = false; setBusy(false); }
    }
  };
  const confirm = async () => {
    if (busyRef.current || !canConfirm || !review) return;
    if (Date.parse(review.expires_at) <= Date.now()) { setClock(Date.now()); return; }
    const generation = ++requestGeneration.current;
    busyRef.current = true; setBusy(true); setConfirming(true); setElapsedSeconds(0); setError(null); setMessage(null);
    const current = review;
    setReview(null); // A dispatched ticket is never reused, even after a lost response.
    try {
      await post(`/videos/${id}/cloud-intelligence/confirm`, { execution_id: current.execution_id, review_hash: current.review_hash, authorize: true, ...(current.profile_id === "legacy" ? {} : { profile_id: current.profile_id }) });
      if (generation !== requestGeneration.current) return;
      setMessage("Cloud confirmation returned. Check this Content's current Intelligence status."); onSettled();
    } catch (error) {
      if (generation === requestGeneration.current) {
        if (error instanceof ApiRequestError && error.code === "CLOUD_PRECLAIM_ABORTED") manualCommand.current = commandId();
        setError(error instanceof ApiRequestError && cloudBlockerCopy[error.code] ? cloudBlockerCopy[error.code]
          : "Cloud confirmation was refused or could not be verified. Check the current task and model settings before preparing another review. Nothing is retried automatically.");
        onSettled();
      }
    } finally {
      if (generation === requestGeneration.current) { busyRef.current = false; setBusy(false); setConfirming(false); }
    }
  };
  const profileList = manual && profiles.data && Array.isArray(profiles.data.profiles) ? profiles.data.profiles : [];
  const qualifiedProfiles = profileList.filter(item => item.qualified);
  const archivedProfiles = profileList.filter(item => !item.qualified);
  const activeProfile = profileList.find(item => item.profile_id === selectedProfile);
  const elapsedFormatted = `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, "0")}`;

  return <div className="cloud-preview-block">
    <button type="button" className="button button-secondary" onClick={() => open ? clear() : setOpen(true)}>{t("Review cloud Intelligence")}</button>
    {open && <section className="semantic-state state-neutral cloud-disclosure-panel" aria-label={t("Cloud Intelligence disclosure")}>
      <h3>{t("Cloud Intelligence disclosure")}</h3>
      {activeProfile?.qualified && (
        <p className="verified-route-pill">
          <VerifiedSealIcon />
          <span>{t("Recommended verified route selected")}: {activeProfile.provider} · {activeProfile.model}</span>
        </p>
      )}
      {profileList.length > 0 && <label className="field">{t("Cloud model profile")}
        <select disabled={busy} value={selectedProfile} onChange={event => { userChoseProfile.current = true; setSelectedProfile(event.target.value); setReview(null); manualCommand.current = commandId(); }}>
          {qualifiedProfiles.length > 0 && archivedProfiles.length > 0 ? <>
            <optgroup label={t("Recommended · quality verified")}>
              {qualifiedProfiles.map(profile => <option key={profile.profile_id} value={profile.profile_id}>{cloudProfileOptionLabel(profile, t)}</option>)}
            </optgroup>
            <optgroup label={t("Archived history · not qualified")}>
              {archivedProfiles.map(profile => <option key={profile.profile_id} value={profile.profile_id}>{cloudProfileOptionLabel(profile, t)}</option>)}
            </optgroup>
          </> : profileList.map(profile => <option key={profile.profile_id} value={profile.profile_id}>{cloudProfileOptionLabel(profile, t)}</option>)}
        </select>
      </label>}
      {includesSummary && <p>{t("The reviewed request includes the complete stored Summary as comparison context. Review all outgoing data before authorization.")}</p>}
      <p>{t("Only bounded, verified Evidence excerpts and the task context needed for this Intelligence judgment would leave this device. The full database, unrelated Content, Followings, library, and credentials are excluded. Your original Evidence remains authoritative here.")}</p>
      <p>{t("Preparing a review does not create a task. Confirming authorizes exactly one request for the reviewed Evidence and task context.")}</p>
      <div className="button-row"><button type="button" className="button button-secondary" disabled={busy} onClick={() => void prepare()}>{t(busy ? "Working…" : "Prepare one request for review")}</button>
        <button type="button" className="button button-ghost" onClick={clear}>{t("Dismiss cloud review")}</button>
        <a className="button button-ghost" href={`#Settings/models/moonshot?return=${encodeURIComponent(location.hash)}`}>{t("Open model settings")}</a>
        <a className={`button ${blockers.some(code => code.startsWith("CLOUD_")) ? "button-primary" : "button-secondary"}`} href={`#Settings/models/moonshot?return=${encodeURIComponent(location.hash)}&panel=spending`}>{t("Configure spending limits")}</a></div>
      {manual && review?.profile_id === "legacy" && blockers.includes("CLOUD_SPENDING_POLICY_REQUIRED") && <p>{t("The finite spending settings cover kimi-k3.1-pro. For that policy, choose kimi-k3.1-pro in the cloud model profile list and prepare a new review.")}</p>}
      {review && <div className="cloud-review-ticket">
        <p>{t("Provider/model")}: {review.provider} · {review.model}</p>
        <p className="tabular-nums">{t("Source")}: {review.source_id} · {t("Output language")}: {review.output_language} · {t("Maximum output tokens")}: {review.outputLimit ?? t("Unavailable")}</p>
        <p>{t("Cost status")}: {t(review.cost_status === "UNKNOWN" ? "Unknown" : review.cost_status)}. {t("An unknown cost or an unverified budget is not a promise of free usage. The backend rechecks budget before execution.")}</p>
        {reserveEstimate !== null && <p className="tabular-nums">{t("Estimated reservation for this request")}: CNY {formatMicroCny(reserveEstimate)} · {t("Unknown charges stay held after restart or Restore.")}</p>}
        <h4>{t("Evidence that would be sent")}</h4>
        {review.evidence.map(item => <blockquote key={item.evidence_id}><p>{item.excerpt}</p><a href={`#Content/${encodeURIComponent(id)}/Evidence/${encodeURIComponent(item.evidence_id)}`}>{t("View original Evidence")}</a></blockquote>)}
        <h4>{t("Task context that would be sent")}</h4>
        <p>{t("Personalization")}: {review.context.personalization.join(" · ") || t("None")}</p>
        <p>{t("Focus")}: {review.context.focus.join(" · ") || t("None")}</p>
        <p>{t("Ignore")}: {review.context.ignore.join(" · ") || t("None")}</p>
        <p>{t("Insight style")}: {review.context.style ? t(STYLES.find(style => style[0] === review.context.style)?.[1] ?? review.context.style) : t("None")}</p>
        {!readinessValid && <p role="status">{t("Cloud readiness could not be verified. Prepare a new review or check model settings.")}</p>}
        {readinessValid && <>{!blockers.includes(String(readiness.budget_state)) && <p>{t(readiness.budget_state === "BUDGET_UNVERIFIED" ? "Budget has not been verified. Confirmation requires the backend's current budget check." : readiness.budget_state === "CLOUD_SPENDING_POLICY_REQUIRED" ? cloudBlockerCopy.CLOUD_SPENDING_POLICY_REQUIRED : "Budget policy will be rechecked before execution.")}</p>}
          {blockers.map((code, index) => <p key={`${code}:${index}`}>{t(cloudBlockerCopy[code] ?? "Cloud confirmation is unavailable. Prepare a new review or check model settings.")}</p>)}
          {!readiness.can_confirm && !blockers.length && <p>{t("Cloud confirmation is unavailable. Prepare a new review or check model settings.")}</p>}</>}
        {expired && <p role="status">{t("This review expired. Prepare a new review before confirming.")}</p>}
        <details className="provenance"><summary>{t("Exact outgoing request details")}</summary><pre className="transcript-copy">{JSON.stringify(review.raw, null, 2)}</pre></details>
        <div className="button-row">
          <button type="button" className="button button-primary" disabled={!canConfirm} onClick={() => void confirm()}>{t("Authorize this one cloud execution")}</button>
        </div>
      </div>}
      {confirming && (
        <div className="distill-live-card" data-testid="distill-live-progress">
          <div className="distill-live-head">
            <span className="distill-live-title"><DistillOrbitIcon /><strong>{t("Kimi deep judgment in progress")}</strong></span>
            <span className="distill-live-timer tabular-nums">{elapsedFormatted}</span>
          </div>
          <p className="hint">{t("Usually takes 1–2.5 minutes for full-transcript cross-paragraph judgment.")}</p>
          <ol className="distill-stages">
            <li className={elapsedSeconds < 5 ? "is-active" : "is-done"}>{t("Verifying budget & locking Evidence excerpts")}</li>
            <li className={elapsedSeconds >= 5 && elapsedSeconds < 75 ? "is-active" : elapsedSeconds >= 75 ? "is-done" : ""}>{t("Cross-checking complete Summary & reasoning")}</li>
            <li className={elapsedSeconds >= 75 ? "is-active" : ""}>{t("Streaming & verifying source citations")}</li>
          </ol>
        </div>
      )}
      {busy && <p role="status">{t("Waiting for the local service. Nothing is retried automatically.")}</p>}
      {error && <p role="alert" className="form-error">{t(error)}</p>}{message && <p role="status" className="status-banner">{t(message)}</p>}
    </section>}
  </div>;
}

const READER_SECTION_IDS = [
  "section-intelligence",
  "section-summary",
  "section-evidence",
  "section-transcript",
  "section-history",
] as const;

const SETTINGS_SECTION_IDS = [
  "settings-language",
  "settings-interests",
  "settings-models",
  "settings-backup",
] as const;

function useActiveSection(sectionIds: readonly string[], resetKey?: string): [string, (sectionId: string) => void] {
  const [activeId, setActiveId] = useState<string>(() => sectionIds[0] ?? "");
  useEffect(() => {
    setActiveId(sectionIds[0] ?? "");
  }, [resetKey, sectionIds]);
  useEffect(() => {
    const onScroll = () => {
      if (typeof window === "undefined") return;
      if (window.scrollY <= 24) {
        setActiveId(sectionIds[0] ?? "");
        return;
      }
      let current = sectionIds[0] ?? "";
      for (const id of sectionIds) {
        const el = document.getElementById(id);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        if (rect.height === 0 && rect.top === 0) continue;
        if (rect.top <= 132) {
          current = id;
        }
      }
      setActiveId(current);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [sectionIds]);
  const jumpTo = useCallback((sectionId: string) => {
    setActiveId(sectionId);
    const el = document.getElementById(sectionId);
    if (!el) return;
    el.scrollIntoView?.({ block: "start", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    pulseCelebration(el);
  }, []);
  return [activeId, jumpTo];
}

function formatHumanDuration(seconds: number): string {
  const rounded = Math.ceil(seconds);
  if (rounded < 60) return `${rounded}s`;
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function PendingContentDetailView({
  video,
  onClose,
  onAddLocal,
  onRetry,
  onRemoved,
}: {
  video: ContentItem;
  onClose: () => void;
  onAddLocal?: () => void;
  onRetry: () => void;
  onRemoved: () => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [retryBusy, setRetryBusy] = useState(false);
  const [removeBusy, setRemoveBusy] = useState(false);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const needsAttention = video.processing_status === "NEEDS_ATTENTION";
  const canRemove = Boolean(
    video.source_id && !video.source_id.startsWith("youtube-channel-"),
  );

  const handleRetry = async () => {
    if (!video.source_id || retryBusy || removeBusy) return;
    setRetryBusy(true);
    setActionError(null);
    setStatusNote(null);
    try {
      await post(`/sources/${video.source_id}/check`, { command_id: commandId() });
      setStatusNote(
        zh
          ? "已重新发起获取；若数秒后仍显示“需要处理”，说明 YouTube 匿名访问验证限制尚未解除，建议改用本地文件导入。"
          : "Retry started. If this item stays in Needs attention, YouTube is still blocking anonymous access — consider importing a local file.",
      );
      onRetry();
    } catch {
      setActionError(
        zh
          ? "暂时无法发起重试，请确认本地服务正常运行后再试。"
          : t("The source could not be checked. Try again later."),
      );
    } finally {
      setRetryBusy(false);
    }
  };

  const handleRemove = async () => {
    if (!video.source_id || !canRemove || removeBusy || retryBusy) return;
    setRemoveBusy(true);
    setActionError(null);
    setStatusNote(null);
    try {
      await patch(`/sources/${video.source_id}`, { enabled: false });
      onRemoved();
    } catch {
      setActionError(
        zh
          ? "移除记录失败，请稍后重试。"
          : "Could not remove this pending entry. Please try again.",
      );
    } finally {
      setRemoveBusy(false);
    }
  };

  return (
    <div className="dashboard-stack">
      <button type="button" className="button button-ghost" onClick={onClose}>
        <PhosphorIcon name="arrow-left" size={14} />
        {t("Back to Content")}
      </button>
      <Panel
        title={
          zh
            ? `YouTube 视频导入详情 · ${video.video_id}`
            : `YouTube video import · ${video.video_id}`
        }
      >
        <div className="reading-meta">
          <Status {...contentStatus(video.provider, video.processing_status)} />
          {video.last_updated ? (
            <span className="tabular-nums">{humanDate(video.last_updated)}</span>
          ) : null}
          {video.source_url ? <span className="hint">{video.source_url}</span> : null}
        </div>
        {needsAttention ? (
          <div className="semantic-state state-neutral">
            <strong>{zh ? "需要处理的原因" : "Why this video needs attention"}</strong>
            <p>
              {zh
                ? "YouTube 当前对该链接触发了匿名访问与机器人验证限制（例如要求登录确认非机器人），或该视频存在访问权限限制。为保护账号安全，本应用不会在后台读取你的浏览器登录状态，因此暂时无法自动拉取标题与字幕。"
                : "YouTube blocked anonymous access to this video (for example, requiring sign-in bot verification or permission checks). Because Intelligence never reads browser cookies behind your back, metadata and captions could not be fetched automatically."}
            </p>
            <p className="hint">
              {zh
                ? "你可以将该视频或字幕文件下载到电脑后直接导入离线转写分析，也可以稍后重新尝试获取，或从列表中移除这条未完成记录。"
                : "You can import a local video or transcript file for offline analysis, retry fetching later, or remove this unfinished entry."}
            </p>
          </div>
        ) : (
          <p role="status">
            {zh
              ? "正在连接 YouTube 获取视频标题、简介与字幕，获取完成后本页会自动刷新为完整阅读详情页。"
              : "Fetching video metadata and captions from YouTube. This page will automatically refresh to the full reader once ready."}
          </p>
        )}
        <div className="button-row">
          {onAddLocal ? (
            <button
              type="button"
              className="button button-primary"
              disabled={retryBusy || removeBusy}
              onClick={onAddLocal}
            >
              {zh ? "改用本地文件导入" : "Import local file instead"}
            </button>
          ) : null}
          <button
            type="button"
            className="button button-secondary"
            disabled={!video.source_id || retryBusy || removeBusy}
            onClick={() => void handleRetry()}
          >
            {retryBusy
              ? zh
                ? "正在重试…"
                : "Retrying…"
              : zh
                ? "重新尝试获取"
                : t("Retry")}
          </button>
          {video.source_url ? (
            <a
              className="button button-secondary"
              href={video.source_url}
              target="_blank"
              rel="noreferrer"
            >
              {zh ? "在浏览器打开原视频" : t("Open original source")}
            </a>
          ) : null}
          {canRemove ? (
            <button
              type="button"
              className="button button-ghost"
              disabled={removeBusy || retryBusy}
              onClick={() => void handleRemove()}
            >
              {removeBusy
                ? zh
                  ? "正在移除…"
                  : "Removing…"
                : zh
                  ? "从列表移除此记录"
                  : "Remove from list"}
            </button>
          ) : null}
        </div>
        {statusNote ? (
          <p className="hint" role="status">
            {statusNote}
          </p>
        ) : null}
        {actionError ? <p role="alert">{actionError}</p> : null}
      </Panel>
    </div>
  );
}

function ContentDetailPanel(
  {
    id,
    highlightedEvidenceId,
    onClose,
    onAddLocal,
    activeFilterSummary,
    nextUnreadVideo,
    onAdvanceToVideo,
    onListChanged,
    onSelectTopicCluster,
  }: {
    id: string;
    highlightedEvidenceId?: string | null;
    onClose: () => void;
    onAddLocal?: () => void;
    activeFilterSummary?: string | null;
    nextUnreadVideo?: {
      videoId: string;
      title: string;
      remainingCount: number;
      scoped?: boolean;
    } | null;
    onAdvanceToVideo?: (nextId: string) => void;
    onListChanged?: () => void;
    onSelectTopicCluster?: (clusterName: string) => void;
  },
) {
  const creatorCapability = useCreatorFollowingCapability();
  const { language, t } = useUiLanguage();
  const [activeSection, scrollToSection] = useActiveSection(READER_SECTION_IDS, id);
  const [refresh, setRefresh] = useState(0);
  const { data, error, errorCode, reload } = useRemote<ContentDetail>(`/videos/${id}`, refresh, undefined, true, true);
  const [evidenceRefresh, setEvidenceRefresh] = useState(0);
  const [captionResultRefresh, setCaptionResultRefresh] = useState(0);
  const transcriptionRefreshId = useRef<string | null>(null);
  const [transcriptionStatus, setTranscriptionStatus] = useState<string | null>(null);
  const [cloudBusy, setCloudBusy] = useState(false);
  const [cloudError, setCloudError] = useState<string | null>(null);
  const [cancelFeedback, setCancelFeedback] = useState<string | null>(null);
  const trackedRetryCommands = useRef(new Map<string, string>());
  const [retryBusy, setRetryBusy] = useState(false);
  const [retryFeedback, setRetryFeedback] = useState<string | null>(null);
  const [transcriptVerbatim, setTranscriptVerbatim] = useState(false);
  const [summaryVerbatim, setSummaryVerbatim] = useState(false);
  const [loadedEvidence, setLoadedEvidence] = useState<ContentEvidence[]>([]);
  const [sharedTranslations, setSharedTranslations] = useState<Record<string, { excerpt: string; language: "zh-CN" | "en" }>>({});
  const [guideMode, setGuideMode] = useState<"译文" | "双语" | "原文">("译文");
  const [guideProgress, setGuideProgress] = useState<{ current: number; total: number } | null>(null);
  const [guideError, setGuideError] = useState<string | null>(null);
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);
  const [wsTranscribeRunning, setWsTranscribeRunning] = useState<{ running: boolean; stage?: string }>({ running: false });
  const [wsActionRequest, setWsActionRequest] = useState<{ nonce: number; kind: "transcribe" | "distill" } | null>(null);
  useEffect(() => {
    setWsTranscribeRunning({ running: false });
    setWsActionRequest(null);
  }, [id]);
  const recordSharedTranslation = useCallback((evidenceId: string, excerpt: string, lang: "zh-CN" | "en") => {
    setSharedTranslations(current => ({ ...current, [evidenceId]: { excerpt, language: lang } }));
  }, []);
  const completedRetry = readTrackedRetry(data?.video.tracked_content_retry, id)?.request;
  const captionResultIdentity = completedRetry?.state === "SUCCEEDED"
    ? `${completedRetry.request_id}:${completedRetry.revision}` : null;
  useEffect(() => {
    if (captionResultIdentity) {
      setEvidenceRefresh(value => value + 1);
      setCaptionResultRefresh(value => value + 1);
    }
  }, [id, captionResultIdentity]);
  useEffect(() => {
    if (!data || (!trackedRetryActive(data.video.tracked_content_retry, id) && !["WAITING", "FETCHING", "READING_CAPTIONS", "ORGANIZING", "TRANSCRIPT_READY", "RETRY_PENDING", "RUNNING", "PENDING"].includes(data.video.processing_status))) return;
    const timer = setTimeout(() => setRefresh(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data]);
  if (error) return <ErrorState error={error} code={errorCode} onReload={reload} />;
  if (!data || data.video.video_id !== id) return <Empty>Loading Content detail…</Empty>;
  if (data.video.work_kind) {
    return (
      <PendingContentDetailView
        video={data.video}
        onClose={onClose}
        onAddLocal={onAddLocal}
        onRetry={() => setRefresh((value) => value + 1)}
        onRemoved={() => {
          onListChanged?.();
          onClose();
        }}
      />
    );
  }
  const transcript = data.transcript;
  const isBilibili = data.video.provider === "BILIBILI";
  const isLocalMedia = data.video.provider === "LOCAL" && data.video.media_kind !== "TEXT";
  const note = data.note.v2;
  const aiBrief = readVideoAiBrief(data.video.ai_brief, data.video.duration_seconds);
  const wsCapabilities = readWorkspaceAiCapabilities(data.workspace_ai_capabilities);
  const wsAiReady = Boolean(wsCapabilities?.ready || aiBrief);
  const wsTranscriberReady = Boolean(wsCapabilities?.transcriber_ready);
  const wsTranscribeJobActive =
    wsTranscribeRunning.running || wsCapabilities?.transcribe_job?.status === "RUNNING";
  const wsTranscribeStage =
    wsTranscribeRunning.stage ?? wsCapabilities?.transcribe_job?.stage ?? "TRANSCRIBING";
  const localCapability = readContentLocal(data.local_intelligence, data.video, id);
  const cloudWait = data.intelligence_result.status === "WAITING_MODEL" && data.intelligence_result.selected_provider === "zhipu_bigmodel";
  const unstartedLongWait = data.intelligence_result.status === "WAITING_MODEL"
    && !cloudWait
    && ["local-grounding-qwen35-9b-lossless-rle-runtime-0.40.6-v2", "local-grounding-qwen35-9b-lossless-rle-runtime-0.40.9-v3"].includes(localCapability?.profile_id ?? "")
    && data.waiting_model_executions?.some(wait => wait.can_cancel === true) === true;
  const visibleHistory = data.history.filter((event) =>
    event.type === "JOB_STATUS" || !event.type
  );
  // The offline transcription job owns the displayed state once it has one, so
  // a run in progress is not summarised by the snapshot status behind it.
  const readingStatus = isLocalMedia && wsTranscribeJobActive
    ? {
        value: "RUNNING",
        label:
          language === "zh-CN"
            ? wsTranscribeStage === "DISTILLING"
              ? "正在提炼中文洞察…"
              : "正在离线语音转写…"
            : "Transcribing…",
      }
    : isLocalMedia && wsTranscriberReady && transcript.status !== "AVAILABLE"
      ? {
          value: "IMPORTED",
          label: language === "zh-CN" ? "已导入 · 待语音转写" : "Imported · Ready to transcribe",
        }
      : isLocalMedia && aiBrief && transcript.status === "AVAILABLE"
        ? {
            value: "READY",
            label: language === "zh-CN" ? "已完成转写与洞察" : "Transcribed & distilled",
          }
        : isLocalMedia && transcriptionStatus
          ? { value: transcriptionStatus, label: transcriptionCopy(transcriptionStatus) }
          : aiBrief?.source_basis === "METADATA_ONLY" &&
              (data.video.provider ?? "YOUTUBE") === "YOUTUBE" &&
              ["FAILED", "FAILED_FINAL", "FAILED_RETRYABLE", "RETRY_REQUIRED", "METADATA_READY"].includes(
                data.video.processing_status,
              )
            ? {
                value: "METADATA_READY",
                label: language === "zh-CN" ? "无原生字幕" : "No native captions",
              }
            : contentStatus(
                data.video.provider,
                isLocalMedia && data.video.processing_status === "TRANSCRIPTION_UNAVAILABLE"
                  ? "IMPORTED"
                  : data.video.processing_status,
              );
  return (
    <div className="dashboard-stack reader-detail-stack">
      <div className="reader-back-row">
        <button className="button button-ghost" onClick={onClose}>
          <PhosphorIcon name="arrow-left" size={14} />
          {t("Back to Content")}
        </button>
        {activeFilterSummary ? (
          <span className="reader-filter-context-pill" role="status">
            <PhosphorIcon name="funnel" size={12} />
            {language === "zh-CN"
              ? `当前筛选：${activeFilterSummary}`
              : `Active filter: ${activeFilterSummary}`}
          </span>
        ) : null}
      </div>
      <Panel title={data.video.title ?? data.video.video_id} className="reader-hero-panel">
        <div className={`reading-meta${isLocalMedia || isBilibili ? " local-media-meta" : ""}`}>
          <Status {...readingStatus} />
          <span>{data.video.provider === "LOCAL" ? t("Local") : isBilibili ? `${t("Bilibili")} · ${data.video.channel_name ?? ""}` : data.video.channel_name} · {humanDate(isBilibili ? data.video.published_at : data.video.imported_at ?? data.video.published_at)}</span>
          {data.video.media_kind && <span>{t(({TEXT:"Text",AUDIO:"Audio",VIDEO:"Video"} as Record<string,string>)[data.video.media_kind])}{isBilibili ? "" : ` · ${data.video.format}`}</span>}
          {data.video.source_language && <span>{t("Source language")}: {data.video.source_language === "und" ? t("Language unavailable") : data.video.source_language}</span>}
          {data.video.duration_seconds != null && <span>{t("Media duration")}: {formatHumanDuration(data.video.duration_seconds)}</span>}
        </div>
        <div className="button-row">
          {data.video.source_url
            ? (
              <a className="button button-ghost button-small" href={data.video.source_url} target="_blank" rel="noreferrer">
                {t("Open original source")}
              </a>
            )
            : null}
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={event => {
              pulseCelebration(event.currentTarget);
              const guideLines = loadedEvidence
                .map(ev => {
                  const tr = sharedTranslations[ev.evidence_id]?.excerpt ?? ev.translated_excerpt;
                  if (!tr) return null;
                  const range = ev.locator_type === "TEXT_RANGE" ? "" : `[${timestampRange(ev.start_ms, ev.end_ms)}] `;
                  return `${range}${cleanTranslatedCaptionText(tr)}`;
                })
                .filter((v): v is string => Boolean(v));
              const cleanedSummary = note?.summary ? cleanCaptionText(note.summary).text : "";
              const cleanedPts = note?.core_points ? dedupeSummaryPoints(cleanedSummary, note.core_points) : [];
              const md = buildMarkdownVideoNote({
                title: data.video.title ?? data.video.video_id,
                channelName: data.video.channel_name,
                sourceUrl: data.video.source_url,
                publishedAt: humanDate(data.video.published_at ?? data.video.imported_at),
                summary: cleanedSummary,
                chineseGuide: guideLines,
                corePoints: cleanedPts,
              });
              void navigator.clipboard?.writeText(md);
              setCopiedMarkdown(true);
              setTimeout(() => setCopiedMarkdown(false), 2200);
            }}
          >
            <PhosphorIcon name="file-text" size={13} />
            {t(copiedMarkdown ? "Copied Markdown note" : "Copy Markdown note")}
          </button>
          <WorkspaceVideoAiActions
            videoId={data.video.video_id}
            title={data.video.title ?? data.video.video_id}
            channelName={data.video.channel_name}
            sourceUrl={data.video.source_url}
            provider={data.video.provider}
            isLocalMedia={isLocalMedia}
            transcriptAvailable={transcript.status === "AVAILABLE"}
            aiBrief={aiBrief}
            obsidianMarkdown={data.obsidian_markdown}
            initialTranscribeJob={wsCapabilities?.transcribe_job}
            actionRequest={wsActionRequest}
            onTranscribeStateChange={(running, stage) =>
              setWsTranscribeRunning({ running, stage })
            }
            nextUnreadVideo={nextUnreadVideo}
            onAdvanceToVideo={onAdvanceToVideo}
            onBack={onClose}
            onCompleted={() => {
              setRefresh(value => value + 1);
              setEvidenceRefresh(value => value + 1);
              onListChanged?.();
            }}
          />
        </div>
      </Panel>
      <div role="toolbar" aria-label={t("Section jump")} className="reader-jump-bar">
        {([
          ["section-intelligence", "sparkle", "Jump · Intelligence"],
          ["section-summary", "file-text", "Jump · Summary"],
          ["section-evidence", "shield-check", "Jump · Evidence"],
          ["section-transcript", "quotes", "Jump · Transcript"],
          ["section-history", "clock", "Jump · History"],
        ] as const).map(([secId, iconName, labelKey]) => {
          const isActive = activeSection === secId;
          return (
            <button
              key={secId}
              type="button"
              aria-current={isActive ? "location" : undefined}
              className={`reader-jump-chip${isActive ? " is-active" : ""}`}
              onClick={() => scrollToSection(secId)}
            >
              <PhosphorIcon name={iconName} weight={isActive ? "fill" : "regular"} size={13} />
              {t(labelKey)}
            </button>
          );
        })}
      </div>
      <TrackedContentRetry id={id} value={data.video.tracked_content_retry} commands={trackedRetryCommands} onRefresh={() => { setRefresh(value => value + 1); setEvidenceRefresh(value => value + 1); }} />
      {data.video.caption_timing_status === "UNAVAILABLE" && !data.video.source_id && <Panel title="Processing needs attention"><p>{t("The captured captions have no verified source timing. Content needs timed captions before Summary and source references can be prepared.")}</p></Panel>}
      {data.video.source_id && (["RETRY_REQUIRED", "FAILED"].includes(data.video.processing_status) || data.video.caption_timing_status === "UNAVAILABLE") && <Panel title="Processing needs attention">{data.video.caption_timing_status === "UNAVAILABLE" && <p>{t("The captured captions have no verified source timing. Content needs timed captions before Summary and source references can be prepared.")}</p>}<p>{t(data.video.retry_allowed === false ? "This Content needs source or processing readiness review before it can be processed again." : data.video.summary_preparation_status === "NEEDS_ATTENTION" ? "Timed captions are saved, but the Summary could not be prepared. Retry to organize this Content; your captured text and source references are kept." : data.video.caption_timing_status === "UNAVAILABLE" ? "Retry to check this source for native timed captions. Your captured text and history are kept." : "Processing needs attention. Check the source and processing history before retrying; retry may still fail.")}</p><button className="button button-secondary" disabled={retryBusy || data.video.retry_allowed === false} onClick={async () => { setRetryBusy(true); setRetryFeedback(null); try { await post(`/sources/${data.video.source_id}/check`, { command_id: commandId() }); setRetryFeedback("Retry accepted. Processing status will update here."); setRefresh(value => value + 1); } catch { setRetryFeedback("The source could not be checked. Try again later."); } finally { setRetryBusy(false); } }}>{t(retryBusy ? "Retrying…" : "Retry")}</button>{retryFeedback && <p role="status">{t(retryFeedback)}</p>}</Panel>}
      {isBilibili && data.video.processing_status !== "SOURCE_UNAVAILABLE" && <FollowCreatorFromContent id={id} capability={creatorCapability} />}
      {data.video.provider === "YOUTUBE" && data.video.channel_id && /^UC[A-Za-z0-9_-]{22}$/.test(data.video.channel_id) && <FollowCreatorFromContent id={id} provider="YOUTUBE" />}
      <Panel id="section-intelligence" icon="sparkle" title="Intelligence result">
        <WorkspaceVideoAiBriefCard
          brief={aiBrief}
          obsidianMarkdown={data.obsidian_markdown}
          onSelectTopicCluster={onSelectTopicCluster}
        />
        {(() => {
          const hasActiveLegacyExecution = Boolean(
            cloudWait ||
              unstartedLongWait ||
              data.waiting_model_executions?.length ||
              data.pending_synthesis_executions?.length ||
              ["RUNNING", "PENDING"].includes(data.intelligence_result.status),
          );
          const legacyIntelBody = (
            <>
              <LocalIntelligencePresentation content={localCapability} onReload={reload} />
              <div className="semantic-state state-neutral">
                <Status value={data.intelligence_result.status} label={cloudWait ? "Waiting for cloud execution prerequisites" : unstartedLongWait ? "Extraction has not started" : undefined} />
                <p role={data.intelligence_result.status === "CANCELLED" ? "status" : undefined}>{t(unstartedLongWait
                  ? "This extraction has not run. You can safely cancel it, then request extraction again."
                  : intelligenceResultCopy(data.intelligence_result.status, data.intelligence_result.cloud_http429_code, data.intelligence_result.selected_provider, data.intelligence_result.can_cancel))}</p>
                {(cloudWait || (data.intelligence_result.status === "REJECTED_OUTPUT" && data.intelligence_result.cloud_http429_code === "1315")) && <a className="source-link" href={`#Settings/models/bigmodel?return=${encodeURIComponent(`#Content/${id}`)}`}>{t("Settings")}</a>}
                {cancelFeedback && data.intelligence_result.status !== "CANCELLED" && <p role="status">{cancelFeedback}</p>}
                {Boolean(data.waiting_model_executions?.length || data.pending_synthesis_executions?.length) && <div>
                  {[...(data.waiting_model_executions ?? []), ...(data.pending_synthesis_executions ?? [])].map((wait) => <div key={wait.execution_id}>
                    {data.pending_synthesis_executions?.some(pending => pending.execution_id === wait.execution_id) ? <p>{t("This extraction has not run. You can safely cancel it, then request extraction again.")}</p> : wait.selected_provider === "zhipu_bigmodel"
                      ? <><p>{t(intelligenceResultCopy("WAITING_MODEL", undefined, wait.selected_provider, wait.can_cancel))}</p>
                        <a className="source-link" href={`#Settings/models/bigmodel?return=${encodeURIComponent(`#Content/${id}`)}`}>{t("Settings")}</a></>
                      : (!unstartedLongWait || localCapability?.qualification_status === "NOT_QUALIFIED")
                        && <p>{t("No qualified Intelligence model is currently available.")}</p>}
                    <div className="button-row">
                    <span className="hint">{humanDate(wait.updated_at)}</span>
                    {wait.can_cancel === true ? <button type="button" className="button button-secondary" disabled={cloudBusy} onClick={async () => {
                      setCloudBusy(true); setCloudError(null);
                      try {
                        await post(`/videos/${id}/intelligence/cancel`, { execution_id: wait.execution_id });
                        setCancelFeedback(t(intelligenceResultCopy("CANCELLED")));
                        setRefresh(value => value + 1);
                      } catch {
                        setCloudError(t("This task cannot be safely cancelled. Refresh its current state."));
                        setRefresh(value => value + 1);
                      } finally { setCloudBusy(false); }
                    }}>{t(cloudBusy ? "Cancelling…" : "Cancel this extraction")}</button>
                      : <p>{t("This task cannot be safely cancelled. Refresh its current state.")}</p>}
                    </div>
                  </div>)}
                </div>}
                {data.manual_intelligence_eligible && <div className="button-row">
                  <button type="button" className="button button-primary" disabled={cloudBusy || !localCapability || ["UNKNOWN", "CONFIGURATION_REQUIRED"].includes(localCapability.request_state) || Boolean(data.waiting_model_executions?.length)} onClick={async () => {
                    setCloudBusy(true); setCloudError(null); setCancelFeedback(null);
                    try { await post(`/videos/${id}/intelligence`, { command_id: commandId() }); setRefresh(value => value + 1); }
                    catch (error) { setCloudError(t(error instanceof ApiRequestError && error.code === "MODEL_CONFIGURATION_REQUIRED" ? "Configure the local Intelligence model in Settings before requesting extraction. No task will be created with the current route." : "Intelligence could not start. Check model readiness and try again.")); }
                    finally { setCloudBusy(false); }
                  }}>{t(cloudBusy ? "Considering Content…" : "Extract Intelligence")}</button>
                  <p className="hint">{t("Uses qualified local processing when available. Cloud processing requires a separate review and explicit authorization.")}</p>
                </div>}
                {cloudError ? <p role="alert">{cloudError}</p> : null}
                {data.intelligence_result.status === "WAITING_MODEL" && data.cloud_intelligence_available === false
                  ? <p>{t("Cloud Intelligence is currently unavailable because the provider or its runtime credential is unavailable. Existing Summary and Evidence remain usable.")}</p>
                  : null}
                {data.intelligence_result.status === "SUCCEEDED_NO_NEW_INTELLIGENCE"
                  ? (
                    <p className="hint">
                      {t("This is a completed processing result, not an Intelligence validation posture or numeric confidence score.")}
                    </p>
                  )
                  : null}
                {data.video.provider === "YOUTUBE" && (data.intelligence_result.status === "WAITING_MODEL"
                  || (["NOT_PROCESSED", "CANCELLED", "REJECTED_OUTPUT"].includes(data.intelligence_result.status) && data.manual_intelligence_eligible === true))
                  && note?.status === "AVAILABLE" && transcript.status === "AVAILABLE" && (
                  <CloudIntelligencePreview key={id} id={id} manual={data.manual_intelligence_eligible === true}
                    executionKey={`${data.intelligence_result.execution_id ?? ""}:${data.intelligence_result.status}`}
                    onSettled={() => setRefresh(value => value + 1)} />
                )}
              </div>
            </>
          );
          const wsReadyGuide =
            wsAiReady && !aiBrief && !hasActiveLegacyExecution ? (
              <div className="semantic-state state-neutral">
                {isLocalMedia && transcript.status !== "AVAILABLE" ? (
                  wsTranscribeJobActive ? (
                    <>
                      <span className="status status-neutral">
                        {language === "zh-CN"
                          ? wsTranscribeStage === "DISTILLING"
                            ? "语音听写完成 · 正在提炼中文洞察"
                            : "正在本机免费离线听写语音"
                          : "Transcribing offline on this Mac"}
                      </span>
                      <p role="status">
                        {language === "zh-CN"
                          ? "正在你电脑本机将整段课程录音转成带时间戳的逐字稿，并提炼中文核心结论（长视频约需几分钟，期间切去浏览其他页面也不会中断，完成后这里会自动刷新）。"
                          : "Transcribing the full lecture audio locally and distilling Chinese insights. Longer videos take a few minutes; switching pages will not interrupt progress."}
                      </p>
                    </>
                  ) : wsTranscriberReady ? (
                    <>
                      <span className="status status-neutral">
                        {language === "zh-CN" ? "已就绪 · 待一键转写与提炼" : "Ready · Awaiting 1-click transcription"}
                      </span>
                      <p>
                        {language === "zh-CN"
                          ? "音视频已安全保存在本机。点击下方按钮即可在本机免费完成语音听写，自动生成完整时间轴字幕、中文摘要与干货洞察。"
                          : "Media is saved locally. Click below to transcribe speech offline on this Mac and generate timestamped captions, Chinese summary, and key insights."}
                      </p>
                      <div className="button-row">
                        <button
                          type="button"
                          className="button button-primary button-small"
                          onClick={(event) => {
                            pulseCelebration(event.currentTarget);
                            setWsActionRequest((prev) => ({
                              nonce: (prev?.nonce ?? 0) + 1,
                              kind: "transcribe",
                            }));
                          }}
                        >
                          <PhosphorIcon name="sparkle" size={13} />
                          {language === "zh-CN"
                            ? "开始离线语音转写并提炼中文洞察"
                            : "Start offline transcription & Chinese insight"}
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <span className="status status-neutral">
                        {language === "zh-CN" ? "待配置本机语音模型" : "Offline speech model required"}
                      </span>
                      <p>
                        {language === "zh-CN"
                          ? "当前尚未检测到可用的本机 Whisper 语音模型，请前往设置完成配置后再转写。"
                          : "No local Whisper speech model was detected yet. Configure it in Settings first."}
                      </p>
                    </>
                  )
                ) : transcript.status === "AVAILABLE" ? (
                  <>
                    <span className="status status-neutral">
                      {language === "zh-CN" ? "字幕已就绪 · 待提炼洞察" : "Transcript ready · Awaiting insight"}
                    </span>
                    <p>
                      {language === "zh-CN"
                        ? "原始字幕已准备完毕。点击下方按钮即可自动提炼中文总结、评分与核心洞察。"
                        : "Transcript is ready. Click below to distill Chinese summary, score, and insights."}
                    </p>
                    <div className="button-row">
                      <button
                        type="button"
                        className="button button-primary button-small"
                        onClick={(event) => {
                          pulseCelebration(event.currentTarget);
                          setWsActionRequest((prev) => ({
                            nonce: (prev?.nonce ?? 0) + 1,
                            kind: "distill",
                          }));
                        }}
                      >
                        <PhosphorIcon name="sparkle" size={13} />
                        {language === "zh-CN" ? "AI 提炼中文总结与洞察" : "Distill AI Chinese brief"}
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            ) : null;
          return (aiBrief || wsAiReady) && !hasActiveLegacyExecution ? (
            <>
              {wsReadyGuide}
              <details className="legacy-model-diagnostics">
                <summary>
                  {language === "zh-CN"
                    ? "底层离线模型路由与手动核验诊断"
                    : "Underlying local model route & manual diagnostics"}
                </summary>
                {legacyIntelBody}
              </details>
            </>
          ) : (
            legacyIntelBody
          );
        })()}
      </Panel>
      <Panel id="section-summary" icon="file-text" title={data.video.provider === "LOCAL" || isBilibili ? "Summary" : "Summary / Video Notes"}>
        {note?.status === "AVAILABLE"
          ? (() => {
            const summaryClean = note.summary ? cleanCaptionText(note.summary) : { text: "", collapsedCount: 0 };
            const cleanedPoints = (note.core_points ?? []).map(point => cleanCaptionText(point));
            const dedupedPoints = note.core_points ? dedupeSummaryPoints(summaryClean.text, note.core_points) : [];
            const cleanedTimedPoints = (note.timestamped_key_points ?? []).map(point => ({
              point,
              cleaned: cleanCaptionText(point.text),
            }));
            const totalCollapsed = summaryClean.collapsedCount
              + cleanedPoints.reduce((sum, item) => sum + item.collapsedCount, 0)
              + Math.max(0, (note.core_points?.length ?? 0) - dedupedPoints.length)
              + cleanedTimedPoints.reduce((sum, item) => sum + item.cleaned.collapsedCount, 0);
            const rawTranslatable = language === "zh-CN"
              ? loadedEvidence.filter(ev => ev.translation_target_language === "zh-CN" && !evidenceSourceMatchesTarget(ev.source_language, "zh-CN"))
              : [];
            const dedupedGuideMap = new Map<string, ContentEvidence>();
            for (const ev of rawTranslatable) {
              const sig = `${ev.start_ms ?? ""}:${ev.end_ms ?? ""}:${ev.start_line ?? ""}:${ev.end_line ?? ""}:${cleanCaptionText(ev.original_excerpt).text.trim().toLowerCase()}`;
              const existing = dedupedGuideMap.get(sig);
              const hasTr = Boolean((sharedTranslations[ev.evidence_id]?.excerpt ?? ev.translated_excerpt) && (sharedTranslations[ev.evidence_id]?.language ?? ev.translated_language) === "zh-CN");
              const existingHasTr = existing
                ? Boolean((sharedTranslations[existing.evidence_id]?.excerpt ?? existing.translated_excerpt) && (sharedTranslations[existing.evidence_id]?.language ?? existing.translated_language) === "zh-CN")
                : false;
              if (!existing || (hasTr && !existingHasTr)) {
                dedupedGuideMap.set(sig, ev);
              }
            }
            const translatableEvidence = Array.from(dedupedGuideMap.values());
            const translatedGuideRows = translatableEvidence
              .map(ev => {
                const tr = sharedTranslations[ev.evidence_id]?.excerpt ?? ev.translated_excerpt;
                const trLang = sharedTranslations[ev.evidence_id]?.language ?? ev.translated_language;
                return tr && trLang === "zh-CN"
                  ? { item: ev, zh: cleanTranslatedCaptionText(tr), orig: cleanCaptionText(ev.original_excerpt).text }
                  : null;
              })
              .filter((row): row is { item: ContentEvidence; zh: string; orig: string } => row !== null);
            const untranslatedGuideItems = translatableEvidence.filter(ev => {
              const tr = sharedTranslations[ev.evidence_id]?.excerpt ?? ev.translated_excerpt;
              const trLang = sharedTranslations[ev.evidence_id]?.language ?? ev.translated_language;
              return !(tr && trLang === "zh-CN");
            });
            const runChineseGuide = async () => {
              if (guideProgress || !untranslatedGuideItems.length) return;
              setGuideError(null);
              setGuideProgress({ current: 0, total: untranslatedGuideItems.length });
              try {
                for (let idx = 0; idx < untranslatedGuideItems.length; idx++) {
                  const targetItem = untranslatedGuideItems[idx];
                  setGuideProgress({ current: idx + 1, total: untranslatedGuideItems.length });
                  const result = await post<{
                    evidence_id: string;
                    translated_excerpt: string | null;
                    translated_language: "zh-CN" | "en" | null;
                    translation_target_language: "zh-CN" | "en";
                  }>(`/videos/${encodeURIComponent(id)}/evidence/${encodeURIComponent(targetItem.evidence_id)}/translation`, {});
                  if (result.evidence_id !== targetItem.evidence_id || !result.translated_excerpt || result.translated_language !== result.translation_target_language) {
                    throw new Error("INCOMPLETE_GUIDE");
                  }
                  recordSharedTranslation(targetItem.evidence_id, result.translated_excerpt, result.translated_language);
                }
                setGuideMode("译文");
              } catch {
                setGuideError("Could not create a verified local translation. Original Evidence is still available.");
              } finally {
                setGuideProgress(null);
              }
            };
            const visiblePoints = summaryVerbatim ? (note.core_points ?? []) : dedupedPoints;
            const summaryNoteNode = (
              <div className="summary-note">
                <div className="reading-meta">
                  <Status value="AVAILABLE" />
                  <span>{note.method === "SOURCE_EXCERPTS"
                    ? t("Original source language (unchanged)")
                    : !note.language || note.language === "und" ? t("Language unavailable") : note.language}</span>
                </div>
                {translatableEvidence.length > 0 && (
                  <div className="chinese-guide-box">
                    <div className="chinese-guide-head">
                      <strong>{t("Chinese guide · Local Qwen3")}</strong>
                      <div className="button-row">
                        {translatedGuideRows.length > 0 && (
                          <div className="segmented" role="group" aria-label={t("Chinese reading guide")}>
                            {([
                              ["译文", t("Chinese reading guide")],
                              ["双语", t("Bilingual comparison")],
                              ["原文", t("Original summary")],
                            ] as const).map(([key, label]) => (
                              <button
                                key={key}
                                type="button"
                                aria-pressed={guideMode === key}
                                className={guideMode === key ? "active" : ""}
                                onClick={() => setGuideMode(key)}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        )}
                        {untranslatedGuideItems.length > 0 && (
                          <button
                            type="button"
                            className="button button-primary button-small"
                            disabled={guideProgress !== null}
                            onClick={event => {
                              pulseCelebration(event.currentTarget);
                              void runChineseGuide();
                            }}
                          >
                            {guideProgress
                              ? `${t("Generating local Chinese reading guide")} ${guideProgress.current}/${guideProgress.total}…`
                              : translatedGuideRows.length > 0
                                ? `${t("Complete Chinese reading guide (free local)")} (${translatedGuideRows.length}/${translatableEvidence.length})`
                                : t("Generate Chinese reading guide (free local)")}
                          </button>
                        )}
                      </div>
                    </div>
                    {guideError && <p className="hint" role="alert">{t(guideError)}</p>}
                    {translatedGuideRows.length > 0 && guideMode !== "原文" && (
                      <ol className="chinese-guide-list">
                        {translatedGuideRows.map(({ item: ev, zh, orig }) => (
                          <li key={ev.evidence_id}>
                            <span className="chinese-guide-time tabular-nums">
                              {ev.locator_type === "TEXT_RANGE" ? textLineRange(ev.start_line, ev.end_line, t) : timestampRange(ev.start_ms, ev.end_ms)}
                            </span>
                            <div>
                              <p className="summary-copy">{zh}</p>
                              {guideMode === "双语" && <p className="hint">{orig}</p>}
                            </div>
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                )}
                {note.method === "SOURCE_EXCERPTS" && <p className="hint">{t("These are original source excerpts, selected deterministically without a model or new interpretation.")}</p>}
                <CaptionCleanBar
                  collapsedCount={totalCollapsed}
                  showVerbatim={summaryVerbatim}
                  onToggle={() => setSummaryVerbatim(current => !current)}
                />
                {note.summary && (translatedGuideRows.length === 0 || guideMode !== "译文" || summaryVerbatim)
                  ? <><h3>{t("Summary")}</h3><p className="summary-copy">{summaryVerbatim ? note.summary : summaryClean.text}</p></>
                  : null}
                {visiblePoints.length
                  ? <><h3>{t("Key points")}</h3><ul>{visiblePoints.map((point, idx) => <li key={`${idx}:${point}`}>{point}</li>)}</ul></>
                  : null}
                {note.timestamped_key_points?.length
                  ? (
                    <>
                      <h3>{t("Timestamped key points")}</h3>
                      <ol>
                        {cleanedTimedPoints.map(({ point, cleaned }) => (
                          <li key={`${point.start_seconds}:${point.text}`}>
                            {data.video.source_url
                              ? (
                                <a
                                  className="source-link tabular-nums"
                                  href={videoAt(data.video.source_url, point.start_seconds * 1000)}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {timestamp(point.start_seconds * 1000)}
                                </a>
                              )
                              : <strong className="tabular-nums">{timestamp(point.start_seconds * 1000)}</strong>} · {summaryVerbatim ? point.text : cleaned.text}
                          </li>
                        ))}
                      </ol>
                      <p className="hint">
                        {t("Timestamps appear only when the cited trusted Evidence has a timed-subtitle position.")}
                      </p>
                    </>
                  )
                  : null}
                {note.evidence_references?.length
                  ? (
                    <details className="provenance">
                      <summary>{t("Evidence references")}</summary>
                      <ul>
                        {note.evidence_references.map((reference) => (
                          <li key={reference.evidence_id}>
                            <strong>{reference.evidence_id}</strong>
                            {reference.start_seconds === null ? "" : ` · ${Math.round(reference.start_seconds)}s`}
                            <p>{summaryVerbatim ? reference.excerpt : cleanCaptionText(reference.excerpt).text}</p>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )
                  : null}
                <p className="hint">
                  {t("This is the current verified version for this Content. Failed or unverified newer attempts do not replace it.")}
                </p>
              </div>
            );
            return aiBrief && note.note_identity?.startsWith("workspace-ai/") ? (
              <details className="provenance workspace-ai-note-details">
                <summary>
                  {language === "zh-CN"
                    ? "查看分段要点、时间戳跳转与证据引用明细"
                    : "View timestamped key points & evidence references"}
                </summary>
                {summaryNoteNode}
              </details>
            ) : (
              summaryNoteNode
            );
          })()
          : !aiBrief ? (
            isLocalMedia && wsTranscriberReady && transcript.status !== "AVAILABLE" ? (
              <div className="semantic-state state-neutral">
                <span className="status status-neutral">
                  {language === "zh-CN" ? "待语音转写后生成" : "Pending transcription"}
                </span>
                <p>
                  {language === "zh-CN"
                    ? "完成上方「离线语音转写并提炼中文洞察」后，这里会自动展示结构化中文导读与关键时间点。"
                    : "Complete offline speech transcription above to view structured Chinese summary and timestamped key points here."}
                </p>
              </div>
            ) : (
              <div className="semantic-state state-neutral">
                <Status value="UNAVAILABLE" />
                <p>{t("Summary / Video Notes are not available for this Content yet. No summary is fabricated from missing output.")}</p>
              </div>
            )
          ) : (
            <p className="hint">
              {language === "zh-CN"
                ? "AI 中文核心结论与洞察切口已展示在上方「洞察处理结果」卡片中；分段原话时间轴请查阅下方「原始证据」与「原始字幕」。"
                : "The Chinese AI executive summary is shown in the Intelligence Result card above; check Evidence and Transcript below for timestamped quotes."}
            </p>
          )}
      </Panel>
      <ContentEvidencePanel
        videoId={data.video.video_id}
        sourceUrl={data.video.source_url}
        refresh={evidenceRefresh}
        highlightedEvidenceId={highlightedEvidenceId}
        externalTranslations={sharedTranslations}
        onTranslateSuccess={recordSharedTranslation}
        onEvidenceLoaded={setLoadedEvidence}
      />
      <Panel id="section-transcript" icon="quotes" title={data.video.provider === "LOCAL" && data.video.media_kind === "TEXT" ? "Source text" : "Transcript"}>
        {isBilibili && <BilibiliCaptionStatus id={id} status={data.video.processing_status} onCompleted={() => { setRefresh(value => value + 1); setEvidenceRefresh(value => value + 1); }} />}
        {isLocalMedia && wsTranscriberReady && transcript.status !== "AVAILABLE" ? (
          <>
            <div className="semantic-state state-neutral">
              <span className="status status-neutral">
                {language === "zh-CN"
                  ? wsTranscribeJobActive
                    ? "正在离线听写逐字稿…"
                    : "本机离线语音模型已就绪"
                  : wsTranscribeJobActive
                    ? "Transcribing speech…"
                    : "Offline speech model ready"}
              </span>
              <p>
                {language === "zh-CN"
                  ? "已内置 Whisper 离线语音识别模型（全程在本机运行，音视频不会上传云端）。完成语音转写后，完整带时间戳的原始逐字稿会保存在这里。"
                  : "Built-in offline Whisper speech model is ready on this Mac. Once transcribed, the full timestamped transcript will be saved here."}
              </p>
            </div>
            <details className="legacy-model-diagnostics">
              <summary>
                {language === "zh-CN"
                  ? "底层本地转写器高级设置与诊断"
                  : "Advanced local transcriber settings & diagnostics"}
              </summary>
              <LocalTranscription
                id={id}
                onStatusChange={setTranscriptionStatus}
                onCompleted={() => {
                  if (transcriptionRefreshId.current === id) return;
                  transcriptionRefreshId.current = id;
                  setRefresh(value => value + 1);
                  setEvidenceRefresh(value => value + 1);
                }}
              />
            </details>
          </>
        ) : (
          isLocalMedia && (
            <LocalTranscription
              id={id}
              onStatusChange={setTranscriptionStatus}
              onCompleted={() => {
                if (transcriptionRefreshId.current === id) return;
                transcriptionRefreshId.current = id;
                setRefresh(value => value + 1);
                setEvidenceRefresh(value => value + 1);
              }}
            />
          )
        )}
        {transcript.status === "AVAILABLE" && transcript.text
          ? (() => {
            const timedClean = transcript.timed_segments?.length ? cleanTimedSegments(transcript.timed_segments) : null;
            const plainClean = !timedClean ? cleanCaptionText(transcript.text) : null;
            const collapsed = timedClean ? timedClean.collapsedCount : (plainClean?.collapsedCount ?? 0);
            const displaySegments = timedClean ? (transcriptVerbatim ? transcript.timed_segments! : timedClean.segments) : null;
            return (
              <>
                <CaptionCleanBar
                  collapsedCount={collapsed}
                  showVerbatim={transcriptVerbatim}
                  onToggle={() => setTranscriptVerbatim(current => !current)}
                />
                <div className="transcript-scroll-box">
                  {displaySegments
                    ? <ol className="timed-transcript">{displaySegments.map((segment, index) => <li key={index}><time className="tabular-nums">{timestampRange(segment.start_ms, segment.end_ms)}</time><span>{segment.text}</span></li>)}</ol>
                    : <div className="transcript-copy">{transcriptVerbatim ? transcript.text : plainClean!.text}</div>}
                </div>
              </>
            );
          })()
          : isLocalMedia || isBilibili ? null : (
            <div className="semantic-state state-neutral">
              <Status {...contentStatus(data.video.provider, transcript.status)} />
              <p>{t(({
                TRANSCRIPTION_UNAVAILABLE: "Media snapshots are saved. A provisioned offline transcription adapter is required for transcript, Summary and Evidence; nothing is sent to a cloud service.",
                TRANSCRIPTION_FAILED: "Local transcription failed",
                NOT_PROCESSED: "No canonical transcript has been recorded for this video.",
                FAILED: "Transcript processing ended without a canonical transcript.",
                UNAVAILABLE: "The recorded canonical transcript cannot be safely read.",
              } as Record<string, string>)[transcript.status] ?? "A readable transcript is not available yet.")}</p>
            </div>
          )}
      </Panel>
      {wsAiReady ? (
        <details className="legacy-model-diagnostics">
          <summary>
            {language === "zh-CN"
              ? "高级实验性功能：多模型对照深度分析与资格诊断"
              : "Experimental: Multi-model Deep Analysis & qualification diagnostics"}
          </summary>
          <DeepAnalysisPanel
            videoId={data.video.video_id}
            inputRefresh={captionResultRefresh}
            onCompleted={() => setEvidenceRefresh((value) => value + 1)}
          />
        </details>
      ) : (
        <DeepAnalysisPanel
          videoId={data.video.video_id}
          inputRefresh={captionResultRefresh}
          onCompleted={() => setEvidenceRefresh((value) => value + 1)}
        />
      )}
      <Panel id="section-history" icon="clock" title="Processing history">
        {visibleHistory.length
          ? visibleHistory.slice(0, 12).map((event, index) => (
            <div className="metadata-row" key={`${event.timestamp}:${event.summary}:${index}`}>
              <span>{humanDate(event.timestamp)}</span>
              <div><Status value={event.status} /><p>{event.code === "INVALID_RESPONSE" && event.context?.stage === "ANALYSIS"
                ? t("The local Summary did not pass output checks. The transcript remains available; no Summary or Evidence was invented. Check Settings for local model readiness.")
                : event.type === "JOB_STATUS"
                  ? <>{t(({ METADATA: "Source metadata", TRANSCRIPT: "Transcript", SCORING: "Scoring", ANALYSIS: "Summary" } as Record<string, string>)[event.context?.stage ?? ""] ?? "Processing")}: {t(statusLabel(event.status))}.</>
                  : t(event.summary)}</p></div>
            </div>
          ))
          : <Empty>No processing history yet.</Empty>}
      </Panel>
    </div>
  );
}

/** English source labels; Chinese is provided by the UI-language mechanism. */
function deepAnalysisRoleLabel(role: string) {
  const labels: Record<string, string> = {
    CORE_CONCLUSION: "Core conclusion",
    KEY_EVIDENCE: "Key evidence",
    UNCERTAINTY: "Uncertainty",
    RELEVANCE_TO_USER: "Relevance to you",
    NEXT_QUESTION: "Next question",
  };
  return labels[role] ?? role;
}

function deepAnalysisReasonCopy(
  availability: string,
  reasonCode: string | null,
) {
  // Localize on the stable machine code. Backend English prose is a developer
  // diagnostic and must never be the Chinese product text.
  const byCode: Record<string, string> = {
    CREDENTIAL_MISSING: "The model is qualified, but its cloud credential is missing. Configure the runtime credential before requesting Deep Analysis.",
    ROUTE_UNREACHABLE: "The model is qualified, but the provider is currently unreachable. Deep Analysis cannot run until connectivity is restored.",
    PRODUCTION_ROUTE_UNAVAILABLE: "The model is qualified, but this route cannot execute in the current environment.",
    NO_QUALIFIED_MODEL:
      "Deep Analysis is unavailable because no model is currently qualified for it. Nothing is downgraded silently, and Summary and Evidence stay usable.",
    CONTENT_NOT_FOUND: "This Content is not available.",
    NOT_REQUESTED:
      "Deep Analysis has not been run for this Content. It is an on-demand action and runs nothing until you ask for it.",
    RESULT_AVAILABLE: "A Deep Analysis result is available for this Content.",
    SCORING_UNAVAILABLE:
      "Deep Analysis needs a verified scoring read for this Content. It is unavailable right now.",
    NO_TIMED_TRANSCRIPT_EVIDENCE:
      "This Content has no trusted timed transcript Evidence, so Deep Analysis cannot cite anything durably. No timestamp is invented and no result is produced.",
    CLOUD_CONSENT_REQUIRED:
      "This route would send bounded data to a cloud provider and needs your explicit consent for this run.",
    VALIDATION_FAILED:
      "Deep Analysis did not produce a trusted result. No partial or invented result is shown.",
    SERVICE_UNAVAILABLE: "Deep Analysis is unavailable for this Content right now.",
  };
  if (reasonCode && byCode[reasonCode]) return byCode[reasonCode];
  const byAvailability: Record<string, string> = {
    NOT_REQUESTED:
      "Deep Analysis has not been run for this Content. It is an on-demand action and runs nothing until you ask for it.",
    NOT_QUALIFIED:
      "Deep Analysis is unavailable because no model is currently qualified for it. Nothing is downgraded silently, and Summary and Evidence stay usable.",
    CONTENT_UNAVAILABLE: "This Content is not available.",
    SCORING_UNAVAILABLE:
      "Deep Analysis needs a verified scoring read for this Content. It is unavailable right now.",
    EVIDENCE_UNAVAILABLE:
      "This Content has no trusted timed transcript Evidence, so Deep Analysis cannot cite anything durably. No timestamp is invented and no result is produced.",
    CLOUD_CONSENT_REQUIRED:
      "This route would send bounded data to a cloud provider and needs your explicit consent for this run.",
    FAILED:
      "Deep Analysis did not produce a trusted result. No partial or invented result is shown.",
    AVAILABLE: "A Deep Analysis result is available for this Content.",
  };
  return (
    byAvailability[availability] ??
    "Deep Analysis is unavailable for this Content right now."
  );
}

function deepAnalysisRunErrorCopy(reasonCode: string | null, availability: string) {
  // Localize on the stable machine reason_code; never on backend English prose.
  if (["CREDENTIAL_MISSING", "ROUTE_UNREACHABLE", "PRODUCTION_ROUTE_UNAVAILABLE"].includes(reasonCode ?? "")) return deepAnalysisReasonCopy(availability, reasonCode);
  const governance: Record<string, string> = {
    DISPATCH_AMBIGUOUS: "The cloud request may have been processed. It will not be retried automatically. Check the provider before requesting another run.",
    EXECUTION_ALREADY_DISPATCHED: "This execution has already been dispatched. It will not be charged again.",
    PREFLIGHT_CHANGED: "The input or route changed. Review a new preflight before authorizing.",
    COST_ACKNOWLEDGEMENT_REQUIRED: "Acknowledge the unknown cost before authorizing this execution.",
  };
  if (reasonCode && governance[reasonCode]) return governance[reasonCode];
  const byCode: Record<string, string> = {
    NO_QUALIFIED_MODEL:
      "Deep Analysis could not run because no model is currently qualified for it.",
    CONTENT_NOT_FOUND: "This Content is not available.",
    SCORING_UNAVAILABLE:
      "Deep Analysis needs a verified scoring read for this Content. It is unavailable right now.",
    NO_TIMED_TRANSCRIPT_EVIDENCE:
      "This Content has no trusted timed transcript Evidence, so Deep Analysis cannot cite anything durably.",
    CLOUD_CONSENT_REQUIRED:
      "This route would send bounded data to a cloud provider and needs your explicit consent for this run.",
    VALIDATION_FAILED:
      "Deep Analysis did not produce a trusted result. No partial or invented result is shown. You can retry.",
  };
  if (reasonCode && byCode[reasonCode]) return byCode[reasonCode];
  if (availability === "FAILED") {
    return "Deep Analysis did not produce a trusted result. No partial or invented result is shown. You can retry.";
  }
  return "Deep Analysis could not run for this Content right now. You can retry.";
}

function deepAnalysisConfidenceCopy(code: string) {
  // Stable machine confidence codes; unknown codes stay honestly unknown.
  const known: Record<string, string> = {
    INSUFFICIENT_EVIDENCE: "Insufficient Evidence",
  };
  return known[code] ?? code;
}

function DeepAnalysisStatusLabel({ value }: { value: string }) {
  const { t } = useUiLanguage();
  // Source text is English; Chinese is the translation, matching the existing
  // localization convention.
  const labels: Record<string, string> = {
    AVAILABLE: "Completed",
    UNAVAILABLE: "Unavailable",
    NOT_REQUESTED: "Not run yet",
    NOT_QUALIFIED: "Not qualified",
    CONTENT_UNAVAILABLE: "Unavailable",
    SCORING_UNAVAILABLE: "Unavailable",
    EVIDENCE_UNAVAILABLE: "Unavailable",
    CLOUD_CONSENT_REQUIRED: "Consent required",
    FAILED: "Failed",
  };
  return <>{t(labels[value] ?? value)}</>;
}

function qualificationCopy(state: string) {
  const labels: Record<string, string> = {
    NOT_TESTED: "Qualification not tested", FAILED: "Qualification failed",
    STALE: "Qualification needs renewal", CONTRACT_VERIFIED: "Fixture contract verified; live qualification missing",
    QUALIFIED: "Live model qualified", DEVELOPER_INJECTION: "Development fixture route",
  };
  return labels[state] ?? "Qualification unavailable";
}
function costDisclosureCopy(state: string) {
  const labels: Record<string, string> = {
    UNKNOWN: "The monetary cost is unknown. No hard spending cap is enforced.",
    FREE: "No cloud model charge applies.",
    ESTIMATED: "The cost is estimated and may change.",
    KNOWN: "The disclosed cost is known for this execution.",
  };
  return labels[state] ?? labels.UNKNOWN;
}

function DeepAnalysisPanel(
  { videoId, onCompleted, inputRefresh = 0 }: { videoId: string; onCompleted: () => void; inputRefresh?: number },
) {
  const { t } = useUiLanguage();
  const [refresh, setRefresh] = useState(0);
  const { data, error, errorCode, reload } = useRemote<DeepAnalysisEnvelope>(
    `/videos/${videoId}/deep-analysis`,
    refresh + inputRefresh,
  );
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [preflight, setPreflight] = useState<DeepAnalysisPreflight | null>(null);
  const [costAcknowledged, setCostAcknowledged] = useState(false);
  const [dispatchBlocked, setDispatchBlocked] = useState(false);
  useEffect(() => { setPreflight(null); setCostAcknowledged(false); }, [videoId, inputRefresh]);
  useEffect(() => { setDispatchBlocked(false); }, [videoId]);

  async function run(authorized?: DeepAnalysisPreflight) {
    setBusy(true);
    setActionError(null);
    try {
      const status = data?.deep_analysis?.status;
      if (status?.consent_required && !authorized) {
        const response = await post<{ preflight: DeepAnalysisPreflight }>(`/videos/${videoId}/deep-analysis/preflight`, { route_id: status.route_id });
        setCostAcknowledged(false);
        setPreflight(response.preflight);
        return;
      }
      await post(`/videos/${videoId}/deep-analysis`, authorized ? {
        route_id: authorized.route_id, execution_id: authorized.execution_id,
        authorize_cloud: true, acknowledge_unknown_cost: costAcknowledged,
        egress_mode: authorized.data_egress_mode,
      } : {});
      setPreflight(null);
      setRefresh((value) => value + 1);
      onCompleted();
    } catch (reason) {
      setPreflight(null);
      if (reason instanceof ApiRequestError) {
        const code = reason.details?.reason_code ?? null;
        const uncertainDispatch = authorized && !["CLOUD_CONSENT_REQUIRED", "COST_ACKNOWLEDGEMENT_REQUIRED", "PREFLIGHT_CHANGED", "NO_QUALIFIED_MODEL", "CREDENTIAL_MISSING", "ROUTE_UNREACHABLE", "PRODUCTION_ROUTE_UNAVAILABLE"].includes(code ?? "");
        if (uncertainDispatch || code === "DISPATCH_AMBIGUOUS" || code === "EXECUTION_ALREADY_DISPATCHED") setDispatchBlocked(true);
        setActionError(deepAnalysisRunErrorCopy(uncertainDispatch ? "DISPATCH_AMBIGUOUS" : code, reason.details?.availability ?? ""));
      } else {
        if (authorized) setDispatchBlocked(true);
        setActionError(deepAnalysisRunErrorCopy(authorized ? "DISPATCH_AMBIGUOUS" : null, ""));
      }
    } finally {
      setBusy(false);
    }
  }

  // A missing or partial projection must never break the Content page; the
  // panel simply reports that Deep Analysis is unavailable.
  const status = data?.deep_analysis?.status;
  const result = data?.deep_analysis?.result;
  const durableCitations = result?.evidence_citation_status === "DURABLE_EVIDENCE_VERIFIED";
  const availability = status?.availability;
  const statusRead = typeof availability === "string" && [
    "AVAILABLE", "UNAVAILABLE", "NOT_REQUESTED", "NOT_QUALIFIED",
    "CONTENT_UNAVAILABLE", "SCORING_UNAVAILABLE", "EVIDENCE_UNAVAILABLE",
    "CLOUD_CONSENT_REQUIRED", "FAILED",
  ].includes(availability) && typeof status?.qualified === "boolean"
    && (status?.production_eligible === undefined || typeof status.production_eligible === "boolean")
    && (status?.consent_required === undefined || typeof status.consent_required === "boolean");
  const canRun = !error && statusRead && (status?.production_eligible ?? status?.qualified) === true && !busy && !dispatchBlocked && !preflight;

  return (
    <Panel title={t("Deep Analysis")}>
      <p className="hint">
        {t("Summary explains what this content says. Deep Analysis is a separate, on-demand action for the conclusions, evidence, uncertainty, what it means for you, and what to investigate next.")}
      </p>
      {error ? <ErrorState error={error} code={errorCode} onReload={reload} hideRawMessage deepAnalysisSurface /> : null}
      {actionError ? (
        <p className="semantic-state state-neutral">{t(actionError)}</p>
      ) : null}
      {error ? null : !data ? <p role="status" aria-live="polite">{t("Reading Deep Analysis status…")}</p> : !statusRead ? <ErrorState error="" code="READ_RESPONSE_INVALID" onReload={reload} hideRawMessage /> : result ? (
        <div className="summary-note deep-analysis-result">
          <div className="reading-meta">
            <Status value="AVAILABLE" />
            <span>{result.output_language}</span>
            <span>{humanDate(result.generated_at)}</span>
          </div>
          {DEEP_ANALYSIS_ROLE_ORDER.map((role) => {
            const claims = result.roles.filter((item) => item.role === role);
            if (claims.length === 0) return null;
            return (
              <section className="intelligence-section" key={role}>
                <p className="section-label">{t(deepAnalysisRoleLabel(role))}</p>
                <ul>
                  {claims.map((claim, index) => (
                    <li key={`${role}-${index}`}>
                      <p>{claim.text}</p>
                      {durableCitations ? (
                        <p className="reading-meta">
                          {(claim.evidence_ids ?? []).map((id, citationIndex) => (
                            <a href={`#content-evidence-${encodeURIComponent(id)}`} key={id}>
                              {t("Evidence")} {citationIndex + 1}
                            </a>
                          ))}
                        </p>
                      ) : null}
                      {durableCitations && claim.language_validation === "UNCERTAIN" ? (
                        <p className="hint">{t("Output language could not be fully verified.")}</p>
                      ) : null}
                      {claim.confidence ? (
                        <p className="hint">
                          {t("Confidence")}: {t(deepAnalysisConfidenceCopy(claim.confidence))}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
          <p className="hint">
            {t(durableCitations
              ? "Evidence citations have been verified against this Content’s original transcript."
              : "Per-claim Evidence citations are not shown yet. Deep Analysis never presents an unverified reference as an authoritative citation.")}
          </p>
        </div>
      ) : (
        <div className="semantic-state state-neutral">
          <span className="status status-neutral">
            <DeepAnalysisStatusLabel value={availability!} />
          </span>
          <p>{t(deepAnalysisReasonCopy(availability!, status?.reason_code ?? null))}</p>
        </div>
      )}
      {(error || !statusRead ? [] : status?.routes ?? []).map((route) => (
        <div className="semantic-state state-neutral" key={route.route_id}>
          <p>{route.provider_id} · {route.model_id}</p>
          <p>{t(route.configured ? "Route configured" : "Route not configured")} · {t(route.credential_configured ? "Credential available" : "Credential missing")}</p>
          <p>{t(route.reachability === "REACHABLE" ? "Provider reachable" : route.reachability === "NOT_CHECKED" ? "Reachability not checked" : "Provider unavailable")}</p>
          <p>{t(qualificationCopy(route.qualification_status))} · {t(route.production_eligible ? "Eligible for an explicit run" : "Production activation unavailable")}</p>
        </div>
      ))}
      {preflight ? (
        <div className="semantic-state state-neutral" role="region" aria-label={t("Cloud Deep Analysis preflight")}>
          <p>{t("You selected a cloud route for this Content.")}</p>
          <p>{preflight.provider_id} · {preflight.model_id}</p>
          <p>{t(preflight.credential_configured ? "Credential available" : "Credential missing")} · {t(qualificationCopy(preflight.qualification_status))}</p>
          <p>{t("Only selected original Evidence leaves this device. Full transcript mode is unavailable.")}</p>
          <p>{t(costDisclosureCopy(preflight.cost.state))}</p>
          <p>{t("Input characters")}: {preflight.cost.input_characters}</p>
          <p>{t("This approval applies only to this execution.")}</p>
          <label className="deep-analysis-consent"><input type="checkbox" checked={costAcknowledged} onChange={(event) => setCostAcknowledged(event.target.checked)} />{t("I acknowledge the unknown cost for this execution.")}</label>
          <div className="reading-meta">
            <button className="button button-primary" type="button" disabled={busy || !costAcknowledged || !preflight.credential_configured || preflight.qualification_status !== "QUALIFIED" || preflight.data_egress_mode !== "SELECTED_EVIDENCE_ONLY"} onClick={() => run(preflight)}>{t("Authorize this cloud run")}</button>
            <button className="button button-secondary" type="button" disabled={busy} onClick={() => { setPreflight(null); setCostAcknowledged(false); }}>{t("Cancel cloud run")}</button>
          </div>
        </div>
      ) : null}
      <div className="reading-meta">
        <button
          type="button"
          className="button button-primary"
          onClick={() => run()}
          disabled={!canRun}
        >
          {busy ? t("Working…") : t("Run Deep Analysis")}
        </button>
        {!error && statusRead && status?.qualified === false ? (
          <span className="hint">
            {t("Unavailable until a model is qualified for Deep Analysis.")}
          </span>
        ) : null}
      </div>
      <DeepAnalysisPublishAction
        key={`${videoId}:${result?.result_identity ?? "none"}`}
        videoId={videoId}
        resultIdentity={!error && statusRead && durableCitations ? result?.result_identity ?? null : null}
      />
    </Panel>
  );
}

function DeepAnalysisPublishAction({ videoId, resultIdentity }: { videoId: string; resultIdentity: string | null }) {
  const { t } = useUiLanguage();
  type PublishState = { state: string; result_identity?: string; relative_path?: string };
  const path = `/videos/${videoId}/deep-analysis/obsidian`;
  const { data, error, errorCode, reload } = useRemote<{ publish: PublishState }>(path);
  const [outcome, setOutcome] = useState<PublishState | null>(null);
  const [busy, setBusy] = useState(false);
  const status = data?.publish;
  const canPublish = !busy && resultIdentity !== null && status?.state === "AVAILABLE" && status.result_identity === resultIdentity;
  const copy: Record<string, string> = {
    NO_VAULT: "No Obsidian vault is configured.",
    RESULT_INELIGIBLE: "Only a verified durable Deep Analysis result can be published.",
    RESULT_CHANGED: "The Deep Analysis result changed. Reopen this Content before publishing.",
    PUBLISHED: "Published to Obsidian.",
    UPDATED: "Updated in Obsidian.",
    UNCHANGED: "The Obsidian note is already up to date.",
    WRITE_FAILED: "The write did not complete. Check vault permissions, paths, or file conflicts and retry.",
  };
  const state = outcome?.state ?? (status?.state === "AVAILABLE" && resultIdentity !== null && status.result_identity !== resultIdentity ? "RESULT_CHANGED" : status?.state);
  async function publish() {
    if (!canPublish) return;
    setBusy(true);
    setOutcome(null);
    try {
      const response = await post<{ publish: PublishState }>(path, { result_identity: resultIdentity });
      setOutcome(response.publish);
    } catch (reason) {
      setOutcome({ state: reason instanceof ApiRequestError ? reason.code : "WRITE_FAILED" });
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="deep-analysis-publish">
      <button type="button" className="button button-secondary" onClick={publish} disabled={!canPublish}>
        {busy ? t("Working…") : t("Publish to Obsidian")}
      </button>
      <p className="hint">{t("Publishing updates the managed note. Your My thoughts section is preserved.")}</p>
      {error && <ErrorState error={error} code={errorCode} onReload={reload} hideRawMessage deepAnalysisSurface />}
      {state && state !== "AVAILABLE" ? <p role="status" className="hint">{t(copy[state] ?? copy.WRITE_FAILED)}</p> : null}
      {outcome?.relative_path ? <p className="hint deep-analysis-publish-path">{outcome.relative_path}</p> : null}
    </div>
  );
}

function ContentEvidencePanel(
  {
    videoId,
    sourceUrl,
    refresh,
    highlightedEvidenceId,
    externalTranslations,
    onTranslateSuccess,
    onEvidenceLoaded,
  }: {
    videoId: string;
    sourceUrl: string | null;
    refresh: number;
    highlightedEvidenceId?: string | null;
    externalTranslations?: Record<string, { excerpt: string; language: "zh-CN" | "en" }>;
    onTranslateSuccess?: (evidenceId: string, excerpt: string, lang: "zh-CN" | "en") => void;
    onEvidenceLoaded?: (items: ContentEvidence[]) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const { data, error, errorCode, reload } = useRemote<{ evidence: ContentEvidence[] }>(
    `/videos/${encodeURIComponent(videoId)}/evidence`,
    refresh,
  );
  const [selectedMode, setSelectedMode] = useState<EvidenceDisplayMode | null>(null);
  const [evidenceVerbatim, setEvidenceVerbatim] = useState(false);
  const [translationBusy, setTranslationBusy] = useState<string | null>(null);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [createdTranslations, setCreatedTranslations] = useState<Record<
    string,
    { excerpt: string; language: "zh-CN" | "en" }
  >>({});
  useEffect(() => {
    if (data?.evidence && onEvidenceLoaded) {
      onEvidenceLoaded(data.evidence);
    }
  }, [data, onEvidenceLoaded]);
  const evidencePanelTitle = data?.evidence?.some(item => item.locator_type === "TEXT_RANGE") ? "Evidence · source text" : "Evidence · source transcript";
  if (error) {
    return (
      <Panel id="section-evidence" icon="shield-check" title={evidencePanelTitle}>
        <p className="hint">{t("Canonical Evidence could not be loaded. The Summary remains available with its own recorded references.")}</p>
        <ErrorState error={error} code={errorCode} onReload={reload} hideRawMessage />
      </Panel>
    );
  }
  if (!data) {
    return <Panel id="section-evidence" icon="shield-check" title={evidencePanelTitle}><Empty>Loading canonical Evidence…</Empty></Panel>;
  }
  const evidence = data.evidence ?? [];
  const collapsedEvidenceLines = evidence.reduce(
    (sum, item) => sum + cleanCaptionText(item.original_excerpt).collapsedCount,
    0,
  );
  const hasPreferredTranslation = evidence.some((item) => {
    const local = externalTranslations?.[item.evidence_id] ?? createdTranslations[item.evidence_id];
    const language = local?.language ?? item.translated_language;
    const excerpt = local?.excerpt ?? item.translated_excerpt;
    return Boolean(
      excerpt
      && language === item.translation_target_language
      && !evidenceSourceMatchesTarget(item.source_language, item.translation_target_language),
    );
  });
  const mode = selectedMode ?? (hasPreferredTranslation ? "译文" : "原文");
  const generateTranslation = async (item: ContentEvidence) => {
    setTranslationBusy(item.evidence_id);
    setTranslationError(null);
    try {
      const result = await post<{
        evidence_id: string;
        translated_excerpt: string | null;
        translated_language: "zh-CN" | "en" | null;
        translation_target_language: "zh-CN" | "en";
      }>(
        `/videos/${encodeURIComponent(videoId)}/evidence/${encodeURIComponent(item.evidence_id)}/translation`,
        {},
      );
      if (
        result.evidence_id !== item.evidence_id
        || !result.translated_excerpt
        || result.translated_language !== result.translation_target_language
      ) {
        throw new Error("The local translation response is incomplete.");
      }
      setCreatedTranslations((current) => ({
        ...current,
        [item.evidence_id]: {
          excerpt: result.translated_excerpt!,
          language: result.translated_language!,
        },
      }));
      onTranslateSuccess?.(item.evidence_id, result.translated_excerpt!, result.translated_language!);
      setSelectedMode("译文");
    } catch {
      setTranslationError("Could not create a verified local translation. Original Evidence is still available.");
    } finally {
      setTranslationBusy(null);
    }
  };
  return (
    <Panel id="section-evidence" icon="shield-check" title={evidencePanelTitle}>
      {evidence.length
        ? (
          <div className="evidence-trace-list">
            <CaptionCleanBar
              collapsedCount={collapsedEvidenceLines}
              showVerbatim={evidenceVerbatim}
              onToggle={() => setEvidenceVerbatim(current => !current)}
            />
            {evidence.map((item, idx) => {
              const local = externalTranslations?.[item.evidence_id] ?? createdTranslations[item.evidence_id];
              const translatedExcerpt = local?.excerpt ?? item.translated_excerpt;
              const translatedLanguage = local?.language ?? item.translated_language;
              const target = item.translation_target_language;
              const sourceMatchesTarget = evidenceSourceMatchesTarget(
                item.source_language,
                target,
              );
              const translationAvailable = Boolean(
                translatedExcerpt
                && translatedLanguage === target
                && !sourceMatchesTarget,
              );
              const showTranslation = mode !== "原文";
              const showOriginal = mode !== "译文" || !translationAvailable;
              const isTargeted = highlightedEvidenceId === item.evidence_id;
              return (
                <article
                  className={`evidence-item evidence-trace-item${isTargeted ? " is-targeted-evidence" : ""}`}
                  id={`content-evidence-${encodeURIComponent(item.evidence_id)}`}
                  data-content-id={videoId}
                  key={item.evidence_id}
                >
                  <div className="reading-meta">
                    <span className="tabular-nums">#{idx + 1}</span>
                    <strong className="tabular-nums">
                      {item.locator_type === "TEXT_RANGE" ? textLineRange(item.start_line, item.end_line, t) : timestampRange(item.start_ms, item.end_ms)}
                    </strong>
                    <span>{t("Source language")}: {item.source_language} · {t(item.locator_type === "TEXT_RANGE" ? "Original source text" : evidenceLineageLabel(item.lineage_kind))}</span>
                    {isTargeted && <span className="targeted-citation-pill">{t("Targeted citation")}</span>}
                  </div>
                  <div className="segmented evidence-display-modes" role="group" aria-label={t("Evidence presentation mode")}>
                    {(["译文", "双语", "原文"] as const).map((option) => (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={mode === option}
                        className={mode === option ? "active" : ""}
                        onClick={() => setSelectedMode(option)}
                      >
                        {language === "en" ? ({ "译文": "Translation", "双语": "Bilingual", "原文": "Original" } as const)[option] : option}
                      </button>
                    ))}
                  </div>
                  {showTranslation
                    ? (
                      <div>
                        <strong>{t("Translation")} · {target}</strong>
                        {translationAvailable
                          ? <blockquote>{evidenceVerbatim ? translatedExcerpt : cleanTranslatedCaptionText(translatedExcerpt!)}</blockquote>
                          : sourceMatchesTarget
                          ? <p className="hint">{t("Original Evidence already matches the requested output language.")}</p>
                          : (
                            <>
                              <p className="hint">{t("Translation unavailable. Original Evidence remains authoritative.")}</p>
                              {translationBusy === null
                                ? (
                                  <button
                                    type="button"
                                    className="button button-secondary button-small"
                                    onClick={() => void generateTranslation(item)}
                                  >
                                    {t("Generate translation")}
                                  </button>
                                )
                                : translationBusy === item.evidence_id
                                ? <p className="hint" role="status">{t("Generating a local translation…")}</p>
                                : null}
                            </>
                          )}
                      </div>
                    )
                    : null}
                  {showOriginal
                    ? (
                      <div>
                        <strong>{t("Original · authoritative source")} · {item.source_language}</strong>
                        <blockquote>{evidenceVerbatim ? item.original_excerpt : cleanCaptionText(item.original_excerpt).text}</blockquote>
                      </div>
                    )
                    : null}
                  {mode === "原文" && !translationAvailable && !sourceMatchesTarget
                    ? <p className="hint">{t("Translation unavailable.")}</p>
                    : null}
                  {translationError ? <p className="hint" role="alert">{t(translationError)}</p> : null}
                  <div className="evidence-card-footer">
                    {sourceUrl
                      ? (
                        <a
                          className="button button-ghost button-small evidence-source-link"
                          href={videoAt(sourceUrl, item.start_ms)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {t(item.start_ms === null ? "Open original" : "Open original at timestamp")}
                        </a>
                      )
                      : <p className="hint">{t("Source URL unavailable.")}</p>}
                    <details className="provenance">
                      <summary>{t("Citation details")}</summary>
                      <p>{t("Source position")}: {item.locator_type === "TEXT_RANGE" ? textLineRange(item.start_line, item.end_line, t) : timestampRange(item.start_ms, item.end_ms)}</p>
                      <p>{t("Provenance")}: {t(item.locator_type === "TEXT_RANGE" ? "Original source text" : evidenceLineageLabel(item.lineage_kind))} · {t(evidenceRoleLabel(item.role))}</p>
                      <small>{item.evidence_id} · {item.artifact_id} · {item.created_at ? humanDate(item.created_at) : "Timestamp unavailable"}</small>
                    </details>
                  </div>
                </article>
              );
            })}
          </div>
        )
        : <Empty>No available, verified canonical transcript Evidence is recorded for this Content.</Empty>}
    </Panel>
  );
}
function Topics({
  refresh,
  handoffSeq,
  targetTopicId,
  latestSelectedRef,
  consumeOriginRestore,
  onOpenContent,
  onAskTopicResearch,
  onBrowseTopicContent,
  onBrowseTopicIntelligence,
}: {
  refresh: number;
  handoffSeq?: number;
  targetTopicId?: string | null;
  latestSelectedRef?: { current: string | null };
  consumeOriginRestore?: () => string | null;
  onOpenContent?: (videoId: string) => void;
  onAskTopicResearch?: (topicName: string) => void;
  onBrowseTopicContent?: (topicName: string, channelKey?: string) => void;
  onBrowseTopicIntelligence?: (topicId: string) => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const list = useRemote<{ topics: Topic[] }>("/topics", refresh, undefined, true, true);
  const [selected, setSelected] = useState<string | null>(
    () => targetTopicId ?? consumeOriginRestore?.() ?? null,
  );
  if (latestSelectedRef) {
    latestSelectedRef.current = selected;
  }
  const [pendingClusterName, setPendingClusterName] = useState(() =>
    consumePendingTopicClusterName(),
  );
  useEffect(() => {
    if (targetTopicId) setSelected(targetTopicId);
  }, [targetTopicId]);
  useEffect(() => {
    const nextName = consumePendingTopicClusterName();
    if (nextName) setPendingClusterName(nextName);
  }, [handoffSeq]);
  useEffect(() => {
    if (!pendingClusterName || !list.data?.topics) return;
    const targetName = pendingClusterName.trim();
    setPendingClusterName("");
    const matched = list.data.topics.find((item) => item.name.trim() === targetName);
    if (matched) {
      setSelected(matched.topic_id);
    } else {
      onBrowseTopicContent?.(targetName, "ALL");
    }
  }, [pendingClusterName, list.data?.topics]);
  const detail = useRemote<{ topic: Topic }>(
    selected ? `/topics/${selected}` : "/topics",
    refresh,
    undefined,
    true,
    true,
  );
  const failedReads = [list, detail].filter(read => read.error);
  if (failedReads.length) {
    return <ErrorState error={failedReads[0].error ?? ""} code={failedReads[0].errorCode}
      onReload={() => failedReads.forEach(read => read.reload())} />;
  }
  if (!list.data) return <Empty>Loading Topics…</Empty>;
  if (!selected) {
    return (
      <>
        {list.data.topics.length
          ? (
            <div className="compact-list content-media-list">
              {sortTopicsNewestFirst(list.data.topics).map((topic) => {
                const evo = readTopicAiEvolution(topic.ai_evolution);
                return (
                  <button
                    className="list-row content-media-row"
                    key={topic.topic_id}
                    onClick={() => setSelected(topic.topic_id)}
                  >
                    <span className="content-media-lead">
                      <span className="provider-glyph provider-local" aria-hidden="true">
                        <PhosphorIcon name="stack" weight={topic.pinned ? "fill" : "regular"} size={16} />
                      </span>
                      <span className="content-media-copy">
                        <strong>{topic.name}</strong>
                        {evo?.latest_headline_zh ? (
                          <span className="content-ai-headline">{evo.latest_headline_zh}</span>
                        ) : null}
                        <small className="tabular-nums">
                          {evo && evo.video_count > 0
                            ? [
                                evo.latest_published_at
                                  ? zh
                                    ? `最近更新 ${humanDate(evo.latest_published_at)}`
                                    : `Updated ${humanDate(evo.latest_published_at)}`
                                  : null,
                                zh
                                  ? `${evo.video_count} 条内容 · ${evo.must_watch_count} 条必看`
                                  : `${evo.video_count} items · ${evo.must_watch_count} must-watch`,
                                evo.recent_7d_count > 0
                                  ? zh
                                    ? `近7天 +${evo.recent_7d_count}`
                                    : `+${evo.recent_7d_count} in 7d`
                                  : null,
                                evo.avg_score !== null
                                  ? zh
                                    ? `均分 ${evo.avg_score.toFixed(1)}`
                                    : `Avg ${evo.avg_score.toFixed(1)}`
                                  : null,
                                evo.source_channels.length > 0
                                  ? evo.source_channels.join(" / ")
                                  : null,
                              ]
                                .filter(Boolean)
                                .join(" · ")
                            : `${t("Current understanding")}: ${t(statusLabel(topic.current_state))}`}
                        </small>
                      </span>
                    </span>
                    <Status value={topic.pinned ? "PINNED" : topic.lifecycle} />
                  </button>
                );
              })}
            </div>
          )
          : <Empty>No Topics yet.</Empty>}
      </>
    );
  }
  if (!detail.data?.topic) return <Empty>Loading Topic detail…</Empty>;
  const topic = detail.data.topic;
  const evo = readTopicAiEvolution(topic.ai_evolution);
  const hasEvoEntries = Boolean(evo && evo.entries.length > 0);
  const availableIntelCount = new Set(
    topic.contributions
      .filter((c) => c.available)
      .map((c) => c.intelligence_id),
  ).size;
  const contributionNodes = topic.contributions.map((contribution) => (
    <article key={`${contribution.intelligence_id}:${contribution.claim_kind}`}>
      <Claim kind={contribution.claim_kind} />{" "}
      <Status value={contribution.available ? contribution.state : "UNAVAILABLE"} />
      <p>
        {contribution.available
          ? t("A current contribution supports this topic.")
          : t("Some supporting information is no longer available.")}
      </p>
      <details className="provenance">
        <summary>
          {t("Technical evidence references")} ({contribution.evidence_ids.length})
        </summary>
        <p className="tabular-nums">{contribution.evidence_ids.join(", ")}</p>
      </details>
    </article>
  ));

  return (
    <div className="dashboard-stack">
      <button className="button button-ghost" onClick={() => setSelected(null)}>
        <PhosphorIcon name="arrow-left" size={14} />
        {t("Back to Topics")}
      </button>
      <Panel title={topic.name} icon="stack">
        {evo && evo.video_count > 0 ? (
          <p className="weekly-funnel-strip tabular-nums">
            <span>
              {zh
                ? `已聚合 ${evo.video_count} 条相关内容 · ${evo.must_watch_count} 条必看干货${evo.recent_7d_count > 0 ? ` · 近7天 +${evo.recent_7d_count}` : ""}${evo.avg_score !== null ? ` · 平均评分 ${evo.avg_score.toFixed(1)}` : ""}`
                : `${evo.video_count} items · ${evo.must_watch_count} must-watch${evo.recent_7d_count > 0 ? ` · +${evo.recent_7d_count} in 7d` : ""}${evo.avg_score !== null ? ` · Avg ${evo.avg_score.toFixed(1)}` : ""}`}
            </span>{" "}
            {evo.source_channels.length > 0 ? <span>{evo.source_channels.join(" · ")}</span> : null}
          </p>
        ) : null}
        <h3>{t("Current understanding")}</h3>
        {hasEvoEntries && evo ? (
          <>
            <p className="summary-copy">{evo.synthesis_zh || evo.latest_headline_zh}</p>
            <p className="hint">
              {evo.independence_summary_zh ||
                (evo.source_channels.length >= 2
                  ? zh
                    ? `已汇聚 ${evo.source_channels.join("、")} 共 ${evo.source_channels.length} 个独立来源交叉印证（共 ${evo.video_count} 篇内容）。`
                    : `Cross-referenced across ${evo.source_channels.length} independent sources (${evo.video_count} items).`
                  : zh
                    ? `当前基于 ${evo.video_count} 篇已提炼内容持续追踪。`
                    : `Grounded in ${evo.video_count} distilled items.`)}
            </p>
            {evo.top_opportunities_zh.length > 0 ? (
              <div className="topic-opp-pills">
                {evo.top_opportunities_zh.map((opp, idx) => (
                  <span key={`top-opp:${idx}`} className="ai-basis-pill">
                    {zh ? `高优切口：${opp}` : opp}
                  </span>
                ))}
              </div>
            ) : null}
            {evo.channel_breakdown.length > 0 && onBrowseTopicContent ? (
              <div
                className="ai-suggested-pills topic-channel-breakdown tabular-nums"
                role="group"
                aria-label={zh ? "按频道筛选本专题干货" : "Filter topic by channel"}
              >
                {evo.channel_breakdown.map((ch) => (
                  <button
                    key={ch.channel_key}
                    type="button"
                    className="ai-question-chip tabular-nums"
                    onClick={() => onBrowseTopicContent(topic.name, ch.channel_key)}
                  >
                    {zh
                      ? `${ch.channel_label} · ${ch.video_count} 篇${ch.must_watch_count > 0 ? `（${ch.must_watch_count} 必看）` : ""}`
                      : `${ch.channel_label} · ${ch.video_count}${ch.must_watch_count > 0 ? ` (${ch.must_watch_count} must-watch)` : ""}`}
                  </button>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <>
            <p>{t(statusLabel(topic.current_state)).trim()}{zh ? "。" : "."}</p>
            <p>
              {t(topic.independence === "UNKNOWN"
                ? "Not enough reliable information yet to determine how independent the supporting sources are."
                : "This understanding is based on the available supporting sources.")}
            </p>
          </>
        )}
        <div className="button-row">
          {onAskTopicResearch ? (
            <button
              type="button"
              className="button button-primary"
              onClick={event => {
                pulseCelebration(event.currentTarget);
                onAskTopicResearch(topic.name);
              }}
            >
              <PhosphorIcon name="sparkle" size={14} />
              {zh ? "围绕本专题跨视频提问" : "Ask AI across this topic"}
            </button>
          ) : null}
          {evo && evo.video_count > 0 && onBrowseTopicContent ? (
            <button
              type="button"
              className="button button-secondary tabular-nums"
              onClick={event => {
                pulseCelebration(event.currentTarget);
                onBrowseTopicContent(topic.name, "ALL");
              }}
            >
              <PhosphorIcon name="funnel" size={14} />
              {zh
                ? `在内容库筛选本专题 (${evo.video_count})`
                : `Filter in Content (${evo.video_count})`}
            </button>
          ) : null}
          {availableIntelCount > 0 && onBrowseTopicIntelligence ? (
            <button
              type="button"
              className="button button-secondary tabular-nums"
              onClick={event => {
                pulseCelebration(event.currentTarget);
                onBrowseTopicIntelligence(topic.topic_id);
              }}
            >
              <PhosphorIcon name="shield-check" size={14} />
              {zh
                ? `查看本专题验证洞察 (${availableIntelCount})`
                : `View verified insights (${availableIntelCount})`}
            </button>
          ) : null}
          <button
            className="button button-secondary"
            onClick={event => {
              pulseCelebration(event.currentTarget);
              void post(`/topics/${topic.topic_id}/pin`, { pinned: !topic.pinned })
                .then(() => setSelected(null));
            }}
          >
            <PhosphorIcon name="push-pin" weight={topic.pinned ? "fill" : "regular"} size={14} />
            {t(topic.pinned ? "Unpin Topic" : "Pin Topic")}
          </button>
        </div>
        {evo?.obsidian_markdown ? (
          <TopicObsidianExportBar
            topicName={topic.name}
            obsidianMarkdown={evo.obsidian_markdown}
            evolution={evo}
          />
        ) : null}
      </Panel>
      {hasEvoEntries && evo ? (
        <Panel title={zh ? "专题核心脉络与时间演进" : "Topic Insight Evolution"} icon="sparkle">
          <div className="topic-evolution-list">
            {evo.entries.map((entry) => (
              <article className="topic-evolution-card" key={entry.video_id}>
                <div className="topic-evolution-head tabular-nums">
                  <button
                    type="button"
                    className="topic-evolution-title-btn"
                    onClick={() => onOpenContent?.(entry.video_id)}
                  >
                    <strong>{entry.title}</strong>
                  </button>
                  <div className="content-row-trailing">
                    {entry.source_basis === "METADATA_ONLY" ? (
                      <span className="ai-basis-pill is-compact">
                        {zh ? "简介速览" : "Metadata"}
                      </span>
                    ) : null}
                    <span
                      className={`ai-score-pill is-compact tabular-nums ${
                        entry.score >= 8 ? "ai-score-high" : entry.score >= 5 ? "ai-score-mid" : "ai-score-noise"
                      }`}
                    >
                      <strong>{entry.score.toFixed(1)}</strong>
                    </span>
                  </div>
                </div>
                <small className="hint tabular-nums">
                  {[entry.channel_name, entry.published_at ? humanDate(entry.published_at) : null]
                    .filter(Boolean)
                    .join(" · ")}
                </small>
                <p className="topic-evolution-headline">{entry.headline_zh}</p>
                {entry.summary_zh && entry.summary_zh.trim() !== entry.headline_zh.trim() ? (
                  <p className="summary-copy">{entry.summary_zh}</p>
                ) : null}
                {entry.product_opportunities_zh.length > 0 || entry.business_opportunities_zh.length > 0 ? (
                  <div className="topic-opp-pills">
                    {entry.product_opportunities_zh.slice(0, 2).map((opp, idx) => (
                      <span key={`p:${idx}`} className="ai-basis-pill">
                        {zh ? `产品切口：${opp}` : opp}
                      </span>
                    ))}
                    {entry.business_opportunities_zh.slice(0, 2).map((opp, idx) => (
                      <span key={`b:${idx}`} className="ai-basis-pill">
                        {zh ? `变现模型：${opp}` : opp}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </Panel>
      ) : null}
      <Panel title="Evidence" icon="shield-check">
        {topic.contributions.length
          ? hasEvoEntries
            ? (
              <details className="topic-raw-contributions legacy-model-diagnostics">
                <summary>
                  {zh
                    ? `底层技术证据溯源记录 (${topic.contributions.length})`
                    : `Technical contribution records (${topic.contributions.length})`}
                </summary>
                {contributionNodes}
              </details>
            )
            : contributionNodes
          : <Empty>No current supporting information.</Empty>}
      </Panel>
      <Panel title="Timeline" icon="clock">
        {hasEvoEntries && evo ? (
          <div className="timeline">
            {evo.entries.slice(0, 10).map((entry) => (
              <div className="timeline-item" key={entry.video_id}>
                <span className="timeline-dot" aria-hidden="true" />
                <div className="timeline-copy">
                  <div className="topic-timeline-meta tabular-nums">
                    <strong>{entry.published_at ? humanDate(entry.published_at) : "—"}</strong>
                    <span className="ai-basis-pill is-compact">
                      {entry.recommendation_tier === "MUST_WATCH"
                        ? zh
                          ? "必看节点"
                          : "Must-watch"
                        : zh
                          ? "收录节点"
                          : "Indexed"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="topic-evolution-title-btn tabular-nums"
                    onClick={() => onOpenContent?.(entry.video_id)}
                  >
                    {`${entry.channel_name || (zh ? "来源" : "Source")} · 《${entry.title}》（${entry.score.toFixed(1)}）`}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : topic.timeline.length
          ? (
            <div className="timeline">
              {topic.timeline.map((event) => (
                <div className="timeline-item" key={event.event_id}>
                  <span className="timeline-dot" aria-hidden="true" />
                  <div className="timeline-copy">
                    <strong className="tabular-nums">{humanDate(event.created_at)}</strong>
                    <Status value={event.state} />
                  </div>
                </div>
              ))}
            </div>
          )
          : <Empty>No historical events.</Empty>}
      </Panel>
      <Panel title="Related Topics" icon="stack">
        {(() => {
          const mergedRelated: { id: string; name?: string; videoCount?: number }[] = [];
          const seen = new Set<string>();
          for (const rel of topic.relations) {
            if (!rel.related_topic_id || seen.has(rel.related_topic_id)) continue;
            seen.add(rel.related_topic_id);
            mergedRelated.push({
              id: rel.related_topic_id,
              name: rel.related_topic_name,
            });
          }
          for (const sib of evo?.related_topics ?? []) {
            if (!sib.topic_id || seen.has(sib.topic_id)) continue;
            seen.add(sib.topic_id);
            mergedRelated.push({
              id: sib.topic_id,
              name: sib.name,
              videoCount: sib.video_count,
            });
          }
          if (!mergedRelated.length) return <Empty>No related Topics.</Empty>;
          return (
            <div className="ai-suggested-pills tabular-nums">
              {mergedRelated.map((rel) =>
                rel.name ? (
                  <button
                    type="button"
                    className="ai-question-chip"
                    key={rel.id}
                    onClick={() => setSelected(rel.id)}
                  >
                    {rel.videoCount && rel.videoCount > 0
                      ? zh
                        ? `${rel.name} · ${rel.videoCount} 篇`
                        : `${rel.name} · ${rel.videoCount} items`
                      : rel.name}
                  </button>
                ) : (
                  <p key={rel.id}>{t("Related topic")}</p>
                ),
              )}
            </div>
          );
        })()}
      </Panel>
    </div>
  );
}

function validSourceReadIdentity(value: unknown): boolean {
  if (!validFollowingSourceRead(value)) return false;
  const source = value as Partial<Source>;
  return typeof source.source_id === "string" && !!source.source_id.trim()
    && typeof source.canonical_url === "string" && typeof source.enabled === "boolean";
}
function validSourcesRead(value: unknown): boolean {
  if (!value || typeof value !== "object" || !("sources" in value)) return false;
  return Array.isArray(value.sources) && value.sources.every(validSourceReadIdentity)
    && new Set(value.sources.map(source => source.source_id)).size === value.sources.length;
}

function FollowingReadNotice({ reading, error, errorCode, onReload, detail = false }: {
  reading: boolean; error: string | null; errorCode?: string; onReload: () => void; detail?: boolean;
}) {
  const { t } = useUiLanguage();
  return <>
    {error && <div>
      <p className="hint">{t(detail ? "Source details could not be refreshed. Showing previously loaded details." : "The Following list could not be refreshed. Showing previously loaded sources.")}</p>
      <ErrorState error={error} code={errorCode} hideRawMessage onReload={reading ? undefined : onReload} />
    </div>}
    {reading && <p role="status" className="hint">{t(detail ? "Refreshing source details…" : "Refreshing the Following list…")}</p>}
  </>;
}

function Sources(
  {
    refresh,
    onRefresh,
    targetSourceId,
    onAdd,
    onBrowseChannelContent,
    onAskChannelResearch,
  }: {
    refresh: number;
    onRefresh: () => void;
    targetSourceId?: string | null;
    onAdd: (provider: "YOUTUBE" | "LOCAL") => void;
    onBrowseChannelContent?: (channelKey: string) => void;
    onAskChannelResearch?: (channelKey: string) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const { data, error, errorCode, reading, reload } = useRemote<{
    sources: Source[];
    ai_signal_by_source?: unknown;
  }>("/sources", refresh, validSourcesRead, true, true);
  const [selected, setSelected] = useState<string | null>(targetSourceId ?? null);
  const [filter, setFilter] = useState("all");
  const [sortMode, setSortMode] = useState<"default" | "must_watch" | "avg_score">("default");
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowMessage, setRowMessage] = useState<string | null>(null);
  useEffect(() => {
    if (reading || !data?.sources.some(source => source.tracking?.checking)) return;
    const timer = setTimeout(onRefresh, 2000);
    return () => clearTimeout(timer);
  }, [data, reading]);
  useEffect(() => {
    const check = () => {
      if (document.visibilityState !== "hidden") {
        void post<{ checks?: unknown[] }>("/sources/check-stale", {})
          .then((res) => {
            if (!Array.isArray(res?.checks) || res.checks.length > 0) {
              onRefresh();
            }
          })
          .catch(() => {});
      }
    };
    check(); window.addEventListener("focus", check);
    return () => window.removeEventListener("focus", check);
  }, []);
  const creatorCapability = useCreatorFollowingCapability();
  const creatorFollowingWithdrawn = creatorCapability.known &&
    creatorCapability.capability !== null && !creatorCapability.capability.available;
  if (error && !data) return <ErrorState error={error} code={errorCode} onReload={reload} />;
  if (!data) return <Empty>Loading Sources…</Empty>;
  const followingSources = data.sources.filter(source => source.source_type !== "VIDEO_URL");
  const aiSignals = readSourceAiSignalMap(data.ai_signal_by_source);
  const hasAiSignals = Object.keys(aiSignals).length > 0;
  const topLevelSources = followingSources.filter(
    source => !source.tracking_parent_source_ids?.length,
  );
  const totalSignalSummary = hasAiSignals
    ? topLevelSources.reduce(
        (acc, src) => {
          const sig = aiSignals[src.source_id];
          if (sig) {
            acc.longForm += sig.long_form_count;
            acc.mustWatch += sig.must_watch_count;
            acc.shorts += sig.shorts_count;
          }
          return acc;
        },
        { longForm: 0, mustWatch: 0, shorts: 0 },
      )
    : null;
  const filteredFollowing = topLevelSources.filter(
    source =>
      filter === "all" ||
      (filter === "updates" && (source.tracking?.update_count ?? 0) > 0) ||
      (filter === "insights" && (source.insight_count ?? 0) > 0) ||
      (filter === "high_signal" && (aiSignals[source.source_id]?.must_watch_count ?? 0) >= 1) ||
      (filter === "attention" &&
        Boolean(
          (source.source_type === "CHANNEL" && !source.tracking) ||
            (source.provider === "BILIBILI" && source.tracking && creatorFollowingWithdrawn) ||
            source.last_error ||
            (source.tracking?.pending_count ?? 0) > 0 ||
            (source.tracking?.processing_count ?? 0) > 0 ||
            (source.tracking?.unavailable_count ?? 0) > 0,
        )) ||
      (filter === "paused" && !source.enabled),
  );
  const orderedFollowing =
    sortMode === "default"
      ? filteredFollowing
      : [...filteredFollowing].sort((a, b) => {
          const sigA = aiSignals[a.source_id];
          const sigB = aiSignals[b.source_id];
          if (sortMode === "must_watch") {
            const mwDiff = (sigB?.must_watch_count ?? -1) - (sigA?.must_watch_count ?? -1);
            if (mwDiff !== 0) return mwDiff;
            return (sigB?.avg_long_score ?? -1) - (sigA?.avg_long_score ?? -1);
          }
          const avgDiff = (sigB?.avg_long_score ?? -1) - (sigA?.avg_long_score ?? -1);
          if (avgDiff !== 0) return avgDiff;
          return (sigB?.must_watch_count ?? -1) - (sigA?.must_watch_count ?? -1);
        });
  return (
    <>
      {!selected && <FollowingReadNotice reading={reading} error={error} errorCode={errorCode} onReload={reload} />}
      {creatorFollowingWithdrawn && <p className="hint" role="status">{t("Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.")}</p>}
      <div className="page-actions">
        <button
          className="button button-primary"
          onClick={() => onAdd("YOUTUBE")}
        >
          {t("Add Source")}
        </button>
      </div>
      {rowMessage && <p role="status" aria-live="polite">{t(rowMessage)}</p>}
      {followingSources.length
        ? (
          <div className="source-list">
            <label className="field">{t("Following filter")}<select value={filter} onChange={event => setFilter(event.target.value)}>
              <option value="all">{t("All Following")}</option><option value="updates">{t("Has updates")}</option>
              <option value="insights">{t("Produces new insights")}</option>
              {hasAiSignals ? (
                <option value="high_signal">
                  {language === "zh-CN" ? "高干货产出（必看 ≥ 1）" : "High signal (must-watch ≥ 1)"}
                </option>
              ) : null}
              <option value="attention">{t("Needs attention")}</option>
              <option value="paused">{t("Paused")}</option>
            </select></label>
            {hasAiSignals &&
            topLevelSources.length > 1 &&
            totalSignalSummary &&
            totalSignalSummary.longForm > 0 ? (
              <div className="following-signal-overview tabular-nums">
                <span>
                  {language === "zh-CN"
                    ? `共 ${topLevelSources.length} 个订阅源 · 累计沉淀 ${totalSignalSummary.longForm} 篇长视频干货 · ${totalSignalSummary.mustWatch} 篇必看${totalSignalSummary.shorts > 0 ? ` · 已折叠 ${totalSignalSummary.shorts} 条 Shorts` : ""}`
                    : `${topLevelSources.length} sources · ${totalSignalSummary.longForm} long-form items · ${totalSignalSummary.mustWatch} must-watch`}
                </span>
                <div
                  className="segmented"
                  role="group"
                  aria-label={language === "zh-CN" ? "关注信源排序" : "Sort Following"}
                >
                  {(
                    [
                      ["default", language === "zh-CN" ? "默认顺序" : "Default"],
                      ["must_watch", language === "zh-CN" ? "必看产出优先" : "Most must-watch"],
                      ["avg_score", language === "zh-CN" ? "干货均分优先" : "Highest avg score"],
                    ] as const
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={sortMode === key}
                      className={sortMode === key ? "active" : ""}
                      onClick={() => setSortMode(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            {orderedFollowing.map((source) => {
              const sig = aiSignals[source.source_id] ?? null;
              const signalCopy =
                sig && sig.distilled_count > 0
                  ? language === "zh-CN"
                    ? `干货 ${sig.long_form_count}/${sig.total_videos}${sig.signal_rate_pct !== null ? ` (${sig.signal_rate_pct}%)` : ""} · 必看 ${sig.must_watch_count}${sig.avg_long_score !== null ? ` · 均分 ${sig.avg_long_score.toFixed(1)}` : ""}${sig.shorts_count > 0 ? ` · 折叠 ${sig.shorts_count} Shorts` : ""}`
                    : `Long-form ${sig.long_form_count}/${sig.total_videos}${sig.signal_rate_pct !== null ? ` (${sig.signal_rate_pct}%)` : ""} · Must-watch ${sig.must_watch_count}${sig.avg_long_score !== null ? ` · Avg ${sig.avg_long_score.toFixed(1)}` : ""}${sig.shorts_count > 0 ? ` · ${sig.shorts_count} Shorts folded` : ""}`
                  : null;
              return (
              <div className="list-row source-row" key={source.source_id} data-source-id={source.source_id}>
                <button
                  className="source-select"
                  onClick={() =>
                    setSelected(source.source_id)}
                >
                  <span className="content-media-lead">
                    <span
                      className={`provider-glyph provider-${(source.provider ?? "YOUTUBE").toLowerCase()}`}
                      aria-hidden="true"
                    >
                      <PhosphorIcon
                        name={source.provider === "LOCAL" ? "folder-open" : source.provider === "BILIBILI" ? "television" : "rss"}
                        size={16}
                      />
                    </span>
                    <span className="content-media-copy">
                      <strong>{source.provider === "LOCAL" ? t("Local library") : sourceLabel(source)}</strong>
                      <small>
                        {t(sourceSummary(source, creatorFollowingWithdrawn))} · {source.provider === "LOCAL" ? t("Local") : source.provider === "BILIBILI" ? t("Bilibili") : "YouTube"}
                      </small>
                      {signalCopy ? (
                        <span className="source-signal-strip tabular-nums">{signalCopy}</span>
                      ) : null}
                    </span>
                  </span>
                </button>
                <div className="source-actions">
                  {sig && sig.long_form_count > 0 && sig.channel_key && onBrowseChannelContent ? (
                    <button
                      type="button"
                      className="button button-secondary button-small tabular-nums"
                      onClick={() => onBrowseChannelContent(sig.channel_key)}
                    >
                      {language === "zh-CN"
                        ? `看干货 (${sig.long_form_count})`
                        : `Browse (${sig.long_form_count})`}
                    </button>
                  ) : null}
                  {sig && sig.long_form_count > 0 && sig.channel_key && onAskChannelResearch ? (
                    <button
                      type="button"
                      className="button button-ghost button-small"
                      onClick={() => onAskChannelResearch(sig.channel_key)}
                    >
                      {language === "zh-CN" ? "问此频道" : "Ask Q&A"}
                    </button>
                  ) : null}
                  {source.tracking &&
                    source.enabled &&
                    !source.tracking.checking &&
                    !(source.provider === "BILIBILI" && creatorFollowingWithdrawn) &&
                    [
                      "OFFLINE",
                      "NETWORK_UNAVAILABLE",
                      "PROVIDER_ERROR",
                      "RATE_LIMITED",
                      "UPDATE_GAP",
                      "CHECK_INCOMPLETE",
                    ].includes(source.tracking.health) && (
                      <button
                        type="button"
                        className="button button-primary button-small"
                        disabled={rowBusy !== null}
                        onClick={async () => {
                          setRowBusy(`check:${source.source_id}`);
                          setRowMessage(null);
                          try {
                            const result = await post<{ status?: string }>(
                              `/sources/${source.source_id}/check`,
                              { command_id: commandId() },
                            );
                            if (result.status === "CAPABILITY_UNAVAILABLE") {
                              setRowMessage(trackingCopy("CAPABILITY_UNAVAILABLE"));
                            } else {
                              setRowMessage(
                                language === "zh-CN"
                                  ? "已发起来源重检，最新状态即将刷新。"
                                  : "Source check started.",
                              );
                            }
                            onRefresh();
                          } catch {
                            setRowMessage("The source could not be checked. Try again later.");
                          } finally {
                            setRowBusy(null);
                          }
                        }}
                      >
                        {rowBusy === `check:${source.source_id}`
                          ? t("Checking…")
                          : language === "zh-CN"
                            ? "立即重检"
                            : "Retry check"}
                      </button>
                    )}
                  {source.tracking && <button className="button button-secondary" disabled={rowBusy !== null} onClick={async () => {
                    setRowBusy(source.source_id); setRowMessage(null);
                    try { await patch(`/sources/${source.source_id}`, { enabled: !source.enabled }); setRowMessage(source.enabled ? "Following paused. Existing content is preserved." : "Following resumed. New content will be checked while the app is running."); onRefresh(); }
                    catch { setRowMessage("The source could not be checked. Try again later."); }
                    finally { setRowBusy(null); }
                  }}>{t(rowBusy === source.source_id ? "Saving…" : source.enabled ? "Pause following" : "Resume following")}</button>}
                  {source.source_type === "CHANNEL" && !source.tracking ? <Status value="NEEDS_ATTENTION" /> : source.tracking
                    ? <Status
                        value={!source.enabled ? "PAUSED" : source.provider === "BILIBILI" && creatorFollowingWithdrawn ? "CAPABILITY_UNAVAILABLE" : source.tracking?.checking ? "RUNNING" : source.tracking?.health ?? "BASELINE_PENDING"}
                        label={!source.enabled ? "Monitoring is paused" : source.provider === "BILIBILI" && creatorFollowingWithdrawn ? "Continuous creator tracking is currently unavailable" : source.tracking?.checking ? "Checking…" : trackingCopy(source.tracking?.health ?? "BASELINE_PENDING", source.provider)}
                      />
                    : <Status
                        {...(source.provider === "BILIBILI"
                          ? contentStatus("BILIBILI", source.last_error?.code ?? "IMPORTED")
                          : { value: source.last_error?.code ?? (source.enabled ? "ENABLED" : "DISABLED"), label: undefined })}
                      />}
                  {source.provider === "LOCAL" ? <button className="button button-secondary" onClick={() => onAdd("LOCAL")}>{t("Import files")}</button> : <a
                    href={source.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("Open Source")}
                  </a>}
                </div>
              </div>
              );
            })}
          </div>
        )
        : (
          <Empty>
            <strong>{t("Set up your first Source")}</strong>
            <p>
              {t("Follow a YouTube channel to watch for new content. You can also import a single YouTube or Bilibili video, or a local file.")}
            </p>
            <button
              className="button button-primary"
              onClick={() => onAdd("YOUTUBE")}
            >
              {t("Add Source")}
            </button>
          </Empty>
        )}
      {selected && (
        <SourceDetail
          id={selected}
          refreshNotice={<FollowingReadNotice reading={reading} error={error} errorCode={errorCode} onReload={reload} />}
          onAddLocal={() => { setSelected(null); onAdd("LOCAL"); }}
          onClose={() => setSelected(null)}
          onRefresh={onRefresh}
        />
      )}
    </>
  );
}
function SourceForm(props: Parameters<typeof ExistingSourceForm>[0]) {
  return props.source ? <ExistingSourceForm {...props} /> : <AddEntry onClose={props.onClose} onSaved={props.onSaved} initialLocal={props.initialProvider === "LOCAL"} />;
}
function validGlobalPolicy(value: unknown): value is { policy: SourcePolicy } {
  if (!value || typeof value !== "object" || !("policy" in value)) return false;
  const policy = value.policy;
  if (!policy || typeof policy !== "object") return false;
  const rules = (value: unknown) => Array.isArray(value) && value.every(item => typeof item === "string");
  return "focus_rules" in policy && rules(policy.focus_rules)
    && "ignore_rules" in policy && rules(policy.ignore_rules)
    && "initial_history_count" in policy && typeof policy.initial_history_count === "number"
    && Number.isSafeInteger(policy.initial_history_count) && policy.initial_history_count >= 0
    && "per_run_max_new_videos" in policy && typeof policy.per_run_max_new_videos === "number"
    && Number.isSafeInteger(policy.per_run_max_new_videos) && policy.per_run_max_new_videos > 0
    && "distillation_style" in policy && STYLES.some(([style]) => style === policy.distillation_style);
}
export function ExistingSourceForm(
  { onClose, onSaved, source, policy, policyModes, schedules, refreshNotice, initialProvider = "YOUTUBE" }: {
    initialProvider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
    onClose: () => void;
    onSaved: () => void;
    source?: Source;
    policy?: SourcePolicy;
    policyModes?: SourcePolicyModes;
    schedules?: Schedule[];
    refreshNotice?: ReactNode;
  },
) {
  const { t } = useUiLanguage();
  const [providerChoice,setProviderChoice] = useState(initialProvider);
  const [youtubeMode, setYoutubeMode] = useState<"video" | "channel">("video");
  const globalPolicy = useRemote<{ policy: SourcePolicy }>("/settings/source-policy", 0, validGlobalPolicy);
  const schedule = schedules?.[0];
  const [url, setUrl] = useState(source?.canonical_url ?? "");
  const [enabled, setEnabled] = useState(source?.enabled ?? true);
  const [processingPolicy, setProcessingPolicy] = useState(
    source?.processing_policy ?? "STANDARD_INTELLIGENCE",
  );
  const [initialHistory, setInitialHistory] = useState(
    String(policy?.initial_history_count ?? 5),
  );
  const [perRunLimit, setPerRunLimit] = useState(
    String(policy?.per_run_max_new_videos ?? 5),
  );
  const [focus, setFocus] = useState<InterestRuleDraft[]>(() => ruleDrafts(policy?.focus_rules ?? []));
  const [ignore, setIgnore] = useState<InterestRuleDraft[]>(() => ruleDrafts(policy?.ignore_rules ?? []));
  const [style, setStyle] = useState(policy?.distillation_style ?? "BALANCED");
  const [focusMode, setFocusMode] = useState<"INHERIT" | "OVERRIDE">(policyModes?.focus ?? (source ? "OVERRIDE" : "INHERIT"));
  const [ignoreMode, setIgnoreMode] = useState<"INHERIT" | "OVERRIDE">(policyModes?.ignore ?? (source ? "OVERRIDE" : "INHERIT"));
  const [styleMode, setStyleMode] = useState<"INHERIT" | "OVERRIDE">(policyModes?.style ?? (source ? "OVERRIDE" : "INHERIT"));
  const [frequency, setFrequency] = useState(schedule?.frequency ?? "DAILY");
  const [time, setTime] = useState(schedule?.local_time ?? "09:00");
  const [scheduleEnabled, setScheduleEnabled] = useState(
    schedule?.enabled ?? true,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expected, setExpected] = useState<string | null | undefined>(source ? policy?.source_policy_revision_id : null);
  const [policyKnown, setPolicyKnown] = useState(!source || (validGlobalPolicy({ policy }) && (!policyModes || Object.values(policyModes).every(mode => mode === "INHERIT" || mode === "OVERRIDE"))));
  const [versionConflict, setVersionConflict] = useState(false);
  const saving = useRef(false), alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const attempt = useRef<{ signature: string; sourceId?: string; command: string; scheduleId: string;
    policyDone: boolean; sourceDone: boolean; scheduleDone: boolean; request: object } | null>(null);
  const versionKnown = policyKnown && (expected === null || (typeof expected === "string" && !!expected.trim() && expected.length <= 512));
  const reloadVersion = async () => {
    if (!source || busy) return;
    setBusy(true);
    try {
      const value = await api<{ source: Source; policy: SourcePolicy; policy_modes?: SourcePolicyModes }>(`/sources/${source.source_id}`);
      if (!alive.current) return;
      const revision = value?.policy?.source_policy_revision_id;
      if (value?.source?.source_id !== source.source_id || !validGlobalPolicy(value)
          || (value.policy_modes && !Object.values(value.policy_modes).every(mode => mode === "INHERIT" || mode === "OVERRIDE"))
          || !(revision === null || (typeof revision === "string" && !!revision.trim() && revision.length <= 512))) throw new Error("invalid policy read");
      if (!STYLES.some(([value]) => value === style)) setStyle(value.policy.distillation_style);
      if (!["INHERIT", "OVERRIDE"].includes(focusMode)) setFocusMode(value.policy_modes?.focus ?? "OVERRIDE");
      if (!["INHERIT", "OVERRIDE"].includes(ignoreMode)) setIgnoreMode(value.policy_modes?.ignore ?? "OVERRIDE");
      if (!["INHERIT", "OVERRIDE"].includes(styleMode)) setStyleMode(value.policy_modes?.style ?? "OVERRIDE");
      setPolicyKnown(true); setExpected(revision); setVersionConflict(false); attempt.current = null; setError(null);
    } catch { if (alive.current) setError("Interests could not be read. Retry before saving. Your draft is preserved."); }
    finally { if (alive.current) setBusy(false); }
  };
  const policyReadRequired = [focusMode, ignoreMode, styleMode].includes("INHERIT");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (saving.current || !versionKnown || versionConflict || (policyReadRequired && !globalPolicy.data)) return;
    if (!source && /^(?:@|UC|https:\/\/(?:www\.)?youtube\.com\/(?:@|channel\/))/.test(url.trim())) {
      setError(t("Use Follow a channel to follow from now on without importing existing videos."));
      return;
    }
    const effectiveFocus = focusMode === "INHERIT" ? globalPolicy.data?.policy?.focus_rules ?? [] : interestRuleValues(focus);
    if (processingPolicy === "STANDARD_INTELLIGENCE" && !effectiveFocus.length) {
      setError(t("Add at least one focus word to let the app select relevant videos for insight extraction."));
      return;
    }
    const policyBody = { initial_history_count: Number(initialHistory), per_run_max_new_videos: Number(perRunLimit),
      focus_mode: focusMode, focus_rules: focusMode === "INHERIT" ? [] : interestRuleValues(focus),
      ignore_mode: ignoreMode, ignore_rules: ignoreMode === "INHERIT" ? [] : interestRuleValues(ignore),
      distillation_style_mode: styleMode, distillation_style: styleMode === "INHERIT" ? null : style };
    if (![...policyBody.focus_rules, ...policyBody.ignore_rules].every(validInterestRule)) {
      setError(t("Each rule needs text without leading or trailing whitespace, up to 160 characters.")); return;
    }
    const signature = JSON.stringify({ url, policyBody, enabled, processingPolicy, frequency, time, scheduleEnabled });
    if (attempt.current?.signature !== signature) attempt.current = { signature, sourceId: source?.source_id,
      command: commandId(), scheduleId: schedule?.schedule_id ?? commandId(), policyDone: false, sourceDone: false, scheduleDone: false,
      request: { expected_source_policy_revision_id: expected, ...policyBody } };
    const step = attempt.current;
    saving.current = true; setBusy(true); setError(null);
    try {
      if (!step.sourceId) {
        const created = await post<{ source: Source }>("/sources", { url, processing_policy: processingPolicy });
        step.sourceId = created.source.source_id;
        if (!alive.current) return;
      }
      if (!step.policyDone) {
        const result = await put<{ applied_source_policy_revision_id?: string; current_source_policy_revision_id?: string; historical_replay?: boolean }>(`/sources/${step.sourceId}/policy`, { command_id: step.command, ...step.request });
        if (!alive.current) return;
        if (!result.applied_source_policy_revision_id || !result.current_source_policy_revision_id || typeof result.historical_replay !== "boolean") throw new Error("The Source could not be saved.");
        if (result.historical_replay || result.applied_source_policy_revision_id !== result.current_source_policy_revision_id) {
          setVersionConflict(true); setError("This command was already applied, and newer interests exist. Your draft is preserved. Reload the current version."); return;
        }
        step.policyDone = true; setExpected(result.current_source_policy_revision_id);
      }
      if (!step.sourceDone) {
        await patch(`/sources/${step.sourceId}`, { enabled, processing_policy: processingPolicy });
        step.sourceDone = true;
        if (!alive.current) return;
      }
      if (frequency !== "MANUAL" && !step.scheduleDone) {
        await post("/automation", { schedule_id: step.scheduleId, target_type: "SOURCE_CHECK", target_id: step.sourceId,
          frequency, weekday: frequency === "WEEKLY" ? 1 : null, local_time: time, timezone: "Asia/Shanghai", enabled: scheduleEnabled });
        step.scheduleDone = true;
        if (!alive.current) return;
      }
      onSaved();
    } catch (reason) {
      if (!alive.current) return;
      if (!step.policyDone && reason instanceof ApiRequestError && reason.code === "CONFLICT") {
        setVersionConflict(true); setError("Interests changed elsewhere. Your draft is preserved. Reload the current version before saving again.");
      } else setError(step.sourceDone ? "Source settings saved. The automatic schedule could not be saved. Retry resumes remaining steps."
        : step.policyDone ? "Policy saved. Source settings could not be saved. Retry resumes remaining steps."
        : "The Source could not be saved. Your draft is preserved. Retry resumes remaining steps.");
    } finally { saving.current = false; if (alive.current) setBusy(false); }
  };
  if (providerChoice === "BILIBILI") return <BilibiliImport onClose={onClose} onSaved={onSaved} onProvider={setProviderChoice} />;
  if (providerChoice === "LOCAL") return <LocalImport onBilibili={() => setProviderChoice("BILIBILI")} onClose={onClose} onSaved={onSaved} onYouTube={() => setProviderChoice("YOUTUBE")} />;
  return (
    <div className="overlay">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-form-title"
      >
        <div className="modal-head">
          <div>
            <h2 id="source-form-title">
              {t(source ? "Edit Source configuration" : "Add a Source")}
            </h2>
            <p className="hint">
              {t("These settings control how this Following is checked and processed.")}
            </p>
          </div>
          <button className="button button-ghost" onClick={onClose}>
            {t("Cancel")}
          </button>
        </div>
        {refreshNotice}
        {source && (!versionKnown || versionConflict) && <div role="alert">
          {!versionKnown && <p>{t("Interests could not be read. Retry before saving. Your draft is preserved.")}</p>}
          <button type="button" className="button button-secondary" disabled={busy} onClick={() => void reloadVersion()}>{t("Reload current interests")}</button>
        </div>}
        {!source && <div className="button-row" aria-label={t("Source provider")}><button className="button button-primary" aria-pressed="true">YouTube</button><button className="button button-secondary" onClick={() => setProviderChoice("LOCAL")}>{t("Local files")}</button><button className="button button-secondary" onClick={() => setProviderChoice("BILIBILI")}>{t("Bilibili")}</button></div>}
        {!source && <div className="button-row" aria-label={t("YouTube source type")}>
          <button className="button button-secondary" aria-pressed={youtubeMode === "video"} onClick={() => setYoutubeMode("video")}>{t("Add one video")}</button>
          <button className="button button-secondary" aria-pressed={youtubeMode === "channel"} onClick={() => setYoutubeMode("channel")}>{t("Follow a channel")}</button>
        </div>}
        {!source && youtubeMode === "channel" ? <CreatorFollowForm provider="YOUTUBE" onSaved={onSaved} /> : <form onSubmit={submit}>
          {!globalPolicy.data && (globalPolicy.error
            ? <div role="alert">
              <ErrorState error={t("Global interests could not be loaded. Check the local connection and retry. Your draft is preserved.")} />
              <button type="button" className="button button-secondary" onClick={globalPolicy.reload}>{t("Retry global interests")}</button>
            </div>
            : <p className="hint" role="status">{t("Loading global interests…")}</p>)}
          <details><summary>{t("Advanced source configuration")}</summary>
          <label className="field">
            {t("Source URL")}<input
              aria-label={t("Source URL")}
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
              placeholder={source ? "https://www.youtube.com/@channel" : "https://www.youtube.com/watch?v=…"}
            />
          </label>
          <label className="field">
            {t("Processing level")}<select
              aria-label={t("Processing level")}
              value={processingPolicy}
              onChange={(event) => setProcessingPolicy(event.target.value)}
            >
              <option value="DISCOVER_ONLY">{t("Discover new videos only")}</option>
              <option value="STANDARD_INTELLIGENCE">
                {t("Turn relevant videos into Intelligence")}
              </option>
            </select>
            <small>{t("The app analyzes relevant videos and creates traceable insights only when Evidence is sufficient. Not every video produces an insight.")}</small>
          </label>
          <label className="field">
            <span>
              <input
                aria-label={t("Monitor this Source")}
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
              />{" "}
              {t("Monitor this Source")}
            </span>
            <small>
              {t("Turning monitoring off affects future checks only; it never removes existing Intelligence.")}
            </small>
          </label>
          <Panel title="What to process">
            <p className="hint">{t("A Following can use your global interests or its own focus and ignore words. Changes affect future checks and insights only.")}</p>
            <label className="field">
              {t("Initial history")}<select
                aria-label={t("Initial history")}
                value={initialHistory}
                onChange={(event) => setInitialHistory(event.target.value)}
              >
                {INITIAL_HISTORY.map((value) => (
                  <option key={value} value={value}>
                    {value} {t("recent videos")}
                  </option>
                ))}
              </select>
              <small>
                {t("How many recent existing videos are considered when this Following is first added.")}
              </small>
            </label>
            <label className="field">
              {t("Per-run limit")}<select
                aria-label={t("Per-run limit")}
                value={perRunLimit}
                onChange={(event) => setPerRunLimit(event.target.value)}
              >
                {PER_RUN_LIMIT.map((value) => (
                  <option key={value} value={value}>{value} {t("new videos")}</option>
                ))}
              </select>
              <small>
                {t("The maximum number of new videos processed in one check. Videos beyond this limit remain pending.")}
              </small>
            </label>
            <label className="field">
              {t("Focus preference")}
              <select aria-label={t("Focus preference")} value={focusMode} onChange={(event) => { setFocusMode(event.target.value as "INHERIT" | "OVERRIDE"); if (event.target.value === "OVERRIDE" && !focus.length) setFocus(ruleDrafts([""])); }}>
                <option value="INHERIT">{t("Use global interests")}</option>
                <option value="OVERRIDE">{t("Set for this Following")}</option>
              </select>
            </label>
            {focusMode === "INHERIT" && globalPolicy.data ? <p className="hint">{t("Global focus")}: {globalPolicy.data?.policy?.focus_rules.join("、") || t("Not set")}</p> : null}
            {focusMode === "OVERRIDE" ? <div>
              <InterestRulesEditor kind="focus" rows={focus} onChange={setFocus} />
              <small>{t("Each row is one rule. Commas and line breaks stay in that rule. Blank rows are omitted.")}</small>
              {processingPolicy === "STANDARD_INTELLIGENCE" && !interestRuleValues(focus).length ? <small>{t("Add at least one focus word to let the app select relevant videos for insight extraction.")}</small> : null}
            </div> : null}
            <label className="field">
              {t("Ignore preference")}
              <select aria-label={t("Ignore preference")} value={ignoreMode} onChange={(event) => { setIgnoreMode(event.target.value as "INHERIT" | "OVERRIDE"); if (event.target.value === "OVERRIDE" && !ignore.length) setIgnore(ruleDrafts([""])); }}>
                <option value="INHERIT">{t("Use global interests")}</option>
                <option value="OVERRIDE">{t("Set for this Following")}</option>
              </select>
            </label>
            {ignoreMode === "INHERIT" && globalPolicy.data ? <p className="hint">{t("Global ignore")}: {globalPolicy.data?.policy?.ignore_rules.join("、") || t("Not set")}</p> : null}
            {ignoreMode === "OVERRIDE" ? <div>
              <InterestRulesEditor kind="ignore" rows={ignore} onChange={setIgnore} />
              <small>{t("Each row is one rule. Commas and line breaks stay in that rule. Blank rows are omitted.")}</small>
            </div> : null}
            <label className="field">
              {t("Style preference")}
              <select aria-label={t("Style preference")} value={styleMode} onChange={(event) => setStyleMode(event.target.value as "INHERIT" | "OVERRIDE")}>
                <option value="INHERIT">{t("Use global interests")}</option>
                <option value="OVERRIDE">{t("Set for this Following")}</option>
              </select>
            </label>
            {styleMode === "OVERRIDE" ? <label className="field">
              {t("Distillation style")}<select
                aria-label={t("Distillation style")}
                value={style}
                onChange={(event) => setStyle(event.target.value)}
              >
                {STYLES.map(([value, label]) => (
                  <option key={value} value={value}>{t(label)}</option>
                ))}
              </select>
              <small>{t(STYLES.find(([value]) => value === style)?.[2] ?? "")}</small>
            </label> : null}
          </Panel>
          <Panel title="When it runs">
            <label className="field">
              {t("Automatic schedule")}<select
                aria-label={t("Automatic schedule")}
                value={frequency}
                onChange={(event) => setFrequency(event.target.value)}
              >
                <option value="DAILY">{t("Daily")}</option>
                <option value="WEEKLY">{t("Weekly")}</option>
                <option value="MANUAL">{t("Run manually")}</option>
              </select>
              <small>
                {t("Choose when this Following runs automatically. Manual does not create an automatic schedule.")}
              </small>
            </label>
            {frequency !== "MANUAL"
              ? (
                <>
                  <label className="field">
                    {t("Time")}<input
                      aria-label={t("Schedule time")}
                      type="time"
                      value={time}
                      onChange={(event) => setTime(event.target.value)}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>
                      <input
                        aria-label={t("Enable automatic schedule")}
                        type="checkbox"
                        checked={scheduleEnabled}
                        onChange={(event) =>
                          setScheduleEnabled(event.target.checked)}
                      />{" "}
                      {t("Enable this automatic schedule")}
                    </span>
                  </label>
                </>
              )
              : null}
          </Panel>
          </details>
          {error && <div role="alert"><ErrorState error={t(error)} /></div>}
          <div className="modal-actions">
            <button
              type="button"
              className="button button-ghost"
              onClick={onClose}
            >
              {t("Cancel")}
            </button>
            <button
              className="button button-primary"
              disabled={busy || !versionKnown || versionConflict || (policyReadRequired && !globalPolicy.data)}
              type="submit"
            >
              {t(busy ? "Saving…" : source ? "Save changes" : "Add Source")}
            </button>
          </div>
        </form>}
      </section>
    </div>
  );
}
function SourceDetail(
  { id, onClose, onRefresh, onAddLocal, refreshNotice }: {
    id: string;
    refreshNotice?: ReactNode;
    onClose: () => void;
    onRefresh: () => void;
    onAddLocal: () => void;
  },
) {
  const { t } = useUiLanguage();
  const creatorCapability = useCreatorFollowingCapability();
  const [refresh, setRefresh] = useState(0);
  const acceptedIdentity = useRef<{ id: string; tracked: boolean } | null>(null);
  const validateRead = useCallback((value: unknown) => {
    if (!value || typeof value !== "object") return false;
    const read = value as { source?: Source; source_runs?: unknown; recent_videos?: unknown };
    if (!validSourceReadIdentity(read.source) || !validFollowingDetailRead(value, id,
      acceptedIdentity.current?.id === id && acceptedIdentity.current.tracked)) return false;
    acceptedIdentity.current = { id, tracked: Boolean(read.source?.tracking) };
    return true;
  }, [id]);
  const { data, error, errorCode, reading, reload } = useRemote<
    {
      source: Source;
      policy: SourcePolicy;
      policy_modes?: SourcePolicyModes;
      schedules: Schedule[];
      recent_videos: {
        video_id: string;
        title: string | null;
        processing_status: string;
        filter: { outcome: string; reason: string } | null;
      }[];
      source_runs: SourceRun[];
    }
  >(`/sources/${id}`, refresh, validateRead, true);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    if (
      reading || !data?.source_runs.some((run) =>
        ["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(run.state)
      )
    ) return;
    const timer = window.setTimeout(() => setRefresh((value) => value + 1), 1000);
    return () => window.clearTimeout(timer);
  }, [data, reading]);
  if (error && !data) return <ErrorState error={error} code={errorCode} onReload={reload} />;
  if (!data) return <Empty>Loading Source…</Empty>;
  const readNotice = <>{refreshNotice}<FollowingReadNotice reading={reading} error={error} errorCode={errorCode} onReload={reload} detail /></>;
  if (data.source.tracking) return <CreatorFollowingDetail refreshNotice={readNotice} id={id} capability={creatorCapability} onClose={onClose} onRefresh={onRefresh} />;
  if (data.source.source_type === "CHANNEL" && !data.source.tracking) return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={sourceLabel(data.source)}>
    <div className="modal-head"><h2>{sourceLabel(data.source)}</h2><button className="button button-ghost" aria-label={t("Close")} onClick={onClose}>{t("Close")}</button></div>
    {readNotice}
    <p role="status">{t("Legacy channel needs attention. Re-add explicitly to establish tracking; its history is preserved.")}</p>
    <a href={data.source.canonical_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
  </section></div>;
  if (data.source.provider === "BILIBILI") return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t("Bilibili")}>
    <div className="modal-head"><h2>{sourceLabel(data.source)}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    {readNotice}
    <p>{t("This Following contains one imported video. Creator monitoring is not enabled.")}</p>
    <ul>{data.recent_videos.map(content => <li key={content.video_id}><a href={`#Content/${content.video_id}`} onClick={onClose}>{content.title}</a></li>)}</ul>
  </section></div>;
  if (data.source.provider === "LOCAL") return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t("Local library")}>
    <div className="modal-head"><h2>{t("Local library")}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    {readNotice}
    <p>{t("Explicit imports only")}</p><button className="button button-primary" onClick={onAddLocal}>{t("Import files")}</button>
    <ul>{data.recent_videos.map(content => <li key={content.video_id}><a href={`#Content/${content.video_id}`} onClick={onClose}>{content.title}</a> · {t(localStatus(content.processing_status))}</li>)}</ul>
  </section></div>;
  const check = async () => {
    if (checking || !data.source.enabled) return;
    setChecking(true);
    try {
      const result = await post<
        { source_run?: SourceRun; status?: string; message?: string }
      >(`/sources/${id}/check`, { command_id: commandId() });
      if (result.source_run) {
        setMessage(
          "Your durable Source Run was accepted. Progress and any required attention appear below.",
        );
        setRefresh((value) => value + 1);
        return;
      }
      if (result.status === "BLOCKED") {
        setMessage(
          "This Following is disabled, so no new Source Run was started. Resume monitoring before checking again.",
        );
        return;
      }
      if (result.status === "FAILED_FINAL") {
        setMessage(
          "The Source check did not complete. Your Source configuration and existing Intelligence are unchanged.",
        );
        return;
      }
      setMessage(
        "The Source check completed. Review recent videos and Source status for the outcome.",
      );
    } catch {
      setMessage(
        "The Source Run could not be submitted. No completion was recorded; try again after checking local service availability.",
      );
    } finally {
      setChecking(false);
    }
  };
  return (
    <div className="overlay">
      <section className="modal" role="dialog" aria-modal="true">
        <div className="modal-head">
          <div>
            <h2>{sourceLabel(data.source)}</h2>
            <a
              className="source-url"
              href={data.source.canonical_url}
              target="_blank"
              rel="noreferrer"
            >
              {t("Open Source")}
            </a>
          </div>
          <button className="button button-ghost" onClick={onClose}>
            {t("Close")}
          </button>
        </div>
        {!editing && readNotice}
        <Panel title="Source management">
          <p>
            <Status value={data.source.enabled ? "ENABLED" : "DISABLED"} />{" "}
            {t("Monitoring changes affect future checks only; existing Intelligence remains unchanged.")}
          </p>
          <div className="inline-actions">
            <button
              className="button button-secondary"
              onClick={() => setEditing(true)}
            >
              {t("Edit configuration")}
            </button>
            <button
              className="button button-secondary"
              onClick={async () => {
                await patch(`/sources/${id}`, {
                  enabled: !data.source.enabled,
                });
                onRefresh();
                onClose();
              }}
            >
              {t(data.source.enabled
                ? "Stop future monitoring"
                : "Resume monitoring")}
            </button>
          </div>
        </Panel>
        {(data.source_runs.length === 0 || data.source.processing_policy === "DISCOVER_ONLY") && (
          <div className="semantic-state state-neutral" role="status">
            <p>{t(data.source.processing_policy === "DISCOVER_ONLY"
              ? data.source_runs.length === 0
                ? "This Following only discovers new videos and has not been checked yet. No Content or Intelligence has been produced. Change Processing level to extract insights, then choose Check Now."
                : "This Following only discovers new videos. It does not create Summaries or Intelligence. Change Processing level to extract insights from future checks."
              : "This Following has not been checked yet, so there is no Content or Intelligence to review. Choose Check Now to begin.")}</p>
          </div>
        )}
        <Panel title="Processing policy">
          <p>
            {t("Initial history")}: {data.policy.initial_history_count}{" "}
            {t("recent existing videos when this Following was first added.")}
          </p>
          <p>
            {t("Per-run limit")}: {data.policy.per_run_max_new_videos}{" "}
            {t("new videos in one check; overflow remains pending.")}
          </p>
          <p>
            {t("Focus")}:{" "}
            {data.policy.focus_rules.join(", ") || t("No focus terms")}. {t("Ignore")}:
            {" "}
            {data.policy.ignore_rules.join(", ") || t("No ignore terms")}.
          </p>
          <p>
            {t("Style")}:{" "}
            {t(STYLES.find(([value]) => value === data.policy.distillation_style)
              ?.[1] ?? "Balanced")}.
          </p>
        </Panel>
        <Panel title="Schedule">
          {data.schedules.length
            ? data.schedules.map((schedule) => (
              <p key={schedule.schedule_id}>
                <Status value={schedule.enabled ? "ENABLED" : "DISABLED"} />
                {" "}
                {t("Runs")} {t(schedule.frequency.toLowerCase())}
                {schedule.local_time ? ` at ${schedule.local_time}` : ""}
                {schedule.timezone ? ` (${schedule.timezone})` : ""}.
              </p>
            ))
            : (
              <Empty>
                {t("This Following runs manually. Edit configuration to add an automatic schedule.")}
              </Empty>
            )}
        </Panel>
        <button
          className="button button-primary"
          onClick={check}
          disabled={checking || !data.source.enabled}
          aria-busy={checking}
        >
          {t(checking ? "Starting Source Run…" : "Check Now")}
        </button>
        <p className="hint">
          {data.source.enabled
            ? t("Checks enter the durable processing path. Repeated clicks reuse active work.")
            : t("Resume monitoring to start a new check. Historical data remains available.")}
        </p>
        {message && (
          <div className="semantic-state state-neutral" role="status" aria-live="polite">
            <p>{t(message)}</p>
          </div>
        )}
        <Panel title="Recent videos">
          {data.recent_videos.length
            ? data.recent_videos.map((video) => {
              const skipped = video.filter?.outcome === "NOT_RELEVANT";
              const uncertain = video.filter?.outcome === "UNCERTAIN";
              return (
                <div className="metadata-row" key={video.video_id}>
                  <span>{video.title ?? video.video_id}</span>
                  <div>
                    <Status
                      value={skipped
                        ? "SKIPPED"
                        : video.filter?.outcome ?? video.processing_status}
                    />
                    {skipped
                      ? (
                        <>
                          <p>{t(filterReason(video.filter?.reason))}</p>
                          <button
                            className="button button-secondary"
                            onClick={async () => {
                              const result = await post<
                                { source_run?: SourceRun }
                              >(
                                `/sources/${id}/videos/${video.video_id}/manual-analyze`,
                                { command_id: commandId() },
                              );
                              setMessage(
                                result.source_run
                                  ? "This video was accepted for analysis. Its relevance skip has been overridden; other safety, budget, and model rules still apply."
                                  : "This video’s relevance skip has been overridden; other safety, budget, and model rules still apply.",
                              );
                            }}
                          >
                            {t("Analyze this Video")}
                          </button>
                          <p className="hint">
                            {t("Analyze this video even though it was skipped for relevance. Other safety, budget and model rules still apply.")}
                          </p>
                        </>
                      )
                      : (
                        <p>
                          {uncertain ? <>{t(filterReason(video.filter?.reason))} </> : null}
                          {t("Current processing state")}: {t(statusLabel(video.processing_status))}.
                        </p>
                      )}
                  </div>
                </div>
              );
            })
            : <Empty>No recent videos for this Source.</Empty>}
        </Panel>
        <Panel title="Source Run status">
          {data.source_runs.length
            ? data.source_runs.map((run) =>
              run.attention_reason
                ? <Attention key={run.run_id} run={run} />
                : (
                  <p key={run.run_id}>
                    <Status value={run.state} /> {t("A check is")} {t(statusLabel(run.state).toLowerCase())}.
                  </p>
                )
            )
            : <Empty>No Source Runs yet.</Empty>}
        </Panel>
      </section>
      {editing && (
        <SourceForm
          refreshNotice={readNotice}
          source={data.source}
          policy={data.policy}
          policyModes={data.policy_modes}
          schedules={data.schedules}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onRefresh();
            onClose();
          }}
        />
      )}
    </div>
  );
}
function Investigations() {
  return (
    <div className="semantic-state state-neutral">
      <Status value="UNAVAILABLE" />
      <h2>Investigations are not active in V1</h2>
      <p>
        This is planned beyond V1. Evidence Expansion, external validation, and
        Deep Analysis are not available.
      </p>
    </div>
  );
}
type ProviderStatus = {
  provider: string;
  model: string | null;
  adapter_available: boolean;
  configured?: boolean;
  credential_status?: string;
  qualification_status: string;
  authorized: boolean;
  production_eligible: boolean;
  scope: string;
  reason: string;
};
function preferenceCopy(preference: Preference) {
  return ({
    EXPLICIT: "You directly chose this.",
    DERIVED: "The app inferred this from your feedback.",
    TEMPORARY: "Used only until its expiry.",
  } as Record<string, string>)[preference.provenance] ??
    "This preference keeps its recorded origin.";
}
function usageReason(value: string) {
  return ({
    PERSONALIZED_INTELLIGENCE: "Personalized Intelligence",
    MANUAL_DISTILLATION: "Manual analysis",
  } as Record<string, string>)[value] ?? "Recorded work";
}
type BackupPreview = {
  backup_date: string;
  application_version: string;
  schema_version: number;
  following_count: number;
  content_count: number;
  summary_count: number;
  evidence_count: number;
  intelligence_count: number;
  topic_count: number;
  settings_included: boolean;
  data_artifact_count: number;
  data_size_bytes: number;
  data_file_count?: number;
  data_file_size_bytes?: number;
  vault_excluded: boolean;
};

type BackupRestoreStatus = {
  ready: boolean;
  reasons: string[];
  message: string;
  restore_pending: boolean;
  last_restore?: { state: string; message: string; restore_id?: string; completed_at?: string } | null;
};

const backupReasonCopy: Record<string, string> = {
  SOURCE_RUN_ACTIVE: "a Source Run is still working",
  DISTILLATION_ACTIVE: "an Intelligence extraction has not finished",
  JOBS_ACTIVE: "a background job is still running",
  PROVIDER_CALL_UNRESOLVED: "a provider call has an unresolved outcome",
  PROVIDER_DISPATCH_UNRESOLVED: "a provider dispatch has an unresolved outcome",
  RESTORE_PENDING: "a restore is pending",
  TRACKED_CONTENT_RETRY_ACTIVE: "a caption retry is still unfinished",
  MAINTENANCE_ACTIVE: "another Backup, Restore or model configuration operation is in progress",
  DATABASE_UNAVAILABLE: "Stored files or the database could not be verified. Check local storage and retry.",
};

function byteSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Why Backup is or is not available, built from the structured reason codes the
 * service returns. The service's own message is English engineering prose, so
 * rendering it would put untranslated backend text into the Chinese UI — and
 * would also hide the actual safety blocker. Each fragment is translated on its
 * own because the sentence is assembled here.
 */
function backupReadiness(status: BackupRestoreStatus | null) {
  if (!status) return { lead: "Checking whether core data is safe to back up…", items: [] as string[] };
  if (status.restore_pending && status.reasons.every(reason => reason === "RESTORE_PENDING")) return { lead: "A restore is pending. Intelligence restarts before processing resumes.", items: [] as string[] };
  if (status.ready && !status.restore_pending) return { lead: "Core data is quiescent and ready for backup.", items: [] as string[] };
  const unknown = "Backup safety has not been confirmed. Read its status again.";
  const reasons = status.restore_pending ? ["RESTORE_PENDING", ...status.reasons] : status.reasons;
  const items = [...new Set(reasons.map((reason) => backupReasonCopy[reason] ?? unknown))];
  const workOnly = reasons.length > 0 && reasons.every(reason =>
    reason !== "DATABASE_UNAVAILABLE" && backupReasonCopy[reason] !== undefined);
  return {
    lead: workOnly ? "Backup is unavailable while this work remains unfinished:" : "Backup is unavailable for these reasons:",
    items: items.length ? items : [unknown],
  };
}
function BackupRestorePanel() {
  const { t } = useUiLanguage();
  const [status, setStatus] = useState<BackupRestoreStatus | null>(null);
  const [backup, setBackup] = useState<{
    backup_id: string;
    file_name: string;
    size_bytes: number;
    created_at: string;
    preview: BackupPreview;
  } | null>(null);
  const [restore, setRestore] = useState<{
    restore_id: string;
    preview: BackupPreview;
  } | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirmationDialog = useRef<HTMLDialogElement>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const inspectedRestore = useRef<{ id: string; baselineKnown: boolean; alreadyApplied: boolean } | null>(null);
  const confirmedRestore = useRef<{ id: string; deadline: number; failed: boolean } | null>(null);
  const reconnectTimer = useRef<number>();
  const statusReadVersion = useRef(0);
  const [reconnecting, setReconnecting] = useState(false);

  const finishReconnect = () => {
    confirmedRestore.current = null;
    window.clearTimeout(reconnectTimer.current);
    reconnectTimer.current = undefined;
    setReconnecting(false);
  };

  useEffect(() => {
    const receipt = status?.last_restore;
    if (error && !restore) {
      inspectedRestore.current = null;
    } else if (restore && inspectedRestore.current?.id !== restore.restore_id) {
      inspectedRestore.current = {
        id: restore.restore_id,
        baselineKnown: status !== null && !statusError && (receipt == null || (
          ["APPLIED", "REJECTED", "ROLLED_BACK"].includes(receipt.state)
          && typeof receipt.restore_id === "string" && receipt.restore_id.length > 0
        )),
        alreadyApplied: receipt?.state === "APPLIED" && receipt.restore_id === restore.restore_id,
      };
    } else if (!restore && !busy && !showConfirm && !confirmedRestore.current && !status?.restore_pending
      && receipt?.restore_id !== inspectedRestore.current?.id) {
      inspectedRestore.current = null;
    }
  }, [restore, status, statusError, busy, showConfirm, error]);

  useEffect(() => {
    const dialog = confirmationDialog.current;
    if (!dialog) return;
    if (showConfirm && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!showConfirm && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [showConfirm]);

  const refreshStatus = async () => {
    const version = ++statusReadVersion.current;
    try {
      const result = await api<{ status: BackupRestoreStatus }>("/backup-restore/status");
      if (version !== statusReadVersion.current) return;
      setStatus(result.status);
      const attempt = confirmedRestore.current;
      if (attempt) {
        const receipt = result.status.last_restore;
        if (receipt?.restore_id === attempt.id && receipt.state === "APPLIED" && !result.status.restore_pending) {
          finishReconnect();
        } else if (attempt.failed || (receipt?.restore_id === attempt.id && receipt.state !== "APPLIED")) {
          attempt.failed = true;
          window.clearTimeout(reconnectTimer.current);
          reconnectTimer.current = undefined;
          setReconnecting(false);
          setStatusError("Restore did not complete successfully. Read its status before trying again.");
          return;
        } else if (Date.now() >= attempt.deadline) {
          setReconnecting(false);
          setStatusError("Backup status is unavailable. Check the local connection and retry.");
          return;
        } else {
          setReconnecting(true);
        }
      }
      setStatusError(null);
    } catch (reason) {
      if (version !== statusReadVersion.current) return;
      const attempt = confirmedRestore.current;
      if (attempt?.failed) {
        setReconnecting(false);
        setStatusError("Restore did not complete successfully. Read its status before trying again.");
      } else if (attempt && Date.now() < attempt.deadline) {
        setReconnecting(true);
        setStatusError(null);
      } else {
        setReconnecting(false);
        setStatusError("Backup status is unavailable. Check the local connection and retry.");
      }
    }
  };

  useEffect(() => {
    void refreshStatus();
    const timer = window.setInterval(() => void refreshStatus(), 10_000);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(reconnectTimer.current);
      statusReadVersion.current += 1;
    };
  }, []);

  const createBackup = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await post<{ backup: NonNullable<typeof backup> }>(
        "/backup-restore/backups",
        {},
      );
      setBackup(result.backup);
    } catch (reason) {
      setError("Backup could not be created. Check readiness and available storage, then retry.");
    } finally {
      setBusy(false);
      await refreshStatus();
    }
  };

  const chooseBackup = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setError("Choose an Intelligence ZIP backup.");
      return;
    }
    setBusy(true);
    setError(null);
    setRestore(null);
    try {
      const result = await uploadZip<{
        restore: { restore_id: string; preview: BackupPreview };
      }>("/backup-restore/restore/stage", file);
      setRestore(result.restore);
    } catch (reason) {
      setError("Backup inspection failed. Choose an intact Intelligence ZIP backup; current data has not changed.");
    } finally {
      setBusy(false);
      await refreshStatus();
    }
  };

  const cancelRestore = async () => {
    if (!restore) return;
    setBusy(true);
    setError(null);
    try {
      await post("/backup-restore/restore/cancel", { restore_id: restore.restore_id });
      setRestore(null);
      setShowConfirm(false);
      setConfirmation("");
    } catch (reason) {
      setError("Restore inspection could not be cancelled. Check the local connection and retry before restoring.");
    } finally {
      setBusy(false);
      await refreshStatus();
    }
  };

  const confirmRestore = async () => {
    if (!restore || confirmation !== "RESTORE") return;
    setBusy(true);
    setError(null);
    try {
      const result = await post<{ restore?: { restore_id?: string } }>("/backup-restore/restore/confirm", { restore_id: restore.restore_id });
      if (result.restore?.restore_id !== undefined && result.restore.restore_id !== restore.restore_id) {
        throw new Error("Restore acknowledgement identity mismatch");
      }
      finishReconnect();
      const attempt = { id: restore.restore_id, deadline: Date.now() + 60_000, failed: false };
      confirmedRestore.current = attempt;
      statusReadVersion.current += 1;
      setStatusError(null);
      setReconnecting(true);
      reconnectTimer.current = window.setTimeout(() => {
        if (confirmedRestore.current !== attempt) return;
        setReconnecting(false);
        setStatusError("Backup status is unavailable. Check the local connection and retry.");
      }, 60_000);
      setShowConfirm(false);
      setRestore(null);
      setConfirmation("");
      setStatus((current) => current ? {
        ...current,
        ready: false,
        restore_pending: true,
        reasons: ["RESTORE_PENDING"],
        message: "Restore is pending. Intelligence will restart before processing resumes.",
      } : current);
    } catch (reason) {
      setError("Restore confirmation failed. Check restore status before trying again.");
    } finally {
      setBusy(false);
      await refreshStatus();
    }
  };

  const preview = (value: BackupPreview) => (
    <dl className="metadata-grid">
      <div><dt>{t("Backup date")}</dt><dd>{humanDate(value.backup_date)}</dd></div>
      <div><dt>{t("App / schema")}</dt><dd>{value.application_version} · {value.schema_version}</dd></div>
      <div><dt>{t("Following")}</dt><dd>{value.following_count}</dd></div>
      <div><dt>{t("Content")}</dt><dd>{value.content_count}</dd></div>
      <div><dt>{t("Current Summaries")}</dt><dd>{value.summary_count}</dd></div>
      <div><dt>{t("Evidence")}</dt><dd>{value.evidence_count}</dd></div>
      <div><dt>{t("Intelligence")}</dt><dd>{value.intelligence_count}</dd></div>
      <div><dt>{t("Topics")}</dt><dd>{value.topic_count}</dd></div>
      <div><dt>{t("Settings")}</dt><dd>{t(value.settings_included ? "Included" : "Not included")}</dd></div>
      <div>{Number.isSafeInteger(value.data_file_count) && value.data_file_count! >= 0 && Number.isSafeInteger(value.data_file_size_bytes) && value.data_file_size_bytes! >= 0
        ? <><dt>{t("DATA files")}</dt><dd>{value.data_file_count} · {byteSize(value.data_file_size_bytes!)}</dd></>
        : <><dt>{t("DATA entries")}</dt><dd>{value.data_artifact_count} · {byteSize(value.data_size_bytes)}</dd></>}</div>
    </dl>
  );

  const readiness = backupReadiness(status);
  const receipt = status?.last_restore;
  const currentRestoreCompleted = typeof receipt?.restore_id === "string" && receipt.restore_id.length > 0
    && inspectedRestore.current?.id === receipt.restore_id
    && inspectedRestore.current.baselineKnown && !inspectedRestore.current.alreadyApplied;
  const receiptDate = typeof receipt?.completed_at === "string" && Number.isFinite(Date.parse(receipt.completed_at))
    ? humanDate(receipt.completed_at) : null;
  return (
    <Panel id="settings-backup" icon="archive" title="Backup and Restore">
      <p>{t("Backups include Intelligence core data and persisted settings. External Vault content, credentials, and model files are excluded.")}</p>
      {!statusError ? <p className="hint" role="status">
        {t(readiness.lead)}
        {readiness.items.length > 0 && ` ${readiness.items.map((item) => t(item)).join(" ")}`}
      </p> : null}
      <div className="button-row">
        <button type="button" className="button button-primary" onClick={createBackup} disabled={busy || !status?.ready}>
          {t(busy ? "Working…" : "Create Backup")}
        </button>
        <label className="button secondary-button">
          {t("Choose backup")}
          <input
            aria-label={t("Choose backup file")}
            aria-describedby="backup-file-hint"
            type="file"
            disabled={busy || status?.restore_pending}
            onChange={chooseBackup}
          />
        </label>
      </div>
      <p id="backup-file-hint" className="hint">
        {t("Choose an Intelligence .zip backup. Invalid files are rejected; you can choose another file.")}
      </p>
      {backup ? (
        <article className="metadata-row" aria-label={t("Backup result")}>
          <div>
            <strong>{backup.file_name}</strong>
            <p>{humanDate(backup.created_at)} · {byteSize(backup.size_bytes)}</p>
            {preview(backup.preview)}
            <a href={`/api/v1/backup-restore/backups/${backup.backup_id}/download`}>
              {t("Save backup file")}
            </a>
          </div>
        </article>
      ) : null}
      {restore ? (
        <article className="metadata-row" aria-label={t("Inspected backup preview")}>
          <div>
            <strong>{t("Backup inspected")}</strong>
            <p>{t("Nothing has changed yet. Review this backup before continuing.")}</p>
            {preview(restore.preview)}
            <p className="hint">{t("External Vault content is excluded and will not be overwritten.")}</p>
            <div className="button-row">
              <button type="button" className="danger-button" disabled={busy} onClick={() => setShowConfirm(true)}>
                {t("Restore this backup…")}
              </button>
              <button type="button" className="secondary-button" disabled={busy} onClick={cancelRestore}>
                {t("Cancel")}
              </button>
            </div>
          </div>
        </article>
      ) : null}
      {!statusError && !error && !busy && !restore && !showConfirm && status?.restore_pending === false && receipt?.state === "APPLIED" ? (
        <p className={currentRestoreCompleted ? "success-message" : "hint"} role="status">
          <span>{t(currentRestoreCompleted ? "Restore completed successfully." : "Previous restore completed successfully.")}</span>
          {receiptDate ? <> <span className="reading-meta">{receiptDate}</span></> : null}
        </p>
      ) : null}
      {status?.restore_pending ? (
        <p role="status">{t("Restore is pending. Intelligence will restart and validate the restored data before processing resumes.")}</p>
      ) : null}
      {reconnecting ? <p role="status">{t("Reconnecting and validating the restored data…")}</p> : null}
      {error ? <p className="form-error" role="alert">{t(error)}</p> : null}
      {statusError ? <p className="form-error" role="alert">{t(statusError)} <button disabled={busy} onClick={() => void refreshStatus()}>{t("Retry")}</button></p> : null}
      {showConfirm && restore ? (
        <dialog
          ref={confirmationDialog}
          aria-labelledby="restore-confirm-title"
          aria-modal="true"
          onCancel={(event) => {
            event.preventDefault();
            setShowConfirm(false);
            setConfirmation("");
          }}
        >
          <h2 id="restore-confirm-title">{t("Replace Intelligence core data?")}</h2>
          <p>{t("This replaces the current core database and DATA artifacts at restart. Your external Vault remains untouched.")}</p>
          <label className="field">
            {t("Type RESTORE to confirm")}
            <input
              autoFocus
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              autoComplete="off"
            />
          </label>
          <div className="button-row">
            <button type="button" className="danger-button" disabled={busy || confirmation !== "RESTORE"} onClick={confirmRestore}>
              {t("Confirm Restore and restart")}
            </button>
            <button type="button" className="secondary-button" disabled={busy} onClick={() => { setShowConfirm(false); setConfirmation(""); }}>
              {t("Go back")}
            </button>
          </div>
        </dialog>
      ) : null}
    </Panel>
  );
}

function GlobalInterests({
  policy,
  savedNotice,
  onClearNotice,
  onSaved,
}: {
  policy: SourcePolicy;
  savedNotice?: boolean;
  onClearNotice?: () => void;
  onSaved: () => void;
}) {
  const { t } = useUiLanguage();
  const [focus, setFocus] = useState<InterestRuleDraft[]>(() => ruleDrafts(policy.focus_rules));
  const [ignore, setIgnore] = useState<InterestRuleDraft[]>(() => ruleDrafts(policy.ignore_rules));
  const [style, setStyle] = useState(policy.distillation_style);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelEdit = () => {
    setFocus(ruleDrafts(policy.focus_rules));
    setIgnore(ruleDrafts(policy.ignore_rules));
    setStyle(policy.distillation_style);
    setError(null);
    setEditing(false);
  };
  const save = async () => {
    const focusValues = interestRuleValues(focus);
    const ignoreValues = interestRuleValues(ignore);
    if (![...focusValues, ...ignoreValues].every(validInterestRule)) {
      setError(t("Each rule needs text without leading or trailing whitespace, up to 160 characters.")); return;
    }
    const hasDuplicates = (values: string[]) => {
      const seen = new Set<string>();
      for (const item of values) {
        const folded = item.toLocaleLowerCase();
        if (seen.has(folded)) return true;
        seen.add(folded);
      }
      return false;
    };
    if (hasDuplicates(focusValues) || hasDuplicates(ignoreValues)) {
      setError(t("Preferences could not be saved: duplicate rules found. Remove duplicates and save again."));
      return;
    }
    setBusy(true);
    setError(null);
    const cmdId = commandId();
    try {
      for (let attempt = 0; attempt < 4; attempt += 1) {
        try {
          await put("/settings/source-policy", {
            command_id: cmdId,
            initial_history_count: policy.initial_history_count,
            per_run_max_new_videos: policy.per_run_max_new_videos,
            focus_rules: focusValues,
            ignore_rules: ignoreValues,
            distillation_style: style,
          });
          break;
        } catch (err) {
          if (err instanceof ApiRequestError && err.code === "CONFIGURATION_APPLYING" && attempt < 3) {
            await new Promise(resolve => setTimeout(resolve, 550));
            continue;
          }
          throw err;
        }
      }
      setEditing(false);
      onSaved();
    } catch {
      setError(t("Preferences could not be saved."));
    } finally {
      setBusy(false);
    }
  };
  const styleLabel = STYLES.find(([value]) => value === policy.distillation_style)?.[1] ?? policy.distillation_style;
  return <Panel id="settings-interests" icon="funnel" title="My interests">
    <p className="hint">{t("These are defaults for future insight selection. A Following can use them or set its own focus. Summaries remain faithful to source content; existing insights and Topics do not change.")}</p>
    {!editing ? <>
      <p>{t("What I focus on")}: {policy.focus_rules.join(", ") || t("Not set")}</p>
      <p>{t("Less of / ignore")}: {policy.ignore_rules.join(", ") || t("Not set")}</p>
      <p>{t("Insight style")}: {t(styleLabel)}</p>
      {savedNotice ? <p className="hint">{t("Preferences saved.")}</p> : null}
      <button type="button" className="button button-secondary" onClick={() => { onClearNotice?.(); setError(null); setEditing(true); }}>{t("Edit interests")}</button>
    </> : <div onKeyDown={event => { if (event.key === "Escape" && !busy) { event.stopPropagation(); cancelEdit(); } }}>
    <InterestRulesEditor kind="focus" label="What I focus on" rows={focus} onChange={setFocus} />
    <InterestRulesEditor kind="ignore" label="Less of / ignore" rows={ignore} onChange={setIgnore} />
    <p className="hint">{t("Each row is one rule. Commas and line breaks stay in that rule. Blank rows are omitted.")}</p>
    <label className="field">{t("Insight style")}
      <select aria-label={t("Insight style")} value={style} onChange={(event) => setStyle(event.target.value)}>
        {STYLES.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}
      </select>
    </label>
    <div className="button-row">
      <button type="button" className="button button-primary" disabled={busy} onClick={save}>{t(busy ? "Saving…" : "Save preferences")}</button>
      <button type="button" className="button button-secondary" disabled={busy} onClick={cancelEdit}>{t("Cancel")}</button>
    </div>
    {error ? <p className="form-error" role="alert">{error}</p> : null}</div>}
  </Panel>;
}

function Settings({ refresh }: { refresh: number }) {
  const [modelMessage, setModelMessage] = useState("");
  const { language, setLanguage, t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const [interestsSavedNotice, setInterestsSavedNotice] = useState(false);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [editingLanguage, setEditingLanguage] = useState(false);
  const [legacyDiagOpen, setLegacyDiagOpen] = useState(false);
  const [interfaceDraft, setInterfaceDraft] = useState(language);
  const [outputDraft, setOutputDraft] = useState<"zh-CN" | "en">("zh-CN");
  const [languageError, setLanguageError] = useState<string | null>(null);
  const settings = useRemote<{
    general: {
      timezone: string;
      output_language: "zh-CN" | "en";
      output_language_source: string;
      output_language_updated_at: string | null;
    };
    providers: ProviderStatus[];
    runtime_local_model?: { model: string | null; status: string; installed?: boolean; digest_valid?: boolean };
    local_intelligence?: unknown;
    content_processing?: { status: string; requires_cloud: boolean };
    cloud_credential?: { configured: boolean; source: string };
    model_preference?: { desired_provider: string | null; desired_model: string | null };
    workspace_ai?: unknown;
  }>(
    "/settings",
    refresh + revision,
    undefined, true,
  );
  const prefs = useRemote<{ active: Preference[]; history: Preference[] }>(
    "/settings/preferences",
    refresh,
  );
  const policy = useRemote<{ policy: SourcePolicy }>(
    "/settings/source-policy",
    refresh + revision,
    undefined, true,
  );
  const usage = useRemote<{ usage: ResourceUsage[] }>(
    "/settings/resource-usage",
    refresh,
  );
  const [activeSettingSection, jumpToSetting] = useActiveSection(SETTINGS_SECTION_IDS);
  const failedReads = [settings, prefs, policy, usage].filter(read => read.error);
  if (failedReads.length) {
    return <ErrorState error={failedReads[0].error ?? ""} code={failedReads[0].errorCode}
      onReload={() => failedReads.forEach(read => read.reload())} />;
  }
  if (!settings.data || !prefs.data || !policy.data || !usage.data) {
    return <Empty>Loading Settings…</Empty>;
  }
  const globalPolicy = policy.data.policy;
  const videoDistillation = settings.data.providers.find((provider) =>
    provider.configured && provider.adapter_available &&
    ["V1_VIDEO_DISTILLATION_ONLY", "PUBLIC_YOUTUBE_TIMED_MEDIA"].includes(provider.scope)
  ) ?? settings.data.providers.find(provider => provider.adapter_available && provider.scope === "V1_VIDEO_DISTILLATION_ONLY");
  const localFoundation = settings.data.providers.find((provider) =>
    provider.provider === "Local" && provider.scope === "SCORING_SUMMARY_ONLY"
  );
  const otherProviders = settings.data.providers.filter((provider) =>
    provider !== videoDistillation
  );
  const saveLanguage = async (value: "zh-CN" | "en") => {
    setSavingLanguage(true);
    setLanguageError(null);
    try {
      await put("/settings/output-language", { output_language: value });
      setLanguage(interfaceDraft);
      setEditingLanguage(false);
      setRevision((current) => current + 1);
    } catch (reason) {
      setLanguageError(
        reason instanceof Error
          ? reason.message
          : "Output language could not be saved.",
      );
    } finally {
      setSavingLanguage(false);
    }
  };
  return (
    <div className="settings-stack">
      <div role="toolbar" aria-label={t("Settings sections")} className="reader-jump-bar settings-jump-bar">
        {([
          ["settings-language", "translate", "Jump · Language"],
          ["settings-interests", "funnel", "Jump · Interests"],
          ["settings-models", "sparkle", "Jump · Models"],
          ["settings-backup", "archive", "Jump · Backup"],
        ] as const).map(([secId, iconName, labelKey]) => {
          const isActive = activeSettingSection === secId;
          return (
            <button
              key={secId}
              type="button"
              aria-current={isActive ? "location" : undefined}
              className={`reader-jump-chip${isActive ? " is-active" : ""}`}
              onClick={() => jumpToSetting(secId)}
            >
              <PhosphorIcon name={iconName} weight={isActive ? "fill" : "regular"} size={13} />
              {t(labelKey)}
            </button>
          );
        })}
      </div>
      <Panel id="settings-language" icon="translate" title="Language">
        {!editingLanguage ? <>
          <p>{t("Interface language")}: {language === "zh-CN" ? "中文" : "English"} · {t("Generated output")}: {settings.data.general.output_language === "zh-CN" ? "中文" : "English"}</p>
          <button className="button button-secondary" onClick={() => { setInterfaceDraft(language); setOutputDraft(settings.data!.general.output_language); setEditingLanguage(true); }}>{t("Edit language")}</button>
        </> : <>
          <label className="field">{t("Interface language")}<select aria-label={t("Interface language")} value={interfaceDraft} disabled={savingLanguage} onChange={event => setInterfaceDraft(event.target.value as "zh-CN" | "en")}><option value="zh-CN">中文</option><option value="en">English</option></select></label>
          <label className="field">{t("Preferred output language")}<select aria-label={t("Preferred output language")} value={outputDraft} disabled={savingLanguage} onChange={event => setOutputDraft(event.target.value as "zh-CN" | "en")}><option value="zh-CN">中文</option><option value="en">English</option></select></label>
          <button className="button button-primary" disabled={savingLanguage} onClick={() => void saveLanguage(outputDraft)}>{t(savingLanguage ? "Saving…" : "Save language")}</button>
          <button className="button button-secondary" disabled={savingLanguage} onClick={() => { setEditingLanguage(false); setLanguageError(null); }}>{t("Cancel")}</button>
        </>}
        <p className="hint">{t("Source language is detected automatically. Language choices apply to future output; existing content is preserved.")}</p>
        {languageError ? <p className="form-error" role="alert">{languageError}</p> : null}
      </Panel>
      <GlobalInterests
        key={JSON.stringify(globalPolicy)}
        policy={globalPolicy}
        savedNotice={interestsSavedNotice}
        onClearNotice={() => setInterestsSavedNotice(false)}
        onSaved={() => {
          setInterestsSavedNotice(true);
          setRevision(current => current + 1);
        }}
      />
      {(() => {
        const hasWorkspaceAi = Boolean(readWorkspaceAiSettings(settings.data.workspace_ai));
        const legacyModelsPanel = (
          <Panel id={hasWorkspaceAi ? undefined : "settings-models"} icon="sparkle" title="Models and processing">
            <h3>{t("Content processing")}</h3><p>{t("Ready. Content is saved and organized locally when source text or captions are available. Cloud Intelligence is optional.")}</p>
            <h3>{t("Local model for scoring and Summary")}</h3><p>{settings.data.runtime_local_model?.model ?? localFoundation?.model ?? t("Not configured")} · {t(settings.data.runtime_local_model?.status === "READY" ? "Installed; identity verified" : "Readiness needs attention")}</p>
            <p className="hint">{t("Installation and identity checks do not qualify a model for Intelligence.")}</p>
            <p className="hint">{t("Scoring and model-based Summary use this runtime configuration. Candidate preferences in Advanced do not change it.")}</p>
            <h3>{t("Intelligence")}</h3>
            {!readLocalMatrix(settings.data.local_intelligence) && localFoundation?.qualification_status === "INTELLIGENCE_UNQUALIFIED" && <p>{t("The current local model has not passed Intelligence quality verification. Existing Content, Summary and Evidence remain readable.")}</p>}
            <LocalIntelligencePresentation matrix={settings.data.local_intelligence} onReload={settings.reload} />
            <p>{t(videoDistillation?.production_eligible ? "Optional cloud analysis is available after your authorization for each request." : videoDistillation?.credential_status === "BLOCKED" ? "Cloud Intelligence is optional. It needs a credential and your separate authorization for each request. Content processing remains usable." : "Cloud Intelligence is optional and requires a qualified model and your separate authorization for each request. Content processing remains usable.")}</p>
            <div className="button-row">
              <a className="button button-secondary button-small" href="#Settings/models/moonshot?panel=spending">{t("Adjust cloud spending limits")}</a>
            </div>
            <details><summary>{t("Cloud setup and model details")}</summary><ModelSettings message={modelMessage} setMessage={setModelMessage} credential={settings.data.cloud_credential} preference={settings.data.model_preference} onSaved={() => setRevision(current => current + 1)} /></details>
          </Panel>
        );
        return hasWorkspaceAi ? (
          <>
            <WorkspaceAiSettingsPanel id="settings-models" initial={settings.data.workspace_ai} />
            <details
              className="settings-advanced legacy-model-diagnostics"
              onToggle={event =>
                setLegacyDiagOpen((event.currentTarget as HTMLDetailsElement).open)
              }
            >
              <summary>
                {language === "zh-CN"
                  ? "底层模型资格校验与受控云端账单诊断（工程高级项）"
                  : "Underlying model qualification & cloud billing diagnostics"}
              </summary>
              {legacyDiagOpen ? (
                <>
                  {legacyModelsPanel}
                  <LocalIntelligenceSetup />
                  <TranscriptionSetup />
                </>
              ) : null}
            </details>
          </>
        ) : (
          <>
            {legacyModelsPanel}
            <WorkspaceAiSettingsPanel initial={settings.data.workspace_ai} />
            <LocalIntelligenceSetup />
            <TranscriptionSetup />
          </>
        );
      })()}
      <BackupRestorePanel />
      <Panel title="Data and privacy (read-only)"><p>{t("Local-first means local persistence by default. Credential values are never shown.")}</p></Panel>
      <details className="settings-advanced"><summary>{t("Advanced and diagnostics")}</summary>
      <Panel title="Preference history (read-only)">
        <p className="hint">
          {t("Explicit means you directly chose it. Derived means the app inferred it from feedback. Temporary means it is used only until its expiry.")}
        </p>
        {prefs.data.history.length
          ? prefs.data.history.map((preference) => (
            <article className="metadata-row" key={preference.preference_id}>
              <span>
                <Status value={preference.provenance} />
              </span>
              <div>
                <strong>{preference.statement}</strong>
                <p>
                  {t(preferenceCopy(preference))}
                  {preference.expires_at
                    ? ` Expires ${humanDate(preference.expires_at)}.`
                    : ""}
                </p>
              </div>
            </article>
          ))
          : <Empty>No Preferences yet.</Empty>}
      </Panel>
      <Panel title="Source policy (read-only here)">
        <p className="hint">{t("Edit a Following to change its own processing policy.")}</p>
        <p>
          {language === "zh-CN"
            ? `未单独配置的关注默认采用：首次纳入 ${globalPolicy.initial_history_count} 个视频，每次检查最多 ${globalPolicy.per_run_max_new_videos} 个新视频，提炼方式为${t(STYLES.find(([value]) => value === globalPolicy.distillation_style)?.[1] ?? "Balanced")}。`
            : `Default for Followings without their own configuration: initial history ${globalPolicy.initial_history_count}, per-run limit ${globalPolicy.per_run_max_new_videos}, ${STYLES.find(([value]) => value === globalPolicy.distillation_style)?.[1] ?? "Balanced"} style.`}
        </p>
      </Panel>
      <Panel title="Models and cost (read-only)">
        <div className="capability-grid">
          {localFoundation && (
            <article className="capability-card">
              <div className="capability-heading">
                <h3>{t("Scoring and Summary")}</h3>
                <Status value={localFoundation.adapter_available ? "AVAILABLE" : "UNAVAILABLE"} />
              </div>
              <p>{localFoundation.adapter_available
                ? language === "zh-CN"
                  ? `使用本地模型 ${localFoundation.model} 运行；原始证据保留在这台 Mac 上。`
                  : `Runs locally with ${localFoundation.model}. Original Evidence remains on this Mac.`
                : t("The local model is unavailable; existing Content and Evidence remain readable.")}</p>
            </article>
          )}
          <article className="capability-card">
            <div className="capability-heading">
              <h3>{t("Intelligence")}</h3>
              <Status value={videoDistillation?.production_eligible ? "AVAILABLE" : "UNAVAILABLE"} />
            </div>
            <p>
              {t(videoDistillation?.production_eligible
                ? "Qualified for V1 video analysis. Each cloud execution requires your separate consent."
                : videoDistillation?.credential_status === "BLOCKED"
                ? "Moonshot K2.6 is qualified for V1 video analysis, but the runtime credential is unavailable. Cloud Intelligence cannot run until the backend receives the credential. Local Summary and Evidence remain usable; each future cloud execution still requires separate consent."
                : "No qualified Intelligence model is currently available. Local Summary and Evidence remain usable; cloud execution requires a separate explicit authorization.")}
            </p>
            {videoDistillation && (
              <details className="provenance">
                <summary>{t("Provider and model details")}</summary>
                <p>
                  {videoDistillation.provider} · {videoDistillation.model}
                </p>
                <p>{t("Scope: Video Distillation only.")}</p>
                <p>{t(videoDistillation.reason)}</p>
              </details>
            )}
          </article>
          <article className="capability-card">
            <div className="capability-heading">
              <h3>{t("Deep Analysis")}</h3>
              <Status value="UNAVAILABLE" />
            </div>
            <p>{t("Deep Analysis is unavailable.")}</p>
            <p className="hint">
              {t("Kimi is not authorized for this capability, and this screen cannot enable it.")}
            </p>
          </article>
        </div>
        {otherProviders.length > 0 && (
          <details className="provenance">
            <summary>{t("Other model options")}</summary>
            {otherProviders.map((provider) => (
              <p key={provider.provider}>
                {provider.provider}: {t("not available for production use.")}
              </p>
            ))}
          </details>
        )}
      </Panel>
      <Panel title="Resource Usage (read-only)">
        {usage.data.usage.length
          ? usage.data.usage.map((item) => (
            <article className="metadata-row" key={item.execution_id}>
              <div>
                <strong>{t(usageReason(item.reason))}</strong>
                <p>
                  {item.invocation_count} {t("calls")} · {item.duration_ms === null
                    ? t("Duration unavailable")
                    : `${t("Duration")} ${item.duration_ms}ms`}
                </p>
                <p>
                  {t("Token usage")}:{" "}
                  {item.input_tokens === null || item.output_tokens === null
                    ? t("Unavailable")
                    : `${item.input_tokens} ${t("input")} / ${item.output_tokens} ${t("output")}`};
                  {" "}{t("Cost")}: {item.cost_microunits === null
                    ? t("Unavailable")
                    : `${item.cost_microunits} ${t("microunits")}`}.
                </p>
                <Status value={item.status} />
              </div>
              <details className="provenance">
                <summary>{t("Technical details")}</summary>
                <p>
                  {t("Model")}: {item.actual_model ?? t("Unknown")}. {t("Provider")}:{" "}
                  {item.actual_provider ?? t("Unknown")}.
                </p>
              </details>
            </article>
          ))
          : (
            <Empty>
              No Resource Ledger entries yet. Values are never estimated.
            </Empty>
          )}
      </Panel>
      </details>
    </div>
  );
}
