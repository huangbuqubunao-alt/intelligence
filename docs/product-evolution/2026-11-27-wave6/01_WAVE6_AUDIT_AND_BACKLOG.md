# 01｜Wave 6 市场调研驱动产品审计与高价值迭代规划

- **分支**：`antigravity/autonomous-product-evolution-wave6-20261127`
- **堆叠基线（Wave 5 PR #56）**：`d34b4813c01c9f2b01f0e402ed9bfb3f453701ba` (`14/14` CI green, `CLEAN`)
- **规划时间**：2026-11-27 15:28 (Asia/Shanghai)

---

## 一、竞品盲区与目标用户真实痛点洞察

面向「重度长视频学习者 / 独立研究者 / 一人公司创始人 / Obsidian 重度用户」对比主流工具链（YouTube + Readwise Reader + NotebookLM + Obsidian）：

1. **高亮墓地效应（Highlight Graveyard & Forgetting Curve）**：Readwise 与视频摘要工具擅长“收集金句”，但几周后回看失去上下文；用户缺少**「主动回忆（Active Recall）→ 核对本人批注」**的低摩擦日常闭环。
2. **周度复盘缺失交付闭环（Obsidian Weekly Review Pain）**：用户在 `#Home` 能看到「最近 7 天发生了什么变化？」，却无法一键导出成包含上周批注、证据变动与下周待核查清单的标准 Obsidian 周报 `.md`。
3. **跨模块笔记割裂与批量带走需求**：
   - `#Intelligence` 已能展示「已批注 · #tag」，但研究者无法一键筛选「仅看已批注」洞察，也无法把高可信验证洞察直接导出为 Markdown 文档；
   - `#Topics` 专题详情已有 MOC 双链导出，却遗漏了用户在相关视频下亲自写下的个人批注，形成「AI 综合结论」与「本人思考」的两张皮；
   - 快速文本录入（`QuickPasteNoteForm`）与阅读器缺乏高频键盘流 ergonomics（一键模版、预计阅读耗时预览、单键聚焦批注框 `N` 与 `G + H/F/C/I/T/R/S` 极速跳转）。

---

## 二、Wave 6 迭代优先级与验收契约（`EVO-W6-01` ~ `EVO-W6-06`）

| 迭代 | 代号 | 核心产品目标 | 关键产物 |
| :--- | :--- | :--- | :--- |
| **Iter 30** | `EVO-W6-01` | `#Home` 7 日知识复盘周报一键导出 `.md`（含周期个人批注聚合与行动清单） | `weeklyReviewExport.ts`, `KnowledgeDelta.tsx` |
| **Iter 31** | `EVO-W6-02` | `#Intelligence`「仅看已批注 (N)」筛选与可信洞察 Markdown 汇编导出（严滤未验证条目） | `intelligenceExport.ts`, `App.tsx` |
| **Iter 32** | `EVO-W6-03` | `#Home`「温故知新 · 主动回忆」双面卡片（先默想再展开核对，含个人批注优先队列） | `activeRecall.ts`, `App.tsx` |
| **Iter 33** | `EVO-W6-04` | `#Topics` 专题详情内联展示个人批注 + 专题 MOC 导出附带个人批注开关 | `WorkspaceAiWidgets.tsx`, `App.tsx` |
| **Iter 34** | `EVO-W6-05` | 快速粘贴表单结构化模板与实时精读耗时预览 + 阅读器 `N` 键直达思考输入框 | `QuickPasteNoteForm.tsx`, `ReaderPersonalNoteCard.tsx`, `App.tsx` |
| **Iter 35** | `EVO-W6-06` | `G + H/F/C/I/T/R/S` 全局极速跳转和弦、快捷键弹窗同步、`⌘K` 有批注内容直达与 8 视图 QA | `App.tsx`, `KeyboardShortcutsModal.tsx` |
