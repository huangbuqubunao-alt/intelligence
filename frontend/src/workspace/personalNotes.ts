export type PersonalNote = {
  text: string;
  tags: string[];
  updatedAt: string;
};

export const PERSONAL_NOTES_STORAGE_KEY = "yia.personal-notes.v1";
const STORAGE_KEY = PERSONAL_NOTES_STORAGE_KEY;
export const PERSONAL_NOTES_CHANGED_EVENT = "yia-personal-notes-changed";
export const MAX_STUDY_SNAPSHOT_BYTES = 10 * 1024 * 1024;
export const MAX_PERSONAL_NOTES_IMPORT_COUNT = 10000;

export function utf8ByteLength(text: string): number {
  if (typeof TextEncoder !== "undefined") {
    return new TextEncoder().encode(text).length;
  }
  let bytes = 0;
  for (let i = 0; i < text.length; i += 1) {
    const code = text.charCodeAt(i);
    if (code < 0x80) bytes += 1;
    else if (code < 0x800) bytes += 2;
    else if (code >= 0xd800 && code <= 0xdbff) {
      bytes += 4;
      i += 1;
    } else bytes += 3;
  }
  return bytes;
}

const UNSAFE_NOTE_KEYS = new Set(["__proto__", "constructor", "prototype"]);

function isSafeNoteKey(rawKey: string): boolean {
  const clean = rawKey.trim();
  return clean.length > 0 && !UNSAFE_NOTE_KEYS.has(clean);
}

function emptyNoteDict(): Record<string, PersonalNote> {
  return Object.create(null) as Record<string, PersonalNote>;
}

export function parseSingleTagRename(raw: string): {
  valid: boolean;
  targetTag: string;
  error?: "EMPTY" | "MULTI_TOKEN";
} {
  const clean = raw.trim().replace(/^#+/, "");
  if (!clean) {
    return { valid: false, targetTag: "", error: "EMPTY" };
  }
  if (/[\s,，;；#]/.test(clean)) {
    return { valid: false, targetTag: "", error: "MULTI_TOKEN" };
  }
  return { valid: true, targetTag: clean.slice(0, 32) };
}

export function normalizeNoteTags(raw: string): string[] {
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const part of raw.split(/[\s,，;；#]+/)) {
    const clean = part.trim().replace(/^#+/, "");
    if (!clean) continue;
    const key = clean.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    tags.push(clean.slice(0, 32));
    if (tags.length >= 12) break;
  }
  return tags;
}

function readNoteStore(): Record<string, PersonalNote> {
  if (typeof localStorage === "undefined") return emptyNoteDict();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyNoteDict();
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return emptyNoteDict();
    const out = emptyNoteDict();
    for (const [key, val] of Object.entries(parsed)) {
      if (!isSafeNoteKey(key) || !val || typeof val !== "object" || Array.isArray(val)) continue;
      const candidate = val as Partial<PersonalNote>;
      const text = typeof candidate.text === "string" ? candidate.text : "";
      const tags = Array.isArray(candidate.tags)
        ? candidate.tags.filter((t): t is string => typeof t === "string" && t.trim().length > 0).slice(0, 12)
        : [];
      if (!text.trim() && tags.length === 0) continue;
      out[key] = {
        text,
        tags,
        updatedAt:
          typeof candidate.updatedAt === "string" && candidate.updatedAt
            ? candidate.updatedAt
            : new Date(0).toISOString(),
      };
    }
    return out;
  } catch {
    return emptyNoteDict();
  }
}

function writeNoteStore(store: Record<string, PersonalNote>): boolean {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    }
  } catch {
    return false;
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(PERSONAL_NOTES_CHANGED_EVENT));
  }
  return true;
}

export function readPersonalNote(videoId: string): PersonalNote | null {
  if (!videoId) return null;
  const store = readNoteStore();
  return store[videoId] ?? null;
}

export function readAllPersonalNotes(): Record<string, PersonalNote> {
  return readNoteStore();
}

export function listPersonalNoteVideoIds(): Set<string> {
  return new Set(Object.keys(readNoteStore()));
}

export type PersonalTagCount = {
  tag: string;
  count: number;
  videoIds: string[];
};

let pendingContentTag = "";

export function setPendingContentTag(tag: string): void {
  pendingContentTag = tag.trim().replace(/^#+/, "");
}

export function consumePendingContentTag(): string {
  const next = pendingContentTag;
  pendingContentTag = "";
  return next;
}

export function listPersonalTagCounts(): PersonalTagCount[] {
  const store = readNoteStore();
  const buckets = new Map<string, { tag: string; videoIds: Set<string> }>();
  for (const [videoId, note] of Object.entries(store)) {
    for (const rawTag of note.tags) {
      const clean = rawTag.trim().replace(/^#+/, "");
      if (!clean) continue;
      const key = clean.toLowerCase();
      const existing = buckets.get(key);
      if (existing) {
        existing.videoIds.add(videoId);
      } else {
        buckets.set(key, { tag: clean, videoIds: new Set([videoId]) });
      }
    }
  }
  return Array.from(buckets.values())
    .map((entry) => ({
      tag: entry.tag,
      count: entry.videoIds.size,
      videoIds: Array.from(entry.videoIds),
    }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}

export function savePersonalNoteChecked(
  videoId: string,
  input: { text: string; tags: string[] },
): { note: PersonalNote | null; persisted: boolean } {
  if (!isSafeNoteKey(videoId)) return { note: null, persisted: false };
  const store = readNoteStore();
  const cleanTags = input.tags.map((t) => t.trim()).filter(Boolean).slice(0, 12);
  if (!input.text.trim() && cleanTags.length === 0) {
    if (videoId in store) {
      delete store[videoId];
      const persisted = writeNoteStore(store);
      return { note: null, persisted };
    }
    return { note: null, persisted: true };
  }
  const saved: PersonalNote = {
    text: input.text,
    tags: cleanTags,
    updatedAt: new Date().toISOString(),
  };
  store[videoId] = saved;
  const persisted = writeNoteStore(store);
  return { note: persisted ? saved : null, persisted };
}

export function savePersonalNote(
  videoId: string,
  input: { text: string; tags: string[] },
): PersonalNote | null {
  return savePersonalNoteChecked(videoId, input).note;
}

export function deletePersonalNote(videoId: string): void {
  if (!videoId) return;
  const store = readNoteStore();
  if (videoId in store) {
    delete store[videoId];
    writeNoteStore(store);
  }
}

export function batchAddPersonalTags(
  videoIds: readonly string[],
  rawTags: string,
): { updatedCount: number; tagsAdded: string[] } {
  const tagsAdded = normalizeNoteTags(rawTags);
  const cleanIds = Array.from(
    new Set(videoIds.map((id) => id.trim()).filter(Boolean)),
  );
  if (tagsAdded.length === 0 || cleanIds.length === 0) {
    return { updatedCount: 0, tagsAdded: [] };
  }
  const store = readNoteStore();
  const nowIso = new Date().toISOString();
  let updatedCount = 0;

  for (const videoId of cleanIds) {
    const existing = store[videoId];
    const baseTags = existing?.tags ?? [];
    const seen = new Set(baseTags.map((tag) => tag.trim().toLowerCase()));
    const mergedTags = [...baseTags];
    let addedForNote = false;
    for (const nextTag of tagsAdded) {
      if (mergedTags.length >= 12) break;
      const lower = nextTag.toLowerCase();
      if (seen.has(lower)) continue;
      seen.add(lower);
      mergedTags.push(nextTag);
      addedForNote = true;
    }
    if (!existing || addedForNote) {
      store[videoId] = {
        text: existing?.text ?? "",
        tags: mergedTags,
        updatedAt: nowIso,
      };
      updatedCount += 1;
    }
  }

  if (updatedCount > 0) {
    writeNoteStore(store);
  }
  return { updatedCount, tagsAdded };
}

export function renamePersonalTag(
  oldTag: string,
  newTagRaw: string,
): { affectedCount: number; targetTag: string; error?: "EMPTY" | "MULTI_TOKEN" } {
  const oldClean = oldTag.trim().replace(/^#+/, "");
  const parsedTarget = parseSingleTagRename(newTagRaw);
  if (!parsedTarget.valid) {
    return { affectedCount: 0, targetTag: "", error: parsedTarget.error };
  }
  const { targetTag } = parsedTarget;
  if (!oldClean || oldClean === targetTag) {
    return { affectedCount: 0, targetTag };
  }
  const oldLower = oldClean.toLowerCase();
  const targetLower = targetTag.toLowerCase();
  const store = readNoteStore();
  const nowIso = new Date().toISOString();
  let affectedCount = 0;

  for (const [videoId, note] of Object.entries(store)) {
    const hasOld = note.tags.some((t) => t.trim().toLowerCase() === oldLower);
    if (!hasOld) continue;
    const seen = new Set<string>();
    const nextTags: string[] = [];
    for (const tag of note.tags) {
      const clean = tag.trim().replace(/^#+/, "");
      if (!clean) continue;
      const lower = clean.toLowerCase();
      if (lower === oldLower) {
        if (!seen.has(targetLower)) {
          seen.add(targetLower);
          nextTags.push(targetTag);
        }
      } else if (!seen.has(lower)) {
        seen.add(lower);
        nextTags.push(clean);
      }
    }
    store[videoId] = {
      text: note.text,
      tags: nextTags.slice(0, 12),
      updatedAt: nowIso,
    };
    affectedCount += 1;
  }

  if (affectedCount > 0) {
    writeNoteStore(store);
  }
  return { affectedCount, targetTag };
}

export function deletePersonalTag(tagToDelete: string): { affectedCount: number } {
  const cleanTarget = tagToDelete.trim().replace(/^#+/, "").toLowerCase();
  if (!cleanTarget) return { affectedCount: 0 };
  const store = readNoteStore();
  const nowIso = new Date().toISOString();
  let affectedCount = 0;

  for (const [videoId, note] of Object.entries(store)) {
    const nextTags = note.tags.filter((t) => t.trim().replace(/^#+/, "").toLowerCase() !== cleanTarget);
    if (nextTags.length === note.tags.length) continue;
    affectedCount += 1;
    if (!note.text.trim() && nextTags.length === 0) {
      delete store[videoId];
    } else {
      store[videoId] = {
        text: note.text,
        tags: nextTags,
        updatedAt: nowIso,
      };
    }
  }

  if (affectedCount > 0) {
    writeNoteStore(store);
  }
  return { affectedCount };
}

export function appendQuoteToPersonalNote(videoId: string, formattedQuote: string): PersonalNote | null {
  const quote = formattedQuote.trim();
  if (!videoId || !quote) return readPersonalNote(videoId);
  const existing = readPersonalNote(videoId);
  const currentText = existing?.text ?? "";
  if (currentText.includes(quote)) {
    return existing;
  }
  const nextText = currentText.trimEnd() ? `${currentText.trimEnd()}\n\n${quote}` : quote;
  return savePersonalNote(videoId, {
    text: nextText,
    tags: existing?.tags ?? [],
  });
}

export function mergePersonalNoteIntoMarkdown(
  baseMarkdown: string,
  note: PersonalNote | null,
  zh = true,
): string {
  if (!note || (!note.text.trim() && note.tags.length === 0)) {
    return baseMarkdown;
  }
  const parts: string[] = [baseMarkdown.trimEnd()];
  parts.push(zh ? "## 我的思考与摘录" : "## My Notes & Highlights");
  if (note.tags.length > 0) {
    parts.push(note.tags.map((tag) => `#${tag}`).join(" "));
  }
  if (note.text.trim()) {
    parts.push(note.text.trim());
  }
  return `${parts.filter(Boolean).join("\n\n")}\n`;
}

export function exportPersonalNotesJson(): string {
  const notes = readAllPersonalNotes();
  return `${JSON.stringify(
    {
      version: 1,
      exported_at: new Date().toISOString(),
      note_count: Object.keys(notes).length,
      notes,
    },
    null,
    2,
  )}\n`;
}

export type ImportPersonalNotesResult = {
  importedCount: number;
  totalCount: number;
  conflictCount: number;
  skippedOlderCount: number;
  persisted: boolean;
};

function tagsEqual(a: readonly string[], b: readonly string[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((item, idx) => item === b[idx]);
}

function daysInGregorianMonth(year: number, month: number): number {
  if (month === 2) {
    const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
    return isLeap ? 29 : 28;
  }
  if (month === 4 || month === 6 || month === 9 || month === 11) return 30;
  return 31;
}

const STRICT_ISO_TIMESTAMP_RE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?(Z|[+-]\d{2}:\d{2})$/;

function parseStrictUpdatedAtMs(raw: unknown): { valid: boolean; iso: string; ms: number } {
  const epochFallback = { valid: false, iso: new Date(0).toISOString(), ms: 0 };
  if (typeof raw !== "string") {
    return epochFallback;
  }
  const clean = raw.trim();
  const match = STRICT_ISO_TIMESTAMP_RE.exec(clean);
  if (!match) {
    return epochFallback;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = match[6] ? Number(match[6]) : 0;
  const msPart = match[7] ? Number(match[7].slice(0, 3).padEnd(3, "0")) : 0;
  const tz = match[8];

  if (
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > daysInGregorianMonth(year, month) ||
    hour > 23 ||
    minute > 59 ||
    second > 59
  ) {
    return epochFallback;
  }

  let offsetMinutes = 0;
  if (tz !== "Z") {
    const sign = tz[0] === "+" ? 1 : -1;
    const offH = Number(tz.slice(1, 3));
    const offM = Number(tz.slice(4, 6));
    if (offH > 23 || offM > 59) {
      return epochFallback;
    }
    offsetMinutes = sign * (offH * 60 + offM);
  }

  const localAsUtc = Date.UTC(year, month - 1, day, hour, minute, second, msPart);
  const checkDate = new Date(localAsUtc);
  if (
    checkDate.getUTCFullYear() !== year ||
    checkDate.getUTCMonth() + 1 !== month ||
    checkDate.getUTCDate() !== day
  ) {
    return epochFallback;
  }

  const ms = localAsUtc - offsetMinutes * 60_000;
  if (!Number.isFinite(ms) || ms <= 0) {
    return epochFallback;
  }
  return { valid: true, iso: clean, ms };
}

export function importPersonalNotesObject(
  parsed: Record<string, unknown>,
): ImportPersonalNotesResult {
  const candidateVersion = parsed.version;
  if (
    candidateVersion !== undefined &&
    candidateVersion !== 1 &&
    candidateVersion !== 2
  ) {
    throw new Error("UNSUPPORTED_PERSONAL_NOTES_VERSION");
  }
  const candidateNotes = parsed.notes;
  if (!candidateNotes || typeof candidateNotes !== "object" || Array.isArray(candidateNotes)) {
    throw new Error("MISSING_NOTES_MAP");
  }
  const current = readNoteStore();
  let importedCount = 0;
  let conflictCount = 0;
  let skippedOlderCount = 0;
  let storeChanged = false;
  const entries = Object.entries(candidateNotes);
  if (entries.length > MAX_PERSONAL_NOTES_IMPORT_COUNT) {
    throw new Error("TOO_MANY_PERSONAL_NOTES");
  }
  for (const [videoId, value] of entries) {
    if (!isSafeNoteKey(videoId) || !value || typeof value !== "object" || Array.isArray(value)) {
      continue;
    }
    const rawEntry = value as Partial<PersonalNote>;
    const text = typeof rawEntry.text === "string" ? rawEntry.text : "";
    const tags = Array.isArray(rawEntry.tags)
      ? rawEntry.tags.filter((t): t is string => typeof t === "string" && t.trim().length > 0).map((t) => t.trim()).slice(0, 12)
      : [];
    if (!text.trim() && tags.length === 0) continue;

    const incomingTime = parseStrictUpdatedAtMs(rawEntry.updatedAt);
    const existing = current[videoId];
    if (!existing) {
      current[videoId] = { text, tags, updatedAt: incomingTime.iso };
      importedCount += 1;
      storeChanged = true;
      continue;
    }
    const existingTime = parseStrictUpdatedAtMs(existing.updatedAt);
    if (existing.text === text && tagsEqual(existing.tags, tags)) {
      if (incomingTime.valid) {
        if (!existingTime.valid || incomingTime.ms > existingTime.ms) {
          current[videoId] = {
            text: existing.text,
            tags: existing.tags,
            updatedAt: incomingTime.iso,
          };
          storeChanged = true;
        } else if (incomingTime.ms < existingTime.ms) {
          skippedOlderCount += 1;
        }
      }
      continue;
    }
    if (!incomingTime.valid) {
      // Unknown/malformed incoming timestamp never overwrites an existing note.
      conflictCount += 1;
      continue;
    }
    if (existingTime.valid && incomingTime.ms < existingTime.ms) {
      skippedOlderCount += 1;
      continue;
    }
    if (existingTime.valid && incomingTime.ms === existingTime.ms) {
      // Same timestamp with differing content is treated conservatively as a conflict.
      conflictCount += 1;
      continue;
    }
    current[videoId] = { text, tags, updatedAt: incomingTime.iso };
    importedCount += 1;
    storeChanged = true;
  }

  let persisted = true;
  if (storeChanged) {
    persisted = writeNoteStore(current);
  }
  const verified = readNoteStore();
  if (!persisted) {
    return {
      importedCount: 0,
      totalCount: Object.keys(verified).length,
      conflictCount,
      skippedOlderCount,
      persisted: false,
    };
  }
  return {
    importedCount,
    totalCount: Object.keys(verified).length,
    conflictCount,
    skippedOlderCount,
    persisted: true,
  };
}

export function importPersonalNotesJson(rawJson: string): ImportPersonalNotesResult {
  if (!rawJson || utf8ByteLength(rawJson) > MAX_STUDY_SNAPSHOT_BYTES) {
    throw new Error("INVALID_PERSONAL_NOTES_FILE");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch {
    throw new Error("INVALID_PERSONAL_NOTES_JSON");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("INVALID_PERSONAL_NOTES_SHAPE");
  }
  return importPersonalNotesObject(parsed as Record<string, unknown>);
}

function sanitizeWikilinkTitle(rawTitle: string, fallbackId: string): string {
  const cleaned = rawTitle
    .replace(/[[\]|#^\n\r]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || fallbackId;
}

export function exportPersonalNotesMarkdown(
  titleByVideoId: Record<string, string> = {},
  zh = true,
): { markdown: string; noteCount: number } {
  const store = readAllPersonalNotes();
  const entries = Object.entries(store)
    .filter(([, note]) => note.text.trim().length > 0 || note.tags.length > 0)
    .sort(([, a], [, b]) => (Date.parse(b.updatedAt || "") || 0) - (Date.parse(a.updatedAt || "") || 0));

  const exportedStamp = new Date().toISOString().slice(0, 16).replace("T", " ");
  const header = [
    zh ? "# 个人研究笔记与标签汇编" : "# Personal Research Notes & Tags Digest",
    "",
    zh
      ? `- 导出时间：${exportedStamp} UTC\n- 笔记条数：${entries.length}`
      : `- Exported at: ${exportedStamp} UTC\n- Notes: ${entries.length}`,
  ];

  const tagCounts = listPersonalTagCounts();
  if (tagCounts.length > 0) {
    header.push("");
    header.push(zh ? "## 标签索引" : "## Tag Index");
    header.push(tagCounts.map((item) => `#${item.tag} (${item.count})`).join(" · "));
  }

  if (entries.length === 0) {
    header.push("");
    header.push(
      zh
        ? "_暂无本地个人笔记，可在任意内容详情页记录心得或摘录时间戳。_"
        : "_No local personal notes recorded yet._",
    );
    return { markdown: `${header.join("\n")}\n`, noteCount: 0 };
  }

  const sections = entries.map(([videoId, note]) => {
    const safeTitle = sanitizeWikilinkTitle(titleByVideoId[videoId] ?? videoId, videoId);
    const updated = note.updatedAt ? note.updatedAt.slice(0, 16).replace("T", " ") : "";
    const lines: string[] = [
      `## [[${safeTitle}]]`,
      zh
        ? `- 来源 ID：\`${videoId}\`${updated ? ` · 更新时间：${updated}` : ""}`
        : `- Source ID: \`${videoId}\`${updated ? ` · Updated: ${updated}` : ""}`,
    ];
    if (note.tags.length > 0) {
      lines.push(note.tags.map((tag) => `#${tag}`).join(" "));
    }
    if (note.text.trim()) {
      lines.push("");
      lines.push(note.text.trim());
    }
    return lines.join("\n");
  });

  return {
    markdown: `${header.join("\n")}\n\n---\n\n${sections.join("\n\n---\n\n")}\n`,
    noteCount: entries.length,
  };
}
