import { useEffect, useState } from "react";
import { ApiRequestError, api, patch, post } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

export type Tracking = {
  health: string; coverage: string; verified_at?: string | null;
  baseline_at?: string | null; next_check_at?: string;
  update_count: number; pending_count: number; unavailable_count?: number;
  checking?: boolean; processing_count?: number;
};
export const trackingCopy = (health: string) => ({
  HEALTHY: "Source checks are working",
  BASELINE_PENDING: "Waiting to establish the starting point",
  OFFLINE: "Unable to connect. Your last successful check is preserved.",
  RATE_LIMITED: "Public source requests are limited. Try again later.",
  RISK_CONTROLLED: "Bilibili has temporarily restricted public requests. Try again later.",
  ACCESS_DENIED: "This source is not publicly accessible. No login is used.",
  NOT_FOUND: "This public source is unavailable. Stored Content is preserved.",
  PROVIDER_ERROR: "The source could not be checked. Try again later.",
  STATE_INVALID: "Tracking data failed verification. Existing Content is preserved.",
  CHECK_INCOMPLETE: "Some updates may still be missing. Later checks will continue.",
  UPDATE_GAP: "Some updates may still be missing. Later checks will continue.",
  COOLDOWN: "Checked recently. Please wait before checking again.",
  BUSY: "A source check is already running.",
  PAUSED: "Monitoring is paused",
}[health] ?? "The source could not be checked. Try again later.");

export function CreatorFollowForm({ onSaved, provider = "BILIBILI" }: { onSaved: () => void; provider?: "YOUTUBE" | "BILIBILI" }) {
  const youtube = provider === "YOUTUBE";
  const { t } = useUiLanguage();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  return <>
    <p>{t("Follow from now on. Newly published public videos enter Content automatically while the app is running. Existing videos are not imported.")}</p>
    {!saved && <form onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setMessage(null);
      try {
        await post(youtube ? "/sources/channels" : "/sources/creators", { input: input.trim() });
        setSaved(true);
      } catch (error) {
        const code = error instanceof ApiRequestError ? error.code.replace(/^(BILIBILI|YOUTUBE)_/, "") : "OFFLINE";
        setMessage(code === "INVALID_INPUT" ? (youtube ? "Enter an HTTPS YouTube channel URL, @handle or channel id." : "Enter an HTTPS Bilibili creator profile URL or numeric creator id.") : trackingCopy(code));
      } finally { setBusy(false); }
    }}>
      <label className="field">{t(youtube ? "Channel URL, @handle or channel id" : "Creator profile URL or numeric id")}<input autoFocus maxLength={2048} value={input} disabled={busy} onChange={event => setInput(event.target.value)} placeholder={youtube ? "https://www.youtube.com/@channel" : "https://space.bilibili.com/123"} /></label>
      <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? "Establishing tracking…" : youtube ? "Follow channel" : "Follow creator")}</button>
    </form>}
    {busy && <p role="status">{t("Establishing tracking…")}</p>}
    {message && <p role="alert">{t(message)}</p>}
    {saved && <div role="status"><p>{t(youtube ? "Channel followed. Check Following for its starting point and source health." : "Creator followed. Check the Following detail for its starting point and source health.")}</p><button className="button button-primary" onClick={onSaved}>{t("Done")}</button></div>}
  </>;
}

export function FollowCreatorFromContent({ id, provider = "BILIBILI" }: { id: string; provider?: "YOUTUBE" | "BILIBILI" }) {
  const youtube = provider === "YOUTUBE";
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  return <div className="button-row">
    <button className="button button-secondary" disabled={busy} onClick={async () => {
      if (busy) return; setBusy(true);
      try { await post(`/videos/${id}/follow-${youtube ? "channel" : "creator"}`, {}); setMessage(youtube ? "Channel followed. Check Following for its starting point and source health." : "Creator followed. Check the Following detail for its starting point and source health."); }
      catch { setMessage("The source could not be checked. Try again later."); }
      finally { setBusy(false); }
    }}>{t(busy ? "Establishing tracking…" : youtube ? "Follow this channel" : "Follow this creator")}</button>
    {message && <p role="status">{t(message)}</p>}
  </div>;
}

type Detail = {
  source: { provider?: string; source_id: string; display_name: string | null; canonical_url: string; enabled: boolean;
    last_checked_at: string | null; last_success_at: string | null; tracking: Tracking };
  recent_videos: { video_id: string; title: string | null; processing_status: string }[];
  source_runs: { state: string }[];
};

export function CreatorFollowingDetail({ id, onClose, onRefresh }: { id: string; onClose: () => void; onRefresh: () => void }) {
  const { t } = useUiLanguage();
  const [data, setData] = useState<Detail | null>(null);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    let disposed = false;
    void api<Detail>(`/sources/${id}`).then(value => { if (!disposed) setData(value); }).catch(() => { if (!disposed) setMessage("The source could not be checked. Try again later."); });
    return () => { disposed = true; };
  }, [id, revision]);
  useEffect(() => {
    if (!data?.source_runs.some(run => ["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(run.state))) return;
    const timer = setTimeout(() => setRevision(value => value + 1), 2000);
    return () => clearTimeout(timer);
  }, [data]);
  useEffect(() => {
    if (data && !data.source_runs.some(run => ["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(run.state))) {
      setMessage(current => current === "Checking…" ? null : current);
    }
  }, [data]);
  const source = data?.source;
  const active = data?.source_runs.some(run => ["QUEUED", "RUNNING", "WAITING", "PARTIAL"].includes(run.state)) ?? false;
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-label={t(source?.provider === "YOUTUBE" ? "Channel Following" : "Creator Following")}>
    <div className="modal-head"><h2>{source?.display_name ?? t(source?.provider === "YOUTUBE" ? "Channel Following" : "Creator Following")}</h2><button className="button button-ghost" onClick={onClose}>{t("Close")}</button></div>
    {source && <>
      <p>{t(source.provider === "YOUTUBE" ? "YouTube" : "Bilibili")} · {t(source.enabled ? "Monitoring new videos" : "Monitoring is paused")}</p>
      <a href={source.canonical_url} target="_blank" rel="noreferrer">{t("Open Source")}</a>
      <dl className="creator-tracking">
        <dt>{t("Last checked")}</dt><dd>{source.last_checked_at ? new Date(source.last_checked_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Last successful check")}</dt><dd>{source.last_success_at ? new Date(source.last_success_at).toLocaleString() : t("Not checked yet")}</dd>
        <dt>{t("Source health")}</dt><dd>{t(trackingCopy(source.tracking.health))}</dd>
        <dt>{t("Discovered Content since following")}</dt><dd>{source.tracking.update_count}</dd>
        <dt>{t("Waiting for Content acquisition")}</dt><dd>{source.tracking.pending_count}</dd>
        <dt>{t("Videos that could not be imported")}</dt><dd>{source.tracking.unavailable_count ?? 0}</dd>
      </dl>
      <p className="hint">{t("Existing videos are not imported. Updates are checked while the app is running, with a 15-minute cooldown.")}</p>
      <div className="button-row">
        <button className="button button-primary" disabled={busy || !source.enabled || source.tracking.checking || active} onClick={async () => {
          setBusy(true); setMessage(null);
          try {
            const result = await post<{ source_run?: unknown; message?: string }>(`/sources/${id}/check`, { command_id: crypto.randomUUID() });
            setMessage(result.source_run ? "Checking…" : trackingCopy(result.message ?? "HEALTHY"));
            setRevision(value => value + 1); onRefresh();
          } catch { setMessage("The source could not be checked. Try again later."); }
          finally { setBusy(false); }
        }}>{t(busy ? "Checking…" : "Check Now")}</button>
        <button className="button button-secondary" disabled={busy} onClick={async () => {
          setBusy(true);
          try { await patch(`/sources/${id}`, { enabled: !source.enabled }); setRevision(value => value + 1); onRefresh(); }
          catch { setMessage("The source could not be checked. Try again later."); }
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
