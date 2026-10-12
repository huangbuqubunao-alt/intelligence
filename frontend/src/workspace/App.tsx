import { AddEntry } from "./AddEntry";
import { CreatorFollowForm, CreatorFollowingDetail, FollowCreatorFromContent, Tracking, trackingCopy, useCreatorFollowingCapability } from "./CreatorFollowing";
import { BilibiliImport, BilibiliCaptionStatus, bilibiliStatus } from "./BilibiliImport";
import { LocalImport, localStatus, localImportErrors } from "./LocalImport";
import { NativeImportActivity } from "./NativeLocalImport";
import { LocalTranscription, transcriptionCopy } from "./LocalTranscription";
import { TranscriptionSetup } from "./TranscriptionSetup";
import { ChangeEvent, FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { ApiRequestError, api, patch, post, put, uploadZip } from "../api/client";
import { ModelSettings } from "./ModelSettings";
import { Logo } from "./Logo";
import { FirstRunOnboarding, completeOnboarding, onboardingCompleted } from "./Onboarding";
import { DeltaTarget, KnowledgeDelta } from "./KnowledgeDelta";
import { Research } from "./Research";
import { savedLanguage, UiLanguageProvider, useUiLanguage } from "./uiLanguage";

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
  relations: { related_topic_id: string }[];
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
};
type SourcePolicy = {
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
  processing_job?: { status: string; stage: string; retry_at: string | null; error_code: string | null } | null;
  filename?: string;
  media_kind?: string;
  format?: string;
  imported_at?: string;
  source_language?: string | null;
  duration_seconds?: number | null;
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
  video: ContentItem;
  waiting_model_executions?: { execution_id: string; updated_at: string; can_cancel: boolean }[];
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
  const match = /^#Content\/([^/]+)$/.exec(location.hash);
  if (!match) return null;
  try { const value = decodeURIComponent(match[1]); return value && value.length <= 256 && !/[\p{Cc}\p{Cs}]/u.test(value) ? value : null; } catch { return null; }
}

function initialPage(): Page {
  const raw = location.hash.slice(1);
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

function useRemote<T>(path: string, refresh = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Keep the stable machine code so failures can be localized by code instead of
  // rendering backend English prose.
  const [errorCode, setErrorCode] = useState<string | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    setErrorCode(undefined);
    api<T>(path).then((value) => alive && setData(value)).catch((reason: Error) => {
      if (!alive) return;
      setError(reason.message);
      setErrorCode(reason instanceof ApiRequestError ? reason.code : undefined);
    });
    return () => {
      alive = false;
    };
  }, [path, refresh]);
  return { data, error, errorCode };
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
function Panel({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useUiLanguage();
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{t(title)}</h2>
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
  { error, code, hideRawMessage }: {
    error: string;
    code?: string;
    /** Hide raw backend prose; used by normal Deep Analysis product UI. */
    hideRawMessage?: boolean;
  },
) {
  const { language, t } = useUiLanguage();
  // These are browser transport failures, rather than service error prose.
  if (["Failed to fetch", "Load failed", "NetworkError when attempting to fetch resource."].includes(error)) {
    return <div className="semantic-state state-danger" role="alert">
      <p>{t("The local service is disconnected. Reopen Intelligence, then retry when the connection returns.")}</p>
      <button className="button button-secondary" onClick={() => window.location.reload()}>{t("Retry")}</button>
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
      </div>
    );
  }
  if (hideRawMessage) {
    return (
      <div className="semantic-state state-danger">
        <Status value="Blocked" />
        <p>{t("The operation could not be completed.")}</p>
      </div>
    );
  }
  return (
    <div className="semantic-state state-danger">
      <Status value="Blocked" />
      {language === "zh-CN" ? <p>{t("The operation could not be completed.")}</p> : null}
      <p>{error}</p>
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
function humanDate(value: string) {
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
  return <Status value={labels[kind] ?? kind} />;
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
export function intelligenceResultCopy(status: string) {
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
  sourceLanguage: string,
  targetLanguage: string,
): boolean {
  const source = sourceLanguage.trim().replace(/_/g, "-").toLowerCase();
  if (targetLanguage === "en") return source === "en" || source.startsWith("en-");
  if (targetLanguage === "zh-CN") {
    return ["zh-cn", "zh-hans", "zh-hans-cn"].includes(source);
  }
  return false;
}

function Evidence(
  { item, onOpenContent }: {
    item: Intelligence;
    onOpenContent?: (videoId: string) => void;
  },
) {
  const { language, t } = useUiLanguage();
  const [selectedMode, setSelectedMode] = useState<EvidenceDisplayMode | null>(null);
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [createdTranslations, setCreatedTranslations] = useState<Record<
    string,
    { excerpt: string; language: "zh-CN" | "en" }
  >>({});
  const card = item.card;
  const links = card?.evidence_links ?? [];
  if (!card || !links.length) return null;
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
          <small>{card.source_id} · {card.video_id}</small>
          {card.source_url
            ? <a href={card.source_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
            : null}
        </div>
        <div>
          <span>{t("Content")}</span>
          <strong>{card.video_title || card.video_id}</strong>
        </div>
      </div>
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
                          ? <blockquote>{translatedExcerpt}</blockquote>
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
                          ? <blockquote>{link.original_excerpt}</blockquote>
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
              <p>{timestampRange(link.start_ms, link.end_ms)}</p>
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
                    onClick={() => onOpenContent(card.video_id)}
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
function IntelligenceCard(
  { item, saved, onSaved, onOpenContent }: {
    item: Intelligence;
    saved: boolean;
    onSaved: () => void;
    onOpenContent?: (videoId: string) => void;
  },
) {
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [showTopicForm, setShowTopicForm] = useState(false);
  const [topicName, setTopicName] = useState(item.card?.video_title ?? "");
  const [topicBusy, setTopicBusy] = useState(false);
  const [topicError, setTopicError] = useState<string | null>(null);
  const [createdTopic, setCreatedTopic] = useState<string | null>(null);
  const toggle = async () => {
    setBusy(true);
    try {
      await post(
        saved ? "/saved-intelligence/unsave" : "/saved-intelligence/save",
        { intelligence_id: item.intelligence_id },
      );
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
  return (
    <article className="panel intelligence-card">
      <header className="intelligence-conclusion">
        <p className="section-label">{t("Conclusion")}</p>
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
      </div>
      <section className="intelligence-section">
        <h3>{t("Validation posture")}</h3>
        <p>{t(intelligenceValidationCopy(item.state ?? ""))}</p>
        <p className="hint">
          {t("This is a validation posture, not a numeric confidence score.")}
        </p>
      </section>
      <Evidence item={item} onOpenContent={onOpenContent} />
      <button
        className="button button-secondary"
        disabled={busy}
        onClick={toggle}
      >
        {t(busy ? "Saving…" : saved ? "Unsave" : "Save")}
      </button>
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
                  <button type="submit" className="button" disabled={topicBusy}>
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
  return <UiLanguageProvider><Workspace /></UiLanguageProvider>;
}

function Workspace() {
  const { t } = useUiLanguage();
  const [page, setPage] = useState<Page>(initialPage);
  const [refresh, setRefresh] = useState(0);
  // Add lives above refreshed/navigated pages: file chooser focus must not unmount it.
  const [addProvider, setAddProvider] = useState<"YOUTUBE" | "LOCAL" | null>(null);
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
        setPage("Content"); setContentTarget(target); setDeltaTarget(null); setResearchReturn(null);
        return;
      }
      const next = initialPage();
      setImported(false);
      setResearchReturn(null); setResearchEvidence(null);
      setContentTarget(null); setDeltaTarget(null);
      setPage(next);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const [deltaTarget, setDeltaTarget] = useState<DeltaTarget | null>(null);
  const [researchReturn, setResearchReturn] = useState<string | null>(null);
  const [researchEvidence, setResearchEvidence] = useState<string | null>(null);
  useEffect(() => {
    if (page !== "Content" || !researchEvidence) return;
    const focusEvidence = () => {
      const element = document.getElementById(`content-evidence-${researchEvidence}`);
      if (!element) return false;
      element.scrollIntoView({ block: "center" });
      element.setAttribute("tabindex", "-1"); element.focus({ preventScroll: true });
      return true;
    };
    if (focusEvidence()) return;
    const observer = new MutationObserver(() => { if (focusEvidence()) observer.disconnect(); });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [page, researchEvidence]);
  const changeHash = (hash: string) => {
    const next = `#${hash}`;
    // A no-op emits no event. Preserve a marker for an already queued real
    // assignment, but never create one for a no-op.
    if (location.hash === next) return;
    programmaticHash.current = next;
    location.hash = hash;
  };
  const navigate = (next: Page) => {
    setImported(false);
    setResearchReturn(null); setResearchEvidence(null);
    setContentTarget(null);
    setDeltaTarget(null);
    changeHash(next);
    setPage(next);
  };
  const openContent = (videoId: string) => {
    setDeltaTarget(null);
    setContentTarget(videoId);
    changeHash(`Content/${encodeURIComponent(videoId)}`);
    setPage("Content");
  };
  const openDelta = (target: DeltaTarget) => {
    const destinations: Record<DeltaTarget["kind"], Page> = {
      content: "Content", intelligence: "Intelligence", topic: "Topics", source: "Following",
    };
    setDeltaTarget(target);
    setContentTarget(target.kind === "content" ? target.id : null);
    changeHash(target.kind === "content" ? `Content/${encodeURIComponent(target.id)}` : destinations[target.kind]);
    setPage(destinations[target.kind]);
  };
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
          {pages.map((item) => (
            <button
              type="button"
              key={item}
              className={`nav-item ${page === item || (page === "Research" && item === "Intelligence") ? "active" : ""}`}
              aria-current={page === item || (page === "Research" && item === "Intelligence") ? "page" : undefined}
              onClick={() => navigate(item)}
            >
              {t(item)}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">{t("Evidence stays reachable")}</div>
      </aside>
      <main className="workspace-main">
        <header className="page-header">
          <div>
            <p className="eyebrow">{t("INTELLIGENCE")}</p>
            <h1>{t(page)}</h1>
            <p className="page-subtitle">{t(subtitles[page])}</p>
          </div>
          {researchReturn && page !== "Research" && <button className="button button-secondary" onClick={() => {
            const target = researchReturn; navigate("Research"); location.hash = target;
          }}>{t("Back to Research")}</button>}
        </header>
        <NativeImportActivity onOpen={openContent} errors={localImportErrors} routeKey={`${page}/${contentTarget ?? ""}`} modalOpen={addProvider !== null} />
        {page === "Research" && <Research onOpen={(kind, id, evidenceId) => {
          const returnTo = location.hash.slice(1);
          if (kind === "content") { openContent(id); setResearchEvidence(evidenceId ?? null); }
          else openDelta({ kind: "intelligence", id });
          setResearchReturn(returnTo);
        }} />}
        {page === "Home" && (
          <div className="dashboard-stack">
            <KnowledgeDelta refresh={refresh} onOpen={openDelta} />
            <Dashboard refresh={refresh} navigate={navigate} openContent={openContent} />
          </div>
        )}
        {page === "Following" && (
          <Sources
            refresh={refresh}
            onRefresh={() => setRefresh((value) => value + 1)}
            targetSourceId={deltaTarget?.kind === "source" ? deltaTarget.id : null}
            onAdd={setAddProvider}
          />
        )}
        {page === "Content" && (
          <>
            {imported && <p role="status" aria-live="polite">{t("File imported. Its processing status appears below.")}</p>}
            <ContentPage refresh={refresh} targetVideoId={contentTarget} onOpen={openContent} onClose={() => navigate("Content")} />
          </>
        )}
        {page === "Intelligence" && (
          deltaTarget?.kind === "intelligence"
            ? <IntelligenceDetail id={deltaTarget.id} openContent={openContent} onBack={() => navigate("Intelligence")} />
            : <IntelligencePage refresh={refresh} openContent={openContent} openResearch={() => navigate("Research")} />
        )}
        {page === "Topics" && <Topics refresh={refresh} targetTopicId={deltaTarget?.kind === "topic" ? deltaTarget.id : null} />}
        {page === "Settings" && <Settings refresh={refresh} />}
      </main>
      {addProvider !== null && <AddEntry initialLocal={addProvider === "LOCAL"} onClose={() => setAddProvider(null)} onSaved={() => { setAddProvider(null); setRefresh(value => value + 1); }} onImported={id => {
        setAddProvider(null); setRefresh(value => value + 1); setImported(true); openContent(id);
      }} />}
    </div>
  );
}
function Dashboard(
  { refresh, navigate, openContent }: {
    refresh: number;
    navigate: (page: Page) => void;
    openContent: (videoId: string) => void;
  },
) {
  const { t } = useUiLanguage();
  const { data, error } = useRemote<
    {
      intelligence?: Intelligence[];
      pinned_topics?: Topic[];
      weekly_v1?: unknown[];
      needs_attention?: SourceRun[];
      operations?: { source_count?: number };
    }
  >("/dashboard", refresh);
  const [onboardingDone, setOnboardingDone] = useState(onboardingCompleted);
  const finishOnboarding = () => { completeOnboarding(); setOnboardingDone(true); };
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Home…</Empty>;
  const intelligence = (data.intelligence ?? []).filter((item) =>
      item.status === "AVAILABLE" && item.trusted
    ),
    attention = data.needs_attention ?? [],
    topics = data.pinned_topics ?? [],
    hasWeeklyHistory = (data.weekly_v1 ?? []).length > 0;
  const isFreshLibrary = data.operations?.source_count === 0 &&
    !intelligence.length && !topics.length && !hasWeeklyHistory && !attention.length;
  if (isFreshLibrary && !onboardingDone) {
    return <FirstRunOnboarding onSkip={finishOnboarding} onAddFollowing={() => { finishOnboarding(); navigate("Following"); }} />;
  }
  if (!intelligence.length && !topics.length && !attention.length) {
    return (
      <div className="dashboard-stack">
        <Panel title="No important new intelligence yet.">
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
    <div className="dashboard-stack">
      <Panel title="What matters now">
        {intelligence.length
          ? intelligence.map((item) => (
            <IntelligenceCard
              key={item.intelligence_id ?? item.code}
              item={item}
              saved={false}
              onSaved={() => undefined}
              onOpenContent={openContent}
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
      <Panel title="Pinned Topics">
        {topics.length
          ? topics.map((topic) => (
            <p key={topic.topic_id}>
              <strong>{topic.name}</strong> · {t(statusLabel(topic.current_state))}
            </p>
          ))
          : <Empty>No pinned Topics yet.</Empty>}
      </Panel>
      {attention.length
        ? (
          <Panel title="Needs Attention">
            {attention.map((run) => <Attention key={run.run_id} run={run} />)}
          </Panel>
        )
        : null}
    </div>
  );
}
function Attention({ run }: { run: SourceRun }) {
  const { t } = useUiLanguage();
  const [title, safety, action] = attentionCopy(run.attention_reason);
  return (
    <article className="semantic-state state-blocked">
      <strong>{t(title)}</strong>
      <p>{t(safety)}</p>
      <p>{t(action)}</p>
    </article>
  );
}
function IntelligenceDetail({ id, openContent, onBack }: {
  id: string; openContent: (videoId: string) => void; onBack: () => void;
}) {
  const { t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const detail = useRemote<{ intelligence: Intelligence }>(`/intelligence/${id}`, revision);
  return <>
    <button type="button" className="button button-ghost" onClick={onBack}>{t("Back to Intelligence")}</button>
    {detail.error ? <ErrorState error={detail.error} code={detail.errorCode} hideRawMessage />
      : !detail.data ? <Empty>Loading verified Intelligence…</Empty>
      : <IntelligenceCard item={detail.data.intelligence} saved={false}
          onSaved={() => setRevision(value => value + 1)} onOpenContent={openContent} />}
  </>;
}
function IntelligencePage(
  { refresh, openContent, openResearch }: {
    refresh: number;
    openContent: (videoId: string) => void;
    openResearch: () => void;
  },
) {
  const { t } = useUiLanguage();
  const [view, setView] = useState<"Current" | "Saved">("Current");
  const [revision, setRevision] = useState(0);
  const current = useRemote<{ intelligence: Intelligence[]; activity?: { video_id: string; title: string; status: string }[] }>(
    "/intelligence",
    refresh + revision,
  );
  const saved = useRemote<{ saved: Saved[] }>(
    "/saved-intelligence",
    refresh + revision,
  );
  const source = view === "Current"
    ? current
    : saved;
  const currentAvailable = (current.data?.intelligence ?? []).filter((item) =>
    item.status === "AVAILABLE" && item.trusted
  );
  const researchEntry = <div className="button-row"><button type="button" className="button button-secondary" onClick={openResearch}>{t("Research")}</button></div>;
  if (source.error) return <>{researchEntry}<ErrorState error={source.error} /></>;
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
            onClick={() => setView(item)}
          >
            {t(item)}
          </button>
        ))}
      </div>
      {view === "Current" && current.data?.activity?.length ? <Panel title="Analysis activity">
        {current.data.activity.map(item => <article className="metadata-row" key={`${item.video_id}:${item.status}`}>
          <div><strong>{item.title}</strong><p>{t(intelligenceResultCopy(item.status))}</p>
            <button className="button button-secondary" onClick={() => openContent(item.video_id)}>{t("Open Content")}</button></div>
        </article>)}
      </Panel> : null}
      {view === "Current" && (!current.data
        ? <Empty>Loading verified Intelligence…</Empty>
        : currentAvailable.length
        ? currentAvailable.map((item) => (
          <IntelligenceCard
            key={item.intelligence_id ?? item.code}
            item={item}
            saved={false}
            onSaved={() => setRevision((value) => value + 1)}
            onOpenContent={openContent}
          />
        ))
        : current.data.activity?.length ? null : <Empty>No verified Intelligence yet.</Empty>)}
      {view === "Saved" && (!saved.data
        ? <Empty>Loading saved Intelligence…</Empty>
        : saved.data.saved.length
        ? saved.data.saved.map((item) => (
          <SavedCard
            key={item.intelligence_id}
            item={item}
            revision={revision}
            onChanged={() =>
              setRevision((value) => value + 1)}
            onOpenContent={openContent}
          />
        ))
        : <Empty>No saved Intelligence.</Empty>)}
    </>
  );
}
function SavedCard(
  { item, revision, onChanged, onOpenContent }: {
    item: Saved;
    revision: number;
    onChanged: () => void;
    onOpenContent: (videoId: string) => void;
  },
) {
  const { t } = useUiLanguage();
  const detail = useRemote<{ intelligence: Intelligence }>(
    `/intelligence/${item.intelligence_id}`,
    revision,
  );
  if (item.intelligence.status !== "AVAILABLE") {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>
          {t("This saved item is no longer available as current Intelligence. Its saved reference remains until you choose Unsave.")}
        </p>
        <button
          className="button button-secondary"
          onClick={async () => {
            await post("/saved-intelligence/unsave", {
              intelligence_id: item.intelligence_id,
            });
            onChanged();
          }}
        >
          {t("Unsave")}
        </button>
      </div>
    );
  }
  if (detail.error) return <ErrorState error={detail.error} />;
  if (!detail.data) return <Empty>Loading current saved Intelligence…</Empty>;
  return (
    <IntelligenceCard
      item={detail.data.intelligence}
      saved
      onSaved={onChanged}
      onOpenContent={onOpenContent}
    />
  );
}
function ContentPage(
  { refresh, targetVideoId, onOpen, onClose }: {
    refresh: number;
    targetVideoId?: string | null;
    onOpen: (id: string) => void;
    onClose: () => void;
  },
) {
  const { t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const list = useRemote<{ videos: ContentItem[] }>("/videos", refresh + revision);
  useEffect(() => {
    if (!list.data?.videos.some(item => ["WAITING", "FETCHING", "READING_CAPTIONS", "ORGANIZING", "TRANSCRIPT_READY", "RETRY_PENDING", "RUNNING", "PENDING"].includes(item.processing_status))) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [list.data]);
  if (list.error) return <ErrorState error={list.error} />;
  if (!list.data) return <Empty>Loading Content…</Empty>;
  if (targetVideoId) {
    return <ContentDetailPanel key={targetVideoId} id={targetVideoId} onClose={onClose} />;
  }
  return list.data.videos.length
    ? (
      <div className="compact-list">
        {list.data.videos.map((item) => (
          <button
            className="list-row"
            key={item.video_id}
            onClick={() => onOpen(item.video_id)}
          >
            <span>
              <strong>{item.title ?? item.video_id}</strong>
              <small>{item.provider === "LOCAL" ? t("Local") : item.provider === "BILIBILI" ? `${t("Bilibili")} · ${item.channel_name ?? ""}` : item.channel_name} · {humanDate(item.provider === "BILIBILI" ? item.published_at : item.imported_at ?? item.published_at)}</small>
            </span>
            <Status {...contentStatus(item.provider, item.processing_status)} />
          </button>
        ))}
      </div>
    )
    : (
      <Empty>
        No Content yet. Add a video link, follow a YouTube channel, or import a local file.
      </Empty>
    );
}
function ContentDetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const creatorCapability = useCreatorFollowingCapability();
  const { t } = useUiLanguage();
  const [refresh, setRefresh] = useState(0);
  const { data, error } = useRemote<ContentDetail>(`/videos/${id}`, refresh);
  const [evidenceRefresh, setEvidenceRefresh] = useState(0);
  const transcriptionRefreshId = useRef<string | null>(null);
  const [transcriptionStatus, setTranscriptionStatus] = useState<string | null>(null);
  const [showCloudTerms, setShowCloudTerms] = useState(false);
  const [cloudReview, setCloudReview] = useState<{
    execution_id: string;
    verified_input_hash: string;
    source_id: string;
    provider: string;
    model: string;
    evidence_ids: string[];
    cost_status: string;
  } | null>(null);
  const [cloudBusy, setCloudBusy] = useState(false);
  const [cloudError, setCloudError] = useState<string | null>(null);
  const [cancelFeedback, setCancelFeedback] = useState<string | null>(null);
  const [retryBusy, setRetryBusy] = useState(false);
  const [retryFeedback, setRetryFeedback] = useState<string | null>(null);
  useEffect(() => {
    if (!data || !["WAITING", "FETCHING", "READING_CAPTIONS", "ORGANIZING", "TRANSCRIPT_READY", "RETRY_PENDING", "RUNNING", "PENDING"].includes(data.video.processing_status)) return;
    const timer = setTimeout(() => setRefresh(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data]);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Content detail…</Empty>;
  if (data.video.work_kind) return <div className="dashboard-stack"><button className="button button-ghost" onClick={onClose}>{t("Back to Content")}</button><Panel title={data.video.title ?? id}><Status {...contentStatus(data.video.provider, data.video.processing_status)} /><p>{t("Import accepted. Processing and any required attention appear in Content.")}</p><a href={data.video.source_url ?? undefined} target="_blank" rel="noreferrer">{t("Open original source")}</a><button className="button button-secondary" onClick={async () => { try { await post(`/sources/${data.video.source_id}/check`, { command_id: commandId() }); setRefresh(value => value + 1); } catch { setCloudError("The source could not be checked. Try again later."); } }}>{t("Retry")}</button>{cloudError && <p role="alert">{t(cloudError)}</p>}</Panel></div>;
  const transcript = data.transcript;
  const isBilibili = data.video.provider === "BILIBILI";
  const isLocalMedia = data.video.provider === "LOCAL" && data.video.media_kind !== "TEXT";
  const note = data.note.v2;
  const visibleHistory = data.history.filter((event) =>
    event.type === "JOB_STATUS" || !event.type
  );
  // The offline transcription job owns the displayed state once it has one, so
  // a run in progress is not summarised by the snapshot status behind it.
  const readingStatus = isLocalMedia && transcriptionStatus
    ? { value: transcriptionStatus, label: transcriptionCopy(transcriptionStatus) }
    : contentStatus(
        data.video.provider,
        isLocalMedia && data.video.processing_status === "TRANSCRIPTION_UNAVAILABLE"
          ? "IMPORTED"
          : data.video.processing_status,
      );
  return (
    <div className="dashboard-stack">
      <button className="button button-ghost" onClick={onClose}>{t("Back to Content")}</button>
      <Panel title={data.video.title ?? data.video.video_id}>
        <div className={`reading-meta${isLocalMedia || isBilibili ? " local-media-meta" : ""}`}>
          <Status {...readingStatus} />
          <span>{data.video.provider === "LOCAL" ? t("Local") : isBilibili ? `${t("Bilibili")} · ${data.video.channel_name ?? ""}` : data.video.channel_name} · {humanDate(isBilibili ? data.video.published_at : data.video.imported_at ?? data.video.published_at)}</span>
          {data.video.media_kind && <span>{t(({TEXT:"Text",AUDIO:"Audio",VIDEO:"Video"} as Record<string,string>)[data.video.media_kind])}{isBilibili ? "" : ` · ${data.video.format}`}</span>}
          {data.video.source_language && <span>{t("Source language")}: {data.video.source_language === "und" ? t("Language unavailable") : data.video.source_language}</span>}
          {data.video.duration_seconds != null && <span>{t("Duration")}: {Math.ceil(data.video.duration_seconds)}s</span>}
        </div>
        {data.video.source_url
          ? (
            <a className="source-link" href={data.video.source_url} target="_blank" rel="noreferrer">
              {t("Open original source")}
            </a>
          )
          : null}
      </Panel>
      {data.video.source_id && ["RETRY_REQUIRED", "FAILED"].includes(data.video.processing_status) && <Panel title="Processing needs attention"><p>{t(data.video.retry_allowed === false ? "This Content needs source or processing readiness review before it can be processed again." : "Processing needs attention. Retry this Content when the connection is available.")}</p><button className="button button-secondary" disabled={retryBusy || data.video.retry_allowed === false} onClick={async () => { setRetryBusy(true); setRetryFeedback(null); try { await post(`/sources/${data.video.source_id}/check`, { command_id: commandId() }); setRetryFeedback("Retry accepted. Processing status will update here."); setRefresh(value => value + 1); } catch { setRetryFeedback("The source could not be checked. Try again later."); } finally { setRetryBusy(false); } }}>{t(retryBusy ? "Retrying…" : "Retry")}</button>{retryFeedback && <p role="status">{t(retryFeedback)}</p>}</Panel>}
      {isBilibili && data.video.processing_status !== "SOURCE_UNAVAILABLE" && <FollowCreatorFromContent id={id} capability={creatorCapability} />}
      {data.video.provider === "YOUTUBE" && data.video.channel_id && /^UC[A-Za-z0-9_-]{22}$/.test(data.video.channel_id) && <FollowCreatorFromContent id={id} provider="YOUTUBE" />}
      <Panel title={data.video.provider === "LOCAL" && data.video.media_kind === "TEXT" ? "Source text" : "Transcript"}>
        {isBilibili && <BilibiliCaptionStatus id={id} status={data.video.processing_status} onCompleted={() => { setRefresh(value => value + 1); setEvidenceRefresh(value => value + 1); }} />}
        {isLocalMedia && <LocalTranscription id={id} onStatusChange={setTranscriptionStatus} onCompleted={() => { if (transcriptionRefreshId.current === id) return; transcriptionRefreshId.current = id; setRefresh(value => value + 1); setEvidenceRefresh(value => value + 1); }} />}
        {transcript.status === "AVAILABLE" && transcript.text
          ? transcript.timed_segments?.length
            ? <ol className="timed-transcript">{transcript.timed_segments.map((segment, index) => <li key={index}><time>{(segment.start_ms / 1000).toFixed(3)}s – {(segment.end_ms / 1000).toFixed(3)}s</time><span>{segment.text}</span></li>)}</ol>
            : <div className="transcript-copy">{transcript.text}</div>
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
      <Panel title={data.video.provider === "LOCAL" || isBilibili ? "Summary" : "Summary / Video Notes"}>
        {note?.status === "AVAILABLE"
          ? (
            <div className="summary-note">
              <div className="reading-meta">
                <Status value="AVAILABLE" />
                <span>{!note.language || note.language === "und" ? t("Language unavailable") : note.language}</span>
              </div>
              {note.method === "SOURCE_EXCERPTS" && <p className="hint">{t("These are original source excerpts, selected deterministically without a model or new interpretation.")}</p>}
              {note.summary ? <><h3>{t("Summary")}</h3><p>{note.summary}</p></> : null}
              {note.core_points?.length
                ? <><h3>{t("Key points")}</h3><ul>{note.core_points.map((point) => <li key={point}>{point}</li>)}</ul></>
                : null}
              {note.timestamped_key_points?.length
                ? (
                  <>
                    <h3>{t("Timestamped key points")}</h3>
                    <ol>
                      {note.timestamped_key_points.map((point) => (
                        <li key={`${point.start_seconds}:${point.text}`}>
                          {data.video.source_url
                            ? (
                              <a
                                className="source-link"
                                href={videoAt(data.video.source_url, point.start_seconds * 1000)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {timestamp(point.start_seconds * 1000)}
                              </a>
                            )
                            : <strong>{timestamp(point.start_seconds * 1000)}</strong>} · {point.text}
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
                          <p>{reference.excerpt}</p>
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
          )
          : (
            <div className="semantic-state state-neutral">
              <Status value="UNAVAILABLE" />
              <p>{t("Summary / Video Notes are not available for this Content yet. No summary is fabricated from missing output.")}</p>
            </div>
          )}
      </Panel>
      <DeepAnalysisPanel
        videoId={data.video.video_id}
        onCompleted={() => setEvidenceRefresh((value) => value + 1)}
      />
      <ContentEvidencePanel
        videoId={data.video.video_id}
        sourceUrl={data.video.source_url}
        refresh={evidenceRefresh}
      />
      <Panel title="Intelligence result">
        <div className="semantic-state state-neutral">
          <Status value={data.intelligence_result.status} />
          <p role={data.intelligence_result.status === "CANCELLED" ? "status" : undefined}>{t(intelligenceResultCopy(data.intelligence_result.status))}</p>
          {cancelFeedback && data.intelligence_result.status !== "CANCELLED" && <p role="status">{cancelFeedback}</p>}
          {Boolean(data.waiting_model_executions?.length) && <div>
            <p>{t("No qualified Intelligence model is currently available.")}</p>
            {data.waiting_model_executions?.map((wait) => <div className="button-row" key={wait.execution_id}>
              <span className="hint">{humanDate(wait.updated_at)}</span>
              {wait.can_cancel ? <button type="button" className="button button-secondary" disabled={cloudBusy} onClick={async () => {
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
            </div>)}
          </div>}
          {data.manual_intelligence_eligible && <div className="button-row">
            <button type="button" className="button button-primary" disabled={cloudBusy || Boolean(data.waiting_model_executions?.length)} onClick={async () => {
              setCloudBusy(true); setCloudError(null); setCancelFeedback(null);
              try { await post(`/videos/${id}/intelligence`, { command_id: commandId() }); setRefresh(value => value + 1); }
              catch { setCloudError(t("Intelligence could not start. Check model readiness and try again.")); }
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
          {data.intelligence_result.status === "WAITING_MODEL" && note?.status === "AVAILABLE"
            ? (
              <div>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setShowCloudTerms((current) => !current)}
                >
                  {t("Review high-quality Intelligence")}
                </button>
                {showCloudTerms
                  ? (
                    <div className="semantic-state state-neutral">
                      <h3>{t("Cloud Intelligence disclosure")}</h3>
                      <p>{t("Provider: Moonshot · Model: kimi-k2.6 (thinking disabled).")}</p>
                      <p>{t("Only bounded, verified Evidence excerpts and the task context needed for this Intelligence judgment would leave this device. The full database, unrelated Content, Followings, library, and credentials are excluded. Your original Evidence remains authoritative here.")}</p>
                      <p>{t("Moonshot API usage is billed separately and may incur charges. Cost for this execution: UNKNOWN before the response. Published China-platform K2.6 rates: ¥6.50 per million uncached input tokens, ¥1.10 per million cached input tokens, and ¥27 per million output tokens. This request allows up to 8,192 output tokens.")}</p>
                      {data.cloud_intelligence_available
                        ? (
                          <>
                            <p>{t("Preparing a review stores a local reservation only. Confirming authorizes exactly one request for the reviewed Evidence and task context.")}</p>
                            <button type="button" className="button button-secondary" disabled={cloudBusy}
                              onClick={async () => {
                                setCloudBusy(true);
                                setCloudError(null);
                                try {
                                  const response = await post<{ review: NonNullable<typeof cloudReview> }>(
                                    `/videos/${id}/cloud-intelligence/review`, data.manual_intelligence_eligible ? { command_id: commandId() } : {},
                                  );
                                  setCloudReview(response.review);
                                } catch (reason) {
                                  setCloudError((reason as Error).message);
                                } finally { setCloudBusy(false); }
                              }}>{t("Prepare one request for review")}</button>
                            {cloudReview && (
                              <div>
                                <p>{t("Source")}: {cloudReview.source_id}. {t("Evidence items")}: {cloudReview.evidence_ids.length}. {t("Provider/model")}: {cloudReview.provider} · {cloudReview.model}. {t("Cost")}: {t(cloudReview.cost_status)}.</p>
                                <p>{t("Review the original Evidence on this Content page before confirming. This permission applies only to this execution.")}</p>
                                <button type="button" className="button" disabled={cloudBusy}
                                  onClick={async () => {
                                    setCloudBusy(true);
                                    setCloudError(null);
                                    try {
                                      await post(`/videos/${id}/cloud-intelligence/confirm`, {
                                        execution_id: cloudReview.execution_id,
                                        review_hash: cloudReview.verified_input_hash,
                                        authorize: true,
                                      });
                                      setCloudReview(null);
                                      setRefresh((value) => value + 1);
                                    } catch (reason) {
                                      setCloudError((reason as Error).message);
                                    } finally { setCloudBusy(false); }
                                  }}>{t("Authorize this one cloud execution")}</button>
                              </div>
                            )}
                            {cloudError && <p role="alert">{cloudError}</p>}
                          </>
                        )
                        : <p>{t("Cloud execution is currently unavailable. This review does not authorize a request or send data.")}</p>}
                    </div>
                  )
                  : null}
              </div>
            )
            : null}
        </div>
      </Panel>
      <Panel title="Processing history">
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
  { videoId, onCompleted }: { videoId: string; onCompleted: () => void },
) {
  const { t } = useUiLanguage();
  const [refresh, setRefresh] = useState(0);
  const { data, error, errorCode } = useRemote<DeepAnalysisEnvelope>(
    `/videos/${videoId}/deep-analysis`,
    refresh,
  );
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [preflight, setPreflight] = useState<DeepAnalysisPreflight | null>(null);
  const [costAcknowledged, setCostAcknowledged] = useState(false);
  const [dispatchBlocked, setDispatchBlocked] = useState(false);
  useEffect(() => { setPreflight(null); setCostAcknowledged(false); setDispatchBlocked(false); }, [videoId]);

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
  const availability = status?.availability ?? "NOT_REQUESTED";
  const canRun = (status?.production_eligible ?? status?.qualified) === true && !busy && !dispatchBlocked && !preflight;

  return (
    <Panel title={t("Deep Analysis")}>
      <p className="hint">
        {t("Summary explains what this content says. Deep Analysis is a separate, on-demand action for the conclusions, evidence, uncertainty, what it means for you, and what to investigate next.")}
      </p>
      {error ? <ErrorState error={error} code={errorCode} hideRawMessage /> : null}
      {actionError ? (
        <p className="semantic-state state-neutral">{t(actionError)}</p>
      ) : null}
      {result ? (
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
            <DeepAnalysisStatusLabel value={availability} />
          </span>
          <p>{t(deepAnalysisReasonCopy(availability, status?.reason_code ?? null))}</p>
        </div>
      )}
      {(status?.routes ?? []).map((route) => (
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
        {status && !status.qualified ? (
          <span className="hint">
            {t("Unavailable until a model is qualified for Deep Analysis.")}
          </span>
        ) : null}
      </div>
      <DeepAnalysisPublishAction
        key={`${videoId}:${result?.result_identity ?? "none"}`}
        videoId={videoId}
        resultIdentity={durableCitations ? result?.result_identity ?? null : null}
      />
    </Panel>
  );
}

function DeepAnalysisPublishAction({ videoId, resultIdentity }: { videoId: string; resultIdentity: string | null }) {
  const { t } = useUiLanguage();
  type PublishState = { state: string; result_identity?: string; relative_path?: string };
  const path = `/videos/${videoId}/deep-analysis/obsidian`;
  const { data, error } = useRemote<{ publish: PublishState }>(path);
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
  const state = outcome?.state ?? (error ? "WRITE_FAILED" : status?.state === "AVAILABLE" && resultIdentity !== null && status.result_identity !== resultIdentity ? "RESULT_CHANGED" : status?.state);
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
      {state && state !== "AVAILABLE" ? <p role="status" className="hint">{t(copy[state] ?? copy.WRITE_FAILED)}</p> : null}
      {outcome?.relative_path ? <p className="hint deep-analysis-publish-path">{outcome.relative_path}</p> : null}
    </div>
  );
}

function ContentEvidencePanel(
  { videoId, sourceUrl, refresh }: { videoId: string; sourceUrl: string | null; refresh: number },
) {
  const { language, t } = useUiLanguage();
  const { data, error } = useRemote<{ evidence: ContentEvidence[] }>(
    `/videos/${encodeURIComponent(videoId)}/evidence`,
    refresh,
  );
  const [selectedMode, setSelectedMode] = useState<EvidenceDisplayMode | null>(null);
  const [translationBusy, setTranslationBusy] = useState<string | null>(null);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [createdTranslations, setCreatedTranslations] = useState<Record<
    string,
    { excerpt: string; language: "zh-CN" | "en" }
  >>({});
  const evidencePanelTitle = data?.evidence?.some(item => item.locator_type === "TEXT_RANGE") ? "Evidence · source text" : "Evidence · source transcript";
  if (error) {
    return (
      <Panel title={evidencePanelTitle}>
        <p className="hint">{t("Canonical Evidence could not be loaded. The Summary remains available with its own recorded references.")}</p>
      </Panel>
    );
  }
  if (!data) {
    return <Panel title={evidencePanelTitle}><Empty>Loading canonical Evidence…</Empty></Panel>;
  }
  const evidence = data.evidence ?? [];
  const hasPreferredTranslation = evidence.some((item) => {
    const local = createdTranslations[item.evidence_id];
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
      setSelectedMode("译文");
    } catch {
      setTranslationError("Could not create a verified local translation. Original Evidence is still available.");
    } finally {
      setTranslationBusy(null);
    }
  };
  return (
    <Panel title={evidencePanelTitle}>
      {evidence.length
        ? (
          <div className="evidence-trace-list">
            {evidence.map((item) => {
              const local = createdTranslations[item.evidence_id];
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
              return (
                <article className="evidence-item evidence-trace-item" id={`content-evidence-${encodeURIComponent(item.evidence_id)}`} key={item.evidence_id}>
                  <div className="reading-meta">
                    <span>{t("Source language")}: {item.source_language} · {t(item.locator_type === "TEXT_RANGE" ? "Original source text" : evidenceLineageLabel(item.lineage_kind))}</span>
                    <strong>{item.evidence_id}</strong>
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
                          ? <blockquote>{translatedExcerpt}</blockquote>
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
                        <blockquote>{item.original_excerpt}</blockquote>
                      </div>
                    )
                    : null}
                  {mode === "原文" && !translationAvailable && !sourceMatchesTarget
                    ? <p className="hint">{t("Translation unavailable.")}</p>
                    : null}
                  {translationError ? <p className="hint" role="alert">{t(translationError)}</p> : null}
                  <div>
                    <strong>{t("Source position")}</strong>
                    <p>{item.locator_type === "TEXT_RANGE" ? `${t("Lines")} ${item.start_line}–${item.end_line}` : timestampRange(item.start_ms, item.end_ms)}</p>
                  </div>
                  <div>
                    <strong>{t("Provenance")}</strong>
                    <p>{t(item.locator_type === "TEXT_RANGE" ? "Original source text" : evidenceLineageLabel(item.lineage_kind))} · {t(evidenceRoleLabel(item.role))}</p>
                    <small>{item.artifact_id} · {item.created_at ? humanDate(item.created_at) : "Timestamp unavailable"}</small>
                  </div>
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
                </article>
              );
            })}
          </div>
        )
        : <Empty>No available, verified canonical transcript Evidence is recorded for this Content.</Empty>}
    </Panel>
  );
}
function Topics({ refresh, targetTopicId }: { refresh: number; targetTopicId?: string | null }) {
  const { t } = useUiLanguage();
  const list = useRemote<{ topics: Topic[] }>("/topics", refresh);
  const [selected, setSelected] = useState<string | null>(targetTopicId ?? null);
  const detail = useRemote<{ topic: Topic }>(
    selected ? `/topics/${selected}` : "/topics",
  );
  if (list.error || detail.error) {
    return <ErrorState error={list.error ?? detail.error ?? ""} />;
  }
  if (!list.data) return <Empty>Loading Topics…</Empty>;
  if (!selected) {
    return (
      <>
        {list.data.topics.length
          ? list.data.topics.map((topic) => (
            <button
              className="list-row"
              key={topic.topic_id}
              onClick={() => setSelected(topic.topic_id)}
            >
              <span>
                <strong>{topic.name}</strong>
                <small>
                  {t("Current understanding")}: {t(statusLabel(topic.current_state))}
                </small>
              </span>
              <Status value={topic.pinned ? "PINNED" : topic.lifecycle} />
            </button>
          ))
          : <Empty>No Topics yet.</Empty>}
      </>
    );
  }
  if (!detail.data?.topic) return <Empty>Loading Topic detail…</Empty>;
  const topic = detail.data.topic;
  return (
    <div className="dashboard-stack">
      <button className="button button-ghost" onClick={() => setSelected(null)}>
        {t("Back to Topics")}
      </button>
      <Panel title={topic.name}>
        <h3>{t("Current understanding")}</h3>
        <p>{t(statusLabel(topic.current_state))}.</p>
        <p>
          {t(topic.independence === "UNKNOWN"
            ? "Not enough reliable information yet to determine how independent the supporting sources are."
            : "This understanding is based on the available supporting sources.")}
        </p>
        <button
          className="button button-secondary"
          onClick={() =>
            post(`/topics/${topic.topic_id}/pin`, { pinned: !topic.pinned })
              .then(() => setSelected(null))}
        >
          {t(topic.pinned ? "Unpin Topic" : "Pin Topic")}
        </button>
      </Panel>
      <Panel title="Evidence">
        {topic.contributions.length
          ? topic.contributions.map((contribution) => (
            <article
              key={`${contribution.intelligence_id}:${contribution.claim_kind}`}
            >
              <Claim kind={contribution.claim_kind} />{" "}
              <Status
                value={contribution.available
                  ? contribution.state
                  : "UNAVAILABLE"}
              />
              <p>
                {contribution.available
                  ? t("A current contribution supports this topic.")
                  : t("Some supporting information is no longer available.")}
              </p>
              <details className="provenance">
                <summary>{t("Technical evidence references")}</summary>
                <p>{contribution.evidence_ids.join(", ")}</p>
              </details>
            </article>
          ))
          : <Empty>No current supporting information.</Empty>}
      </Panel>
      <Panel title="Timeline">
        {topic.timeline.length
          ? topic.timeline.map((event) => (
            <p key={event.event_id}>
              {humanDate(event.created_at)} · {t(statusLabel(event.state))}
            </p>
          ))
          : <Empty>No historical events.</Empty>}
      </Panel>
      <Panel title="Related Topics">
        {topic.relations.length
          ? topic.relations.map((relation) => (
            <p key={relation.related_topic_id}>{t("Related topic")}</p>
          ))
          : <Empty>No related Topics.</Empty>}
      </Panel>
    </div>
  );
}

function Sources(
  { refresh, onRefresh, targetSourceId, onAdd }: { refresh: number; onRefresh: () => void; targetSourceId?: string | null; onAdd: (provider: "YOUTUBE" | "LOCAL") => void },
) {
  const { t } = useUiLanguage();
  const { data, error } = useRemote<{ sources: Source[] }>("/sources", refresh);
  const [selected, setSelected] = useState<string | null>(targetSourceId ?? null);
  const [filter, setFilter] = useState("all");
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowMessage, setRowMessage] = useState<string | null>(null);
  useEffect(() => {
    if (!data?.sources.some(source => source.tracking?.checking)) return;
    const timer = setTimeout(onRefresh, 2000);
    return () => clearTimeout(timer);
  }, [data]);
  useEffect(() => {
    const check = () => { if (document.visibilityState !== "hidden") void post("/sources/check-stale", {}).then(onRefresh).catch(() => {}); };
    check(); window.addEventListener("focus", check);
    return () => window.removeEventListener("focus", check);
  }, []);
  const creatorCapability = useCreatorFollowingCapability();
  const creatorFollowingWithdrawn = creatorCapability.known &&
    creatorCapability.capability !== null && !creatorCapability.capability.available;
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Sources…</Empty>;
  const followingSources = data.sources.filter(source => source.source_type !== "VIDEO_URL");
  return (
    <>
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
              <option value="insights">{t("Produces new insights")}</option><option value="attention">{t("Needs attention")}</option>
              <option value="paused">{t("Paused")}</option>
            </select></label>
            {followingSources.filter(source => !source.tracking_parent_source_ids?.length).filter(source => filter === "all" || (filter === "updates" && (source.tracking?.update_count ?? 0) > 0)
              || (filter === "insights" && (source.insight_count ?? 0) > 0)
              || (filter === "attention" && Boolean((source.source_type === "CHANNEL" && !source.tracking) || (source.provider === "BILIBILI" && source.tracking && creatorFollowingWithdrawn) || source.last_error || (source.tracking?.pending_count ?? 0) > 0 || (source.tracking?.processing_count ?? 0) > 0 || (source.tracking?.unavailable_count ?? 0) > 0))
              || (filter === "paused" && !source.enabled)).map((source) => (
              <div className="list-row source-row" key={source.source_id} data-source-id={source.source_id}>
                <button
                  className="source-select"
                  onClick={() =>
                    setSelected(source.source_id)}
                >
                  <span>
                    <strong>{source.provider === "LOCAL" ? t("Local library") : sourceLabel(source)}</strong>
                    <small>
                      {t(sourceSummary(source, creatorFollowingWithdrawn))} · {source.provider === "LOCAL" ? t("Local") : source.provider === "BILIBILI" ? t("Bilibili") : "YouTube"}
                    </small>
                  </span>
                </button>
                <div className="source-actions">
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
            ))}
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
          onAddLocal={() => { setSelected(null); onAdd("LOCAL"); }}
          onClose={() => setSelected(null)}
          onRefresh={onRefresh}
        />
      )}
    </>
  );
}
function ruleList(value: string) {
  return value.split(/[,，]/).map((item) => item.trim()).filter(Boolean);
}
function SourceForm(props: Parameters<typeof ExistingSourceForm>[0]) {
  return props.source ? <ExistingSourceForm {...props} /> : <AddEntry onClose={props.onClose} onSaved={props.onSaved} initialLocal={props.initialProvider === "LOCAL"} />;
}
export function ExistingSourceForm(
  { onClose, onSaved, source, policy, policyModes, schedules, initialProvider = "YOUTUBE" }: {
    initialProvider?: "YOUTUBE" | "LOCAL" | "BILIBILI";
    onClose: () => void;
    onSaved: () => void;
    source?: Source;
    policy?: SourcePolicy;
    policyModes?: SourcePolicyModes;
    schedules?: Schedule[];
  },
) {
  const { t } = useUiLanguage();
  const [providerChoice,setProviderChoice] = useState(initialProvider);
  const [youtubeMode, setYoutubeMode] = useState<"video" | "channel">("video");
  const globalPolicy = useRemote<{ policy: SourcePolicy }>("/settings/source-policy", 0);
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
  const [focus, setFocus] = useState(policy?.focus_rules.join(", ") ?? "");
  const [ignore, setIgnore] = useState(policy?.ignore_rules.join(", ") ?? "");
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
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!source && /^(?:@|UC|https:\/\/(?:www\.)?youtube\.com\/(?:@|channel\/))/.test(url.trim())) {
      setError(t("Use Follow a channel to follow from now on without importing existing videos."));
      return;
    }
    const effectiveFocus = focusMode === "INHERIT" ? globalPolicy.data?.policy?.focus_rules ?? [] : ruleList(focus);
    if (processingPolicy === "STANDARD_INTELLIGENCE" && !effectiveFocus.length) {
      setError(t("Add at least one focus word to let the app select relevant videos for insight extraction."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let sourceId = source?.source_id;
      if (!sourceId) {
        const created = await post<{ source: Source }>("/sources", {
          url,
          processing_policy: processingPolicy,
        });
        sourceId = created.source.source_id;
      }
      await patch(`/sources/${sourceId}`, {
        enabled,
        processing_policy: processingPolicy,
      });
      await put(`/sources/${sourceId}/policy`, {
        command_id: commandId(),
        initial_history_count: Number(initialHistory),
        per_run_max_new_videos: Number(perRunLimit),
        focus_mode: focusMode,
        focus_rules: focusMode === "INHERIT" ? [] : ruleList(focus),
        ignore_mode: ignoreMode,
        ignore_rules: ignoreMode === "INHERIT" ? [] : ruleList(ignore),
        distillation_style_mode: styleMode,
        distillation_style: styleMode === "INHERIT" ? null : style,
      });
      if (frequency !== "MANUAL") {
        await post("/automation", {
          schedule_id: schedule?.schedule_id,
          target_type: "SOURCE_CHECK",
          target_id: sourceId,
          frequency,
          weekday: frequency === "WEEKLY" ? 1 : null,
          local_time: time,
          timezone: "Asia/Shanghai",
          enabled: scheduleEnabled,
        });
      }
      onSaved();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The Source could not be saved.",
      );
    } finally {
      setBusy(false);
    }
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
        {!source && <div className="button-row" aria-label={t("Source provider")}><button className="button button-primary" aria-pressed="true">YouTube</button><button className="button button-secondary" onClick={() => setProviderChoice("LOCAL")}>{t("Local files")}</button><button className="button button-secondary" onClick={() => setProviderChoice("BILIBILI")}>{t("Bilibili")}</button></div>}
        {!source && <div className="button-row" aria-label={t("YouTube source type")}>
          <button className="button button-secondary" aria-pressed={youtubeMode === "video"} onClick={() => setYoutubeMode("video")}>{t("Add one video")}</button>
          <button className="button button-secondary" aria-pressed={youtubeMode === "channel"} onClick={() => setYoutubeMode("channel")}>{t("Follow a channel")}</button>
        </div>}
        {!source && youtubeMode === "channel" ? <CreatorFollowForm provider="YOUTUBE" onSaved={onSaved} /> : <form onSubmit={submit}><details><summary>{t("Advanced source configuration")}</summary>
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
              <select aria-label={t("Focus preference")} value={focusMode} onChange={(event) => setFocusMode(event.target.value as "INHERIT" | "OVERRIDE")}>
                <option value="INHERIT">{t("Use global interests")}</option>
                <option value="OVERRIDE">{t("Set for this Following")}</option>
              </select>
            </label>
            {focusMode === "INHERIT" ? <p className="hint">{t("Global focus")}: {globalPolicy.data?.policy?.focus_rules.join("、") || t("Not set")}</p> : null}
            {focusMode === "OVERRIDE" ? <label className="field">
              {t("Focus")}<input
                aria-label={t("Focus")}
                value={focus}
                onChange={(event) => setFocus(event.target.value)}
                placeholder={t("Comma-separated terms")}
              />
              <small>{t("Use simple terms that help choose what is relevant.")}</small>
              {processingPolicy === "STANDARD_INTELLIGENCE" && !ruleList(focus).length
                ? <small>{t("Add at least one focus word to let the app select relevant videos for insight extraction.")}</small>
                : null}
            </label> : null}
            <label className="field">
              {t("Ignore preference")}
              <select aria-label={t("Ignore preference")} value={ignoreMode} onChange={(event) => setIgnoreMode(event.target.value as "INHERIT" | "OVERRIDE")}>
                <option value="INHERIT">{t("Use global interests")}</option>
                <option value="OVERRIDE">{t("Set for this Following")}</option>
              </select>
            </label>
            {ignoreMode === "INHERIT" ? <p className="hint">{t("Global ignore")}: {globalPolicy.data?.policy?.ignore_rules.join("、") || t("Not set")}</p> : null}
            {ignoreMode === "OVERRIDE" ? <label className="field">
              {t("Ignore")}<input
                aria-label={t("Ignore")}
                value={ignore}
                onChange={(event) => setIgnore(event.target.value)}
                placeholder={t("Comma-separated terms")}
              />
              <small>
                {t("Use simple terms to exclude videos from automatic relevance selection.")}
              </small>
            </label> : null}
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
          {error && <ErrorState error={error} />}
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
              disabled={busy}
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
  { id, onClose, onRefresh, onAddLocal }: {
    id: string;
    onClose: () => void;
    onRefresh: () => void;
    onAddLocal: () => void;
  },
) {
  const { t } = useUiLanguage();
  const creatorCapability = useCreatorFollowingCapability();
  const [refresh, setRefresh] = useState(0);
  const { data, error } = useRemote<
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
  >(`/sources/${id}`, refresh);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    if (
      !data?.source_runs.some((run) =>
        ["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(run.state)
      )
    ) return;
    const timer = window.setTimeout(() => setRefresh((value) => value + 1), 1000);
    return () => window.clearTimeout(timer);
  }, [data]);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Source…</Empty>;
  if (data.source.tracking) return <CreatorFollowingDetail id={id} capability={creatorCapability} onClose={onClose} onRefresh={onRefresh} />;
  if (data.source.source_type === "CHANNEL" && !data.source.tracking) return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={sourceLabel(data.source)}>
    <div className="modal-head"><h2>{sourceLabel(data.source)}</h2><button className="button button-ghost" aria-label={t("Close")} onClick={onClose}>{t("Close")}</button></div>
    <p role="status">{t("Legacy channel needs attention. Re-add explicitly to establish tracking; its history is preserved.")}</p>
    <a href={data.source.canonical_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
  </section></div>;
  if (data.source.provider === "BILIBILI") return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t("Bilibili")}>
    <div className="modal-head"><h2>{sourceLabel(data.source)}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    <p>{t("This Following contains one imported video. Creator monitoring is not enabled.")}</p>
    <ul>{data.recent_videos.map(content => <li key={content.video_id}><a href={`#Content/${content.video_id}`} onClick={onClose}>{content.title}</a></li>)}</ul>
  </section></div>;
  if (data.source.provider === "LOCAL") return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t("Local library")}>
    <div className="modal-head"><h2>{t("Local library")}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
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
  vault_excluded: boolean;
};

type BackupRestoreStatus = {
  ready: boolean;
  reasons: string[];
  message: string;
  restore_pending: boolean;
  last_restore?: { state: string; message: string } | null;
};

const backupReasonCopy: Record<string, string> = {
  SOURCE_RUN_ACTIVE: "a Source Run is still working",
  DISTILLATION_ACTIVE: "a distillation is still running",
  JOBS_ACTIVE: "a background job is still running",
  PROVIDER_CALL_UNRESOLVED: "a provider call has an unresolved outcome",
  PROVIDER_DISPATCH_UNRESOLVED: "a provider dispatch has an unresolved outcome",
  RESTORE_PENDING: "a restore is pending",
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
 * would also hide *what* is still running. Each fragment is translated on its
 * own because the sentence is assembled here.
 */
function backupReadiness(status: BackupRestoreStatus | null) {
  if (!status) return { lead: "Checking whether core data is safe to back up…", items: [] as string[] };
  if (status.restore_pending) return { lead: "A restore is pending. Intelligence restarts before processing resumes.", items: [] as string[] };
  if (status.ready) return { lead: "Core data is quiescent and ready for backup.", items: [] as string[] };
  const items = status.reasons
    .map((reason) => backupReasonCopy[reason])
    .filter((value): value is string => value !== undefined);
  return items.length
    ? { lead: "Backup is unavailable while these are still running:", items }
    : { lead: "Backup is unavailable while other work is still in flight.", items: [] as string[] };
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
    try {
      const result = await api<{ status: BackupRestoreStatus }>("/backup-restore/status");
      setStatus(result.status);
      setStatusError(null);
    } catch (reason) {
      setStatusError("Backup status is unavailable. Check the local connection and retry.");
    }
  };

  useEffect(() => {
    void refreshStatus();
    const timer = window.setInterval(() => void refreshStatus(), 10_000);
    return () => window.clearInterval(timer);
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
      await post("/backup-restore/restore/confirm", { restore_id: restore.restore_id });
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
      <div><dt>{t("DATA artifacts")}</dt><dd>{value.data_artifact_count} · {byteSize(value.data_size_bytes)}</dd></div>
    </dl>
  );

  const readiness = backupReadiness(status);
  return (
    <Panel title="Backup and Restore">
      <p>{t("Backups include Intelligence core data and persisted settings. External Vault content, credentials, and model files are excluded.")}</p>
      <p className="hint" role="status">
        {t(readiness.lead)}
        {readiness.items.length > 0 && ` ${readiness.items.map((item) => t(item)).join(" ")}`}
      </p>
      <div className="button-row">
        <button type="button" onClick={createBackup} disabled={busy || !status?.ready}>
          {t(busy ? "Working…" : "Create Backup")}
        </button>
        <label className="button secondary-button">
          {t("Choose backup")}
          <input
            aria-label={t("Choose backup file")}
            type="file"
            accept=".zip,application/zip"
            disabled={busy || status?.restore_pending}
            onChange={chooseBackup}
          />
        </label>
      </div>
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
      {status?.last_restore?.state === "APPLIED" ? (
        <p className="success-message" role="status">{t("Restore completed successfully.")}</p>
      ) : null}
      {status?.restore_pending ? (
        <p role="status">{t("Restore is pending. Intelligence will restart and validate the restored data before processing resumes.")}</p>
      ) : null}
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

function GlobalInterests({ policy, onSaved }: { policy: SourcePolicy; onSaved: () => void }) {
  const { t } = useUiLanguage();
  const [focus, setFocus] = useState(policy.focus_rules.join(", "));
  const [ignore, setIgnore] = useState(policy.ignore_rules.join(", "));
  const [style, setStyle] = useState(policy.distillation_style);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await put("/settings/source-policy", {
        command_id: commandId(),
        initial_history_count: policy.initial_history_count,
        per_run_max_new_videos: policy.per_run_max_new_videos,
        focus_rules: ruleList(focus),
        ignore_rules: ruleList(ignore),
        distillation_style: style,
      });
      setEditing(false);
      onSaved();
    } catch {
      setError(t("Preferences could not be saved."));
    } finally {
      setBusy(false);
    }
  };
  return <Panel title="My interests">
    <p className="hint">{t("These are defaults for future insight selection. A Following can use them or set its own focus. Summaries remain faithful to source content; existing insights and Topics do not change.")}</p>
    {!editing ? <><p>{t("What I focus on")}: {policy.focus_rules.join(", ") || t("Not set")}</p><button className="button button-secondary" onClick={() => setEditing(true)}>{t("Edit interests")}</button></> : <>
    <label className="field">{t("What I focus on")}
      <input aria-label={t("What I focus on")} value={focus} onChange={(event) => setFocus(event.target.value)} placeholder={t("For example: AI Agent, language models, commercialization")} />
    </label>
    <label className="field">{t("Less of / ignore")}
      <input aria-label={t("Less of / ignore")} value={ignore} onChange={(event) => setIgnore(event.target.value)} placeholder={t("For example: repetitive launch news")} />
    </label>
    <p className="hint">{t("Separate phrases with commas. These explicit rules apply to future checks and insights only.")}</p>
    <label className="field">{t("Insight style")}
      <select aria-label={t("Insight style")} value={style} onChange={(event) => setStyle(event.target.value)}>
        {STYLES.map(([value, label]) => <option value={value} key={value}>{t(label)}</option>)}
      </select>
    </label>
    <button type="button" className="button button-primary" disabled={busy} onClick={save}>{t(busy ? "Saving…" : "Save preferences")}</button>
    {error ? <p className="form-error" role="alert">{error}</p> : null}</>}
  </Panel>;
}

function Settings({ refresh }: { refresh: number }) {
  const [modelMessage, setModelMessage] = useState("");
  const { language, setLanguage, t } = useUiLanguage();
  const [revision, setRevision] = useState(0);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [editingLanguage, setEditingLanguage] = useState(false);
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
    content_processing?: { status: string; requires_cloud: boolean };
    cloud_credential?: { configured: boolean; source: string };
    model_preference?: { desired_provider: string | null; desired_model: string | null };
  }>(
    "/settings",
    refresh + revision,
  );
  const prefs = useRemote<{ active: Preference[]; history: Preference[] }>(
    "/settings/preferences",
    refresh,
  );
  const policy = useRemote<{ policy: SourcePolicy }>(
    "/settings/source-policy",
    refresh + revision,
  );
  const usage = useRemote<{ usage: ResourceUsage[] }>(
    "/settings/resource-usage",
    refresh,
  );
  if (settings.error || prefs.error || policy.error || usage.error) {
    return (
      <ErrorState
        error={settings.error ?? prefs.error ?? policy.error ?? usage.error ??
          ""}
      />
    );
  }
  if (!settings.data || !prefs.data || !policy.data || !usage.data) {
    return <Empty>Loading Settings…</Empty>;
  }
  const globalPolicy = policy.data.policy;
  const videoDistillation = settings.data.providers.find((provider) =>
    provider.provider === "moonshot" && provider.model === "kimi-k2.6" &&
    provider.scope === "V1_VIDEO_DISTILLATION_ONLY"
  );
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
      <Panel title="Language">
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
      <GlobalInterests key={JSON.stringify(globalPolicy)} policy={globalPolicy} onSaved={() => setRevision(current => current + 1)} />
      <Panel title="Models and processing">
        <h3>{t("Content processing")}</h3><p>{t("Ready. Content is saved and organized locally when source text or captions are available. Cloud Intelligence is optional.")}</p>
        <h3>{t("Currently used local model")}</h3><p>{settings.data.runtime_local_model?.model ?? localFoundation?.model ?? t("Not configured")} · {t(settings.data.runtime_local_model?.status === "READY" ? "Installed and ready" : "Readiness needs attention")}</p>
        <p className="hint">{t("Scoring and model-based Summary use this runtime configuration. Candidate preferences in Advanced do not change it.")}</p>
        <h3>{t("Intelligence")}</h3><p>{t(videoDistillation?.production_eligible ? "Optional cloud analysis is available after your authorization for each request." : videoDistillation?.credential_status === "BLOCKED" ? "Cloud Intelligence needs a credential and authorization. Content processing remains usable." : "Configure a qualified Intelligence model. Content processing remains usable.")}</p>
        <details><summary>{t("Cloud setup and model details")}</summary><ModelSettings message={modelMessage} setMessage={setModelMessage} credential={settings.data.cloud_credential} preference={settings.data.model_preference} onSaved={() => setRevision(current => current + 1)} /></details>
      </Panel>
      <TranscriptionSetup />
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
