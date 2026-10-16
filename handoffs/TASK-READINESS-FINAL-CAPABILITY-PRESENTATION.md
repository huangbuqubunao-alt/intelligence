# TASK-READINESS-FINAL-CAPABILITY-PRESENTATION 交接报告

## 元数据与边界

- Role: Implementer `local_text_repair_resume`; Reviewer 由 root 串行分配。
- Base: `6854ed3c3e0d90d7f4852faa8a7ccc6f6db07b42`，branch `codex/task-readiness-final-capability`。
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-final-capability`。
- 持续默认授权及 root `74dc50a` 允许 service 的极小公开只读 binding / 实际执行语言接口。
- 两个提交分别呈现精确能力和追加物理备份统计；不合并/发布，不改资格、模型资源、Schema、依赖、配置、CODE_FILES 或现有 execution admission。
- 复用 DIRECT 既有 reviewed qualification reader、服务语言 callback、React/TypeScript、validated backup manifest、标准库；无新依赖/许可证。
- graph-first 查询根图不可用/旧索引不足时精确读取当前源码，不重建图。

## 第一段合同与实现

| 消费者/状态 | 严格边界与呈现 |
|---|---|
| Settings `local_intelligence` | 唯一 model/profile、精确三 scope × 两输出语言；缺失、异常、部分、重复、错误类型一律 UNKNOWN。六个状态逐项显示，目标 9b 与旧 fast 8b 分开。 |
| Content scope | 使用当前 server provider + 完整 canonical coverage 的已验证 locator；YT timed、LOCAL timed、LOCAL TEXT 分别匹配。服务实际 language callback 决定输出语言，不用 UI/全局设置猜测。 |
| NOT_QUALIFIED | 明确未通过该 scope/language，允许既有安全 WAIT0 请求/取消；POST 仍只含 command_id。 |
| QUALIFIED route mismatch | 明确需重启重新初始化；呈现不会把 callback 资格授给当前另一个 model/profile。 |
| QUALIFIED resource false/unknown/true | 分别 WAIT、UNKNOWN closed、仍需原准入检查；不声明绕过预算/Cloud 授权。 |
| Unknown/malformed/foreign/late Content | 操作关闭，GET 重读；异步晚返回不把其它 Content 状态用于当前 Content。已有 WAIT 取消入口保留。 |
| Old Settings / fast 8b / Cloud | 既有 runtime_local_model/providers/Cloud 边界保留；新字段缺失按 unknown 显示。 |

`runtime_composition.py` 仅 LocalApiApplication 构造位置一行 callback 注入。`distillation.py` 两个方法只读当前值/复用实际语言 resolver，异常不泄露。无 client model/scope 赋权，无真实 load/tokenize/generation。

## 第一段检查与失败证据

- 初始 backend RED：`/tmp/final-capability-api-red.log`，14 failed，constructor 缺 callback；实现后 focused 14 PASS，再扩展实际语言/资源/wiring。
- UI 初始 RED：`/tmp/final-capability-ui-red.log`。夹具漏 `/videos`、late detail 漏 transcript/note，改为完整共享 DTO 夹具；未修改产品列表/Detail 容错。另一次 undefined 默认参数掩盖 malformed case，移除默认值。失败日志保留。
- `npm run typecheck` PASS（`/tmp/final-capability-ui-types9.log`）；新增 UI 26 PASS（`/tmp/final-capability-ui-expanded6.log`）。
- 完整 frontend 第一轮 921/921 PASS（`/tmp/final-capability-front-full.log`）；TS/Vite build PASS（`/tmp/final-capability-build1.log`）。其后仅新增 1 个 GET failure 测试，最终完整检查见第二段。
- Ruff PASS（`/tmp/final-capability-ruff1.log`），strict mypy 104 source files PASS（`/tmp/final-capability-mypy1.log`）。
- 真实 Chrome：`node /tmp/final-capability-chrome.mjs`，24 个 EN/ZH × 320/1440 Settings/三 scope/unknown GET 恢复/WAIT+cancel 场景 PASS（`/tmp/final-capability-chrome3.log`）；无 pageerror/横向溢出；请求只有显式 extract/cancel，extract body 仅 command_id；真实 model IO 0。截图 `/tmp/final-capability-{settings,content}-{en,zh-CN}-{320,1440}.png`，已检视中文窄窗。
- Chrome 第一版中文 locator 与实际翻译不一致，第二版过早检查 GET 恢复按钮；脚本改为真实可访问名称和等待更新，不改产品。原 `/tmp/final-capability-chrome{,2}.log` 保留。
- backend 相关大组发现旧 `test_intelligence_card_projects_readable_persisted_provenance` fixture 缺 locator_type；基线 local_api 已访问该字段（git show HEAD 第2499–2502行）。仅补 fixture `TIMED_MEDIA`，保留原断言。反证 `/tmp/final-capability-local-api-isolate.log`；重跑结果后补。

## 第二段物理备份统计

待独立小提交追加；保持 manifest format1/counts/验证/归档集合及34–39恢复语义不变。

## 尚待与状态

- 正在完成相关 backend 回归及第二段物理计数；最终 SHA/checks/clean STOP 后补。
- root 仍须实际普通 factory/零模型副作用和真实新 backup/restore 全表/物理文件统一验收；合成资格 fixture 不授生产资格。
- Reviewer/主控验收未执行。不得以本报告代替独立接受。

### 第一段补充证据

- 基线归因 `/tmp/final-capability-base-fixture-proof.log`：base6854ed3 与当前 locator_type consumer 的 IfExp AST 完全相同；旧 fixture 缺 discriminator，本次补值后所有原 assertion AST 完全相同。相关 unit API 34/34 PASS（`/tmp/final-capability-local-api-fixed.log`）。
- 相关 backend 首轮 208 PASS / 2 FAIL（`/tmp/final-capability-backend-related2.log`）：上述基线夹具 + `PYTHONPATH=src` 未含根目录导致 scripts import 失败；当前以 `PYTHONPATH=src:.` 完整重跑中，非改变测试/生产 import。
- Chrome 额外24边界场景 PASS（`/tmp/final-capability-chrome-boundaries2.log`）：四种 qualified route/resource 状态、真实 503 GET 失败/显式读取恢复、晚返回隔离；EN/ZH × 320/1440，无 mutation/pageerror/modelIO。此脚本第一版中文 reload 名称不符，精确对照字典修正，原失败日志保留。

## 最终作者交接（2026-10-16，覆盖前述进行中状态）

第一提交 `c990538` 为能力呈现。第二提交为物理统计及最终回归（SHA 由 git log 读取，报告不自引用）。

### 第二段合同与验证

- `_public_preview` 仅追加 `data_file_count`（validated manifest.data_files unique relative_path）与 `data_file_size_bytes`（相同 validated 物理集合 bytes）。旧 data_artifact_count/data_size_bytes/counts、format1、归档集合、校验和恢复路径全部不变。
- UI 仅在两项均为非负 safe integer 时称 DATA files / 数据文件；缺失或非法新值回退旧 data_artifact_count + data_size_bytes，并明确称 DATA entries / 数据条目。创建和恢复检查使用同一个预览投影。
- RED `/tmp/final-capability-backup-red.log`：2 artifact 同一物理 path 时缺 data_file_count；UI RED `/tmp/final-capability-backup-ui-red.log`：缺正确标签/仍显示2。实现后 focused backend 1 PASS、UI6 PASS。UI focused 首轮第一例在 readiness GET 之前点击，按实际按钮 enabled 状态等待后恢复，不改产品/断言。
- 新真实 SQLite/ZIP fixture：2 artifact → 1 physical path；旧 manifest counts 保持2/physical bytes，只归档一个文件；真实 create→stage→confirm→recover 全 iterdump 与 DATA bytes 完全相等。
- Chrome `node /tmp/final-capability-backup-chrome.mjs` 24/24 PASS（`/tmp/final-capability-backup-chrome.log`）：EN/ZH × 320/1440 × 新/旧/非法统计 × create/stage。每例只有显式 create 或 stage 一次，无 confirm、pageerror、横向溢出和模型调用。截图 `/tmp/final-capability-backup-{en,zh-CN}-{320,1440}-{create,stage}.png`；已检视中文窄窗 stage。

### 最终检查

| 命令 | 结果与日志 |
|---|---|
| `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_final_capability_presentation.py tests/integration/test_runtime_composition.py tests/unit/test_local_api.py tests/integration/test_dogfood_day1_intelligence.py tests/integration/test_local_intelligence_text.py tests/integration/test_local_intelligence_timed.py` | **210 PASS**，245.92s；`/tmp/final-capability-backend-related3.log`。含原 API 全部34断言、23新 capability 场景；基线夹具及 import path 问题均闭合。 |
| `PYTHONPATH=src:. .venv/bin/pytest -q tests/unit/test_backup_restore.py tests/integration/test_v1x_phase1b_backup_restore.py tests/integration/test_dogfood_day2_backup_limits.py tests/integration/test_research_backup_restore.py` | **88 PASS**，56.38s；`/tmp/final-capability-backup-related.log`。唯一 warning 为既有 malicious duplicate ZIP name 负控。 |
| `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_local_text_input_proof.py -k 'legacy_backup_restore or terminal_proof_backup_restore'` | **7 PASS**，12.03s；`/tmp/final-capability-legacy-restore.log`。真实34/35/36/37/38 archive→restore→正常启动39 domain rows/DATA 不变；39 cancelled/unknown 恢复不 redispatch。 |
| `npm run typecheck && npm test && npm run build` | **929/929 PASS**，33 files；`/tmp/final-capability-types-final2.log`、`/tmp/final-capability-front-final2.log`、`/tmp/final-capability-build-final2.log`。保留原896，新增27 capability +6 physical preview。含 capability未知时既有 WAIT 仍可取消，原 Summary 保留。 |
| Ruff scoped7files、`mypy src`、compileall scoped4source | **PASS**；`/tmp/final-capability-ruff-final.log`、`/tmp/final-capability-mypy-final.log`；本固定base strict104 source files（未整合root capacity106，不改base）。 |
| 真实 Chrome | **72 PASS**：能力基础24+边界24+备份24；上述3个成功日志。合成 API/假资格仅 UI 工程验证，真实 load/tokenize/generation/model/provider IO **0**。 |
| `git diff --check`、累计 diff 复核 | PASS；无依赖/锁/Schema/config/资格/CODE_FILES/生成文件变动；runtime 构造仅一行 callback。 |

### 范围、风险与 STOP

- 累计实际文件：App/uiLanguage、2新前端测试、local_api/distillation/runtime_composition/backup_restore、1新集成测试、unit local_api fixture、unit backup_restore 测试、本 handoff。无公共状态文档写入，无 main/integration/rebase/reset。
- 仅使用隔离测试数据库/DATA、合成 API 和本任务5195前端；root5908/6098/6099、正式 owner/Vault/真实模型均未触碰。
- 不运行完整仓库 backend 或真实模型，按任务执行305项相关后端；root 仍负责合并容量后的普通 factory、真实全表/物理文件 backup restore 和最终 GUI。资格全 false 保持不变；测试 qualified fixture 不构成任何真实可用/质量宣称。
- 当前作者建议 **IN_REVIEW / clean STOP**；无未解决失败，无 DECISION NEEDED。独立 Reviewer 应审查累计 `6854ed3..HEAD` 两提交，不能仅审第二段。
