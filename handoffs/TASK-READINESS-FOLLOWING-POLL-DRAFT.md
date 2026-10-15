# TASK-READINESS-FOLLOWING-POLL-DRAFT 交接报告

## 元数据与范围

- Role：Implementer；session `local_text_repair_resume`。
- Base：`aa18dea681c86645f7aa2efdea5b6c278dc96c89`，包含已独立审查整合的 SourceCAS。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-following-poll-draft`。
- Branch：`codex/task-readiness-following-poll-draft`；修复 HEAD 以本报告随附提交记录为准。
- 日期：2026-10-15。任务卡与 root 持续授权为依据；不改原 CAS 树/root，不自行整合或更新公共状态。
- 目标：实际 App → Sources → SourceDetail → CreatorFollowingDetail → SourceInterestEditor 组合，在
  tracking.checking/active run 轮询期间保持详情、逐条规则草稿、DOM 输入节点和焦点；读取错误可见、可重读，
  不假称旧数据已刷新；来源/路径/晚响应/CAS 隔离保留。

实际仅 App.tsx、CreatorFollowing.tsx、uiLanguage.tsx、新 FollowingPollDraft.test.tsx、本交接五个路径。
DIRECT 既有 React18.3.1 state/ref/effect/api/ErrorState 与前轮逐条词条控件；无新增外部源码或许可负担。
使用已批准的现 node_modules/venv symlink，不安装依赖；沿用现有设计样式，无重写 DESIGN 或新增 CSS。
图工具先定位 useRemote/Sources/CreatorFollowingDetail，索引签名/行号滞后，以固定 base 实际源码为准。

## 根因与最小修复

1. `Sources` 2s polling 的 useRemote 在每次读开始时清 data，早退 Loading 导致整棵打开的详情/兴趣表单卸载。
   `SourceDetail` 在 source_runs 活跃时自己还有1s polling，同样能卸载 Creator 子树；两点都需要修复。
2. useRemote 新增默认 false 的显式同路径保留选项，仅这两个位置 opt in；其它调用默认清数据/错误行为保持。
   新选项保留已加载同路径快照、reading 与错误分开；错误直到有效成功响应才清除，重试期间显示读取状态。
   路径切换在 effect 前一帧即屏蔽旧 data/error，随后清旧快照；alive cleanup 继续忽略晚响应。
3. Sources/SourceDetail 继续原2s/1s节拍，在当前读取完成后安排下一次，避免慢请求不断被新请求取代；失败后
   仍依据已知活跃状态继续读取。未停止/延长轮询，未靠抢先保存。
4. Sources list 校验基本来源读取形状；SourceDetail 校验匹配 id 与列表形状。已确认 tracking 的同源详情若
   刷新丢失 tracking，拒绝该读并保留原视图，避免错误切换成 legacy channel 又卸载草稿。新 id 独立绑定。
5. 保留原 ErrorState 的机器码文案和“Reload page data”GET入口，补充“显示上次加载数据”及读取中提示。
   当前 tracked modal 内同时展示父读取错误，避免提示被遮在详情之后；不将读取失败变为已刷新成功。
   非 tracked SourceDetail 原错误早退保持，不因保留选项而静默隐藏原错误。
6. Creator 的活动判断原只看 source_runs，只有 tracking.checking 时详情不会更新。反证后将 checking 纳入
   原2s轮询；reading 时不重叠，失败后可继续读，显示正在刷新。既有独立详情错误/手动GET恢复仍保留。
   草稿、expected revision、命令身份、409阻塞与显式重读均仍归 SourceInterestEditor 原逻辑所有；不改 CAS。

## 红绿与故障证据

- 先类型检查：`/tmp/following-poll-red-types.log` 发现新测试用了不支持的 ByRoleOptions.exact；移除该多余
  选项（字符串 name 本就精确），`/tmp/following-poll-red-types2.log` PASS 后才跑行为反证。
- 原真实 App 组合 checking=true，active run=false/true 两例：
  `npm --prefix frontend test -- src/workspace/FollowingPollDraft.test.tsx -t 'retains the actual'`，
  `/tmp/following-poll-red.log` **2 failed/3 deselected**，跨周期 `Unable to find a label ... Focus`。
- 非法 list/foreign source 读：`/tmp/following-poll-boundary-red.log` **1 failed/5 deselected**，原路径损坏读取
  会导致树崩溃；校验后保留已加载身份和草稿并报错。
- checking-only 详情状态不更新：`/tmp/following-poll-state-red.log` **1 failed/6 deselected**，等待2s后看不到
  新 OFFLINE 真实状态；补 checking 活动条件后绿。
- 已确认 tracking 的响应丢字段：`/tmp/following-poll-tracking-red.log` **1 failed/10 deselected**，原实现切
  legacy 视图丢 Focus；收紧同源已确认身份校验后11项全绿。
- 首轮相关5项时，导航测试的 Content fixture 缺 videos[]，导致 ContentPage.length 异常；只补新测试
  fixture，原 Content 产品代码不改，失败保留 `/tmp/following-poll-focused.log`。
- 首轮 full 前端 `/tmp/following-poll-full-frontend.log` **505 passed/1 failed**：原 App.test 的 open import
  draft recovery 期待原服务错误文案及 Reload page data。修复为保留原 ErrorState + 附加过期说明，原测试
  一字未改；`/tmp/following-poll-focused4.log` App147 + 新10 =157 passed，随后完整回归通过。
- Chrome 首轮 `/tmp/following-poll-browser.log` 在显式 GET 后的 verify(false) 报 focus 不同：探针未将
  requireFocus 参数传入 page callback，误读取 window.focus。修正探针参数后八矩阵通过，未更改产品焦点
  行为迎合探针；故意503/409控制台记录保留，不将其称作零控制台错误。

## 最终验证

| 检查 | 实际结果与证据 |
|---|---|
| 新真实 App 组合 | **11 passed,522ms**；`/tmp/following-poll-tracking-green.log`。覆盖双父轮询、跨3周期同DOM/焦点/草稿、慢list/detail、失败/手动恢复、坏形状/foreign/missing tracking、checking结束、CAS不自动rebase/重放、来源切换及导航卸载晚返回、初次失败closed |
| `cd frontend && npm test` | **31 files / 507 passed,13.16s**；`/tmp/following-poll-final-frontend2.log`。原 React act warnings 保留，无删改/skip原测试、断言或脚本 |
| `npm run typecheck` | PASS；`/tmp/following-poll-tracking-types.log` |
| `npm run build` | PASS，50 modules，531ms；`/tmp/following-poll-final-build2.log`（含 tsc -b） |
| `git diff --check aa18dea681c86645f7aa2efdea5b6c278dc96c89` | PASS |
| 后端 | 本任务 backend/schema/config/依赖0 diff，按任务继承 root36 backend 既有结果，未重复跑或冒称本作者新运行 |

真实 Chrome（现有 Node Playwright/Google Chrome，独立 Vite5194）加载实际 index/完整 App/CSS，HTTP API
为明确标注的离线控制 fixture，未调用真实 provider/API DB：

- `/tmp/following-poll-browser.mjs`、`/tmp/following-poll-browser2.log`：**8矩阵 PASS**，ZH/EN ×320/1440 ×
  checking-only/active SourceRun。每例真实等待至少两个2s列表周期，校验原 DOM handle、focus、selection
  [2,5]、多行/中文逗号草稿；保持慢列表请求2.5s期间无重叠新列表读；503在modal中明确显示上次数据，
  手动GET未完成前错误不消失，成功后清除；409期间跨周期草稿和旧expected不动、仅1命令；显式GET后
  新command成功且原词条逐值相等；checking结束后恢复Check Now；页面无横向溢出。每例2 interest PUT
  （故意409+显式GET后成功），JS errors0。现有启动check-stale POST仍只在fixture中记录，不冒充零所有请求。
- 最终 tracking 身份校验补充后，对最新代码再跑中文320/active=true同完整序列：
  `/tmp/following-poll-browser-final.mjs`、`/tmp/following-poll-browser-final.log` **PASS**。
- 图像 `/tmp/following-poll-browser/{en,zh-CN}-{320,1440}-{false,true}-{failure,saved}.png`；已实际查看
  en320失败截图：错误/重读入口位于当前modal内，原文本框保有选区与草稿，窄窗无横溢。

这些是工程运行证明，不代替 root 6098/6099 真 factory/API/真实 Google checking 场景复验；未读写 root
正式/验收 DB 或修改 root 原失败截图。原已审 CAS 树未动；root5908/6098/6099未操作。

## Diff 复核与交付状态

仅五个任务允许路径；无后端、Schema/SQL、模型/资格/ASR/Cloud、费用、配置/凭据、依赖/lock、正式数据、
公共 status 或 main/push 更改，模型调用0。无新缓存 authority、无跨路径共享旧数据、无自动重放兴趣命令。
不新增独立计时器队列或后台工作。读取轮询仍为原有节拍，慢读会等待该读完成再进入下一周期。

剩余门禁：同 Reviewer 独立 base...HEAD 审查，以及 root 原真实 Google/双页CAS/0副作用 GUI 复验；作者报告
不是 ACCEPTED。本任务不推进 tracked retry/model任务。提交后关闭自用5194、确认clean **STOP**。

## 独立审查 — REJECT（2026-10-16）

- Reviewer：`local_text_review_resume`；固定范围
  `aa18dea681c86645f7aa2efdea5b6c278dc96c89...81c17f9d5d4452a871c8613e45983bd89d2aaead`。
  作者clean STOP后独立读task/package、完整5路径diff和测试；额度中断恢复后再次核实同HEAD与clean树。
  不把额度中断当作测试完成，逐一读取真实完整结果；未重复已完成大套件。
- **REJECT；P0=0，P1=0，P2=1。** 普通轮询组合已改善，但下面坏响应仍会使整棵树崩溃、草稿丢失，
  不符合本任务“未知读取保留上次视图并明确失败”的边界。交回原作者，不直接修改业务/测试。

### P2：同源响应数组中的坏条目绕过校验，轮询使整个 App 空白

`frontend/src/workspace/App.tsx:3124` 只用 `Array.isArray` 校验 `source_runs/recent_videos`，接受
`source_runs: [null]`。随后 `:3149–3150` 的轮询 effect 直接读取 `run.state`，触发
`TypeError: Cannot read properties of null (reading 'state')`。React卸载整个App，已打开规则草稿DOM
disconnected、dialog=0、body为空，原来的错误说明与GET重试也不存在。该负控没有任何PUT/PATCH。

独立真实Chrome/完整App/CSS、离线HTTP fixture：先以真实同源合法tracking与active run打开兴趣草稿，
仅将后续详情响应的 `source_runs` 改成 `[null]`，其余id/source/list/policy都保持合法。约一个轮询周期
即崩溃。证据 `/tmp/following-poll-review-invalid-runs.mjs`、同名 `.log`、`.png`；日志记录
`draftConnected:false, dialogs:0, body:"", writes:[]` 及SourceDetail堆栈，实际查看截图亦为空白。

要求：在保存响应前校验实际消费的集合条目与字段形状，坏响应走原读取失败路径而保留原树/草稿/焦点。
`CreatorFollowing.tsx:189–191` 的独立详情读同样只验数组容器，应检查相同响应边界；不要用忽略异常、
ErrorBoundary替换草稿、停止轮询或缩减合法后端响应来掩盖。补完整App组合的坏成员负控，保留现有通过断言。

### 独立通过的检查与五轴复核

| 检查 | 真实结果/证据 |
|---|---|
| `cd frontend && npm test` | **31 files / 507 passed，14.88s**；`/tmp/following-poll-review-frontend507.log`。包含新11项及原496项，原React警告保留 |
| `npm run typecheck` | 恢复后显式复核exit0；`/tmp/following-poll-review-resumed-ts.log`，不从早先只有启动头的日志推断完成 |
| `npm run build` | PASS，50 modules，608ms；`/tmp/following-poll-review-build.log`，完整Vite完成记录 |
| `node /tmp/following-poll-browser.mjs` | **8矩阵完成**，ZH/EN×320/1440×checking-only/active run；`/tmp/following-poll-review-browser8.log`，每矩阵真实完整App跨2+周期，同DOM/focus/selection[2,5]/多行草稿、2.5s慢list无重叠、503/modal错误直到GET成功、409不自动rebase/重放、显式GET新command、checking结束、无横溢出，JSerrors0。故意503/409控制台记录保留 |
| 额外坏成员Chrome反证 | 上述P2成立；不能称invalid-response边界PASS |
| `git diff --check aa18dea...HEAD` / 范围 | PASS；仅原5路径，无后端/schema/config/依赖/锁/模型或资格变更 |

正确性/规格：useRemote的retain默认false、只有Sources/SourceDetail显式启用；同path保留快照、path变化
在effect前屏蔽旧值，late cleanup忽略旧响应，正常组合通过。安全/异常：错误在有效成功前不清，既有机器码/
GET文案保留，foreign/missing tracking测试通过，但坏成员未拒绝，形成本次P2。回归/测试：仅新增测试，
旧测试/断言/脚本无修改；默认其它useRemote行为未改成保留快照。性能/并发：原2s/1s节拍按读取完成后
再安排下一次，慢list/detail与两父轮询普通场景通过，未延长间隔或停止轮询。范围/复用：DIRECT现React/
API/CSS，无外部源码/依赖/许可改变；graph返回旧useRemote签名，使用实际固定diff作为新实现依据。

本轮没有调用真实provider/model或root6098/6099，没有正式数据写入；后端0diff，按任务继承root后端证据，
未声称本轮重跑backend。真实factory/API GUI仍由root复验。保留原作者全部RED及额度中断前日志，停止仅本轮
独立Vite5194；审查只提交本handoff，之后clean **STOP**。

## 原作者 P2 返修（2026-10-16）

从独立 REJECT clean HEAD `1ad96976b51d27e2725b0faa1f76d53317d3f309` 继续原任务，保留
`aa18dea...81c17f9...1ad9697` 全历史及上面失败证据；未动原已审 CAS 树、root 树或公共状态。
Graph 查到两个旧符号，但未包含当前轮询修复，以本树固定源码与消费者为准。

### 最小改动与复用

- DIRECT 既有 TypeScript/React/API 失败流程，无依赖、Schema 或 backend 变更。两个独立详情读取
  在 `setData` 前共用 `validFollowingDetailRead`，逐项验证 run/state/可选 run id，video/id/title/status
  及实际读取的 filter 字段；如成员附带 source_id，必须与请求来源一致。空数组仍合法；null、空对象、
  错类型、空必需 identity/state 和 foreign 成员拒绝整次读取，不过滤坏成员来冒充完整成功。
- 共用 source 校验验证渲染标签字段与 tracking 对象、health/coverage、非负整数数量、可选 boolean
  checking 和可选日期字段类型。Sources 列表已有身份校验也复用它；兼容原有可选字段和无 tracking 的
  合法 legacy 来源，不改变原 established-tracking guard、路径隔离、晚返回与其它 useRemote 默认行为。
- 坏响应沿用各自已有错误/GET 重试分支，保留已接受快照与原 editor DOM。没有 ErrorBoundary、停轮询、
  自动写入、隐式 policy rebase 或重放命令。兴趣编辑器及 CAS 合同未改。

### 红绿及检查证据

| 检查 | 结果 |
|---|---|
| `npm run typecheck`（新增测试后、实现前） | PASS；`/tmp/following-poll-repair-red-types.log` |
| `npm test -- src/workspace/FollowingPollDraft.test.tsx -t 'null run'`（实现前） | **2 failed**：完整 App `Cannot read properties of null (reading 'state')`，独立 Creator 未拒绝坏读、缺少错误说明；`/tmp/following-poll-repair-red.log`。此次聚焦执行的其余45项未选择，不是删/skip 测试 |
| 修复首次类型检查 | TS18048 `read.source is possibly undefined`，`/tmp/following-poll-repair-types.log`；将记录 tracking 身份的访问改为已校验后的可选访问，校验器保留 boolean 返回而不宣称所有 legacy 读都有 tracking。未改变测试断言 |
| `npm run typecheck`（最终） | PASS；`/tmp/following-poll-repair-types-green.log` |
| `npm test -- src/workspace/FollowingPollDraft.test.tsx` | **47 passed**；`/tmp/following-poll-repair-focused.log`。原11项保留，新增18种坏成员×App/独立Creator=36项；核对同 DOM/focus/selection[2,5]/原多行草稿、明确失败及显式 GET 恢复、PUT/PATCH0 |
| `npm test` | **31 files / 543 passed，13.79s**；`/tmp/following-poll-repair-full.log`；原507项全部保留，已有 React act 警告保留 |
| `npm run build` | PASS，50 modules，546ms；`/tmp/following-poll-repair-build.log` |
| Reviewer 原 Chrome 探针原样重跑 | `/tmp/following-poll-review-invalid-runs.mjs` 未修改；`/tmp/following-poll-repair-review-probe.log` 为 `draftConnected:true, dialogs:1, errors:[], writes:[]`。两个读取失败说明及各自 GET 重试可见。原失败 `.log` 不动；原空白 `.png` 在重跑前另存 `/tmp/following-poll-review-invalid-runs-before-repair.png`；已实际查看重跑截图，320窄窗原文本框与选区仍在 |
| Chrome 相关坏成员边界 | `/tmp/following-poll-repair-members-browser.mjs` 和 `.log`：EN/ZH×320×6种（null run/video、object count、空 tracking、foreign run/video）**12 PASS**。实际完整 App/CSS 跨轮询、原 DOM/focus/selection/草稿、两处错误、GET 恢复、pageerror0/PUT-PATCH0；未调用真实 provider |
| 原完整 Chrome 八矩阵原样重跑 | `/tmp/following-poll-browser.mjs`，`/tmp/following-poll-repair-browser8.log`：**8 PASS**，EN/ZH×320/1440×checking-only/active run；含多周期、慢读无重叠、503+显式GET恢复、409保留r0草稿无自动重放、显式兴趣GET后新命令、checking结束、无横溢出。每例故意409+成功为2 PUT，JSerrors0；预期503/409控制台记录保留 |
| `git diff --check` / `git diff --check aa18dea...` | PASS；累计仍仅原5个任务允许路径；返修仅 App/Creator/原测试/handoff |

后端0diff，本轮不重复后端/Ruff/mypy 或宣称重跑 backend；按原任务继承 root 已有后端证据。没有模型、
Cloud/ASR、资格、owner、正式数据、配置/凭据/lockfile 触碰。自用 Vite5194 及测试页在交付前停止。
这里的离线 HTTP fixture/真实 Chrome 只证明工程边界；root 的真实 factory/API Google checking GUI
和同 Reviewer 对 `aa18dea...新HEAD` 的累计复审仍为剩余门禁。作者提交后 clean **STOP**，不自行接受或整合。
