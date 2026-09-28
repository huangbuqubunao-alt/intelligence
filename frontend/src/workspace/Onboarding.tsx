import { useState } from "react";
import { useUiLanguage } from "./uiLanguage";

type FirstRunOnboardingProps = {
  onAddFollowing: () => void;
};

const steps = 3;

export function FirstRunOnboarding({ onAddFollowing }: FirstRunOnboardingProps) {
  const { language, t } = useUiLanguage();
  const [step, setStep] = useState(0);

  return (
    <section className="onboarding-panel" aria-labelledby="onboarding-title">
      <div className="onboarding-progress" aria-label={language === "en" ? `Onboarding step ${step + 1} of ${steps}` : `${t("Onboarding step")} ${step + 1} / ${steps}`}>
        <span style={{ width: `${((step + 1) / steps) * 100}%` }} />
      </div>

      {step === 0 && (
        <div className="onboarding-step">
          <p className="eyebrow">{t("FIRST RUN")} · 1 / 3</p>
          <h2 id="onboarding-title">{t("Turn what you follow into traceable knowledge.")}</h2>
          <p className="onboarding-lede">
            {t("Intelligence follows selected sources, keeps the original evidence reachable, and turns useful changes into revisable knowledge.")}
          </p>
          <div className="onboarding-value-grid">
            <article><strong>{t("Following")}</strong><p>{t("Choose what should be watched over time.")}</p></article>
            <article><strong>{t("Content")}</strong><p>{t("Read the source material and its processing state.")}</p></article>
            <article><strong>{t("Intelligence")}</strong><p>{t("Keep only evidence-linked judgments worth revisiting.")}</p></article>
          </div>
          <div className="onboarding-actions">
            <button className="button button-primary" onClick={() => setStep(1)}>{t("Continue")}</button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="onboarding-step">
          <p className="eyebrow">{t("FIRST RUN")} · 2 / 3</p>
          <h2 id="onboarding-title">{t("Start with the recommended local-first policy.")}</h2>
          <div className="semantic-state state-neutral onboarding-policy">
            <strong>{t("Recommended")}</strong>
            <p>{t("Use local capability first. Never make a paid cloud call unless you explicitly opt in.")}</p>
            <p>{t("If the available local model is not reliable enough, processing pauses and explains why instead of silently falling back.")}</p>
          </div>

          <div className="sample-experience" aria-label={t("Synthetic sample experience")}>
            <div className="sample-heading">
              <div>
                <span className="sample-badge">{t("SYNTHETIC SAMPLE")}</span>
                <h3>{t("See the knowledge chain before adding real data")}</h3>
              </div>
              <small>{t("UI-only example · not written to your library · no network or model call")}</small>
            </div>
            <ol className="sample-chain">
              <li><span>{t("Content")}</span><strong>{t("How a small team reduced agent evaluation drift")}</strong></li>
              <li><span>{t("Summary")}</span><strong>{t("Version the evaluation baseline before changing prompts or model settings.")}</strong></li>
              <li><span>{t("Evidence · supporting")}</span><strong>{t("“We froze the baseline suite before each prompt revision.” · synthetic 02:14–02:41")}</strong></li>
              <li><span>{t("Intelligence")}</span><strong>{t("Evaluation baselines should be versioned before prompt changes.")}</strong></li>
              <li><span>{t("Topic")}</span><strong>{t("Agent evaluation practice")}</strong></li>
            </ol>
          </div>

          <div className="onboarding-actions">
            <button className="button button-ghost" onClick={() => setStep(0)}>{t("Back")}</button>
            <button className="button button-primary" onClick={() => setStep(2)}>{t("Continue")}</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="onboarding-step">
          <p className="eyebrow">{t("FIRST RUN")} · 3 / 3</p>
          <h2 id="onboarding-title">{t("Add your first Following.")}</h2>
          <p className="onboarding-lede">
            {t("Start with a public YouTube source. Choose how many recent videos to include and add it to Following.")}
          </p>
          <div className="semantic-state state-neutral">
            <strong>{t("Local-first processing")}</strong>
            <p>
              {t("A public YouTube source is processed locally first. Getting a transcript and local summary can take a little time.")}
            </p>
            <p>
              {t("If captions, the local model, or network access are unavailable, processing pauses and explains why. It will not silently switch to a cloud model.")}
            </p>
          </div>
          <div className="onboarding-actions">
            <button className="button button-ghost" onClick={() => setStep(1)}>{t("Back")}</button>
            <button className="button button-primary" onClick={onAddFollowing}>{t("Add first Following")}</button>
          </div>
        </div>
      )}
    </section>
  );
}
