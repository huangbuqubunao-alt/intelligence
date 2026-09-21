import { useState } from "react";

type FirstRunOnboardingProps = {
  onAddFollowing: () => void;
};

const steps = 3;

export function FirstRunOnboarding({ onAddFollowing }: FirstRunOnboardingProps) {
  const [step, setStep] = useState(0);

  return (
    <section className="onboarding-panel" aria-labelledby="onboarding-title">
      <div className="onboarding-progress" aria-label={`Onboarding step ${step + 1} of ${steps}`}>
        <span style={{ width: `${((step + 1) / steps) * 100}%` }} />
      </div>

      {step === 0 && (
        <div className="onboarding-step">
          <p className="eyebrow">FIRST RUN · 1 / 3</p>
          <h2 id="onboarding-title">Turn what you follow into traceable knowledge.</h2>
          <p className="onboarding-lede">
            Intelligence follows selected sources, keeps the original evidence reachable, and turns useful changes into revisable knowledge.
          </p>
          <div className="onboarding-value-grid">
            <article><strong>Following</strong><p>Choose what should be watched over time.</p></article>
            <article><strong>Content</strong><p>Read the source material and its processing state.</p></article>
            <article><strong>Intelligence</strong><p>Keep only evidence-linked judgments worth revisiting.</p></article>
          </div>
          <div className="onboarding-actions">
            <button className="button button-primary" onClick={() => setStep(1)}>Continue</button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="onboarding-step">
          <p className="eyebrow">FIRST RUN · 2 / 3</p>
          <h2 id="onboarding-title">Start with the recommended local-first policy.</h2>
          <div className="semantic-state state-neutral onboarding-policy">
            <strong>Recommended</strong>
            <p>Use local capability first. Never make a paid cloud call unless you explicitly opt in.</p>
            <p>If the available local model is not reliable enough, processing pauses and explains why instead of silently falling back.</p>
          </div>

          <div className="sample-experience" aria-label="Synthetic sample experience">
            <div className="sample-heading">
              <div>
                <span className="sample-badge">SYNTHETIC SAMPLE</span>
                <h3>See the knowledge chain before adding real data</h3>
              </div>
              <small>UI-only example · not written to your library · no network or model call</small>
            </div>
            <ol className="sample-chain">
              <li><span>Content</span><strong>How a small team reduced agent evaluation drift</strong></li>
              <li><span>Summary</span><strong>Version the evaluation baseline before changing prompts or model settings.</strong></li>
              <li><span>Evidence · supporting</span><strong>“We froze the baseline suite before each prompt revision.” · synthetic 02:14–02:41</strong></li>
              <li><span>Intelligence</span><strong>Evaluation baselines should be versioned before prompt changes.</strong></li>
              <li><span>Topic</span><strong>Agent evaluation practice</strong></li>
            </ol>
          </div>

          <div className="onboarding-actions">
            <button className="button button-ghost" onClick={() => setStep(0)}>Back</button>
            <button className="button button-primary" onClick={() => setStep(2)}>Continue</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="onboarding-step">
          <p className="eyebrow">FIRST RUN · 3 / 3</p>
          <h2 id="onboarding-title">Add your first Following.</h2>
          <p className="onboarding-lede">
            Start with a public YouTube channel or source. Adding it uses the existing production Following configuration path.
          </p>
          <div className="semantic-state state-neutral">
            <strong>Runtime qualification is separate.</strong>
            <p>
              This setup does not claim that real transcript processing or a local analysis model is already qualified. If runtime processing is unavailable, the app must stay honest and keep your configuration unchanged.
            </p>
          </div>
          <div className="onboarding-actions">
            <button className="button button-ghost" onClick={() => setStep(1)}>Back</button>
            <button className="button button-primary" onClick={onAddFollowing}>Add first Following</button>
          </div>
        </div>
      )}
    </section>
  );
}
