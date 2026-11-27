export interface ReadingHistoryEntry {
  videoId: string;
  title: string;
  channelName: string | null;
  provider: string | null;
  mediaKind: string | null;
  estimatedMinutes: number | null;
  lastVisitedAt: string;
  visitCount: number;
}

const READING_HISTORY_KEY = "yia.reading_history.v1";
const READER_COMFORT_KEY = "yia.reader_comfort_mode.v1";
const MAX_HISTORY_ENTRIES = 8;

export const READING_HISTORY_CHANGED_EVENT = "yia:reading-history-changed";

function dispatchHistoryChanged(): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(new CustomEvent(READING_HISTORY_CHANGED_EVENT));
  }
}

export function estimateReadingMinutes(input: {
  text?: string | null;
  durationSeconds?: number | null;
}): number | null {
  const raw = typeof input.text === "string" ? input.text.trim() : "";
  if (raw.length > 0) {
    const cjkChars = (raw.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) ?? []).length;
    const latinText = raw.replace(/[\u4e00-\u9fff\u3400-\u4dbf]/g, " ");
    const latinWords = latinText
      .trim()
      .split(/\s+/)
      .filter((token) => token.length > 0).length;
    if (cjkChars >= 20 || latinWords >= 5) {
      const minutes = cjkChars / 350 + latinWords / 220;
      return Math.max(1, Math.ceil(minutes));
    }
  }
  if (
    typeof input.durationSeconds === "number" &&
    Number.isFinite(input.durationSeconds) &&
    input.durationSeconds > 0
  ) {
    return Math.max(1, Math.round(input.durationSeconds / 60));
  }
  return raw.length > 0 ? 1 : null;
}

function sanitizeEntry(raw: unknown): ReadingHistoryEntry | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.videoId !== "string" || !obj.videoId.trim()) return null;
  const title = typeof obj.title === "string" && obj.title.trim() ? obj.title.trim() : obj.videoId;
  const lastVisitedAt =
    typeof obj.lastVisitedAt === "string" && obj.lastVisitedAt.trim()
      ? obj.lastVisitedAt
      : new Date(0).toISOString();
  const visitCount =
    typeof obj.visitCount === "number" && Number.isFinite(obj.visitCount) && obj.visitCount > 0
      ? Math.floor(obj.visitCount)
      : 1;
  const estimatedMinutes =
    typeof obj.estimatedMinutes === "number" &&
    Number.isFinite(obj.estimatedMinutes) &&
    obj.estimatedMinutes > 0
      ? Math.round(obj.estimatedMinutes)
      : null;
  return {
    videoId: obj.videoId.trim(),
    title,
    channelName: typeof obj.channelName === "string" && obj.channelName.trim() ? obj.channelName.trim() : null,
    provider: typeof obj.provider === "string" && obj.provider.trim() ? obj.provider.trim() : null,
    mediaKind: typeof obj.mediaKind === "string" && obj.mediaKind.trim() ? obj.mediaKind.trim() : null,
    estimatedMinutes,
    lastVisitedAt,
    visitCount,
  };
}

export function readReadingHistory(): ReadingHistoryEntry[] {
  try {
    const raw = window.localStorage.getItem(READING_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const byId = new Map<string, ReadingHistoryEntry>();
    for (const item of parsed) {
      const clean = sanitizeEntry(item);
      if (!clean) continue;
      const existing = byId.get(clean.videoId);
      if (!existing || clean.lastVisitedAt > existing.lastVisitedAt) {
        byId.set(clean.videoId, clean);
      }
    }
    return [...byId.values()]
      .sort((a, b) => b.lastVisitedAt.localeCompare(a.lastVisitedAt))
      .slice(0, MAX_HISTORY_ENTRIES);
  } catch {
    return [];
  }
}

export function recordReadingVisit(input: {
  videoId: string;
  title: string;
  channelName?: string | null;
  provider?: string | null;
  mediaKind?: string | null;
  estimatedMinutes?: number | null;
  lastVisitedAt?: string;
}): ReadingHistoryEntry[] {
  const videoId = input.videoId.trim();
  if (!videoId) return readReadingHistory();
  const current = readReadingHistory();
  const prev = current.find((item) => item.videoId === videoId);
  const nextEntry: ReadingHistoryEntry = {
    videoId,
    title: input.title.trim() || videoId,
    channelName: input.channelName?.trim() || null,
    provider: input.provider?.trim() || null,
    mediaKind: input.mediaKind?.trim() || null,
    estimatedMinutes:
      typeof input.estimatedMinutes === "number" &&
      Number.isFinite(input.estimatedMinutes) &&
      input.estimatedMinutes > 0
        ? Math.round(input.estimatedMinutes)
        : prev?.estimatedMinutes ?? null,
    lastVisitedAt: input.lastVisitedAt?.trim() || new Date().toISOString(),
    visitCount: (prev?.visitCount ?? 0) + 1,
  };
  const updated = [nextEntry, ...current.filter((item) => item.videoId !== videoId)].slice(
    0,
    MAX_HISTORY_ENTRIES,
  );
  try {
    window.localStorage.setItem(READING_HISTORY_KEY, JSON.stringify(updated));
  } catch {
    // Ignore storage quota errors in restricted webviews.
  }
  dispatchHistoryChanged();
  return updated;
}

export function clearReadingHistory(): void {
  try {
    window.localStorage.removeItem(READING_HISTORY_KEY);
  } catch {
    // Ignore storage removal errors.
  }
  dispatchHistoryChanged();
}

export function readReaderComfortMode(): boolean {
  try {
    return window.localStorage.getItem(READER_COMFORT_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeReaderComfortMode(enabled: boolean): void {
  try {
    if (enabled) {
      window.localStorage.setItem(READER_COMFORT_KEY, "1");
    } else {
      window.localStorage.removeItem(READER_COMFORT_KEY);
    }
  } catch {
    // Ignore storage quota errors.
  }
}
