import { useEffect, useState } from "react";
import { ApiRequestError, api, patch, post } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

export type Tracking = {
  health: string; coverage: string; verified_at?: string | null;
  baseline_at?: string | null; next_check_at?: string;
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
export function useCreatorFollowingCapability(): CreatorFollowingCapabilityState {
  const [state, setState] = useState<CreatorFollowingCapabilityState>({ known: false });
  useEffect(() => {
    let disposed = false;
    void api<{ bilibili?: { creator_following?: CreatorFollowingCapability } }>("/settings")
      .then(value => { if (!disposed) setState({ known: true, capability: value.bilibili?.creator_following ?? null }); })
      .catch(() => { if (!disposed) setState({ known: true, capability: null }); });
    return () => { disposed = true; };
  }, []);
  return state;
}

const withdrawn = (state: CreatorFollowingCapabilityState) =>
  state.known && state.capability !== null && !state.capability.available;

/**
 * Health is a fact about stored data, so every value must resolve to a sentence
 * the user can act on. An unknown value is reported as unknown rather than
 * smoothed into a reassuring phrase.
 */
export const trackingCopy = (health: string) => ({
  HEALTHY: "Source checks are working",
  BASELINE_PENDING: "Waiting to establish the starting point",
  OFFLINE: "Unable to connect. Your last successful check is preserved.",
  RATE_LIMITED: "Bilibili requests are limited. Try again later.",
  RISK_CONTROLLED: "Bilibili has temporarily restricted public requests. Your stored Content is preserved.",
  ACCESS_DENIED: "This creator is not publicly accessible. No login is used.",
  NOT_FOUND: "This public creator is unavailable. Stored Content is preserved.",
  VIDEO_UNAVAILABLE: "One or more of this creator's videos are no longer public. Everything already stored is preserved.",
  PROVIDER_ERROR: "The creator could not be checked. Try again later.",
  STATE_INVALID: "Tracking data failed verification. Existing Content is preserved.",
  CHECK_INCOMPLETE: "Some updates may still be missing. Later checks will continue.",
  UPDATE_GAP: "Some updates may still be missing. Later checks will continue.",
  COOLDOWN: "Checked recently. Please wait before checking again.",
  BUSY: "A source check is already running.",
  PAUSED: "Monitoring is paused",
  CAPABILITY_UNAVAILABLE: "Continuous creator tracking is currently unavailable. Stored Content is preserved.",
}[health] ?? "The creator could not be checked. Try again later.");

function UnavailableNotice({ state, creator }: { state: CreatorFollowingCapabilityState; creator: boolean }) {
  const { t } = useUiLanguage();
  if (!withdrawn(state)) return null;
  return <div role="status" className="hint">
    <strong>{t("Continuous creator tracking is currently unavailable")}</strong>
    <p>{t((state.known ? state.capability?.message : null) || "Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.")}</p>
    {creator && <p>{t("Sources already followed, their stored Content and all Evidence are preserved. No new creator can be followed until this returns.")}</p>}
  </div>;
}

export function CreatorFollowForm({ capability, onSaved }: {
  capability: CreatorFollowingCapabilityState; onSaved: () => void;
}) {
  const { t } = useUiLanguage();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  if (!capability.known) return <p role="status">{t("Checking whether this is available…")}</p>;
  if (withdrawn(capability)) return <UnavailableNotice state={capability} creator={false} />;
  return <>
    <p>{t("Follow from now on. Newly published public videos enter Content automatically while the app is running. Existing videos are not imported.")}</p>
    {!saved && <form onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setMessage(null);
      try {
        await post("/sources/creators", { input: input.trim() });
        setSaved(true);
      } catch (error) {
        const code = error instanceof ApiRequestError ? error.code.replace(/^BILIBILI_/, "") : "OFFLINE";
        setMessage(code === "INVALID_INPUT" ? "Enter an HTTPS Bilibili creator profile URL or numeric creator id." : trackingCopy(code));
      } finally { setBusy(false); }
    }}>
      <label className="field">{t("Creator profile URL or numeric id")}<input autoFocus maxLength={2048} value={input} disabled={busy} onChange={event => setInput(event.target.value)} placeholder="https://space.bilibili.com/123" /></label>
      <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? "Establishing tracking…" : "Follow creator")}</button>
    </form>}
    {busy && <p role="status">{t("Establishing tracking…")}</p>}
    {message && <p role="alert">{t(message)}</p>}
    {saved && <div role="status"><p>{t("Creator followed. Check the Following detail for its starting point and source health.")}</p><button className="button button-primary" onClick={onSaved}>{t("Done")}</button></div>}
  </>;
}

export function FollowCreatorFromContent({ id, capability }: {
  id: string; capability: CreatorFollowingCapabilityState;
}) {
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (withdrawn(capability)) return <div className="button-row">
    <button className="button button-secondary" disabled>{t("Continuous creator tracking is currently unavailable")}</button>
  </div>;
  return <div className="button-row">
    <button className="button button-secondary" disabled={busy} onClick={async () => {
      if (busy) return; setBusy(true);
      try { await post(`/videos/${id}/follow-creator`, {}); setMessage("Creator followed. Check the Following detail for its starting point and source health."); }
      catch (error) {
        const code = error instanceof ApiRequestError ? error.code.replace(/^BILIBILI_/, "") : "PROVIDER_ERROR";
        setMessage(trackingCopy(code));
      }
      finally { setBusy(false); }
    }}>{t(busy ? "Establishing tracking…" : "Follow this creator")}</button>
    {message && <p role="status">{t(message)}</p>}
  </div>;
}

type Detail = {
  source: { source_id: string; display_name: string | null; canonical_url: string; enabled: boolean;
    last_checked_at: string | null; last_success_at: string | null; last_error_code?: string | null;
    tracking: Tracking };
  recent_videos: { video_id: string; title: string | null; processing_status: string }[];
  source_runs: { state: string }[];
};

const ACTIVE_STATES = ["QUEUED", "RUNNING", "WAITING", "PARTIAL"];
const isActive = (data: Detail | null) =>
  data?.source_runs.some(run => ACTIVE_STATES.includes(run.state)) ?? false;

export function CreatorFollowingDetail({ id, capability, onClose, onRefresh }: {
  id: string; capability: CreatorFollowingCapabilityState; onClose: () => void; onRefresh: () => void;
}) {
  const { t } = useUiLanguage();
  const [data, setData] = useState<Detail | null>(null);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useEffect(() => {
    let disposed = false;
    void api<Detail>(`/sources/${id}`).then(value => { if (!disposed) setData(value); }).catch(() => { if (!disposed) setMessage("The creator could not be checked. Try again later."); });
    return () => { disposed = true; };
  }, [id, revision]);
  useEffect(() => {
    if (!isActive(data)) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data]);
  // Polling replaces this component's data, so the outcome of the last command is
  // held separately: the user is told what happened and a refetch cannot erase it.
  useEffect(() => {
    if (data && !isActive(data) && notice) setMessage(notice);
  }, [data, notice]);
  const source = data?.source;
  const active = isActive(data);
  const off = withdrawn(capability);
  const baselineEstablished = Boolean(source?.tracking.baseline_at ?? source?.tracking.verified_at);
  const cooldownUntil = source?.tracking.next_check_at ? new Date(source.tracking.next_check_at) : null;
  const coolingDown = cooldownUntil !== null && cooldownUntil.getTime() - Date.now() > 0;
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t("Creator Following")}>
    <div className="modal-head"><h2>{source?.display_name ?? t("Creator Following")}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    {off && <UnavailableNotice state={capability} creator />}
    {source && <>
      <p>{t("Bilibili")} · {off ? t("Continuous creator tracking is currently unavailable") : source.enabled ? t("Monitoring new videos") : t("Monitoring is paused")}</p>
      <a href={source.canonical_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
      <dl className="creator-tracking">
        <dt>{t("Source health")}</dt><dd>{t(trackingCopy(source.tracking.health))}</dd>
        <dt>{t("Starting point established")}</dt><dd>{baselineEstablished ? t("Yes") : t("No, no successful check has completed yet")}</dd>
        <dt>{t("Last checked")}</dt><dd>{source.last_checked_at ? new Date(source.last_checked_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Last successful check")}</dt><dd>{source.last_success_at ? new Date(source.last_success_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Next automatic check")}</dt><dd>{!source.enabled ? t("Paused") : off ? t("None while this capability is unavailable") : coolingDown ? cooldownUntil.toLocaleString() : t("Not scheduled")}</dd>
        <dt>{t("Discovered Content since following")}</dt><dd>{source.tracking.update_count}</dd>
        <dt>{t("Waiting for Content acquisition")}</dt><dd>{source.tracking.pending_count}</dd>
        <dt>{t("Videos that could not be imported")}</dt><dd>{source.tracking.unavailable_count ?? 0}</dd>
      </dl>
      {!off && <p className="hint">{t("Existing videos are not imported. Updates are checked while the app is running, with a 15-minute cooldown.")}</p>}
      <div className="button-row">
        <button className="button button-primary" disabled={busy || !capability.known || off || !source.enabled || source.tracking.checking || active || coolingDown} onClick={async () => {
          setBusy(true); setMessage(null); setNotice(null);
          try {
            const result = await post<{ source_run?: unknown; message?: string; status?: string }>(`/sources/${id}/check`, { command_id: crypto.randomUUID() });
            if (result.status === "CAPABILITY_UNAVAILABLE") setNotice(trackingCopy("CAPABILITY_UNAVAILABLE"));
            else if (result.source_run) setNotice("Checking…");
            else setNotice(trackingCopy(result.message ?? "HEALTHY"));
            setRevision(value => value + 1); onRefresh();
          } catch { setMessage("The creator could not be checked. Try again later."); }
          finally { setBusy(false); }
        }}>{t(coolingDown ? "Cooling down" : busy ? "Checking…" : "Check Now")}</button>
        <button className="button button-secondary" disabled={busy} onClick={async () => {
          setBusy(true); setMessage(null); setNotice(null);
          try {
            await patch(`/sources/${id}`, { enabled: !source.enabled });
            setNotice(source.enabled ? "Monitoring is paused" : "Source checks are working");
            setRevision(value => value + 1); onRefresh();
          } catch { setMessage("The creator could not be checked. Try again later."); }
          finally { setBusy(false); }
        }}>{t(source.enabled ? "Pause monitoring" : "Resume monitoring")}</button>
      </div>
      <h3>{t("Discovered Content")}</h3>
      {data && data.recent_videos.length ? <ul>{data.recent_videos.map(video => <li key={video.video_id}><a href={`#Content/${video.video_id}`} onClick={onClose}>{video.title ?? video.video_id}</a></li>)}</ul> : <p>{t("No new public videos have been discovered yet.")}</p>}
    </>}
    {!source && !message && <p role="status">{t("Loading Source…")}</p>}
    {message && <p role="status" aria-live="polite">{t(message)}</p>}
  </section></div>;
}