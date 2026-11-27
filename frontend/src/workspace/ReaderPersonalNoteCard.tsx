import { useEffect, useRef, useState } from "react";
import {
  deletePersonalNote,
  listPersonalTagCounts,
  normalizeNoteTags,
  PERSONAL_NOTES_CHANGED_EVENT,
  PersonalNote,
  PersonalTagCount,
  readPersonalNote,
  savePersonalNote,
} from "./personalNotes";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";

const NOTE_REFLECTION_TEMPLATES = [
  {
    id: "review321",
    labelZh: "+ 3-2-1 复盘",
    labelEn: "+ 3-2-1 Review",
    bodyZh: "### 3 个核心收获\n- \n\n### 2 个延伸思考\n- \n\n### 1 个落地动作\n- ",
    bodyEn: "### 3 Key Takeaways\n- \n\n### 2 Deeper Questions\n- \n\n### 1 Next Action\n- ",
  },
  {
    id: "openQuestions",
    labelZh: "+ 质疑与待核查",
    labelEn: "+ Open questions",
    bodyZh: "### 质疑与待核查\n- ",
    bodyEn: "### Open Questions & Assumptions\n- ",
  },
  {
    id: "nextActions",
    labelZh: "+ 下一步行动",
    labelEn: "+ Next actions",
    bodyZh: "### 实践行动项\n- [ ] ",
    bodyEn: "### Action Checklist\n- [ ] ",
  },
] as const;

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
  const [libraryTags, setLibraryTags] = useState<PersonalTagCount[]>(() =>
    listPersonalTagCounts(),
  );
  const debounceRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const onNoteChangeRef = useRef(onNoteChange);
  onNoteChangeRef.current = onNoteChange;

  useEffect(() => {
    const syncFromStore = () => {
      const latest = readPersonalNote(videoId);
      setText(latest?.text ?? "");
      setTagDraft(latest?.tags.join(", ") ?? "");
      setLibraryTags(listPersonalTagCounts());
      if (latest) setExpanded(true);
      onNoteChangeRef.current?.(latest);
    };
    const syncTagsOnly = () => setLibraryTags(listPersonalTagCounts());
    syncFromStore();
    window.addEventListener(PERSONAL_NOTES_CHANGED_EVENT, syncFromStore);
    window.addEventListener("storage", syncTagsOnly);
    return () => {
      window.removeEventListener(PERSONAL_NOTES_CHANGED_EVENT, syncFromStore);
      window.removeEventListener("storage", syncTagsOnly);
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
  const parsedTagSet = new Set(parsedTags.map((item) => item.toLowerCase()));
  const suggestedLibraryTags = libraryTags
    .filter((entry) => !parsedTagSet.has(entry.tag.toLowerCase()))
    .slice(0, 8);
  const hasContent = Boolean(text.trim() || parsedTags.length > 0);

  const appendTemplate = (snippet: string) => {
    const nextText = text.trimEnd() ? `${text.trimEnd()}\n\n${snippet}` : snippet;
    setText(nextText);
    flushSave(nextText, tagDraft);
    queueMicrotask(() => {
      const el = textareaRef.current;
      if (el) {
        el.focus();
        const len = nextText.length;
        el.setSelectionRange?.(len, len);
      }
    });
  };

  const appendSuggestedTag = (tag: string) => {
    const merged = normalizeNoteTags([...parsedTags, tag].join(", "));
    const nextDraft = merged.join(", ");
    setTagDraft(nextDraft);
    flushSave(text, nextDraft);
  };

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

      <div
        className="personal-note-templates-row"
        role="group"
        aria-label={zh ? "结构化思考模板" : "Reflection note templates"}
      >
        {NOTE_REFLECTION_TEMPLATES.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            className="personal-note-template-chip"
            onClick={() => appendTemplate(zh ? tpl.bodyZh : tpl.bodyEn)}
          >
            {zh ? tpl.labelZh : tpl.labelEn}
          </button>
        ))}
      </div>

      <textarea
        ref={textareaRef}
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
      {suggestedLibraryTags.length > 0 ? (
        <div
          className="personal-note-suggested-tags"
          role="group"
          aria-label={zh ? "点选已有自建标签" : "Reuse existing library tags"}
        >
          <span className="personal-note-suggested-label">
            {zh ? "已有标签：" : "Library tags:"}
          </span>
          {suggestedLibraryTags.map((entry) => (
            <button
              key={entry.tag}
              type="button"
              className="personal-note-suggested-tag"
              onClick={() => appendSuggestedTag(entry.tag)}
            >
              + #{entry.tag}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
