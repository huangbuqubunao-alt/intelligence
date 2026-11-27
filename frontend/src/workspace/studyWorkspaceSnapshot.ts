import {
  importPersonalNotesObject,
  MAX_STUDY_SNAPSHOT_BYTES,
  readAllPersonalNotes,
} from "./personalNotes";
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

export type StudyWorkspaceImportResult = {
  importedNotes: number;
  totalNotes: number;
  noteConflicts: number;
  skippedOlderNotes: number;
  notesPersisted: boolean;
  importedViews: number;
  totalViews: number;
  viewsPersisted: boolean;
  failedViewsCount: number;
};

export function importStudyWorkspaceSnapshotJson(rawJson: string): StudyWorkspaceImportResult {
  if (!rawJson || rawJson.length > MAX_STUDY_SNAPSHOT_BYTES) {
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
  const obj = parsed as Record<string, unknown>;
  if (obj.version !== undefined && obj.version !== 1 && obj.version !== 2) {
    throw new Error("UNSUPPORTED_STUDY_SNAPSHOT_VERSION");
  }

  const noteResult = importPersonalNotesObject(obj);
  const candidateViews = obj.saved_views;
  const viewResult = Array.isArray(candidateViews)
    ? mergeSavedContentViews(candidateViews)
    : {
        importedCount: 0,
        totalCount: readSavedContentViews().length,
        persisted: true,
        failedCount: 0,
      };

  return {
    importedNotes: noteResult.importedCount,
    totalNotes: noteResult.totalCount,
    noteConflicts: noteResult.conflictCount,
    skippedOlderNotes: noteResult.skippedOlderCount,
    notesPersisted: noteResult.persisted,
    importedViews: viewResult.importedCount,
    totalViews: viewResult.totalCount,
    viewsPersisted: viewResult.persisted,
    failedViewsCount: viewResult.failedCount,
  };
}
