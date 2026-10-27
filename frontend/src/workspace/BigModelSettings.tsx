import { useEffect, useRef, useState } from "react";
import { api, post, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type CandidateStatus = {
  provider: "zhipu_bigmodel"; model: "glm-4.7-flash";
  configured: boolean; source: "NONE" | "KEYCHAIN" | "UNAVAILABLE";
  qualification: "NOT_VERIFIED"; budget: "CLOSED";
};
const endpoint = "/settings/bigmodel-credential";
function validStatus(value: unknown): value is CandidateStatus {
  if (!value || typeof value !== "object") return false;
  const status = value as Partial<CandidateStatus>;
  return status.provider === "zhipu_bigmodel" && status.model === "glm-4.7-flash"
    && typeof status.configured === "boolean" && ["NONE", "KEYCHAIN", "UNAVAILABLE"].includes(status.source ?? "")
    && status.configured === (status.source === "KEYCHAIN") && status.qualification === "NOT_VERIFIED" && status.budget === "CLOSED";
}
function sendableCredential(value: string) {
  return value.length > 0 && value.length <= 2048 && !/[^\x21-\x7e]/.test(value);
}
function contentReturn(): string | null {
  const target = new URLSearchParams(location.hash.split("?")[1] ?? "").get("return");
  return target && /^#Content\/[^/?#]+(?:\/Evidence\/[^/?#]+)?$/.test(target) && !/[\p{Cc}\p{Cs}]/u.test(target) ? target : null;
}
export function bigModelSettingsHref(returnHash = location.hash) {
  return `#Settings/models/bigmodel${returnHash.startsWith("#Content/") ? `?return=${encodeURIComponent(returnHash)}` : ""}`;
}

export function BigModelSettings({ onSelected }: { onSelected?: () => void }) {
  const { t } = useUiLanguage();
  const [active, setActive] = useState(false);
  const [status, setStatus] = useState<CandidateStatus>();
  const [key, setKey] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [message, setMessage] = useState("");
  const [returnHash, setReturnHash] = useState(contentReturn);
  const panel = useRef<HTMLDetailsElement>(null);
  const mounted = useRef(true);
  const pending = useRef(false);
  const read = async () => {
    if (pending.current) return;
    pending.current = true; setBusy(true);
    try {
      const value = await api<unknown>(endpoint);
      if (!validStatus(value)) throw new Error("Invalid candidate status");
      if (mounted.current) { setStatus(value); setError(false); }
    } catch { if (mounted.current) { setStatus(undefined); setError(true); } }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  };
  useEffect(() => {
    mounted.current = true;
    const navigate = () => {
      setKey(""); setConfirmed(false); setMessage(""); setReturnHash(contentReturn());
      if (!location.hash.startsWith("#Settings/models/bigmodel")) return;
      const element = panel.current;
      if (!element) return;
      setActive(true); element.open = true;
      const parent = element.parentElement?.closest("details");
      if (parent) parent.open = true;
      element.scrollIntoView?.({ block: "start" }); element.focus({ preventScroll: true });
    };
    navigate();
    // Native toggle does not bubble: each enclosing disclosure must clear a
    // password that remains mounted when that disclosure is folded.
    const parents: HTMLDetailsElement[] = [];
    let parent = panel.current?.parentElement?.closest("details");
    while (parent) { parents.push(parent); parent = parent.parentElement?.closest("details"); }
    const clearHiddenDraft = () => {
      if (parents.some(element => !element.open)) { setKey(""); setConfirmed(false); }
    };
    parents.forEach(element => element.addEventListener("toggle", clearHiddenDraft));
    window.addEventListener("hashchange", navigate);
    return () => {
      mounted.current = false; window.removeEventListener("hashchange", navigate);
      parents.forEach(element => element.removeEventListener("toggle", clearHiddenDraft));
    };
  }, []);
  useEffect(() => { if (active) void read(); }, [active]);
  const mutate = async (action: "save" | "delete") => {
    if (pending.current || !status || (action === "delete" && !confirmed) || (action === "save" && !sendableCredential(key))) return;
    pending.current = true; setBusy(true); setError(false); setMessage("");
    try {
      const value = action === "save"
        ? await put<unknown>(endpoint, { credential: key })
        : await post<unknown>(`${endpoint}/delete`, { confirm: "DELETE" });
      if (!validStatus(value) || value.configured !== (action === "save")) throw new Error("Unverified credential change");
      if (mounted.current) {
        setStatus(value); setKey(""); setConfirmed(false);
        setMessage(action === "save" ? "BigModel key saved. No model was run; quality and account eligibility remain unverified." : "BigModel key deleted. Other providers and existing Content are unchanged.");
      }
    } catch { if (mounted.current) setError(true); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  };
  const invalidKey = key.length > 0 && !sendableCredential(key);
  return <details id="bigmodel-settings" ref={panel} tabIndex={-1} onToggle={event => {
    if (event.currentTarget.open) { setActive(true); onSelected?.(); }
    else { setKey(""); setConfirmed(false); }
  }}>
    <summary>{t("BigModel GLM-4.7-Flash candidate setup")}</summary>
    <h3>{t("Optional cloud Intelligence candidate")}</h3>
    <p>BigModel · GLM-4.7-Flash</p>
    <p>{t("Quality not verified · Execution closed")}</p>
    <p className="hint">{t("The official price currently lists this exact model as free. Account entitlement, limits, connectivity, quality and actual billing are unverified. Prices may change. No paid model fallback is enabled.")}</p>
    <p className="hint">{t("Cloud requests would send selected text to BigModel. Its privacy policy allows necessary retention and anonymized service improvement. Saving a key uploads no Content and authorizes no request.")}</p>
    <p><a href="https://bigmodel.cn" target="_blank" rel="noreferrer">{t("BigModel official account and API keys")}</a> · <a href="https://docs.bigmodel.cn/cn/terms/privacy-policy" target="_blank" rel="noreferrer">{t("BigModel privacy policy")}</a></p>
    <p role="status">{t(status?.source === "KEYCHAIN" ? "Configured in macOS Keychain" : status?.source === "NONE" ? "Not configured" : status?.source === "UNAVAILABLE" ? "System credential store is unavailable." : "Reading BigModel key status…")}</p>
    <form onSubmit={event => { event.preventDefault(); void mutate("save"); }}>
      <label className="field">{t("BigModel API key")}<input type="password" value={key} onChange={event => setKey(event.target.value)} disabled={busy} autoComplete="off" spellCheck={false} maxLength={2048} aria-invalid={invalidKey} aria-describedby={invalidKey ? "bigmodel-key-format" : undefined} /></label>
      {invalidKey && <p id="bigmodel-key-format" className="form-error" role="alert">{t("This key contains unsupported characters or is too long. Copy the full API key again from BigModel, without spaces.")}</p>}
      <button className="button button-secondary" disabled={busy || !status || !sendableCredential(key)}>{t("Save BigModel key securely")}</button>
    </form>
    {status?.source === "KEYCHAIN" && <>
      <label className="credential-confirm"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />{t("Confirm BigModel key deletion")}</label>
      <button type="button" className="button button-secondary" disabled={busy || !confirmed} onClick={() => void mutate("delete")}>{t("Delete BigModel key")}</button>
    </>}
    <button type="button" className="button button-ghost" disabled={busy} onClick={() => void read()}>{t("Read BigModel key status")}</button>
    {error && <p className="form-error" role="alert">{t("BigModel key settings could not be verified. Read the status before retrying; check macOS Keychain access. No model request was sent.")}</p>}
    {message && <p role="status">{t(message)}</p>}
    <p className="hint">{t("This credential is separate from Moonshot. It does not change local transcription, Summary or model qualification. Keys are excluded from backups.")}</p>
    {returnHash && <a className="button button-secondary" href={returnHash}>{t("Back to Content")}</a>}
  </details>;
}
