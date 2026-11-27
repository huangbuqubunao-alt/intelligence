import type { AiResearchCitation, AiResearchSession } from "./WorkspaceAiWidgets";

export type ResearchTrustTier =
  | "VERIFIED_EXACT"
  | "PARTIAL_OR_HEURISTIC"
  | "NEEDS_REVERIFICATION"
  | "REFUSED";

export function getVerifiableCitations(session: AiResearchSession): AiResearchCitation[] {
  return (session.citations ?? []).filter(
    (c) => c.verified !== false && Boolean(c.video_id?.trim()),
  );
}

export function classifyResearchSessionTrust(session: AiResearchSession): ResearchTrustTier {
  const verifiable = getVerifiableCitations(session);
  if (
    session.refused ||
    session.answer_status === "REFUSED_INSUFFICIENT_EVIDENCE" ||
    session.source_integrity_status === "REFUSED" ||
    verifiable.length === 0
  ) {
    return "REFUSED";
  }
  if (
    session.answer_status === "NEEDS_REVERIFICATION" ||
    session.source_integrity_status === "NEEDS_REVERIFICATION" ||
    session.fact_verification_state === "NEEDS_REVERIFICATION" ||
    session.fact_verification_state === "CITATION_FACT_CONFLICT" ||
    session.fact_verification_state === "NO_VERIFIED_CITATIONS" ||
    session.fact_verification_state === "UNSUPPORTED_CLAIM_UNVERIFIED"
  ) {
    return "NEEDS_REVERIFICATION";
  }
  if (
    session.fact_verification_state === "SUPPORTED" &&
    session.source_integrity_status === "VERIFIED" &&
    session.contains_heuristic_claims !== true
  ) {
    return "VERIFIED_EXACT";
  }
  return "PARTIAL_OR_HEURISTIC";
}

export function researchTrustLabel(
  tier: ResearchTrustTier,
  session: AiResearchSession,
  zh = true,
): string {
  if (tier === "VERIFIED_EXACT") {
    return zh ? "严格已核验（出处完整）" : "Strictly verified (all claims supported)";
  }
  if (tier === "NEEDS_REVERIFICATION") {
    return zh ? "待复核（暂不可直接入库）" : "Needs re-verification";
  }
  if (tier === "REFUSED") {
    return zh ? "已拒答 / 无可核验引用" : "Refused / No verifiable citations";
  }
  if (
    session.fact_verification_state === "PARTIAL_PRUNED_HEURISTIC" ||
    session.contains_heuristic_claims
  ) {
    return zh
      ? "部分未支持内容已裁剪 · 含启发式关联（请核对原话）"
      : "Unsupported parts pruned · Contains heuristic statements (verify sources)";
  }
  if (session.fact_verification_state === "PARTIAL_PRUNED") {
    return zh
      ? "部分未支持内容已裁剪（请核对引用）"
      : "Partially pruned · Verify cited excerpts";
  }
  if (session.fact_verification_state === "HEURISTIC_ONLY") {
    return zh ? "启发式相关 · 请核对原话" : "Heuristic match · Verify sources";
  }
  return zh
    ? "未附完整核验状态 · 请核对原文出处"
    : "Verification posture incomplete · Verify sources";
}

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

function stripLeadingFrontmatter(markdown: string): {
  frontmatter: string;
  body: string;
} {
  const trimmed = markdown.trim();
  if (trimmed.startsWith("---\n") || trimmed.startsWith("---\r\n")) {
    const closeMatch = /\r?\n---(?:\r?\n|$)/.exec(trimmed.slice(3));
    if (closeMatch && closeMatch.index !== undefined) {
      const splitEnd = 3 + closeMatch.index + closeMatch[0].length;
      return {
        frontmatter: trimmed.slice(0, splitEnd).trimEnd(),
        body: trimmed.slice(splitEnd).trimStart(),
      };
    }
  }
  return { frontmatter: "", body: trimmed };
}

export function buildResearchSynthesisMarkdown(session: AiResearchSession, zh = true): string {
  const tier = classifyResearchSessionTrust(session);
  if (tier === "REFUSED" || tier === "NEEDS_REVERIFICATION") {
    return "";
  }
  const verifiable = getVerifiableCitations(session);
  const trustNotice = researchTrustLabel(tier, session, zh);
  const existing = (session.obsidian_markdown ?? "").trim();
  if (existing) {
    if (
      tier === "PARTIAL_OR_HEURISTIC" &&
      !/启发式|部分未支持|PARTIAL_PRUNED|heuristic/i.test(existing)
    ) {
      const { frontmatter, body } = stripLeadingFrontmatter(existing);
      const bodyLines = body.split("\n");
      const h1Idx = bodyLines.findIndex((line) => line.startsWith("# "));
      const noticeLine = zh
        ? `> 证据等级：${trustNotice}`
        : `> Verification posture: ${trustNotice}`;
      if (h1Idx >= 0) {
        bodyLines.splice(h1Idx + 1, 0, "", noticeLine);
      } else {
        bodyLines.unshift(noticeLine, "");
      }
      const nextBody = bodyLines.join("\n").trimEnd();
      return frontmatter ? `${frontmatter}\n\n${nextBody}\n` : `${nextBody}\n`;
    }
    return `${existing}\n`;
  }
  const lines: string[] = [
    `# ${session.question.trim()}`,
    "",
    zh
      ? `> 来源范围：${session.scope_label_zh || "全库对比"} · 证据等级：${trustNotice} · 生成时间：${session.created_at}`
      : `> Scope: ${session.scope_label_zh || "Library"} · Trust: ${trustNotice} · Created: ${session.created_at}`,
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
  for (const c of verifiable) {
    const loc = c.timestamp_label ? ` (${c.timestamp_label})` : "";
    lines.push(`- **[${c.ref_label}] ${c.video_title}${loc}**：${c.excerpt}`);
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function buildSourceNoteResearchExcerpt(
  session: AiResearchSession,
  zh = true,
): {
  quoteMarkdown: string;
  primaryVideoId: string;
  primaryVideoTitle: string;
  distinctSourceCount: number;
  tier: ResearchTrustTier;
} | null {
  const tier = classifyResearchSessionTrust(session);
  if (tier === "REFUSED" || tier === "NEEDS_REVERIFICATION") {
    return null;
  }
  const verifiable = getVerifiableCitations(session);
  const primary = verifiable[0];
  if (!primary?.video_id) return null;

  const bySource = new Map<string, { title: string; refs: string[] }>();
  for (const c of verifiable) {
    const vid = c.video_id.trim();
    const label = `[${c.ref_label}]${c.timestamp_label ? ` ${c.timestamp_label}` : ""}`;
    const existing = bySource.get(vid);
    if (existing) {
      if (!existing.refs.includes(label)) existing.refs.push(label);
    } else {
      bySource.set(vid, {
        title: c.video_title || vid,
        refs: [label],
      });
    }
  }

  const sourceListText = Array.from(bySource.values())
    .map((src) => `《${src.title}》(${src.refs.join("、")})`)
    .join("；");
  const trustLine =
    tier === "PARTIAL_OR_HEURISTIC"
      ? zh
        ? `\n> 证据等级：${researchTrustLabel(tier, session, true)}`
        : `\n> Trust posture: ${researchTrustLabel(tier, session, false)}`
      : zh
        ? "\n> 证据等级：严格已核验"
        : "\n> Trust posture: Strictly verified";

  const quoteMarkdown = zh
    ? `> 【跨视频研究结论】${session.question.trim()}\n> ${session.answer_zh.trim()}${trustLine}\n— 综合 ${bySource.size} 篇来源：${sourceListText}`
    : `> [Cross-Source Conclusion] ${session.question.trim()}\n> ${session.answer_zh.trim()}${trustLine}\n— Synthesized across ${bySource.size} source(s): ${sourceListText}`;

  return {
    quoteMarkdown,
    primaryVideoId: primary.video_id,
    primaryVideoTitle: primary.video_title || primary.video_id,
    distinctSourceCount: bySource.size,
    tier,
  };
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
  fallbackQuestion: string,
  pinned: boolean,
  tier: ResearchTrustTier,
  zh: boolean,
): string {
  const { body } = stripLeadingFrontmatter(singleMarkdown);
  const lines = body.split("\n");
  const pinPrefix = pinned ? (zh ? "[置顶] " : "[Pinned] ") : "";
  const tierBadge =
    tier === "VERIFIED_EXACT"
      ? zh
        ? " [严格已核验]"
        : " [Verified]"
      : zh
        ? " [含启发式/部分裁剪]"
        : " [Heuristic/Partial]";
  const h1Index = lines.findIndex((line) => line.startsWith("# "));
  const out: string[] = [];

  if (h1Index >= 0) {
    const title = lines[h1Index].slice(2).trim() || fallbackQuestion.trim();
    for (let i = 0; i < lines.length; i += 1) {
      if (i === h1Index) {
        out.push(`## ${index + 1}. ${pinPrefix}${title}${tierBadge}`);
        continue;
      }
      const line = lines[i];
      if (/^#{1,5}\s+/.test(line)) {
        out.push(
          line.startsWith("# ")
            ? `### ${line.slice(2)}`
            : line.replace(/^(#{2,5})\s+/, (_, hashes: string) => `${hashes}# `),
        );
      } else {
        out.push(line);
      }
    }
  } else {
    out.push(`## ${index + 1}. ${pinPrefix}${fallbackQuestion.trim()}${tierBadge}`, "");
    for (const line of lines) {
      if (/^#{1,5}\s+/.test(line)) {
        out.push(
          line.startsWith("# ")
            ? `### ${line.slice(2)}`
            : line.replace(/^(#{2,5})\s+/, (_, hashes: string) => `${hashes}# `),
        );
      } else {
        out.push(line);
      }
    }
  }

  return out.join("\n").trimEnd();
}

export function buildResearchDossierMarkdown(
  sessions: AiResearchSession[],
  zh = true,
): {
  markdown: string;
  includedCount: number;
  verifiedCount: number;
  heuristicCount: number;
  skippedCount: number;
} {
  const exportable = sessions
    .map((session) => ({ session, tier: classifyResearchSessionTrust(session) }))
    .filter(
      ({ tier }) => tier === "VERIFIED_EXACT" || tier === "PARTIAL_OR_HEURISTIC",
    )
    .sort((a, b) => {
      const pinDiff = Number(Boolean(b.session.pinned)) - Number(Boolean(a.session.pinned));
      if (pinDiff !== 0) return pinDiff;
      return (Date.parse(b.session.created_at || "") || 0) - (Date.parse(a.session.created_at || "") || 0);
    });

  const verifiedCount = exportable.filter((x) => x.tier === "VERIFIED_EXACT").length;
  const heuristicCount = exportable.filter((x) => x.tier === "PARTIAL_OR_HEURISTIC").length;
  const skippedCount = sessions.length - exportable.length;
  const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");

  const header: string[] = [
    zh ? "# 跨来源研究汇编" : "# Cross-Source Research Dossier",
    "",
    zh
      ? [
          `- 导出时间：${stamp} UTC`,
          `- 严格已核验问答：${verifiedCount} 条`,
          heuristicCount > 0
            ? `- 含启发式/部分裁剪问答（已保留警示，请核对原文）：${heuristicCount} 条`
            : "",
          skippedCount > 0
            ? `- 已自动过滤拒答/待复核/无有效引用条目：${skippedCount} 条`
            : "",
        ]
          .filter(Boolean)
          .join("\n")
      : [
          `- Exported at: ${stamp} UTC`,
          `- Strictly verified sessions: ${verifiedCount}`,
          heuristicCount > 0
            ? `- Heuristic / partially pruned drafts (verify against sources): ${heuristicCount}`
            : "",
          skippedCount > 0
            ? `- Refused / unverified / uncited sessions excluded: ${skippedCount}`
            : "",
        ]
          .filter(Boolean)
          .join("\n"),
  ];

  if (exportable.length === 0) {
    header.push("");
    header.push(
      zh
        ? "_暂无可导出的带有效出处跨视频研究问答（无引用、待复核或拒答会话已按规则排除）。_"
        : "_No eligible Q&A sessions available to export (refused, unverified, or uncited outputs excluded)._",
    );
    return {
      markdown: `${header.join("\n")}\n`,
      includedCount: 0,
      verifiedCount: 0,
      heuristicCount: 0,
      skippedCount,
    };
  }

  header.push("", zh ? "## 目录" : "## Table of Contents", "");
  exportable.forEach(({ session, tier }, idx) => {
    const pinTag = session.pinned ? (zh ? " [置顶]" : " [Pinned]") : "";
    const tierTag =
      tier === "VERIFIED_EXACT"
        ? zh
          ? " [严格已核验]"
          : " [Verified]"
        : zh
          ? " [含启发式/部分裁剪]"
          : " [Heuristic/Partial]";
    header.push(`${idx + 1}. ${session.question.trim()}${pinTag}${tierTag}`);
  });

  const sections = exportable
    .map(({ session, tier }, idx) => {
      const single = buildResearchSynthesisMarkdown(session, zh);
      if (!single) return "";
      return normalizeSynthesisForDossier(
        single,
        idx,
        session.question,
        Boolean(session.pinned),
        tier,
        zh,
      );
    })
    .filter(Boolean);

  return {
    markdown: `${header.join("\n")}\n\n---\n\n${sections.join("\n\n---\n\n")}\n`,
    includedCount: exportable.length,
    verifiedCount,
    heuristicCount,
    skippedCount,
  };
}
