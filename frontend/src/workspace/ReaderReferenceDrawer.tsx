import {
  KeyboardEvent as ReactKeyboardEvent,
  ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
} from "react";

export type ReaderDrawerTab = "evidence" | "transcript" | "history";

const TAB_ORDER: readonly ReaderDrawerTab[] = ["transcript", "evidence", "history"];

function isInsideClosedDetails(el: HTMLElement): boolean {
  let ancestor: HTMLElement | null = el.parentElement;
  while (ancestor) {
    if (ancestor.tagName === "DETAILS" && !ancestor.hasAttribute("open")) {
      const directSummary = Array.from(ancestor.children).find(
        (child) => child.tagName === "SUMMARY",
      );
      if (!directSummary || !directSummary.contains(el)) {
        return true;
      }
    }
    ancestor = ancestor.parentElement;
  }
  return false;
}

function listFocusableInDrawer(container: HTMLElement): HTMLElement[] {
  const nodes = container.querySelectorAll<HTMLElement>(
    'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
  );
  return Array.from(nodes).filter((el) => {
    const tIdx = el.getAttribute("tabindex");
    if (tIdx === "-1") return false;
    if (el.closest(".reader-ref-pane-inactive, [hidden], [inert]") !== null) return false;
    if (isInsideClosedDetails(el)) return false;
    const style = typeof window !== "undefined" ? window.getComputedStyle(el) : null;
    if (style && (style.display === "none" || style.visibility === "hidden")) return false;
    return true;
  });
}

export type ReaderReferenceDrawerProps = {
  activeTab: ReaderDrawerTab | null;
  zhReader: boolean;
  isTextDocument: boolean;
  evidenceCount: number;
  historyCount: number;
  returnFocusTarget: HTMLElement | null;
  onSelectTab: (tab: ReaderDrawerTab) => void;
  onClose: () => void;
  evidencePane: ReactNode;
  transcriptPane: ReactNode;
  historyPane: ReactNode;
};

export function ReaderReferenceDrawer({
  activeTab,
  zhReader,
  isTextDocument,
  evidenceCount,
  historyCount,
  returnFocusTarget,
  onSelectTab,
  onClose,
  evidencePane,
  transcriptPane,
  historyPane,
}: ReaderReferenceDrawerProps) {
  const isOpen = activeTab !== null;
  const drawerRef = useRef<HTMLElement | null>(null);
  const tabRefs = useRef<Record<ReaderDrawerTab, HTMLButtonElement | null>>({
    transcript: null,
    evidence: null,
    history: null,
  });
  const wasOpenRef = useRef(false);
  const openerRef = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    const el = drawerRef.current as (HTMLElement & { inert: boolean }) | null;
    if (!el) return;
    el.inert = !isOpen;
    if (isOpen) {
      el.removeAttribute("inert");
    } else {
      el.setAttribute("inert", "");
    }
  }, [isOpen]);

  useEffect(() => {
    const wasOpen = wasOpenRef.current;
    wasOpenRef.current = isOpen;
    if (!wasOpen && isOpen) {
      const capturedOpener =
        returnFocusTarget ??
        (document.activeElement instanceof HTMLElement ? document.activeElement : null);
      if (capturedOpener && drawerRef.current && !drawerRef.current.contains(capturedOpener)) {
        openerRef.current = capturedOpener;
      }
      const activeEl = document.activeElement;
      if (drawerRef.current && (!activeEl || !drawerRef.current.contains(activeEl))) {
        const targetTab = activeTab ? tabRefs.current[activeTab] : null;
        if (targetTab) {
          targetTab.focus();
        } else {
          const fallback = listFocusableInDrawer(drawerRef.current)[0];
          fallback?.focus();
        }
      }
    } else if (wasOpen && !isOpen) {
      const restoreTarget = openerRef.current ?? returnFocusTarget;
      openerRef.current = null;
      if (restoreTarget && restoreTarget.isConnected) {
        restoreTarget.focus();
      }
    }
  }, [isOpen, activeTab, returnFocusTarget]);

  const handleDrawerKeyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
    if (!isOpen || !drawerRef.current) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusables = listFocusableInDrawer(drawerRef.current);
    if (focusables.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const current = document.activeElement as HTMLElement | null;
    if (event.shiftKey) {
      if (!current || current === first || !drawerRef.current.contains(current)) {
        event.preventDefault();
        last.focus();
      }
    } else if (!current || current === last || !drawerRef.current.contains(current)) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleTabListKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!isOpen || !activeTab) return;
    const currentIdx = TAB_ORDER.indexOf(activeTab);
    if (currentIdx === -1) return;
    let nextTab: ReaderDrawerTab | null = null;
    if (event.key === "ArrowRight") {
      nextTab = TAB_ORDER[(currentIdx + 1) % TAB_ORDER.length];
    } else if (event.key === "ArrowLeft") {
      nextTab = TAB_ORDER[(currentIdx - 1 + TAB_ORDER.length) % TAB_ORDER.length];
    } else if (event.key === "Home") {
      nextTab = TAB_ORDER[0];
    } else if (event.key === "End") {
      nextTab = TAB_ORDER[TAB_ORDER.length - 1];
    }
    if (!nextTab) return;
    event.preventDefault();
    onSelectTab(nextTab);
    tabRefs.current[nextTab]?.focus();
  };

  const tabSpecs: ReadonlyArray<{ key: ReaderDrawerTab; label: string }> = [
    {
      key: "transcript",
      label: isTextDocument
        ? zhReader
          ? "原始全文"
          : "Source text"
        : zhReader
          ? "原始字幕"
          : "Transcript",
    },
    {
      key: "evidence",
      label: zhReader ? `原话证据 (${evidenceCount})` : `Evidence (${evidenceCount})`,
    },
    {
      key: "history",
      label: zhReader ? `处理记录 (${historyCount})` : `History (${historyCount})`,
    },
  ];

  return (
    <>
      {isOpen ? (
        <div className="reader-ref-scrim" aria-hidden="true" onClick={onClose} />
      ) : null}
      <aside
        ref={drawerRef}
        className={`reader-ref-drawer${isOpen ? " is-open" : ""}`}
        role={isOpen ? "dialog" : undefined}
        aria-modal={isOpen ? "true" : undefined}
        aria-labelledby={isOpen ? "reader-ref-drawer-title" : undefined}
        aria-label={
          !isOpen
            ? zhReader
              ? "原文与溯源资料抽屉"
              : "Source transcript & evidence drawer"
            : undefined
        }
        onKeyDown={handleDrawerKeyDown}
      >
        <div className="reader-ref-drawer-head">
          <div className="reader-ref-drawer-title-group">
            <h2 id="reader-ref-drawer-title" className="reader-ref-drawer-title">
              {zhReader ? "原文与溯源资料" : "Reference drawer"}
            </h2>
            <div
              className="segmented reader-ref-tabs"
              role="tablist"
              aria-label={zhReader ? "辅助资料分类" : "Reference sections"}
              onKeyDown={handleTabListKeyDown}
            >
              {tabSpecs.map(({ key: tabKey, label }) => {
                const selected = activeTab === tabKey;
                return (
                  <button
                    key={tabKey}
                    ref={(node) => {
                      tabRefs.current[tabKey] = node;
                    }}
                    id={`reader-tab-${tabKey}`}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    aria-controls={`reader-panel-${tabKey}`}
                    tabIndex={isOpen ? (selected ? 0 : -1) : -1}
                    className={selected ? "active" : ""}
                    onClick={() => onSelectTab(tabKey)}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
          <button
            type="button"
            className="button button-ghost button-small"
            tabIndex={isOpen ? 0 : -1}
            onClick={onClose}
          >
            {zhReader ? "关闭 (Esc)" : "Close (Esc)"}
          </button>
        </div>
        <div className="reader-ref-drawer-body">
          <div
            id="reader-panel-evidence"
            role={isOpen ? "tabpanel" : undefined}
            aria-labelledby={isOpen ? "reader-tab-evidence" : undefined}
            hidden={isOpen && activeTab !== "evidence"}
            className={isOpen && activeTab !== "evidence" ? "reader-ref-pane-inactive" : "reader-ref-pane"}
          >
            {evidencePane}
          </div>
          <div
            id="reader-panel-transcript"
            role={isOpen ? "tabpanel" : undefined}
            aria-labelledby={isOpen ? "reader-tab-transcript" : undefined}
            hidden={isOpen && activeTab !== "transcript"}
            className={isOpen && activeTab !== "transcript" ? "reader-ref-pane-inactive" : "reader-ref-pane"}
          >
            {transcriptPane}
          </div>
          <div
            id="reader-panel-history"
            role={isOpen ? "tabpanel" : undefined}
            aria-labelledby={isOpen ? "reader-tab-history" : undefined}
            hidden={isOpen && activeTab !== "history"}
            className={isOpen && activeTab !== "history" ? "reader-ref-pane-inactive" : "reader-ref-pane"}
          >
            {historyPane}
          </div>
        </div>
      </aside>
    </>
  );
}
