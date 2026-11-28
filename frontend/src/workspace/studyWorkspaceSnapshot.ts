import {
  importPersonalNotesObject,
  MAX_PERSONAL_NOTES_IMPORT_COUNT,
  MAX_STUDY_SNAPSHOT_BYTES,
  type PersonalNote,
  readAllPersonalNotes,
  utf8ByteLength,
} from "./personalNotes";
import { mergeSavedContentViews, readSavedContentViews, type SavedContentView } from "./savedViews";

export type StudyWorkspaceSnapshotPart = {
  partIndex: number;
  totalParts: number;
  noteCount: number;
  savedViewCount: number;
  byteLength: number;
  json: string;
};

function buildSnapshotPayloadString(
  entries: ReadonlyArray<readonly [string, PersonalNote]>,
  savedViews: readonly SavedContentView[],
  exportedAt: string,
  options: {
    pretty?: boolean;
    partIndex?: number;
    totalParts?: number;
    minimal?: boolean;
    notesOnly?: boolean;
  } = {},
): string {
  const notesObj: Record<string, PersonalNote> = {};
  for (const [videoId, note] of entries) {
    notesObj[videoId] = note;
  }
  if (options.notesOnly) {
    return `${JSON.stringify({ notes: notesObj })}\n`;
  }
  if (options.minimal) {
    return `${JSON.stringify({ version: 2, notes: notesObj })}\n`;
  }
  const payload: Record<string, unknown> = {
    version: 2,
    exported_at: exportedAt,
  };
  if (typeof options.partIndex === "number" && typeof options.totalParts === "number") {
    payload.part_index = options.partIndex;
    payload.total_parts = options.totalParts;
  }
  payload.note_count = entries.length;
  payload.saved_view_count = savedViews.length;
  payload.notes = notesObj;
  payload.saved_views = savedViews;
  return `${options.pretty ? JSON.stringify(payload, null, 2) : JSON.stringify(payload)}\n`;
}

export function exportStudyWorkspaceSnapshotParts(options: {
  maxBytes?: number;
  maxNotesPerPart?: number;
} = {}): StudyWorkspaceSnapshotPart[] {
  const maxBytes = options.maxBytes ?? MAX_STUDY_SNAPSHOT_BYTES;
  const maxNotesPerPart = options.maxNotesPerPart ?? MAX_PERSONAL_NOTES_IMPORT_COUNT;
  const notes = readAllPersonalNotes();
  const savedViews = readSavedContentViews();
  const noteEntries = Object.entries(notes);
  const exportedAt = new Date().toISOString();

  if (noteEntries.length <= maxNotesPerPart) {
    const pretty = buildSnapshotPayloadString(noteEntries, savedViews, exportedAt, {
      pretty: true,
    });
    const prettyBytes = utf8ByteLength(pretty);
    if (prettyBytes <= maxBytes) {
      return [
        {
          partIndex: 1,
          totalParts: 1,
          noteCount: noteEntries.length,
          savedViewCount: savedViews.length,
          byteLength: prettyBytes,
          json: pretty,
        },
      ];
    }
  }

  // Reserve a small framing budget for shard wrapper fields and saved views when estimating.
  const emptyFrameBytes = utf8ByteLength(
    buildSnapshotPayloadString([], [], exportedAt, { partIndex: 999, totalParts: 999 }),
  );
  const entrySegments = noteEntries.map(([videoId, note]) => {
    const pair = [videoId, note] as const;
    const pairBytes = utf8ByteLength(`${JSON.stringify(videoId)}:${JSON.stringify(note)}`) + 1;
    return { pair, pairBytes };
  });

  const chunks: Array<{
    entries: Array<readonly [string, PersonalNote]>;
    views: SavedContentView[];
    minimal?: boolean;
    notesOnly?: boolean;
  }> = [];

  let currentEntries: Array<readonly [string, PersonalNote]> = [];
  let runningBytes = emptyFrameBytes + 32;

  for (const seg of entrySegments) {
    const wouldExceedCount = currentEntries.length >= maxNotesPerPart;
    const wouldExceedBytes =
      currentEntries.length > 0 && runningBytes + seg.pairBytes > maxBytes;
    if (wouldExceedCount || wouldExceedBytes) {
      chunks.push({ entries: currentEntries, views: [] });
      currentEntries = [];
      runningBytes = emptyFrameBytes + 32;
    }
    currentEntries.push(seg.pair);
    runningBytes += seg.pairBytes;
  }

  if (currentEntries.length > 0 || chunks.length === 0) {
    chunks.push({ entries: currentEntries, views: [] });
  }

  // Attach savedViews to the first chunk if it stays within maxBytes; otherwise place in a dedicated tail chunk.
  if (savedViews.length > 0) {
    const withViewsCandidate = buildSnapshotPayloadString(
      chunks[0].entries,
      savedViews,
      exportedAt,
      { partIndex: 1, totalParts: Math.max(chunks.length, 10) },
    );
    if (utf8ByteLength(withViewsCandidate) <= maxBytes) {
      chunks[0].views = savedViews;
    } else {
      chunks.push({ entries: [], views: savedViews });
    }
  }

  // Exact verification pass: split any multi-entry chunk whose actual serialized UTF-8 exceeds maxBytes,
  // or fall back to minimal framing for a single maximally packed note so existing notes are never truncated.
  const verifiedChunks: typeof chunks = [];
  for (const chunk of chunks) {
    const fullStr = buildSnapshotPayloadString(chunk.entries, chunk.views, exportedAt, {
      partIndex: 999,
      totalParts: 999,
    });
    if (utf8ByteLength(fullStr) <= maxBytes) {
      verifiedChunks.push(chunk);
      continue;
    }
    if (chunk.views.length > 0 && chunk.entries.length > 0) {
      verifiedChunks.push({ entries: [], views: chunk.views });
      chunk.views = [];
    }
    if (chunk.entries.length <= 1) {
      const minV2 = buildSnapshotPayloadString(chunk.entries, [], exportedAt, { minimal: true });
      if (utf8ByteLength(minV2) <= maxBytes) {
        verifiedChunks.push({ entries: chunk.entries, views: [], minimal: true });
      } else {
        verifiedChunks.push({ entries: chunk.entries, views: [], notesOnly: true });
      }
      continue;
    }
    let acc: Array<readonly [string, PersonalNote]> = [];
    for (const entry of chunk.entries) {
      const next = [...acc, entry];
      const probe = buildSnapshotPayloadString(next, [], exportedAt, {
        partIndex: 999,
        totalParts: 999,
      });
      if (acc.length > 0 && utf8ByteLength(probe) > maxBytes) {
        verifiedChunks.push({ entries: acc, views: [] });
        acc = [entry];
      } else {
        acc = next;
      }
    }
    if (acc.length > 0) {
      const tailProbe = buildSnapshotPayloadString(acc, [], exportedAt, {
        partIndex: 999,
        totalParts: 999,
      });
      if (acc.length === 1 && utf8ByteLength(tailProbe) > maxBytes) {
        const minV2 = buildSnapshotPayloadString(acc, [], exportedAt, { minimal: true });
        if (utf8ByteLength(minV2) <= maxBytes) {
          verifiedChunks.push({ entries: acc, views: [], minimal: true });
        } else {
          verifiedChunks.push({ entries: acc, views: [], notesOnly: true });
        }
      } else {
        verifiedChunks.push({ entries: acc, views: [] });
      }
    }
  }

  const totalParts = verifiedChunks.length;
  return verifiedChunks.map((chunk, idx) => {
    const partIndex = idx + 1;
    const json = buildSnapshotPayloadString(chunk.entries, chunk.views, exportedAt, {
      partIndex: totalParts > 1 ? partIndex : undefined,
      totalParts: totalParts > 1 ? totalParts : undefined,
      minimal: chunk.minimal,
      notesOnly: chunk.notesOnly,
    });
    return {
      partIndex,
      totalParts,
      noteCount: chunk.entries.length,
      savedViewCount: chunk.views.length,
      byteLength: utf8ByteLength(json),
      json,
    };
  });
}

export function exportStudyWorkspaceSnapshotJson(): string {
  const parts = exportStudyWorkspaceSnapshotParts();
  if (parts.length === 1) {
    return parts[0].json;
  }
  const notes = readAllPersonalNotes();
  const savedViews = readSavedContentViews();
  return buildSnapshotPayloadString(Object.entries(notes), savedViews, new Date().toISOString(), {
    pretty: true,
  });
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
  if (!rawJson || utf8ByteLength(rawJson) > MAX_STUDY_SNAPSHOT_BYTES) {
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
