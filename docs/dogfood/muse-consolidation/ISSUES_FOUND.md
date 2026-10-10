# Muse 独立发现的问题（ISSUES_FOUND）

> 范围：muse-work 分支（`muse/user-pilot-consolidation` from main `fad25e6`）代码审查 + 后端回归测试实测。
> 方法边界：本环境无浏览器自动化能力，前端结论基于代码阅读与静态分析；后端结论基于代码阅读 + 独立重跑测试。未编造任何未执行的验证。
> 严重程度：高（功能失效/数据风险）/ 中（体验明显受损）/ 低（边缘不一致）/ 建议（代码整洁度）。

---

## M-1：豆包路由修复的 `#` 缺陷（中 → 已修复）

**现象**：豆包版 `App.tsx` 中，`programmaticHash.current` 存的是不带 `#` 的裸值（如 `"Settings"`、`"Content"`），而 `hashchange` 处理器比较的是 `location.hash`（浏览器恒返回带 `#` 的值，如 `"#Settings"`）。去重比较 `programmaticHash.current === location.hash` **永不为真**。

**后果**：每一次程序导航（如导入成功后 `navigate()`）触发的 hashchange 事件都被误判为"用户导航"，进入用户分支执行 `setImported(false)` —— **导入成功提示被立即清除**，de-dup 机制形同虚设。

**位置**：`frontend/src/workspace/App.tsx`（豆包版 `navigate`/`openContent`/`openDelta` 三处赋值；已用 `~/workspace/intelligence/pilot/` 快照中的豆包原始代码独立核验确认）。

**严重程度**：中（豆包修复引入的新回归：导航本身可用，但导入成功反馈被吞）。

**状态：已修复**（muse-work 分支）。修正为 `"#" + next` / `"#Content"` / `"#" + destinations[kind]`，三处赋值与各自对应的 `location.hash = …` 语句语义一致，并加注说明"必须带 `#`，否则永不命中"。回归测试：`App.test.tsx` 新增 2 个测试（用户 hash 导航切换 Settings/Topics/Content/Following/空 hash 回首页；hashchange 深链接仍打开内容详情）。前端测试待 npm 环境补执行；后端相关套件已实测通过（见 TEST_REPORT.md）。

---

## M-2：Research 详情页后退到 `#Research` 时视图不重置（低 → 未修复，待验证）

**现象**：用户在 `#Research/<64位id>` 查看详情，按浏览器后退回到裸 `#Research` 时，App 层 `onHashChange` 正确把页面定为 Research，但 `Research.tsx` 内 `followRoute` 的正则 `/^#Research\/([a-f0-9]{64})…/` 不匹配裸 `#Research` → `activeId` 不重置 → **URL 显示列表地址，视图仍停留在旧详情**（URL/视图不一致）。

**位置**：`frontend/src/workspace/Research.tsx`（`followRoute` hashchange 监听，约第 25 行）。

**严重程度**：低（用户可手动点回列表；非数据问题）。

**状态**：未修复。pre-existing（main 即如此；豆包与 Muse 的路由修复均未涉及 Research 内部状态机）。验证级别：代码审查，**待 GUI 验证**。

---

## M-3：`openDelta` 内容深链信息在 hash 中丢失（低 → 未修复，待验证）

**现象**：`openDelta({kind:"content", id})` 执行 `setContentTarget(target.id)`，但 `location.hash` 被设为 `"Content"` 而非 `"Content/<id>"`。用户在该状态复制 URL 或刷新页面，只能回到内容列表，无法回到当时那条内容详情。

**位置**：`frontend/src/workspace/App.tsx`（`openDelta`）。

**严重程度**：低（刷新/分享深链的边缘场景）。

**状态**：未修复。pre-existing（main 即如此，非本次改动引入）。验证级别：代码审查，**待 GUI 验证**。

---

## M-4：备份豁免两处条件表述不一致（建议级 → 未修复）

**现象**：`_is_completed_no_new_intelligence` 要求 `c.invocation_count = 1`，而 `_is_settled_attention_source_run` 的 SQL 豁免仅要求 `distillation_no_new_intelligence_results` 表中 `EXISTS` 对应行，未写 invocation_count 条件。

**核查结论**：无行为差异。`invocation_count` 取值域为 {0,1}（`begin_distillation_execution` 对非法值抛错；claim 成功后置 1）；有结果行即证明该执行已跑完，结果行存在 ⇒ invocation_count 必为 1。两处语义等价。

**位置**：`src/youtube_intel/backup_restore.py`（`_is_completed_no_new_intelligence` 与 `_is_settled_attention_source_run`）。

**严重程度**：建议级（代码表述统一性，不影响行为）。

**状态**：未修复（无需修复；如后续重构可统一为同一 helper）。

---

## 问题统计

| 类别 | 数量 |
|---|---|
| 独立发现的问题 | 4（M-1～M-4） |
| 已修复 | 1（M-1，含回归测试） |
| 未修复（低/建议级，pre-existing 或无行为影响） | 3（M-2、M-3、M-4；M-2/M-3 待 GUI 验证） |
