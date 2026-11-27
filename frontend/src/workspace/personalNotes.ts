export type PersonalNote = {
  text: string;
  tags: string[];
  updatedAt: string;
};

const STORAGE_KEY = "yia.personal-notes.v1";
export const PERSONAL_NOTES_CHANGED_EVENT = "yia-personal-notes-changed";

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
  if (typeof localStorage === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const out: Record<string, PersonalNote> = {};
    for (const [key, val] of Object.entries(parsed)) {
      if (!key || !val || typeof val !== "object" || Array.isArray(val)) continue;
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
    return {};
  }
}

function writeNoteStore(store: Record<string, PersonalNote>): void {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(PERSONAL_NOTES_CHANGED_EVENT));
  }
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

export function savePersonalNote(
  videoId: string,
  input: { text: string; tags: string[] },
): PersonalNote | null {
  if (!videoId) return null;
  const store = readNoteStore();
  const cleanTags = input.tags.map((t) => t.trim()).filter(Boolean).slice(0, 12);
  if (!input.text.trim() && cleanTags.length === 0) {
    if (videoId in store) {
      delete store[videoId];
      writeNoteStore(store);
    }
    return null;
  }
  const saved: PersonalNote = {
    text: input.text,
    tags: cleanTags,
    updatedAt: new Date().toISOString(),
  };
  store[videoId] = saved;
  writeNoteStore(store);
  return saved;
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

export function importPersonalNotesJson(rawJson: string): {
  importedCount: number;
  totalCount: number;
} {
  if (!rawJson || rawJson.length > 2 * 1024 * 1024) {
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
  const candidateNotes = (parsed as { notes?: unknown }).notes;
  if (!candidateNotes || typeof candidateNotes !== "object" || Array.isArray(candidateNotes)) {
    throw new Error("MISSING_NOTES_MAP");
  }
  const current = readNoteStore();
  let importedCount = 0;
  const entries = Object.entries(candidateNotes);
  if (entries.length > 500) {
    throw new Error("TOO_MANY_PERSONAL_NOTES");
  }
  for (const [videoId, value] of entries) {
    if (!videoId.trim() || !value || typeof value !== "object" || Array.isArray(value)) {
      continue;
    }
    const rawEntry = value as Partial<PersonalNote>;
    const text = typeof rawEntry.text === "string" ? rawEntry.text : "";
    const tags = Array.isArray(rawEntry.tags)
      ? rawEntry.tags.filter((t): t is string => typeof t === "string" && t.trim().length > 0).slice(0, 12)
      : [];
    if (!text.trim() && tags.length === 0) continue;
    const incomingUpdated =
      typeof rawEntry.updatedAt === "string" && Number.isFinite(Date.parse(rawEntry.updatedAt))
        ? rawEntry.updatedAt
        : new Date().toISOString();
    const existing = current[videoId];
    if (!existing || Date.parse(incomingUpdated) >= Date.parse(existing.updatedAt || "")) {
      current[videoId] = { text, tags, updatedAt: incomingUpdated };
      importedCount += 1;
    }
  }
  writeNoteStore(current);
  return {
    importedCount,
    totalCount: Object.keys(current).length,
  };
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
