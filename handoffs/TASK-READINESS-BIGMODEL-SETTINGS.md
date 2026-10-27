# TASK-READINESS-BIGMODEL-SETTINGS 交接报告

## 元数据

- Task: TASK-READINESS-BIGMODEL-SETTINGS
- Role: Implementer, sole writer `/root/bigmodel_audit_writer`; no subagents
- Base: `2065e49777ffd83ef1c36f0085c0b936cc4d7f6e`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-settings`
- Branch: `codex/task-readiness-bigmodel-settings`
- Head: this scoped commit; exact SHA reported to Root after commit (no self-referential hash).
- Date: 2026-10-27 Asia/Shanghai
- Suggested state: IN_REVIEW. Root alone accepts/integrates. No main/push/release.

## 目标与实际范围

普通用户可从引导或受阻云预览直达独立的 BigModel GLM-4.7-Flash 候选设置；跳过、保存、删除、返回原 Content/Evidence 和浏览器后退均可操作。保存只配置密钥，不推理、上传、连接测试、启动 worker、选择生产 provider、授予资格或费用授权。

实际修改 3 个后端产品文件（model_settings/local_api/runtime_composition），新增 BigModelSettings 及最小 ModelSettings/App/Onboarding/i18n 接线，相关测试与本报告。无需 orchestration 改动、CSS/新框架或通用 provider 注册机制。

DIRECT: 既有 React18.3.1、标准库 ctypes/Security.framework/HTTP/SQLite、受保护 loopback API、既有按钮/field/details/路由。
ADAPT: base 的原生 Keychain adapter（同一继承实现，仅固定服务名）、设置表单/引导/云预览入口。
REFERENCE: DESIGN.md、既有官方 preflight 快照（FREE_CLOUD_PREFLIGHT_2026_10_26.md）和模型路径补充。
无外部代码移植；既有 NOTICE/依赖许可证继续适用，无新增 SDK、依赖、lockfile 或工具链变更。agent-browser skill 已读；Root 已有两次 CLI about:blank 工具故障，本轮不重复盲试。改用仓库已有 Playwright-core1.62.1 + 已安装 Chrome 的隔离 headful 进程完成实际 UI 测试。

## 有限凭据边界

| 用途 | 固定 service | account |
|---|---|---|
| 历史 Moonshot，保持原样 | `com.huangbuqubunao.intelligence.moonshot` | `api-key` |
| BigModel 候选 | `com.huangbuqubunao.intelligence.zhipu-bigmodel` | `api-key` |
| 仅可信代码注入的隔离 QA | `com.huangbuqubunao.intelligence.qa.zhipu-bigmodel` | `api-key` |

`MacOSBigModelCredentialStore` / `MacOSBigModelQACredentialStore` 均固定 namespace、惰性加载原生 framework。HTTP 不接受 service/account/provider/model，不能指定任意 Keychain namespace。新 `BigModelCredentialSettings` 无环境变量 fallback，不读取 Moonshot store/env。历史 `MacOSKeychainCredentialStore`、`ModelSettingsService` 两个 class AST 与 base 完全相等；历史 env/route/service/account/call signatures 不变。既有运行组合的 `cloud_service` 与 `ProductionDistillationBudget` AST 也完全相等。

### 路由与 DTO

- GET `/api/v1/settings/bigmodel-credential`，空 body、无 query。
- PUT 同一路径，仅 `{credential: <string>}`。
- POST `/api/v1/settings/bigmodel-credential/delete`，仅 `{confirm:"DELETE"}`；重复删除可操作。
- 未知方法/路径/body形状/额外字段/query在存储访问前拒绝；密钥长度1–2048，无空白/ASCII控制字符。新入口保留原始值校验，不静默 trim；旧入口行为不变。
- 新 route 位于原 protected surface；mutation 继续要求 `X-YIA-Request: local-ui` 和现有本地 Origin 规则，原 body 大小限制/脱敏 error/no-store/log silence 不变。

成功 GET/save/delete 均只返回：

```json
{"provider":"zhipu_bigmodel","model":"glm-4.7-flash","configured":false,"source":"NONE","qualification":"NOT_VERIFIED","budget":"CLOSED"}
```

source 有限为 NONE/KEYCHAIN/UNAVAILABLE；configured 仅表示选定 store 内存在值。没有 secret、endpoint自由输入、连接成功、质量通过或付费权限。save/delete 完成后只读同一选定 store，不调用旧 getter/factory、模型或预算。原生写失败转为既有脱敏 CREDENTIAL_STORE_UNAVAILABLE。

## UI 与持久性

- `#Settings/models/bigmodel` 直接识别为 Settings，自动展开外层 Cloud details 和候选 details、滚动并聚焦。
- `?return=<encoded #Content/id[/Evidence/id]>` 仅接受内部 Content/Evidence 形状；返回链接保留精确阅读位置；未知外部 return 忽略。
- 云预览设置链接保留当前 Content/Evidence URL；引导第二步新增可选候选设置入口，原跳过与本地转写入口保留。
- 候选初始关闭时零 status 请求；显式展开或直达才读状态，避免隐藏配置问题污染无关页面。单次并行读/写 ref guard 防重复点击；保存无隐式 retry。
- password draft 仅组件内存；成功保存清空，选择/折叠/导航/卸载清空；失败保留供明确操作。未确认返回的保存状态不宣称已保存。删除需明确勾选，且只动 BigModel namespace。
- 双语文案区分当前官方精确型号免费标价与未验证的实际账号权益/额度/网络/质量/账单；可能调价，不回退 FlashX 等付费型号。准确说明所选文字外发、隐私必要保留与匿名改进，不作零留存或永久免费承诺。
- 仅官方 BigModel 账号和隐私链接，无注册、充值或条款代操作。无“测试”生成按钮。
- 新凭据无 SQLite/DATA 持久化，沿用 Keychain 原子存储；credentials 不入 backup。配置不改变转写、Summary 或 Intelligence 资格。

## QA 可信注入方法（仅 Root 后续真实隔离录入使用）

所有本轮检查使用 fake keys/in-memory store/fake native framework；从未调用以下真实 Keychain class 的原生方法。

直接 API 组合可在可信启动代码构造：

```python
candidate = BigModelCredentialSettings(MacOSBigModelQACredentialStore())
app = LocalApiApplication(repo, product, bigmodel_settings=candidate, ...)
```

保留既有隔离其余 services；旧 model_settings 可为 None 或现有离线 fake。不要为 QA 使用默认正式 runtime。若确需 runtime composition，新增仅 keyword `bigmodel_credential_store=` 支持注入上述固定 QA store；**既有生产 builder 启动时仍保留旧 Moonshot/env 读取行为**，本任务没有改动它，隔离启动应继续显式使用 Root 的无旧凭据组合。新候选 API 自身保证不访问旧 store/factory，这有 fail-on-access 测试。

仅独审接受后，Root 提供隔离页，用户本人填写；不要在聊天、argv、日志或此报告传递真实密钥。本任务无 transport resolver 或生产绑定，不能由“已保存”推定可执行。

## 验收证据

所有本地证据位于本 WT `.var/bigmodel-settings/`。最终 manifest `final-manifest.json` SHA256 **70dc6f0afc901369dbc83cc450351557c5064e299b55a0635fcf2833cbb2edfe**，记录14个产品/测试文件源码 SHA、45个 protected 文件相等证明、26份日志/图/脚本 SHA。最终检查期间源码 SHA 未变化。

| 检查 | 结果/证据 |
|---|---|
| 后端4完整文件 | **103 PASS /61.76s**, `backend-fixed.log` |
| 完整前端41文件 | **1066 PASS /22.52s**, `frontend-full-final.log` |
| TypeScript | PASS（`npm run build` 包含 tsc -b；另有多次 typecheck 日志） |
| Production build | PASS /570ms Vite，`build-final.log` |
| Strict mypy | **122 source files PASS**, `mypy-final2.log` |
| Ruff | src + 两个改变的后端测试文件 PASS，`ruff-final.log` |
| 语法 | 改变的5个 Python 文件 AST parse PASS；先前3个产品文件 compile PASS |
| Diff | `git diff --check` PASS；无SQL/distillation/state/依赖变化 |
| 旧兼容 | 两历史classes/旧factory/预算AST全等；原Moonshot测试保留完整通过 |
| 假 native | 两新 namespace 精确 service/account/add/delete，构造惰性；无系统凭据访问 |
| API隔离/失败 | 旧store/factory fail-on-access、无DB写入、坏shape/query/model/provider/缺确认、状态失败脱敏、HTTP正反Origin/header均覆盖 |
| UI正反 | 双语保存、错误不泄露、status failclosed、双点仅一写、明确删除、折叠/导航清draft、引导skip、精确Evidence route均覆盖 |

精确后端命令（当前 WT 为 cwd）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python -m pytest tests/unit/test_bigmodel_settings.py tests/unit/test_closure_model_settings.py tests/unit/test_local_api.py tests/integration/test_runtime_composition.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python -m mypy --strict src
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python -m ruff check src tests/unit/test_bigmodel_settings.py tests/integration/test_runtime_composition.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --check
```

## 真实 macOS headful（假密钥、真实本机 API）

最终源码 `gui-fixed/gui_server.py` 使用新独立 SQLite、MemoryStore，socket outbound connect 全拒、无runtime/worker/native storage；临时 API53808/Vite6194，仅本任务进程。`gui-fixed/gui.mjs` 用已安装 Chrome headful + Playwright-core，页面 external request 全拒。真实操作9项 PASS：引导模型入口/跳过、候选自动展开聚焦、保存并清空、未资格/关闭、精确Evidence返回链接、320px无横溢出、勾选独立删除、回原ContentURL、浏览器后退draft为空。

- `gui-fixed/gui-result.json` / `gui-fixed/gui.log` 均真实 PASS；页面仅两次mutation：新route PUT和新route/delete POST；observed external=[]，模型0次。
- 实际截图 `gui-fixed/settings-desktop.png`、`gui-fixed/settings-320.png`（已视检窄屏图，使用既有样式）。不是mock截图。
- 前后所有 **81张表每行**的完整 SQL dump 字节一致：`gui-fixed/gui-sql-before.sql` / `gui-fixed/gui-sql-after.sql`；SHA256 **052112b1970b0bf20d697935a98595481707ba27953e81ed3b7871e86a5a35ee**。integrity=ok、FK空。此fixture无Content DATA，不能冒称真实内容恢复验收。
- 所有本任务浏览器、两轮API/Vite进程已正常停止；Ctrl-C的退出130/KeyboardInterrupt仅正常停服务，finally已输出after SQL。Root其他服务未动。
- 重现：运行gui-fixed/gui_server.py（显式本WT PYTHONPATH），读其随机port，以 `YIA_API_BASE=http://127.0.0.1:<port> npm --prefix frontend run dev -- --host 127.0.0.1 --port 6194 --strictPort` 启动本任务Vite，再 `node .var/bigmodel-settings/gui-fixed/gui.mjs`。该脚本仅synthetic fake key；真实key不得进入脚本。结束仅停止自有session。
- 此fixture没有目标 video-1 的真实内容记录；返回验收证明精确URL/浏览器返回，**不宣称目标文字可读**。已有真实Content在Root集成QA继续检查。本任务 App 测试保留已有真实DTO Content/Evidence回归。未重跑全Goal BackupRestore；Root既有42全数据GUI恢复证据保留，未改相应实现。

## 失败历史（不掩盖）

1. 后端 RED：`backend-red.log` ImportError: BigModelCredentialSettings 不存在；前端 RED：`frontend-red.log` BigModelSettings 模块不存在；均在实现前留存。
2. 首次4文件前端 `frontend-affected-first.log` **162PASS/3FAIL**：新候选未展开就读取状态，旧fake不含新DTO使隐藏候选额外alert污染无关兴趣/Backup断言。修产品lazy-open读取，原断言不弱化；完整同4文件165PASS，扩测试后170PASS。
3. 完整前端首次 `frontend-full.log` **1064PASS/2FAIL**：原中英云预览精确期待`#Settings`，实际新正确深链含原Content返回。仅将该一个双语断言更新为更精确的新URL；原confirm禁用、零credential请求、零confirm断言完整保留，最终1066PASS。
4. GUI首次已真正打开浏览器并通过引导，测试locator写了“尚未配置”而既有翻译是“未配置”，超时；`gui-first-failure.json/log`保留。只修测试selector，未改产品文案；后续和最终源码headful均PASS。
5. 原始secret严格校验补充后，`mypy-final.log` 一处object→str静态类型错误（local_api.py save参数）。用raw_secret窄化后赋str局部修复；`mypy-final2.log`122PASS，后端同4文件最终103PASS。没有以中间通过冒充最终。

## 保护/剩余边界

所有001–042 SQL、state.py、distillation.py、pyproject.toml和frontend lockfile共45文件与base逐字节相同；原审计/claim失败历史不改写，未重签旧实验库。无正式数据、配置、凭据、Vault、paid provider、真实模型调用、下载或依赖变更。源码/测试最终14文件SHA均已固定；`.var`是离线证据，不是产品持久化。

账号已注册未充值只是Root记录的用户事实。本次不验证本人key/账号精确免费权益/额度/网络/实际usage费用/模型语义。BigModel资格保持NOT_VERIFIED、预算CLOSED，旧本地门禁不变。独审后Root才进行真实隔离输入/精确免费政策核实/冻结公开样例资格/费用和全链验收；没有可用模型/全Goal完成/main采用声明。DECISION NEEDED: None for this implementation; next step independent review.

## Reviewer / Root

待独立fixed-commit review；本实现者不填写APPROVE/ACCEPT或公共任务状态。
