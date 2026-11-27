import { useEffect, useRef, useState } from "react";
import {
  deletePersonalNote,
  normalizeNoteTags,
  PERSONAL_NOTES_CHANGED_EVENT,
  PersonalNote,
  readPersonalNote,
  savePersonalNote,
} from "./personalNotes";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";

export function ReaderPersonalNoteCard({
  videoId,
  onNoteChange,
}: {
  videoId: string;
  onNoteChange?: (note: PersonalNote | null) => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const initialNote = readPersonalNote(videoId);
  const [text, setText] = useState(initialNote?.text ?? "");
  const [tagDraft, setTagDraft] = useState(initialNote?.tags.join(", ") ?? "");
  const [expanded, setExpanded] = useState(Boolean(initialNote));
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved">("idle");
  const debounceRef = useRef<number | null>(null);
  const onNoteChangeRef = useRef(onNoteChange);
  onNoteChangeRef.current = onNoteChange;

  useEffect(() => {
    const syncFromStore = () => {
      const latest = readPersonalNote(videoId);
      setText(latest?.text ?? "");
      setTagDraft(latest?.tags.join(", ") ?? "");
      if (latest) setExpanded(true);
      onNoteChangeRef.current?.(latest);
    };
    syncFromStore();
    window.addEventListener(PERSONAL_NOTES_CHANGED_EVENT, syncFromStore);
    return () => {
      window.removeEventListener(PERSONAL_NOTES_CHANGED_EVENT, syncFromStore);
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [videoId]);

  const flushSave = (nextText: string, nextTagDraft: string) => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    const saved = savePersonalNote(videoId, {
      text: nextText,
      tags: normalizeNoteTags(nextTagDraft),
    });
    onNoteChangeRef.current?.(saved);
    setSaveStatus(saved ? "saved" : "idle");
  };

  const scheduleSave = (nextText: string, nextTagDraft: string) => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    debounceRef.current = window.setTimeout(() => {
      debounceRef.current = null;
      flushSave(nextText, nextTagDraft);
    }, 280);
  };

  const parsedTags = normalizeNoteTags(tagDraft);
  const hasContent = Boolean(text.trim() || parsedTags.length > 0);

  if (!expanded && !hasContent) {
    return (
      <section
        className="panel reader-personal-note-collapsed"
        aria-label={zh ? "我的思考与批注" : "My Notes & Highlights"}
      >
        <div className="reader-personal-note-collapsed-copy">
          <PhosphorIcon name="file-text" size={15} className="panel-title-icon" />
          <span>
            {zh
              ? "记录我的思考与批注（纯本机保存 · 复制或下载 Obsidian 笔记时自动附带）"
              : "Capture personal notes & clipped quotes (saved locally & merged into Obsidian exports)"}
          </span>
        </div>
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={() => setExpanded(true)}
        >
          {zh ? "写笔记" : "Add note"}
        </button>
      </section>
    );
  }

  return (
    <section
      className="panel reader-personal-note-card"
      aria-label={zh ? "我的思考与批注" : "My Notes & Highlights"}
    >
      <div className="panel-head reader-personal-note-head">
        <h2>
          <PhosphorIcon name="file-text" size={15} className="panel-title-icon" />
          <span>{zh ? "我的思考与批注" : "My Notes & Highlights"}</span>
        </h2>
        <div className="reader-personal-note-head-actions">
          <span className="hint" role="status">
            {saveStatus === "saved" || hasContent
              ? zh
                ? "已保存在本机（导出 Obsidian 时自动附带）"
                : "Saved locally (merged on Obsidian export)"
              : zh
                ? "纯本机存储"
                : "Stored locally"}
          </span>
          {hasContent ? (
            <button
              type="button"
              className="button button-ghost button-small"
              onClick={() => {
                if (debounceRef.current !== null) {
                  window.clearTimeout(debounceRef.current);
                  debounceRef.current = null;
                }
                setText("");
                setTagDraft("");
                setSaveStatus("idle");
                deletePersonalNote(videoId);
                onNoteChangeRef.current?.(null);
              }}
            >
              {zh ? "清空" : "Clear"}
            </button>
          ) : (
            <button
              type="button"
              className="button button-ghost button-small"
              onClick={() => setExpanded(false)}
            >
              {zh ? "收起" : "Collapse"}
            </button>
          )}
        </div>
      </div>

      <textarea
        rows={4}
        className="personal-note-textarea"
        aria-label={zh ? "我的思考与批注内容" : "My personal notes"}
        placeholder={
          zh
            ? "写下自己的核心判断、实践启发，或在原话证据中点击「+ 摘录到笔记」自动收集金句…"
            : "Write your own takeaways or click '+ Clip to notes' in the Evidence drawer…"
        }
        value={text}
        onChange={(event) => {
          const val = event.target.value;
          setText(val);
          scheduleSave(val, tagDraft);
        }}
        onBlur={() => flushSave(text, tagDraft)}
      />

      <div className="personal-note-tags-row">
        <input
          type="text"
          className="personal-note-tags-input"
          aria-label={zh ? "个人标签（逗号或空格分隔）" : "Personal tags (comma-separated)"}
          placeholder={zh ? "个人标签，如：架构, Agent, 待验证" : "Tags, e.g.: architecture, followup"}
          value={tagDraft}
          onChange={(event) => {
            const val = event.target.value;
            setTagDraft(val);
            scheduleSave(text, val);
          }}
          onBlur={() => flushSave(text, tagDraft)}
        />
        {parsedTags.length > 0 ? (
          <div className="personal-note-tag-pills">
            {parsedTags.map((tag) => (
              <span key={tag} className="personal-note-tag-pill">
                #{tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
