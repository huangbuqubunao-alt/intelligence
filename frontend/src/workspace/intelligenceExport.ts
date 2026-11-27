import { readPersonalNote } from "./personalNotes";
export { downloadMarkdownText } from "./weeklyReviewExport";

export type ExportableEvidenceLink = {
  evidence_id: string;
  original_excerpt?: string | null;
  translated_excerpt?: string | null;
};

export type ExportableIntelligenceItem = {
  status: string;
  trusted: boolean;
  intelligence_id?: string;
  effective_published_at?: string | null;
  linked_topics?: { topic_id: string; name: string }[];
  card?: {
    core_conclusion: string;
    user_relevant_information: string[];
    important_new_information: string[];
    meaningful_details: string[];
    source_display_name: string | null;
    video_id: string;
    video_title: string | null;
    evidence_links?: ExportableEvidenceLink[];
  };
};

function sanitizeWikiTitle(raw: string): string {
  return raw.replace(/[[\]|]/g, "").replace(/\s+/g, " ").trim() || "Untitled";
}

function formatDayStamp(): string {
  return new Date().toISOString().slice(0, 10);
}

export function buildVerifiedIntelligenceMarkdown(
  items: ExportableIntelligenceItem[],
  zh: boolean,
  scopeLabel?: string,
): {
  markdown: string;
  filename: string;
  itemCount: number;
  notedCount: number;
} {
  const verifiedItems = items.filter(
    (item) => item.status === "AVAILABLE" && item.trusted === true && Boolean(item.card),
  );

  const lines: string[] = [];
  lines.push(zh ? "# 已核验洞察知识汇编" : "# Verified Intelligence Dossier");
  lines.push("");
  if (scopeLabel?.trim()) {
    lines.push(zh ? `- **筛选范围**：${scopeLabel.trim()}` : `- **Scope**: ${scopeLabel.trim()}`);
  }
  lines.push(zh ? `- **收录条目**：${verifiedItems.length} 条（仅限通过事实与引用核验）` : `- **Included Items**: ${verifiedItems.length} (verified only)`);
  lines.push(zh ? `- **导出日期**：${formatDayStamp()}` : `- **Exported**: ${formatDayStamp()}`);
  lines.push("");

  let notedCount = 0;

  if (verifiedItems.length === 0) {
    lines.push(
      zh
        ? "> 当前筛选范围下暂无通过核验的可信洞察条目。"
        : "> No verified intelligence entries match the current scope.",
    );
    lines.push("");
  } else {
    for (const item of verifiedItems) {
      const card = item.card!;
      const heading = sanitizeWikiTitle(card.video_title || card.core_conclusion || card.video_id);
      const sourceName = card.source_display_name?.trim() || (zh ? "未知来源" : "Unknown source");
      const dateStr = item.effective_published_at ? item.effective_published_at.slice(0, 10) : "";
      const topicNames = (item.linked_topics ?? []).map((tp) => tp.name).filter(Boolean);

      lines.push(`## [[${heading}]]`);
      lines.push("");
      lines.push(
        zh
          ? `- **来源**：${sourceName}${dateStr ? ` · ${dateStr}` : ""}${topicNames.length ? ` · 专题：${topicNames.join("、")}` : ""}`
          : `- **Source**: ${sourceName}${dateStr ? ` · ${dateStr}` : ""}${topicNames.length ? ` · Topics: ${topicNames.join(", ")}` : ""}`,
      );
      lines.push("");
      lines.push(
        zh
          ? `**核心判断**：${card.core_conclusion}`
          : `**Core Conclusion**: ${card.core_conclusion}`,
      );
      lines.push("");

      const bullets = [
        ...card.user_relevant_information,
        ...card.important_new_information,
        ...card.meaningful_details,
      ]
        .map((line) => line.trim())
        .filter(Boolean);
      const seenBullets = new Set<string>();
      for (const bullet of bullets) {
        if (seenBullets.has(bullet)) continue;
        seenBullets.add(bullet);
        lines.push(`- ${bullet}`);
      }
      if (seenBullets.size > 0) {
        lines.push("");
      }

      const quotes = (card.evidence_links ?? [])
        .map((link) => (link.translated_excerpt || link.original_excerpt || "").trim())
        .filter(Boolean)
        .slice(0, 3);
      if (quotes.length > 0) {
        lines.push(zh ? `**原话证据引用**（共 ${card.evidence_links?.length ?? quotes.length} 处）：` : `**Verified Evidence Quotes** (${card.evidence_links?.length ?? quotes.length}):`);
        for (const quote of quotes) {
          lines.push(`> ${quote.replace(/\r?\n/g, " ")}`);
        }
        lines.push("");
      }

      const personalNote = card.video_id ? readPersonalNote(card.video_id) : null;
      if (personalNote && (personalNote.text.trim() || personalNote.tags.length > 0)) {
        notedCount += 1;
        const tagsLine = personalNote.tags.length
          ? ` (${personalNote.tags.map((tag) => `#${tag}`).join(" ")})`
          : "";
        lines.push(zh ? `### 个人批注${tagsLine}` : `### Personal Note${tagsLine}`);
        if (personalNote.text.trim()) {
          lines.push(personalNote.text.trim());
        }
        lines.push("");
      }
    }
  }

  return {
    markdown: lines.join("\n"),
    filename: `verified-insights-${formatDayStamp()}.md`,
    itemCount: verifiedItems.length,
    notedCount,
  };
}
