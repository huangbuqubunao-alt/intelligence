import { useId } from "react";

/**
 * Intelligence product mark — "Orbit".
 *
 * An incomplete circular ring with a single small node sitting slightly
 * outside the orbit in the ring's gap. Reads as continuous attention,
 * signals gathering around a core, and long-term knowledge accumulation
 * without leaning on a planet, spinner, coin, or brain metaphor.
 *
 * Geometry (24×24 viewBox, center 12,12):
 *   • Ring  — R = 7.0, stroke-width 2.9, round caps, 300° of arc with a
 *             60° gap opening toward the upper right (θ = 10° → −50°).
 *   • Node  — filled circle r = 2.0 centered at (19.09, 6.46): angle
 *             −38° (deliberately off the gap's mid-line at −20° so the
 *             mark stays asymmetric), radius 9.0 so it floats just
 *             outside the ring's outer edge (8.45) with a small breath
 *             of negative space.
 *   • Stroke weight (~2.66 CSS px at the 22×22 display size) keeps the
 *     ring legible without going ultra-thin at 20 px.
 *
 * The gradient runs diagonally from the upper-right (blue) to the
 * lower-left (blue-purple) so the orbiting node picks up the brighter
 * stop and the ring's mass settles into the deeper one — same palette
 * the product has been using, just re-oriented for the orbit form.
 *
 * The mark always renders alongside a text wordmark in this Demo, so
 * it is exposed as decorative to assistive tech (aria-hidden). Sizing
 * is controlled by the CSS class passed in.
 */
export function Logo({ className }: { className?: string }) {
  // React's useId() emits values like ":r0:" — sanitize so url(#...) refs stay portable.
  const gradientId = `intel-logo-grad-${useId().replace(/:/g, "")}`;
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={gradientId} x1="20" y1="4" x2="4" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4C8DFF" />
          <stop offset="100%" stopColor="#8B6CF0" />
        </linearGradient>
      </defs>
      <path
        d="M18.89 13.22 A7 7 0 1 1 16.5 6.64"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.9"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="19.09" cy="6.46" r="2" fill={`url(#${gradientId})`} />
    </svg>
  );
}
