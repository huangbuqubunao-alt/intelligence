import { useEffect, useRef, useState } from "react";
import { api, ApiRequestError, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type Candidate = { candidate_id: string; model: string; catalog_hash: string; runtime: string;
  installation: "READY" | "NOT_INSTALLED" | "IDENTITY_MISMATCH" | "RUNTIME_MISMATCH" | "UNAVAILABLE" };
type Setup = {
  status: "NOT_CONFIGURED" | "INVALID" | "APPLYING" | "APPLIED" | "ROUTE_MISMATCH";
  etag: string | null; selected_candidate_id: string | null;
  actual_route: { provider: string; model: string; profile_id: string | null } | null;
  candidates: Candidate[]; blocking_work: { video_id: string; status: string }[];
};
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
// Matches local_intelligence_catalog.CATALOG: the fixed 0.40.1, 0.40.6 and 0.40.9 choices.
const MAX_LOCAL_INTELLIGENCE_CANDIDATES = 3;
function readSetup(raw: unknown): Setup {
  if (!object(raw) || !["NOT_CONFIGURED", "INVALID", "APPLYING", "APPLIED", "ROUTE_MISMATCH"].includes(raw.status as string)
      || !(raw.etag === null || typeof raw.etag === "string" && /^[a-f0-9]{64}$/.test(raw.etag))
      || !Array.isArray(raw.candidates) || !raw.candidates.length || raw.candidates.length > MAX_LOCAL_INTELLIGENCE_CANDIDATES) throw new Error("SETTINGS_STATUS_INVALID");
  const candidates = raw.candidates;
  if (!candidates.every(c => object(c) && ["candidate_id", "model", "catalog_hash", "runtime"].every(k => typeof c[k] === "string" && c[k].length > 0)
      && ["READY", "NOT_INSTALLED", "IDENTITY_MISMATCH", "RUNTIME_MISMATCH", "UNAVAILABLE"].includes(c.installation as string))
      || new Set(candidates.map(c => c.candidate_id)).size !== candidates.length
      || !(raw.selected_candidate_id === null || candidates.some(c => c.candidate_id === raw.selected_candidate_id))
      || !(raw.actual_route === null || object(raw.actual_route) && typeof raw.actual_route.model === "string" && typeof raw.actual_route.provider === "string")
      || !Array.isArray(raw.blocking_work) || !raw.blocking_work.every(r => object(r) && typeof r.video_id === "string" && typeof r.status === "string")) throw new Error("SETTINGS_STATUS_INVALID");
  const actual = raw.actual_route;
  if (raw.status === "APPLIED" && (!object(actual) || actual.provider !== "ollama"
      || !candidates.some(c => c.candidate_id === raw.selected_candidate_id && c.model === actual.model))) throw new Error("SETTINGS_STATUS_INVALID");
  return raw as Setup;
}

export function LocalIntelligenceSetup({ pollMillis = 1000 }: { pollMillis?: number }) {
  const { t } = useUiLanguage();
  const [data, setData] = useState<Setup | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [iteration, setIteration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const dirty = useRef(false);
  const attempts = useRef(0);
  async function read(keepError = false) {
    try {
      const response = await api<{ local_intelligence: unknown }>("/settings/local-intelligence");
      const next = readSetup(response.local_intelligence);
      if (!mounted.current) return;
      setData(next);
      if (!dirty.current) setSelected(next.selected_candidate_id);
      setApplying(next.status === "APPLYING");
      if (!keepError) setError(null);
    } catch {
      if (mounted.current && !keepError) setError("Model settings could not be read. Retry the status; your selection is kept.");
    } finally {
      if (mounted.current) setIteration(n => n + 1);
    }
  }
  useEffect(() => { mounted.current = true; void read(); return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!applying) return;
    if (attempts.current++ >= 30) {
      setApplying(false);
      setError("The local service is still reconnecting. Read its status again; your selection is kept.");
      return;
    }
    const timer = setTimeout(() => void read(), pollMillis);
    return () => clearTimeout(timer);
  }, [applying, iteration, pollMillis]);
  async function save() {
    if (!data || !data.etag || !selected) return;
    setBusy(true); setError(null); attempts.current = 0;
    try {
      const response = await put<{ local_intelligence: unknown }>("/settings/local-intelligence", {
        candidate_id: selected, expected_etag: data.etag,
      });
      if (!mounted.current) return;
      const next = readSetup(response.local_intelligence);
      setData(next); setApplying(next.status === "APPLYING"); setIteration(n => n + 1);
    } catch (reason) {
      if (!mounted.current) return;
      if (reason instanceof ApiRequestError) {
        await read(true);
        setError(({ CONFIGURATION_BUSY: "Unfinished or uncertain work prevents applying this model. Open the affected Content and settle it safely; your selection is kept.",
          CONFIGURATION_CONFLICT: "Model settings changed elsewhere. Read the current status and apply your selection again.",
          MODEL_NOT_READY: "The fixed local model or runtime identity is not ready. Nothing was downloaded or loaded.",
          CONFIGURATION_APPLY_FAILED: "Model settings did not apply. Read the status before trying again; existing Content is preserved." } as Record<string, string>)[reason.code]
          ?? "Model settings did not apply. Read the status before trying again; existing Content is preserved.");
      } else {
        setError("The apply result is unknown. Checking the actual local service; the save will not be repeated automatically.");
        setApplying(true);
      }
    } finally { if (mounted.current) setBusy(false); }
  }
  return <section role="region" aria-label={t("Local Intelligence model setup")}>
    <h3>{t("Local Intelligence model setup")}</h3>
    <p>{t("This selection is only for Intelligence. It does not change the local model used for scoring and Summary.")}</p>
    {data ? <>
      <p>{t("Actual Intelligence route")}: {data.actual_route?.model ?? t("Not configured")}</p>
      {data.candidates.map(candidate => <div key={candidate.candidate_id}>
        <label><input type="radio" name="local-intelligence-candidate" value={candidate.candidate_id} checked={selected === candidate.candidate_id}
          disabled={busy || applying || candidate.installation !== "READY"}
          onChange={() => { dirty.current = true; setSelected(candidate.candidate_id); }} /> {candidate.model} · Ollama {candidate.runtime}</label>
        <p>{t(({ READY: "Installed model and runtime identity match.", NOT_INSTALLED: "The fixed Intelligence model is not installed. Install it locally, then read the status again.",
          IDENTITY_MISMATCH: "The installed model identity does not match this fixed candidate.", RUNTIME_MISMATCH: "The installed Ollama version does not match the required version shown above. This selection cannot apply.",
          UNAVAILABLE: "The local model service is unavailable. Start it locally, then read the status again." })[candidate.installation])}</p>
      </div>)}
      {data.status === "INVALID" && <p role="status">{t("Saved local model settings are invalid. Select the fixed model to repair them safely.")}</p>}
      {data.status === "ROUTE_MISMATCH" && <p role="status">{t("The saved selection has not been confirmed by the current local service. Resolve its identity status, then save and apply again.")}</p>}
      {data.status === "APPLIED" && <p role="status">{t("The Intelligence model selection is applied. Quality verification and execution eligibility are unchanged.")}</p>}
      <button type="button" className="button button-primary" disabled={busy || applying || !selected || !data.etag || !data.candidates.some(c => c.candidate_id === selected && c.installation === "READY")} onClick={() => void save()}>
        {t(busy || applying ? "Applying and reconnecting…" : "Save and apply Intelligence model")}</button>
      {data.blocking_work.length > 0 && <div><p>{t("Unfinished or uncertain Intelligence tasks")}</p><ul>{data.blocking_work.map((work, i) =>
        <li key={`${work.video_id}/${i}`}><a href={`#Content/${encodeURIComponent(work.video_id)}`}>{t("Open affected Content")}</a></li>)}</ul></div>}
    </> : null}
    <p className="hint">{t("Saving checks installed identity only. It does not download, load, run or qualify a model.")}</p>
    {(applying || busy) && <p role="status">{t("Applying and reconnecting…")}</p>}
    {error && <p role="alert">{t(error)}</p>}
    <button type="button" className="button button-secondary" disabled={busy} onClick={() => { attempts.current = 0; void read(); }}>{t("Refresh model settings")}</button>
  </section>;
}
