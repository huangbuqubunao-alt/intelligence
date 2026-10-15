# TASK-READINESS-SOURCE-INTEREST-CAS 交接报告

## 元数据

- Task: `TASK-READINESS-SOURCE-INTEREST-CAS`
- Role: Implementer `local_text_repair_resume`
- Base: `1aef3e0ec18568bb503a1b8663364cd05ca221d1`，开工时 clean。
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-source-interest-cas`
- Branch: `codex/task-readiness-source-interest-cas`
- Reviewer: `local_text_review_resume`，作者提交、clean STOP 后独立审查。
- 授权：原精确 CAS 提案、2026-10-15 并发补充与持续默认授权；不逐文件重复请求。

## 实现与合同

新增 `PUT /api/v1/sources/{source_id}/interests`，仅接受 command_id、明确存在且可为 NULL 的
expected_source_policy_revision_id、focus/ignore mode+rules、style mode+value。
数量/enabled/processing/schedule/未知字段拒绝。沿用有限枚举、20 条/160 字符规则等原领域限制。
既有 full `PUT .../policy` 保留领域字段，新增 expected 版本前置；已有 raw revision 的新无版本盲写
409，不猜当前版本。首次无 raw revision 可兼容 missing 初始化，但 missing 与 explicit NULL 的
命令身份不同；新完整编辑器始终发送捕获的明确版本或 NULL。

持久 ID 为 `source-policy:source-interest:v1:<operation/source/command canonical SHA256>:<complete typed request SHA256>`，
固定长度小于512。完整 request hash 包含 expected 是否明确提供及其 NULL/值，full 操作还包含
两个数量字段；客户端不能指定持久 revision ID。`BEGIN IMMEDIATE` 内以主键的 BINARY prefix
范围和 LIMIT2 查历史，先拒同 command 的不同请求；同请求历史重放返回 applied revision，绝不
更新 head。旧历史 full 命令可按相同字段、原无 expected 请求重放；不能借该旧身份新增 expected
或改字段另写。新版本才校验 expected/head，从同事务真实 raw row 原样复制 nullable 数量，追加
immutable revision 并以原指针条件更新 head。失败整个事务回滚，不新增表或迁移。

写响应除原 policy 外明确返回 applied_source_policy_revision_id、current_source_policy_revision_id、
historical_replay；historical replay 不假称当前已保存。新增 applied 元数据不参与有效 policy 的
领域语义相等性。GET 用一个 SQLite SELECT 同时读取 GLOBAL 与 raw SOURCE；由该同一 row 集
构造 effective/expected/modes，没有新增 raw 数量 DTO。

实际 tracked 详情 `CreatorFollowing.tsx` 添加独立兴趣 form，使用既有 modal/field/button 和
`frontend/src/workspace/DESIGN.md`。仅一个兴趣 PUT，真实 policy/mode/identity/version 未读或坏值
不可保存，有显式 GET 重读；冲突/历史重放保留草稿并禁止自动重放。重读只更新捕获版本，不覆盖
已编辑草稿；最初失败后开始输入的草稿也保留。关闭重开读取新版本，源 ID key/unmount/disposed
隔离晚响应，双击同步 guard；Escape 取消，中英文完整。未调用 Source PATCH、automation、模型
或 check。专用兴趣路径除 policy revision/pointer 外其他全部表不变。

旧完整表单改为 policy CAS 先于其原 Source PATCH/automation，保存 attempt 保留稳定 command/
完整请求和已完成步骤；未知响应重试同请求，后续步骤失败仅继续未完成部分，不重置 DAILY。
policy 409 与后续 Source PATCH 409 分开反馈已完成步骤。坏持久 enum/缺版本关闭保存，显式重读
且保留草稿，修复非法旧 enum 后再提交。历史 replay 阻止后续 Source/automation 写。

复用 DIRECT 现 SQLite/事务/immutable policy/source DTO、API client、React 和现有样式；无外部源码
复制或新依赖，未改许可/owner。graph-first 找到现方法，当前未提交实现以实际 source/diff 为准；
无 `.codegraph/`。Jev 路由 HTTP451 不可用，保持 strong/default 与独立 review，没有降级。

## 验收证据

| 检查 | 结果与证据 |
|---|---|
| 最终新 CAS + 原 policy | `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_source_interest_cas.py tests/integration/test_task021_source_policy_filtering.py`：**49 passed, 15.58s**，`/tmp/source-interest-last-backend.log`。两种提交顺序分别覆盖无 raw/已有 R0，另有真实双线程竞争；NULL/所有合法数量、继承/显式空 override/全部 style、完整 command 改 expected/fields、历史 replay、未知来源/字段、原子 rollback、同快照 GET。 |
| 最终 restart/restore 加强 | 同新模块 `-k 'complete_command_replay or interest_null_counts'`：**2 passed**，`/tmp/source-interest-restart-restore-final.log`。全新 repository 重放和真实 UTF-8 LOCAL 导入非空 DATA 全表/全部字节哈希 backup/stage/activation 相等，恢复后同命令仍幂等。该2项与49重叠，不相加为独立总数。 |
| 相关旧编排/上下文/reservation | `pytest -q tests/integration/test_task024_processing_orchestration.py tests/integration/test_distillation_source_context.py tests/integration/test_task023b_distillation_reservation.py tests/unit/test_orchestration_service.py`：**56 passed, 41.61s**，`/tmp/source-interest-related.log`。 |
| 完整 frontend | `cd frontend && npm test`：**30 files / 485 passed, 15.69s**，`/tmp/source-interest-last-front.log`。保留既有 React act 警告，不称零警告；新增完整请求、409 草稿/历史 replay、坏/失败/晚 ID 读、重试、键盘/中英文、双 submit、旧完整 form 两种 PATCH 失败重试。 |
| TS/build | `npm run typecheck` 与 `npm run build` PASS，`/tmp/source-interest-last-ts.log`、`/tmp/source-interest-last-build.log`，50 modules，564ms。 |
| 静态 | `ruff check src/youtube_intel tests scripts/prepare_readiness_local_text.py` PASS，`/tmp/source-interest-last-ruff.log`；`mypy --strict src scripts/prepare_readiness_local_text.py` **103 files PASS**，`/tmp/source-interest-final-types.log`；`python -m compileall -q src scripts/prepare_readiness_local_text.py tests/integration/test_source_interest_cas.py` PASS；`git diff --check` PASS。 |
| 隔离真实 Chrome UI | 已安装 Playwright/Chrome，实际 CreatorFollowing 组件/CSS，离线 HTTP API fixture。en 320/768/1024/1440 和 zh-CN 同四尺寸保存/重开/409/草稿/只1 GET/Escape/无横向 overflow PASS，JS runtime errors0。截图 `/tmp/source-interest-browser/{en,zh-CN}-{320,768,1024,1440}.png`；英文结果在 `/tmp/source-interest-browser-fixed.log`，中文完整结果 `/tmp/source-interest-browser-zh.log`。每矩阵1 accepted PUT+1故意409，非真实模型或真实 owner 数据。保留 Chrome 对 dev HMR WebSocket 的 LocalNetworkAccess 拒绝日志和故意409 console资源日志，不声称 console零警告。 |

## 失败证据与修正

- 新 tree 无 `.venv`、node_modules；首次 `.venv/bin/python/pytest` 不存在。随后仅创建 ignored symlink
  复用已安装 runtime/deps，未安装或改包/锁/配置。Agent-browser CLI `command not found`，未安装，
  用已有 Playwright/Chrome fallback。此阶段无模型、正式数据或对外服务访问。
- 首轮 TDD `/tmp/source-interest-red.log`：**15 failed**（兴趣路由未实现、旧 full PUT 无完整身份/
  CAS、GET mixed snapshot getter）。原代码已真实运行，失败未隐藏。
- 首轮 strict mypy **2 errors**：request dict inferred value union 未包含数量 int；显式
  `dict[str, object]` 后通过，再进行测试调试，`/tmp/source-interest-backend-types.log`。
- 首轮 backend **27 passed, 1 failed**，原偏好不改 policy 相等断言受新增 applied 元数据影响；
  将该传输元数据 `compare=False`，原断言保留，之后28/32/47/49队列相继通过；
  `/tmp/source-interest-backend-first.log`、`backend-green.log`、`backend-expanded.log` 等。
- UI RED **9 failed**（无 Edit interests 入口），`/tmp/source-interest-ui-red.log`；旧 form CAS先行
  RED **1 failed / 2 deselected**，`/tmp/source-interest-old-form-red.log`。后续 typed fixture 补齐
  capability.code；补译时撞既有 Edit interests 字典键产生 TS1117，移除本轮重复新增行，既有翻译保留。
- 首次完整 front **462 passed, 18 failed**，旧 SourcePolicyRead fixture 缺 source revision，旧正常
  full form write fixture 缺新 applied/current/history 返回值；仅补齐合法响应并等候异步完成，原
  数量/字段/写入口断言全部保留，`/tmp/source-interest-frontend-first.log`，随后完整483/484/485 PASS。
  一个新重试测试要求 role=alert 暴露原 form 错误可访问性不足，改局部明确 alert 与本地化失败反馈，
  `/tmp/source-interest-ui-green.log`。没有删除或弱化旧断言、skip 或更改测试脚本。
- 自查后追加 RED：后续 PATCH 409 被误当 policy CAS 409，`/tmp/source-interest-partial-conflict-red.log`
  **1 failed / 3 deselected**；已只在尚未完成 policy 时处理 CAS，后续步骤保留完成反馈。坏持久 style
  仍可保存，`/tmp/source-interest-old-bad-read-red.log` **1 failed / 4 deselected**；已加入初始 policy/
  mode/version 有效性门禁与显式有效重读，最终全485包含两反证。
- 浏览器 harness 首次 missing Edit interests timeout，诊断确认预构建 react-dom/client 只导出 default，
  不是产品组件错误；改 default.createRoot 后英文四尺寸通过。中文 locator 最初误用全局兴趣标签
  `我重点关注`，改该现有字段真实标签 `重点词` 后四尺寸通过。保留
  `/tmp/source-interest-browser.log`、`/tmp/source-interest-browser-diagnosis.log` 及上述fixed/zh日志。
  未修改产品路由/权限/浏览器配置来隐藏失败。

## Diff 复核、限制与交付

实际范围：source_policy.py/state.py/local_api.py；App.tsx/CreatorFollowing.tsx/uiLanguage.tsx；新
CAS integration 与两份 UI test，现两份 fixture 的兼容补齐；本 handoff。原任务/提案/公共 status
不改。原 migration SQL、Schema39、依赖/lock、credentials/config、provider/runtime/预算/资格/
Cloud、SourceRun/tracking/health/Source/enabled/processing 写合同均未扩张。

语义/安全/性能自查：未知字段严格拒绝；所有 SQL 参数化；raw 数量只在同事务复制；命令 prefix
是 SHA 命名且 BINARY 范围 LIMIT2，无扫描猜 hash；旧原始行/原 SQL 不改；React plain text；
所有 GET/晚响应有 identity/mount gate，冲突不重放。测试中的新建 SQLite/LOCAL bytes 均隔离。

本报告是作者证据，不是独立 APPROVE。root 仍负责独立真实完整 GUI（非 fixture API）、最终全
backend/Frontend gate 和正式采用；本次无 main/push/正式配置或任何模型调用。持续默认授权
不授模型资格；原资格失败仍保留。候选提交后 clean **STOP**，等待指定 Reviewer。

## 独立审查 — REJECT（2026-10-15）

- Reviewer：`local_text_review_resume`，独立会话；未修改业务代码或仓库测试。
- 固定范围：`1aef3e0ec18568bb503a1b8663364cd05ca221d1...b6d2133843cc69c751e38f325c35f65cddf425c6`。
  恢复审查时重新确认 HEAD、branch 与 clean worktree，保留中断前已经完成的独立检查，不重复跑同一大套件。
- 结论：**REJECT；P0=0，P1=0，P2=1**。以下 P2 必须由原作者修复，再提交独立复审；未授予 ACCEPTED。

### P2：仅修改风格会拆分并改写已保存的合法规则

文件：`frontend/src/workspace/CreatorFollowing.tsx:349`（读取时 `:339`，提交时 `:354–355`）。
`SourceInterestEditor` 把规则数组用 `join(", ")` 放进输入框，再按英文逗号、中文逗号和换行拆分。
领域合同允许单条规则包含这些字符；规则使用完整字符串匹配，因此拆成多条会改变过滤含义。
用户无需编辑这些规则：仅调整 Distillation style 并保存就会发生改写。

独立 Chrome 探针使用实际组件/CSS 和离线 HTTP fixture，原值为
`focus_rules=["robotics, autonomy","产品，案例"]`、`ignore_rules=["ads, promotions"]`。
只把风格改成 `TECHNICAL_DETAIL_FIRST` 后，唯一一个 PUT 实际发送
`focus_rules=["robotics","autonomy","产品","案例"]`、`ignore_rules=["ads","promotions"]`，并显示
`Interests saved.`。`RULES_PRESERVED false`，JS errors 为0。
证据：`/tmp/source-interest-review-rule-probe.mjs`、`/tmp/source-interest-review-rule-probe.log`、
`/tmp/source-interest-review-rule-loss.png`。

另外独立调用真实隔离 SQLite/API，确认原始带逗号数组合法且逐值持久化；重启后历史重放不移动 head，
missing/NULL 与不同 expected 也不能作为相同完整请求重放。
证据：`PYTHONPATH=src:. .venv/bin/python /tmp/source-interest-review-api-probe.py`，exit0，
`/tmp/source-interest-review-api-probe.log`。该探针无网络、模型或正式数据访问。

要求：使用能逐条保留合法字符串的编辑表示，不能依赖有损 join/split 或要求用户自行编码 CSV。
补充仅修改 style、未编辑 focus/ignore 的数组逐值相等回归，以及含中英文逗号、合法内部换行的往返。
不得通过收紧既有领域规则或弱化断言消除该反证。

### 五轴复核与独立证据

1. **正确性/规格**：逐项复核完整 typed command identity（含 expected supplied/null/value）、
   namespaced PK prefix 范围 LIMIT2、旧 identity 兼容、历史重放不更新 head；BEGIN IMMEDIATE 内校验
   expected 并复制真实 raw nullable 数量；新旧 PUT 两种次序及真实双线程只有一个 winner；GET 单 SELECT
   同快照。现有关键测试独立通过；上述 UI 规则改写仍违反输入保真。
2. **边界/安全/恢复**：新兴趣路由拒数量/未知字段、非法 mode/style/unknown source；专用路径只追加
   policy revision/pointer，无 Source/processing/automation/job/model 写。独立49项包含事务失败回滚、
   非空 UTF-8 DATA 的真实 backup/stage/activate 全表/文件哈希相等及恢复后幂等；未改 Schema39 或备份实现。
3. **回归/测试**：检查旧测试 diff，AdvancedSourceForm 只补有效新响应和异步等待，SourcePolicyRead
   只补明确 nullable revision；原断言保留，无 skip/删测试/阈值或脚本改动。旧全量表单 CAS 先行、
   部分成功后的未完成步骤重试、原 DAILY 时间、uncertain response 同 command、失败/晚读/坏 enum
   与历史 replay 的 UI 测试均独立通过。新测试遗漏了合法分隔字符的输入保真。
4. **性能/维护性**：command 查找有 BINARY PK 范围和 LIMIT2，无全表猜 hash；同快照 GET 为单语句，
   沿用现有限制，无新增后台任务或外部调用。新命令 identity 和原 legacy identity 分支均已审阅。
5. **范围/复用/来源**：完整12路径 diff 无 schema/SQL/dependency/lock/config/credential/provider/runtime/
   Cloud/模型资格修改；DIRECT 现 SQLite/API/React，无新增外部源码或许可。只在本 handoff 写审查结果。
   graph-first 的旧项目索引未覆盖新符号，实际固定 SHA source/diff 为依据；未把作者汇报当作独立 PASS。

独立运行结果（均为上述固定候选）：

| 命令/范围 | 结果 |
|---|---|
| `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_source_interest_cas.py tests/integration/test_task021_source_policy_filtering.py` | **49 passed, 18.80s**；`/tmp/source-interest-review-backend49.log` |
| `cd frontend && npm test` | **30 files / 485 passed, 14.17s**；`/tmp/source-interest-review-frontend485.log`，原 React 警告保留 |
| `npm run typecheck` / `npm run build` | PASS；`/tmp/source-interest-review-ts.log`、`/tmp/source-interest-review-build.log`（50 modules，535ms） |
| `PYTHONPATH=src:. .venv/bin/python -m compileall -q src scripts/prepare_readiness_local_text.py tests/integration/test_source_interest_cas.py` | exit0 |
| `.venv/bin/ruff check src/youtube_intel tests scripts/prepare_readiness_local_text.py` | PASS；`/tmp/source-interest-review-ruff.log` |
| `PYTHONPATH=src:. .venv/bin/mypy --strict src scripts/prepare_readiness_local_text.py` | **103 files PASS**；`/tmp/source-interest-review-mypy.log` |
| `git diff --check 1aef3e0ec18568bb503a1b8663364cd05ca221d1...HEAD` | PASS |
| 两个 `/tmp/source-interest-review-{api,rule}-probe.*` | 真实隔离 API 控制 PASS；实际 Chrome 产品组件的规则保真反证成立，不能称功能 PASS |

Agent-browser CLI 与 Python Playwright 均未安装；保留 Python `ModuleNotFoundError: No module named 'playwright'`
证据，未安装依赖，改用已有 Node Playwright/Chrome。独立 Vite 仅占用5193并在审查后停止；root 服务未触碰。
作者56项相关旧编排测试仅记录为作者证据，本轮未重复运行；root 的完整 backend、真实 API GUI 与最终采用仍是
后续独立门禁，不冒充本轮通过。所有原失败/原通过日志均保留。审查提交后 clean **STOP**。
