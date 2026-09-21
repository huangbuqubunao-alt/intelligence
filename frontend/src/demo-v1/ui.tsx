import type { ButtonHTMLAttributes, ReactNode } from "react";

export function SectionHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="section-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <p className="lede">{description}</p>}</div>{action && <div className="header-action">{action}</div>}</header>;
}

export function StatusLine({ tone = "neutral", title, children }: { tone?: "neutral" | "success" | "warning" | "danger"; title: string; children?: ReactNode }) {
  return <div className={`status-line status-${tone}`} role={tone === "danger" ? "alert" : "status"}><span className="status-mark" aria-hidden="true" /><div><strong>{title}</strong>{children && <p>{children}</p>}</div></div>;
}

export function Button({ children, variant = "primary", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" | "danger" }) {
  return <button className={`button button-${variant}`} {...props}>{children}</button>;
}

export function ProviderLabel({ provider, type }: { provider: string; type?: string }) {
  return <span className="provider-label">{provider}{type ? ` · ${type}` : ""}</span>;
}

export function MetaRow({ children }: { children: ReactNode }) {
  return <div className="meta-row">{children}</div>;
}
