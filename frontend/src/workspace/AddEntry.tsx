import { useState } from "react";
import { ApiRequestError, post } from "../api/client";
import { LocalImport } from "./LocalImport";
import { bilibiliStatus } from "./BilibiliImport";
import { trackingCopy } from "./CreatorFollowing";
import { useUiLanguage } from "./uiLanguage";

export type RecognizedLink = { kind: "YOUTUBE_CHANNEL" | "YOUTUBE_VIDEO" | "BILIBILI_VIDEO"; canonical: string };
const videoId = /^[A-Za-z0-9_-]{11}$/;
const channelId = /^UC[A-Za-z0-9_-]{22}$/;
const handle = /^@[A-Za-z0-9._-]{3,100}$/;
const bv = /^BV[1-9A-HJ-NP-Za-km-z]{10}$/;
const channelTabs = new Set(["videos", "shorts", "streams", "playlists", "about", "featured"]);
export const invalidLinkCopy = "Paste a supported HTTPS YouTube video or channel link, @handle, channel ID, or Bilibili BV video link. To add a file, choose Import local file.";

/** Recognition is local and deterministic. Provider boundaries validate again. */
export function recognizeLink(value: string): RecognizedLink | null {
  const raw = value.trim();
  if (!raw || raw.length > 2048 || /[\p{Cc}\p{Cf}\p{Cs}]/u.test(raw)) return null;
  if (handle.test(raw) || channelId.test(raw)) return { kind: "YOUTUBE_CHANNEL", canonical: `https://www.youtube.com/${raw.startsWith("@") ? raw : `channel/${raw}`}` };
  if (bv.test(raw)) return { kind: "BILIBILI_VIDEO", canonical: `https://www.bilibili.com/video/${raw}/` };
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || url.username || url.password || url.port) return null;
    const parts = url.pathname.replace(/\/$/, "").split("/").slice(1);
    if (["youtube.com", "www.youtube.com", "m.youtube.com"].includes(url.hostname)) {
      if (parts.at(-1) && channelTabs.has(parts.at(-1)!)) parts.pop();
      if (!url.search && !url.hash && ((parts.length === 1 && handle.test(parts[0])) || (parts.length === 2 && parts[0] === "channel" && channelId.test(parts[1])))) {
        return { kind: "YOUTUBE_CHANNEL", canonical: `https://www.youtube.com/${parts.join("/")}` };
      }
      const id = url.pathname === "/watch" && url.searchParams.getAll("v").length === 1 ? url.searchParams.get("v") : parts.length === 2 && ["shorts", "live"].includes(parts[0]) ? parts[1] : null;
      if (id && videoId.test(id)) return { kind: "YOUTUBE_VIDEO", canonical: `https://www.youtube.com/watch?v=${id}` };
    }
    if (url.hostname === "youtu.be" && parts.length === 1 && videoId.test(parts[0])) return { kind: "YOUTUBE_VIDEO", canonical: `https://www.youtube.com/watch?v=${parts[0]}` };
    if (["bilibili.com", "www.bilibili.com", "m.bilibili.com"].includes(url.hostname) && parts.length === 2 && parts[0] === "video" && bv.test(parts[1]) && (!url.searchParams.has("p") || url.searchParams.getAll("p").join() === "1")) return { kind: "BILIBILI_VIDEO", canonical: `https://www.bilibili.com/video/${parts[1]}/` };
  } catch { /* Invalid URLs have an actionable explanation below. */ }
  return null;
}

const confirmation: Record<RecognizedLink["kind"], string> = {
  YOUTUBE_CHANNEL: "YouTube channel — keep following future content. Existing videos are not imported.",
  YOUTUBE_VIDEO: "YouTube video — process this video only. Its channel will not be followed.",
  BILIBILI_VIDEO: "Bilibili video — import this public video only. Its creator will not be followed.",
};
export function AddEntry({ onClose, onSaved, initialLocal = false }: { onClose: () => void; onSaved: () => void; initialLocal?: boolean }) {
  const { t } = useUiLanguage();
  const [local, setLocal] = useState(initialLocal);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("ORGANIZE_CONTENT");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ kind: RecognizedLink["kind"]; content_id?: string; status?: string } | null>(null);
  const recognized = recognizeLink(input);
  if (local) return <LocalImport onClose={onClose} onSaved={onSaved} onYouTube={() => setLocal(false)} />;
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="add-entry-title">
    <div className="modal-head"><h2 id="add-entry-title">{t("Add a Source")}</h2><button className="button button-ghost" aria-label={t("Close")} disabled={busy} onClick={result ? onSaved : onClose}>{t(result ? "Done" : "Close")}</button></div>
    {!result && <>
      <p>{t("Paste a YouTube or Bilibili link. We will recognize it before you add it.")}</p>
      <form onSubmit={async event => {
        event.preventDefault(); if (busy) return;
        if (!recognized) { setError(invalidLinkCopy); return; }
        setBusy(true); setError(null);
        try {
          if (recognized.kind === "YOUTUBE_CHANNEL") {
            await post("/sources/channels", { input: recognized.canonical, processing_mode: mode });
            setResult({ kind: recognized.kind });
          } else if (recognized.kind === "BILIBILI_VIDEO") {
            const response = await post<{ import: { content_id: string; processing_status: string } }>("/bilibili/imports", { input: recognized.canonical });
            setResult({ kind: recognized.kind, content_id: response.import.content_id, status: response.import.processing_status });
          } else {
            const response = await post<{ source: { video_id: string } }>("/sources/import", { url: recognized.canonical, command_id: crypto.randomUUID() });
            setResult({ kind: recognized.kind, content_id: response.source.video_id });
          }
        } catch (reason) {
          const code = reason instanceof ApiRequestError ? reason.code : "NETWORK_UNAVAILABLE";
          setError(code.includes("INVALID") || code.includes("UNSUPPORTED") ? invalidLinkCopy : recognized.kind === "BILIBILI_VIDEO" ? bilibiliStatus(code) : trackingCopy(code.replace(/^YOUTUBE_/, ""), "YOUTUBE"));
        } finally { setBusy(false); }
      }}>
        <label className="field">{t("Paste link")}<input autoFocus aria-label={t("Paste link")} value={input} maxLength={2048} disabled={busy} onChange={event => { setInput(event.target.value); setError(null); }} placeholder="https://www.youtube.com/@channel/videos" /></label>
        {recognized && <p className="semantic-state state-neutral" role="status">{t(confirmation[recognized.kind])}</p>}
        {recognized?.kind === "YOUTUBE_CHANNEL" && <fieldset disabled={busy} className="processing-modes"><legend>{t("When new content is found")}</legend>
          <label><input type="radio" name="processing-mode" checked={mode === "ORGANIZE_CONTENT"} onChange={() => setMode("ORGANIZE_CONTENT")} /> {t("Organize content")}<small>{t("Automatically save new content with readable summaries and verifiable source references.")}</small></label>
          <label><input type="radio" name="processing-mode" checked={mode === "EXTRACT_INTELLIGENCE"} onChange={() => setMode("EXTRACT_INTELLIGENCE")} /> {t("Also extract Intelligence")}<small>{t("After organizing content, consider which information deserves lasting knowledge. A qualified model and any required consent are needed.")}</small></label>
        </fieldset>}
        {error && <p className="form-error" role="alert">{t(error)}</p>}
        <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? recognized?.kind === "YOUTUBE_CHANNEL" ? "Establishing tracking…" : "Starting import…" : recognized?.kind === "YOUTUBE_CHANNEL" ? "Follow channel" : "Confirm import")}</button>
      </form>
      <button className="button button-secondary" disabled={busy} onClick={() => setLocal(true)}>{t("Import local file")}</button>
      <p className="hint">{t("YouTube · Local files · Bilibili public-video import")}</p>
    </>}
    {busy && <p role="status" aria-live="polite">{t(recognized?.kind === "YOUTUBE_CHANNEL" ? "Establishing tracking…" : "Starting import…")}</p>}
    {result && <div role="status" aria-live="polite"><p>{t(result.kind === "YOUTUBE_CHANNEL" ? "Channel followed. Check Following for its starting point and source health." : "Import accepted. Processing and any required attention appear in Content.")}</p>
      {result.status && <p>{t(bilibiliStatus(result.status))}</p>}
      {result.content_id && <a href={`#Content/${result.content_id}`} onClick={onSaved}>{t("Open Content")}</a>}
      <button className="button button-primary" onClick={onSaved}>{t("Done")}</button>
    </div>}
  </section></div>;
}
