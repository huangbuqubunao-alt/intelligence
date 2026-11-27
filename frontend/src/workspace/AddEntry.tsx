import { useEffect, useState } from "react";
import { ApiRequestError, post } from "../api/client";
import { LocalImport } from "./LocalImport";
import { QuickPasteNoteForm } from "./QuickPasteNoteForm";
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

export type BatchParsedLink = {
  raw: string;
  recognized: RecognizedLink | null;
};

export type BatchParseSummary = {
  items: BatchParsedLink[];
  validItems: Array<{ raw: string; recognized: RecognizedLink }>;
  invalidCount: number;
  duplicateCount: number;
  truncatedCount: number;
};

const MAX_BATCH_LINKS = 10;

export function parseBatchLinks(raw: string, maxItems: number = MAX_BATCH_LINKS): BatchParseSummary {
  const tokens = raw
    .split(/[\r\n\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  const items: BatchParsedLink[] = [];
  const validItems: Array<{ raw: string; recognized: RecognizedLink }> = [];
  const seenCanonical = new Set<string>();
  const seenInvalid = new Set<string>();
  let invalidCount = 0;
  let duplicateCount = 0;
  let truncatedCount = 0;

  for (const token of tokens) {
    const cleaned = token.replace(/[,.;:!，。；：！？>\]"']+$/, "");
    const rec = recognizeLink(token) ?? (cleaned !== token ? recognizeLink(cleaned) : null);
    if (!rec) {
      if (seenInvalid.has(token)) {
        duplicateCount += 1;
        continue;
      }
      seenInvalid.add(token);
      invalidCount += 1;
      items.push({ raw: token, recognized: null });
      continue;
    }
    if (seenCanonical.has(rec.canonical)) {
      duplicateCount += 1;
      continue;
    }
    seenCanonical.add(rec.canonical);
    if (validItems.length >= maxItems) {
      truncatedCount += 1;
      continue;
    }
    const entry = { raw: token, recognized: rec };
    validItems.push(entry);
    items.push(entry);
  }

  return {
    items,
    validItems,
    invalidCount,
    duplicateCount,
    truncatedCount,
  };
}

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

function linkHint(value: string, zh: boolean): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^http:\/\//i.test(trimmed)) {
    return zh
      ? "请使用 https:// 开头（出于安全限制不支持明文 http://）。"
      : "Use https:// at the start (plaintext http:// is not supported).";
  }
  if (/^(www\.)?(youtube\.com|youtu\.be|bilibili\.com|m\.bilibili\.com)\b/i.test(trimmed)) {
    return zh
      ? "请补全 https:// 开头，例如 https://www.youtube.com/watch?v=..."
      : "Include https:// at the start, e.g. https://www.youtube.com/watch?v=...";
  }
  return zh
    ? "支持 https:// YouTube 视频或频道、@用户名，或 B 站 BV 号。"
    : "Supports https:// YouTube video/channel links, @handle, or Bilibili BV ID.";
}

const confirmation: Record<RecognizedLink["kind"], string> = {
  YOUTUBE_CHANNEL: "YouTube channel — keep following future content. Existing videos are not imported.",
  YOUTUBE_VIDEO: "YouTube video — process this video only. Its channel will not be followed.",
  BILIBILI_VIDEO: "Bilibili video — import this public video only. Its creator will not be followed.",
};
export function AddEntry({
  onClose,
  onSaved,
  onImported,
  initialLocal = false,
  initialMode,
}: {
  onClose: () => void;
  onSaved: () => void;
  onImported?: (contentId: string, sourceKind?: "LOCAL" | "YOUTUBE_VIDEO" | "BILIBILI_VIDEO") => void;
  initialLocal?: boolean;
  initialMode?: "YOUTUBE" | "LOCAL" | "PASTE";
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [entryMode, setEntryMode] = useState<"YOUTUBE" | "LOCAL" | "PASTE">(
    initialMode ?? (initialLocal ? "LOCAL" : "YOUTUBE"),
  );
  const [input, setInput] = useState("");
  const [batchMode, setBatchMode] = useState(false);
  const [batchText, setBatchText] = useState("");
  const [batchRunState, setBatchRunState] = useState<
    Record<string, { status: "pending" | "running" | "done" | "error"; detail?: string }>
  >({});
  const [batchSummary, setBatchSummary] = useState<{
    succeeded: number;
    failed: number;
    lastContentId?: string;
  } | null>(null);
  const [mode, setMode] = useState("ORGANIZE_CONTENT");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ kind: RecognizedLink["kind"]; content_id?: string; status?: string } | null>(null);
  const recognized = recognizeLink(input);
  const parsedBatch = parseBatchLinks(batchText);
  const batchHasChannel = parsedBatch.validItems.some((item) => item.recognized.kind === "YOUTUBE_CHANNEL");
  const batchKindLabel = (kind: RecognizedLink["kind"]) =>
    kind === "YOUTUBE_CHANNEL"
      ? zh
        ? "YouTube 频道"
        : "YouTube channel"
      : kind === "BILIBILI_VIDEO"
        ? zh
          ? "B站视频"
          : "Bilibili video"
        : zh
          ? "YouTube 视频"
          : "YouTube video";
  const formatBatchApiError = (reason: unknown, kind: RecognizedLink["kind"]) => {
    const code = reason instanceof ApiRequestError ? reason.code : "NETWORK_UNAVAILABLE";
    if (code.includes("INVALID") || code.includes("UNSUPPORTED")) return t(invalidLinkCopy);
    return kind === "BILIBILI_VIDEO"
      ? t(bilibiliStatus(code))
      : t(trackingCopy(code.replace(/^YOUTUBE_/, ""), "YOUTUBE"));
  };
  useEffect(() => {
    if (entryMode !== "YOUTUBE") return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        if (result) onSaved();
        else onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [entryMode, busy, result, onClose, onSaved]);
  if (entryMode === "LOCAL") {
    return (
      <LocalImport
        onClose={onClose}
        onSaved={onSaved}
        onImported={onImported ? id => onImported(id, "LOCAL") : undefined}
        onYouTube={() => setEntryMode("YOUTUBE")}
      />
    );
  }
  if (entryMode === "PASTE") {
    return (
      <QuickPasteNoteForm
        onClose={onClose}
        onSaved={onSaved}
        onImported={onImported ? id => onImported(id, "LOCAL") : undefined}
        onYouTube={() => setEntryMode("YOUTUBE")}
        onLocalFiles={() => setEntryMode("LOCAL")}
      />
    );
  }
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="add-entry-title">
    <div className="modal-head"><h2 id="add-entry-title">{t("Add a Source")}</h2><button className="button button-ghost" aria-label={t("Close")} disabled={busy} onClick={result ? onSaved : onClose}>{t(result ? "Done" : "Close")}</button></div>
    {!result && <>
      <div className="button-row" aria-label={t("Source provider")}>
        <button type="button" className="button button-primary" aria-pressed="true" disabled={busy}>YouTube / Bilibili</button>
        <button type="button" className="button button-secondary" disabled={busy} onClick={() => setEntryMode("LOCAL")}>{t("Local files")}</button>
        <button type="button" className="button button-secondary" disabled={busy} onClick={() => setEntryMode("PASTE")}>{zh ? "粘贴文本/笔记" : "Paste text"}</button>
      </div>
      <div className="batch-mode-bar">
        <p>
          {batchMode
            ? zh
              ? "最多可批量粘贴 10 条 YouTube 或 B 站链接（每行一条）。"
              : "Paste up to 10 YouTube or Bilibili links (one per line)."
            : t("Paste a YouTube or Bilibili link. We will recognize it before you add it.")}
        </p>
        <button
          type="button"
          className="button button-ghost button-small batch-mode-toggle"
          disabled={busy}
          onClick={() => {
            setError(null);
            setBatchSummary(null);
            setBatchRunState({});
            setBatchMode((prev) => {
              const next = !prev;
              if (next && !batchText.trim() && input.trim()) {
                setBatchText(input.trim());
              }
              return next;
            });
          }}
        >
          {batchMode
            ? zh
              ? "切换单条输入"
              : "Single link"
            : zh
              ? "批量粘贴多条"
              : "Batch paste"}
        </button>
      </div>
      {!batchMode ? (
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
            if (onImported) {
              onImported(response.import.content_id, recognized.kind);
              return;
            }
            setResult({ kind: recognized.kind, content_id: response.import.content_id, status: response.import.processing_status });
          } else {
            const response = await post<{ source: { video_id: string } }>("/sources/import", { url: recognized.canonical, command_id: crypto.randomUUID() });
            if (onImported) {
              onImported(response.source.video_id, recognized.kind);
              return;
            }
            setResult({ kind: recognized.kind, content_id: response.source.video_id });
          }
        } catch (reason) {
          const code = reason instanceof ApiRequestError ? reason.code : "NETWORK_UNAVAILABLE";
          setError(code.includes("INVALID") || code.includes("UNSUPPORTED") ? invalidLinkCopy : recognized.kind === "BILIBILI_VIDEO" ? bilibiliStatus(code) : trackingCopy(code.replace(/^YOUTUBE_/, ""), "YOUTUBE"));
        } finally { setBusy(false); }
      }}>
        <label className="field">{t("Paste link")}<input autoFocus aria-label={t("Paste link")} value={input} maxLength={2048} disabled={busy} onPaste={event => {
          const pasted = event.clipboardData?.getData("text") ?? "";
          if (/[\r\n]/.test(pasted)) {
            const preview = parseBatchLinks(pasted);
            if (preview.validItems.length >= 2) {
              event.preventDefault();
              const combined = input.trim() && !pasted.includes(input.trim()) ? `${input.trim()}\n${pasted}` : pasted;
              setBatchText(combined);
              setBatchMode(true);
              setBatchRunState({});
              setBatchSummary(null);
              setError(null);
            }
          }
        }} onChange={event => { setInput(event.target.value); setError(null); }} placeholder={zh ? "粘贴 YouTube 视频/频道链接，或 B 站 BV 链接" : "https://www.youtube.com/watch?v=..., @channel, or BV..."} /></label>
        {recognized && <p className="semantic-state state-neutral" role="status">{zh ? "✓ 已识别 · " : "✓ Recognized · "}{t(confirmation[recognized.kind])}</p>}
        {!recognized && !error && input.trim().length > 0 && <p className="hint" role="status">{linkHint(input, zh)}</p>}
        {recognized?.kind === "YOUTUBE_CHANNEL" && <fieldset disabled={busy} className="processing-modes"><legend>{t("When new content is found")}</legend>
          <label><input type="radio" name="processing-mode" checked={mode === "ORGANIZE_CONTENT"} onChange={() => setMode("ORGANIZE_CONTENT")} /> {t("Organize content")}<small>{t("Automatically save new content with readable summaries and verifiable source references.")}</small></label>
          <label><input type="radio" name="processing-mode" checked={mode === "EXTRACT_INTELLIGENCE"} onChange={() => setMode("EXTRACT_INTELLIGENCE")} /> {t("Also extract Intelligence")}<small>{t("After organizing content, consider which information deserves lasting knowledge. A qualified model and any required consent are needed.")}</small></label>
        </fieldset>}
        {error && <p className="form-error" role="alert">{t(error)}</p>}
        <div className="button-row">
          <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? recognized?.kind === "YOUTUBE_CHANNEL" ? "Establishing tracking…" : "Starting import…" : recognized?.kind === "YOUTUBE_CHANNEL" ? "Follow channel" : "Confirm import")}</button>
          <button type="button" className="button button-secondary" disabled={busy} onClick={() => setEntryMode("LOCAL")}>{t("Import local file")}</button>
        </div>
      </form>
      ) : (
      <form onSubmit={async event => {
        event.preventDefault();
        if (busy || parsedBatch.validItems.length === 0) return;
        setBusy(true);
        setError(null);
        setBatchSummary(null);
        const initialState: Record<string, { status: "pending" | "running" | "done" | "error"; detail?: string }> = {};
        for (const item of parsedBatch.validItems) {
          initialState[item.recognized.canonical] = { status: "pending" };
        }
        setBatchRunState(initialState);
        let succeeded = 0;
        let failed = 0;
        let lastContentId: string | undefined;
        try {
          for (const item of parsedBatch.validItems) {
            const key = item.recognized.canonical;
            setBatchRunState((prev) => ({ ...prev, [key]: { status: "running" } }));
            try {
              if (item.recognized.kind === "YOUTUBE_CHANNEL") {
                await post("/sources/channels", { input: key, processing_mode: mode });
              } else if (item.recognized.kind === "BILIBILI_VIDEO") {
                const response = await post<{ import: { content_id: string } }>("/bilibili/imports", { input: key });
                lastContentId = response.import.content_id;
              } else {
                const response = await post<{ source: { video_id: string } }>("/sources/import", { url: key, command_id: crypto.randomUUID() });
                lastContentId = response.source.video_id;
              }
              succeeded += 1;
              setBatchRunState((prev) => ({ ...prev, [key]: { status: "done" } }));
            } catch (reason) {
              failed += 1;
              setBatchRunState((prev) => ({
                ...prev,
                [key]: { status: "error", detail: formatBatchApiError(reason, item.recognized.kind) },
              }));
            }
          }
          setBatchSummary({ succeeded, failed, lastContentId });
        } finally {
          setBusy(false);
        }
      }}>
        <label className="field">
          {zh ? "批量链接（每行一条，最多 10 条）" : "Batch links (one per line, up to 10)"}
          <textarea
            autoFocus
            className="batch-links-textarea"
            rows={5}
            aria-label={zh ? "批量链接（每行一条，最多 10 条）" : "Batch links (one per line, up to 10)"}
            value={batchText}
            disabled={busy}
            placeholder={zh ? "每行粘贴一条 YouTube 视频、频道/@用户名，或 B 站 BV 链接…" : "Paste up to 10 YouTube video/channel URLs, @handles, or Bilibili BV links…"}
            onChange={(event) => {
              setBatchText(event.target.value);
              setBatchRunState({});
              setBatchSummary(null);
              setError(null);
            }}
          />
        </label>
        {batchText.trim().length > 0 && (
          <p className="semantic-state state-neutral batch-preview-summary" role="status">
            {zh
              ? `已识别 ${parsedBatch.validItems.length} 条可导入${parsedBatch.invalidCount > 0 ? ` · ${parsedBatch.invalidCount} 条未识别` : ""}${parsedBatch.duplicateCount > 0 ? ` · 已去重 ${parsedBatch.duplicateCount} 条` : ""}${parsedBatch.truncatedCount > 0 ? ` · 超出上限跳过 ${parsedBatch.truncatedCount} 条` : ""}`
              : `${parsedBatch.validItems.length} recognized${parsedBatch.invalidCount > 0 ? ` · ${parsedBatch.invalidCount} invalid` : ""}${parsedBatch.duplicateCount > 0 ? ` · ${parsedBatch.duplicateCount} duplicates removed` : ""}${parsedBatch.truncatedCount > 0 ? ` · ${parsedBatch.truncatedCount} over 10-link cap skipped` : ""}`}
          </p>
        )}
        {parsedBatch.items.length > 0 && (
          <ul className="batch-preview-list" aria-label={zh ? "批量链接识别队列" : "Batch link recognition queue"}>
            {parsedBatch.items.map((item, idx) => {
              const key = item.recognized ? item.recognized.canonical : `invalid-${idx}-${item.raw}`;
              const run = item.recognized ? batchRunState[item.recognized.canonical] : undefined;
              return (
                <li key={key} className={`batch-preview-item${item.recognized ? "" : " is-invalid"}`}>
                  <span className={`batch-kind-pill${item.recognized ? "" : " is-invalid"}`}>
                    {item.recognized ? batchKindLabel(item.recognized.kind) : zh ? "未识别" : "Invalid"}
                  </span>
                  <span className="batch-preview-target">{item.recognized ? item.recognized.canonical : item.raw}</span>
                  {run && (
                    <span className={`batch-status-pill is-${run.status}`}>
                      {run.status === "pending"
                        ? zh
                          ? "排队中"
                          : "Queued"
                        : run.status === "running"
                          ? zh
                            ? "导入中…"
                            : "Importing…"
                          : run.status === "done"
                            ? zh
                              ? "✓ 已加入"
                              : "✓ Added"
                            : run.detail
                              ? `✗ ${run.detail}`
                              : zh
                                ? "✗ 失败"
                                : "✗ Failed"}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {batchHasChannel && (
          <fieldset disabled={busy} className="processing-modes"><legend>{t("When new content is found")}</legend>
            <label><input type="radio" name="batch-processing-mode" checked={mode === "ORGANIZE_CONTENT"} onChange={() => setMode("ORGANIZE_CONTENT")} /> {t("Organize content")}<small>{t("Automatically save new content with readable summaries and verifiable source references.")}</small></label>
            <label><input type="radio" name="batch-processing-mode" checked={mode === "EXTRACT_INTELLIGENCE"} onChange={() => setMode("EXTRACT_INTELLIGENCE")} /> {t("Also extract Intelligence")}<small>{t("After organizing content, consider which information deserves lasting knowledge. A qualified model and any required consent are needed.")}</small></label>
          </fieldset>
        )}
        {batchSummary && (
          <div className="batch-run-summary" role="status" aria-live="polite">
            <p>
              {zh
                ? `批量导入完成：${batchSummary.succeeded} 条成功，${batchSummary.failed} 条失败。`
                : `Batch complete: ${batchSummary.succeeded} succeeded, ${batchSummary.failed} failed.`}
            </p>
            <div className="button-row">
              <a className="button button-secondary" href="#Content" onClick={onSaved}>
                {zh ? "打开内容库" : "Open Content"}
              </a>
              <button type="button" className="button button-primary" onClick={onSaved}>
                {t("Done")}
              </button>
            </div>
          </div>
        )}
        {!batchSummary && (
          <div className="button-row">
            <button
              type="submit"
              className="button button-primary"
              disabled={busy || parsedBatch.validItems.length === 0}
            >
              {busy
                ? zh
                  ? "正在依次导入…"
                  : "Importing queue…"
                : zh
                  ? `开始批量导入 (${parsedBatch.validItems.length})`
                  : `Import batch (${parsedBatch.validItems.length})`}
            </button>
            <button type="button" className="button button-secondary" disabled={busy} onClick={() => setEntryMode("LOCAL")}>
              {t("Import local file")}
            </button>
          </div>
        )}
      </form>
      )}
      <p className="hint">
        {zh
          ? "B 站与本地文件国内直连即可使用；YouTube 链接需当前网络可访问 YouTube。"
          : "Bilibili and local files work without VPN; YouTube links require reachable access to YouTube."}
      </p>
    </>}
    {busy && <p role="status" aria-live="polite">{t(recognized?.kind === "YOUTUBE_CHANNEL" ? "Establishing tracking…" : "Starting import…")}</p>}
    {result && <div role="status" aria-live="polite"><p>{t(result.kind === "YOUTUBE_CHANNEL" ? "Channel followed. Check Following for its starting point and source health." : "Import accepted. Processing and any required attention appear in Content.")}</p>
      {result.status && <p>{t(bilibiliStatus(result.status))}</p>}
      <div className="button-row">
        {result.content_id && <a className="button button-secondary" href={`#Content/${result.content_id}`} onClick={onSaved}>{t("Open Content")}</a>}
        <button className="button button-primary" onClick={onSaved}>{t("Done")}</button>
      </div>
    </div>}
  </section></div>;
}
