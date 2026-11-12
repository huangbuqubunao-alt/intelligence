import { useEffect, useRef, useState } from "react";
import { api, ApiRequestError, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type Policy = { enabled: boolean; total_microunits: number; per_request_microunits: number; max_calls: number; price_hash: string };
type Price = { price_hash: string; price_date: string; profile_id: string; model: string;
  input_microcny_per_token_worst: number; output_microcny_per_token: number; billing_guarantee: false };
type Spending = { revision: number | null; policy: Policy | null; held_microunits: number | null; held_requests: number | null;
  remaining_microunits?: number; remaining_requests?: number; blocker: string | null;
  price: Price; prices?: Price[] };
const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const integer = (value: unknown): value is number => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
function valid(value: unknown): value is Spending {
  if (!object(value) || !(value.revision === null || integer(value.revision)) || !(value.blocker === null || typeof value.blocker === "string")
    || !object(value.price) || typeof value.price.price_hash !== "string" || !/^[a-f0-9]{64}$/.test(value.price.price_hash)
    || typeof value.price.profile_id !== "string" || typeof value.price.price_date !== "string" || typeof value.price.model !== "string"
    || !integer(value.price.input_microcny_per_token_worst) || !integer(value.price.output_microcny_per_token)
    || value.price.billing_guarantee !== false || !(value.held_microunits === null || integer(value.held_microunits))
    || !(value.held_requests === null || integer(value.held_requests))) return false;
  if (value.prices !== undefined && (!Array.isArray(value.prices) || value.prices.length < 1 || value.prices.length > 5
    || value.prices.some(price => !object(price) || !["moonshot-k31-system-synthesis-v1-20261029", "moonshot-k31-system-synthesis-v2-attribution-20261105", "moonshot-k31-system-synthesis-v3-source-level-20261106", "moonshot-k31-system-synthesis-v4-readable-summary-20261107", "moonshot-k31-system-synthesis-v5-judgment-stream-20261112"].includes(String(price.profile_id))
      || typeof price.price_hash !== "string" || !/^[a-f0-9]{64}$/.test(price.price_hash) || typeof price.model !== "string"
      || typeof price.price_date !== "string" || !integer(price.input_microcny_per_token_worst) || !integer(price.output_microcny_per_token)
      || price.billing_guarantee !== false)
    || new Set(value.prices.map(price => price.profile_id)).size !== value.prices.length)) return false;
  return value.policy === null || (object(value.policy) && typeof value.policy.enabled === "boolean"
    && integer(value.policy.total_microunits) && integer(value.policy.per_request_microunits) && integer(value.policy.max_calls)
    && typeof value.policy.price_hash === "string");
}
export function formatMicroCny(value: number): string {
  return `${Math.floor(value / 1_000_000)}.${String(value % 1_000_000).padStart(6, "0")}`;
}

export function CloudSpendingSettings() {
  const { t } = useUiLanguage();
  const [state, setState] = useState<Spending | null>(null);
  const [total, setTotal] = useState(""), [perRequest, setPerRequest] = useState(""), [count, setCount] = useState("");
  const [enabled, setEnabled] = useState(false), [acknowledged, setAcknowledged] = useState(false), [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedProfile, setSelectedProfile] = useState("");
  const prices = state ? state.prices ?? [state.price] : [];
  const price = prices.find(item => item.profile_id === selectedProfile) ?? state?.price;
  const pending = useRef(false), panel = useRef<HTMLElement>(null);
  const refresh = async (replaceDraft: boolean) => {
    try {
      const response = await api<{ spending_policy: unknown }>("/settings/cloud-spending-policy");
      if (!valid(response.spending_policy)) throw new Error("INVALID_SPENDING_POLICY");
      const next = response.spending_policy;
      setState(next); setAcknowledged(false);
      if (replaceDraft) {
        setSelectedProfile(next.price.profile_id);
        setTotal(next.policy ? formatMicroCny(next.policy.total_microunits) : "");
        setPerRequest(next.policy ? formatMicroCny(next.policy.per_request_microunits) : "");
        setCount(next.policy ? String(next.policy.max_calls) : ""); setEnabled(next.policy?.enabled ?? false);
      }
    } catch { setMessage(t("Spending history could not be verified. Cloud execution remains blocked.")); }
  };
  useEffect(() => { void refresh(true); }, []);
  useEffect(() => {
    if (state && new URLSearchParams(location.hash.split("?")[1] ?? "").get("panel") === "spending") panel.current?.scrollIntoView?.({ block: "start" });
  }, [state]);
  const validCount = /^[0-9]{1,4}$/.test(count) && Number(count) >= 1 && Number(count) <= 1000;
  const countError = count !== "" && !validCount;
  const save = async () => {
    if (!validCount) { setMessage(t("Enter a whole request count from 1 to 1000.")); return; }
    if (pending.current || !state || !price || state.revision === null || !acknowledged) return;
    pending.current = true; setBusy(true); setMessage("");
    try {
      const response = await put<{ spending_policy: unknown }>("/settings/cloud-spending-policy", {
        expected_revision: state.revision, enabled, total_cny: total, per_request_cny: perRequest, max_calls: Number(count),
        accept_price_hash: price.price_hash, acknowledge: true,
      });
      if (!valid(response.spending_policy)) throw new Error("INVALID_SPENDING_POLICY");
      setState(response.spending_policy); setAcknowledged(false);
      setMessage(t("Spending limits saved. No request was authorized or sent, and model qualification is unchanged."));
    } catch (error) {
      setAcknowledged(false);
      setMessage(t(error instanceof ApiRequestError && error.code === "CLOUD_POLICY_CONFLICT"
        ? "Spending settings changed elsewhere. Your draft is kept; reload current totals, review and save explicitly."
        : "Spending limits were not saved. Your draft is kept; check limits and retained history before trying again."));
    } finally { pending.current = false; setBusy(false); }
  };
  return <section ref={panel} aria-label={t("Cloud spending limits")}>
    <h3>{t("Cloud spending limits")}</h3>
    <p>{t("These limits apply to kimi-k3.1-pro. In Content, open cloud review and choose that model profile. Model qualification and separate request confirmation are still required.")}</p>
    <p>{t("These cumulative limits apply only to normal system-synthesis requests. They do not reset monthly, qualify a model or authorize a request.")}</p>
    {state && <>
      {prices.length > 1 && <label className="field">{t("Model policy and price reference")}<select value={price?.profile_id} disabled={busy} onChange={event => { setSelectedProfile(event.target.value); setAcknowledged(false); }}>
        {prices.map(item => <option key={item.profile_id} value={item.profile_id}>{item.model} · {t(
          item.profile_id === "moonshot-k31-system-synthesis-v5-judgment-stream-20261112" ? "Judgment beyond the complete Summary"
            : item.profile_id === "moonshot-k31-system-synthesis-v4-readable-summary-20261107" ? "Complete Summary comparison"
            : item.profile_id === "moonshot-k31-system-synthesis-v3-source-level-20261106" ? "Source-level attribution"
            : item.profile_id === "moonshot-k31-system-synthesis-v2-attribution-20261105" ? "Explicit speaker attribution policy"
              : "Original synthesis policy")}</option>)}
      </select></label>}
      <p>{t("Switching policy keeps all held reservations and requires a new price acknowledgement.")}</p>
      <p>{t("For this price reference, choose the same analysis policy in Content before preparing a cloud review.")}</p>
      <p>{price?.model} · {t("Frozen price reference")}: {price?.price_date}</p>
      <p>{t("Worst-case input / output CNY per million tokens")}: {price?.input_microcny_per_token_worst} / {price?.output_microcny_per_token}</p>
      <p>{t("Reservations are conservative estimates, not a guaranteed bill or account balance. Unknown charges stay held, including after restoring a backup.")}</p>
      <p>{t("Held reservation estimate")}: {state.held_microunits === null ? t("Unknown") : `CNY ${formatMicroCny(state.held_microunits)}`} · {t("Reserved request count")}: {state.held_requests ?? t("Unknown")}</p>
      {state.remaining_microunits !== undefined && <p>{t("Remaining reservation capacity")}: CNY {formatMicroCny(state.remaining_microunits)} · {state.remaining_requests}</p>}
      {state.revision === null && <p role="alert">{t("Spending history could not be verified. Cloud execution remains blocked.")}</p>}
      <label className="credential-confirm"><input type="checkbox" checked={enabled} disabled={busy || state.revision === null} onChange={event => setEnabled(event.target.checked)} />{t("Enable this finite spending policy")}</label>
      <label className="field">{t("Cumulative reservation budget (CNY)")}<input inputMode="decimal" value={total} disabled={busy} onChange={event => setTotal(event.target.value)} /></label>
      <label className="field">{t("Per-request reservation cap (CNY)")}<input inputMode="decimal" value={perRequest} disabled={busy} onChange={event => setPerRequest(event.target.value)} /></label>
      <p>{t("Use positive CNY amounts with up to six decimal places, a total no higher than CNY 10,000, and a per-request cap no higher than the total. The backend verifies all limits.")}</p>
      <label className="field">{t("Maximum cumulative requests")}<input inputMode="numeric" value={count} disabled={busy} aria-invalid={countError} aria-describedby="cloud-spending-count-help" onChange={event => setCount(event.target.value)} /></label>
      <p id="cloud-spending-count-help" role={countError ? "alert" : undefined}>{t("Enter a whole request count from 1 to 1000.")}</p>
      <label className="credential-confirm"><input type="checkbox" checked={acknowledged} disabled={busy || state.revision === null} onChange={event => setAcknowledged(event.target.checked)} />{t("I accept this exact profile and price reference, and understand that each request needs separate confirmation.")}</label>
      <div className="button-row"><button type="button" disabled={busy || state.revision === null || !acknowledged || !total || !perRequest || !validCount} onClick={() => void save()}>{t("Save finite spending limits")}</button>
        <button type="button" disabled={busy} onClick={() => void refresh(false)}>{t("Reload current spending totals (keep draft)")}</button></div>
    </>}
    {!state && <button type="button" onClick={() => void refresh(false)}>{t("Retry")}</button>}
    {message && <p role="status">{message}</p>}
  </section>;
}
