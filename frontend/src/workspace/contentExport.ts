import type { PersonalNote } from "./personalNotes";

export type ContentExportItemLike = {
  video_id: string;
  title: string | null;
  channel_name?: string | null;
  provider?: string;
  source_url?: string | null;
  published_at?: string;
};

export type ContentExportBriefLike = {
  score: number;
  recommendation_tier?: string;
  headline_zh: string;
  summary_zh: string;
  topic_cluster_zh?: string;
  product_opportunities_zh?: string[];
  business_opportunities_zh?: string[];
};

export type ContentExportEntry = {
  item: ContentExportItemLike;
  brief: ContentExportBriefLike | null;
  note: PersonalNote | null;
};

function sanitizeWikiTitle(raw: string, fallback: string): string {
  const cleaned = raw.replace(/[[\]|#^\n\r]/g, " ").replace(/\s+/g, " ").trim();
  return cleaned || fallback;
}

function tierLabel(tier: string | undefined, zh: boolean): string | null {
  if (!tier) return null;
  if (tier === "MUST_WATCH") return zh ? "必看干货" : "Must-watch";
  if (tier === "WORTH_SKIMMING") return zh ? "值得泛读" : "Worth skimming";
  if (tier === "SKIP_NOISE") return zh ? "低信噪比" : "Low signal";
  return tier;
}

export function buildSelectedContentMarkdown(
  entries: readonly ContentExportEntry[],
  zh = true,
): { markdown: string; count: number; filename: string } {
  const todayStamp = new Date().toISOString().slice(0, 10);
  const filename = `reading-pack-${todayStamp}.md`;
  if (!entries.length) {
    return {
      markdown: zh ? "# 精选内容阅读包\n\n_尚未选中任何内容。_\n" : "# Selected Reading Pack\n\n_No items selected._\n",
      count: 0,
      filename,
    };
  }

  const lines: string[] = [];
  lines.push(zh ? "# 精选内容阅读包" : "# Selected Content Reading Pack");
  lines.push("");
  lines.push(
    zh
      ? `- 导出日期：${todayStamp}\n- 收录篇数：${entries.length}`
      : `- Exported: ${todayStamp}\n- Items: ${entries.length}`,
  );
  lines.push("");
  lines.push(zh ? "## 目录索引" : "## Contents");
  entries.forEach(({ item, brief }, index) => {
    const title = sanitizeWikiTitle(item.title ?? item.video_id, item.video_id);
    const meta = [
      item.channel_name?.trim() || null,
      brief ? `${brief.score.toFixed(1)}/10` : null,
      brief?.topic_cluster_zh?.trim() ? `[[${sanitizeWikiTitle(brief.topic_cluster_zh, "Topic")}]]` : null,
    ]
      .filter(Boolean)
      .join(" · ");
    lines.push(`${index + 1}. [[${title}]]${meta ? ` — ${meta}` : ""}`);
  });

  for (const { item, brief, note } of entries) {
    const title = sanitizeWikiTitle(item.title ?? item.video_id, item.video_id);
    lines.push("");
    lines.push("---");
    lines.push("");
    lines.push(`## [[${title}]]`);
    const metaParts: string[] = [];
    if (item.channel_name?.trim()) {
      metaParts.push(zh ? `来源：${item.channel_name.trim()}` : `Source: ${item.channel_name.trim()}`);
    }
    if (brief) {
      const tier = tierLabel(brief.recommendation_tier, zh);
      metaParts.push(
        zh
          ? `AI 评分：${brief.score.toFixed(1)}/10${tier ? ` (${tier})` : ""}`
          : `Score: ${brief.score.toFixed(1)}/10${tier ? ` (${tier})` : ""}`,
      );
      if (brief.topic_cluster_zh?.trim()) {
        metaParts.push(
          zh
            ? `专题：[[${sanitizeWikiTitle(brief.topic_cluster_zh, "Topic")}]]`
            : `Topic: [[${sanitizeWikiTitle(brief.topic_cluster_zh, "Topic")}]]`,
        );
      }
    }
    if (item.source_url?.trim()) {
      metaParts.push(`[${zh ? "原始链接" : "Source link"}](${item.source_url.trim()})`);
    }
    if (metaParts.length > 0) {
      lines.push(`- ${metaParts.join(" · ")}`);
    }

    if (brief) {
      if (brief.headline_zh.trim() || brief.summary_zh.trim()) {
        lines.push("");
        lines.push(zh ? "### 核心结论" : "### Core Takeaways");
        if (brief.headline_zh.trim()) {
          lines.push(`**${brief.headline_zh.trim()}**`);
        }
        if (brief.summary_zh.trim() && brief.summary_zh.trim() !== brief.headline_zh.trim()) {
          lines.push("");
          lines.push(brief.summary_zh.trim());
        }
      }
      const opps = [
        ...(brief.product_opportunities_zh ?? []),
        ...(brief.business_opportunities_zh ?? []),
      ].filter((line) => line.trim().length > 0);
      if (opps.length > 0) {
        lines.push("");
        lines.push(zh ? "### AI 产品与商业启发" : "### Product & Business Takeaways");
        for (const opp of opps) {
          lines.push(`- ${opp.trim()}`);
        }
      }
    }

    if (note && (note.text.trim() || note.tags.length > 0)) {
      lines.push("");
      lines.push(zh ? "### 我的个人批注与标签" : "### My Notes & Tags");
      if (note.tags.length > 0) {
        lines.push(note.tags.map((tag) => `#${tag}`).join(" "));
      }
      if (note.text.trim()) {
        lines.push("");
        lines.push(note.text.trim());
      }
    }
  }

  return {
    markdown: `${lines.join("\n")}\n`,
    count: entries.length,
    filename,
  };
}
