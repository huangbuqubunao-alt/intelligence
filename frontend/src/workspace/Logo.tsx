import { useId } from "react";

export function Logo({ className }: { className?: string }) {
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
