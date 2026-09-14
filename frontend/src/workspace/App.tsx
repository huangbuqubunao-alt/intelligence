import {
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  ReactNode,
  RefObject,
  useEffect,
  useRef,
  useState,
} from "react";
import { api, patch, post, put } from "../api/client";
import {
  LanguageProvider,
  Locale,
  MessageKey,
  Translate,
  useLanguage,
} from "./localization";

type Page =
  | "Dashboard"
  | "Intelligence"
  | "Topics"
  | "Sources"
  | "Investigations"
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
      start_ms: number | null;
      end_ms: number | null;
      excerpt: string;
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
  source_id?: string;
  state: string;
  attention_reason: string | null;
  trigger: string;
  updated_at: string;
  progress?: { code: string; label: string };
  result?: { kind: string; label: string; intelligence_count?: number };
  recovery?: {
    kind: string;
    what_happened: string;
    why_it_matters: string;
    safe_action: { kind: string; label: string; target: string } | null;
    will_not: string;
  } | null;
};
type ReadinessDimension = {
  code: string;
  label: string;
  message: string;
  source_id?: string;
  limit?: number | null;
  used?: number | null;
  recovery?: { action: string; will_not: string };
};
type Readiness = {
  overall: ReadinessDimension;
  application: ReadinessDimension;
  video_distillation: ReadinessDimension;
  model: ReadinessDimension;
  credential: ReadinessDimension;
  budget: ReadinessDimension;
  source: ReadinessDimension;
  deep_analysis: ReadinessDimension;
};

function isReadiness(value: unknown): value is Readiness {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Record<keyof Readiness, unknown>>;
  return [
    "overall",
    "application",
    "video_distillation",
    "model",
    "credential",
    "budget",
    "source",
    "deep_analysis",
  ].every((key) => {
    const dimension = candidate[key as keyof Readiness];
    return Boolean(
      dimension && typeof dimension === "object" &&
        typeof (dimension as ReadinessDimension).code === "string" &&
        typeof (dimension as ReadinessDimension).label === "string" &&
        typeof (dimension as ReadinessDimension).message === "string",
    );
  });
}
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

const pages: Page[] = [
  "Dashboard",
  "Intelligence",
  "Topics",
  "Sources",
  "Investigations",
  "Settings",
];
const subtitles: Record<Page, MessageKey> = {
  Dashboard: "What changed that matters to you.",
  Intelligence: "Verified, evidence-linked intelligence.",
  Topics: "Current understanding and its history.",
  Sources: "Choose what the app monitors and how it processes new videos.",
  Investigations: "Reserved V2 capability.",
  Settings: "Preferences, model readiness, resource truth, and privacy.",
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
function statusLabel(value: string, t: Translate) {
  const labels: Record<string, MessageKey> = {
    Blocked: "Blocked",
    READY: "Ready",
    SETUP_REQUIRED: "Setup required",
    BUDGET_BLOCKED: "Review usage limit",
    TEMPORARILY_UNAVAILABLE: "Temporarily unavailable",
    LIMIT_REACHED: "Usage limit reached",
    CONNECTED: "Connected",
    READY_TO_START: "Ready to start",
    WITHIN_LIMIT: "Within limit",
    READY_FOR_MANUAL_CHECK: "Ready for manual check",
    QUEUED: "Queued",
    WAITING: "Waiting",
    PARTIAL: "Partially completed",
    FAILED_FINAL: "Failed",
    FAILED: "Failed",
    COMPLETED: "Completed",
    CANCELLED: "Cancelled",
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
  return labels[value] ? t(labels[value]) :
    value.replaceAll("_", " ").toLowerCase().replace(
      /^./,
      (letter) => letter.toUpperCase(),
    );
}
function Status({ value }: { value: string }) {
  const { t } = useLanguage();
  const upper = value.toUpperCase();
  const tone =
    /AVAILABLE|ENABLED|SUCCEEDED|VERIFIED|ACTIVE|ADMITTED|READY/.test(upper) &&
      !/UNAVAILABLE/.test(upper)
      ? "success"
      : /BLOCKED|ATTENTION|UNAVAILABLE|DEGRADED|UNRESOLVED|SKIPPED|AMBIGUOUS|UNQUALIFIED|INVALID|SETUP|LIMIT_REACHED|TEMPORARILY/
          .test(upper)
      ? "warning"
      : "neutral";
  return <span className={`status status-${tone}`}>{statusLabel(value, t)}</span>;
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
  const { translateKnown } = useLanguage();
  return (
    <div className="semantic-state state-danger">
      <Status value="Blocked" />
      <p>{translateKnown(error)}</p>
    </div>
  );
}

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

function useModalKeyboard(
  dialogRef: RefObject<HTMLElement>,
  initialFocusRef: RefObject<HTMLElement>,
  onClose: () => void,
  restoreFocusRef?: RefObject<HTMLElement>,
) {
  const opener = useRef<HTMLElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    opener.current = restoreFocusRef?.current ??
      (document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null);
    initialFocusRef.current?.focus();
    return () => opener.current?.focus();
  }, [initialFocusRef, restoreFocusRef]);
  return (event: ReactKeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeRef.current();
      return;
    }
    if (event.key !== "Tab") return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>(FOCUSABLE),
    ).filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
    if (!focusable.length) {
      event.preventDefault();
      initialFocusRef.current?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey &&
      (document.activeElement === first || document.activeElement === initialFocusRef.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}
function humanDate(value: string, locale: Locale) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
function Claim({ kind }: { kind: string }) {
  const { t } = useLanguage();
  const labels: Record<string, MessageKey> = {
    FACT: "Fact",
    EVIDENCE_BACKED_STATEMENT: "Supported statement",
    OPINION: "Attributed opinion",
    PREDICTION: "Prediction",
    RUMOR: "Unconfirmed rumor",
    SYSTEM_INFERENCE: "System inference",
  };
  return <Status value={labels[kind] ? t(labels[kind]) : kind} />;
}
function filterReason(reason: string | undefined, t: Translate) {
  return ({
    IGNORE_RULE_MATCH: "Excluded by your ignore rules.",
    FOCUS_MATCH: "Matched your focus.",
    FOCUS_MISMATCH: "Outside your current focus.",
    NOT_RELEVANT: "Not relevant enough under this Source’s current policy.",
  } as Record<string, MessageKey>)[reason ?? ""]
    ? t(({
      IGNORE_RULE_MATCH: "Excluded by your ignore rules.",
      FOCUS_MATCH: "Matched your focus.",
      FOCUS_MISMATCH: "Outside your current focus.",
      NOT_RELEVANT: "Not relevant enough under this Source’s current policy.",
    } as Record<string, MessageKey>)[reason ?? ""])
    : t("This video was skipped under this Source’s current policy.");
}
function attentionCopy(reason: string | null, t: Translate) {
  const copy = ({
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
  } as Record<string, [MessageKey, MessageKey, MessageKey]>)[reason ?? ""] ??
    [
      "This Source needs attention.",
      "Existing Intelligence remains safe.",
      "Review the Source details for the available next step.",
    ];
  return copy.map((item) => t(item)) as [string, string, string];
}

const readinessFacts: [keyof Readiness, MessageKey][] = [
  ["application", "Application"],
  ["video_distillation", "Source processing"],
  ["model", "Video analysis model"],
  ["credential", "NVIDIA credential"],
  ["budget", "Usage budget"],
  ["source", "Source"],
];

function readinessActionLabel(
  dimension: ReadinessDimension,
  t: Translate,
  { compact = false }: { compact?: boolean } = {},
) {
  return dimension.recovery?.action === "EDIT_SOURCE_CONFIGURATION"
    ? t("Open Source configuration")
    : dimension.recovery?.action === "VIEW_USAGE"
    ? t("View usage")
    : dimension.recovery?.action === "VIEW_SETUP_INSTRUCTIONS"
    ? compact ? t("Review setup guidance") : t("Check readiness")
    : t("Check readiness");
}

function ReadinessPanel(
  { readiness, compact = false, onAction }: {
    readiness: Readiness;
    compact?: boolean;
    onAction?: (dimension: ReadinessDimension) => void;
  },
) {
  const { t, translateKnown } = useLanguage();
  const blocked = readinessFacts
    .map(([key]) => readiness[key])
    .filter((item) => ![
      "CONNECTED",
      "READY_TO_START",
      "APPROVED",
      "AVAILABLE",
      "WITHIN_LIMIT",
      "READY_FOR_MANUAL_CHECK",
    ].includes(item.code));
  if (compact) {
    return (
      <section className="readiness-summary" aria-labelledby="readiness-summary-title">
        <div>
          <p className="section-label">{t("Run readiness")}</p>
          <h2 id="readiness-summary-title">{translateKnown(readiness.overall.label)}</h2>
          <p>{translateKnown(readiness.overall.message)}</p>
          {blocked.slice(0, 2).map((item) => (
            <p key={item.label}><strong>{translateKnown(item.label)}.</strong> {translateKnown(item.message)}</p>
          ))}
        </div>
        {blocked[0] && onAction && (
          <button
            type="button"
            className="button button-secondary"
            onClick={() => onAction(blocked[0])}
          >
            {readinessActionLabel(blocked[0], t, { compact: true })}
          </button>
        )}
      </section>
    );
  }
  return (
    <section className="panel readiness-panel" id="run-readiness">
      <div className="panel-heading readiness-heading">
        <div>
          <p className="section-label">{t("Normal Video Distillation")}</p>
          <h2>{t("Run readiness")}</h2>
        </div>
        <Status value={readiness.overall.code} />
      </div>
      <h3>{translateKnown(readiness.overall.label)}</h3>
      <p>{translateKnown(readiness.overall.message)}</p>
      <div className="readiness-grid">
        {readinessFacts.map(([key, title]) => {
          const item = readiness[key];
          return (
            <article className="readiness-fact" key={key}>
              <small>{t(title)}</small>
              <strong>{translateKnown(item.label)}</strong>
              <p>{translateKnown(item.message)}</p>
              {item.recovery && <p className="hint">{translateKnown(item.recovery.will_not)}</p>}
              {item.recovery && onAction && (
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => onAction(item)}
                >
                  {readinessActionLabel(item, t)}
                </button>
              )}
            </article>
          );
        })}
      </div>
      <details className="provenance">
        <summary>{t("Capability boundary")}</summary>
        <p>{translateKnown(readiness.deep_analysis.label)}. {translateKnown(readiness.deep_analysis.message)}</p>
      </details>
    </section>
  );
}

function DisconnectedReadiness() {
  const { t } = useLanguage();
  return (
    <section className="readiness-summary state-danger" aria-label={t("Run readiness")}>
      <div>
        <p className="section-label">{t("Run readiness")}</p>
        <h2>{t("Application cannot connect")}</h2>
        <p>
          {t("Source processing, credential, budget, and Source status are unavailable until the local application service responds.")}
        </p>
      </div>
    </section>
  );
}

function sourceLabel(source: Source, t: Translate) {
  return source.display_name || source.friendly_name || source.channel_id ||
    source.video_id || t("YouTube Source");
}
function timestamp(value: number) {
  const seconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}
function timestampRange(
  start: number | null,
  end: number | null,
  t: Translate,
) {
  if (start === null) return t("Timestamp unavailable");
  return end === null
    ? timestamp(start)
    : `${timestamp(start)}–${timestamp(end)}`;
}
function videoAt(url: string, start: number | null) {
  if (start === null) return url;
  return `${url}${url.includes("?") ? "&" : "?"}t=${Math.floor(start / 1000)}`;
}

export function ScoringTab(
  { scoring }: {
    scoring: { status: string; reason?: string; code?: string } | null;
    error: string | null;
  },
) {
  const { t, translateKnown } = useLanguage();
  if (!scoring || scoring.status !== "AVAILABLE") {
    return (
      <div className="semantic-state state-neutral">
        <Status value="UNAVAILABLE" />
        <p>
          {scoring?.reason ? translateKnown(scoring.reason) :
            t("No verified scoring result is available for this video.")}
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
function Evidence({ item }: { item: Intelligence }) {
  const { t } = useLanguage();
  const card = item.card;
  const links = card?.evidence_links ?? [];
  if (!card || !links.length) return null;
  return (
    <section
      className="evidence-block"
      aria-labelledby={`evidence-${item.intelligence_id}`}
    >
      <h3 id={`evidence-${item.intelligence_id}`}>{t("Evidence")}</h3>
      <div className="evidence-origin">
        <div>
          <span>{t("Source")}</span>
          <strong>
            {card.source_display_name || t("Source name unavailable")}
          </strong>
          {card.source_url
            ? (
              <a href={card.source_url} target="_blank" rel="noreferrer">
                {t("Open Source")}
              </a>
            )
            : null}
        </div>
        <div>
          <span>{t("Video")}</span>
          <strong>{card.video_title || card.video_id}</strong>
        </div>
      </div>
      {links.map((link) => (
        <figure className="evidence-item" key={link.evidence_id}>
          <figcaption>
            <strong>{timestampRange(link.start_ms, link.end_ms, t)}</strong>
            {card.original_video_url
              ? (
                <a
                  href={videoAt(card.original_video_url, link.start_ms)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("Open video at {time}", {
                    time: link.start_ms === null
                      ? t("source")
                      : timestamp(link.start_ms),
                  })}
                </a>
              )
              : null}
          </figcaption>
          <blockquote>{link.excerpt}</blockquote>
          <details className="provenance">
            <summary>{t("Technical provenance")}</summary>
            <p>{link.evidence_id} · {card.source_id} · {card.video_id}</p>
          </details>
        </figure>
      ))}
    </section>
  );
}
function IntelligenceCard(
  { item, saved, onSaved }: {
    item: Intelligence;
    saved: boolean;
    onSaved: () => void;
  },
) {
  const { t } = useLanguage();
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
        <Status value={item.state ?? "AVAILABLE"} />
      </div>
      <Evidence item={item} />
      <button
        className="button button-secondary"
        disabled={busy}
        onClick={toggle}
      >
        {busy ? t("Saving…") : saved ? t("Unsave") : t("Save")}
      </button>
    </article>
  );
}

export function App() {
  return <LanguageProvider><Workspace /></LanguageProvider>;
}

function Workspace() {
  const { t } = useLanguage();
  const [page, setPage] = useState<Page>(
    (location.hash.slice(1) as Page) || "Dashboard",
  );
  const [refresh, setRefresh] = useState(0);
  const [requestedSource, setRequestedSource] = useState<string | null>(null);
  const navigate = (next: Page) => {
    location.hash = next;
    setPage(next);
  };
  const recover = (dimension: ReadinessDimension, sourceId?: string) => {
    if (dimension.recovery?.action === "EDIT_SOURCE_CONFIGURATION" && sourceId) {
      setRequestedSource(sourceId);
      navigate("Sources");
      return;
    }
    navigate("Settings");
  };
  const recoverRun = (run: SourceRun) => {
    const kind = run.recovery?.safe_action?.kind;
    if (kind === "VIEW_USAGE" || kind === "VIEW_CREDENTIAL_SETUP" ||
      kind === "CHECK_READINESS") {
      navigate("Settings");
      return;
    }
    if (run.source_id) setRequestedSource(run.source_id);
    navigate("Sources");
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">YI</span>
          <div>
            <strong>YouTube Intelligence Agent</strong>
            <small>{t("Local-first workspace")}</small>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label={t("Primary navigation")}>
          {pages.map((item) => (
            <button
              type="button"
              key={item}
              className={`nav-item ${page === item ? "active" : ""}`}
              aria-current={page === item ? "page" : undefined}
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
            <p className="eyebrow">YOUTUBE INTELLIGENCE AGENT</p>
            <h1>{t(page)}</h1>
            <p className="page-subtitle">{t(subtitles[page])}</p>
          </div>
        </header>
        {page === "Dashboard" && (
          <Dashboard
            refresh={refresh}
            navigate={navigate}
            onRecover={recoverRun}
            onReadinessAction={recover}
          />
        )}
        {page === "Intelligence" && <IntelligencePage refresh={refresh} />}
        {page === "Topics" && <Topics refresh={refresh} />}
        {page === "Sources" && (
          <Sources
            refresh={refresh}
            onRefresh={() => setRefresh((value) => value + 1)}
            requestedSource={requestedSource}
            onRequestedSourceOpened={() => setRequestedSource(null)}
            onOpenSettings={() => navigate("Settings")}
          />
        )}
        {page === "Investigations" && <Investigations />}
        {page === "Settings" && (
          <Settings
            refresh={refresh}
            onReadinessAction={(dimension) =>
              recover(dimension, dimension.source_id)}
          />
        )}
      </main>
    </div>
  );
}
function Dashboard(
  { refresh, navigate, onRecover, onReadinessAction }: {
    refresh: number;
    navigate: (page: Page) => void;
    onRecover: (run: SourceRun) => void;
    onReadinessAction: (dimension: ReadinessDimension, sourceId?: string) => void;
  },
) {
  const { t, locale } = useLanguage();
  const { data, error } = useRemote<
    {
      intelligence?: Intelligence[];
      pinned_topics?: Topic[];
      weekly_v1?: Weekly[];
      needs_attention?: SourceRun[];
    }
  >("/dashboard", refresh);
  const readiness = useRemote<{ readiness: Readiness }>("/readiness", refresh);
  const readinessProjection = isReadiness(readiness.data?.readiness)
    ? readiness.data.readiness
    : null;
  if (error) {
    return <><DisconnectedReadiness /><ErrorState error={error} /></>;
  }
  if (!data || (!readiness.data && !readiness.error)) {
    return <Empty>{t("Loading dashboard…")}</Empty>;
  }
  const intelligence = (data.intelligence ?? []).filter((item) =>
      item.status === "AVAILABLE" && item.trusted
    ),
    attention = data.needs_attention ?? [],
    topics = data.pinned_topics ?? [],
    weekly = data.weekly_v1 ?? [];
  const blockingAttention = readinessProjection?.overall.code !== "READY"
    ? attention
    : attention.filter((run) =>
      ["AMBIGUOUS", "DECISION_REQUIRED"].includes(run.recovery?.kind ?? "")
    );
  if (
    !intelligence.length && !topics.length && !weekly.length &&
    !attention.length
  ) {
    return (
      <div className="dashboard-stack">
        {(readiness.error || !readinessProjection) && <DisconnectedReadiness />}
        {readinessProjection && (
          <ReadinessPanel
            readiness={readinessProjection}
            compact
            onAction={(dimension) =>
              onReadinessAction(dimension, dimension.source_id)}
          />
        )}
        <Panel title={t("No important new intelligence yet.")}>
          <p>
            {t("Add a Source to start monitoring videos that matter. New conclusions will appear here with their Evidence.")}
          </p>
          <button
            className="button button-primary"
            onClick={() => navigate("Sources")}
          >
            {t("Add Source")}
          </button>
        </Panel>
      </div>
    );
  }
  return (
    <div className="dashboard-stack">
      {(readiness.error || !readinessProjection) && <DisconnectedReadiness />}
      {readinessProjection?.overall.code !== "READY" &&
        readinessProjection && (
        <ReadinessPanel
          readiness={readinessProjection}
          compact
          onAction={(dimension) =>
            onReadinessAction(dimension, dimension.source_id)}
        />
      )}
      {blockingAttention.length > 0 && (
        <section className="blocking-summary" aria-label={t("Blocking Source Runs")}>
          <div>
            <strong>{t(
              blockingAttention.length === 1
                ? "{count} Source Run needs action"
                : "{count} Source Runs need action",
              { count: blockingAttention.length },
            )}</strong>
            <p>{t("Review the affected Source for the finite safe next step.")}</p>
          </div>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => onRecover(blockingAttention[0])}
          >
            {t("Open affected Source")}
          </button>
        </section>
      )}
      <Panel title={t("What matters now")}>
        {intelligence.length
          ? intelligence.map((item) => (
            <IntelligenceCard
              key={item.intelligence_id ?? item.code}
              item={item}
              saved={false}
              onSaved={() => undefined}
            />
          ))
          : <Empty>{t("No important new intelligence yet.")}</Empty>}
        <button
          className="button button-ghost"
          onClick={() => navigate("Intelligence")}
        >
          {t("See all Intelligence")}
        </button>
      </Panel>
      <Panel title={t("Topic changes")}>
        {topics.length
          ? topics.map((topic) => (
            <p key={topic.topic_id}>
              <strong>{topic.name}</strong> · {statusLabel(topic.current_state, t)}
            </p>
          ))
          : <Empty>{t("No important Topic changes since you last checked.")}</Empty>}
      </Panel>
      <Panel title={t("This week")}>
        {weekly.length
          ? weekly.map((brief) => (
            <div key={brief.brief_id}>
              {brief.no_important_information
                ? <p>{t("No important changes this week.")}</p>
                : brief.items.slice(0, 2).map((item) => (
                  <p className="dashboard-weekly-item" key={item.intelligence_id}>
                    <strong>{item.summary}</strong>
                    <small>
                      {item.topic_name} · {humanDate(brief.period_start, locale)}
                    </small>
                  </p>
                ))}
            </div>
          ))
          : <Empty>{t("No finalized weekly brief yet.")}</Empty>}
        <button
          className="button button-ghost"
          onClick={() => navigate("Intelligence")}
        >
          {t("Open Weekly")}
        </button>
      </Panel>
      {attention.length
        ? (
          <Panel title={t("Needs Attention")}>
            {attention.map((run) => (
              <Attention key={run.run_id} run={run} onRecover={onRecover} />
            ))}
          </Panel>
        )
        : null}
    </div>
  );
}
function Attention(
  { run, onRecover }: { run: SourceRun; onRecover?: (run: SourceRun) => void },
) {
  const { t, translateKnown } = useLanguage();
  if (run.recovery) {
    return (
      <article className="semantic-state state-blocked">
        <strong>{translateKnown(run.recovery.what_happened)}</strong>
        <p>{translateKnown(run.recovery.why_it_matters)}</p>
        <p>{translateKnown(run.recovery.will_not)}</p>
        {run.recovery.safe_action && onRecover && (
          <button
            type="button"
            className="button button-secondary"
            onClick={() => onRecover(run)}
          >
            {translateKnown(run.recovery.safe_action.label)}
          </button>
        )}
      </article>
    );
  }
  const [title, safety, action] = attentionCopy(run.attention_reason, t);
  return (
    <article className="semantic-state state-blocked">
      <strong>{title}</strong>
      <p>{safety}</p>
      <p>{action}</p>
    </article>
  );
}
function IntelligencePage({ refresh }: { refresh: number }) {
  const { t } = useLanguage();
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
            {t(item)}
          </button>
        ))}
      </div>
      {view === "Current" && (!current.data
        ? <Empty>{t("Loading verified Intelligence…")}</Empty>
        : currentAvailable.length
        ? currentAvailable.map((item) => (
          <IntelligenceCard
            key={item.intelligence_id ?? item.code}
            item={item}
            saved={false}
            onSaved={() => setRevision((value) => value + 1)}
          />
        ))
        : <Empty>{t("No verified Intelligence yet.")}</Empty>)}
      {view === "Saved" && (!saved.data
        ? <Empty>{t("Loading saved Intelligence…")}</Empty>
        : saved.data.saved.length
        ? saved.data.saved.map((item) => (
          <SavedCard
            key={item.intelligence_id}
            item={item}
            revision={revision}
            onChanged={() =>
              setRevision((value) => value + 1)}
          />
        ))
        : <Empty>{t("No saved Intelligence.")}</Empty>)}
      {view === "Weekly" && (!weekly.data
        ? <Empty>{t("Loading weekly digest…")}</Empty>
        : weekly.data.weekly_v1.length
        ? weekly.data.weekly_v1.map((brief) => (
          <WeeklyCard key={brief.brief_id} brief={brief} />
        ))
        : <Empty>{t("No finalized weekly digest. An empty week is valid.")}</Empty>)}
    </>
  );
}
function SavedCard(
  { item, revision, onChanged }: {
    item: Saved;
    revision: number;
    onChanged: () => void;
  },
) {
  const { t } = useLanguage();
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
  if (!detail.data) return <Empty>{t("Loading current saved Intelligence…")}</Empty>;
  return (
    <IntelligenceCard
      item={detail.data.intelligence}
      saved
      onSaved={onChanged}
    />
  );
}
function WeeklyCard({ brief }: { brief: Weekly }) {
  const { t, locale } = useLanguage();
  return (
    <Panel title={t("What mattered · {date}", { date: humanDate(brief.period_start, locale) })}>
      {brief.no_important_information
        ? <Empty>{t("No important information this week.")}</Empty>
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
              <summary>{t("Evidence references")}</summary>
              <p>{item.evidence_ids.join(", ")}</p>
            </details>
          </article>
        ))}
      <small>{t("Historical weekly content remains unchanged.")}</small>
    </Panel>
  );
}
function Topics({ refresh }: { refresh: number }) {
  const { t, locale } = useLanguage();
  const list = useRemote<{ topics: Topic[] }>("/topics", refresh);
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useRemote<{ topic: Topic }>(
    selected ? `/topics/${selected}` : "/topics",
  );
  if (list.error || detail.error) {
    return <ErrorState error={list.error ?? detail.error ?? ""} />;
  }
  if (!list.data) return <Empty>{t("Loading Topics…")}</Empty>;
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
                  {t("Current understanding: {status}", {
                    status: statusLabel(topic.current_state, t),
                  })}
                </small>
              </span>
              <Status value={topic.pinned ? "PINNED" : topic.lifecycle} />
            </button>
          ))
          : <Empty>{t("No Topics yet.")}</Empty>}
      </>
    );
  }
  if (!detail.data?.topic) return <Empty>{t("Loading Topic detail…")}</Empty>;
  const topic = detail.data.topic;
  return (
    <div className="dashboard-stack">
      <button className="button button-ghost" onClick={() => setSelected(null)}>
        {t("Back to Topics")}
      </button>
      <Panel title={topic.name}>
        <h3>{t("Current understanding")}</h3>
        <p>{statusLabel(topic.current_state, t)}.</p>
        <p>
          {topic.independence === "UNKNOWN"
            ? t("Not enough reliable information yet to determine how independent the supporting sources are.")
            : t("This understanding is based on the available supporting sources.")}
        </p>
        <button
          className="button button-secondary"
          onClick={() =>
            post(`/topics/${topic.topic_id}/pin`, { pinned: !topic.pinned })
              .then(() => setSelected(null))}
        >
          {topic.pinned ? t("Unpin Topic") : t("Pin Topic")}
        </button>
      </Panel>
      <Panel title={t("Evidence")}>
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
          : <Empty>{t("No current supporting information.")}</Empty>}
      </Panel>
      <Panel title={t("Timeline")}>
        {topic.timeline.length
          ? topic.timeline.map((event) => (
            <p key={event.event_id}>
              {humanDate(event.created_at, locale)} · {statusLabel(event.state, t)}
            </p>
          ))
          : <Empty>{t("No historical events.")}</Empty>}
      </Panel>
      <Panel title={t("Related Topics")}>
        {topic.relations.length
          ? topic.relations.map((relation) => (
            <p key={relation.related_topic_id}>{t("Related topic")}</p>
          ))
          : <Empty>{t("No related Topics.")}</Empty>}
      </Panel>
    </div>
  );
}

function Sources(
  { refresh, onRefresh, requestedSource, onRequestedSourceOpened, onOpenSettings }: {
    refresh: number;
    onRefresh: () => void;
    requestedSource: string | null;
    onRequestedSourceOpened: () => void;
    onOpenSettings: () => void;
  },
) {
  const { t } = useLanguage();
  const { data, error } = useRemote<{ sources: Source[] }>("/sources", refresh);
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  useEffect(() => {
    if (requestedSource) {
      setSelected(requestedSource);
      onRequestedSourceOpened();
    }
  }, [onRequestedSourceOpened, requestedSource]);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>{t("Loading Sources…")}</Empty>;
  return (
    <>
      <div className="page-actions">
        <button
          className="button button-primary"
          onClick={() => setAdding(true)}
        >
          {t("Add Source")}
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
                    <strong>{sourceLabel(source, t)}</strong>
                    <small>
                      {source.enabled
                        ? t("Monitoring new videos")
                        : t("Monitoring is paused")}
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
                    {t("Open Source")}
                  </a>
                </div>
              </div>
            ))}
          </div>
        )
        : (
          <Empty>
            <strong>{t("Set up your first Source")}</strong>
            <p>
              {t("Add a YouTube Source to monitor new videos, turn them into Intelligence, and keep Evidence inspectable.")}
            </p>
            <button
              className="button button-primary"
              onClick={() => setAdding(true)}
            >
              {t("Add Source")}
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
          onOpenSettings={onOpenSettings}
        />
      )}
    </>
  );
}
function ruleList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
function SourceForm(
  { onClose, onSaved, source, policy, schedules, returnFocusRef }: {
    onClose: () => void;
    onSaved: () => void;
    source?: Source;
    policy?: SourcePolicy;
    schedules?: Schedule[];
    returnFocusRef?: RefObject<HTMLElement>;
  },
) {
  const { t } = useLanguage();
  const dialogRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const onDialogKeyDown = useModalKeyboard(
    dialogRef,
    titleRef,
    onClose,
    returnFocusRef,
  );
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
          : t("The Source could not be saved."),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="overlay">
      <section
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-form-title"
        onKeyDown={onDialogKeyDown}
      >
        <div className="modal-head">
          <div>
            <h2 id="source-form-title" ref={titleRef} tabIndex={-1}>
              {source ? t("Edit Source configuration") : t("Add a Source")}
            </h2>
            <p className="hint">
              {t("These settings use the existing Source policy and schedule services.")}
            </p>
          </div>
          <button className="button button-ghost" onClick={onClose}>
            {t("Cancel")}
          </button>
        </div>
        <form
          onSubmit={submit}
          aria-describedby={error ? "source-form-error" : undefined}
        >
          <label className="field">
            {t("Source URL")}<input
              aria-label={t("Source URL")}
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
              placeholder="https://www.youtube.com/@channel"
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
          <Panel title={t("What to process")}>
            <label className="field">
              {t("Initial history")}<select
                aria-label={t("Initial history")}
                value={initialHistory}
                onChange={(event) => setInitialHistory(event.target.value)}
              >
                {INITIAL_HISTORY.map((value) => (
                  <option key={value} value={value}>
                    {t("{count} recent videos", { count: value })}
                  </option>
                ))}
              </select>
              <small>
                {t("How many recent existing videos are considered when this Source is first added.")}
              </small>
            </label>
            <label className="field">
              {t("Per-run limit")}<select
                aria-label={t("Per-run limit")}
                value={perRunLimit}
                onChange={(event) => setPerRunLimit(event.target.value)}
              >
                {PER_RUN_LIMIT.map((value) => (
                  <option key={value} value={value}>{t("{count} new videos", { count: value })}</option>
                ))}
              </select>
              <small>
                {t("The maximum number of new videos processed in one Source Run. Videos beyond this limit remain pending.")}
              </small>
            </label>
            <label className="field">
              {t("Focus")}<input
                aria-label={t("Focus")}
                value={focus}
                onChange={(event) => setFocus(event.target.value)}
                placeholder={t("Comma-separated terms")}
              />
              <small>{t("Use simple terms that help choose what is relevant.")}</small>
            </label>
            <label className="field">
              {t("Ignore")}<input
                aria-label={t("Ignore")}
                value={ignore}
                onChange={(event) => setIgnore(event.target.value)}
                placeholder={t("Comma-separated terms")}
              />
              <small>
                {t("Use simple terms to exclude videos from automatic relevance selection.")}
              </small>
            </label>
            <label className="field">
              {t("Distillation style")}<select
                aria-label={t("Distillation style")}
                value={style}
                onChange={(event) => setStyle(event.target.value)}
              >
                {STYLES.map(([value, label]) => (
                  <option key={value} value={value}>{t(label)}</option>
                ))}
              </select>
              <small>{t(STYLES.find(([value]) => value === style)?.[2] ?? "A useful mix of product, technical, and trend context.")}</small>
            </label>
          </Panel>
          <Panel title={t("When it runs")}>
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
                {t("Choose when this Source runs automatically. Manual does not create an automatic schedule.")}
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
          {error && (
            <div id="source-form-error" role="alert">
              <ErrorState error={error} />
            </div>
          )}
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
              {busy ? t("Saving…") : source ? t("Save changes") : t("Add Source")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
function SourceDetail(
  { id, onClose, onRefresh, onOpenSettings }: {
    id: string;
    onClose: () => void;
    onRefresh: () => void;
    onOpenSettings: () => void;
  },
) {
  const { t, translateKnown } = useLanguage();
  const [revision, setRevision] = useState(0);
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
  >(`/sources/${id}`, revision);
  const sourceReadiness = useRemote<{ readiness: Readiness }>(
    `/sources/${id}/readiness`,
    revision,
  );
  const sourceReadinessProjection = isReadiness(sourceReadiness.data?.readiness)
    ? sourceReadiness.data.readiness
    : null;
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const editTriggerRef = useRef<HTMLButtonElement>(null);
  const onDialogKeyDown = useModalKeyboard(dialogRef, titleRef, onClose);
  useEffect(() => {
    if (dialogRef.current) dialogRef.current.inert = editing;
  }, [editing]);
  const closeEditor = () => {
    if (dialogRef.current) {
      dialogRef.current.inert = false;
      dialogRef.current.removeAttribute("aria-hidden");
    }
    setEditing(false);
  };
  const latestRun = data?.source_runs.at(-1);
  useEffect(() => {
    if (!latestRun || !["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(
      latestRun.state,
    )) return;
    const timer = window.setInterval(() => {
      setRevision((value) => value + 1);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [latestRun?.run_id, latestRun?.state]);
  if (error) return <ErrorState error={error} />;
  if (!data) return <Empty>{t("Loading Source…")}</Empty>;
  const check = async () => {
    const result = await post<
      {
        source_run?: SourceRun;
        status?: string;
        message?: string;
        readiness?: Readiness;
      }
    >(`/sources/${id}/check`, { command_id: commandId() });
    if (result.source_run) {
      setMessage(
        t("Your check was accepted. {status}. You can leave and return; this status comes from the saved run.", {
          status: result.source_run.progress?.label
            ? translateKnown(result.source_run.progress.label)
            : t("Waiting to start"),
        }),
      );
      setRevision((value) => value + 1);
      onRefresh();
      return;
    }
    if (result.status === "BLOCKED") {
      setMessage(
        `${result.readiness?.overall.label
          ? translateKnown(result.readiness.overall.label)
          : t("Setup required")}. ${result.readiness?.overall.message
          ? translateKnown(result.readiness.overall.message)
          : t("No Source Run was created.")}`,
      );
      return;
    }
    if (result.status === "FAILED_FINAL") {
      setMessage(
        t("The Source check did not complete. Your Source configuration and existing Intelligence are unchanged."),
      );
      return;
    }
    setMessage(
      t("The Source check completed. Review recent videos and Source status for the outcome."),
    );
  };
  return (
    <div className="overlay">
      <section
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-detail-title"
        aria-hidden={editing ? "true" : undefined}
        onKeyDown={onDialogKeyDown}
      >
        <div className="modal-head">
          <div>
            <h2 id="source-detail-title" ref={titleRef} tabIndex={-1}>
              {sourceLabel(data.source, t)}
            </h2>
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
        <Panel title={t("Source management")}>
          <p>
            <Status value={data.source.enabled ? "ENABLED" : "DISABLED"} />{" "}
            {t("Monitoring changes affect future checks only; existing Intelligence remains unchanged.")}
          </p>
          <div className="inline-actions">
            <button
              ref={editTriggerRef}
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
              {data.source.enabled
                ? t("Stop future monitoring")
                : t("Resume monitoring")}
            </button>
          </div>
        </Panel>
        <Panel title={t("Processing policy")}>
          <p>
            {t("Initial history: {count} recent existing videos when this Source was first added.", {
              count: data.policy.initial_history_count,
            })}
          </p>
          <p>
            {t("Per-run limit: {count} new videos in one Source Run; overflow remains pending.", {
              count: data.policy.per_run_max_new_videos,
            })}
          </p>
          <p>
            {t("Focus: {focus}. Ignore: {ignore}.", {
              focus: data.policy.focus_rules.join(", ") || t("No focus terms"),
              ignore: data.policy.ignore_rules.join(", ") || t("No ignore terms"),
            })}
          </p>
          <p>
            {t("Style: {style}.", {
              style: t(STYLES.find(([value]) => value === data.policy.distillation_style)
                ?.[1] ?? "Balanced"),
            })}
          </p>
        </Panel>
        <Panel title={t("Schedule")}>
          {data.schedules.length
            ? data.schedules.map((schedule) => (
              <p key={schedule.schedule_id}>
                <Status value={schedule.enabled ? "ENABLED" : "DISABLED"} />
                {" "}
                {t("Runs {frequency}{time}{timezone}.", {
                  frequency: schedule.frequency === "DAILY"
                    ? t("daily")
                    : schedule.frequency === "WEEKLY"
                    ? t("weekly")
                    : schedule.frequency.toLowerCase(),
                  time: schedule.local_time
                    ? t(" at {time}", { time: schedule.local_time })
                    : "",
                  timezone: schedule.timezone ? ` (${schedule.timezone})` : "",
                })}
              </p>
            ))
            : (
              <Empty>
                {t("This Source runs manually. Edit configuration to add an automatic schedule.")}
              </Empty>
            )}
        </Panel>
        {(sourceReadiness.error ||
          (sourceReadiness.data && !sourceReadinessProjection)) && (
          <DisconnectedReadiness />
        )}
        {sourceReadinessProjection && (
          <ReadinessPanel
            readiness={sourceReadinessProjection}
            compact
            onAction={(dimension) => {
              if (dimension.recovery?.action === "EDIT_SOURCE_CONFIGURATION") {
                setEditing(true);
              } else {
                onOpenSettings();
              }
            }}
          />
        )}
        <button
          className="button button-primary"
          onClick={check}
          disabled={sourceReadinessProjection?.overall.code !== "READY"}
          aria-describedby="check-now-guidance"
        >
          {t("Check Now")}
        </button>
        <p className="hint" id="check-now-guidance">
          {sourceReadinessProjection?.overall.code === "READY"
            ? t("Starts one new normal Source Run. This is not a retry action.")
            : t("Check Now remains unavailable until the prerequisite summary says Ready to check a Source.")}
        </p>
        {message && (
          <div className="semantic-state state-neutral">
            <p>{message}</p>
          </div>
        )}
        <Panel title={t("Recent videos")}>
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
                          <p>{filterReason(video.filter?.reason, t)}</p>
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
                                  ? t("This video was accepted for analysis. Its relevance skip has been overridden; other safety, budget, and model rules still apply.")
                                  : t("This video’s relevance skip has been overridden; other safety, budget, and model rules still apply."),
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
                          {t("Current processing state: {status}.", {
                            status: statusLabel(video.processing_status, t),
                          })}
                        </p>
                      )}
                  </div>
                </div>
              );
            })
            : <Empty>{t("No recent videos for this Source.")}</Empty>}
        </Panel>
        <Panel title={t("Source Run status")}>
          {data.source_runs.length
            ? data.source_runs.map((run) =>
              run.attention_reason
                ? (
                  <Attention
                    key={run.run_id}
                    run={run}
                    onRecover={(item) => {
                      const kind = item.recovery?.safe_action?.kind;
                      if (kind === "VIEW_USAGE" ||
                        kind === "VIEW_CREDENTIAL_SETUP" ||
                        kind === "CHECK_READINESS") {
                        onOpenSettings();
                      }
                    }}
                  />
                )
                : (
                  <article className="run-orientation" key={run.run_id}>
                    <Status value={run.state} />
                    <strong>{run.result?.label
                      ? translateKnown(run.result.label)
                      : run.progress?.label
                      ? translateKnown(run.progress.label)
                      : statusLabel(run.state, t)}</strong>
                    {run.result?.kind !== "COMPLETED_WITH_INTELLIGENCE" &&
                      run.progress?.label && run.result?.label !== run.progress.label && (
                      <p>{t("Current step: {status}.", {
                        status: translateKnown(run.progress.label),
                      })}</p>
                    )}
                    {run.result?.kind === "COMPLETED_WITH_INTELLIGENCE" && (
                      <p>
                        {t(
                          run.result.intelligence_count === 1
                            ? "Produced {count} trusted Intelligence item."
                            : "Produced {count} trusted Intelligence items.",
                          { count: run.result.intelligence_count ?? 0 },
                        )}
                      </p>
                    )}
                  </article>
                )
            )
            : <Empty>{t("No Source Runs yet.")}</Empty>}
        </Panel>
      </section>
      {editing && (
        <SourceForm
          source={data.source}
          policy={data.policy}
          schedules={data.schedules}
          returnFocusRef={editTriggerRef}
          onClose={closeEditor}
          onSaved={() => {
            closeEditor();
            onRefresh();
            onClose();
          }}
        />
      )}
    </div>
  );
}
function Investigations() {
  const { t } = useLanguage();
  return (
    <div className="semantic-state state-neutral">
      <Status value="UNAVAILABLE" />
      <h2>{t("Investigations are not active in V1")}</h2>
      <p>
        {t("This is planned beyond V1. Evidence Expansion, external validation, and Deep Analysis are not available.")}
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
function preferenceCopy(preference: Preference, t: Translate) {
  const key = ({
    EXPLICIT: "You directly chose this.",
    DERIVED: "The app inferred this from your feedback.",
    TEMPORARY: "Used only until its expiry.",
  } as Record<string, MessageKey>)[preference.provenance] ??
    "This preference keeps its recorded origin.";
  return t(key);
}
function usageReason(value: string, t: Translate) {
  const key = ({
    PERSONALIZED_INTELLIGENCE: "Personalized Intelligence",
    MANUAL_DISTILLATION: "Manual analysis",
  } as Record<string, MessageKey>)[value] ?? "Recorded work";
  return t(key);
}
function Settings(
  { refresh, onReadinessAction }: {
    refresh: number;
    onReadinessAction: (dimension: ReadinessDimension) => void;
  },
) {
  const { locale, setLocale, t, translateKnown } = useLanguage();
  const [readinessRefresh, setReadinessRefresh] = useState(0);
  const readiness = useRemote<{ readiness: Readiness }>(
    "/readiness",
    refresh + readinessRefresh,
  );
  const readinessProjection = isReadiness(readiness.data?.readiness)
    ? readiness.data.readiness
    : null;
  const settings = useRemote<{ providers: ProviderStatus[] }>(
    "/settings",
    refresh,
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
      <>
        <DisconnectedReadiness />
        <ErrorState
          error={settings.error ?? prefs.error ?? policy.error ?? usage.error ??
            ""}
        />
      </>
    );
  }
  if (!settings.data || !prefs.data || !policy.data || !usage.data ||
    (!readiness.data && !readiness.error)) {
    return <Empty>{t("Loading Settings…")}</Empty>;
  }
  const globalPolicy = policy.data.policy;
  const videoDistillation = settings.data.providers.find((provider) =>
    provider.production_eligible && provider.authorized &&
    provider.scope === "V1_VIDEO_DISTILLATION_ONLY"
  );
  const otherProviders = settings.data.providers.filter((provider) =>
    provider !== videoDistillation
  );
  return (
    <div className="settings-stack">
      <Panel title={t("General")}>
        <div className="field language-setting">
          <label htmlFor="ui-language">{t("Language")}</label>
          <select
            id="ui-language"
            aria-describedby="ui-language-description"
            value={locale}
            onChange={(event) =>
              setLocale(event.target.value === "zh-CN" ? "zh-CN" : "en")}
          >
            <option value="en">English</option>
            <option value="zh-CN">简体中文</option>
          </select>
          <small id="ui-language-description">
            {t("Choose the language used for product controls and guidance. Source content and Intelligence remain unchanged.")}
          </small>
        </div>
      </Panel>
      {(readiness.error || !readinessProjection) && <DisconnectedReadiness />}
      {readinessProjection && (
        <ReadinessPanel
          readiness={readinessProjection}
          onAction={(dimension) => {
            if (dimension.recovery?.action === "CHECK_READINESS" ||
              dimension.recovery?.action === "VIEW_SETUP_INSTRUCTIONS") {
              setReadinessRefresh((value) => value + 1);
              return;
            }
            if (dimension.recovery?.action === "VIEW_USAGE") {
              document.getElementById("resource-usage")?.scrollIntoView();
              return;
            }
            onReadinessAction(dimension);
          }}
        />
      )}
      <Panel title={t("Preference Center")}>
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
                  {preferenceCopy(preference, t)}
                  {preference.expires_at
                    ? ` ${t("Expires {date}.", {
                      date: humanDate(preference.expires_at, locale),
                    })}`
                    : ""}
                </p>
              </div>
            </article>
          ))
          : <Empty>{t("No Preferences yet.")}</Empty>}
      </Panel>
      <Panel title={t("Source policy")}>
        <p>
          {t("Default for Sources without their own configuration: initial history {initial}, per-run limit {limit}, {style} style.", {
            initial: globalPolicy.initial_history_count,
            limit: globalPolicy.per_run_max_new_videos,
            style: t(STYLES.find(([value]) =>
              value === globalPolicy.distillation_style
            )?.[1] ?? "Balanced"),
          })}
        </p>
      </Panel>
      <Panel title={t("Models and cost")}>
        <div className="capability-grid">
          <article className="capability-card">
            <div className="capability-heading">
              <h3>{t("Video Distillation")}</h3>
              <Status
                value={readinessProjection?.video_distillation.code ??
                  "UNAVAILABLE"}
              />
            </div>
            <p>
              {readinessProjection?.video_distillation.message
                ? translateKnown(readinessProjection.video_distillation.message)
                : t("Video Distillation readiness is unavailable.")}
            </p>
            {videoDistillation && (
              <details className="provenance">
                <summary>{t("Provider and model details")}</summary>
                <p>
                  {videoDistillation.provider} · {videoDistillation.model}
                </p>
                <p>{t("Scope: Video Distillation only.")}</p>
                <p>{translateKnown(videoDistillation.reason)}</p>
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
                {t("{provider}: not available for production use.", {
                  provider: provider.provider,
                })}
              </p>
            ))}
          </details>
        )}
      </Panel>
      <section id="resource-usage">
        <Panel title={t("Resource Usage")}>
        {usage.data.usage.length
          ? usage.data.usage.map((item) => (
            <article className="metadata-row" key={item.execution_id}>
              <div>
                <strong>{usageReason(item.reason, t)}</strong>
                <p>
                  {t("{count} calls · {duration}", {
                    count: item.invocation_count,
                    duration: item.duration_ms === null
                      ? t("Duration unavailable")
                      : t("Duration {duration}ms", {
                        duration: item.duration_ms,
                      }),
                  })}
                </p>
                <p>
                  {t("Token usage: {tokens}; Cost: {cost}.", {
                    tokens: item.input_tokens === null ||
                        item.output_tokens === null
                      ? t("Unavailable")
                      : t("{input} input / {output} output", {
                        input: item.input_tokens,
                        output: item.output_tokens,
                      }),
                    cost: item.cost_microunits === null
                      ? t("Unavailable")
                      : t("{cost} microunits", {
                        cost: item.cost_microunits,
                      }),
                  })}
                </p>
                <Status value={item.status} />
              </div>
              <details className="provenance">
                <summary>{t("Technical details")}</summary>
                <p>
                  {t("Model: {model}. Provider: {provider}.", {
                    model: item.actual_model ?? t("Unknown"),
                    provider: item.actual_provider ?? t("Unknown"),
                  })}
                </p>
              </details>
            </article>
          ))
          : (
            <Empty>
              {t("No Resource Ledger entries yet. Values are never estimated.")}
            </Empty>
          )}
        </Panel>
      </section>
      <Panel title={t("Data and privacy")}>
        <p>
          {t("Local-first means local persistence by default. Credential values are never shown.")}
        </p>
      </Panel>
    </div>
  );
}
