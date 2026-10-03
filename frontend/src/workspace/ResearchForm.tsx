import { FormEvent, useEffect, useState } from "react";
import { api, ApiRequestError } from "../api/client";
import { researchErrorCopy, ScopeOptions } from "./ResearchTypes";
import { useUiLanguage } from "./uiLanguage";

export function ResearchForm({ busy, onRun, onCancel }: {
  busy: boolean; onRun: (question: string, contentIds: string[]) => void; onCancel: () => void;
}) {
  const { t, language } = useUiLanguage();
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<{ id: string; title: string }[]>([]);
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [options, setOptions] = useState<ScopeOptions | null>(null);
  const [scopeError, setScopeError] = useState<string | null>(null);
  const [validation, setValidation] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setOptions(null); setScopeError(null);
    api<ScopeOptions>(`/research/scope?query=${encodeURIComponent(query)}&offset=${offset}`).then(data => {
      if (alive) setOptions(data);
    }).catch(error => { if (alive) setScopeError(researchErrorCopy(error instanceof ApiRequestError ? error.code : undefined)); });
    return () => { alive = false; };
  }, [query, offset, retry]);
  const submit = (event: FormEvent) => {
    event.preventDefault(); setValidation(null);
    if (!question.trim() || question.length > 2000) return setValidation(researchErrorCopy("RESEARCH_INVALID_QUESTION"));
    if (!selected.length) return setValidation(researchErrorCopy("RESEARCH_EMPTY_SCOPE"));
    onRun(question, selected.map(item => item.id));
  };
  return <form className="panel research-form" onSubmit={submit} aria-label={t("New Research")}>
    <h2>{t("New Research")}</h2>
    <label className="field">{t("Research question")}
      <textarea autoFocus maxLength={2000} rows={3} value={question} disabled={busy} onChange={event => setQuestion(event.target.value)} />
    </label>
    <p className="hint">{t("Ask what you want to inspect or understand from your library.")}</p>
    <fieldset disabled={busy} className="research-scope-picker">
      <legend>{t("Select library Content")}</legend>
      <p className="hint">{t("Select 1–20 existing items. Research stays inside this scope.")}</p>
      <label className="field">{t("Filter Content by title or source")}
        <input type="search" maxLength={120} value={query} onChange={event => { setQuery(event.target.value); setOffset(0); }} />
      </label>
      {scopeError && <div role="alert"><p>{t(scopeError)}</p><button type="button" onClick={() => setRetry(value => value + 1)}>{t("Retry")}</button></div>}
      {!options && !scopeError && <p role="status">{t("Loading library scope…")}</p>}
      {options && <>
        {!options.content.length && <p>{t("No Content matches this filter. Add material to your library or change the filter.")}</p>}
        <div className="research-options">{options.content.map(item => <label className="research-option" key={item.content_id}>
          <input type="checkbox" checked={selected.some(value => value.id === item.content_id)} disabled={selected.length >= 20 && !selected.some(value => value.id === item.content_id)} onChange={event => {
            setSelected(values => event.target.checked ? [...values, { id: item.content_id, title: item.title || t("Untitled Content") }] : values.filter(value => value.id !== item.content_id));
          }} />
          <span>{item.title || t("Untitled Content")}<small>{item.channel_name}</small></span>
        </label>)}</div>
        <p className="hint">{language === "zh-CN" ? `当前筛选共 ${options.total} 个内容；每页最多 50 个。` : `${options.total} Content items match this filter; at most 50 per page.`}</p>
        <div className="button-row">
          <button type="button" disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 50))}>{t("Previous")}</button>
          <button type="button" disabled={offset + 50 >= options.total} onClick={() => setOffset(value => value + 50)}>{t("Next")}</button>
        </div>
      </>}
      <p>{language === "zh-CN" ? `已选择 ${selected.length} 个内容` : `${selected.length} Content items selected`}</p>
      <ul className="research-selected">{selected.map(item => <li key={item.id}>{item.title} <button type="button" onClick={() => setSelected(values => values.filter(value => value.id !== item.id))}>{t("Remove")}</button></li>)}</ul>
    </fieldset>
    {validation && <p className="form-error" role="alert">{t(validation)}</p>}
    <div className="button-row">
      <button type="submit" className="button button-primary" disabled={busy}>{t(busy ? "Assembling library packet…" : "Assemble library packet")}</button>
      <button type="button" className="button button-secondary" disabled={busy} onClick={onCancel}>{t("Cancel")}</button>
    </div>
  </form>;
}
