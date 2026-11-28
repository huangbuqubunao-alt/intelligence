# 01｜Wave 7 市场调研驱动产品审计与高价值迭代规划

- **分支**：`antigravity/autonomous-product-evolution-wave7-20261127`
- **堆叠基线（Wave 6 PR #57）**：`06b75b9622fab6a33f069dc0084597a4d388f220` (`14/14` CI green, `CLEAN`)
- **规划时间**：2026-11-27 17:04 (Asia/Shanghai)

---

## 一、竞品盲区与目标用户真实痛点洞察

基于前六轮演进已建立的「AI 知识工作台 + 本机个人思考与 `#tag` + Obsidian 双链导出 + 全键盘导航」基础，面向重度个人研究者、Obsidian PKM 用户与独立创作者的高频工作流仍存在六个可即刻打通的「最后一公里」断点：

1. **多选精选后无法批量沉淀或打包带走（Readwise / Notion Web Clipper 级批量动作缺口）**：在 `#Content` 多选模式下已支持对比提问和复制摘要，但缺少**「批量追加个人 `#tag`」**以及**「将选中篇目连同核心结论、原话链接与个人批注一键导出为 Obsidian Reading Pack `.md`」**。
2. **个人 `#tag` 只增不改导致标签膨胀（Obsidian Tag Wrangler 刚需）**：用户在阅读器累计打入十余个 `#tag` 后，不可避免产生同义标签（如 `#Agent` 与 `#Agents`）或废弃临时标签；在 `#Topics` 的「我的自建标签」中缺少原地**重命名 / 安全合并**与**删除标签**（绝不误删正文思考）的治理入口。
3. **订阅源列表扩展后的检索与信息食谱审计盲区（YouTube / RSS 工具痛点）**：随着 `#Following` 订阅频道增多，缺少即时频道搜索栏；且虽有顶部信噪比简报，用户却无法一键导出一份可用于定期「断舍离低信噪比频道」的 **信息食谱体检报告 (`.md`)**。
4. **跨视频深度问答成果尚未反哺单篇个人笔记**：在 `#Research` 中已置顶与积累的多轮高质量问答缺乏**「仅看置顶」**筛选，且研究得出的有据结论难以直接反写摘录进对应被引用视频的个人批注中形成正反馈闭环。
5. **阅读器 AI 洞察条目缺乏一键「+ 摘录」到个人笔记**：阅读器内点击时间戳证据能一键摘录进笔记，但面对 `WorkspaceVideoAiBriefCard` 里的「AI 产品化启发」与「商业变现机会」列表时，仍需手动复制粘贴到个人思考框。
6. **轻量学习资产迁移碎片化**：常用筛选视图（`SavedContentView`）已在本地工作流扮演高频入口，却未被纳入本机个人笔记的 `.json` 便携快照导出与合并恢复。

---

## 二、Wave 7 迭代优先级与验收契约（`EVO-W7-01` ~ `EVO-W7-06`）

| 迭代 | 代号 | 核心产品目标 | 关键产物 |
| :--- | :--- | :--- | :--- |
| **Iter 36** | `EVO-W7-01` | `#Content` 多选模式新增「批量打标签」与「导出精选阅读包 (.md)」 | `personalNotes.ts`, `contentExport.ts`, `App.tsx` |
| **Iter 37** | `EVO-W7-02` | `#Topics`「我的自建标签」治理面板：安全重命名/跨标签合并与删除标签 | `personalNotes.ts`, `App.tsx`, `styles.css` |
| **Iter 38** | `EVO-W7-03` | `#Following` 即时搜索栏与「导出信源体检 (.md)」信息食谱审计报告 | `followingAuditExport.ts`, `App.tsx`, `styles.css` |
| **Iter 39** | `EVO-W7-04` | `#Research`「仅看置顶 (N)」历史筛选与有据结论「摘录进来源批注」闭环 | `WorkspaceAiWidgets.tsx`, `styles.css` |
| **Iter 40** | `EVO-W7-05` | 阅读器 AI 产品化/变现启发清单支持单条一键 `"+ 摘录"` 入本机个人批注 | `WorkspaceAiWidgets.tsx`, `App.tsx`, `styles.css` |
| **Iter 41** | `EVO-W7-06` | 统一便携学习快照 v2（笔记 + 标签 + 常用视图 JSON，兼容 v1）与 Wave 7 8 视图全界面验收 | `studyWorkspaceSnapshot.ts`, `savedViews.ts`, `WorkspaceAiWidgets.tsx` |
