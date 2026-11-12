import { useEffect, useRef, useState } from "react";
import { api, ApiRequestError, put } from "../api/client";
import { pulseCelebration, VerifiedSealIcon } from "./motion";
import { useUiLanguage } from "./uiLanguage";

const V5_PROFILE_ID = "moonshot-k31-system-synthesis-v5-judgment-stream-20261112";

type Policy = { enabled: boolean; total_microunits: number; per_request_microunits: number; max_calls: number; price_hash: string };
type Price = { price_hash: string; price_date: string; profile_id: string; model: string;
  input_microcny_per_token_worst: number; output_microcny_per_token: number; billing_guarantee: false };
type Spending = { revision: number | null; policy: Policy | null; held_microunits: number | null; held_requests: number | null;
  remaining_microunits?: number; remaining_requests?: number; blocker: string | null;
  price: Price; prices?: Price[] };

const PRESETS = [
  { id: "starter", label: "Starter · CNY 5 / 3 calls", total: "5.000000", perRequest: "2.000000", calls: "3" },
  { id: "recommended", label: "Recommended · CNY 12 / 8 calls", total: "12.000000", perRequest: "2.000000", calls: "8" },
  { id: "deep", label: "Deep research · CNY 30 / 20 calls", total: "30.000000", perRequest: "2.000000", calls: "20" },
] as const;

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
    || value.prices.some(price => !object(price) || !["moonshot-k31-system-synthesis-v1-20261029", "moonshot-k31-system-synthesis-v2-attribution-20261105", "moonshot-k31-system-synthesis-v3-source-level-20261106", "moonshot-k31-system-synthesis-v4-readable-summary-20261107", V5_PROFILE_ID].includes(String(price.profile_id))
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

function profileOptionLabel(item: Price, t: (text: string) => string): string {
  return `${item.model} · ${t(
    item.profile_id === V5_PROFILE_ID ? "Judgment beyond the complete Summary"
      : item.profile_id === "moonshot-k31-system-synthesis-v4-readable-summary-20261107" ? "Complete Summary comparison"
      : item.profile_id === "moonshot-k31-system-synthesis-v3-source-level-20261106" ? "Source-level attribution"
      : item.profile_id === "moonshot-k31-system-synthesis-v2-attribution-20261105" ? "Explicit speaker attribution policy"
        : "Original synthesis policy",
  )}`;
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
  const pending = useRef(false), panel = useRef<HTMLElement>(null), saveBtnRef = useRef<HTMLButtonElement>(null);
  const refresh = async (replaceDraft: boolean) => {
    try {
      const response = await api<{ spending_policy: unknown }>("/settings/cloud-spending-policy");
      if (!valid(response.spending_policy)) throw new Error("INVALID_SPENDING_POLICY");
      const next = response.spending_policy;
      setState(next); setAcknowledged(false);
      if (replaceDraft) {
        const defaultProfile = next.policy === null && next.prices?.some(item => item.profile_id === V5_PROFILE_ID)
          ? V5_PROFILE_ID
          : next.price.profile_id;
        setSelectedProfile(defaultProfile);
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
      pulseCelebration(saveBtnRef.current);
      setMessage(t("Spending limits saved. No request was authorized or sent, and model qualification is unchanged."));
    } catch (error) {
      setAcknowledged(false);
      setMessage(t(error instanceof ApiRequestError && error.code === "CLOUD_POLICY_CONFLICT"
        ? "Spending settings changed elsewhere. Your draft is kept; reload current totals, review and save explicitly."
        : "Spending limits were not saved. Your draft is kept; check limits and retained history before trying again."));
    } finally { pending.current = false; setBusy(false); }
  };
  const verifiedPrices = prices.filter(item => item.profile_id === V5_PROFILE_ID);
  const archivedPrices = prices.filter(item => item.profile_id !== V5_PROFILE_ID);
  const policyTotal = state?.policy?.total_microunits ?? null;
  const heldMicro = state?.held_microunits ?? null;
  const usedRatio = policyTotal && policyTotal > 0 && heldMicro !== null
    ? Math.min(100, Math.round((heldMicro / policyTotal) * 100))
    : 0;

  return <section ref={panel} className="spending-settings-card" aria-label={t("Cloud spending limits")}>
    <h3>{t("Cloud spending limits")}</h3>
    <p className="hint">{t("These limits apply to kimi-k3.1-pro. In Content, open cloud review and choose that model profile. Model qualification and separate request confirmation are still required.")}</p>
    <p className="hint">{t("These cumulative limits apply only to normal system-synthesis requests. They do not reset monthly, qualify a model or authorize a request.")}</p>
    {state && <>
      <div className="quota-meter" data-testid="spending-quota-meter">
        <div className="quota-meter-stats">
          <div>
            <span>{t("Held reservation estimate")}</span>
            <strong className="tabular-nums">{state.held_microunits === null ? t("Unknown") : `CNY ${formatMicroCny(state.held_microunits)}`}</strong>
          </div>
          <div>
            <span>{t("Reserved request count")}</span>
            <strong className="tabular-nums">{state.held_requests ?? t("Unknown")}{state.policy ? ` / ${state.policy.max_calls}` : ""}</strong>
          </div>
          {state.remaining_microunits !== undefined && (
            <div>
              <span>{t("Remaining reservation capacity")}</span>
              <strong className="tabular-nums">CNY {formatMicroCny(state.remaining_microunits)} · {state.remaining_requests}</strong>
            </div>
          )}
        </div>
        {policyTotal !== null && heldMicro !== null && (
          <div className="quota-bar-track" aria-hidden="true">
            <span className="quota-bar-fill" style={{ width: `${usedRatio}%` }} />
          </div>
        )}
        <p className="hint quota-explain">{t("Why hold differs from actual billing: each call pre-locks worst-case max output (~CNY 1.1–1.8) for safety; typical Kimi token spend is ~CNY 0.1–0.2.")}</p>
      </div>
      {prices.length > 1 && <label className="field">{t("Model policy and price reference")}<select value={price?.profile_id} disabled={busy} onChange={event => { setSelectedProfile(event.target.value); setAcknowledged(false); }}>
        {verifiedPrices.length > 0 && archivedPrices.length > 0 ? <>
          <optgroup label={t("Recommended · quality verified")}>
            {verifiedPrices.map(item => <option key={item.profile_id} value={item.profile_id}>{profileOptionLabel(item, t)}</option>)}
          </optgroup>
          <optgroup label={t("Archived history · not qualified")}>
            {archivedPrices.map(item => <option key={item.profile_id} value={item.profile_id}>{profileOptionLabel(item, t)}</option>)}
          </optgroup>
        </> : prices.map(item => <option key={item.profile_id} value={item.profile_id}>{profileOptionLabel(item, t)}</option>)}
      </select></label>}
      {price?.profile_id === V5_PROFILE_ID && (
        <p className="verified-route-pill"><VerifiedSealIcon /><span>{t("Recommended verified route selected")}: {price.model}</span></p>
      )}
      <div className="preset-group" role="group" aria-label={t("Quick budget presets")}>
        <span className="preset-label">{t("Quick budget presets")}</span>
        <div className="preset-chips">
          {PRESETS.map(preset => {
            const active = total === preset.total && perRequest === preset.perRequest && count === preset.calls && enabled;
            return (
              <button
                key={preset.id}
                type="button"
                className={`button button-small preset-chip${active ? " is-active" : " button-secondary"}`}
                disabled={busy || state.revision === null}
                onClick={event => {
                  if (prices.some(item => item.profile_id === V5_PROFILE_ID) && selectedProfile !== V5_PROFILE_ID) {
                    setSelectedProfile(V5_PROFILE_ID);
                  }
                  setTotal(preset.total);
                  setPerRequest(preset.perRequest);
                  setCount(preset.calls);
                  setEnabled(true);
                  setAcknowledged(false);
                  pulseCelebration(event.currentTarget);
                }}
              >
                {t(preset.label)}
              </button>
            );
          })}
        </div>
      </div>
      <p className="hint">{t("Switching policy keeps all held reservations and requires a new price acknowledgement.")}</p>
      <p className="hint">{t("For this price reference, choose the same analysis policy in Content before preparing a cloud review.")}</p>
      <p className="hint tabular-nums">{price?.model} · {t("Frozen price reference")}: {price?.price_date} · {t("Worst-case input / output CNY per million tokens")}: {price?.input_microcny_per_token_worst} / {price?.output_microcny_per_token}</p>
      <p className="hint">{t("Reservations are conservative estimates, not a guaranteed bill or account balance. Unknown charges stay held, including after restoring a backup.")}</p>
      {state.revision === null && <p role="alert" className="form-error">{t("Spending history could not be verified. Cloud execution remains blocked.")}</p>}
      <label className="credential-confirm"><input type="checkbox" checked={enabled} disabled={busy || state.revision === null} onChange={event => setEnabled(event.target.checked)} />{t("Enable this finite spending policy")}</label>
      <div className="field-grid">
        <label className="field">{t("Cumulative reservation budget (CNY)")}<input className="tabular-nums" inputMode="decimal" value={total} disabled={busy} onChange={event => setTotal(event.target.value)} /></label>
        <label className="field">{t("Per-request reservation cap (CNY)")}<input className="tabular-nums" inputMode="decimal" value={perRequest} disabled={busy} onChange={event => setPerRequest(event.target.value)} /></label>
      </div>
      <p className="hint">{t("Use positive CNY amounts with up to six decimal places, a total no higher than CNY 10,000, and a per-request cap no higher than the total. The backend verifies all limits.")}</p>
      <label className="field">{t("Maximum cumulative requests")}<input className="tabular-nums" inputMode="numeric" value={count} disabled={busy} aria-invalid={countError} aria-describedby="cloud-spending-count-help" onChange={event => setCount(event.target.value)} /></label>
      <p id="cloud-spending-count-help" className={countError ? "form-error" : "hint"} role={countError ? "alert" : undefined}>{t("Enter a whole request count from 1 to 1000.")}</p>
      <label className="credential-confirm"><input type="checkbox" checked={acknowledged} disabled={busy || state.revision === null} onChange={event => setAcknowledged(event.target.checked)} />{t("I accept this exact profile and price reference, and understand that each request needs separate confirmation.")}</label>
      <div className="button-row"><button ref={saveBtnRef} type="button" className="button button-primary" disabled={busy || state.revision === null || !acknowledged || !total || !perRequest || !validCount} onClick={() => void save()}>{t("Save finite spending limits")}</button>
        <button type="button" className="button button-secondary" disabled={busy} onClick={() => void refresh(false)}>{t("Reload current spending totals (keep draft)")}</button></div>
    </>}
    {!state && <button type="button" className="button button-secondary" onClick={() => void refresh(false)}>{t("Retry")}</button>}
    {message && <p role="status" className="status-banner">{message}</p>}
  </section>;
}
