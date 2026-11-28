export type ContentProviderFilter = "ALL" | "YOUTUBE" | "BILIBILI" | "LOCAL";
export type ContentBucketFilter =
  | "ALL"
  | "UNREAD"
  | "MUST_WATCH"
  | "STARRED"
  | "TUTORIAL"
  | "SHORTS"
  | "NOTED";

export interface ContentFilterCriteria {
  searchQuery: string;
  providerFilter: ContentProviderFilter;
  bucketFilter: ContentBucketFilter;
  topicFilter: string;
  channelFilter: string;
  tagFilter: string;
}

const VALID_PROVIDER_FILTERS = new Set<string>(["ALL", "YOUTUBE", "BILIBILI", "LOCAL"]);
const VALID_BUCKET_FILTERS = new Set<string>([
  "ALL",
  "UNREAD",
  "MUST_WATCH",
  "STARRED",
  "TUTORIAL",
  "SHORTS",
  "NOTED",
]);

function normalizeProviderFilter(value: unknown): ContentProviderFilter {
  return typeof value === "string" && VALID_PROVIDER_FILTERS.has(value)
    ? (value as ContentProviderFilter)
    : "ALL";
}

function normalizeBucketFilter(value: unknown): ContentBucketFilter {
  return typeof value === "string" && VALID_BUCKET_FILTERS.has(value)
    ? (value as ContentBucketFilter)
    : "ALL";
}

export interface SavedContentView extends ContentFilterCriteria {
  id: string;
  name: string;
  createdAt: string;
}

const SAVED_VIEWS_KEY = "yia.content_saved_views.v1";
const MAX_SAVED_VIEWS = 8;

export const SAVED_VIEWS_CHANGED_EVENT = "yia:saved-views-changed";

function dispatchSavedViewsChanged(): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(new CustomEvent(SAVED_VIEWS_CHANGED_EVENT));
  }
}

function sanitizeView(raw: unknown): SavedContentView | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.id !== "string" || !obj.id.trim()) return null;
  if (typeof obj.name !== "string" || !obj.name.trim()) return null;
  return {
    id: obj.id.trim(),
    name: obj.name.trim().slice(0, 40),
    searchQuery: typeof obj.searchQuery === "string" ? obj.searchQuery.trim() : "",
    providerFilter: normalizeProviderFilter(obj.providerFilter),
    bucketFilter: normalizeBucketFilter(obj.bucketFilter),
    topicFilter: typeof obj.topicFilter === "string" && obj.topicFilter ? obj.topicFilter : "ALL",
    channelFilter: typeof obj.channelFilter === "string" && obj.channelFilter ? obj.channelFilter : "ALL",
    tagFilter: typeof obj.tagFilter === "string" && obj.tagFilter ? obj.tagFilter : "ALL",
    createdAt:
      typeof obj.createdAt === "string" && obj.createdAt.trim()
        ? obj.createdAt
        : new Date(0).toISOString(),
  };
}

export function readSavedContentViews(): SavedContentView[] {
  try {
    const raw = window.localStorage.getItem(SAVED_VIEWS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const seenIds = new Set<string>();
    const views: SavedContentView[] = [];
    for (const item of parsed) {
      const clean = sanitizeView(item);
      if (!clean || seenIds.has(clean.id)) continue;
      seenIds.add(clean.id);
      views.push(clean);
      if (views.length >= MAX_SAVED_VIEWS) break;
    }
    return views;
  } catch {
    return [];
  }
}

function writeSavedViews(views: SavedContentView[]): boolean {
  try {
    if (views.length === 0) {
      window.localStorage.removeItem(SAVED_VIEWS_KEY);
    } else {
      window.localStorage.setItem(SAVED_VIEWS_KEY, JSON.stringify(views.slice(0, MAX_SAVED_VIEWS)));
    }
  } catch {
    return false;
  }
  dispatchSavedViewsChanged();
  return true;
}

export function matchesSavedContentView(
  view: ContentFilterCriteria,
  current: ContentFilterCriteria,
): boolean {
  return (
    view.searchQuery.trim().toLowerCase() === current.searchQuery.trim().toLowerCase() &&
    view.providerFilter === current.providerFilter &&
    view.bucketFilter === current.bucketFilter &&
    view.topicFilter === current.topicFilter &&
    view.channelFilter === current.channelFilter &&
    view.tagFilter.toLowerCase() === current.tagFilter.toLowerCase()
  );
}

const BUCKET_NAME_ZH: Record<string, string> = {
  UNREAD: "未读",
  MUST_WATCH: "必看",
  STARRED: "已收藏",
  TUTORIAL: "教程",
  SHORTS: "Shorts",
  NOTED: "有笔记",
};

const BUCKET_NAME_EN: Record<string, string> = {
  UNREAD: "Unread",
  MUST_WATCH: "Must-watch",
  STARRED: "Starred",
  TUTORIAL: "Tutorials",
  SHORTS: "Shorts",
  NOTED: "Noted",
};

export function suggestSavedViewName(filters: ContentFilterCriteria, zh = true): string {
  const parts: string[] = [];
  if (filters.bucketFilter !== "ALL") {
    parts.push(
      (zh ? BUCKET_NAME_ZH[filters.bucketFilter] : BUCKET_NAME_EN[filters.bucketFilter]) ??
        filters.bucketFilter,
    );
  }
  if (filters.tagFilter !== "ALL") {
    parts.push(`#${filters.tagFilter}`);
  }
  if (filters.topicFilter !== "ALL") {
    parts.push(filters.topicFilter);
  }
  if (filters.providerFilter !== "ALL") {
    parts.push(filters.providerFilter);
  }
  if (filters.searchQuery.trim()) {
    parts.push(
      zh ? `搜:${filters.searchQuery.trim()}` : `q:${filters.searchQuery.trim()}`,
    );
  }
  if (parts.length === 0 && filters.channelFilter !== "ALL") {
    parts.push(filters.channelFilter === "LOCAL" ? (zh ? "本地库" : "Local") : filters.channelFilter);
  }
  const combined = parts.join(" · ").trim();
  if (!combined) return zh ? "自定义视图" : "Saved view";
  return combined.length > 36 ? `${combined.slice(0, 35)}…` : combined;
}

export function saveContentView(
  input: ContentFilterCriteria & { name?: string },
  zh = true,
): SavedContentView[] {
  const criteria: ContentFilterCriteria = {
    searchQuery: input.searchQuery.trim(),
    providerFilter: normalizeProviderFilter(input.providerFilter),
    bucketFilter: normalizeBucketFilter(input.bucketFilter),
    topicFilter: input.topicFilter || "ALL",
    channelFilter: input.channelFilter || "ALL",
    tagFilter: input.tagFilter || "ALL",
  };
  const name = (input.name?.trim() || suggestSavedViewName(criteria, zh)).slice(0, 40);
  const current = readSavedContentViews();
  const existing = current.find((v) => matchesSavedContentView(v, criteria));
  const nextEntry: SavedContentView = {
    id: existing?.id ?? `view_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    ...criteria,
    createdAt: new Date().toISOString(),
  };
  const updated = [nextEntry, ...current.filter((v) => v.id !== nextEntry.id)].slice(
    0,
    MAX_SAVED_VIEWS,
  );
  writeSavedViews(updated);
  return updated;
}

export function deleteSavedContentView(viewId: string): SavedContentView[] {
  const updated = readSavedContentViews().filter((v) => v.id !== viewId);
  writeSavedViews(updated);
  return updated;
}

export function clearSavedContentViews(): void {
  writeSavedViews([]);
}

export function mergeSavedContentViews(incoming: readonly unknown[]): {
  importedCount: number;
  totalCount: number;
  persisted: boolean;
  failedCount: number;
} {
  const current = readSavedContentViews();
  if (!Array.isArray(incoming) || incoming.length === 0) {
    return {
      importedCount: 0,
      totalCount: current.length,
      persisted: true,
      failedCount: 0,
    };
  }
  const beforeIds = new Set(current.map((v) => v.id));
  const next = [...current];
  let candidateCount = 0;

  for (const raw of incoming.slice(0, 32)) {
    if (next.length >= MAX_SAVED_VIEWS) break;
    const clean = sanitizeView(raw);
    if (!clean) continue;
    const duplicate = next.some(
      (existing) => existing.id === clean.id || matchesSavedContentView(existing, clean),
    );
    if (duplicate) continue;
    next.push(clean);
    candidateCount += 1;
  }

  if (candidateCount === 0) {
    return {
      importedCount: 0,
      totalCount: current.length,
      persisted: true,
      failedCount: 0,
    };
  }

  const persisted = writeSavedViews(next);
  const verified = readSavedContentViews();
  const actualImported = persisted
    ? verified.filter((v) => !beforeIds.has(v.id)).length
    : 0;
  const failedCount = Math.max(0, candidateCount - actualImported);
  return {
    importedCount: actualImported,
    totalCount: verified.length,
    persisted: persisted && failedCount === 0,
    failedCount,
  };
}

let pendingContentSavedView: SavedContentView | null = null;

export function setPendingContentSavedView(view: SavedContentView | null): void {
  pendingContentSavedView = view ? { ...view } : null;
}

export function consumePendingContentSavedView(): SavedContentView | null {
  const current = pendingContentSavedView;
  pendingContentSavedView = null;
  return current;
}
