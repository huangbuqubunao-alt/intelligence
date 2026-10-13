import { useEffect, useRef, useState } from "react";
import { ApiRequestError, api, patch, post } from "../api/client";
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

const ACTIVE_STATES = ["QUEUED", "RUNNING", "WAITING", "PARTIAL"];
const isActive = (data: Detail | null) =>
  data?.source_runs.some(run => ACTIVE_STATES.includes(run.state)) ?? false;

type DetailProps = {
  id: string; capability: CreatorFollowingCapabilityState; onClose: () => void; onRefresh: () => void;
};

export function CreatorFollowingDetail(props: DetailProps) {
  // A different source starts with its own identity, commands and read state.
  return <CreatorFollowingDetailContent key={props.id} {...props} />;
}

function CreatorFollowingDetailContent({ id, capability, onClose, onRefresh }: DetailProps) {
  const { t } = useUiLanguage();
  const [data, setData] = useState<Detail | null>(null);
  const [revision, setRevision] = useState(0);
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
      if (value?.source?.source_id !== id || !value.source.tracking
          || (value.source.provider !== undefined && !["YOUTUBE", "BILIBILI"].includes(value.source.provider))
          || !Array.isArray(value.source_runs) || !Array.isArray(value.recent_videos)) {
        throw new Error("Source detail response identity is unavailable");
      }
      setData(value); setReadError(false);
    }).catch(() => { if (!disposed) setReadError(true); })
      .finally(() => { if (!disposed) setReading(false); });
    return () => { disposed = true; };
  }, [id, revision]);
  useEffect(() => {
    if (!isActive(data) && !checkRun) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data, checkRun]);
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
