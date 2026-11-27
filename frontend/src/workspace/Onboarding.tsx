import { useState } from "react";
import { useUiLanguage } from "./uiLanguage";

export const onboardingStorageKey = "intelligence.onboarding.completed.v1";
export const demoOnboardingStorageKey = "intelligence.onboarding.completed.demo.v1";
export const onboardingReturnStepKey = "intelligence.onboarding.returnStep.v1";
function resolveOnboardingKey(demoMode = false) {
  return demoMode ? demoOnboardingStorageKey : onboardingStorageKey;
}
export function onboardingCompleted(demoMode = false) {
  try { return localStorage.getItem(resolveOnboardingKey(demoMode)) === "true"; }
  catch { return false; }
}
export function completeOnboarding(demoMode = false) {
  try {
    localStorage.setItem(resolveOnboardingKey(demoMode), "true");
    sessionStorage.removeItem(onboardingReturnStepKey);
  } catch { /* In-memory state still works when browser storage is unavailable. */ }
}
export function resetOnboarding(demoMode = false) {
  try {
    localStorage.removeItem(resolveOnboardingKey(demoMode));
    sessionStorage.removeItem(onboardingReturnStepKey);
  } catch { /* ignore storage errors */ }
}
export function getOnboardingReturnStep(): number | null {
  try {
    const raw = sessionStorage.getItem(onboardingReturnStepKey);
    if (raw === "0" || raw === "1" || raw === "2") return Number(raw);
  } catch { /* ignore storage errors */ }
  return null;
}
export function setOnboardingReturnStep(step: number | null) {
  try {
    if (step === null) sessionStorage.removeItem(onboardingReturnStepKey);
    else sessionStorage.setItem(onboardingReturnStepKey, String(step));
  } catch { /* ignore storage errors */ }
}

export function FirstRunOnboarding({ onAddFollowing, onSkip, initialStep = 0, onOpenSetup }: {
  onAddFollowing: () => void;
  onSkip: () => void;
  initialStep?: number;
  onOpenSetup?: (target: "models" | "transcription", step: number) => void;
}) {
  const { language, t } = useUiLanguage();
  const zh = language === "zh-CN";
  const [step, setStep] = useState(
    initialStep >= 0 && initialStep <= 2 ? initialStep : 0,
  );
  const steps = ["1. Core flow", "2. Local & privacy", "3. First import"] as const;
  return <section className="onboarding-panel" aria-labelledby="onboarding-title">
    <div className="onboarding-progress" aria-label={`${t("Onboarding step")} ${step + 1} / 3`}>
      <span style={{ width: `${((step + 1) / 3) * 100}%` }} />
    </div>
    <ol className="onboarding-stepper" aria-label={t("Onboarding steps")}>
      {steps.map((label, idx) => (
        <li key={label}>
          <button
            type="button"
            aria-current={step === idx ? "step" : undefined}
            className={step === idx ? "is-active" : step > idx ? "is-done" : undefined}
            onClick={() => setStep(idx)}
          >
            {t(label)}
          </button>
        </li>
      ))}
    </ol>
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
        <p>{t("Importing a video saves the file. Transcript, Summary and Evidence require usable source text. You can also import an existing TXT or MD transcript; no cloud service is used for local transcription.")}</p>
        <div className="button-row onboarding-setup-links">
          <a
            className="button button-secondary"
            href="#Settings/models/bigmodel"
            onClick={() => (onOpenSetup ? onOpenSetup("models", step) : onSkip())}
          >
            {t("Explore optional cloud Intelligence setup")}
          </a>
          <a
            className="button button-secondary"
            href="#Settings/transcription"
            onClick={() => (onOpenSetup ? onOpenSetup("transcription", step) : onSkip())}
          >
            {t("Set up local transcription")}
          </a>
        </div>
        <p className="hint">
          {zh
            ? "对话总结用 AI 模型；本地语音转写仅导入无字幕音视频时需要。跳去配置后可随时返回继续第 3 步。"
            : "Choose an AI summary model (local Ollama or cloud Key); local speech transcription is only needed for uncaptioned local media. Your onboarding progress is preserved when you return."}
        </p>
      </div>}
      {step === 2 && <>
        <p>{t("Paste a YouTube video or channel link, import a public Bilibili video, or choose local files.")}</p>
        <ul className="onboarding-source-list">
          <li><strong>YouTube</strong><span>{zh ? "单视频或频道关注（需当前网络可访问 YouTube）" : "Video link or channel follow (requires YouTube network access)"}</span></li>
          <li><strong>Bilibili</strong><span>{zh ? "公开 BV 视频导入（国内直连，无需 VPN）" : "Public BV video import (direct access, no VPN needed)"}</span></li>
          <li><strong>{t("Local files")}</strong><span>{zh ? "TXT/MD 笔记或本地音视频（完全离线，无需 VPN）" : "TXT, MD notes or local audio/video (100% offline)"}</span></li>
        </ul>
        <p className="hint">{t("Channels follow future uploads. Video links and local files are one-time imports. Bilibili creator following is unavailable.")}</p>
      </>}
      <div className="onboarding-actions">
        <button className="button button-ghost" onClick={onSkip}>{t("Skip for now")}</button>
        <div className="onboarding-actions-primary">
          {step > 0 && <button className="button button-secondary" onClick={() => setStep(step - 1)}>{t("Back")}</button>}
          <button className="button button-primary" onClick={step === 2 ? onAddFollowing : () => setStep(step + 1)}>{t(step === 2 ? "Add something" : "Continue")}</button>
        </div>
      </div>
    </div>
  </section>;
}
