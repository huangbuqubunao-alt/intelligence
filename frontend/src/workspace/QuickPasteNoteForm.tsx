import { useEffect, useState } from "react";
import { ApiRequestError, uploadLocal } from "../api/client";
import { localImportErrors } from "./LocalImport";
import { estimateReadingMinutes } from "./readingHistory";
import { useUiLanguage } from "./uiLanguage";

const QUICK_PASTE_TEMPLATES = [
  {
    id: "meeting",
    labelZh: "+ 会议纪要",
    labelEn: "+ Meeting notes",
    bodyZh: "## 参会背景与目标\n- \n\n## 核心结论与分歧\n- \n\n## 后续行动项\n- [ ] ",
    bodyEn: "## Context & Goal\n- \n\n## Key Decisions\n- \n\n## Next Actions\n- [ ] ",
  },
  {
    id: "reading",
    labelZh: "+ 文章精读摘录",
    labelEn: "+ Reading excerpt",
    bodyZh: "## 原文核心论点\n- \n\n## 关键引用与证据\n> \n\n## 我的思考与质疑\n- ",
    bodyEn: "## Core Thesis\n- \n\n## Key Quotes\n> \n\n## My Takeaways\n- ",
  },
  {
    id: "research",
    labelZh: "+ 调研对比备忘",
    labelEn: "+ Research memo",
    bodyZh: "## 调研问题\n- \n\n## 方案对比与权衡\n- \n\n## 结论与下一步\n- [ ] ",
    bodyEn: "## Question\n- \n\n## Trade-offs Compared\n- \n\n## Conclusion\n- [ ] ",
  },
] as const;

const MAX_PASTE_BYTES = 2 * 1024 * 1024;

export function derivePasteFilename(title: string, body: string): string {
  const firstMeaningfulLine =
    body
      .split(/\r?\n/)
      .map((line) => line.replace(/^#+\s*/, "").trim())
      .find(Boolean) ?? "";
  const candidate = (title.trim() || firstMeaningfulLine)
    .replace(/\.(md|markdown|txt)$/i, "")
    .replace(/[\\/:*?"<>|\p{Cc}\p{Cf}\p{Cs}]/gu, "-")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[.-]+|[.-]+$/g, "")
    .slice(0, 64);
  if (candidate) {
    return `${candidate}.md`;
  }
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    "-",
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
  ].join("");
  return `pasted-note-${stamp}.md`;
}

export function buildPastedMarkdownPayload(title: string, body: string): string {
  const cleanTitle = title.trim();
  const cleanBody = body.trim();
  if (!cleanBody) return "";
  if (cleanTitle && !cleanBody.startsWith("# ")) {
    return `# ${cleanTitle}\n\n${cleanBody}\n`;
  }
  return `${cleanBody}\n`;
}

export function QuickPasteNoteForm({
  onClose,
  onSaved,
  onImported,
  onYouTube,
  onLocalFiles,
}: {
  onClose: () => void;
  onSaved: () => void;
  onImported?: (contentId: string) => void;
  onYouTube: () => void;
  onLocalFiles: () => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);

  const payload = buildPastedMarkdownPayload(title, body);
  const byteCount = payload ? new TextEncoder().encode(payload).length : 0;
  const derivedName = payload ? derivePasteFilename(title, body) : "pasted-note.md";
  const tooLarge = byteCount > MAX_PASTE_BYTES;
  const estimatedMinutes = body.trim() ? estimateReadingMinutes({ text: body }) : null;
  const appendStarterTemplate = (snippet: string) => {
    setBody((prev) => (prev.trimEnd() ? `${prev.trimEnd()}\n\n${snippet}` : snippet));
    if (error) setError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy) return;
    if (!payload) {
      setError(
        zh
          ? "请先粘贴正文内容（支持 Markdown、会议纪要或技术文章摘录）。"
          : "Paste text or Markdown content before importing.",
      );
      return;
    }
    if (tooLarge) {
      setError(localImportErrors.LOCAL_FILE_TOO_LARGE);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const filename = derivePasteFilename(title, body);
      const file = new File([payload], filename, { type: "text/markdown;charset=utf-8" });
      const controller = new AbortController();
      const response = await uploadLocal<{ import: { content_id: string } }>(
        `/local/imports?filename=${encodeURIComponent(filename)}`,
        file,
        controller.signal,
        () => {},
        () => {},
      );
      if (onImported) {
        onImported(response.import.content_id);
      } else {
        onSaved();
      }
    } catch (reason) {
      const code = reason instanceof ApiRequestError ? reason.code : "";
      setError(
        localImportErrors[code] ??
          (zh
            ? "未能保存到本地知识库，请确认本地工作区服务正在运行。"
            : "Could not save pasted note locally. Please ensure the workspace service is running."),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overlay">
      <section
        className="modal local-import"
        role="dialog"
        aria-modal="true"
        aria-labelledby="paste-note-title"
      >
        <div className="modal-head">
          <h2 id="paste-note-title">
            {zh ? "粘贴文本 / 笔记直接入库" : "Paste text or Markdown note"}
          </h2>
          <button
            type="button"
            className="button button-ghost"
            aria-label={t("Close")}
            disabled={busy}
            onClick={onClose}
          >
            {t("Close")}
          </button>
        </div>
        <div className="button-row" aria-label={t("Source provider")}>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy}
            onClick={onYouTube}
          >
            YouTube / Bilibili
          </button>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy}
            onClick={onLocalFiles}
          >
            {t("Local files")}
          </button>
          <button
            type="button"
            className="button button-primary"
            aria-pressed="true"
            disabled={busy}
          >
            {zh ? "粘贴文本/笔记" : "Paste text"}
          </button>
        </div>
        <p className="hint">
          {zh
            ? "无需提前保存本地文件：直接粘贴会议纪要、网页文章或调研笔记，安全保存至本机 127.0.0.1 知识库。"
            : "No file creation needed: paste meeting notes, articles, or Markdown straight into your local library."}
        </p>
        <form onSubmit={(e) => void handleSubmit(e)}>
          <label className="field">
            {zh ? "笔记标题（可选，留空自动提取首行）" : "Note title (optional)"}
            <input
              type="text"
              value={title}
              maxLength={120}
              disabled={busy}
              aria-label={zh ? "笔记标题（可选）" : "Note title (optional)"}
              placeholder={
                zh ? "例如：2026 Agent 架构访谈纪要" : "e.g., Architecture review notes"
              }
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <div
            className="quick-paste-templates-row"
            role="group"
            aria-label={zh ? "快速结构化模板" : "Quick structure templates"}
          >
            {QUICK_PASTE_TEMPLATES.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                className="personal-note-template-chip"
                disabled={busy}
                onClick={() => appendStarterTemplate(zh ? tpl.bodyZh : tpl.bodyEn)}
              >
                {zh ? tpl.labelZh : tpl.labelEn}
              </button>
            ))}
          </div>
          <label className="field">
            {zh ? "正文内容（支持 Markdown）" : "Note content (Markdown supported)"}
            <textarea
              autoFocus
              rows={8}
              className="paste-note-textarea"
              value={body}
              disabled={busy}
              aria-label={zh ? "粘贴正文内容" : "Paste note content"}
              placeholder={
                zh
                  ? "# 标题或直接粘贴长文段落、会议记录、读书笔记…"
                  : "# Heading or paste Markdown, meeting notes, or article excerpts…"
              }
              onChange={(event) => {
                setBody(event.target.value);
                if (error) setError(null);
              }}
            />
          </label>
          <div className="paste-note-meta-row tabular-nums">
            <span className="hint">
              {zh ? `文件名预览：${derivedName}` : `Filename: ${derivedName}`}
            </span>
            <span className={`hint${tooLarge ? " form-error" : ""}`}>
              {estimatedMinutes !== null
                ? zh
                  ? `约 ${estimatedMinutes} 分钟精读 · ${body.length} 字 · ${(byteCount / 1024).toFixed(1)} KB / 2048 KB`
                  : `~${estimatedMinutes} min read · ${body.length} chars · ${(byteCount / 1024).toFixed(1)} KB / 2048 KB`
                : zh
                  ? `${body.length} 字 · ${(byteCount / 1024).toFixed(1)} KB / 2048 KB`
                  : `${body.length} chars · ${(byteCount / 1024).toFixed(1)} KB / 2048 KB`}
            </span>
          </div>
          {error ? (
            <p className="form-error" role="alert">
              {t(error)}
            </p>
          ) : null}
          <div className="button-row">
            <button
              type="submit"
              className="button button-primary"
              disabled={busy || !payload || tooLarge}
            >
              {busy
                ? zh
                  ? "正在保存入库…"
                  : "Saving note…"
                : zh
                  ? "保存并打开阅读器"
                  : "Save & open reader"}
            </button>
            <button
              type="button"
              className="button button-secondary"
              disabled={busy}
              onClick={onClose}
            >
              {t("Cancel")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
