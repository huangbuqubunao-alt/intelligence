import {
  PersonalNote,
  readAllPersonalNotes,
  readPersonalNote,
  savePersonalNote,
} from "./personalNotes";

export type NoteChecklistItem = {
  videoId: string;
  lineIndex: number;
  text: string;
  checked: boolean;
  updatedAt: string;
};

const CHECKLIST_LINE_RE = /^(\s*[-*]\s+\[)([ xX])(\]\s+)(.+)$/;

export function extractNoteChecklistItems(
  videoId: string,
  noteText: string,
  updatedAt: string = "",
): NoteChecklistItem[] {
  const cleanId = videoId.trim();
  if (!cleanId || !noteText) return [];
  const lines = noteText.split(/\r?\n/);
  const items: NoteChecklistItem[] = [];
  for (let i = 0; i < lines.length; i += 1) {
    const match = CHECKLIST_LINE_RE.exec(lines[i]);
    if (!match) continue;
    const text = match[4].trim();
    if (!text) continue;
    items.push({
      videoId: cleanId,
      lineIndex: i,
      text,
      checked: match[2].toLowerCase() === "x",
      updatedAt,
    });
  }
  return items;
}

export function collectWorkspaceChecklistItems(): NoteChecklistItem[] {
  const notes = readAllPersonalNotes();
  const collected: NoteChecklistItem[] = [];
  for (const [videoId, note] of Object.entries(notes)) {
    collected.push(...extractNoteChecklistItems(videoId, note.text, note.updatedAt));
  }
  return collected.sort((a, b) => {
    if (a.checked !== b.checked) return a.checked ? 1 : -1;
    const timeOrder = b.updatedAt.localeCompare(a.updatedAt);
    if (timeOrder !== 0) return timeOrder;
    if (a.videoId !== b.videoId) return a.videoId.localeCompare(b.videoId);
    return a.lineIndex - b.lineIndex;
  });
}

export function toggleChecklistLineInMarkdown(
  noteText: string,
  lineIndex: number,
): string | null {
  if (!noteText || lineIndex < 0) return null;
  const lineBreak = noteText.includes("\r\n") ? "\r\n" : "\n";
  const lines = noteText.split(/\r?\n/);
  if (lineIndex >= lines.length) return null;
  const match = CHECKLIST_LINE_RE.exec(lines[lineIndex]);
  if (!match || !match[4].trim()) return null;
  const nextMark = match[2].toLowerCase() === "x" ? " " : "x";
  lines[lineIndex] = `${match[1]}${nextMark}${match[3]}${match[4]}`;
  return lines.join(lineBreak);
}

export function togglePersonalNoteChecklistItem(
  videoId: string,
  lineIndex: number,
): PersonalNote | null {
  const existing = readPersonalNote(videoId);
  if (!existing) return null;
  const nextText = toggleChecklistLineInMarkdown(existing.text, lineIndex);
  if (nextText === null) return existing;
  return savePersonalNote(videoId, {
    text: nextText,
    tags: existing.tags,
  });
}
