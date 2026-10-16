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
