import { ReactNode, useEffect, useRef, useState } from "react";
import { ApiRequestError, api, patch, post, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

export type Tracking = {
  health: string; coverage: string; verified_at?: string | null;
  baseline_at?: string | null; next_check_at?: string; manual_check_at?: string;
  update_count: number; pending_count: number; unavailable_count?: number;
  checking?: boolean; processing_count?: number;
};

/** Capability as reported by the service. */
export type CreatorFollowingCapability = {
  available: boolean;
  code: string;
  message?: string | null;
};

/**
 * "Unknown" is a distinct state from "available". The service is the only
 * authority on whether creator tracking works, so the UI asks once and shows
 * nothing it cannot support — it never assumes a capability before it is told.
 */
export type CreatorFollowingCapabilityState =
  | { known: false }
  | { known: true; capability: CreatorFollowingCapability | null };

export const CREATOR_TRACKING_UNAVAILABLE = "CREATOR_TRACKING_UNAVAILABLE";

/**
 * Each surface asks the service for itself rather than sharing a cached answer,
 * so a capability that changes is never shown from a stale value.
 */
export function useCreatorFollowingCapability(provider: "YOUTUBE" | "BILIBILI" = "BILIBILI"): CreatorFollowingCapabilityState {
  const [state, setState] = useState<CreatorFollowingCapabilityState>({ known: false });
  useEffect(() => {
    let disposed = false;
    void api<{ bilibili?: { creator_following?: CreatorFollowingCapability }; youtube?: { channel_following?: CreatorFollowingCapability } }>("/settings")
      .then(value => { if (!disposed) setState({ known: true, capability: (provider === "YOUTUBE" ? value.youtube?.channel_following : value.bilibili?.creator_following) ?? null }); })
      .catch(() => { if (!disposed) setState({ known: true, capability: null }); });
    return () => { disposed = true; };
  }, [provider]);
  return state;
}

const withdrawn = (state: CreatorFollowingCapabilityState) =>
  state.known && state.capability !== null && !state.capability.available;

/**
 * Health is a fact about stored data, so every value must resolve to a sentence
 * the user can act on. An unknown value is reported as unknown rather than
 * smoothed into a reassuring phrase.
 */
export const trackingCopy = (health: string, provider?: string) => provider === "YOUTUBE" && ["OFFLINE", "NETWORK_UNAVAILABLE"].includes(health)
  ? "Unable to connect to YouTube. Check your network or VPN and try again."
  : ({
  HEALTHY: "Source checks are working",
  BASELINE_PENDING: "Waiting to establish the starting point",
  OFFLINE: "Unable to connect. Your last successful check is preserved.",
  RATE_LIMITED: "Public source requests are limited. Try again later.",
  RISK_CONTROLLED: "Bilibili has temporarily restricted public requests. Your stored Content is preserved.",
  ACCESS_DENIED: "This source is not publicly accessible. No login is used.",
  NOT_FOUND: "This public source is unavailable. Stored Content is preserved.",
  PROVIDER_ERROR: "The source could not be checked. Try again later.",
  VIDEO_UNAVAILABLE: "One or more of this creator's videos are no longer public. Everything already stored is preserved.",
  STATE_INVALID: "Tracking data failed verification. Existing Content is preserved.",
  CHECK_INCOMPLETE: "Some updates may still be missing. Later checks will continue.",
  UPDATE_GAP: "Some updates may still be missing. Later checks will continue.",
  COOLDOWN: "Checked recently. Please wait before checking again.",
  BUSY: "A source check is already running.",
  PAUSED: "Monitoring is paused",
  CAPABILITY_UNAVAILABLE: "Continuous creator tracking is currently unavailable. Stored Content is preserved.",
}[health] ?? "The source could not be checked. Try again later.");

function UnavailableNotice({ state, creator }: { state: CreatorFollowingCapabilityState; creator: boolean }) {
  const { t } = useUiLanguage();
  if (!withdrawn(state)) return null;
  return <div role="status" className="hint">
    <strong>{t("Continuous creator tracking is currently unavailable")}</strong>
    <p>{t((state.known ? state.capability?.message : null) || "Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.")}</p>
    {creator && <p>{t("Sources already followed, their stored Content and all Evidence are preserved. No new creator can be followed until this returns.")}</p>}
  </div>;
}

export function CreatorFollowForm({ capability: suppliedCapability, onSaved, provider = "BILIBILI" }: {
  capability?: CreatorFollowingCapabilityState; onSaved: () => void; provider?: "YOUTUBE" | "BILIBILI";
}) {
  const youtube = provider === "YOUTUBE";
  const reportedCapability = useCreatorFollowingCapability(provider);
  const capability = suppliedCapability ?? reportedCapability;
  const { t } = useUiLanguage();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  if (!capability.known) return <p role="status">{t("Checking whether this is available…")}</p>;
  if (youtube && capability.known && capability.capability?.available !== true) return <p role="status">{t("Channel following is currently unavailable. Stored Content is preserved.")}</p>;
  if (withdrawn(capability)) return <UnavailableNotice state={capability} creator={false} />;
  return <>
    <p>{t("Follow from now on. Newly published public videos enter Content automatically while the app is running. Existing videos are not imported.")}</p>
    {!saved && <form onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setMessage(null);
      try {
        const result = await post<{ source?: { tracking?: Tracking } }>(youtube ? "/sources/channels" : "/sources/creators", { input: input.trim() });
        if (youtube && result.source?.tracking?.health === "OFFLINE") setMessage(trackingCopy("OFFLINE", provider));
        setSaved(true);
      } catch (error) {
        const code = error instanceof ApiRequestError ? error.code.replace(/^(BILIBILI|YOUTUBE)_/, "") : "OFFLINE";
        setMessage(code === "INVALID_INPUT" ? (youtube ? "Enter an HTTPS YouTube channel URL, @handle or channel id." : "Enter an HTTPS Bilibili creator profile URL or numeric creator id.") : trackingCopy(code, provider));
      } finally { setBusy(false); }
    }}>
      <label className="field">{t(youtube ? "Channel URL, @handle or channel id" : "Creator profile URL or numeric id")}<input autoFocus maxLength={2048} value={input} disabled={busy} onChange={event => setInput(event.target.value)} placeholder={youtube ? "https://www.youtube.com/@channel" : "https://space.bilibili.com/123"} /></label>
      <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? "Establishing tracking…" : youtube && message ? "Retry" : youtube ? "Follow channel" : "Follow creator")}</button>
    </form>}
    {busy && <p role="status">{t("Establishing tracking…")}</p>}
    {message && <p role="alert">{t(message)}</p>}
    {saved && <div role="status"><p>{t(youtube ? "Channel followed. Check Following for its starting point and source health." : "Creator followed. Check the Following detail for its starting point and source health.")}</p><button className="button button-primary" onClick={onSaved}>{t("Done")}</button></div>}
  </>;
}

export function FollowCreatorFromContent({ id, capability: suppliedCapability, provider = "BILIBILI" }: {
  id: string; capability?: CreatorFollowingCapabilityState; provider?: "YOUTUBE" | "BILIBILI";
}) {
  const youtube = provider === "YOUTUBE";
  const reportedCapability = useCreatorFollowingCapability(provider);
  const capability = suppliedCapability ?? reportedCapability;
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (youtube && capability.known && capability.capability?.available !== true) return <button className="button button-secondary" disabled>{t("Channel following is currently unavailable. Stored Content is preserved.")}</button>;
  if (withdrawn(capability)) return <div className="button-row">
    <button className="button button-secondary" disabled>{t("Continuous creator tracking is currently unavailable")}</button>
  </div>;
  return <div className="button-row">
    <button className="button button-secondary" disabled={busy || !capability.known} onClick={async () => {
      if (busy) return; setBusy(true);
      try { await post(`/videos/${id}/follow-${youtube ? "channel" : "creator"}`, {}); setMessage(youtube ? "Channel followed. Check Following for its starting point and source health." : "Creator followed. Check the Following detail for its starting point and source health."); }
      catch (error) {
        const code = error instanceof ApiRequestError ? error.code.replace(/^(BILIBILI|YOUTUBE)_/, "") : "PROVIDER_ERROR";
        setMessage(trackingCopy(code, youtube ? "YOUTUBE" : "BILIBILI"));
      }
      finally { setBusy(false); }
    }}>{t(busy ? "Establishing tracking…" : youtube ? "Follow this channel" : "Follow this creator")}</button>
    {message && <p role="status">{t(message)}</p>}
  </div>;
}

type Detail = {
  source: { provider?: string; source_id: string; display_name: string | null; canonical_url: string; enabled: boolean;
    processing_mode?: "ORGANIZE_CONTENT" | "EXTRACT_INTELLIGENCE"; last_checked_at: string | null; last_success_at: string | null; last_error_code?: string | null; tracking: Tracking };
  recent_videos: { video_id: string; title: string | null; processing_status: string }[];
  source_runs: { run_id?: string; state: string }[];
};

const readObject = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const readText = (value: unknown) => typeof value === "string" && value.trim().length > 0;
const optionalReadText = (value: unknown) => value === undefined || value === null || typeof value === "string";
const readCount = (value: unknown) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
// State/copy dictionaries consume machine tokens, never arbitrary object keys.
const readToken = (value: unknown) => typeof value === "string" && /^[A-Z][A-Z0-9_]*$/.test(value);
const optionalReadDate = (value: unknown) => value === undefined || value === null
  || (readText(value) && typeof value === "string" && Number.isFinite(Date.parse(value)));
const optionalChoice = (value: unknown, choices: string[]) => value === undefined || choices.includes(value as string);
const belongsToSource = (item: Record<string, unknown>, id: string) => item.source_id === undefined || item.source_id === id;

/** Validate the fields consumed by both independently polled detail surfaces. */
export function validFollowingSourceRead(value: unknown): boolean {
  if (!readObject(value) || !readText(value.source_id) || typeof value.enabled !== "boolean") return false;
  if (!["display_name", "friendly_name", "channel_id", "video_id"].every(key => optionalReadText(value[key]))
      || (value.canonical_url !== undefined && typeof value.canonical_url !== "string")
      || !optionalChoice(value.provider, ["YOUTUBE", "BILIBILI", "LOCAL"])
      || !optionalChoice(value.source_type, ["CHANNEL", "CREATOR", "VIDEO_URL", "LOCAL_LIBRARY"])
      || !optionalChoice(value.processing_policy, ["DISCOVER_ONLY", "STANDARD_INTELLIGENCE", "FULL_INTELLIGENCE"])
      || (value.processing_mode !== null && !optionalChoice(value.processing_mode, ["ORGANIZE_CONTENT", "EXTRACT_INTELLIGENCE"]))
      || !["last_checked_at", "last_success_at"].every(key => optionalReadDate(value[key]))
      || (value.tracking_parent_source_ids !== undefined && (!Array.isArray(value.tracking_parent_source_ids) || !value.tracking_parent_source_ids.every(readText)))
      || (value.insight_count !== undefined && !readCount(value.insight_count))) return false;
  if (value.last_error !== undefined && value.last_error !== null
      && (!readObject(value.last_error) || !readToken(value.last_error.code) || !optionalReadText(value.last_error.message))) return false;
  if (value.tracking === undefined || value.tracking === null) return true;
  const tracking = value.tracking;
  if (!readObject(tracking) || !readToken(tracking.health) || !readToken(tracking.coverage)
      || !readCount(tracking.update_count) || !readCount(tracking.pending_count)
      || (tracking.checking !== undefined && typeof tracking.checking !== "boolean")
      || !["unavailable_count", "processing_count"].every(key => tracking[key] === undefined || readCount(tracking[key]))
      || !["verified_at", "baseline_at", "next_check_at", "manual_check_at"].every(key => optionalReadDate(tracking[key]))) return false;
  return value.provider === undefined || value.provider === "YOUTUBE" || value.provider === "BILIBILI";
}

function validFollowingPolicyRead(value: unknown, modes: unknown, id: string): boolean {
  if (!readObject(value) || !belongsToSource(value, id) || !readCount(value.initial_history_count)
      || !readCount(value.per_run_max_new_videos) || value.per_run_max_new_videos === 0
      || ![value.focus_rules, value.ignore_rules].every(rules => Array.isArray(rules) && rules.length <= 20 && rules.every(validInterestRule))
      || !INTEREST_STYLES.includes(value.distillation_style as string)
      || !(value.source_policy_revision_id === undefined || value.source_policy_revision_id === null
        || (typeof value.source_policy_revision_id === "string" && readText(value.source_policy_revision_id) && value.source_policy_revision_id.length <= 512))) return false;
  return modes === undefined || (readObject(modes) && [modes.focus, modes.ignore, modes.style].every(mode => mode === "INHERIT" || mode === "OVERRIDE"));
}

export function validFollowingDetailRead(value: unknown, id: string, requireTracking = false): boolean {
  if (!readObject(value) || !readObject(value.source) || !validFollowingSourceRead(value.source)
      || value.source.source_id !== id || (requireTracking && !value.source.tracking)) return false;
  if (!value.source.tracking && value.source.source_type !== "CHANNEL" && !["LOCAL", "BILIBILI"].includes(value.source.provider as string)) {
    if (!validFollowingPolicyRead(value.policy, value.policy_modes, id) || !Array.isArray(value.schedules)
        || !value.schedules.every(schedule => readObject(schedule) && readText(schedule.schedule_id)
          && ["MANUAL", "DAILY", "WEEKLY"].includes(schedule.frequency as string) && typeof schedule.enabled === "boolean"
          && optionalReadText(schedule.local_time) && (schedule.timezone === undefined || typeof schedule.timezone === "string")
          && (schedule.weekday === undefined || schedule.weekday === null || (typeof schedule.weekday === "number" && Number.isInteger(schedule.weekday) && schedule.weekday >= 0 && schedule.weekday <= 6))
          && (schedule.target_id === undefined || schedule.target_id === id))) return false;
  }
  return Array.isArray(value.source_runs) && value.source_runs.every(run =>
    readObject(run) && readToken(run.state) && (run.run_id === undefined || readText(run.run_id))
    && (run.attention_reason === undefined || run.attention_reason === null || readToken(run.attention_reason)) && belongsToSource(run, id))
    && Array.isArray(value.recent_videos) && value.recent_videos.every(video =>
      readObject(video) && readText(video.video_id) && (video.title === null || typeof video.title === "string")
      && readToken(video.processing_status) && belongsToSource(video, id)
      && (video.filter === undefined || video.filter === null || (readObject(video.filter)
        && readToken(video.filter.outcome) && readToken(video.filter.reason) && belongsToSource(video.filter, id)
        && (video.filter.video_id === undefined || video.filter.video_id === video.video_id))));
}

const ACTIVE_STATES = ["QUEUED", "RUNNING", "WAITING", "PARTIAL"];
const isActive = (data: Detail | null) =>
  Boolean(data?.source.tracking.checking || data?.source_runs.some(run => ACTIVE_STATES.includes(run.state)));

type DetailProps = {
  id: string; capability: CreatorFollowingCapabilityState; refreshNotice?: ReactNode; onClose: () => void; onRefresh: () => void;
};

export function CreatorFollowingDetail(props: DetailProps) {
  // A different source starts with its own identity, commands and read state.
  return <CreatorFollowingDetailContent key={props.id} {...props} />;
}

function CreatorFollowingDetailContent({ id, capability, onClose, onRefresh, refreshNotice }: DetailProps) {
  const { t } = useUiLanguage();
  const [data, setData] = useState<Detail | null>(null);
  const [revision, setRevision] = useState(0);
  const [interestOpen, setInterestOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [checkRun, setCheckRun] = useState<string | null>(null);
  const [readError, setReadError] = useState(false);
  const [reading, setReading] = useState(true);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => {
    let disposed = false;
    setReading(true);
    void api<Detail>(`/sources/${id}`).then(value => {
      if (disposed) return;
      if (!validFollowingDetailRead(value, id, true)) {
        throw new Error("Source detail response identity is unavailable");
      }
      setData(value); setReadError(false);
    }).catch(() => { if (!disposed) setReadError(true); })
      .finally(() => { if (!disposed) setReading(false); });
    return () => { disposed = true; };
  }, [id, revision]);
  useEffect(() => {
    if (reading || (!isActive(data) && !checkRun)) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data, checkRun, reading]);
  // Polling replaces this component's data, so the outcome of the last command is
  // held separately: the user is told what happened and a refetch cannot erase it.
  useEffect(() => {
    if (!data) return;
    if (checkRun) {
      const run = data.source_runs.find(item => item.run_id === checkRun);
      if (run && !ACTIVE_STATES.includes(run.state)) {
        setMessage(trackingCopy(data.source.tracking.health, data.source.provider));
        setNotice(null); setCheckRun(null);
      }
    } else if (!isActive(data) && notice) setMessage(notice);
  }, [data, notice, checkRun]);
  useEffect(() => {
    const retryAt = data?.source.tracking.manual_check_at ?? data?.source.tracking.next_check_at;
    if (!retryAt) return;
    const remaining = new Date(retryAt).getTime() - Date.now();
    if (!Number.isFinite(remaining) || remaining <= 0) return;
    const timer = setTimeout(() => setRevision(value => value + 1), Math.min(remaining + 50, 2147483647));
    return () => clearTimeout(timer);
  }, [data]);
  const source = data?.source;
  const active = isActive(data);
  const off = Boolean(source) && source?.provider !== "YOUTUBE" && withdrawn(capability);
  const title = source ? source.provider === "YOUTUBE" ? "Channel Following" : "Creator Following" : "Following";
  const baselineEstablished = Boolean(source?.tracking.baseline_at ?? source?.tracking.verified_at);
  const manualCheckAt = source?.tracking.manual_check_at ?? source?.tracking.next_check_at;
  const cooldownUntil = manualCheckAt ? new Date(manualCheckAt) : null;
  const coolingDown = cooldownUntil !== null && cooldownUntil.getTime() - Date.now() > 0;
  const automaticCheckAt = source?.tracking.next_check_at ? new Date(source.tracking.next_check_at) : null;
  const needsAttention = ["STATE_INVALID", "RISK_CONTROLLED", "ACCESS_DENIED"].includes(source?.tracking.health ?? "");
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t(title)}>
    <div className="modal-head"><h2>{source?.display_name ?? t(title)}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    {refreshNotice}
    {reading && source && <p role="status" className="hint">{t("Refreshing source details…")}</p>}
    {off && <UnavailableNotice state={capability} creator />}
    {source && <>
      <p>{t(source.provider === "YOUTUBE" ? "YouTube" : "Bilibili")} · {off ? t("Continuous creator tracking is currently unavailable") : source.enabled ? t("Monitoring new videos") : t("Monitoring is paused")}</p>
      {source.provider === "YOUTUBE" && <label className="field">{t("When new content is found")}
        <select aria-label={t("When new content is found")} value={source.processing_mode ?? "ORGANIZE_CONTENT"} disabled={busy || reading || readError} onChange={async event => {
          setBusy(true); setMessage(null);
          try { await patch(`/sources/${id}`, { processing_policy: event.target.value === "ORGANIZE_CONTENT" ? "DISCOVER_ONLY" : "STANDARD_INTELLIGENCE" }); if (!mounted.current) return; setRevision(value => value + 1); onRefresh(); setNotice("Saved"); }
          catch { if (mounted.current) setMessage("The source could not be checked. Try again later."); }
          finally { if (mounted.current) setBusy(false); }
        }}><option value="ORGANIZE_CONTENT">{t("Organize content")}</option><option value="EXTRACT_INTELLIGENCE">{t("Also extract Intelligence")}</option></select>
      </label>}
      <button className="button button-secondary" disabled={busy || reading || readError} onClick={() => setInterestOpen(true)}>{t("Edit interests")}</button>
      {interestOpen && <SourceInterestEditor key={id} id={id} onClose={() => setInterestOpen(false)} />}
      <a href={source.canonical_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
      <dl className="creator-tracking">
        <dt>{t(off ? "Last recorded source health" : "Source health")}</dt><dd>{t(trackingCopy(source.tracking.health, source.provider))}</dd>
        <dt>{t("Starting point established")}</dt><dd>{baselineEstablished ? t("Yes") : t("No, no successful check has completed yet")}</dd>
        <dt>{t("Last checked")}</dt><dd>{source.last_checked_at ? new Date(source.last_checked_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Last successful check")}</dt><dd>{source.last_success_at ? new Date(source.last_success_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Next eligible check")}</dt><dd>{!source.enabled ? t("Paused") : off ? t("None while this capability is unavailable") : coolingDown ? cooldownUntil.toLocaleString() : t("Not scheduled")}</dd>
        <dt>{t("Next automatic check")}</dt><dd>{!source.enabled ? t("Paused") : off ? t("None while this capability is unavailable") : needsAttention ? t("Needs Attention") : automaticCheckAt && automaticCheckAt.getTime() > Date.now() ? automaticCheckAt.toLocaleString() : t("Due for a check")}</dd>
        <dt>{t("Discovered Content since following")}</dt><dd>{source.tracking.update_count}</dd>
        <dt>{t("Waiting for Content acquisition")}</dt><dd>{source.tracking.pending_count}</dd>
        <dt>{t("Videos that could not be imported")}</dt><dd>{source.tracking.unavailable_count ?? 0}</dd>
      </dl>
      {!off && <p className="hint">{t(source.provider === "YOUTUBE" ? "Existing videos are not imported. Successful checks have a 15-minute cooldown." : "Existing videos are not imported. Updates are checked while the app is running, with a 15-minute cooldown.")}</p>}
      {!off && <p className="hint">{t("Updates are checked automatically while the app is running.")}</p>}
      <div className="button-row">
        <button className="button button-primary" disabled={busy || reading || readError || (source.provider !== "YOUTUBE" && !capability.known) || off || !source.enabled || source.tracking.checking || active || coolingDown} onClick={async () => {
          setBusy(true); setMessage(null); setNotice(null); setCheckRun(null);
          try {
            const result = await post<{ source_run?: { run_id: string }; message?: string; status?: string }>(`/sources/${id}/check`, { command_id: crypto.randomUUID() });
            if (!mounted.current) return;
            if (result.status === "CAPABILITY_UNAVAILABLE") setNotice(trackingCopy("CAPABILITY_UNAVAILABLE"));
            else if (result.source_run) { setCheckRun(result.source_run.run_id); setMessage("Checking…"); }
            else setNotice(trackingCopy(result.message ?? "HEALTHY", source.provider));
            setRevision(value => value + 1); onRefresh();
          } catch { if (mounted.current) setMessage("The source could not be checked. Try again later."); }
          finally { if (mounted.current) setBusy(false); }
        }}>{t(busy || active || source.tracking.checking ? "Checking…" : coolingDown ? "Cooling down" : source.provider === "YOUTUBE" && source.tracking.health === "OFFLINE" ? "Retry" : "Check Now")}</button>
        <button className="button button-secondary" disabled={busy || reading || readError} onClick={async () => {
          setBusy(true); setMessage(null); setNotice(null); setCheckRun(null);
          try {
            await patch(`/sources/${id}`, { enabled: !source.enabled });
            if (!mounted.current) return;
            setNotice(source.enabled ? "Monitoring is paused" : off ? trackingCopy("CAPABILITY_UNAVAILABLE") : "Monitoring new videos");
            setRevision(value => value + 1); onRefresh();
          } catch { if (mounted.current) setMessage("The source could not be checked. Try again later."); }
          finally { if (mounted.current) setBusy(false); }
        }}>{t(source.enabled ? "Pause monitoring" : "Resume monitoring")}</button>
      </div>
      <h3>{t("Discovered Content")}</h3>
      {data && data.recent_videos.length ? <ul>{data.recent_videos.map(video => <li key={video.video_id}><a href={`#Content/${video.video_id}`} onClick={onClose}>{video.title ?? video.video_id}</a></li>)}</ul> : <p>{t("No new public videos have been discovered yet.")}</p>}
    </>}
    {!source && !readError && <p role="status">{t("Loading Source…")}</p>}
    {readError && <div className="error" role="alert">
      <p>{t("Source details could not be loaded. Check the local connection and retry. Stored Content is preserved.")}</p>
      <button className="button button-secondary" disabled={reading} onClick={() => setRevision(value => value + 1)}>{t("Retry source details")}</button>
    </div>}
    {message && <p role="status" aria-live="polite">{t(message)}</p>}
  </section></div>;
}

type InterestMode = "INHERIT" | "OVERRIDE";
export type InterestRuleDraft = { id: string; value: string };
// Match Python str.strip's Unicode whitespace without treating a literal BOM
// as whitespace; persisted rules count Unicode codepoints, not UTF-16 units.
const ruleEdgeWhitespace = /^[\p{White_Space}\u001c-\u001f]|[\p{White_Space}\u001c-\u001f]$/u;
export const validInterestRule = (value: unknown): value is string => typeof value === "string"
  && value.length > 0 && Array.from(value).length <= 160 && !ruleEdgeWhitespace.test(value);
export const ruleDrafts = (values: string[]): InterestRuleDraft[] => values.map(value => ({ id: crypto.randomUUID(), value }));
type InterestSnapshot = {
  policy: { source_id: string; source_policy_revision_id: string | null; focus_rules: string[]; ignore_rules: string[]; distillation_style: string };
  policy_modes: { focus: InterestMode; ignore: InterestMode; style: InterestMode };
};
const INTEREST_STYLES = ["BALANCED", "TECHNICAL_DETAIL_FIRST", "PRODUCT_CASE_FIRST", "TREND_OPINION_FIRST"];
function validInterestSnapshot(value: unknown, id: string): value is InterestSnapshot {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<InterestSnapshot> & { source?: { source_id?: string } };
  const p = v.policy, modes = v.policy_modes;
  const rules = (x: unknown) => Array.isArray(x) && x.length <= 20 && x.every(validInterestRule);
  return v.source?.source_id === id && p?.source_id === id
    && (p.source_policy_revision_id === null || (typeof p.source_policy_revision_id === "string" && !!p.source_policy_revision_id.trim() && p.source_policy_revision_id.length <= 512))
    && rules(p.focus_rules) && rules(p.ignore_rules) && INTEREST_STYLES.includes(p.distillation_style)
    && !!modes && [modes.focus, modes.ignore, modes.style].every(m => m === "INHERIT" || m === "OVERRIDE");
}

export const interestRuleValues = (rows: InterestRuleDraft[]) => rows.map(row => row.value).filter(value => value !== "");

export function InterestRulesEditor({ kind, label: customLabel, rows, onChange: change }: { kind: "focus" | "ignore"; label?: string; rows: InterestRuleDraft[]; onChange: (rows: InterestRuleDraft[]) => void }) {
  const { t } = useUiLanguage();
  const [ruleFocus, setRuleFocus] = useState<{ id: string } | null>(null);
  const [addId] = useState(() => `source-interest-add-${crypto.randomUUID()}`);
  useEffect(() => { if (ruleFocus) document.getElementById(ruleFocus.id)?.focus(); }, [ruleFocus]);
  const label = customLabel ?? (kind === "focus" ? "Focus" : "Ignore");
  return <div className="source-interest-rule-editor" role="group" aria-label={t(kind === "focus" ? "Focus rules" : "Ignore rules")}>
    {rows.map((row, index) => <div key={row.id}>
      <label className="field" htmlFor={row.id}>{t(label)}{index > 0 ? ` ${index + 1}` : ""}
        <textarea id={row.id} aria-label={`${t(label)}${index > 0 ? ` ${index + 1}` : ""}`} rows={2} value={row.value}
          onChange={event => { change(rows.map(item => item.id === row.id ? { ...item, value: event.target.value } : item)); }} />
      </label>
      <button type="button" className="button button-secondary" aria-label={`${t(kind === "focus" ? "Remove focus rule" : "Remove ignore rule")} ${index + 1}`} onClick={() => {
        const remaining = rows.filter(item => item.id !== row.id);
        change(remaining); setRuleFocus({ id: remaining[Math.min(index, remaining.length - 1)]?.id ?? addId });
      }}>{t("Remove rule")} {index + 1}</button>
    </div>)}
    <button type="button" id={addId} className="button button-secondary" disabled={rows.length >= 20} onClick={() => {
      const row = ruleDrafts([""])[0]; change([...rows, row]); setRuleFocus({ id: row.id });
    }}>{t(kind === "focus" ? "Add focus rule" : "Add ignore rule")}</button>
  </div>;
}

function SourceInterestEditor({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useUiLanguage();
  const [snapshot, setSnapshot] = useState<InterestSnapshot | null>(null);
  const [focus, setFocus] = useState<InterestRuleDraft[]>([]);
  const [ignore, setIgnore] = useState<InterestRuleDraft[]>([]);
  const [focusMode, setFocusMode] = useState<InterestMode>("INHERIT");
  const [ignoreMode, setIgnoreMode] = useState<InterestMode>("INHERIT");
  const [styleMode, setStyleMode] = useState<InterestMode>("INHERIT");
  const [style, setStyle] = useState("BALANCED");
  const [reading, setReading] = useState(true), [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(false), [message, setMessage] = useState<string | null>(null);
  const [readAttempt, setReadAttempt] = useState(0);
  const edited = useRef(false);
  const initialized = useRef(false), mounted = useRef(true), submitting = useRef(false);
  const command = useRef<{ signature: string; id: string } | null>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let disposed = false;
    setReading(true);
    void api<unknown>(`/sources/${id}`).then(value => {
      if (disposed) return;
      if (!validInterestSnapshot(value, id)) throw new Error("invalid interest read");
      setSnapshot(value); setBlocked(false); setMessage(null);
      if (!initialized.current && !edited.current) {
        setFocus(ruleDrafts(value.policy.focus_rules)); setIgnore(ruleDrafts(value.policy.ignore_rules));
        setFocusMode(value.policy_modes.focus); setIgnoreMode(value.policy_modes.ignore); setStyleMode(value.policy_modes.style);
        setStyle(value.policy.distillation_style);
      }
      initialized.current = true;
    }).catch(() => { if (!disposed) { setBlocked(true); setMessage("Interests could not be read. Retry before saving. Your draft is preserved."); } })
      .finally(() => { if (!disposed) setReading(false); });
    return () => { disposed = true; };
  }, [id, readAttempt]);
  const mode = (label: string, value: InterestMode, change: (m: InterestMode) => void) => <label className="field">{t(label)}<select aria-label={t(label)} value={value} onChange={e => { edited.current = true; change(e.target.value as InterestMode); }}><option value="INHERIT">{t("Use global interests")}</option><option value="OVERRIDE">{t("Set for this Following")}</option></select></label>;
  const savedRules = (label: string, values: string[]) => <div>
    <p className="hint">{t(label)}</p>
    {values.length ? <ul className="source-interest-saved-rules">{values.map((value, index) => <li key={index}>{value}</li>)}</ul> : <p className="hint">{t("Not set")}</p>}
  </div>;
  return <form className="source-interest-editor" aria-label={t("Following interests")} onKeyDown={e => { if (e.key === "Escape" && !busy) { e.stopPropagation(); onClose(); } }} onSubmit={async e => {
    e.preventDefault();
    if (!snapshot || reading || blocked || submitting.current) return;
    const request = { expected_source_policy_revision_id: snapshot.policy.source_policy_revision_id,
      focus_mode: focusMode, focus_rules: focusMode === "INHERIT" ? [] : interestRuleValues(focus),
      ignore_mode: ignoreMode, ignore_rules: ignoreMode === "INHERIT" ? [] : interestRuleValues(ignore),
      distillation_style_mode: styleMode, distillation_style: styleMode === "INHERIT" ? null : style };
    if (![...request.focus_rules, ...request.ignore_rules].every(validInterestRule)) {
      setMessage("Each rule needs text without leading or trailing whitespace, up to 160 characters."); return;
    }
    const signature = JSON.stringify(request);
    if (command.current?.signature !== signature) command.current = { signature, id: crypto.randomUUID() };
    submitting.current = true; setBusy(true); setMessage(null);
    try {
      const result = await put<{ applied_source_policy_revision_id?: string; current_source_policy_revision_id?: string; historical_replay?: boolean }>(`/sources/${id}/interests`, { command_id: command.current.id, ...request });
      if (!mounted.current) return;
      if (!result.applied_source_policy_revision_id || !result.current_source_policy_revision_id || typeof result.historical_replay !== "boolean") throw new Error("invalid interest result");
      if (result.historical_replay || result.applied_source_policy_revision_id !== result.current_source_policy_revision_id) {
        setBlocked(true); setMessage("This command was already applied, and newer interests exist. Your draft is preserved. Reload the current version.");
      } else {
        setSnapshot({ ...snapshot, policy: { ...snapshot.policy, source_policy_revision_id: result.current_source_policy_revision_id } });
        setMessage("Interests saved.");
      }
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof ApiRequestError && error.code === "CONFLICT") {
        setBlocked(true); setMessage("Interests changed elsewhere. Your draft is preserved. Reload the current version before saving again.");
      } else setMessage("Interests could not be saved. Your draft is preserved. Retry or reload the current version.");
    } finally { submitting.current = false; if (mounted.current) setBusy(false); }
  }}>
    <h3>{t("Following interests")}</h3>
    <p className="hint">{t("Changes affect future checks and insights only. Processing and monitoring settings stay the same.")}</p>
    {reading && <p role="status">{t("Loading interests…")}</p>}
    <p className="hint">{t("Each row is one rule. Commas and line breaks stay in that rule. Blank rows are omitted.")}</p>
    <fieldset disabled={busy || reading}>
      {mode("Focus preference", focusMode, value => { setFocusMode(value); if (value === "OVERRIDE" && !focus.length) setFocus(ruleDrafts([""])); })}
      {focusMode === "OVERRIDE" ? <InterestRulesEditor kind="focus" rows={focus} onChange={rows => { edited.current = true; setFocus(rows); }} /> : snapshot && savedRules(snapshot.policy_modes.focus === "INHERIT" ? "Global focus" : "Current saved focus", snapshot.policy.focus_rules)}
      {mode("Ignore preference", ignoreMode, value => { setIgnoreMode(value); if (value === "OVERRIDE" && !ignore.length) setIgnore(ruleDrafts([""])); })}
      {ignoreMode === "OVERRIDE" ? <InterestRulesEditor kind="ignore" rows={ignore} onChange={rows => { edited.current = true; setIgnore(rows); }} /> : snapshot && savedRules(snapshot.policy_modes.ignore === "INHERIT" ? "Global ignore" : "Current saved ignore", snapshot.policy.ignore_rules)}
      {mode("Style preference", styleMode, setStyleMode)}
      {styleMode === "OVERRIDE" && <label className="field">{t("Distillation style")}<select aria-label={t("Distillation style")} value={style} onChange={e => { edited.current = true; setStyle(e.target.value); }}>{INTEREST_STYLES.map(v => <option key={v} value={v}>{t(({ BALANCED:"Balanced", TECHNICAL_DETAIL_FIRST:"Technical", PRODUCT_CASE_FIRST:"Product case", TREND_OPINION_FIRST:"Trend and opinion" })[v] ?? v)}</option>)}</select></label>}
      <p className="hint">{t("An empty override means no words for this Following; inheritance follows global interests.")}</p>
      <div className="button-row"><button className="button button-primary" disabled={!snapshot || blocked || reading || busy}>{t(busy ? "Saving…" : "Save interests")}</button><button type="button" className="button button-secondary" onClick={onClose}>{t("Cancel interest editing")}</button></div>
    </fieldset>
    {message && <p role={blocked ? "alert" : "status"}>{t(message)}</p>}
    <button type="button" className="button button-secondary" disabled={busy || reading} onClick={() => setReadAttempt(v => v + 1)}>{t("Reload current interests")}</button>
  </form>;
}
