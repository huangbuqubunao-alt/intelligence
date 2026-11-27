import type { PersonalNote } from "./personalNotes";
import { readVideoAiBrief } from "./WorkspaceAiWidgets";

export interface RelatedContentCandidate {
  video_id: string;
  title: string | null;
  channel_id?: string | null;
  channel_name?: string | null;
  provider?: string;
  work_kind?: string;
  duration_seconds?: number | null;
  ai_brief?: unknown;
}

export interface RelatedContentMatch<T extends RelatedContentCandidate = RelatedContentCandidate> {
  video: T;
  score: number;
  aiScore: number | null;
  reasonLabel: string;
}

function normTokens(items: string[] | undefined): string[] {
  if (!Array.isArray(items)) return [];
  return items.map((s) => s.trim().toLowerCase()).filter(Boolean);
}

export function findRelatedContentItems<T extends RelatedContentCandidate>(
  current: T,
  allVideos: T[],
  notesByVideoId: Record<string, PersonalNote>,
  zh = true,
  limit = 4,
): RelatedContentMatch<T>[] {
  const currentBrief = readVideoAiBrief(current.ai_brief, current.duration_seconds);
  const currentTags = new Set(normTokens(notesByVideoId[current.video_id]?.tags));
  const currentCluster = (currentBrief?.topic_cluster_zh ?? "").trim().toLowerCase();
  const currentTopics = new Set(normTokens(currentBrief?.topics_zh));
  const currentChannel = (current.channel_id || current.channel_name || "").trim().toLowerCase();

  const matches: RelatedContentMatch<T>[] = [];
  const seen = new Set<string>();

  for (const candidate of allVideos) {
    if (!candidate.video_id || candidate.video_id === current.video_id) continue;
    if (seen.has(candidate.video_id) || candidate.work_kind) continue;
    seen.add(candidate.video_id);

    const candBrief = readVideoAiBrief(candidate.ai_brief, candidate.duration_seconds);
    if (candBrief?.is_short_noise) continue;

    let score = 0;
    const sharedTag = (notesByVideoId[candidate.video_id]?.tags ?? []).find((t) =>
      currentTags.has(t.trim().toLowerCase()),
    );
    const sharedTagCount = normTokens(notesByVideoId[candidate.video_id]?.tags).filter((t) =>
      currentTags.has(t),
    ).length;
    if (sharedTagCount > 0) {
      score += sharedTagCount * 5;
    }

    const candCluster = (candBrief?.topic_cluster_zh ?? "").trim();
    const sameCluster = Boolean(currentCluster && candCluster.toLowerCase() === currentCluster);
    if (sameCluster) {
      score += 3;
    }

    const sharedTopic = (candBrief?.topics_zh ?? []).find((t) =>
      currentTopics.has(t.trim().toLowerCase()),
    );
    const sharedTopicCount = normTokens(candBrief?.topics_zh).filter((t) =>
      currentTopics.has(t),
    ).length;
    if (sharedTopicCount > 0) {
      score += sharedTopicCount * 2;
    }

    const candChannel = (candidate.channel_id || candidate.channel_name || "").trim().toLowerCase();
    const sameChannel = Boolean(currentChannel && candChannel && candChannel === currentChannel);
    if (sameChannel) {
      score += 1;
    }

    if (score <= 0) continue;

    const reasonLabel = sharedTag
      ? zh
        ? `共标 #${sharedTag.trim().replace(/^#+/, "")}`
        : `Shared #${sharedTag.trim().replace(/^#+/, "")}`
      : sameCluster
        ? zh
          ? `同专题 · ${candCluster}`
          : `Topic · ${candCluster}`
        : sharedTopic
          ? zh
            ? `关联领域 · ${sharedTopic}`
            : `Topic · ${sharedTopic}`
          : zh
            ? `同来源 · ${candidate.channel_name || ""}`.replace(/ · $/, "")
            : `Same source`;

    matches.push({
      video: candidate,
      score,
      aiScore: candBrief?.score ?? null,
      reasonLabel,
    });
  }

  return matches
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return (b.aiScore ?? 0) - (a.aiScore ?? 0);
    })
    .slice(0, limit);
}
