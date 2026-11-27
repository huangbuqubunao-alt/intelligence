import { importPersonalNotesJson, readAllPersonalNotes } from "./personalNotes";
import { mergeSavedContentViews, readSavedContentViews } from "./savedViews";

export function exportStudyWorkspaceSnapshotJson(): string {
  const notes = readAllPersonalNotes();
  const savedViews = readSavedContentViews();
  return `${JSON.stringify(
    {
      version: 2,
      exported_at: new Date().toISOString(),
      note_count: Object.keys(notes).length,
      saved_view_count: savedViews.length,
      notes,
      saved_views: savedViews,
    },
    null,
    2,
  )}\n`;
}

export function importStudyWorkspaceSnapshotJson(rawJson: string): {
  importedNotes: number;
  totalNotes: number;
  importedViews: number;
  totalViews: number;
} {
  if (!rawJson || rawJson.length > 2 * 1024 * 1024) {
    throw new Error("INVALID_STUDY_SNAPSHOT_FILE");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch {
    throw new Error("INVALID_STUDY_SNAPSHOT_JSON");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("INVALID_STUDY_SNAPSHOT_SHAPE");
  }

  const noteResult = importPersonalNotesJson(rawJson);
  const candidateViews = (parsed as { saved_views?: unknown }).saved_views;
  const viewResult = Array.isArray(candidateViews)
    ? mergeSavedContentViews(candidateViews)
    : { importedCount: 0, totalCount: readSavedContentViews().length };

  return {
    importedNotes: noteResult.importedCount,
    totalNotes: noteResult.totalCount,
    importedViews: viewResult.importedCount,
    totalViews: viewResult.totalCount,
  };
}
