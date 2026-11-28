# Intelligence · PR #59 独立终审整改交付报告（Round 4 Ready）

- **目标分支**：`antigravity/autonomous-product-evolution-wave8-20261127`（[PR #59](https://github.com/huangbuqubunao-alt/intelligence/pull/59)，保持 Draft）
- **仓库 `main` 基线**：`f7b97134a9fafd3e8e447851a4237bdc66f7e60e`（全程未修改）
- **第 44 项整提交回退锚点**：`f4da98e4`（干净 `git revert f3cd5563`，已验证阅读器回归简洁克制）
- **Round 2 基线**：代码 `81c16adb1be072cb3353d4b7194a4b6fae947e80` · 交付 `edf86fc6a2759a8c36ec0dd4dbfdc9593de9d7d8`
- **Round 3 基线**：代码 `2b0c4d6b40856a89fed7d4c21c2f1b837db1f574` · 交付 `8618ae53d6f46fdbbfc5bd69bd6683f346331c30`
- **最新已验证代码基线（`VERIFIED_CODE_SHA_R4`）**：`a31b0bdcbce9b8af52fe2f31ea0944b5520c2184`
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

## 三、第三轮定向收口（针对 Codex Round 2 `B / HOLD` 仅剩 3 项反例）

| 复审反例 | 触发根因 | 本轮精确收口方案 | Round 3 验证依据 |
| :--- | :--- | :--- | :--- |
| **P1-02** 10,001 条与大中文快照导出不可恢复 + 配额未覆盖分支 | 单份导出整库直出不检查累计 `>10,000` 条与 UTF-8 真实字节超 10 MiB；`notesPersisted=false` 且 `viewsPersisted=true` 时落入普通提示 | 1. 新增按真实 UTF-8 字节（10 MiB）与单卷条数（10,000 条）分卷导出并支持 `<input multiple>` 多卷联合恢复，绝不截断已有笔记；<br>2. 设置页同步提供「分卷单独下载」保底按钮，导入端明确处理 `(notesPersisted, viewsPersisted)` 全部 4 种结果组合；<br>3. `importPersonalNotesJson` / `importStudyWorkspaceSnapshotJson` 统一按 `utf8ByteLength` 校验。 | 真机 Chrome 实测：10,001 条分 2 卷（747,941 B / 226 B）清空后 10,001 完整恢复；两篇 180 万中文字符分 2 卷（各 5,400,221 B）清空后 2/2 无损恢复；真机填满 Chrome 5.2M UTF-16 配额后导入触发 `role="alert"` 明确报出「未能保存个人笔记」与仅合并 1 个视图；`CodexPR59Remediation.test.tsx` 覆盖全 4 种组合。 |
| **P1-03** 同正文推进修订时间倒退与 2 月 30 日非法历日 | 同正文同标签提前 `continue` 未同步更新较新有效 `updatedAt`；浏览器原生 `Date.parse` 把 `2030-02-30` 顺延解析为 3 月有效日期 | 1. 同正文同标签且流入日期有效且更晚时更新持久化 `updatedAt`（不增加正文变更计数），更早则计入 `skippedOlderNotes` 并在设置页显式提示；<br>2. 实现严格公历历法与闰年校验，拒绝 `2030-02-30`、`2026-02-29`、`2026-04-31` 等不存在日期并保留现有记录。 | 真机 Chrome 顺序上传 `1月A → 3月A → 2月B → 2030-02-30`，确认界面依次报出跳过 1 条旧修订与 1 条无效时间冲突，最终落盘 `A` @ `2026-03-01T00:00:00Z`；单元测试验证全部 6 种排列组合与闰年边界。 |
| **P1-04** `NEEDS_REVERIFICATION` 会话单篇出口仍可复制/下载且纯文本漏标等级 | 单篇「复制纯文本提纲」「复制双链问答」「下载 .md」按钮写在信任分级门禁之外，且纯文本直接拼接 `answer_zh` 英文写死 `Verified citations` | 1. 统一以 `classifyResearchSessionTrust` 控制全部 5 个单篇出口，对 `NEEDS_REVERIFICATION` 与无可核验引用会话隐藏全部复制/下载/沉淀/批注按钮并展示暂停说明（保留同范围继续追问）；<br>2. `formatPlainTextResearchBrief` 首部注入精确 `证据等级` 提示、仅输出有效引用并在非严格态不使用「已核验引用」标题。 | 真机 `#Research` 实测：Demo `PARTIAL_PRUNED_HEURISTIC` 复制纯文本含 `证据等级：部分未支持内容已裁剪 · 含启发式关联（请核对原话）`；模拟恢复 `NEEDS_REVERIFICATION` 会话后确认全部 5 个导出与入库按钮数为 `0`；`CodexPR59Remediation.test.tsx` 校验实际剪贴板与下载 Blob 文本。 |

---

## 四、第四轮定向收口（针对 Codex Round 3 仅剩 `P1-02` 两项边界 + 3 项非阻断 P2/P3）

| 复审发现 | 触发根因 | 本轮精确收口方案 | Round 4 验证依据 |
| :--- | :--- | :--- | :--- |
| **P1-02 边界 1** 精确 `10 MiB` v1 单条笔记导出超限 +38 字节导致空库拒绝恢复 | 导入规范化补齐 `tags`/`updatedAt` 后单条略微超过 10 MiB，导出时无法装入单卷 | 1. 新增代理对安全正文分段（`note_segments`）与导入重组逻辑，单条笔记本身超过 10 MiB 时自动无损切成 2+ 卷合规文件；<br>2. 导出端加入下载前不变量校验（单卷 ≤ 10 MiB、100% 笔记/视图覆盖）。 | 真机 Chrome 使用 Codex 复现包 `inputs/single-max-v1.json`（`10,485,760` B）导入→导出两卷（`10,485,712` B 与 `587` B）→空库全选复原，SHA-256 逐字节一致、`tags: []`；单元测试覆盖正/反序恢复。 |
| **P1-02 边界 2** 多条超限常用视图合计超 10 MiB 被装进空尾卷并丢失全部视图 | 导出器把全部视图当作整体塞进唯一尾卷并在超限时清空视图数组 | 1. 改为常用视图逐项独立装卷（单条超限则对 `searchQuery` 无损分段重组），绝不批量丢弃；<br>2. 导出前不变量校验每份视图均被完整覆盖。 | 真机 Chrome 使用 Codex `inputs/saved-view-a/b.json` 导入→导出两卷（`5,400,403` B 含 1 笔记 1 视图、`5,400,331` B 含 0 笔记 1 视图）→空库全选恢复 `1/1` 笔记及 `2/2` 视图，两段 `searchQuery` SHA-256 一致。 |
| **P2（设置）** 多卷导入缺卷未提示、半损坏批量导入无原子校验 | 仅选部分分卷无缺失卷提示；边读边写导致前卷成功而损坏后卷抛错 | 改为「全量解析与结构预检全部通过后再写入存储」的原子批量导入；识别 `part_index`/`total_parts` 缺失并明确列出缺卷与失败文件名。 | 真机验证仅传第 2/2 卷显式提示缺少第 1 卷；第 1 卷+损坏 `{` 文件一起上传整体中止并指明 `corrupt_p2.json`，`localStorage` 保持未写入。 |
| **P2（研究）** 剪贴板写入被权限拒绝仍误报成功 | 异步 `clipboard.writeText` 未捕获拒绝即置为「已复制」 | 改为 `await` 真实剪贴板写入结果：成功才提示已复制，拒绝或异常显式弹出 `role="alert"` 权限受限告警。 | 真机 Chrome 阻断剪贴板权限后点击「复制纯文本提纲」，无成功按钮切换并展示权限拒绝告警；单测验证双复制按钮。 |
| **P3（研究）** `HEURISTIC_ONLY` + `contains_heuristic_claims=true` 误报「已裁剪」 | `researchTrustLabel` 把 `contains_heuristic_claims` 直接映射到裁剪分支 | 仅 `PARTIAL_PRUNED` / `PARTIAL_PRUNED_HEURISTIC` 标示「已裁剪」；纯启发式会话保持「启发式相关 · 请核对原话」。 | `CodexPR59Remediation.test.tsx` 断言中英文输出严格区分纯启发式与部分裁剪状态。 |

---

## 五、最新全量验证证据（均运行于 `VERIFIED_CODE_SHA_R4 = a31b0bdc`）

- **前端构建与静态检查**：`npx tsc --noEmit` 0 错误；`vite v5.4.19` 生产构建 `965ms` 通过。
- **前端自动化测试全集**：`npx vitest run --poolOptions.forks.minForks=1 --poolOptions.forks.maxForks=3` → **102/102 测试文件、1376/1376 用例全部通过（`67.30s`）**。
- **后端静态检查与定向集成回归**：
  - `uv lock --check`（107 packages）、`ruff check src tests scripts`（All checks passed）、`mypy src`（138 source files 0 error）、`scripts/ci_test_manifest.py verify`（`7401 collected / 7190 runnable`）；
  - 定向集成回归（`test_public_beta_demo_showcase.py` + `test_research_lite.py`）：**16 passed in 57.28s**（全量后端以本轮推送后的 GitHub Actions 14/14 远端流水线为准）。
- **真实 Chrome 实机验收**（`http://127.0.0.1:8799/` 独立 Showcase Demo）：
  - 基于 Codex Round 3 复现原件完成 `single-max-v1.json` 与 `saved-view-a/b.json` 导出/空库无损往返、缺卷提示与损坏文件原子回滚、`#Research` 剪贴板拒写诚实报错实测；`0` 控制台错误、`0` 页面异常、`0` HTTP ≥ 400 请求。
