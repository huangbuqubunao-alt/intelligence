import type { AiResearchSession } from "./WorkspaceAiWidgets";

export function deriveResearchNoteFilename(question: string, sessionId: string): string {
  const shortId =
    sessionId
      .replace(/[^A-Za-z0-9_-]/g, "")
      .slice(-8) || "note";
  const slug = question
    .trim()
    .replace(/[\\/:*?"<>|\p{Cc}\p{Cf}\p{Cs}]/gu, "-")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[.-]+|[.-]+$/g, "")
    .slice(0, 48);
  const stem = slug ? `research-${slug}-${shortId}` : `research-synthesis-${shortId}`;
  return `${stem}.md`;
}

export function buildResearchSynthesisMarkdown(session: AiResearchSession, zh = true): string {
  if (session.refused || !session.citations.length) {
    return "";
  }
  const existing = (session.obsidian_markdown ?? "").trim();
  if (existing) {
    return `${existing}\n`;
  }
  const lines: string[] = [
    `# ${session.question.trim()}`,
    "",
    zh
      ? `> 来源范围：${session.scope_label_zh || "全库对比"} · 生成时间：${session.created_at}`
      : `> Scope: ${session.scope_label_zh || "Library"} · Created: ${session.created_at}`,
    "",
    `## ${zh ? "核心综合结论" : "Grounded Synthesis"}`,
    "",
    session.answer_zh.trim(),
  ];

  if (session.key_takeaways_zh.length > 0) {
    lines.push("", `## ${zh ? "关键要点" : "Key Takeaways"}`, "");
    for (const point of session.key_takeaways_zh) {
      if (point.trim()) lines.push(`- ${point.trim()}`);
    }
  }

  if (session.action_items_zh.length > 0) {
    lines.push(
      "",
      `## ${zh ? "可执行动作（AI 推断建议，非原文事实）" : "Suggested Next Steps (AI Advisory)"}`,
      "",
    );
    for (const item of session.action_items_zh) {
      if (item.trim()) lines.push(`- ${item.trim()}`);
    }
  }

  lines.push("", `## ${zh ? "可验证原文出处" : "Verified Citations"}`, "");
  for (const c of session.citations) {
    const loc = c.timestamp_label ? ` (${c.timestamp_label})` : "";
    lines.push(`- **[${c.ref_label}] ${c.video_title}${loc}**：${c.excerpt}`);
  }

  return `${lines.join("\n").trimEnd()}\n`;
}
