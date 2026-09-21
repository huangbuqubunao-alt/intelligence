import { FormEvent, ReactNode, useEffect, useState } from "react";
import { api, patch, post, put } from "../api/client";
import { Logo } from "./Logo";
import { FirstRunOnboarding } from "./Onboarding";

type Page =
  | "Home"
  | "Following"
  | "Content"
  | "Intelligence"
  | "Topics"
  | "Settings";
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
type Weekly = {
  brief_id: string;
  version: string;
  period_start: string;
  no_important_information: boolean;
  items: {
    topic_name: string;
    intelligence_id: string;
    claim_kind: string;
    source_state: string;
    summary: string;
    evidence_ids: string[];
    markers: { kind: string; reason: string }[];
  }[];
  weekly_v2: { status: string };
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
  transcript: {
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
  history: { timestamp: string; status: string; summary: string }[];
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
  Settings: "Language, model readiness, resource truth, and data control.",
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

function initialPage(): Page {
  const raw = location.hash.slice(1);
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
  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    api<T>(path).then((value) => alive && setData(value)).catch((
      reason: Error,
    ) => alive && setError(reason.message));
    return () => {
      alive = false;
    };
  }, [path, refresh]);
  return { data, error };
}
function statusLabel(value: string) {
  const labels: Record<string, string> = {
    AVAILABLE: "Available",
    UNAVAILABLE: "Unavailable",
    ENABLED: "Monitoring on",
    DISABLED: "Monitoring off",
    BLOCKED: "Unavailable",
    NEEDS_ATTENTION: "Needs attention",
    SUCCEEDED: "Completed",
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
  };
  return labels[value] ??
    value.replaceAll("_", " ").toLowerCase().replace(
      /^./,
      (letter) => letter.toUpperCase(),
    );
}
function Status({ value }: { value: string }) {
  const upper = value.toUpperCase();
  const tone =
    /AVAILABLE|ENABLED|SUCCEEDED|VERIFIED|ACTIVE|ADMITTED/.test(upper) &&
      !/UNAVAILABLE/.test(upper)
      ? "success"
      : /BLOCKED|ATTENTION|UNAVAILABLE|DEGRADED|UNRESOLVED|SKIPPED|AMBIGUOUS|UNQUALIFIED|INVALID/
          .test(upper)
      ? "warning"
      : "neutral";
  return <span className={`status status-${tone}`}>{statusLabel(value)}</span>;
}
function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}
function Empty({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
function ErrorState({ error }: { error: string }) {
  return (
    <div className="semantic-state state-danger">
      <Status value="Blocked" />
      <p>{error}</p>
    </div>
  );
}
function humanDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("en", {
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
      "This run is waiting for a clear decision.",
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
  return source.display_name || source.friendly_name || source.channel_id ||
    source.video_id || "YouTube Source";
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
function Evidence(
  { item, onOpenContent }: {
    item: Intelligence;
    onOpenContent?: (videoId: string) => void;
  },
) {
  const card = item.card;
  const links = card?.evidence_links ?? [];
  if (!card || !links.length) return null;
  return (
    <details className="evidence-block evidence-trace">
      <summary>Evidence and source</summary>
      <div className="evidence-origin">
        <div>
          <span>Source</span>
          <strong>{card.source_display_name || "Source name unavailable"}</strong>
          <small>{card.source_id} · {card.video_id}</small>
          {card.source_url
            ? <a href={card.source_url} target="_blank" rel="noreferrer">Open Source</a>
            : null}
        </div>
        <div>
          <span>Content</span>
          <strong>{card.video_title || card.video_id}</strong>
        </div>
      </div>
      <div className="evidence-trace-list">
        {links.map((link) => (
          <article className="evidence-item evidence-trace-item" key={link.evidence_id}>
            <div className="reading-meta">
              <Status value={stanceLabel(link.stance)} />
              <span>{link.language}</span>
            </div>
            <div>
              <strong>Original excerpt</strong>
              {link.original_excerpt
                ? <blockquote>{link.original_excerpt}</blockquote>
                : (
                  <p className="hint">
                    Source excerpt unavailable for this historical Evidence. It is not reconstructed or guessed.
                  </p>
                )}
            </div>
            <div>
              <strong>Translation</strong>
              {link.translated_excerpt
                ? <blockquote>{link.translated_excerpt}</blockquote>
                : (
                  <p className="hint">
                    Translation is not available for this Evidence yet. The original remains authoritative.
                  </p>
                )}
            </div>
            <div>
              <strong>Source position</strong>
              <p>{timestampRange(link.start_ms, link.end_ms)}</p>
            </div>
            <div>
              <strong>Provenance</strong>
              <p>{evidenceLineageLabel(link.lineage_kind)} · {evidenceRoleLabel(link.role)}</p>
              <small>{link.artifact_id}</small>
            </div>
            <div className="evidence-actions">
              {onOpenContent
                ? (
                  <button
                    className="button button-secondary button-small"
                    onClick={() => onOpenContent(card.video_id)}
                  >
                    Open Content
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
                    Open original{link.start_ms === null ? "" : " at timestamp"}
                  </a>
                )
                : null}
            </div>
          </article>
        ))}
      </div>
      <p className="hint">
        Supporting, contradicting, and conditional describe this Evidence only in relation to this specific Intelligence revision. Missing relations are shown as undetermined rather than inferred.
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
  const [busy, setBusy] = useState(false);
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
        <p>This Intelligence is not available as current information.</p>
      </div>
    );
  }
  const card = item.card;
  return (
    <article className="panel intelligence-card">
      <header className="intelligence-conclusion">
        <p className="section-label">Conclusion</p>
        <h2>{card.core_conclusion}</h2>
      </header>
      <section className="intelligence-section">
        <h3>Why this matters</h3>
        <p>{card.user_relevant_information.join(" ")}</p>
      </section>
      {card.important_new_information.length
        ? (
          <section className="intelligence-section">
            <h3>What is new</h3>
            <p>{card.important_new_information.join(" ")}</p>
          </section>
        )
        : null}
      {card.meaningful_details?.length
        ? (
          <section className="intelligence-section">
            <h3>Important details</h3>
            <ul>
              {card.meaningful_details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          </section>
        )
        : null}
      <div className="reading-meta" aria-label="Claim type and current state">
        <Claim kind={item.claim_kind ?? "SYSTEM_INFERENCE"} />
        <Status value={intelligenceStateLabel(item.state)} />
      </div>
      <section className="intelligence-section">
        <h3>Validation posture</h3>
        <p>{intelligenceValidationCopy(item.state ?? "")}</p>
        <p className="hint">
          This is a validation posture, not a numeric confidence score.
        </p>
      </section>
      <Evidence item={item} onOpenContent={onOpenContent} />
      <button
        className="button button-secondary"
        disabled={busy}
        onClick={toggle}
      >
        {busy ? "Saving…" : saved ? "Unsave" : "Save"}
      </button>
    </article>
  );
}

export function App() {
  const [page, setPage] = useState<Page>(initialPage);
  const [refresh, setRefresh] = useState(0);
  const [contentTarget, setContentTarget] = useState<string | null>(null);
  const navigate = (next: Page) => {
    setContentTarget(null);
    location.hash = next;
    setPage(next);
  };
  const openContent = (videoId: string) => {
    setContentTarget(videoId);
    location.hash = "Content";
    setPage("Content");
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo className="brand-logo" />
          <div>
            <strong>Intelligence</strong>
            <small>Local-first workspace</small>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {pages.map((item) => (
            <button
              type="button"
              key={item}
              className={`nav-item ${page === item ? "active" : ""}`}
              aria-current={page === item ? "page" : undefined}
              onClick={() => navigate(item)}
            >
              {item}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">Evidence stays reachable</div>
      </aside>
      <main className="workspace-main">
        <header className="page-header">
          <div>
            <p className="eyebrow">INTELLIGENCE</p>
            <h1>{page}</h1>
            <p className="page-subtitle">{subtitles[page]}</p>
          </div>
        </header>
        {page === "Home" && (
          <Dashboard
            refresh={refresh}
            navigate={navigate}
            openContent={openContent}
          />
        )}
        {page === "Following" && (
          <Sources
            refresh={refresh}
            onRefresh={() => setRefresh((value) => value + 1)}
          />
        )}
        {page === "Content" && (
          <ContentPage refresh={refresh} targetVideoId={contentTarget} />
        )}
        {page === "Intelligence" && (
          <IntelligencePage refresh={refresh} openContent={openContent} />
        )}
        {page === "Topics" && <Topics refresh={refresh} />}
        {page === "Settings" && <Settings refresh={refresh} />}
      </main>
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
  const { data, error } = useRemote<
    {
      intelligence?: Intelligence[];
      pinned_topics?: Topic[];
      weekly_v1?: Weekly[];
      needs_attention?: SourceRun[];
      operations?: { source_count?: number };
    }
  >("/dashboard", refresh);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Home…</Empty>;
  const intelligence = (data.intelligence ?? []).filter((item) =>
      item.status === "AVAILABLE" && item.trusted
    ),
    attention = data.needs_attention ?? [],
    topics = data.pinned_topics ?? [],
    weekly = data.weekly_v1 ?? [];
  const isFreshLibrary = data.operations?.source_count === 0 &&
    !intelligence.length && !topics.length && !weekly.length && !attention.length;
  if (isFreshLibrary) {
    return <FirstRunOnboarding onAddFollowing={() => navigate("Following")} />;
  }
  if (!intelligence.length && !topics.length && !weekly.length && !attention.length) {
    return (
      <div className="dashboard-stack">
        <Panel title="No important new intelligence yet.">
          <p>
            Add a Following to start monitoring videos that matter. New conclusions
            will appear here with their Evidence.
          </p>
          <button
            className="button button-primary"
            onClick={() => navigate("Following")}
          >
            Add Following
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
          See all Intelligence
        </button>
      </Panel>
      <Panel title="Topic changes">
        {topics.length
          ? topics.map((topic) => (
            <p key={topic.topic_id}>
              <strong>{topic.name}</strong> · {statusLabel(topic.current_state)}
            </p>
          ))
          : <Empty>No important Topic changes since you last checked.</Empty>}
      </Panel>
      <Panel title="This week">
        {weekly.length
          ? weekly.map((brief) => (
            <div key={brief.brief_id}>
              {brief.no_important_information
                ? <p>No important changes this week.</p>
                : brief.items.slice(0, 2).map((item) => (
                  <p className="dashboard-weekly-item" key={item.intelligence_id}>
                    <strong>{item.summary}</strong>
                    <small>
                      {item.topic_name} · {humanDate(brief.period_start)}
                    </small>
                  </p>
                ))}
            </div>
          ))
          : <Empty>No finalized weekly brief yet.</Empty>}
        <button
          className="button button-ghost"
          onClick={() => navigate("Intelligence")}
        >
          Open Weekly
        </button>
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
  const [title, safety, action] = attentionCopy(run.attention_reason);
  return (
    <article className="semantic-state state-blocked">
      <strong>{title}</strong>
      <p>{safety}</p>
      <p>{action}</p>
    </article>
  );
}
function IntelligencePage(
  { refresh, openContent }: {
    refresh: number;
    openContent: (videoId: string) => void;
  },
) {
  const [view, setView] = useState<"Current" | "Saved" | "Weekly">("Current");
  const [revision, setRevision] = useState(0);
  const current = useRemote<{ intelligence: Intelligence[] }>(
    "/intelligence",
    refresh + revision,
  );
  const saved = useRemote<{ saved: Saved[] }>(
    "/saved-intelligence",
    refresh + revision,
  );
  const weekly = useRemote<{ weekly_v1: Weekly[] }>("/weekly/v1", refresh);
  const source = view === "Current"
    ? current
    : view === "Saved"
    ? saved
    : weekly;
  const currentAvailable = (current.data?.intelligence ?? []).filter((item) =>
    item.status === "AVAILABLE" && item.trusted
  );
  if (source.error) return <ErrorState error={source.error} />;
  return (
    <>
      <div className="segmented">
        {(["Current", "Saved", "Weekly"] as const).map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={view === item}
            className={view === item ? "active" : ""}
            onClick={() => setView(item)}
          >
            {item}
          </button>
        ))}
      </div>
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
        : <Empty>No verified Intelligence yet.</Empty>)}
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
      {view === "Weekly" && (!weekly.data
        ? <Empty>Loading weekly digest…</Empty>
        : weekly.data.weekly_v1.length
        ? weekly.data.weekly_v1.map((brief) => (
          <WeeklyCard key={brief.brief_id} brief={brief} />
        ))
        : <Empty>No finalized weekly digest. An empty week is valid.</Empty>)}
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
  const detail = useRemote<{ intelligence: Intelligence }>(
    `/intelligence/${item.intelligence_id}`,
    revision,
  );
  if (item.intelligence.status !== "AVAILABLE") {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>
          This saved item is no longer available as current Intelligence. Its
          saved reference remains until you choose Unsave.
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
          Unsave
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
function WeeklyCard({ brief }: { brief: Weekly }) {
  return (
    <Panel title={`What mattered · ${humanDate(brief.period_start)}`}>
      {brief.no_important_information
        ? <Empty>No important information this week.</Empty>
        : brief.items.map((item) => (
          <article className="weekly-item" key={item.intelligence_id}>
            <p className="weekly-summary">{item.summary}</p>
            <strong>{item.topic_name}</strong>
            <div className="reading-meta">
              <Claim kind={item.claim_kind} />
              <Status value={item.source_state} />
            </div>
            {item.markers.map((marker) => (
              <p key={marker.kind}>
                <Status value="CORRECTED" /> {marker.reason}
              </p>
            ))}
            <details className="provenance">
              <summary>Evidence references</summary>
              <p>{item.evidence_ids.join(", ")}</p>
            </details>
          </article>
        ))}
      <small>Historical weekly content remains unchanged.</small>
    </Panel>
  );
}
function ContentPage(
  { refresh, targetVideoId }: {
    refresh: number;
    targetVideoId?: string | null;
  },
) {
  const list = useRemote<{ videos: ContentItem[] }>("/videos", refresh);
  const [selected, setSelected] = useState<string | null>(targetVideoId ?? null);
  useEffect(() => {
    if (targetVideoId) setSelected(targetVideoId);
  }, [targetVideoId]);
  if (list.error) return <ErrorState error={list.error} />;
  if (!list.data) return <Empty>Loading Content…</Empty>;
  if (selected) {
    return <ContentDetailPanel id={selected} onClose={() => setSelected(null)} />;
  }
  return list.data.videos.length
    ? (
      <div className="compact-list">
        {list.data.videos.map((item) => (
          <button
            className="list-row"
            key={item.video_id}
            onClick={() => setSelected(item.video_id)}
          >
            <span>
              <strong>{item.title ?? item.video_id}</strong>
              <small>{item.channel_name} · {humanDate(item.published_at)}</small>
            </span>
            <Status value={item.processing_status} />
          </button>
        ))}
      </div>
    )
    : (
      <Empty>
        No Content yet. Add a Following and ingested items will appear here without mixing in Demo fixtures.
      </Empty>
    );
}
function ContentDetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const { data, error } = useRemote<ContentDetail>(`/videos/${id}`);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Content detail…</Empty>;
  const transcript = data.transcript;
  const note = data.note.v2;
  return (
    <div className="dashboard-stack">
      <button className="button button-ghost" onClick={onClose}>Back to Content</button>
      <Panel title={data.video.title ?? data.video.video_id}>
        <div className="reading-meta">
          <Status value={data.video.processing_status} />
          <span>{data.video.channel_name} · {humanDate(data.video.published_at)}</span>
        </div>
        {data.video.source_url
          ? (
            <a className="source-link" href={data.video.source_url} target="_blank" rel="noreferrer">
              Open original source
            </a>
          )
          : null}
      </Panel>
      <Panel title="Transcript">
        {transcript.status === "AVAILABLE" && transcript.text
          ? <div className="transcript-copy">{transcript.text}</div>
          : (
            <div className="semantic-state state-neutral">
              <Status value={transcript.status} />
              <p>{transcript.reason ?? "A readable transcript is not available yet."}</p>
            </div>
          )}
      </Panel>
      <Panel title="Summary / Video Notes">
        {note?.status === "AVAILABLE"
          ? (
            <div className="summary-note">
              <div className="reading-meta">
                <Status value="AVAILABLE" />
                <span>{note.language ?? "Language unavailable"}</span>
              </div>
              {note.summary ? <><h3>Summary</h3><p>{note.summary}</p></> : null}
              {note.core_points?.length
                ? <><h3>Key points</h3><ul>{note.core_points.map((point) => <li key={point}>{point}</li>)}</ul></>
                : null}
              {note.timestamped_key_points?.length
                ? (
                  <>
                    <h3>Timestamped key points</h3>
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
                      Timestamps appear only when the cited trusted Evidence has a timed-subtitle position.
                    </p>
                  </>
                )
                : null}
              {note.evidence_references?.length
                ? (
                  <details className="provenance">
                    <summary>Evidence references</summary>
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
                This is the current verified version for this Content. Failed or unverified newer attempts do not replace it.
              </p>
            </div>
          )
          : (
            <div className="semantic-state state-neutral">
              <Status value="UNAVAILABLE" />
              <p>Summary / Video Notes are not available for this Content yet. No summary is fabricated from missing output.</p>
            </div>
          )}
      </Panel>
      <Panel title="Processing history">
        {data.history.length
          ? data.history.slice(0, 12).map((event) => (
            <div className="metadata-row" key={`${event.timestamp}:${event.summary}`}>
              <span>{humanDate(event.timestamp)}</span>
              <div><Status value={event.status} /><p>{event.summary}</p></div>
            </div>
          ))
          : <Empty>No processing history yet.</Empty>}
      </Panel>
    </div>
  );
}
function Topics({ refresh }: { refresh: number }) {
  const list = useRemote<{ topics: Topic[] }>("/topics", refresh);
  const [selected, setSelected] = useState<string | null>(null);
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
                  Current understanding: {statusLabel(topic.current_state)}
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
        Back to Topics
      </button>
      <Panel title={topic.name}>
        <h3>Current understanding</h3>
        <p>{statusLabel(topic.current_state)}.</p>
        <p>
          {topic.independence === "UNKNOWN"
            ? "Not enough reliable information yet to determine how independent the supporting sources are."
            : "This understanding is based on the available supporting sources."}
        </p>
        <button
          className="button button-secondary"
          onClick={() =>
            post(`/topics/${topic.topic_id}/pin`, { pinned: !topic.pinned })
              .then(() => setSelected(null))}
        >
          {topic.pinned ? "Unpin Topic" : "Pin Topic"}
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
                  ? "A current contribution supports this topic."
                  : "Some supporting information is no longer available."}
              </p>
              <details className="provenance">
                <summary>Technical evidence references</summary>
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
              {humanDate(event.created_at)} · {statusLabel(event.state)}
            </p>
          ))
          : <Empty>No historical events.</Empty>}
      </Panel>
      <Panel title="Related Topics">
        {topic.relations.length
          ? topic.relations.map((relation) => (
            <p key={relation.related_topic_id}>Related topic</p>
          ))
          : <Empty>No related Topics.</Empty>}
      </Panel>
    </div>
  );
}

function Sources(
  { refresh, onRefresh }: { refresh: number; onRefresh: () => void },
) {
  const { data, error } = useRemote<{ sources: Source[] }>("/sources", refresh);
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Sources…</Empty>;
  return (
    <>
      <div className="page-actions">
        <button
          className="button button-primary"
          onClick={() => setAdding(true)}
        >
          Add Source
        </button>
      </div>
      {data.sources.length
        ? (
          <div className="source-list">
            {data.sources.map((source) => (
              <div className="list-row source-row" key={source.source_id}>
                <button
                  className="source-select"
                  onClick={() =>
                    setSelected(source.source_id)}
                >
                  <span>
                    <strong>{sourceLabel(source)}</strong>
                    <small>
                      {source.enabled
                        ? "Monitoring new videos"
                        : "Monitoring is paused"}
                    </small>
                  </span>
                </button>
                <div className="source-actions">
                  <Status
                    value={source.last_error?.code ??
                      (source.enabled ? "ENABLED" : "DISABLED")}
                  />
                  <a
                    href={source.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Source
                  </a>
                </div>
              </div>
            ))}
          </div>
        )
        : (
          <Empty>
            <strong>Set up your first Source</strong>
            <p>
              Add a YouTube Source to monitor new videos, turn them into
              Intelligence, and keep Evidence inspectable.
            </p>
            <button
              className="button button-primary"
              onClick={() => setAdding(true)}
            >
              Add Source
            </button>
          </Empty>
        )}
      {adding && (
        <SourceForm
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            onRefresh();
          }}
        />
      )}
      {selected && (
        <SourceDetail
          id={selected}
          onClose={() => setSelected(null)}
          onRefresh={onRefresh}
        />
      )}
    </>
  );
}
function ruleList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
function SourceForm(
  { onClose, onSaved, source, policy, schedules }: {
    onClose: () => void;
    onSaved: () => void;
    source?: Source;
    policy?: SourcePolicy;
    schedules?: Schedule[];
  },
) {
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
  const [frequency, setFrequency] = useState(schedule?.frequency ?? "DAILY");
  const [time, setTime] = useState(schedule?.local_time ?? "09:00");
  const [scheduleEnabled, setScheduleEnabled] = useState(
    schedule?.enabled ?? true,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
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
        focus_mode: "OVERRIDE",
        focus_rules: ruleList(focus),
        ignore_mode: "OVERRIDE",
        ignore_rules: ruleList(ignore),
        distillation_style_mode: "OVERRIDE",
        distillation_style: style,
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
              {source ? "Edit Source configuration" : "Add a Source"}
            </h2>
            <p className="hint">
              These settings use the existing Source policy and schedule
              services.
            </p>
          </div>
          <button className="button button-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>
        <form onSubmit={submit}>
          <label className="field">
            Source URL<input
              aria-label="Source URL"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
              placeholder="https://www.youtube.com/@channel"
            />
          </label>
          <label className="field">
            Processing level<select
              aria-label="Processing level"
              value={processingPolicy}
              onChange={(event) => setProcessingPolicy(event.target.value)}
            >
              <option value="DISCOVER_ONLY">Discover new videos only</option>
              <option value="STANDARD_INTELLIGENCE">
                Turn relevant videos into Intelligence
              </option>
            </select>
          </label>
          <label className="field">
            <span>
              <input
                aria-label="Monitor this Source"
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
              />{" "}
              Monitor this Source
            </span>
            <small>
              Turning monitoring off affects future checks only; it never
              removes existing Intelligence.
            </small>
          </label>
          <Panel title="What to process">
            <label className="field">
              Initial history<select
                aria-label="Initial history"
                value={initialHistory}
                onChange={(event) => setInitialHistory(event.target.value)}
              >
                {INITIAL_HISTORY.map((value) => (
                  <option key={value} value={value}>
                    {value} recent videos
                  </option>
                ))}
              </select>
              <small>
                How many recent existing videos are considered when this Source
                is first added.
              </small>
            </label>
            <label className="field">
              Per-run limit<select
                aria-label="Per-run limit"
                value={perRunLimit}
                onChange={(event) => setPerRunLimit(event.target.value)}
              >
                {PER_RUN_LIMIT.map((value) => (
                  <option key={value} value={value}>{value} new videos</option>
                ))}
              </select>
              <small>
                The maximum number of new videos processed in one Source Run.
                Videos beyond this limit remain pending.
              </small>
            </label>
            <label className="field">
              Focus<input
                aria-label="Focus"
                value={focus}
                onChange={(event) => setFocus(event.target.value)}
                placeholder="Comma-separated terms"
              />
              <small>Use simple terms that help choose what is relevant.</small>
            </label>
            <label className="field">
              Ignore<input
                aria-label="Ignore"
                value={ignore}
                onChange={(event) => setIgnore(event.target.value)}
                placeholder="Comma-separated terms"
              />
              <small>
                Use simple terms to exclude videos from automatic relevance
                selection.
              </small>
            </label>
            <label className="field">
              Distillation style<select
                aria-label="Distillation style"
                value={style}
                onChange={(event) => setStyle(event.target.value)}
              >
                {STYLES.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <small>{STYLES.find(([value]) => value === style)?.[2]}</small>
            </label>
          </Panel>
          <Panel title="When it runs">
            <label className="field">
              Automatic schedule<select
                aria-label="Automatic schedule"
                value={frequency}
                onChange={(event) => setFrequency(event.target.value)}
              >
                <option value="DAILY">Daily</option>
                <option value="WEEKLY">Weekly</option>
                <option value="MANUAL">Run manually</option>
              </select>
              <small>
                Choose when this Source runs automatically. Manual does not
                create an automatic schedule.
              </small>
            </label>
            {frequency !== "MANUAL"
              ? (
                <>
                  <label className="field">
                    Time<input
                      aria-label="Schedule time"
                      type="time"
                      value={time}
                      onChange={(event) => setTime(event.target.value)}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>
                      <input
                        aria-label="Enable automatic schedule"
                        type="checkbox"
                        checked={scheduleEnabled}
                        onChange={(event) =>
                          setScheduleEnabled(event.target.checked)}
                      />{" "}
                      Enable this automatic schedule
                    </span>
                  </label>
                </>
              )
              : null}
          </Panel>
          {error && <ErrorState error={error} />}
          <div className="modal-actions">
            <button
              type="button"
              className="button button-ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              className="button button-primary"
              disabled={busy}
              type="submit"
            >
              {busy ? "Saving…" : source ? "Save changes" : "Add Source"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
function SourceDetail(
  { id, onClose, onRefresh }: {
    id: string;
    onClose: () => void;
    onRefresh: () => void;
  },
) {
  const { data, error } = useRemote<
    {
      source: Source;
      policy: SourcePolicy;
      schedules: Schedule[];
      recent_videos: {
        video_id: string;
        title: string | null;
        processing_status: string;
        filter: { outcome: string; reason: string } | null;
      }[];
      source_runs: SourceRun[];
    }
  >(`/sources/${id}`, 0);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>Loading Source…</Empty>;
  const check = async () => {
    const result = await post<
      { source_run?: SourceRun; status?: string; message?: string }
    >(`/sources/${id}/check`, { command_id: commandId() });
    if (result.source_run) {
      setMessage(
        "Your check was accepted and is waiting to run. Review this Source for its current progress.",
      );
      onRefresh();
      return;
    }
    if (result.status === "BLOCKED") {
      setMessage(
        "Check Now cannot start in this local demo because processing is intentionally disabled. No Source Run was created and your existing data is unchanged.",
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
              Open Source
            </a>
          </div>
          <button className="button button-ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <Panel title="Source management">
          <p>
            <Status value={data.source.enabled ? "ENABLED" : "DISABLED"} />{" "}
            Monitoring changes affect future checks only; existing Intelligence
            remains unchanged.
          </p>
          <div className="inline-actions">
            <button
              className="button button-secondary"
              onClick={() => setEditing(true)}
            >
              Edit configuration
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
              {data.source.enabled
                ? "Stop future monitoring"
                : "Resume monitoring"}
            </button>
          </div>
        </Panel>
        <Panel title="Processing policy">
          <p>
            Initial history: {data.policy.initial_history_count}{" "}
            recent existing videos when this Source was first added.
          </p>
          <p>
            Per-run limit: {data.policy.per_run_max_new_videos}{" "}
            new videos in one Source Run; overflow remains pending.
          </p>
          <p>
            Focus:{" "}
            {data.policy.focus_rules.join(", ") || "No focus terms"}. Ignore:
            {" "}
            {data.policy.ignore_rules.join(", ") || "No ignore terms"}.
          </p>
          <p>
            Style:{" "}
            {STYLES.find(([value]) => value === data.policy.distillation_style)
              ?.[1] ?? "Balanced"}.
          </p>
        </Panel>
        <Panel title="Schedule">
          {data.schedules.length
            ? data.schedules.map((schedule) => (
              <p key={schedule.schedule_id}>
                <Status value={schedule.enabled ? "ENABLED" : "DISABLED"} />
                {" "}
                Runs {schedule.frequency.toLowerCase()}
                {schedule.local_time ? ` at ${schedule.local_time}` : ""}
                {schedule.timezone ? ` (${schedule.timezone})` : ""}.
              </p>
            ))
            : (
              <Empty>
                This Source runs manually. Edit configuration to add an
                automatic schedule.
              </Empty>
            )}
        </Panel>
        <button className="button button-primary" onClick={check}>
          Check Now
        </button>
        <p className="hint">
          Checks follow the existing safe processing path. This is not a retry
          action.
        </p>
        {message && (
          <div className="semantic-state state-neutral">
            <p>{message}</p>
          </div>
        )}
        <Panel title="Recent videos">
          {data.recent_videos.length
            ? data.recent_videos.map((video) => {
              const skipped = video.filter?.outcome === "NOT_RELEVANT";
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
                          <p>{filterReason(video.filter?.reason)}</p>
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
                            Analyze this Video
                          </button>
                          <p className="hint">
                            Analyze this video even though it was skipped for
                            relevance. Other safety, budget and model rules
                            still apply.
                          </p>
                        </>
                      )
                      : (
                        <p>
                          Current processing state:{" "}
                          {statusLabel(video.processing_status)}.
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
                    <Status value={run.state} /> A Source Run is{" "}
                    {statusLabel(run.state).toLowerCase()}.
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
function Settings({ refresh }: { refresh: number }) {
  const [revision, setRevision] = useState(0);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [languageError, setLanguageError] = useState<string | null>(null);
  const settings = useRemote<{
    general: {
      timezone: string;
      output_language: "zh-CN" | "en";
      output_language_source: string;
      output_language_updated_at: string | null;
    };
    providers: ProviderStatus[];
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
    refresh,
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
    provider.production_eligible && provider.authorized &&
    provider.scope === "V1_VIDEO_DISTILLATION_ONLY"
  );
  const otherProviders = settings.data.providers.filter((provider) =>
    provider !== videoDistillation
  );
  const saveLanguage = async (value: "zh-CN" | "en") => {
    setSavingLanguage(true);
    setLanguageError(null);
    try {
      await put("/settings/output-language", { output_language: value });
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
      <Panel title="Output language">
        <label className="field">
          Preferred output language
          <select
            aria-label="Preferred output language"
            value={settings.data.general.output_language}
            disabled={savingLanguage}
            onChange={(event) =>
              saveLanguage(event.target.value as "zh-CN" | "en")}
          >
            <option value="zh-CN">Chinese (Simplified)</option>
            <option value="en">English</option>
          </select>
        </label>
        <p>
          New processing batches use this language for generated output. Existing Summary, Evidence, Intelligence, Topic, and historical records stay unchanged.
        </p>
        <p className="hint">
          {settings.data.general.output_language_source === "USER_PREFERENCE"
            ? "Saved locally on this Mac."
            : "Using the app default until you choose a preference."}
        </p>
        {languageError ? <p className="form-error">{languageError}</p> : null}
      </Panel>
      <Panel title="Preference Center">
        <p className="hint">
          Explicit means you directly chose it. Derived means the app inferred
          it from feedback. Temporary means it is used only until its expiry.
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
                  {preferenceCopy(preference)}
                  {preference.expires_at
                    ? ` Expires ${humanDate(preference.expires_at)}.`
                    : ""}
                </p>
              </div>
            </article>
          ))
          : <Empty>No Preferences yet.</Empty>}
      </Panel>
      <Panel title="Source policy">
        <p>
          Default for Sources without their own configuration: initial history
          {" "}
          {globalPolicy.initial_history_count}, per-run limit{" "}
          {globalPolicy.per_run_max_new_videos},{" "}
          {STYLES.find(([value]) => value === globalPolicy.distillation_style)
            ?.[1] ?? "Balanced"} style.
        </p>
      </Panel>
      <Panel title="Models and cost">
        <div className="capability-grid">
          <article className="capability-card">
            <div className="capability-heading">
              <h3>Video Distillation</h3>
              <Status value={videoDistillation ? "AVAILABLE" : "UNAVAILABLE"} />
            </div>
            <p>
              {videoDistillation
                ? "Available for V1 video analysis only."
                : "No approved model is currently available for video analysis."}
            </p>
            {videoDistillation && (
              <details className="provenance">
                <summary>Provider and model details</summary>
                <p>
                  {videoDistillation.provider} · {videoDistillation.model}
                </p>
                <p>Scope: Video Distillation only.</p>
                <p>{videoDistillation.reason}</p>
              </details>
            )}
          </article>
          <article className="capability-card">
            <div className="capability-heading">
              <h3>Deep Analysis</h3>
              <Status value="UNAVAILABLE" />
            </div>
            <p>Deep Analysis is unavailable.</p>
            <p className="hint">
              Kimi is not authorized for this capability, and this screen cannot
              enable it.
            </p>
          </article>
        </div>
        {otherProviders.length > 0 && (
          <details className="provenance">
            <summary>Other model options</summary>
            {otherProviders.map((provider) => (
              <p key={provider.provider}>
                {provider.provider}: not available for production use.
              </p>
            ))}
          </details>
        )}
      </Panel>
      <Panel title="Resource Usage">
        {usage.data.usage.length
          ? usage.data.usage.map((item) => (
            <article className="metadata-row" key={item.execution_id}>
              <div>
                <strong>{usageReason(item.reason)}</strong>
                <p>
                  {item.invocation_count} calls · {item.duration_ms === null
                    ? "Duration unavailable"
                    : `Duration ${item.duration_ms}ms`}
                </p>
                <p>
                  Token usage:{" "}
                  {item.input_tokens === null || item.output_tokens === null
                    ? "Unavailable"
                    : `${item.input_tokens} input / ${item.output_tokens} output`};
                  Cost: {item.cost_microunits === null
                    ? "Unavailable"
                    : `${item.cost_microunits} microunits`}.
                </p>
                <Status value={item.status} />
              </div>
              <details className="provenance">
                <summary>Technical details</summary>
                <p>
                  Model: {item.actual_model ?? "Unknown"}. Provider:{" "}
                  {item.actual_provider ?? "Unknown"}.
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
      <Panel title="Data and privacy">
        <p>
          Local-first means local persistence by default. Credential values are
          never shown.
        </p>
      </Panel>
    </div>
  );
}
