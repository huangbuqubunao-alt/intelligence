import { flushSync } from "react-dom";

type ViewTransitionDocument = Document & {
  startViewTransition?: (updateCallback: () => void) => { finished: Promise<unknown> };
};

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  try {
    return Boolean(window.matchMedia("(prefers-reduced-motion: reduce)")?.matches);
  } catch {
    return false;
  }
}

/**
 * Reuses the native Web Platform View Transitions API (`document.startViewTransition`)
 * paired with React's `flushSync` when available and motion is allowed, falling back
 * synchronously in jsdom and older browsers.
 */
export function runViewTransition(commit: () => void): void {
  if (typeof document === "undefined" || prefersReducedMotion()) {
    commit();
    return;
  }
  const doc = document as ViewTransitionDocument;
  if (typeof doc.startViewTransition !== "function") {
    commit();
    return;
  }
  try {
    let executed = false;
    doc.startViewTransition(() => {
      executed = true;
      flushSync(commit);
    });
    if (!executed) {
      // If a browser queues the callback asynchronously, it will still run;
      // synchronous test mocks execute immediately above.
    }
  } catch {
    commit();
  }
}

/**
 * Tactile Web Animations API micro-celebration on focal user milestones
 * (e.g., saving an insight or completing a spending preset).
 */
export function pulseCelebration(element: HTMLElement | null): void {
  if (!element || prefersReducedMotion() || typeof element.animate !== "function") return;
  try {
    element.animate(
      [
        { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(67, 197, 141, 0)" },
        { transform: "scale(1.035)", boxShadow: "0 0 0 6px rgba(67, 197, 141, 0.22)" },
        { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(67, 197, 141, 0)" },
      ],
      { duration: 360, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
  } catch {
    // Ignore environments with partial WAAPI implementations.
  }
}

export type NavIconName = "Home" | "Following" | "Content" | "Intelligence" | "Topics" | "Research" | "Settings";

export function NavIcon({ name }: { name: NavIconName }) {
  const common = {
    className: "ui-icon nav-svg-icon",
    width: 16,
    height: 16,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: "false" as const,
  };
  switch (name) {
    case "Home":
      return (
        <svg {...common}>
          <rect x="2" y="2" width="5" height="5" rx="1.2" />
          <rect x="9" y="2" width="5" height="5" rx="1.2" />
          <rect x="2" y="9" width="5" height="5" rx="1.2" />
          <path d="M9.5 11.5h4M11.5 9.5v4" />
        </svg>
      );
    case "Following":
      return (
        <svg {...common}>
          <circle cx="5" cy="11" r="1.5" />
          <path d="M3.5 7.2a5.3 5.3 0 0 1 5.3 5.3" />
          <path d="M3.5 3.8a8.7 8.7 0 0 1 8.7 8.7" />
        </svg>
      );
    case "Content":
      return (
        <svg {...common}>
          <rect x="2.2" y="2.8" width="11.6" height="10.4" rx="1.8" />
          <path d="M6.6 6l3.4 2-3.4 2V6Z" />
        </svg>
      );
    case "Intelligence":
    case "Research":
      return (
        <svg {...common}>
          <path d="M8 1.8l1.7 4.5 4.5 1.7-4.5 1.7L8 14.2 6.3 9.7 1.8 8l4.5-1.7L8 1.8Z" />
        </svg>
      );
    case "Topics":
      return (
        <svg {...common}>
          <path d="M8 2.2 13.5 5 8 7.8 2.5 5 8 2.2Z" />
          <path d="M2.5 8.2 8 11l5.5-2.8" />
          <path d="M2.5 11.2 8 14l5.5-2.8" />
        </svg>
      );
    case "Settings":
      return (
        <svg {...common}>
          <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" />
          <circle cx="5.5" cy="4.5" r="1.3" fill="var(--surface)" />
          <circle cx="10.5" cy="8" r="1.3" fill="var(--surface)" />
          <circle cx="6.8" cy="11.5" r="1.3" fill="var(--surface)" />
        </svg>
      );
  }
}

export function BookmarkSparkIcon({ saved }: { saved: boolean }) {
  return (
    <svg
      className={`ui-icon bookmark-icon${saved ? " is-saved" : ""}`}
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill={saved ? "rgba(67, 197, 141, 0.22)" : "none"}
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 2.5h8a1 1 0 0 1 1 1v10l-5-2.9-5 2.9v-10a1 1 0 0 1 1-1Z" />
      {saved && <path className="icon-check-draw" d="M6 6.9l1.4 1.4 2.8-2.8" />}
    </svg>
  );
}

export function VerifiedSealIcon() {
  return (
    <svg
      className="ui-icon verified-seal-icon"
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="8" cy="8" r="6" />
      <path className="icon-check-draw" d="M5.4 8.1l1.8 1.8 3.5-3.6" />
    </svg>
  );
}

export function DistillOrbitIcon() {
  return (
    <svg
      className="ui-icon distill-orbit-icon"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="9" cy="9" r="6.8" strokeOpacity="0.28" />
      <path className="distill-orbit-arc" d="M9 2.2a6.8 6.8 0 0 1 6.8 6.8" />
      <path d="M9 5.5l.95 2.55L12.5 9l-2.55.95L9 12.5l-.95-2.55L5.5 9l2.55-.95L9 5.5Z" />
    </svg>
  );
}
