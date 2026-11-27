import { ReactNode } from "react";
import { PhosphorIcon } from "./ui/phosphorIcons";
import { useUiLanguage } from "./uiLanguage";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlightTextMatches(text: string, query: string): ReactNode {
  const trimmed = query.trim();
  if (!trimmed || !text) return text;
  const regex = new RegExp(`(${escapeRegExp(trimmed)})`, "gi");
  const parts = text.split(regex);
  if (parts.length <= 1) return text;
  const lowerQuery = trimmed.toLowerCase();
  return parts.map((part, idx) =>
    part.toLowerCase() === lowerQuery ? (
      <mark key={idx} className="reader-search-hit">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

export function formatSegmentQuote(text: string, title: string, locator: string): string {
  return `> "${text.trim()}"\n— 《${title}》 [${locator}]`;
}

export function splitSearchableParagraphs(raw: string): string[] {
  if (!raw.trim()) return [];
  const blocks = raw
    .split(/\r?\n\s*\r?\n+/)
    .map((block) => block.trim())
    .filter(Boolean);
  if (blocks.length > 1) return blocks;
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.length > 1 ? lines : blocks;
}

export function ReaderDrawerSearchBar({
  query,
  onChange,
  matchCount,
  totalCount,
  placeholder,
  ariaLabel,
  unitLabel,
}: {
  query: string;
  onChange: (next: string) => void;
  matchCount: number;
  totalCount: number;
  placeholder: string;
  ariaLabel: string;
  unitLabel?: string;
}) {
  const { language } = useUiLanguage();
  const zh = language === "zh-CN";
  const trimmed = query.trim();

  return (
    <div className="reader-drawer-search-bar">
      <div className="reader-drawer-search-input-wrap">
        <PhosphorIcon name="magnifying-glass" size={14} className="search-field-icon" />
        <input
          type="search"
          className="reader-drawer-search-input"
          aria-label={ariaLabel}
          placeholder={placeholder}
          value={query}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      {trimmed ? (
        <>
          <span className="reader-drawer-search-count tabular-nums" role="status">
            {zh
              ? `命中 ${matchCount} / ${totalCount}${unitLabel ? ` ${unitLabel}` : ""}`
              : `${matchCount} / ${totalCount}${unitLabel ? ` ${unitLabel}` : " matched"}`}
          </span>
          <button
            type="button"
            className="button button-ghost button-small"
            onClick={() => onChange("")}
          >
            {zh ? "清除" : "Clear"}
          </button>
        </>
      ) : null}
    </div>
  );
}
