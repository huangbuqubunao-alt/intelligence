import { useEffect, useRef, useState } from "react";
import { BigModelSettings } from "./BigModelSettings";
import { api, post, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type Credential = { configured: boolean; source: string };

function moonshotContentReturn(): string | null {
  const target = new URLSearchParams(location.hash.split("?")[1] ?? "").get("return");
  return target && /^#Content\/[^/?#]+(?:\/Evidence\/[^/?#]+)?$/.test(target) && !/[\p{Cc}\p{Cs}]/u.test(target) ? target : null;
}

export function ModelSettings({ credential, preference, onSaved, message, setMessage }: {
  credential?: Credential;
  preference?: { desired_provider: string | null; desired_model: string | null };
  onSaved: () => void;
  message: string;
  setMessage: (value: string) => void;
}) {
  const { t } = useUiLanguage();
  const [editor, setEditor] = useState<"bigmodel" | "moonshot" | null>(null);
  const panel = useRef<HTMLElement>(null);
  const moonshotPanel = useRef<HTMLDetailsElement>(null);
  const [returnHash, setReturnHash] = useState(moonshotContentReturn);
  const pending = useRef(false);
  const selectEditor = (next: "bigmodel" | "moonshot" | null) => {
    setKey(""); setConfirmed(false); setEditor(next);
    if (next === "moonshot") onSaved();
  };
  const [models, setModels] = useState<{ model: string }[]>([]);
  const [candidate, setCandidate] = useState(preference?.desired_model ?? "");
  const [key, setKey] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reachable, setReachable] = useState(false);
  const scan = async () => {
    try {
      const result = await api<{ models: { model: string }[]; connection: string }>("/settings/local-models");
      setModels(result.models ?? []);
      setReachable(result.connection === "REACHABLE");
    } catch { setModels([]); setReachable(false); }
  };
  useEffect(() => { void scan(); }, []);
  useEffect(() => {
    const clear = () => {
      setKey(""); setConfirmed(false);
      setReturnHash(moonshotContentReturn());
      const moonshot = /^#Settings\/models\/moonshot(?:\?return=[^#]+)?$/.test(location.hash);
      setEditor(moonshot ? "moonshot" : location.hash.startsWith("#Settings/models/bigmodel") ? "bigmodel" : null);
      if (moonshot) {
        onSaved();
        const element = moonshotPanel.current;
        let ancestor = element?.parentElement?.closest("details");
        while (ancestor) { ancestor.open = true; ancestor = ancestor.parentElement?.closest("details"); }
        element?.scrollIntoView?.({ block: "start" }); element?.focus({ preventScroll: true });
      }
    };
    clear();
    const parents: HTMLDetailsElement[] = [];
    let parent = panel.current?.parentElement?.closest("details");
    while (parent) { parents.push(parent); parent = parent.parentElement?.closest("details"); }
    const folded = () => {
      if (parents.some(element => !element.open)) { setKey(""); setConfirmed(false); setEditor(null); }
    };
    parents.forEach(element => element.addEventListener("toggle", folded));
    window.addEventListener("hashchange", clear);
    return () => {
      window.removeEventListener("hashchange", clear);
      parents.forEach(element => element.removeEventListener("toggle", folded));
    };
  }, []);
  const run = async (action: "candidate" | "save" | "delete") => {
    if (pending.current) return;
    pending.current = true; setBusy(true); setMessage("");
    try {
      if (action === "candidate") {
        await put("/settings/model-preference", { provider: "Local", model: candidate });
        setMessage(t("Candidate preference saved. Configuration does not qualify or activate a model."));
      } else if (action === "save") {
        await put("/settings/cloud-credential", { credential: key });
        setKey("");
        setMessage(t("Credential saved in macOS Keychain. Every cloud execution still needs separate consent."));
      } else {
        await post("/settings/cloud-credential/delete", { confirm: "DELETE" });
        setConfirmed(false);
        setMessage(t("Keychain credential deleted. Any environment credential is unchanged."));
      }
      onSaved();
    } catch {
      setMessage(t("Configuration could not be saved. Check the system credential store or try again."));
    } finally { pending.current = false; setBusy(false); }
  };
  return <section ref={panel} className="panel" aria-label={t("Model configuration")}>
    <h2>{t("Model configuration")}</h2>
    <p className="hint">{t("Configured, reachable, qualified and production eligible are separate states. Settings cannot qualify a model.")}</p>
    <details><summary>{t("Experimental candidate preferences")}</summary>
    <h3>{t("Local model candidates")}</h3>
    <p>{t(reachable ? "Local model discovery is reachable." : "Local model discovery is unavailable. Existing library data remains readable.")}</p>
    <label className="field">{t("Discovered candidate")}
      <select aria-label={t("Discovered candidate")} value={candidate} onChange={event => setCandidate(event.target.value)}>
        <option value="">{t("Choose a discovered model")}</option>
        {candidate && !models.some(model => model.model === candidate) ? <option value={candidate}>{candidate}</option> : null}
        {models.map(model => <option key={model.model} value={model.model}>{model.model}</option>)}
      </select>
    </label>
    <div className="button-row">
      <button type="button" disabled={busy} onClick={() => void scan()}>{t("Rescan local models")}</button>
      <button type="button" disabled={busy || !models.some(model => model.model === candidate)} onClick={() => void run("candidate")}>{t("Save candidate preference")}</button>
    </div>
    <p className="hint">{t("This preference changes neither the configured Scoring/Summary model nor reviewed Deep Analysis qualification.")}</p>
    </details>
    <p className="hint">{t("Choose which service's key to edit. This does not change the model used for execution.")}</p>
    <BigModelSettings selected={editor === "bigmodel"} onSelectionChange={open => selectEditor(open ? "bigmodel" : null)} />
    <details id="moonshot-settings" ref={moonshotPanel} tabIndex={-1} open={editor === "moonshot"} onToggle={event => {
      if (event.currentTarget.open !== (editor === "moonshot")) selectEditor(event.currentTarget.open ? "moonshot" : null);
    }}>
    <summary onClick={event => { event.preventDefault(); selectEditor(editor === "moonshot" ? null : "moonshot"); }}>{t("Kimi / Moonshot API credential setup")}</summary>
    {editor === "moonshot" && <>
    <h3>{t("Cloud Intelligence credential")}</h3>
    <p>Kimi / Moonshot API · <span>{t("Public YouTube Content only")}</span></p>
    <p className="hint">{t("This provider key does not select or activate an execution model. Cloud Intelligence still requires a qualified model, budget and separate authorization.")}</p>
    <p>{t(credential?.source === "KEYCHAIN" ? "Configured in macOS Keychain" : credential?.source === "ENVIRONMENT" ? "Using development environment variable" : credential?.source === "UNAVAILABLE" ? "System credential store is unavailable." : "Not configured")}</p>
    <label className="field">{t("Moonshot API key")}
      <input id="moonshot-api-key" name="moonshot-api-key" type="password" aria-label={t("Moonshot API key")} disabled={busy} value={key} onChange={event => setKey(event.target.value)} autoComplete="off" spellCheck={false} />
    </label>
    <button type="button" disabled={busy || !key.trim()} onClick={() => void run("save")}>{t("Save Moonshot key securely")}</button>
    {credential?.source === "KEYCHAIN" ? <>
      <label className="credential-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{t("Confirm Moonshot key deletion")}</label>
      <button type="button" disabled={busy || !confirmed} onClick={() => void run("delete")}>{t("Delete Moonshot key")}</button>
    </> : null}
    <p className="hint">{t("Saving a credential does not call a provider, prove availability, qualify Deep Analysis or authorize paid work.")}</p>
    {message ? <p role="status">{message}</p> : null}
    {returnHash && <a className="button button-secondary" href={returnHash}>{t("Back to Content")}</a>}
    </>}
    </details>
  </section>;
}
