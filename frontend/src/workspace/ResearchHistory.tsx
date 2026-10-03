import { useEffect, useState } from "react";
import { api, ApiRequestError } from "../api/client";
import { ResearchHistoryPage, researchErrorCopy } from "./ResearchTypes";
import { useUiLanguage } from "./uiLanguage";

export function ResearchHistory({ researchId, onOpen }: {
  researchId: string; onOpen: (revisionId: string) => void;
}) {
  const { t, language } = useUiLanguage();
  const [page, setPage] = useState<ResearchHistoryPage | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [previous, setPrevious] = useState<(string | null)[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setPage(null); setError(null);
    api<ResearchHistoryPage>(`/research/${encodeURIComponent(researchId)}/history${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`)
      .then(data => { if (alive) setPage(data); })
      .catch(reason => { if (alive) setError(researchErrorCopy(reason instanceof ApiRequestError ? reason.code : undefined)); });
    return () => { alive = false; };
  }, [researchId, cursor, retry]);
  return <section className="panel research-history" aria-label={t("Research History")}>
    <h2>{t("Research History")}</h2>
    <p className="hint">{t("Previous verified versions of this Research item. Each version keeps its original packet and sources.")}</p>
    {error && <p role="alert">{t(error)} <button onClick={() => setRetry(value => value + 1)}>{t("Retry")}</button></p>}
    {!page && !error && <p role="status">{t("Verifying Research History…")}</p>}
    {page && <>
      {!page.current_available && <p role="status">{t("The current version is unavailable. Verified previous versions remain readable.")}</p>}
      {page.unavailable_count > 0 && <p role="status">{t("Some versions on this page are unavailable and have been excluded because their authority could not be verified.")}</p>}
      {!page.revisions.length && <p className="empty-state">{t(page.unavailable_count || page.has_more || previous.length ? "No verified previous versions on this page." : "No previous versions yet.")}</p>}
      <ul className="research-history-list">{page.revisions.map(revision => <li className="metadata-row" key={revision.revision_id}>
        <div>
          <button className="research-source-link" onClick={() => onOpen(revision.revision_id)}>{t("Open previous version")} · {new Date(revision.assembled_at).toLocaleString(language)}</button>
          <p className="hint">{language === "zh-CN" ? `${revision.scope_count} 个内容 · ${revision.evidence_count} 条证据 · ${revision.intelligence_count} 条洞察` : `${revision.scope_count} Content items · ${revision.evidence_count} Evidence references · ${revision.intelligence_count} Intelligence interpretations`}</p>
          <p className="hint">{t("Output language")}: {revision.output_language === "en" ? "English" : t("Simplified Chinese")} · {t(revision.status === "EVIDENCE_AVAILABLE" ? "Library packet assembled" : "Insufficient local material")}</p>
        </div>
      </li>)}</ul>
      {(page.has_more || previous.length > 0) && <div className="button-row">
        <button disabled={!previous.length} onClick={() => { setCursor(previous[previous.length - 1]); setPrevious(values => values.slice(0, -1)); }}>{t("Previous")}</button>
        <button disabled={!page.has_more} onClick={() => { setPrevious(values => [...values, cursor]); setCursor(page.next_cursor); }}>{t("Next")}</button>
      </div>}
    </>}
  </section>;
}
