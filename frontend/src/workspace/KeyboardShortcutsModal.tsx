import { useEffect, useRef } from "react";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";

type ShortcutRow = {
  keys: string[];
  label: string;
};

type ShortcutGroup = {
  id: string;
  title: string;
  rows: ShortcutRow[];
};

export function KeyboardShortcutsModal({
  open,
  onClose,
  onOpenCommandPalette,
}: {
  open: boolean;
  onClose: () => void;
  onOpenCommandPalette: () => void;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const skipFocusRestoreRef = useRef(false);
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (open) {
      wasOpenRef.current = true;
      skipFocusRestoreRef.current = false;
      previousFocusRef.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      const timer = window.setTimeout(() => {
        closeButtonRef.current?.focus({ preventScroll: true });
      }, 0);
      return () => window.clearTimeout(timer);
    }
    if (wasOpenRef.current) {
      wasOpenRef.current = false;
      if (!skipFocusRestoreRef.current) {
        const previous = previousFocusRef.current;
        previousFocusRef.current = null;
        if (previous && previous.isConnected) {
          previous.focus({ preventScroll: true });
        }
      } else {
        previousFocusRef.current = null;
      }
    }
    return undefined;
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [open, onClose]);

  if (!open) return null;

  const groups: ShortcutGroup[] = zh
    ? [
        {
          id: "global",
          title: "全局导航与面板",
          rows: [
            { keys: ["⌘K", "Ctrl+K"], label: "打开「搜索与直达」命令面板" },
            { keys: ["?"], label: "打开键盘快捷键指南" },
            { keys: ["Esc"], label: "关闭当前弹窗、抽屉或返回" },
          ],
        },
        {
          id: "goto-chords",
          title: "页面直达（G + 键）",
          rows: [
            { keys: ["G", "H"], label: "前往首页（Home）" },
            { keys: ["G", "F"], label: "前往关注与信源（Following）" },
            { keys: ["G", "C"], label: "前往内容库（Content）" },
            { keys: ["G", "I"], label: "前往洞察（Intelligence）" },
            { keys: ["G", "T"], label: "前往主题（Topics）" },
            { keys: ["G", "R"], label: "前往跨视频研究（Research）" },
            { keys: ["G", "S"], label: "前往设置（Settings）" },
          ],
        },
        {
          id: "content-list",
          title: "内容分诊列表（#Content）",
          rows: [
            { keys: ["/"], label: "聚焦搜索框过滤内容" },
            { keys: ["J", "K"], label: "上下切换列表选中条目" },
            { keys: ["Enter"], label: "打开当前选中内容详情" },
            { keys: ["S"], label: "收藏或取消待看" },
            { keys: ["E"], label: "标记已读或取消已读" },
          ],
        },
        {
          id: "content-reader",
          title: "内容阅读器（#Content/:id）",
          rows: [
            { keys: ["N"], label: "聚焦「我的思考与批注」输入框" },
            { keys: ["S"], label: "收藏待看" },
            { keys: ["E"], label: "标为已读并跳至下一篇" },
            { keys: ["U"], label: "返回内容分诊列表" },
            { keys: ["Esc"], label: "关闭原文抽屉或关键帧大图" },
          ],
        },
      ]
    : [
        {
          id: "global",
          title: "Global navigation",
          rows: [
            { keys: ["⌘K", "Ctrl+K"], label: "Open Command Palette" },
            { keys: ["?"], label: "Open Keyboard Shortcuts" },
            { keys: ["Esc"], label: "Close modal, drawer, or detail" },
          ],
        },
        {
          id: "goto-chords",
          title: "Go-to navigation (G + key)",
          rows: [
            { keys: ["G", "H"], label: "Go to Home" },
            { keys: ["G", "F"], label: "Go to Following" },
            { keys: ["G", "C"], label: "Go to Content" },
            { keys: ["G", "I"], label: "Go to Intelligence" },
            { keys: ["G", "T"], label: "Go to Topics" },
            { keys: ["G", "R"], label: "Go to Research" },
            { keys: ["G", "S"], label: "Go to Settings" },
          ],
        },
        {
          id: "content-list",
          title: "Content triage list (#Content)",
          rows: [
            { keys: ["/"], label: "Focus Content search box" },
            { keys: ["J", "K"], label: "Move selection down / up" },
            { keys: ["Enter"], label: "Open selected item in Reader" },
            { keys: ["S"], label: "Toggle Starred" },
            { keys: ["E"], label: "Toggle Read state" },
          ],
        },
        {
          id: "content-reader",
          title: "Content Reader (#Content/:id)",
          rows: [
            { keys: ["N"], label: "Focus Personal Note editor" },
            { keys: ["S"], label: "Toggle Starred" },
            { keys: ["E"], label: "Mark read and open next unread" },
            { keys: ["U"], label: "Return to Content list" },
            { keys: ["Esc"], label: "Close transcript drawer or lightbox" },
          ],
        },
      ];

  return (
    <div
      className="shortcuts-modal-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="shortcuts-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-modal-title"
      >
        <div className="shortcuts-modal-head">
          <div className="shortcuts-modal-title-wrap">
            <h2 id="shortcuts-modal-title">
              {zh ? "键盘快捷键指南" : "Keyboard Shortcuts"}
            </h2>
            <p className="shortcuts-modal-subtitle">
              {zh
                ? "高频分诊、阅读与全站直达快捷键。输入框内自动暂停单键响应。"
                : "Fast triage, reading, and workspace navigation. Single-key shortcuts pause while typing."}
            </p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="button button-secondary button-small"
            aria-label={zh ? "关闭快捷键指南" : "Close keyboard shortcuts"}
            onClick={onClose}
          >
            {zh ? "关闭 (Esc)" : "Close (Esc)"}
          </button>
        </div>

        <div className="shortcuts-modal-body">
          {groups.map((group) => (
            <section key={group.id} className="shortcuts-group">
              <h3>{group.title}</h3>
              <ul className="shortcuts-list">
                {group.rows.map((row) => (
                  <li key={row.label} className="shortcuts-row">
                    <span className="shortcuts-row-label">{row.label}</span>
                    <span className="shortcuts-row-keys">
                      {row.keys.map((keyLabel) => (
                        <kbd key={keyLabel} className="shortcuts-kbd">
                          {keyLabel}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <div className="shortcuts-modal-foot">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={() => {
              skipFocusRestoreRef.current = true;
              onClose();
              onOpenCommandPalette();
            }}
          >
            <PhosphorIcon name="magnifying-glass" size={13} />
            <span>{zh ? "打开 ⌘K 命令面板" : "Open ⌘K palette"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
