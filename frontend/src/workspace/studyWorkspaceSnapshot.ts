import {
  importPersonalNotesObject,
  MAX_PERSONAL_NOTES_IMPORT_COUNT,
  MAX_STUDY_SNAPSHOT_BYTES,
  type PersonalNote,
  readAllPersonalNotes,
  utf8ByteLength,
} from "./personalNotes";
import { mergeSavedContentViews, readSavedContentViews, type SavedContentView } from "./savedViews";

export type SnapshotNoteSegment = {
  video_id: string;
  tags: string[];
  updatedAt: string;
  segment_index: number;
  total_segments: number;
  text_segment: string;
};

export type SnapshotSavedViewSegment = {
  view: Omit<SavedContentView, "searchQuery">;
  segment_index: number;
  total_segments: number;
  search_query_segment: string;
};

export type StudyWorkspaceSnapshotPart = {
  partIndex: number;
  totalParts: number;
  noteCount: number;
  savedViewCount: number;
  byteLength: number;
  json: string;
};

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

export type StudyWorkspaceBatchImportResult = StudyWorkspaceImportResult & {
  missingPartIndices: number[];
  expectedTotalParts: number | null;
  incompleteSegmentedNotes: number;
  incompleteSegmentedViews: number;
};

export class SnapshotImportFileError extends Error {
  readonly fileName: string;
  readonly code: string;

  constructor(code: string, fileName = "") {
    super(code);
    this.code = code;
    this.fileName = fileName;
  }
}

function splitStringByUtf8Budget(text: string, maxSegmentJsonBytes: number): string[] {
  if (!text) return [""];
  const minBudget = 16;
  const budget = Math.max(minBudget, maxSegmentJsonBytes);
  const out: string[] = [];
  let start = 0;

  while (start < text.length) {
    // Lower bound at least 1 code point (2 UTF-16 code units if surrogate pair)
    let low = start + 1;
    if (
      low < text.length &&
      text.charCodeAt(low - 1) >= 0xd800 &&
      text.charCodeAt(low - 1) <= 0xdbff &&
      text.charCodeAt(low) >= 0xdc00 &&
      text.charCodeAt(low) <= 0xdfff
    ) {
      low += 1;
    }
    let high = Math.min(text.length, start + budget);
    let best = low;

    while (low <= high) {
      let mid = Math.floor((low + high) / 2);
      if (
        mid < text.length &&
        mid > start &&
        text.charCodeAt(mid - 1) >= 0xd800 &&
        text.charCodeAt(mid - 1) <= 0xdbff &&
        text.charCodeAt(mid) >= 0xdc00 &&
        text.charCodeAt(mid) <= 0xdfff
      ) {
        if (mid - 1 >= low) {
          mid -= 1;
        } else {
          mid += 1;
        }
      }
      const sliceBytes = utf8ByteLength(JSON.stringify(text.slice(start, mid)));
      if (sliceBytes <= budget) {
        best = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    if (
      best < text.length &&
      text.charCodeAt(best - 1) >= 0xd800 &&
      text.charCodeAt(best - 1) <= 0xdbff &&
      text.charCodeAt(best) >= 0xdc00 &&
      text.charCodeAt(best) <= 0xdfff
    ) {
      if (best - 1 > start) {
        best -= 1;
      } else {
        best += 1;
      }
    }

    out.push(text.slice(start, best));
    start = best;
  }

  return out;
}

type PartDraft = {
  entries: Array<readonly [string, PersonalNote]>;
  views: SavedContentView[];
  noteSegments: SnapshotNoteSegment[];
  viewSegments: SnapshotSavedViewSegment[];
};

function buildSnapshotPayloadString(
  draft: PartDraft,
  exportedAt: string,
  options: {
    pretty?: boolean;
    partIndex?: number;
    totalParts?: number;
  } = {},
): string {
  const notesObj: Record<string, PersonalNote> = {};
  for (const [videoId, note] of draft.entries) {
    notesObj[videoId] = note;
  }
  const payload: Record<string, unknown> = {
    version: 2,
    exported_at: exportedAt,
  };
  if (typeof options.partIndex === "number" && typeof options.totalParts === "number") {
    payload.part_index = options.partIndex;
    payload.total_parts = options.totalParts;
  }
  payload.note_count = draft.entries.length;
  payload.saved_view_count = draft.views.length;
  payload.notes = notesObj;
  payload.saved_views = draft.views;
  if (draft.noteSegments.length > 0) {
    payload.note_segments = draft.noteSegments;
  }
  if (draft.viewSegments.length > 0) {
    payload.saved_view_segments = draft.viewSegments;
  }
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

  // Fast path: everything fits inside a single pretty v2 file
  if (noteEntries.length <= maxNotesPerPart) {
    const wholeDraft: PartDraft = {
      entries: noteEntries,
      views: savedViews,
      noteSegments: [],
      viewSegments: [],
    };
    const pretty = buildSnapshotPayloadString(wholeDraft, exportedAt, { pretty: true });
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

  const reservePartIndex = 99999;
  const emptyDraft: PartDraft = { entries: [], views: [], noteSegments: [], viewSegments: [] };
  const emptyFrameBytes = utf8ByteLength(
    buildSnapshotPayloadString(emptyDraft, exportedAt, {
      partIndex: reservePartIndex,
      totalParts: reservePartIndex,
    }),
  );

  const drafts: PartDraft[] = [];
  let currentEntries: Array<readonly [string, PersonalNote]> = [];
  let runningBytes = emptyFrameBytes + 64;

  const flushWholeNotesDraft = () => {
    if (currentEntries.length > 0) {
      drafts.push({
        entries: currentEntries,
        views: [],
        noteSegments: [],
        viewSegments: [],
      });
      currentEntries = [];
      runningBytes = emptyFrameBytes + 64;
    }
  };

  // Exact verification helper for packing entries into one or more parts
  const appendVerifiedNotesDraft = (entries: Array<readonly [string, PersonalNote]>) => {
    let acc: Array<readonly [string, PersonalNote]> = [];
    for (const entry of entries) {
      const candidate = [...acc, entry];
      const probe = buildSnapshotPayloadString(
        { entries: candidate, views: [], noteSegments: [], viewSegments: [] },
        exportedAt,
        { partIndex: reservePartIndex, totalParts: reservePartIndex },
      );
      if (acc.length > 0 && (candidate.length > maxNotesPerPart || utf8ByteLength(probe) > maxBytes)) {
        drafts.push({ entries: acc, views: [], noteSegments: [], viewSegments: [] });
        acc = [entry];
      } else {
        acc = candidate;
      }
    }
    if (acc.length > 0) {
      const tailProbe = buildSnapshotPayloadString(
        { entries: acc, views: [], noteSegments: [], viewSegments: [] },
        exportedAt,
        { partIndex: reservePartIndex, totalParts: reservePartIndex },
      );
      if (acc.length === 1 && utf8ByteLength(tailProbe) > maxBytes) {
        const [videoId, bigNote] = acc[0];
        const sampleSkeleton = buildSnapshotPayloadString(
          {
            entries: [],
            views: [],
            noteSegments: [
              {
                video_id: videoId,
                tags: bigNote.tags,
                updatedAt: bigNote.updatedAt,
                segment_index: 9999,
                total_segments: 9999,
                text_segment: "",
              },
            ],
            viewSegments: [],
          },
          exportedAt,
          { partIndex: reservePartIndex, totalParts: reservePartIndex },
        );
        const textBudget = maxBytes - utf8ByteLength(sampleSkeleton) - 32;
        const segments = splitStringByUtf8Budget(bigNote.text, textBudget);
        segments.forEach((segText, idx) => {
          drafts.push({
            entries: [],
            views: [],
            noteSegments: [
              {
                video_id: videoId,
                tags: idx === 0 ? bigNote.tags : [],
                updatedAt: bigNote.updatedAt,
                segment_index: idx + 1,
                total_segments: segments.length,
                text_segment: segText,
              },
            ],
            viewSegments: [],
          });
        });
      } else {
        drafts.push({ entries: acc, views: [], noteSegments: [], viewSegments: [] });
      }
    }
  };

  for (const [videoId, note] of noteEntries) {
    const pairBytes = utf8ByteLength(`${JSON.stringify(videoId)}:${JSON.stringify(note)}`) + 1;
    // Check if this single note exceeds maxBytes on its own; if so, segment it losslessly
    if (emptyFrameBytes + pairBytes + 64 > maxBytes) {
      flushWholeNotesDraft();
      appendVerifiedNotesDraft([[videoId, note]]);
      continue;
    }
    if (
      currentEntries.length >= maxNotesPerPart ||
      (currentEntries.length > 0 && runningBytes + pairBytes > maxBytes)
    ) {
      appendVerifiedNotesDraft(currentEntries);
      currentEntries = [];
      runningBytes = emptyFrameBytes + 64;
    }
    currentEntries.push([videoId, note]);
    runningBytes += pairBytes;
  }
  if (currentEntries.length > 0) {
    appendVerifiedNotesDraft(currentEntries);
  }
  if (drafts.length === 0) {
    drafts.push({ entries: [], views: [], noteSegments: [], viewSegments: [] });
  }

  // Pack savedViews individually (never bulk-dropped; segmented only if a single view exceeds maxBytes)
  for (const view of savedViews) {
    let placed = false;
    for (const draft of drafts) {
      if (draft.noteSegments.length > 0 || draft.viewSegments.length > 0) continue;
      const probe = buildSnapshotPayloadString(
        { ...draft, views: [...draft.views, view] },
        exportedAt,
        { partIndex: reservePartIndex, totalParts: reservePartIndex },
      );
      if (utf8ByteLength(probe) <= maxBytes) {
        draft.views.push(view);
        placed = true;
        break;
      }
    }
    if (placed) continue;

    const soloDraft: PartDraft = {
      entries: [],
      views: [view],
      noteSegments: [],
      viewSegments: [],
    };
    const soloProbe = buildSnapshotPayloadString(soloDraft, exportedAt, {
      partIndex: reservePartIndex,
      totalParts: reservePartIndex,
    });
    if (utf8ByteLength(soloProbe) <= maxBytes) {
      drafts.push(soloDraft);
      continue;
    }

    // Single saved view exceeds maxBytes -> losslessly split searchQuery into dedicated viewSegments parts
    const { searchQuery, ...viewMeta } = view;
    const sampleSkeleton = buildSnapshotPayloadString(
      {
        entries: [],
        views: [],
        noteSegments: [],
        viewSegments: [
          {
            view: viewMeta,
            segment_index: 9999,
            total_segments: 9999,
            search_query_segment: "",
          },
        ],
      },
      exportedAt,
      { partIndex: reservePartIndex, totalParts: reservePartIndex },
    );
    const queryBudget = maxBytes - utf8ByteLength(sampleSkeleton) - 32;
    const querySegments = splitStringByUtf8Budget(searchQuery, queryBudget);
    querySegments.forEach((segText, idx) => {
      drafts.push({
        entries: [],
        views: [],
        noteSegments: [],
        viewSegments: [
          {
            view: viewMeta,
            segment_index: idx + 1,
            total_segments: querySegments.length,
            search_query_segment: segText,
          },
        ],
      });
    });
  }

  const totalParts = drafts.length;
  const parts = drafts.map((draft, idx) => {
    const partIndex = idx + 1;
    const json = buildSnapshotPayloadString(draft, exportedAt, {
      partIndex: totalParts > 1 ? partIndex : undefined,
      totalParts: totalParts > 1 ? totalParts : undefined,
    });
    return {
      partIndex,
      totalParts,
      noteCount: draft.entries.length,
      savedViewCount: draft.views.length,
      byteLength: utf8ByteLength(json),
      json,
    };
  });

  // Fail-closed pre-download invariants: size <= maxBytes, count <= maxNotesPerPart, 100% note & view coverage
  const coveredNoteIds = new Set<string>();
  const noteSegTracker = new Map<string, { total: number; seen: Set<number> }>();
  const coveredViewIds = new Set<string>();
  const viewSegTracker = new Map<string, { total: number; seen: Set<number> }>();

  for (let i = 0; i < parts.length; i += 1) {
    const part = parts[i];
    const draft = drafts[i];
    if (part.byteLength > maxBytes || part.noteCount > maxNotesPerPart) {
      throw new Error("STUDY_SNAPSHOT_EXPORT_INVARIANT_FAILED");
    }
    for (const [vid] of draft.entries) {
      coveredNoteIds.add(vid);
    }
    for (const seg of draft.noteSegments) {
      const t = noteSegTracker.get(seg.video_id) ?? {
        total: seg.total_segments,
        seen: new Set<number>(),
      };
      t.seen.add(seg.segment_index);
      noteSegTracker.set(seg.video_id, t);
    }
    for (const v of draft.views) {
      coveredViewIds.add(v.id);
    }
    for (const seg of draft.viewSegments) {
      const t = viewSegTracker.get(seg.view.id) ?? {
        total: seg.total_segments,
        seen: new Set<number>(),
      };
      t.seen.add(seg.segment_index);
      viewSegTracker.set(seg.view.id, t);
    }
  }

  for (const [vid, tracker] of noteSegTracker.entries()) {
    if (tracker.seen.size === tracker.total && tracker.total > 0) {
      coveredNoteIds.add(vid);
    }
  }
  for (const [viewId, tracker] of viewSegTracker.entries()) {
    if (tracker.seen.size === tracker.total && tracker.total > 0) {
      coveredViewIds.add(viewId);
    }
  }

  if (
    coveredNoteIds.size !== noteEntries.length ||
    coveredViewIds.size !== savedViews.length
  ) {
    throw new Error("STUDY_SNAPSHOT_EXPORT_INVARIANT_FAILED");
  }

  return parts;
}

export function exportStudyWorkspaceSnapshotJson(): string {
  const parts = exportStudyWorkspaceSnapshotParts();
  if (parts.length === 1) {
    return parts[0].json;
  }
  const notes = readAllPersonalNotes();
  const savedViews = readSavedContentViews();
  return buildSnapshotPayloadString(
    { entries: Object.entries(notes), views: savedViews, noteSegments: [], viewSegments: [] },
    new Date().toISOString(),
    { pretty: true },
  );
}

function isValidNoteSegment(raw: unknown): raw is SnapshotNoteSegment {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return false;
  const o = raw as Record<string, unknown>;
  return (
    typeof o.video_id === "string" &&
    o.video_id.length > 0 &&
    typeof o.segment_index === "number" &&
    Number.isInteger(o.segment_index) &&
    o.segment_index >= 1 &&
    typeof o.total_segments === "number" &&
    Number.isInteger(o.total_segments) &&
    o.total_segments >= o.segment_index &&
    typeof o.text_segment === "string"
  );
}

function isValidViewSegment(raw: unknown): raw is SnapshotSavedViewSegment {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return false;
  const o = raw as Record<string, unknown>;
  if (!o.view || typeof o.view !== "object" || Array.isArray(o.view)) return false;
  const viewObj = o.view as Record<string, unknown>;
  return (
    typeof viewObj.id === "string" &&
    viewObj.id.trim().length > 0 &&
    typeof viewObj.name === "string" &&
    viewObj.name.trim().length > 0 &&
    typeof o.segment_index === "number" &&
    Number.isInteger(o.segment_index) &&
    o.segment_index >= 1 &&
    typeof o.total_segments === "number" &&
    Number.isInteger(o.total_segments) &&
    o.total_segments >= o.segment_index &&
    typeof o.search_query_segment === "string"
  );
}

export function importStudyWorkspaceSnapshotPayloads(
  rawFiles: ReadonlyArray<{ name?: string; rawJson: string }>,
): StudyWorkspaceBatchImportResult {
  if (rawFiles.length === 0) {
    throw new SnapshotImportFileError("EMPTY_STUDY_SNAPSHOT_LIST");
  }

  // Phase 1: Parse and validate EVERY file atomically before writing anything to localStorage
  const parsedFiles: Array<{
    obj: Record<string, unknown>;
    notesObj: Record<string, unknown>;
    viewsArr: unknown[];
    noteSegments: SnapshotNoteSegment[];
    viewSegments: SnapshotSavedViewSegment[];
  }> = [];
  const expectedTotals = new Set<number>();
  const seenPartIndices = new Set<number>();

  for (const item of rawFiles) {
    const fileName = item.name ?? "";
    const rawJson = item.rawJson;
    if (!rawJson || utf8ByteLength(rawJson) > MAX_STUDY_SNAPSHOT_BYTES) {
      throw new SnapshotImportFileError("INVALID_STUDY_SNAPSHOT_FILE", fileName);
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(rawJson);
    } catch {
      throw new SnapshotImportFileError("INVALID_STUDY_SNAPSHOT_JSON", fileName);
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new SnapshotImportFileError("INVALID_STUDY_SNAPSHOT_SHAPE", fileName);
    }
    const obj = parsed as Record<string, unknown>;
    if (obj.version !== undefined && obj.version !== 1 && obj.version !== 2) {
      throw new SnapshotImportFileError("UNSUPPORTED_STUDY_SNAPSHOT_VERSION", fileName);
    }
    const notesCandidate = obj.notes;
    if (!notesCandidate || typeof notesCandidate !== "object" || Array.isArray(notesCandidate)) {
      throw new SnapshotImportFileError("MISSING_NOTES_MAP", fileName);
    }
    if (Object.keys(notesCandidate).length > MAX_PERSONAL_NOTES_IMPORT_COUNT) {
      throw new SnapshotImportFileError("TOO_MANY_PERSONAL_NOTES", fileName);
    }

    if (
      typeof obj.total_parts === "number" &&
      Number.isInteger(obj.total_parts) &&
      obj.total_parts > 1 &&
      typeof obj.part_index === "number" &&
      Number.isInteger(obj.part_index) &&
      obj.part_index >= 1 &&
      obj.part_index <= obj.total_parts
    ) {
      expectedTotals.add(obj.total_parts);
      seenPartIndices.add(obj.part_index);
    }

    const noteSegments = Array.isArray(obj.note_segments)
      ? obj.note_segments.filter(isValidNoteSegment)
      : [];
    const viewSegments = Array.isArray(obj.saved_view_segments)
      ? obj.saved_view_segments.filter(isValidViewSegment)
      : [];

    parsedFiles.push({
      obj,
      notesObj: notesCandidate as Record<string, unknown>,
      viewsArr: Array.isArray(obj.saved_views) ? obj.saved_views : [],
      noteSegments,
      viewSegments,
    });
  }

  // Detect missing shard indices when files come from a declared multi-part set
  let expectedTotalParts: number | null = null;
  const missingPartIndices: number[] = [];
  if (expectedTotals.size === 1) {
    expectedTotalParts = Array.from(expectedTotals)[0];
    for (let idx = 1; idx <= expectedTotalParts; idx += 1) {
      if (!seenPartIndices.has(idx)) {
        missingPartIndices.push(idx);
      }
    }
  }

  // Group and reassemble segmented notes across all uploaded parts
  const noteSegGroups = new Map<string, SnapshotNoteSegment[]>();
  const viewSegGroups = new Map<string, SnapshotSavedViewSegment[]>();
  for (const pf of parsedFiles) {
    for (const seg of pf.noteSegments) {
      const list = noteSegGroups.get(seg.video_id) ?? [];
      list.push(seg);
      noteSegGroups.set(seg.video_id, list);
    }
    for (const seg of pf.viewSegments) {
      const list = viewSegGroups.get(seg.view.id) ?? [];
      list.push(seg);
      viewSegGroups.set(seg.view.id, list);
    }
  }

  const reassembledNotes: Record<string, PersonalNote> = {};
  let incompleteSegmentedNotes = 0;
  for (const [videoId, segs] of noteSegGroups.entries()) {
    const total = segs[0].total_segments;
    const byIdx = new Map<number, SnapshotNoteSegment>();
    for (const seg of segs) {
      if (seg.total_segments === total && !byIdx.has(seg.segment_index)) {
        byIdx.set(seg.segment_index, seg);
      }
    }
    if (byIdx.size !== total) {
      incompleteSegmentedNotes += 1;
      continue;
    }
    let fullText = "";
    let tags: string[] = [];
    let updatedAt = new Date(0).toISOString();
    let complete = true;
    for (let idx = 1; idx <= total; idx += 1) {
      const partSeg = byIdx.get(idx);
      if (!partSeg) {
        complete = false;
        break;
      }
      fullText += partSeg.text_segment;
      if (Array.isArray(partSeg.tags) && partSeg.tags.length > 0 && tags.length === 0) {
        tags = partSeg.tags;
      }
      if (partSeg.updatedAt) {
        updatedAt = partSeg.updatedAt;
      }
    }
    if (!complete) {
      incompleteSegmentedNotes += 1;
      continue;
    }
    reassembledNotes[videoId] = { text: fullText, tags, updatedAt };
  }

  const reassembledViews: SavedContentView[] = [];
  let incompleteSegmentedViews = 0;
  for (const [, segs] of viewSegGroups.entries()) {
    const total = segs[0].total_segments;
    const byIdx = new Map<number, SnapshotSavedViewSegment>();
    for (const seg of segs) {
      if (seg.total_segments === total && !byIdx.has(seg.segment_index)) {
        byIdx.set(seg.segment_index, seg);
      }
    }
    if (byIdx.size !== total) {
      incompleteSegmentedViews += 1;
      continue;
    }
    let fullQuery = "";
    let complete = true;
    for (let idx = 1; idx <= total; idx += 1) {
      const partSeg = byIdx.get(idx);
      if (!partSeg) {
        complete = false;
        break;
      }
      fullQuery += partSeg.search_query_segment;
    }
    if (!complete) {
      incompleteSegmentedViews += 1;
      continue;
    }
    const meta = segs[0].view;
    reassembledViews.push({
      ...meta,
      searchQuery: fullQuery,
    });
  }

  // Phase 2: Persist validated notes and views
  let importedNotes = 0;
  let noteConflicts = 0;
  let skippedOlderNotes = 0;
  let totalNotes = Object.keys(readAllPersonalNotes()).length;
  let notesPersisted = true;

  for (const pf of parsedFiles) {
    if (Object.keys(pf.notesObj).length === 0) continue;
    const res = importPersonalNotesObject(pf.obj);
    importedNotes += res.importedCount;
    noteConflicts += res.conflictCount;
    skippedOlderNotes += res.skippedOlderCount;
    totalNotes = res.totalCount;
    if (!res.persisted) notesPersisted = false;
  }

  if (Object.keys(reassembledNotes).length > 0) {
    const res = importPersonalNotesObject({ version: 2, notes: reassembledNotes });
    importedNotes += res.importedCount;
    noteConflicts += res.conflictCount;
    skippedOlderNotes += res.skippedOlderCount;
    totalNotes = res.totalCount;
    if (!res.persisted) notesPersisted = false;
  }

  const combinedViews: unknown[] = [];
  for (const pf of parsedFiles) {
    combinedViews.push(...pf.viewsArr);
  }
  combinedViews.push(...reassembledViews);

  const viewResult =
    combinedViews.length > 0
      ? mergeSavedContentViews(combinedViews)
      : {
          importedCount: 0,
          totalCount: readSavedContentViews().length,
          persisted: true,
          failedCount: 0,
        };

  return {
    importedNotes,
    totalNotes,
    noteConflicts,
    skippedOlderNotes,
    notesPersisted,
    importedViews: viewResult.importedCount,
    totalViews: viewResult.totalCount,
    viewsPersisted: viewResult.persisted,
    failedViewsCount: viewResult.failedCount,
    missingPartIndices,
    expectedTotalParts,
    incompleteSegmentedNotes,
    incompleteSegmentedViews,
  };
}

export function importStudyWorkspaceSnapshotJson(rawJson: string): StudyWorkspaceImportResult {
  const batch = importStudyWorkspaceSnapshotPayloads([{ rawJson }]);
  return {
    importedNotes: batch.importedNotes,
    totalNotes: batch.totalNotes,
    noteConflicts: batch.noteConflicts,
    skippedOlderNotes: batch.skippedOlderNotes,
    notesPersisted: batch.notesPersisted,
    importedViews: batch.importedViews,
    totalViews: batch.totalViews,
    viewsPersisted: batch.viewsPersisted,
    failedViewsCount: batch.failedViewsCount,
  };
}
