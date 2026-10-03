import { useEffect, useState } from "react";
import { api, post, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type Credential = { configured: boolean; source: string };

export function ModelSettings({ credential, preference, onSaved, message, setMessage }: {
  credential?: Credential;
  preference?: { desired_provider: string | null; desired_model: string | null };
  onSaved: () => void;
  message: string;
  setMessage: (value: string) => void;
}) {
  const { t } = useUiLanguage();
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
  const run = async (action: "candidate" | "save" | "delete") => {
    setBusy(true); setMessage("");
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
    } finally { setBusy(false); }
  };
  return <section className="panel" aria-label={t("Model configuration")}>
    <h2>{t("Model configuration")}</h2>
    <p className="hint">{t("Configured, reachable, qualified and production eligible are separate states. Settings cannot qualify a model.")}</p>
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
    <h3>{t("Cloud Intelligence credential")}</h3>
    <p>Moonshot / kimi-k2.6 · {t("Video Distillation only")}</p>
    <p>{t(credential?.source === "KEYCHAIN" ? "Configured in macOS Keychain" : credential?.source === "ENVIRONMENT" ? "Using development environment variable" : credential?.source === "UNAVAILABLE" ? "System credential store is unavailable." : "Not configured")}</p>
    <label className="field">{t("New API credential")}
      <input type="password" aria-label={t("New API credential")} value={key} onChange={event => setKey(event.target.value)} autoComplete="off" spellCheck={false} />
    </label>
    <button type="button" disabled={busy || !key.trim()} onClick={() => void run("save")}>{t("Save credential securely")}</button>
    {credential?.source === "KEYCHAIN" ? <>
      <label className="credential-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{t("Confirm Keychain credential deletion")}</label>
      <button type="button" disabled={busy || !confirmed} onClick={() => void run("delete")}>{t("Delete Keychain credential")}</button>
    </> : null}
    <p className="hint">{t("Saving a credential does not call a provider, prove availability, qualify Deep Analysis or authorize paid work.")}</p>
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
