import { useEffect, useRef, useState } from "react";
import {
  deletePersonalNote,
  listPersonalTagCounts,
  normalizeNoteTags,
  PERSONAL_NOTES_CHANGED_EVENT,
  PERSONAL_NOTES_STORAGE_KEY,
  PersonalNote,
  PersonalTagCount,
  readPersonalNote,
  savePersonalNoteChecked,
} from "./personalNotes";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";
import { isKeyboardShortcutBlocked } from "./WorkspaceAiWidgets";

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

type ConflictRemoteState = {
  note: PersonalNote | null;
  updatedAt: string | null;
};

function mergeConflictDrafts(
  localText: string,
  localTagsRaw: string,
  remoteNote: PersonalNote | null,
): { text: string; tags: string[] } {
  const remoteText = remoteNote?.text?.trim() ?? "";
  const trimmedLocal = localText.trim();
  const mergedText =
    remoteText && trimmedLocal && remoteText !== trimmedLocal
      ? `${remoteText}\n\n---\n${trimmedLocal}`
      : trimmedLocal || remoteText;
  const mergedTags = normalizeNoteTags(
    [...(remoteNote?.tags ?? []), ...normalizeNoteTags(localTagsRaw)].join(", "),
  );
  return { text: mergedText, tags: mergedTags };
}

export function ReaderPersonalNoteCard({
  videoId,
  onNoteChange,
}: {
  videoId: string;
  onNoteChange?: (note: PersonalNote | null) => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const [initialLoaded] = useState<PersonalNote | null>(() => readPersonalNote(videoId));
  const [text, setText] = useState(initialLoaded?.text ?? "");
  const [tagDraft, setTagDraft] = useState(initialLoaded?.tags.join(", ") ?? "");
  const [expanded, setExpanded] = useState(Boolean(initialLoaded));
  const [saveStatus, setSaveStatus] = useState<"idle" | "dirty" | "saved" | "error">(
    initialLoaded ? "saved" : "idle",
  );
  const [conflictState, setConflictState] = useState<ConflictRemoteState | null>(null);
  const [libraryTags, setLibraryTags] = useState<PersonalTagCount[]>(() =>
    listPersonalTagCounts(),
  );
  const debounceRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const suppressShortcutCharUntilRef = useRef<number>(0);
  const isDirtyRef = useRef(false);
  const baseUpdatedAtRef = useRef<string | null>(initialLoaded?.updatedAt ?? null);
  const latestDraftRef = useRef({
    videoId,
    text: initialLoaded?.text ?? "",
    tagDraft: initialLoaded?.tags.join(", ") ?? "",
  });
  latestDraftRef.current = { videoId, text, tagDraft };
  const onNoteChangeRef = useRef(onNoteChange);
  onNoteChangeRef.current = onNoteChange;

  useEffect(() => {
    const applySyncedNote = (latest: PersonalNote | null) => {
      isDirtyRef.current = false;
      baseUpdatedAtRef.current = latest?.updatedAt ?? null;
      setConflictState(null);
      setText(latest?.text ?? "");
      setTagDraft(latest?.tags.join(", ") ?? "");
      setSaveStatus(latest ? "saved" : "idle");
      if (latest) setExpanded(true);
      onNoteChangeRef.current?.(latest);
    };

    const syncFromStore = (forceInit = false) => {
      setLibraryTags(listPersonalTagCounts());
      const latest = readPersonalNote(videoId);
      const latestStamp = latest?.updatedAt ?? null;
      if (forceInit || !isDirtyRef.current) {
        applySyncedNote(latest);
        return;
      }
      if (latestStamp !== baseUpdatedAtRef.current) {
        if (debounceRef.current !== null) {
          window.clearTimeout(debounceRef.current);
          debounceRef.current = null;
        }
        setConflictState({ note: latest, updatedAt: latestStamp });
      }
    };

    const onStorageEvent = (event: StorageEvent) => {
      if (event.key !== null && event.key !== PERSONAL_NOTES_STORAGE_KEY) return;
      syncFromStore(false);
    };
    const onLocalStoreChange = () => syncFromStore(false);

    syncFromStore(true);
    window.addEventListener(PERSONAL_NOTES_CHANGED_EVENT, onLocalStoreChange);
    window.addEventListener("storage", onStorageEvent);
    return () => {
      window.removeEventListener(PERSONAL_NOTES_CHANGED_EVENT, onLocalStoreChange);
      window.removeEventListener("storage", onStorageEvent);
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (isDirtyRef.current) {
        const draft = latestDraftRef.current;
        const currentRemote = readPersonalNote(draft.videoId);
        if ((currentRemote?.updatedAt ?? null) === baseUpdatedAtRef.current) {
          savePersonalNoteChecked(draft.videoId, {
            text: draft.text,
            tags: normalizeNoteTags(draft.tagDraft),
          });
        }
        isDirtyRef.current = false;
      }
    };
  }, [videoId]);

  useEffect(() => {
    let focusTimer: number | null = null;
    const focusNoteTextarea = () => {
      const target = textareaRef.current;
      if (!target) return false;
      target.scrollIntoView?.({ behavior: "smooth", block: "center" });
      target.focus();
      const endPos = target.value.length;
      target.setSelectionRange?.(endPos, endPos);
      return true;
    };
    const onBeforeInputGuard = (event: Event) => {
      if (Date.now() > suppressShortcutCharUntilRef.current) return;
      if (event instanceof InputEvent && typeof event.data === "string" && event.data.toLowerCase() === "n") {
        event.preventDefault();
      }
    };
    const onFocusKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key.toLowerCase() !== "n") return;
      if (isKeyboardShortcutBlocked(event)) return;
      if (typeof document !== "undefined" && document.querySelector('[role="dialog"][aria-modal="true"]')) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      suppressShortcutCharUntilRef.current = Date.now() + 80;
      setExpanded(true);
      if (focusNoteTextarea()) return;
      if (focusTimer !== null) {
        window.clearTimeout(focusTimer);
      }
      focusTimer = window.setTimeout(() => {
        focusTimer = null;
        focusNoteTextarea();
      }, 20);
    };
    window.addEventListener("keydown", onFocusKeyDown, true);
    document.addEventListener("beforeinput", onBeforeInputGuard, true);
    return () => {
      window.removeEventListener("keydown", onFocusKeyDown, true);
      document.removeEventListener("beforeinput", onBeforeInputGuard, true);
      if (focusTimer !== null) {
        window.clearTimeout(focusTimer);
      }
    };
  }, []);

  const flushSave = (nextText: string, nextTagDraft: string, forceOverwrite = false) => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    if (!forceOverwrite) {
      const currentRemote = readPersonalNote(videoId);
      const currentStamp = currentRemote?.updatedAt ?? null;
      if (currentStamp !== baseUpdatedAtRef.current) {
        setConflictState({ note: currentRemote, updatedAt: currentStamp });
        return;
      }
    }
    const { note: saved, persisted } = savePersonalNoteChecked(videoId, {
      text: nextText,
      tags: normalizeNoteTags(nextTagDraft),
    });
    if (!persisted) {
      setSaveStatus("error");
      return;
    }
    isDirtyRef.current = false;
    baseUpdatedAtRef.current = saved?.updatedAt ?? null;
    setConflictState(null);
    onNoteChangeRef.current?.(saved);
    setSaveStatus(saved ? "saved" : "idle");
  };

  const scheduleSave = (nextText: string, nextTagDraft: string) => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    debounceRef.current = window.setTimeout(() => {
      debounceRef.current = null;
      if (!isDirtyRef.current) return;
      flushSave(nextText, nextTagDraft);
    }, 280);
  };

  const handleBlurSave = () => {
    if (!isDirtyRef.current) return;
    flushSave(text, tagDraft);
  };

  const parsedTags = normalizeNoteTags(tagDraft);
  const parsedTagSet = new Set(parsedTags.map((item) => item.toLowerCase()));
  const suggestedLibraryTags = libraryTags
    .filter((entry) => !parsedTagSet.has(entry.tag.toLowerCase()))
    .slice(0, 8);
  const hasContent = Boolean(text.trim() || parsedTags.length > 0);

  const appendTemplate = (snippet: string) => {
    const nextText = text.trimEnd() ? `${text.trimEnd()}\n\n${snippet}` : snippet;
    isDirtyRef.current = true;
    setSaveStatus("dirty");
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
    isDirtyRef.current = true;
    setSaveStatus("dirty");
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
            {saveStatus === "error"
              ? zh
                ? "本机存储空间不足，暂未保存"
                : "Local storage full — save failed"
              : saveStatus === "dirty"
                ? zh
                  ? "正在保存…"
                  : "Saving…"
                : saveStatus === "saved"
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
                isDirtyRef.current = false;
                baseUpdatedAtRef.current = null;
                setConflictState(null);
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

      {conflictState ? (
        <div className="personal-note-conflict-banner" role="alert">
          <p>
            {zh
              ? "检测到其他标签页已更新此笔记。为防止覆盖新内容，当前已暂停自动覆写。"
              : "Another tab updated this note. Auto-overwrite is paused to prevent losing newer changes."}
          </p>
          <div className="button-row">
            <button
              type="button"
              className="button button-secondary button-small"
              onClick={() => {
                const remote = readPersonalNote(videoId);
                isDirtyRef.current = false;
                baseUpdatedAtRef.current = remote?.updatedAt ?? null;
                setConflictState(null);
                setText(remote?.text ?? "");
                setTagDraft(remote?.tags.join(", ") ?? "");
                setSaveStatus(remote ? "saved" : "idle");
                onNoteChangeRef.current?.(remote);
              }}
            >
              {zh ? "采用最新内容" : "Load latest"}
            </button>
            <button
              type="button"
              className="button button-primary button-small"
              onClick={() => {
                const remote = readPersonalNote(videoId);
                const merged = mergeConflictDrafts(text, tagDraft, remote);
                setText(merged.text);
                setTagDraft(merged.tags.join(", "));
                baseUpdatedAtRef.current = remote?.updatedAt ?? null;
                flushSave(merged.text, merged.tags.join(", "), true);
              }}
            >
              {zh ? "合并并保留两边" : "Merge & keep both"}
            </button>
          </div>
        </div>
      ) : null}

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
          isDirtyRef.current = true;
          setSaveStatus("dirty");
          setText(val);
          scheduleSave(val, tagDraft);
        }}
        onBlur={handleBlurSave}
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
            isDirtyRef.current = true;
            setSaveStatus("dirty");
            setTagDraft(val);
            scheduleSave(text, val);
          }}
          onBlur={handleBlurSave}
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
