# Intelligence · PR #59 独立终审整改交付报告（Round 2 Ready）

- **目标分支**：`antigravity/autonomous-product-evolution-wave8-20261127`（[PR #59](https://github.com/huangbuqubunao-alt/intelligence/pull/59)，保持 Draft）
- **仓库 `main` 基线**：`f7b97134a9fafd3e8e447851a4237bdc66f7e60e`（全程未修改）
- **第 44 项整提交回退锚点**：`f4da98e4`（干净 `git revert f3cd5563`，已验证阅读器回归简洁克制）
- **最新已验证代码基线（`VERIFIED_CODE_SHA_R2`）**：`81c16adb1be072cb3353d4b7194a4b6fae947e80`
- **日期**：2026-11-28（Asia/Shanghai）

---

## 一、全部 4 项 P1 阻断项闭环情况

| 阻断项 | 根因与用户影响 | 本轮真实修复方案 | 复验依据 |
| :--- | :--- | :--- | :--- |
| **P1-01** 跨标签页失焦覆写笔记 | 两个打开同一篇材料的标签页中，未修改页失焦会直接将旧草稿写回覆盖新内容 | 1. 仅真实输入/插入操作才标记本地脏状态，未编辑状态失焦 `0` 写入；<br>2. 监听真实 `storage` 与本地自定义变更事件实时同步；<br>3. 若存在并发本地草稿而远端先变更，暂停自动覆写并显示冲突条，提供「采用最新内容 / 合并并保留两边」。 | 真实 Chrome 双标签实测（Tab 1 改 `Updated Note B` → Tab 2 实时同步且焦点离开不覆写 → Tab 1 硬刷新保留 `Updated Note B`）；`CodexPR59Remediation.test.tsx` |
| **P1-02** 自建 501 条快照导入失败 | 导出不受限而导入硬拦 500 条及 2 MiB，导致产品自导出的 501 条备份恢复 0 条 | 导出与导入限额对称放开并统一至 **10 MiB / 10,000 条**；使用同一套共享校验与反序列化入口。 | `CodexPR59Remediation.test.tsx` 实测 501 条短笔记 + 视图导出清空后完整恢复 `501/501` |
| **P1-03** 缺时间戳旧记录静默覆写新笔记 | 导入缺失或畸形 `updatedAt` 的 v1 备份时被伪造为当前时间并清空现有标签 | 严格区分「缺时间 / 非法时间 / 等时间不同正文」与明确更新的时间戳：<br>- 未知/非法时间不伪造 `Date.now()`，遇到同 ID 已有笔记一律保守冲突保护、原封保留正文与标签；<br>- 统计并返回 `noteConflicts` / `skippedOlderNotes`。 | `CodexPR59Remediation.test.tsx` 覆盖无时间、坏时间、同时间不同内容 3 类冲突场景 |
| **P1-04** 研究结论丢失证据等级与多来源归属 | `PARTIAL_PRUNED_HEURISTIC` 演示会话被算进“已核验”汇编；多出处回答转存批注只署第一来源；`NEEDS_REVERIFICATION` 缺乏按钮阻断 | 1. 在前端解析保留引用 `verified` 布尔与会话验证字段；<br>2. 按 `VERIFIED_EXACT` / `PARTIAL_OR_HEURISTIC` / `NEEDS_REVERIFICATION` / `REFUSED` 严格分层；<br>3. `NEEDS_REVERIFICATION` 与无有效引用会话禁止入库或导出；启发式会话显式标注「含启发式提示」，汇编分列「严格已核验」与「启发式草稿」计数；<br>4. 来源批注列出**全部引用来源**及各自锚点与证据等级。 | 实机 `#Research` 点击触发反馈 `综合 2 篇出处 · 含启发式提示`；汇编反馈与下载文本核验；`CodexPR59Remediation.test.tsx` |

---

## 二、产品取舍落地与 P2 / P3 全数收口

1. **取舍 A（整提交回退第 44 项 `f3cd5563`）**：通过 `git revert --no-edit f3cd5563`（提交 `f4da98e4`）移除阅读器多余的复制笔记按钮、第二套复选框条与实时字数统计，保留第 42 项（首页跨笔记待办清单）与第 43 项（命令面板直达视图）。
2. **取舍 B + `P2-09`（首页日常优先层级）**：
   - `WeeklyAiBriefPanel` 默认以「核心趋势结论一言摘要 + 导出栏 + `展开完整周报详情`」紧凑呈现，仅在主动展开或点击重新生成/切换期次时展示完整分析栏与精选列表；
   - `390px` 移动端通过网格重排将「高优待读队列 / 最近阅读 / 知识沉淀进度与行动清单」置顶至首屏（`y=259px` 起），周报退居其后。
3. **其余 `P2` & `P3` 修复摘要**：
   - **P2-01 & P2-04**：前置 `File.size` 体积拦截（未读取先拒绝 >10 MiB 文件），单次 JSON 解析并拒绝未知 `version`，导入后真实复读落盘结果并显式提示存储配额不足导致的部分成功（如视图写入失败）。
   - **P2-02 & P2-10**：移除渲染期 `readPersonalNote` 同步解析改为惰性状态初始化；仅在真实落盘后提示「已保存在本机」，防抖期内显示「正在保存…」，组件卸载/切换条目前同步冲刷未冲突草稿。
   - **P2-05**：`parseSingleTagRename` 拒绝含空格/分隔符输入（如 `new tag`），禁止静默截断，并在主题页提供重命名/合并影响篇数即时预览。
   - **P2-06**：`KeyboardShortcutsModal` 实现完整 `Tab` / `Shift+Tab` 模态焦点循环陷阱（兼容无布局 DOM 环境并防焦点逃逸到背景页）。
   - **P2-07**：首页主动回忆卡补充 `visibilitychange`、`focus` 与跨本地自然日午夜定时器，长挂不刷新也能按日重置。
   - **P2-08**：`tests/integration/test_public_beta_demo_showcase.py` 将原空跑 `if` 分支改为绑定真实种子 B 站 `video_id` 的强制断言，验证 `source_display_name == "极客架构演示室（Demo）"`。
   - **P3-01**：研究汇编在重写标题层级前先剥离 YAML frontmatter，统一编号 `## N.` 标题与子级 `###` 层级，消除正文游离 `#` 标题。

---

## 三、复审全量验证证据（均运行于 `VERIFIED_CODE_SHA_R2 = 81c16adb`）

- **前端构建与静态检查**：`npx tsc --noEmit` 0 错误；`npm run build`（`vite v5.4.19`）`889ms` 构建成功。
- **前端自动化测试全集**：`npx vitest run --poolOptions.forks.minForks=1 --poolOptions.forks.maxForks=3` → **102/102 测试文件、1370/1370 用例全部通过（`52.15s`）**。
- **后端静态检查与全量回归**：
  - `uv lock --check`（107 packages）、`ruff check src tests scripts`（All checks passed）、`mypy src`（138 source files 0 error）、`scripts/ci_test_manifest.py verify`（`7401 collected / 7190 runnable`）；
  - 6 个核心单元/集成/E2E 套件（`test_contracts.py`、`test_public_beta_demo_showcase.py`、`test_workspace_intelligence_hub.py`、`test_fast_read_api.py`、`test_final_blocker_closure.py`、`test_po_demo.py`）：**131 passed in 230.50s**。
- **真实 Chrome 双标签页及多场景实机验收**（`http://127.0.0.1:8799/`）：
  - 完成双标签同步与不覆写、#Research 启发式与多出处批注、快捷键弹窗 `Tab` 循环锁定、以及 `1440px` / `390px` 首页紧凑布局与深浅色实机检验；`0` 控制台错误、`0` 页面异常、`0` 失败 HTTP 请求、`0` 静默生成 POST；8 张截图归档于 `docs/product-evolution/2026-11-28-pr59-remediation/screenshots/`。
