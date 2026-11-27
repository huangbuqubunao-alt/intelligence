import type { SourceAiSignal } from "./WorkspaceAiWidgets";

export type FollowingAuditSourceLike = {
  source_id: string;
  display_name: string | null;
  friendly_name?: string | null;
  provider?: string;
  canonical_url: string;
  enabled: boolean;
  last_error?: { code: string } | null;
  tracking?: {
    health: string;
    unavailable_count?: number;
    pending_count?: number;
  } | null;
};

function resolveAuditSourceName(source: FollowingAuditSourceLike, zh: boolean): string {
  if (source.provider === "LOCAL") {
    return zh ? "本地资料库" : "Local library";
  }
  return (
    source.friendly_name?.trim() ||
    source.display_name?.trim() ||
    source.canonical_url ||
    source.source_id
  );
}

function sanitizeHeadingText(raw: string): string {
  return raw.replace(/[\r\n#[\]|]+/g, " ").replace(/\s+/g, " ").trim() || "Unknown";
}

export function buildFollowingAuditMarkdown(
  sources: readonly FollowingAuditSourceLike[],
  aiSignals: Readonly<Record<string, SourceAiSignal>>,
  zh = true,
): { markdown: string; filename: string; sourceCount: number } {
  const todayStamp = new Date().toISOString().slice(0, 10);
  const filename = `following-signal-audit-${todayStamp}.md`;
  if (!sources.length) {
    return {
      markdown: zh
        ? "# 关注信源信息食谱体检报告\n\n_当前尚无订阅信源。_\n"
        : "# Following Signal Audit\n\n_No sources followed yet._\n",
      filename,
      sourceCount: 0,
    };
  }

  let totalVideos = 0;
  let totalLong = 0;
  let totalShorts = 0;
  let totalMustWatch = 0;

  const ranked = sources
    .map((source) => {
      const sig = aiSignals[source.source_id] ?? null;
      if (sig) {
        totalVideos += sig.total_videos;
        totalLong += sig.long_form_count;
        totalShorts += sig.shorts_count;
        totalMustWatch += sig.must_watch_count;
      }
      return { source, sig, label: sanitizeHeadingText(resolveAuditSourceName(source, zh)) };
    })
    .sort((a, b) => {
      const avgDiff = (b.sig?.avg_long_score ?? -1) - (a.sig?.avg_long_score ?? -1);
      if (avgDiff !== 0) return avgDiff;
      return (b.sig?.must_watch_count ?? -1) - (a.sig?.must_watch_count ?? -1);
    });

  const overallSignalPct =
    totalVideos > 0 ? Math.round((totalLong / totalVideos) * 100) : null;

  const lines: string[] = [];
  lines.push(zh ? "# 关注信源信息食谱体检报告" : "# Following Signal-to-Noise Diet Audit");
  lines.push("");
  lines.push(
    zh
      ? `- 体检日期：${todayStamp}\n- 订阅信源数：${sources.length}\n- 累计长视频干货：${totalLong} 篇（必看 ${totalMustWatch} 篇）${totalShorts > 0 ? ` · 已自动折叠 Shorts：${totalShorts} 条` : ""}${overallSignalPct !== null ? `\n- 整体干货信噪比：${overallSignalPct}%` : ""}`
      : `- Audit Date: ${todayStamp}\n- Followed Sources: ${sources.length}\n- Long-form Distilled: ${totalLong} (${totalMustWatch} must-watch)${totalShorts > 0 ? ` · Shorts Folded: ${totalShorts}` : ""}${overallSignalPct !== null ? `\n- Overall Signal Rate: ${overallSignalPct}%` : ""}`,
  );

  lines.push("");
  lines.push(zh ? "## 信源干货排行榜" : "## Signal Quality Leaderboard");
  ranked.forEach(({ source, sig, label }, index) => {
    const providerLabel =
      source.provider === "LOCAL"
        ? zh
          ? "本地库"
          : "Local"
        : source.provider === "BILIBILI"
          ? zh
            ? "B站"
            : "Bilibili"
          : "YouTube";
    const scorePart =
      sig && sig.avg_long_score !== null
        ? zh
          ? `均分 ${sig.avg_long_score.toFixed(1)}/10 · 干货 ${sig.long_form_count}/${sig.total_videos}${sig.signal_rate_pct !== null ? ` (${sig.signal_rate_pct}%)` : ""} · 必看 ${sig.must_watch_count}`
          : `Avg ${sig.avg_long_score.toFixed(1)}/10 · Long ${sig.long_form_count}/${sig.total_videos}${sig.signal_rate_pct !== null ? ` (${sig.signal_rate_pct}%)` : ""} · Must-watch ${sig.must_watch_count}`
        : zh
          ? "暂未完成 AI 信噪比统计"
          : "Signal metrics pending";
    const statusNote = !source.enabled ? (zh ? " · [已暂停]" : " · [Paused]") : "";
    lines.push(`${index + 1}. **${label}** (${providerLabel})${statusNote} — ${scorePart}`);
  });

  const lowSignal = ranked.filter(
    ({ sig }) =>
      sig &&
      sig.total_videos >= 1 &&
      (sig.shorts_count > 0 || (sig.signal_rate_pct !== null && sig.signal_rate_pct < 60)),
  );
  if (lowSignal.length > 0) {
    lines.push("");
    lines.push(zh ? "## 低干货 / Shorts 噪音待评估清单" : "## Low-Signal / Shorts Review List");
    for (const { sig, label } of lowSignal) {
      lines.push(
        zh
          ? `- **${label}**：Shorts ${sig!.shorts_count} 条 · 信噪比 ${sig!.signal_rate_pct ?? "--"}%（建议考虑调整关注权重或暂停订阅）`
          : `- **${label}**: ${sig!.shorts_count} Shorts · Signal rate ${sig!.signal_rate_pct ?? "--"}% (candidate to pause or tighten policy)`,
      );
    }
  }

  const unhealthy = ranked.filter(({ source }) => {
    const health = source.tracking?.health;
    return Boolean(
      !source.enabled ||
        source.last_error ||
        (source.tracking?.unavailable_count ?? 0) > 0 ||
        (health && !["HEALTHY", "BASELINE_PENDING"].includes(health)),
    );
  });
  if (unhealthy.length > 0) {
    lines.push("");
    lines.push(zh ? "## 状态异常与待处理提醒" : "## Health & Attention Alerts");
    for (const { source, label } of unhealthy) {
      const reason = !source.enabled
        ? zh
          ? "已暂停追踪"
          : "Paused"
        : source.last_error?.code || source.tracking?.health || "NEEDS_ATTENTION";
      lines.push(`- **${label}**：${reason}`);
    }
  }

  lines.push("");
  lines.push(zh ? "## 下一步信息食谱调优动作" : "## Recommended Diet Adjustments");
  lines.push(
    zh
      ? "- [ ] 对「低干货 / Shorts」高发频道开启更严格的全局关注词过滤，或点击「暂停关注」。"
      : "- [ ] Tighten topic filters or pause low-signal / Shorts-heavy channels.",
  );
  lines.push(
    zh
      ? "- [ ] 对高均分榜首频道优先使用 `#Research`「问此频道」跨期综合深挖。"
      : "- [ ] Run cross-episode synthesis on top-ranked channels in `#Research`.",
  );

  return {
    markdown: `${lines.join("\n")}\n`,
    filename,
    sourceCount: sources.length,
  };
}
