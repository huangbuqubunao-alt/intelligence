/**
 * Non-destructive reading-layer deduplication for YouTube rolling 2-line
 * auto-captions and deterministic extractive excerpts (`SOURCE_EXCERPTS`).
 *
 * Stored artifacts, hashes, Evidence IDs, and backend qualification files
 * remain 100% untouched; callers can always toggle back to verbatim raw lines.
 */

export type CleanedText = {
  text: string;
  collapsedCount: number;
};

export type TimedSegment = {
  start_ms: number;
  end_ms: number;
  text: string;
};

function normalizeLine(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

export function cleanCaptionText(raw: string): CleanedText {
  if (!raw || !raw.includes("\n")) {
    return { text: raw, collapsedCount: 0 };
  }
  const lines = raw.split(/\r?\n/);
  const kept: string[] = [];
  let lastNonEmptyIndex = -1;
  let lastNorm = "";
  let collapsedCount = 0;

  for (const rawLine of lines) {
    const trimmedRight = rawLine.replace(/[ \t]+$/g, "");
    const norm = normalizeLine(trimmedRight);
    if (!norm) {
      if (kept.length > 0 && kept[kept.length - 1] !== "") {
        kept.push("");
      }
      continue;
    }
    if (lastNorm) {
      if (norm === lastNorm) {
        collapsedCount += 1;
        continue;
      }
      if (lastNorm.length >= 4 && norm.startsWith(`${lastNorm} `) && lastNonEmptyIndex >= 0) {
        kept[lastNonEmptyIndex] = trimmedRight;
        lastNorm = norm;
        collapsedCount += 1;
        continue;
      }
      if (norm.length >= 12 && norm.split(" ").length >= 3 && lastNorm.endsWith(` ${norm}`)) {
        collapsedCount += 1;
        continue;
      }
    }
    lastNonEmptyIndex = kept.length;
    kept.push(trimmedRight);
    lastNorm = norm;
  }

  while (kept.length > 0 && kept[kept.length - 1] === "") {
    kept.pop();
  }

  return {
    text: collapsedCount > 0 ? kept.join("\n") : raw,
    collapsedCount,
  };
}

export function cleanTimedSegments(segments: TimedSegment[]): {
  segments: TimedSegment[];
  collapsedCount: number;
} {
  const result: TimedSegment[] = [];
  let collapsedCount = 0;
  let carryNorm = "";

  for (const segment of segments) {
    const inner = cleanCaptionText(segment.text);
    collapsedCount += inner.collapsedCount;
    const lines = inner.text
      .split(/\r?\n/)
      .map(line => line.replace(/[ \t]+$/g, ""))
      .filter(line => line.trim().length > 0);

    while (lines.length > 0 && carryNorm) {
      const firstNorm = normalizeLine(lines[0]);
      if (firstNorm === carryNorm) {
        lines.shift();
        collapsedCount += 1;
      } else {
        break;
      }
    }

    if (lines.length === 0) continue;
    carryNorm = normalizeLine(lines[lines.length - 1]);
    result.push({
      start_ms: segment.start_ms,
      end_ms: segment.end_ms,
      text: lines.join("\n"),
    });
  }

  return { segments: result, collapsedCount };
}

const TRANSLATION_META_NOTE_RE =
  /[ \t]*[（(][^（）()\n]{0,120}(?:为原文中|未翻译的|保留原样|译注|注：|此处保留)[^（）()\n]{0,120}[）)]/g;

const REPEATED_SENTENCE_RE =
  /([^。！？.!?\n]{4,}[。！？.!?])[ \t]*\1+/g;

export function cleanTranslatedCaptionText(raw: string): string {
  if (!raw) return raw;
  const withoutNotes = raw.replace(TRANSLATION_META_NOTE_RE, "");
  const lineCleaned = cleanCaptionText(withoutNotes).text;
  return lineCleaned
    .split(/\r?\n/)
    .map(line => line.replace(REPEATED_SENTENCE_RE, "$1").trim())
    .filter((line, idx, arr) => line.length > 0 || (idx > 0 && arr[idx - 1] !== ""))
    .join("\n")
    .trim();
}

export function dedupeSummaryPoints(summary: string, points: string[]): string[] {
  if (!points.length) return [];
  const summaryNorm = normalizeLine(cleanCaptionText(summary).text);
  const seen = new Set<string>();
  const kept: string[] = [];
  for (const raw of points) {
    const cleaned = cleanCaptionText(raw).text.trim();
    const norm = normalizeLine(cleaned);
    if (!norm || seen.has(norm)) continue;
    seen.add(norm);
    kept.push(cleaned);
  }
  if (kept.length === 1 && summaryNorm && normalizeLine(kept[0]) === summaryNorm) {
    return [];
  }
  return kept;
}

export function buildMarkdownVideoNote(input: {
  title: string;
  channelName?: string | null;
  sourceUrl?: string | null;
  publishedAt?: string | null;
  summary?: string | null;
  chineseGuide?: string[];
  corePoints?: string[];
}): string {
  const lines: string[] = [`# ${input.title || "Untitled"}`];
  const meta: string[] = [];
  if (input.channelName) meta.push(input.channelName);
  if (input.publishedAt) meta.push(input.publishedAt);
  if (input.sourceUrl) meta.push(input.sourceUrl);
  if (meta.length) {
    lines.push("", `> ${meta.join(" · ")}`);
  }
  if (input.chineseGuide && input.chineseGuide.length > 0) {
    const uniqueGuide = Array.from(
      new Map(input.chineseGuide.map(seg => [normalizeLine(seg), seg])).values(),
    ).filter(Boolean);
    if (uniqueGuide.length > 0) {
      lines.push("", "## 中文导读", "");
      for (const seg of uniqueGuide) {
        lines.push(`- ${seg}`);
      }
    }
  }
  if (input.summary && input.summary.trim()) {
    lines.push("", "## 摘要 / 原文摘录", "", input.summary.trim());
  }
  if (input.corePoints && input.corePoints.length > 0) {
    lines.push("", "## 核心要点", "");
    for (const point of input.corePoints) {
      lines.push(`- ${point}`);
    }
  }
  return `${lines.join("\n")}\n`;
}
