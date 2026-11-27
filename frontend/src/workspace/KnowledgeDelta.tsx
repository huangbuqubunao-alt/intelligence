import { useEffect, useState } from "react";
import { api } from "../api/client";
import { readAllPersonalNotes } from "./personalNotes";
import { buildWeeklyReviewMarkdown, downloadMarkdownText } from "./weeklyReviewExport";
import { useUiLanguage } from "./uiLanguage";

export type DeltaTarget = { kind: "content" | "intelligence" | "topic" | "source"; id: string };
type DeltaKind = "content_completed" | "intelligence_added" | "intelligence_revised" | "topic_updated" | "source_health";
type DeltaFacts = {
  revision_count?: number | null;
  evidence_before?: number | null;
  evidence_after?: number | null;
  evidence_set_changed?: boolean | null;
  state_before?: string | null;
  state_after?: string | null;
  state_changed_at?: string | null;
  topic_event_count?: number | null;
  failure_count?: number | null;
};
type DeltaItem = {
  id: string; kind: DeltaKind; label: string; title: string | null;
  target: DeltaTarget; occurred_at: string; facts: DeltaFacts;
};
export type KnowledgeDeltaProjection = {
  window_start: string; window_end: string; timezone: string;
  status: "available" | "partial" | "unavailable"; detail_limit: number;
  categories: { kind: DeltaKind; status: "available" | "unavailable"; count: number | null; items: DeltaItem[] }[];
};

const categoryLabels: Record<DeltaKind, string> = {
  content_completed: "Completed Content", intelligence_added: "New Intelligence",
  intelligence_revised: "Revised Intelligence", topic_updated: "Topics with new material",
  source_health: "Source health changes",
};
const targetLabels = { content: "Open Content", intelligence: "Open Intelligence", topic: "Open Topic", source: "Open Following" };
const fallbackLabels = { content: "Content", intelligence: "Intelligence", topic: "Topic", source: "Source name unavailable" };

export function KnowledgeDelta({ refresh, onOpen }: { refresh: number; onOpen: (target: DeltaTarget) => void }) {
  const { language, t } = useUiLanguage();
  const separator = language === "zh-CN" ? "：" : ": ";
  const [delta, setDelta] = useState<KnowledgeDeltaProjection | null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  useEffect(() => {
    if (!exportNotice) return undefined;
    const timer = window.setTimeout(() => setExportNotice(null), 2600);
    return () => window.clearTimeout(timer);
  }, [exportNotice]);
  useEffect(() => {
    let alive = true;
    setDelta(null);
    setFailed(false);
    api<{ knowledge_delta: KnowledgeDeltaProjection }>("/knowledge-delta")
      .then(result => { if (alive) setDelta(result.knowledge_delta); })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [refresh, retry]);
  const unavailable = failed || delta?.status === "unavailable";
  const date = (value: string) => new Intl.DateTimeFormat(language, {
    timeZone: delta?.timezone, year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(new Date(value));
  const empty = delta?.status === "available" && delta.categories.every(category => category.count === 0);
  const handleExportWeeklyReview = () => {
    if (!delta || unavailable || empty) return;
    const zh = language === "zh-CN";
    const result = buildWeeklyReviewMarkdown(delta, {
      zh,
      personalNotes: readAllPersonalNotes(),
    });
    downloadMarkdownText(result.filename, result.markdown);
    setExportNotice(
      zh
        ? `已导出本周复盘周报 (.md · ${result.changedItemCount} 条动态 · ${result.recentNoteCount} 篇批注)。`
        : `Exported weekly review (.md · ${result.changedItemCount} updates · ${result.recentNoteCount} notes).`,
    );
  };
  return (
    <section className="panel knowledge-delta" aria-labelledby="knowledge-delta-heading" aria-busy={!delta && !failed}>
      <div className="panel-heading">
        <h2 id="knowledge-delta-heading">{t("What changed in the last 7 days?")}</h2>
        {delta && !unavailable && !empty ? (
          <button
            type="button"
            className="button button-ghost button-small delta-export-btn"
            onClick={handleExportWeeklyReview}
          >
            {language === "zh-CN" ? "导出周报 (.md)" : "Export weekly review (.md)"}
          </button>
        ) : null}
      </div>
      {exportNotice ? (
        <p className="semantic-state state-neutral" role="status">
          {exportNotice}
        </p>
      ) : null}
      {delta && <p className="delta-window">{date(delta.window_start)} – {date(delta.window_end)} · {delta.timezone}</p>}
      {!delta && !failed && <p role="status" className="hint">{t("Checking recent changes…")}</p>}
      {unavailable && <p role="alert" className="hint">{t("Recent changes are unavailable. Try again shortly.")}</p>}
      {delta?.status === "partial" && <p role="alert" className="hint">{t("Some changes could not be checked. Counts below cover available sources only.")}</p>}
      {(unavailable || delta?.status === "partial") && <button type="button" className="button button-ghost" onClick={() => setRetry(value => value + 1)}>{t("Try again")}</button>}
      {empty && <p className="delta-empty">{t("No meaningful knowledge changes in the last 7 days.")}</p>}
      {delta && !unavailable && !empty && <>
        <dl className="delta-counts">
          {delta.categories
            .filter(category => category.count === null || category.count > 0)
            .map(category => <div key={category.kind}>
              <dt>{t(categoryLabels[category.kind])}</dt>
              <dd>{category.count === null ? t("Unavailable") : category.count}</dd>
            </div>)}
        </dl>
        <div className="delta-groups">
          {delta.categories.filter(category => category.items.length > 0).map(category => <div key={category.kind}>
            <h3>{t(categoryLabels[category.kind])}</h3>
            <ul className="delta-items">
              {category.items.slice(0, 2).map(item => <li key={item.id}>
                <div className="delta-item-top">
                  <strong>{item.title || t(fallbackLabels[item.target.kind])}</strong>
                  <time dateTime={item.occurred_at}>{date(item.occurred_at)}</time>
                </div>
                <p className="delta-facts">
                  <span>{t(item.label)}</span>
                  {Boolean(item.facts.revision_count) && <span>{t("Revisions in this window")}{separator}{item.facts.revision_count}</span>}
                  {item.facts.evidence_set_changed && <span>{t("Evidence set changed")}{separator}{item.facts.evidence_before} → {item.facts.evidence_after}</span>}
                  {item.facts.state_after && <span>{t("Recorded state")}{separator}{t(item.facts.state_before ?? "Unknown")} → {t(item.facts.state_after)}</span>}
                  {item.facts.topic_event_count != null && <span>{t("Recorded material changes")}{separator}{item.facts.topic_event_count}</span>}
                  {item.facts.failure_count != null && <span>{t("Blocked source checks")}{separator}{item.facts.failure_count}</span>}
                </p>
                <button type="button" className="button button-ghost delta-open"
                  aria-label={`${t(targetLabels[item.target.kind])}: ${item.title || t(fallbackLabels[item.target.kind])}`}
                  onClick={() => onOpen(item.target)}>{t(targetLabels[item.target.kind])}</button>
              </li>)}
            </ul>
            {(category.count ?? 0) > category.items.length && <p className="delta-more">
              {t("Showing")} {Math.min(2, category.items.length)} {t("of")} {category.count} · {t("Open the related page for more.")}
            </p>}
          </div>)}
        </div>
      </>}
    </section>
  );
}
