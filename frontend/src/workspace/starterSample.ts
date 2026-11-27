import { uploadLocal } from "../api/client";

export const STARTER_SAMPLE_FILENAME = "intelligence-starter-local-first-rag.md";

export function buildStarterSampleNote(language: "zh-CN" | "en"): File {
  const content =
    language === "zh-CN"
      ? [
          "# 本地优先可审计研究工作台设计笔记（内置体验示例）",
          "",
          "> 说明：这是一份仅存于本机的内置入门示例笔记，用于零网络快速体验「本地导入 → 原文证据定位 → 提炼总结 → Obsidian 双链导出」完整工作流，不会访问任何外部网站或消耗云端费用。",
          "",
          "## 一、为什么研究工具需要可验证的原文锚点",
          "",
          "传统 AI 摘要插件最大的信任缺陷，是把原文压缩成一段看起来流畅却无法核对出处的结论。一旦进入深度技术架构调研或商业决策场景，研究者真正需要的是每一条核心判断都能回溯到具体段落或视频时间戳，并在缺乏证据时诚实拒绝编造。",
          "",
          "## 二、双轨推理与成本可控架构",
          "",
          "1. 确定性采集与本地落盘：无论是 YouTube/B站字幕，还是本地 Markdown 技术笔记，先完整持久化原文并锁定校验指纹，确保后续离线反复检索始终一致。",
          "2. 本机零边际成本初筛：默认优先使用本机 Ollama 模型（如 qwen3.5:9b）完成日常阅读分诊、主题聚类与中文摘要；仅在用户主动需要更强推理并明确确认时才按次触发自带密钥（BYOK）的云端接口。",
          "3. 长期知识复利接口：所有单篇摘要、专题演化脉络与跨视频对比问答都可以直接导出为标准 Markdown 与 Obsidian `[[wikilinks]]` 笔记包，数据 100% 留在本机不锁定。",
          "",
          "## 三、下一步可以尝试的操作",
          "",
          "- 点击上方「AI 提炼中文总结与洞察」，使用本机模型提炼关键结论与切入方向。",
          "- 点击「速跳 · 原始证据」或「速跳 · 原始全文」，体验逐段定位与原话复制。",
          "- 前往左下角「AI 跨视频问答」，围绕本篇笔记内容进行带引用的提问验证。",
          "",
        ].join("\n")
      : [
          "# Local-First Auditable Research Workbench Notes (Built-in Starter Sample)",
          "",
          "> Note: This is a built-in, offline starter Markdown note stored only on your device so you can experience the full local import -> verified evidence -> AI brief -> Obsidian export workflow in seconds without network access or cloud spend.",
          "",
          "## 1. Why Research Workbenches Need Auditable Anchors",
          "",
          "The biggest failure mode of generic AI summarizers is producing fluent prose with no way to verify where a claim came from. During architecture evaluations or product strategy work, researchers need every takeaway linked back to exact source timestamps or paragraphs, plus honest refusal when the library lacks evidence.",
          "",
          "## 2. Two-Track Inference with Zero Surprise Cost",
          "",
          "1. Deterministic local capture: Transcripts and local Markdown notes are saved locally in SQLite with content hashes so offline retrieval stays reproducible.",
          "2. Zero-marginal-cost local screening: Local Ollama models (such as qwen3.5:9b) handle daily triage, clustering, and synthesis by default. Bring-your-own cloud keys remain isolated behind explicit review and budget caps.",
          "3. Long-term knowledge compounding: Single briefs, topic timelines, and cross-source Q&A export cleanly to standard Markdown and Obsidian `[[wikilinks]]` bundles with zero vendor lock-in.",
          "",
          "## 3. Suggested Next Steps",
          "",
          "- Click Distill AI brief above to extract structured takeaways using your active engine.",
          "- Open Evidence or Source text to inspect paragraph-level provenance.",
          "- Open Cross-video AI Q&A to test citation-backed questions against this note.",
          "",
        ].join("\n");
  return new File([content], STARTER_SAMPLE_FILENAME, {
    type: "text/markdown;charset=utf-8",
  });
}

export async function importStarterSampleNote(language: "zh-CN" | "en"): Promise<string> {
  const file = buildStarterSampleNote(language);
  const controller = new AbortController();
  const response = await uploadLocal<{ import: { content_id: string } }>(
    `/local/imports?filename=${encodeURIComponent(file.name)}`,
    file,
    controller.signal,
    () => {},
    () => {},
  );
  const contentId = response?.import?.content_id;
  if (!contentId || typeof contentId !== "string") {
    throw new Error("INVALID_STARTER_IMPORT");
  }
  return contentId;
}
