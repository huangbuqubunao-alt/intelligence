import type { KnowledgeDeltaProjection } from "./KnowledgeDelta";
import type { PersonalNote } from "./personalNotes";

const CATEGORY_TITLES_ZH: Record<string, string> = {
  content_completed: "本周已完成精读与提炼",
  intelligence_added: "新增高可信洞察",
  intelligence_revised: "洞察验证状态与证据变更",
  topic_updated: "专题新增材料动态",
  source_health: "订阅信源健康波动",
};

const CATEGORY_TITLES_EN: Record<string, string> = {
  content_completed: "Completed Content",
  intelligence_added: "New Intelligence",
  intelligence_revised: "Revised Intelligence",
  topic_updated: "Topics with New Material",
  source_health: "Source Health Changes",
};

function sanitizeWikiTitle(raw: string): string {
  return raw.replace(/[[\]|]/g, "").replace(/\s+/g, " ").trim() || "Untitled";
}

function formatDayStamp(isoString: string): string {
  const parsed = Date.parse(isoString);
  if (!Number.isFinite(parsed)) {
    return new Date().toISOString().slice(0, 10);
  }
  return new Date(parsed).toISOString().slice(0, 10);
}

function formatIsoDateTime(isoString: string, zh: boolean, timeZone?: string): string {
  const parsed = Date.parse(isoString);
  if (!Number.isFinite(parsed)) return isoString;
  try {
    return new Intl.DateTimeFormat(zh ? "zh-CN" : "en-US", {
      timeZone: timeZone || undefined,
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(parsed));
  } catch {
    return new Date(parsed).toISOString().slice(0, 16).replace("T", " ");
  }
}

export function downloadMarkdownText(filename: string, content: string): void {
  if (typeof document === "undefined" || typeof Blob === "undefined" || typeof URL === "undefined") {
    return;
  }
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => {
    URL.revokeObjectURL(objectUrl);
  }, 1500);
}

export function buildWeeklyReviewMarkdown(
  delta: KnowledgeDeltaProjection,
  options?: {
    zh?: boolean;
    personalNotes?: Record<string, PersonalNote>;
    titleByVideoId?: Record<string, string>;
  },
): {
  markdown: string;
  filename: string;
  changedItemCount: number;
  recentNoteCount: number;
} {
  const zh = options?.zh ?? true;
  const titles = zh ? CATEGORY_TITLES_ZH : CATEGORY_TITLES_EN;
  const personalNotes = options?.personalNotes ?? {};
  const titleByVideoId = options?.titleByVideoId ?? {};

  const winStartMs = Date.parse(delta.window_start);
  const winEndMs = Date.parse(delta.window_end);
  const recentNotes = Object.entries(personalNotes)
    .filter(([, note]) => {
      if (!note || (!note.text.trim() && note.tags.length === 0)) return false;
      const updatedMs = Date.parse(note.updatedAt);
      if (!Number.isFinite(updatedMs)) return false;
      if (Number.isFinite(winStartMs) && updatedMs < winStartMs) return false;
      if (Number.isFinite(winEndMs) && updatedMs > winEndMs) return false;
      return true;
    })
    .sort(([, a], [, b]) => b.updatedAt.localeCompare(a.updatedAt));

  const lines: string[] = [];
  lines.push(zh ? "# 每周知识复盘周报" : "# Weekly Knowledge Review");
  lines.push("");
  lines.push(
    zh
      ? `- **复盘窗口**：${formatIsoDateTime(delta.window_start, zh, delta.timezone)} – ${formatIsoDateTime(delta.window_end, zh, delta.timezone)}（${delta.timezone}）`
      : `- **Window**: ${formatIsoDateTime(delta.window_start, zh, delta.timezone)} – ${formatIsoDateTime(delta.window_end, zh, delta.timezone)} (${delta.timezone})`,
  );
  lines.push(
    zh
      ? `- **本周个人批注沉淀**：${recentNotes.length} 篇`
      : `- **Personal Notes Captured**: ${recentNotes.length}`,
  );
  lines.push("");
  lines.push(zh ? "## 周期变化概览" : "## Weekly Summary");
  lines.push("");

  const nonZeroCategories = delta.categories.filter((c) => (c.count ?? 0) > 0 || c.items.length > 0);
  if (nonZeroCategories.length === 0) {
    lines.push(zh ? "- 本周期内无显著数量变动记录。" : "- No notable volume changes recorded in this window.");
  } else {
    for (const cat of nonZeroCategories) {
      const catLabel = titles[cat.kind] ?? cat.kind;
      const countLabel = cat.count === null ? (zh ? "不可用" : "Unavailable") : String(cat.count);
      lines.push(`- **${catLabel}**：${countLabel}`);
    }
  }
  lines.push("");

  let changedItemCount = 0;
  for (const cat of delta.categories) {
    if (!cat.items.length) continue;
    const catLabel = titles[cat.kind] ?? cat.kind;
    lines.push(`## ${catLabel}`);
    lines.push("");
    for (const item of cat.items) {
      changedItemCount += 1;
      const wiki = sanitizeWikiTitle(item.title || item.id);
      const itemTime = formatIsoDateTime(item.occurred_at, zh, delta.timezone);
      const factParts: string[] = [item.label];
      if (item.facts.revision_count) {
        factParts.push(zh ? `修订 ${item.facts.revision_count} 次` : `revisions: ${item.facts.revision_count}`);
      }
      if (item.facts.evidence_set_changed) {
        factParts.push(
          zh
            ? `证据数 ${item.facts.evidence_before ?? 0} → ${item.facts.evidence_after ?? 0}`
            : `evidence ${item.facts.evidence_before ?? 0} → ${item.facts.evidence_after ?? 0}`,
        );
      }
      if (item.facts.state_after) {
        factParts.push(
          zh
            ? `状态 ${item.facts.state_before ?? "未知"} → ${item.facts.state_after}`
            : `state ${item.facts.state_before ?? "Unknown"} → ${item.facts.state_after}`,
        );
      }
      if (item.facts.topic_event_count != null) {
        factParts.push(
          zh
            ? `新增材料变更 ${item.facts.topic_event_count} 次`
            : `material updates: ${item.facts.topic_event_count}`,
        );
      }
      if (item.facts.failure_count != null) {
        factParts.push(
          zh
            ? `受阻检查 ${item.facts.failure_count} 次`
            : `blocked checks: ${item.facts.failure_count}`,
        );
      }
      lines.push(`- [[${wiki}]]（${itemTime}）— ${factParts.join(" · ")}`);
    }
    lines.push("");
  }

  lines.push(zh ? "## 本周个人批注与思考" : "## Weekly Personal Notes");
  lines.push("");
  if (recentNotes.length === 0) {
    lines.push(
      zh
        ? "- 本时间窗口内暂无新增或更新的本机个人批注。"
        : "- No local personal notes added or updated during this window.",
    );
  } else {
    for (const [videoId, note] of recentNotes) {
      const displayTitle = sanitizeWikiTitle(titleByVideoId[videoId] || videoId);
      const tagSuffix = note.tags.length > 0 ? ` — ${note.tags.map((tag) => `#${tag}`).join(" ")}` : "";
      lines.push(`### [[${displayTitle}]]${tagSuffix}`);
      if (note.text.trim()) {
        for (const bodyLine of note.text.trim().split(/\r?\n/)) {
          lines.push(`> ${bodyLine}`);
        }
      }
      lines.push("");
    }
  }

  lines.push(zh ? "## 下周行动与待核查" : "## Next Week Checklist");
  lines.push("");
  lines.push(
    zh
      ? "- [ ] 回顾本周已批注条目，补充遗漏的跨来源对比问题"
      : "- [ ] Review this week's noted items and follow up with cross-source comparisons",
  );
  lines.push(
    zh
      ? "- [ ] 检查状态或证据发生变更的洞察条目，确认是否需要更新结论"
      : "- [ ] Re-verify any revised insights whose evidence sets changed",
  );
  lines.push("");

  return {
    markdown: lines.join("\n"),
    filename: `weekly-knowledge-review-${formatDayStamp(delta.window_end)}.md`,
    changedItemCount,
    recentNoteCount: recentNotes.length,
  };
}
