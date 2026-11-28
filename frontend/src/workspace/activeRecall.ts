import { readAllPersonalNotes } from "./personalNotes";

export type ActiveRecallCard = {
  videoId: string;
  title: string;
  channelName: string | null;
  topicName: string | null;
  coreConclusion: string;
  keyPoints: string[];
  personalNoteText: string;
  personalTags: string[];
  hasPersonalNote: boolean;
  score: number | null;
};

export type RecallVideoInput = {
  video_id: string;
  title: string | null;
  channel_name?: string | null;
  duration_seconds?: number | null;
  ai_brief?: unknown;
};

export type RecallIntelligenceInput = {
  status: string;
  trusted: boolean;
  linked_topics?: { topic_id: string; name: string }[];
  card?: {
    core_conclusion: string;
    user_relevant_information?: string[];
    important_new_information?: string[];
    meaningful_details?: string[];
    source_display_name?: string | null;
    video_id: string;
    video_title?: string | null;
  };
};

export const ACTIVE_RECALL_CHANGED_EVENT = "yia:active-recall-changed";
const ACTIVE_RECALL_STORAGE_KEY = "yia.active_recall_today.v1";

export function localCalendarDateKey(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dispatchRecallChanged(): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(new CustomEvent(ACTIVE_RECALL_CHANGED_EVENT));
  }
}

export function readRecalledTodayIds(now: Date = new Date()): Set<string> {
  if (typeof localStorage === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(ACTIVE_RECALL_STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return new Set();
    const obj = parsed as Record<string, unknown>;
    if (obj.date !== localCalendarDateKey(now)) {
      return new Set();
    }
    if (!Array.isArray(obj.ids)) return new Set();
    return new Set(obj.ids.filter((id): id is string => typeof id === "string" && id.trim().length > 0));
  } catch {
    return new Set();
  }
}

export function markRecalledToday(videoId: string, now: Date = new Date()): Set<string> {
  const cleanId = videoId.trim();
  const current = readRecalledTodayIds(now);
  if (!cleanId) return current;
  current.add(cleanId);
  try {
    localStorage.setItem(
      ACTIVE_RECALL_STORAGE_KEY,
      JSON.stringify({
        date: localCalendarDateKey(now),
        ids: Array.from(current),
      }),
    );
  } catch {
    // Ignore restricted webview storage quota errors cleanly.
  }
  dispatchRecallChanged();
  return current;
}

export function clearRecalledToday(): void {
  try {
    localStorage.removeItem(ACTIVE_RECALL_STORAGE_KEY);
  } catch {
    // Ignore storage removal errors.
  }
  dispatchRecallChanged();
}

function readAiBriefObject(raw: unknown): {
  isShortNoise: boolean;
  score: number | null;
  headlineZh: string;
  keyTakeaways: string[];
  topicClusterZh: string | null;
} {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return { isShortNoise: false, score: null, headlineZh: "", keyTakeaways: [], topicClusterZh: null };
  }
  const obj = raw as Record<string, unknown>;
  const isShortNoise = obj.is_short_noise === true || obj.recommendation_tier === "SKIP_NOISE";
  const score = typeof obj.score === "number" && Number.isFinite(obj.score) ? obj.score : null;
  const headlineZh =
    typeof obj.headline_zh === "string" && obj.headline_zh.trim()
      ? obj.headline_zh.trim()
      : typeof obj.one_sentence_summary_zh === "string"
        ? obj.one_sentence_summary_zh.trim()
        : "";
  const takeaways = Array.isArray(obj.key_takeaways_zh)
    ? obj.key_takeaways_zh.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
  const topicClusterZh =
    typeof obj.topic_cluster_zh === "string" && obj.topic_cluster_zh.trim()
      ? obj.topic_cluster_zh.trim()
      : null;
  return { isShortNoise, score, headlineZh, keyTakeaways: takeaways, topicClusterZh };
}

export function buildActiveRecallDeck(
  videos: RecallVideoInput[],
  intelligence: RecallIntelligenceInput[],
  zh: boolean,
): ActiveRecallCard[] {
  const personalNotes = readAllPersonalNotes();
  const intelByVideoId = new Map<string, RecallIntelligenceInput>();
  for (const item of intelligence) {
    if (item.status !== "AVAILABLE" || !item.trusted || !item.card?.video_id) continue;
    const vid = item.card.video_id.trim();
    if (!vid || intelByVideoId.has(vid)) continue;
    intelByVideoId.set(vid, item);
  }

  const videoById = new Map<string, RecallVideoInput>();
  const highScoreVideoIds: string[] = [];
  for (const v of videos) {
    if (!v.video_id) continue;
    videoById.set(v.video_id, v);
    const brief = readAiBriefObject(v.ai_brief);
    if (!brief.isShortNoise && brief.score !== null && brief.score >= 8 && brief.headlineZh) {
      highScoreVideoIds.push(v.video_id);
    }
  }

  const candidateIds = new Set<string>([
    ...Object.keys(personalNotes),
    ...Array.from(intelByVideoId.keys()),
    ...highScoreVideoIds,
  ]);

  const cards: ActiveRecallCard[] = [];
  for (const videoId of candidateIds) {
    const video = videoById.get(videoId);
    const intel = intelByVideoId.get(videoId);
    const brief = readAiBriefObject(video?.ai_brief);
    if (brief.isShortNoise) continue;

    const note = personalNotes[videoId];
    const hasPersonalNote = Boolean(note && (note.text.trim().length > 0 || note.tags.length > 0));
    const coreConclusion =
      intel?.card?.core_conclusion?.trim() ||
      brief.headlineZh ||
      "";
    if (!hasPersonalNote && !coreConclusion) continue;

    const keyPoints = [
      ...(intel?.card?.user_relevant_information ?? []),
      ...(intel?.card?.important_new_information ?? []),
      ...brief.keyTakeaways,
    ]
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line, idx, arr) => arr.indexOf(line) === idx && line !== coreConclusion)
      .slice(0, 2);

    const title =
      video?.title?.trim() ||
      intel?.card?.video_title?.trim() ||
      coreConclusion ||
      videoId;

    cards.push({
      videoId,
      title,
      channelName:
        video?.channel_name?.trim() ||
        intel?.card?.source_display_name?.trim() ||
        null,
      topicName:
        intel?.linked_topics?.[0]?.name?.trim() ||
        brief.topicClusterZh ||
        null,
      coreConclusion:
        coreConclusion ||
        (zh ? "回顾你在本篇写下的思考批注与标签关联" : "Recall your saved note and tags for this item"),
      keyPoints,
      personalNoteText: note?.text?.trim() ?? "",
      personalTags: note?.tags ?? [],
      hasPersonalNote,
      score: brief.score,
    });
  }

  return cards.sort((a, b) => {
    if (a.hasPersonalNote !== b.hasPersonalNote) return a.hasPersonalNote ? -1 : 1;
    const scoreA = a.score ?? 0;
    const scoreB = b.score ?? 0;
    if (scoreB !== scoreA) return scoreB - scoreA;
    return a.title.localeCompare(b.title);
  });
}
