import { ReactNode, useEffect, useState } from "react";
import { api, ApiRequestError } from "../api/client";
import { DiffGroup, DiffRevision, OpenResearchSource, ResearchDiffProjection, researchErrorCopy } from "./ResearchTypes";
import { useUiLanguage } from "./uiLanguage";

const fieldCopy = {
  material_status: "Material status", evidence_candidates: "Matching Evidence candidates",
  intelligence_candidates: "Matching Intelligence candidates", retrieval_truncated: "Retrieval bounded",
  unresolved: "Packet limitations",
};
const valueCopy: Record<string, string> = {
  EVIDENCE_AVAILABLE: "Library packet assembled", INSUFFICIENT_MATERIAL: "Insufficient local material",
  NO_SYNTHESIS: "No model synthesis", LEXICAL_RETRIEVAL: "Word matching only",
  BOUNDED_PACKET: "Bounded packet", NO_MATCHING_EVIDENCE: "No matching Evidence",
};
const claimCopy: Record<string, string> = {
  EVIDENCE_BACKED_STATEMENT: "Evidence-backed statement", OPINION: "Attributed opinion",
  SYSTEM_INFERENCE: "System inference", PREDICTION: "Prediction", RUMOR: "Unverified rumor", FACT: "Recorded fact classification",
};
const stateCopy: Record<string, string> = { NEW: "New", PENDING_CONFIRMATION: "Pending confirmation", CONFIRMED: "Confirmed", DISPUTED: "Disputed", UPDATED: "Updated" };
const stanceCopy: Record<string, string> = { supporting: "Supporting", contradicting: "Contradicting", conditional: "Conditional" };

function Changes<T extends { id: string }>({ title, group, renderEntry }: { title: string; group: DiffGroup<T>; renderEntry: (entry: T, side: "base" | "target") => ReactNode }) {
  const { t, language } = useUiLanguage();
  return <section className="panel">
    <h3>{t(title)}</h3>
    {!group.added.length && !group.removed.length && <p>{t("No additions or removals")}</p>}
    {(["added", "removed"] as const).map(kind => group[kind].length > 0 && <div key={kind}>
      <h4>{t(kind === "added" ? "Added" : "Removed")}</h4>
      <ul className="research-diff-list">{group[kind].map(entry => <li key={entry.id}>{renderEntry(entry, kind === "added" ? "target" : "base")}</li>)}</ul>
    </div>)}
    <p className="hint">{language === "zh-CN" ? `未变：${group.unchanged_count}` : `Unchanged: ${group.unchanged_count}`}</p>
  </section>;
}

export function ResearchDiff({ researchId, baseId, targetId, onOpen, onRevision, onClose }: {
  researchId: string; baseId: string; targetId: string; onOpen: OpenResearchSource;
  onRevision: (revisionId: string) => void; onClose: () => void;
}) {
  const { t, language } = useUiLanguage();
  const [diff, setDiff] = useState<ResearchDiffProjection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setDiff(null); setError(null);
    api<{ diff: ResearchDiffProjection }>(`/research/${encodeURIComponent(researchId)}/diff?base_revision=${encodeURIComponent(baseId)}&target_revision=${encodeURIComponent(targetId)}`)
      .then(data => {
        if (!alive) return;
        if (data.diff.contract !== "research-diff-v1" || data.diff.packet_contract !== "research-lite-v1" || data.diff.research_id !== researchId || data.diff.base.revision_id !== baseId || data.diff.target.revision_id !== targetId) {
          setError(researchErrorCopy("RESEARCH_DIFF_INCOMPATIBLE_CONTRACT")); return;
        }
        setDiff(data.diff);
      }).catch(reason => { if (alive) setError(researchErrorCopy(reason instanceof ApiRequestError ? reason.code : undefined)); });
    return () => { alive = false; };
  }, [researchId, baseId, targetId, retry]);
  const value = (input: string | number | boolean | string[]): string => Array.isArray(input)
    ? input.map(item => t(valueCopy[item] || "Recorded limitation")).join(" · ")
    : typeof input === "boolean" ? t(input ? "Yes" : "No") : typeof input === "number" ? String(input) : t(valueCopy[input] || "Recorded status");
  const revision = (item: DiffRevision, label: string) => <div>
    <h3>{t(label)}</h3>
    <p>{language === "zh-CN" ? `版本 ${item.execution_number}` : `Version ${item.execution_number}`} · {new Date(item.assembled_at).toLocaleString(language)}</p>
    <button className="button button-secondary" onClick={() => onRevision(item.revision_id)}>{t(label === "Base version" ? "Open base version" : "Open target version")}</button>
  </div>;
  return <div className="research-diff" aria-label={t("Research revision comparison")}>
    <section className="panel">
      <h2>{t("Research revision comparison")}</h2>
      <button className="button button-secondary" onClick={onClose}>{t("Close comparison")}</button>
      {!diff && !error && <p role="status">{t("Verifying two Research versions…")}</p>}
      {error && <p role="alert">{t(error)} <button onClick={() => setRetry(n => n + 1)}>{t("Retry")}</button></p>}
      {diff && <>
        <p className="research-question">{diff.question}</p>
        <p>{t("Output language")}: {diff.output_language === "en" ? (language === "zh-CN" ? "英语" : "English") : t("Simplified Chinese")}</p>
        <p className="hint">{t("Direction: base → target. Added references belong to target; removed references belong to base.")}</p>
        <div className="research-diff-direction">{revision(diff.base, "Base version")}{revision(diff.target, "Target version")}</div>
        <h3>{t("Selected library scope")}</h3>
        <ul>{diff.base.scope.map(c => <li key={c.content_id}><button className="research-source-link" onClick={() => onOpen("content", c.content_id)}>{c.title || t("Untitled Content")}</button></li>)}</ul>
        <h3>{t("Comparison summary")}</h3>
        <p role="status">{diff.no_material_changes ? t("No material changes") : language === "zh-CN" ? `新增 ${diff.summary.added} · 移除 ${diff.summary.removed} · 变化 ${diff.summary.changed}` : `${diff.summary.added} added · ${diff.summary.removed} removed · ${diff.summary.changed} changed`}</p>
        <p className="hint">{t("Counts describe reference entries and packet fields, not evidence strength. This compares the two bounded stored packets.")}</p>
      </>}
    </section>
    {diff && <>
      <Changes title="Referenced Content" group={diff.content} renderEntry={entry => <button className="research-source-link" onClick={() => onOpen("content", entry.content_id)}>{entry.title || t("Untitled Content")}</button>} />
      <Changes title="Evidence references" group={diff.evidence} renderEntry={entry => <article className="evidence-item">
        <p>{entry.title || t("Untitled Content")} · {entry.provider === "LOCAL" ? t("Local") : entry.provider === "BILIBILI" ? t("Bilibili") : "YouTube"} · {entry.locator_type === "TEXT_RANGE" ? `${t("Lines")} ${entry.start_line}–${entry.end_line}` : entry.start_ms != null && entry.end_ms != null ? `${entry.start_ms / 1000}–${entry.end_ms / 1000}s` : t("Position unavailable")} · {t("Source language")}: {entry.source_language}</p>
        <blockquote>{entry.excerpt}</blockquote>
        <button className="button button-secondary" onClick={() => onOpen("content", entry.content_id, entry.evidence_id)}>{t("Open Content and Evidence")}</button>
      </article>} />
      <Changes title="Recorded interpretations / Intelligence revision references" group={diff.interpretations} renderEntry={(entry, side) => <article>
        <p className="reading-meta">{t(claimCopy[entry.claim_kind] || "Recorded interpretation")} · {t("Recorded state")}: {t(stateCopy[entry.state] || "Validation state unavailable")}</p>
        <p>{entry.conclusion}</p><p className="hint">{entry.title || t("Untitled Content")}</p>
        <p className="hint">{t("Stored Intelligence revision")}: <code>{entry.revision_id}</code></p>
        <p className="hint">{t("Opening Intelligence shows its current state. Open the Research version to inspect the stored interpretation.")}</p>
        <div className="button-row"><button className="button button-secondary" onClick={() => onOpen("intelligence", entry.intelligence_id)}>{t("Open Intelligence")}</button>
          <button className="button button-secondary" onClick={() => onRevision(side === "base" ? diff.base.revision_id : diff.target.revision_id)}>{t(side === "base" ? "Open base version" : "Open target version")}</button>
          {entry.citations.map(c => <button className="button button-secondary" key={c.evidence_id} onClick={() => onOpen("content", entry.content_id, c.evidence_id)}>{t("Evidence")} · {t(stanceCopy[c.stance || ""] || "Relation not determined")}</button>)}
        </div>
      </article>} />
      <section className="panel"><h3>{t("Packet fields")}</h3>
        {!diff.packet_changes.length && <p>{t("No changed packet fields")}</p>}
        <ul>{diff.packet_changes.map(change => <li key={change.id}>{t(fieldCopy[change.field])}: {value(change.base)} → {value(change.target)}</li>)}</ul>
      </section>
    </>}
  </div>;
}
