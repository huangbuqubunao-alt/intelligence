import { useState } from "react";
import { useUiLanguage } from "./uiLanguage";

export const onboardingStorageKey = "intelligence.onboarding.completed.v1";
export function onboardingCompleted() {
  try { return localStorage.getItem(onboardingStorageKey) === "true"; }
  catch { return false; }
}
export function completeOnboarding() {
  try { localStorage.setItem(onboardingStorageKey, "true"); } catch { /* In-memory state still works when browser storage is unavailable. */ }
}

export function FirstRunOnboarding({ onAddFollowing, onSkip }: {
  onAddFollowing: () => void; onSkip: () => void;
}) {
  const { t } = useUiLanguage();
  const [step, setStep] = useState(0);
  return <section className="onboarding-panel" aria-labelledby="onboarding-title">
    <div className="onboarding-progress" aria-label={`${t("Onboarding step")} ${step + 1} / 3`}>
      <span style={{ width: `${((step + 1) / 3) * 100}%` }} />
    </div>
    <div className="onboarding-step">
      <p className="eyebrow">{t("FIRST RUN")} · {step + 1} / 3</p>
      <h2 id="onboarding-title">{t(["Keep up with what matters to you.", "Understand new content quickly.", "Start with a link or a local file."][step])}</h2>
      {step === 0 && <>
        <p className="onboarding-lede">{t("Follow useful sources, read clear summaries, and build knowledge over time.")}</p>
        <div className="onboarding-value-grid">
          <article><strong>{t("Keep watching")}</strong><p>{t("Follow YouTube channels from now on.")}</p></article>
          <article><strong>{t("Understand quickly")}</strong><p>{t("Save content with readable summaries and source references.")}</p></article>
          <article><strong>{t("Build knowledge")}</strong><p>{t("Choose what deserves a closer look, whenever you are ready.")}</p></article>
        </div>
      </>}
      {step === 1 && <div className="semantic-state state-neutral">
        <strong>{t("Local-first processing")}</strong>
        <p>{t("Content can be organized without cloud Intelligence. Some videos have no available captions.")}</p>
        <p>{t("Use local capability first. Never make a paid cloud call unless you explicitly opt in.")}</p>
      </div>}
      {step === 2 && <>
        <p>{t("Paste a YouTube video or channel link, import a public Bilibili video, or choose local files.")}</p>
        <p className="hint">{t("Channels follow future uploads. Video links and local files are one-time imports. Bilibili creator following is unavailable.")}</p>
      </>}
      <div className="onboarding-actions">
        <button className="button button-ghost" onClick={onSkip}>{t("Skip for now")}</button>
        {step > 0 && <button className="button button-secondary" onClick={() => setStep(step - 1)}>{t("Back")}</button>}
        <button className="button button-primary" onClick={step === 2 ? onAddFollowing : () => setStep(step + 1)}>{t(step === 2 ? "Add something" : "Continue")}</button>
      </div>
    </div>
  </section>;
}
