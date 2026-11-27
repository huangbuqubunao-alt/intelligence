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

export type ResearchLensId =
  | "consensus_diff"
  | "product_biz"
  | "action_plan"
  | "risk_audit";

export interface ResearchLens {
  id: ResearchLensId;
  labelZh: string;
  labelEn: string;
}

export const RESEARCH_LENSES: ResearchLens[] = [
  { id: "consensus_diff", labelZh: "视角 · 共识与分歧", labelEn: "Lens · Consensus & Diff" },
  { id: "product_biz", labelZh: "视角 · 产品化与变现", labelEn: "Lens · Product & Biz" },
  { id: "action_plan", labelZh: "视角 · 落地行动清单", labelEn: "Lens · Action Plan" },
  { id: "risk_audit", labelZh: "视角 · 反例与盲区", labelEn: "Lens · Risks & Blindspots" },
];

export function buildLensPrompt(
  lensId: ResearchLensId,
  scopeLabel: string,
  zh = true,
): string {
  const scope = scopeLabel.trim() || (zh ? "当前资料库" : "the current library");
  switch (lensId) {
    case "consensus_diff":
      return zh
        ? `围绕「${scope}」，对比各来源核心观点的明确共识、根本分歧，以及分别适用的前提边界（附原话引用）`
        : `Across "${scope}", compare where sources agree, where they fundamentally diverge, and the conditions under which each claim holds (with grounded citations).`;
    case "product_biz":
      return zh
        ? `从「${scope}」中提炼高留存产品设计切入点、目标付费人群痛点与可持续商业变现路径`
        : `From "${scope}", extract high-retention product opportunities, target user pain points, and viable monetization paths.`;
    case "action_plan":
      return zh
        ? `基于「${scope}」的已验证结论，整理一条可在一周内落地的优先实验步骤清单与验收指标`
        : `Based on grounded findings in "${scope}", synthesize a prioritized 1-week execution checklist and measurable verification signals.`;
    case "risk_audit":
      return zh
        ? `审视「${scope}」中提到的实践失败案例、反直觉警告与容易被忽略的工程/运营盲区`
        : `Audit "${scope}" for documented failure modes, counter-intuitive warnings, and overlooked engineering or operational blindspots.`;
  }
}

function normalizeSynthesisForDossier(
  singleMarkdown: string,
  index: number,
  pinned: boolean,
  zh: boolean,
): string {
  const lines = singleMarkdown.trimEnd().split("\n");
  if (lines.length > 0 && lines[0].startsWith("# ")) {
    const title = lines[0].slice(2).trim();
    const pinPrefix = pinned ? (zh ? "[置顶] " : "[Pinned] ") : "";
    lines[0] = `## ${index + 1}. ${pinPrefix}${title}`;
  }
  return lines
    .map((line, i) => (i > 0 && line.startsWith("## ") ? `#${line}` : line))
    .join("\n");
}

export function buildResearchDossierMarkdown(
  sessions: AiResearchSession[],
  zh = true,
): { markdown: string; includedCount: number; skippedCount: number } {
  const grounded = sessions
    .filter((s) => !s.refused && s.citations.length > 0)
    .sort((a, b) => {
      const pinDiff = Number(Boolean(b.pinned)) - Number(Boolean(a.pinned));
      if (pinDiff !== 0) return pinDiff;
      return (Date.parse(b.created_at || "") || 0) - (Date.parse(a.created_at || "") || 0);
    });
  const skippedCount = sessions.length - grounded.length;
  const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");

  const header: string[] = [
    zh ? "# 跨来源研究汇编" : "# Cross-Source Research Dossier",
    "",
    zh
      ? `- 导出时间：${stamp} UTC\n- 收录已核验问答：${grounded.length} 条${skippedCount > 0 ? `\n- 已自动过滤未核验/拒答条目：${skippedCount} 条` : ""}`
      : `- Exported at: ${stamp} UTC\n- Grounded sessions included: ${grounded.length}${skippedCount > 0 ? `\n- Refused / uncited sessions excluded: ${skippedCount}` : ""}`,
  ];

  if (grounded.length === 0) {
    header.push("");
    header.push(
      zh
        ? "_暂无可导出的已核验跨视频研究问答（无引用或拒答会话已按规则排除）。_"
        : "_No grounded Q&A sessions available to export (refused or uncited outputs excluded)._",
    );
    return { markdown: `${header.join("\n")}\n`, includedCount: 0, skippedCount };
  }

  header.push("", zh ? "## 目录" : "## Table of Contents", "");
  grounded.forEach((s, idx) => {
    const pinTag = s.pinned ? (zh ? " [置顶]" : " [Pinned]") : "";
    header.push(`${idx + 1}. ${s.question.trim()}${pinTag}`);
  });

  const sections = grounded
    .map((s, idx) => {
      const single = buildResearchSynthesisMarkdown(s, zh);
      if (!single) return "";
      return normalizeSynthesisForDossier(single, idx, Boolean(s.pinned), zh);
    })
    .filter(Boolean);

  return {
    markdown: `${header.join("\n")}\n\n---\n\n${sections.join("\n\n---\n\n")}\n`,
    includedCount: grounded.length,
    skippedCount,
  };
}
