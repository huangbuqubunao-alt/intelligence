import { flushSync } from "react-dom";
import { PhosphorIcon, PhosphorIconName } from "./ui/phosphorIcons";

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

function isChromiumAccessibilityTransitionUnsafe(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent ?? "";
  return /(?:Chrome|Chromium|Edg)\//.test(ua);
}

/**
 * Reuses the native Web Platform View Transitions API (`document.startViewTransition`)
 * paired with React's `flushSync` when available and motion is allowed, falling back
 * synchronously in jsdom, older browsers, and Chromium browsers where View Transitions
 * under OS Accessibility trees can trigger renderer SIGTRAP crashes.
 */
export function runViewTransition(commit: () => void): void {
  if (
    typeof document === "undefined" ||
    prefersReducedMotion() ||
    isChromiumAccessibilityTransitionUnsafe()
  ) {
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
      // Browser queued View Transition callback asynchronously.
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

const NAV_PHOSPHOR_MAP: Record<NavIconName, PhosphorIconName> = {
  Home: "house",
  Following: "rss",
  Content: "play-circle",
  Intelligence: "sparkle",
  Research: "sparkle",
  Topics: "stack",
  Settings: "sliders-horizontal",
};

export function NavIcon({ name, active = false }: { name: NavIconName; active?: boolean }) {
  return (
    <PhosphorIcon
      name={NAV_PHOSPHOR_MAP[name]}
      weight={active ? "fill" : "regular"}
      size={17}
      className="nav-svg-icon"
    />
  );
}

export function BookmarkSparkIcon({ saved }: { saved: boolean }) {
  return (
    <PhosphorIcon
      name="bookmark-simple"
      weight={saved ? "fill" : "regular"}
      size={15}
      className={`bookmark-icon${saved ? " is-saved" : ""}`}
    />
  );
}

export function VerifiedSealIcon() {
  return (
    <PhosphorIcon
      name="check-circle"
      weight="fill"
      size={15}
      className="verified-seal-icon"
    />
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
