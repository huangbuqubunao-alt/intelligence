# Issues Found — Intelligence User Pilot

> 记录本次 User Pilot 中发现的所有问题、修复内容与验证证据。
> 测试环境：隔离实例（UI 5588 / API 5589），与正式环境完全隔离。
> 截图目录：`screenshots/`。验证级别：GUI = 真实界面，API = 后端接口，TEST = 自动化测试。

## 已修复问题

### Issue 1：浏览器前进/后退与地址栏 hash 修改不切换视图（严重，影响导航体验）

**发现方式**：接管 OpenCode 现场时发现截图 `23-topics-route.png` 实为设置页、`25-narrow-*.png` 四张全部相同且均为设置页。亲自复现：侧边栏点击正常，但直接访问 hash（整页导航后的 hash 变化、浏览器前进/后退）时视图不跟随 hash 变化。

**复现步骤**：
1. 打开应用，点击侧边栏"设置"（视图 = 设置）。
2. 浏览器地址栏把 `#` 后内容改为 `Topics`（或点击浏览器后退按钮）。
3. 视图仍停留在设置页（hash 已变化但视图未变）。

**根因分析**：`frontend/src/workspace/App.tsx` 的 `hashchange` 事件处理器只处理 `#Content/<videoId>` 深链接；普通视图 hash 变化被完全忽略。侧边栏点击正常是因为 `navigate()` 显式调用 `setPage`。整页刷新时 `initialPage()` 正常（因此刷新可恢复），但**页面内**的 hash 变化（前进/后退/地址栏编辑）全部失效。

**影响**：真实用户最常见的浏览器后退/前进操作完全失效；分享链接在页面内跳转无效（刷新才生效）。

**修复**：`App.tsx` 增加 `programmaticHash` ref + 扩展 `hashchange` 处理器：
- 程序导航（`navigate`/`openContent`/`openDelta`）记录预期 hash，事件到达时匹配后跳过；
- 用户导航（前进/后退/地址栏）解析 hash：深链接打开内容详情，普通 hash 切换到对应视图。

**验证**：
- 新增回归测试 2 个（`App.test.tsx`：用户 hash 导航切换视图、hashchange 深链接仍打开内容）。
- 前端全量测试：`npx vitest run src/workspace/App.test.tsx` → **110 passed**。
- GUI 验证（`p13_nav_verify.mjs` 修复后重跑）：直接 goto `#Topics`/`#Settings`/`#Intelligence` 均正确渲染；浏览器后退/前进正确切换。截图 `30-topics-real.png`。
- 截图：`30-topics-real.png`（修复后 Topics 真实渲染）。

### Issue 2：本地"提炼为洞察"永远卡在 WAITING_MODEL，无法产生洞察（严重，核心功能失效）

**发现方式**：接管现场时数据库 `intelligences=0`，OpenCode 的 p10 截图与内容页相同（提炼无结果）。实测：点击"提炼为洞察"后状态变为 WAITING_MODEL，ollama 无任何负载，任务永不执行。

**复现步骤**：
1. 打开任一已整理内容的详情页。
2. 点击"提炼为洞察"。
3. 返回状态：`WAITING_MODEL`，`invocation_count=0`，且不会恢复（ollama 正常可用）。

**根因分析**：提交 `bfda6c5`（M12 云生产门禁）把 `OllamaLocalDistillationTransport.is_authorized_for_normal_production` 从 `is_authorized_for(value)` 改为 `self._production_qualified and is_authorized_for(value)`，并在 `runtime_composition.py` 构建时硬编码 `production_qualified=False`。但：
- 资格确认（qualification）机制只面向云模型（文档确认），本地模型没有任何授予 `production_qualified=True` 的路径；
- 手动提炼（`continue_reserved_distillation`, qualification=False → normal_production=True）因此永远被拒 → WAITING_MODEL。

**影响**：用户手册第 10 章的核心功能（提炼 Intelligence）完全不可用；自动提炼同样被卡。

**修复**：`runtime_composition.py` 本地 transport `production_qualified=True`（digest 绑定仍每次校验，安全等级不降）。云模型门禁保持不变。

**验证**：
- 新增回归测试（`test_runtime_composition.py::test_local_distillation_transport_is_production_authorized`）：runtime composition 10 passed。
- GUI 验证（`p15_intelligence_fix.mjs`）：点击"提炼为洞察" → ollama 实际加载 qwen3:8b 并执行 → 返回 `SUCCEEDED_NO_NEW_INTELLIGENCE` → UI 显示"已完成，未产生新洞察"。截图 `33/34/35`。
- 截图：`34-intelligence-extracted.png`（提炼完成，未产生新洞察的如实反馈）。

### Issue 3：手动提炼一次后，备份被永久阻止（DISTILLATION_ACTIVE）（严重，备份功能失效）

**发现方式**：修复 Issue 2 后执行提炼，随后备份状态一直为 `ready: false, reasons: ["DISTILLATION_ACTIVE"]`，即使提炼早已完成。

**复现步骤**：
1. 手动提炼一次（无论结果）。
2. 打开设置 → 备份与恢复。
3. 备份永远提示"以下工作尚未结束，暂时无法备份"。

**根因分析**：
- `record_distillation_no_new_intelligence` 把结果写入 `distillation_no_new_intelligence_results`，但 checkpoint 保持 `PENDING`（schema CHECK 约束：`SUCCEEDED` 终态必须有 Intelligence 行，而"无新洞察"没有洞察 → 无法置 SUCCEEDED）。
- `backup_restore.py` readiness 检查把任何 `PENDING` checkpoint 视为活动任务 → 备份永久被阻止。
- 同样的死状态也存在于 `WAITING_MODEL + invocation_count=0`（模型不可用时保留的等待任务，无法自行推进，`continue` 入口只接受 PENDING）。

**修复**：`backup_restore.py` 备份检查增加两个豁免：
- `PENDING` + `distillation_no_new_intelligence_results` 已有结果 → 视为已完结（durably recorded, cannot advance）；
- `WAITING_MODEL` + `invocation_count=0` → 从未调度、无活动工作。
- `_is_settled_attention_source_run` 同步加入相同豁免。

**验证**：
- 新增回归测试 2 个（`test_backup_restore.py`）：备份不被已完结的 no-new 结果阻止、不被未调度的 WAITING_MODEL 阻止。备份测试套件 **28 passed**。
- 端到端验证：重启测试 API 后 `/api/v1/backup-restore/status` → `ready: true`；实际创建备份成功（372 KB，含 3 关注 / 5 内容 / 20 证据）。

## 产品正确行为记录（非缺陷，但值得在手册中说明）

### 转写模型未配置时音频/视频保持"待转写"
导入音频/视频返回 `TRANSCRIPTION_UNAVAILABLE`，详情页显示"正在检查本地转写能力"，能力 API 如实报告 `EXECUTOR_INCOMPATIBLE / model_present: false`。产品不编造字幕，反馈诚实。截图 `36-audio-detail.png`。这是环境限制（模型未安装），记录到 UNRESOLVED_ISSUES。

### Bilibili 字幕不可用
导入公开 Bilibili 视频成功（201），但返回 `CAPTION_UNAVAILABLE`（源站字幕限制）。产品如实反馈。API VERIFIED。

### 备份前检查
有提炼任务执行时备份被阻止（`DISTILLATION_ACTIVE`），修复后仅在**真实活动任务**时阻止。GUI 显示"以下工作尚未结束，暂时无法备份"。诚实反馈。

### 云端模型未配置提示
设置页显示"云端洞察需要配置凭据并授权。内容整理仍可使用。"——不自动调用付费云模型。GUI VERIFIED（截图 `42-settings-english.png`）。

## 问题统计

| 类别 | 数量 |
|------|------|
| 发现并确认的问题 | 3（全部为真实 Bug） |
| 已修复并验证 | 3 |
| 新增自动化测试 | 5（前端 2 + 后端 3） |
| 修改文件 | 6（前端 2、后端 2、测试 2） |
