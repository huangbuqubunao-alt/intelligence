import { useEffect, useState } from "react";
import { api, ApiRequestError, post } from "../api/client";
import { ResearchHistory } from "./ResearchHistory";
import { ResearchForm } from "./ResearchForm";
import { ResearchResult } from "./ResearchResult";
import { OpenResearchSource, ResearchListing, ResearchResult as Result, researchErrorCopy } from "./ResearchTypes";
import { useUiLanguage } from "./uiLanguage";

export function Research({ onOpen }: { onOpen: OpenResearchSource }) {
  const { t, language } = useUiLanguage();
  const initialRoute = /^#Research\/([a-f0-9]{64})(?:\/history\/([a-f0-9]{64}))?$/.exec(location.hash);
  const initialId = initialRoute?.[1] ?? null;
  const [historicalId, setHistoricalId] = useState<string | null>(initialRoute?.[2] ?? null);
  const [activeId, setActiveId] = useState<string | null>(initialId);
  const [historicalIsCurrent, setHistoricalIsCurrent] = useState(false);
  const [creating, setCreating] = useState(false);
  const [listing, setListing] = useState<ResearchListing | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const followRoute = () => {
      const route = /^#Research\/([a-f0-9]{64})(?:\/history\/([a-f0-9]{64}))?$/.exec(location.hash);
      if (route && (route[1] !== activeId || (route[2] ?? null) !== historicalId)) {
        setActiveId(route[1]); setHistoricalId(route[2] ?? null); setCreating(false);
        setResult(null); setError(null);
      }
    };
    window.addEventListener("hashchange", followRoute);
    return () => window.removeEventListener("hashchange", followRoute);
  }, [activeId, historicalId]);
  useEffect(() => {
    let alive = true;
    setListing(null); setListError(null);
    api<ResearchListing>(`/research${offset ? `?offset=${offset}` : ""}`).then(data => {
      if (alive) setListing(data);
    }).catch(reason => { if (alive) setListError(researchErrorCopy(reason instanceof ApiRequestError ? reason.code : undefined)); });
    return () => { alive = false; };
  }, [revision, offset]);
  useEffect(() => {
    if (!activeId) return;
    let alive = true;
    setResult(null); setError(null);
    api<{ research: Result; is_current?: boolean }>(`/research/${encodeURIComponent(activeId)}${historicalId ? `/history/${encodeURIComponent(historicalId)}` : ""}`).then(data => {
      if (alive) { setResult(data.research); setHistoricalIsCurrent(data.is_current === true); }
    }).catch(reason => { if (alive) setError(researchErrorCopy(reason instanceof ApiRequestError ? reason.code : undefined)); });
    return () => { alive = false; };
  }, [activeId, historicalId, revision]);
  const open = (id: string) => { setHistoricalId(null); setActiveId(id); setCreating(false); location.hash = `Research/${id}`; };
  const newResearch = () => { setHistoricalId(null); setActiveId(null); setResult(null); setError(null); setCreating(true); location.hash = "Research"; };
  const run = async (question: string, contentIds: string[]) => {
    setBusy(true); setError(null);
    try {
      const data = await post<{ research: Result }>("/research", { question, content_ids: contentIds });
      open(data.research.packet.research_id);
      setRevision(value => value + 1);
    } catch (reason) { setError(researchErrorCopy(reason instanceof ApiRequestError ? reason.code : undefined)); }
    finally { setBusy(false); }
  };
  return <div className="research-stack">
    <p className="hint">{t("Research uses only your existing library. No web exploration or model call.")}</p>
    {!creating && <div className="button-row">
      <button className="button button-primary" disabled={busy} onClick={newResearch}>{t("New Research")}</button>
      {activeId && <button className="button button-secondary" disabled={busy} onClick={() => { setHistoricalId(null); setActiveId(null); setResult(null); setError(null); location.hash = "Research"; }}>{t("Current Research items")}</button>}
    </div>}
    {error && <p className="form-error" role="alert">{t(error)} <button disabled={busy} onClick={() => setRevision(value => value + 1)}>{t("Retry")}</button></p>}
    {creating && <ResearchForm busy={busy} onRun={(question, ids) => void run(question, ids)} onCancel={() => setCreating(false)} />}
    {!creating && activeId && !result && !error && <p role="status">{t("Verifying saved Research…")}</p>}
    {!creating && result && <>
      <section className="panel" aria-label={t(historicalId && !historicalIsCurrent ? "Previous Research version" : "Current Research version")}>
        <h2>{t(historicalId && !historicalIsCurrent ? "Previous Research version" : "Current Research version")}</h2>
        {historicalId && <><p className="hint">{t("Read-only original packet. Assembling again creates a new version of this Research item.")}</p>
          <button className="button button-secondary" onClick={() => open(result.packet.research_id)}>{t("Open current version")}</button></>}
      </section>
      <ResearchResult result={result} onOpen={onOpen} />
      <button className="button button-secondary" disabled={busy} onClick={() => void run(result.packet.question, result.packet.scope.map(item => item.content_id))}>{t(busy ? "Assembling library packet…" : "Assemble again")}</button>
    </>}
    {!creating && activeId && <ResearchHistory key={`${activeId}:${revision}`} researchId={activeId} onOpen={id => {
      setHistoricalId(id); setResult(null); setError(null); location.hash = `Research/${activeId}/history/${id}`;
    }} />}
    {!creating && !activeId && <section className="panel" aria-label={t("Current Research items")}>
      <h2>{t("Current Research items")}</h2>
      {listError && <p role="alert">{t(listError)} <button onClick={() => setRevision(value => value + 1)}>{t("Retry")}</button></p>}
      {!listing && !listError && <p role="status">{t("Loading Research…")}</p>}
      {listing && !listing.research.length && <p className="empty-state">{t("No Research yet. Start with a question and selected library Content.")}</p>}
      {listing && listing.total > 0 && <p className="hint">{language === "zh-CN" ? `当前显示 ${listing.research.length} 项，共 ${listing.total} 项研究。` : `Showing ${listing.research.length} of ${listing.total} Research items.`}</p>}
      {listing?.research.map(item => <article className="metadata-row" key={item.research_id}>
        <div><button className="research-source-link research-question" onClick={() => open(item.research_id)}>{item.question || t("Saved Research unavailable")}</button>
          {item.assembled_at && <p className="hint">{language === "zh-CN" ? `${item.scope_count} 个内容` : `${item.scope_count} Content items`} · {new Date(item.assembled_at).toLocaleString(language)}</p>}
          <p>{t(item.status === "EVIDENCE_AVAILABLE" ? "Library packet assembled" : item.status === "INSUFFICIENT_MATERIAL" ? "Insufficient local material" : researchErrorCopy(item.status))}</p>
        </div>
      </article>)}
      {listing && listing.total > listing.limit && <div className="button-row">
        <button disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - listing.limit))}>{t("Previous")}</button>
        <button disabled={offset + listing.limit >= listing.total} onClick={() => setOffset(value => value + listing.limit)}>{t("Next")}</button>
      </div>}
    </section>}
  </div>;
}
