# TASK-014 Phase A — Codex Reviewer（发行资料与风险披露）

你是 TASK-014 Phase A 的独立 Codex Reviewer。本授权包只登记未来独立审查的边界；它本身不启动
Reviewer。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、
`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、
`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/ACCEPTANCE_REPORT.md`、
`agent-prompts/PREFLIGHT-TASK-014-RELEASE-READINESS-SCOUT.md`、Implementer 包与本包。如文件与本包冲突，停止并报告。

## 固定审查对象

```text
Task: TASK-014 Phase A — Release Readiness: 发行资料与风险披露
Role: Independent Reviewer
Agent: Codex Reviewer
Control-plane base: main@d0d136a4754a97954f64f1ca39b87837e639decc
Only source worktree: /Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-a
Source branch: codex/task-014-release-readiness-phase-a
Source HEAD: 8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59
Required sole parent: d0d136a4754a97954f64f1ca39b87837e639decc
Required change range: d0d136a4754a97954f64f1ca39b87837e639decc...8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59
Reuse decision: DIRECT — 审查已锁定的项目元数据、现有许可证/来源记录与 Git/文本证据；不新增或复制第三方代码
```

## 唯一写入权限

只能向 source worktree 的既有 `handoffs/TASK-014.md` **追加**审查结论和证据。不得修改、替换或格式化该
文件既有内容；不得修改 source 的任何其他路径，也不得修改 main 控制面。不得创建 worktree、分支、项目自身
`LICENSE` 或任何许可证文本。

审查开始时和追加 handoff 前后，都必须确认 source 指向固定 HEAD、唯一父提交正确、范围恰为以下七路径且
工作树没有无关变更：

1. `.gitignore`
2. `README.md`
3. `docs/RELEASE_CHECKLIST.md`
4. `docs/SBOM.md`
5. `docs/SMOKE_AUTHORIZATION_MATRIX.md`
6. `docs/THIRD_PARTY_NOTICES.md`
7. `handoffs/TASK-014.md`

只允许 Git 与文档核验，例如 `git rev-parse`、`git log -1`、`git diff --name-status`、`git diff --check`、
`git status --short` 与对所列 Markdown/锁定元数据的 `git diff`/`rg`/`sed` 阅读。不得运行测试、构建、安装、
`uv`、Python/import、产品 CLI 或任何 smoke。

## 独立核验要求

对 source 的 `.gitignore`、README、SBOM、第三方 NOTICE、发布检查表、smoke 授权矩阵和实施 handoff，独立对照
提交的 `pyproject.toml`、`uv.lock`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、已接受 ADR、
`docs/PROJECT_STATUS.md`、`docs/ACCEPTANCE_REPORT.md` 与任务卡。至少确认：

1. SBOM 和第三方 NOTICE 对锁文件、已批准依赖、直接/传递关系、版本和已知证据缺口如实表述；没有把锁定、离线
   包含性或开发测试误称为可分发/已签署，也没有作出法律结论。
2. README 与发布检查表面向用户明确当前仅有离线证据和 `No-Go`；不把真实 YouTube/字幕、媒体/ffmpeg/Whisper、
   Ollama/固定模型、OpenAI、launchd、真实 Vault 或恢复演练误称为已验证。
3. `mutagen` 的 GPL-2.0-or-later 分发门禁、`o200k_base.tiktoken` 的文件级来源/归属/NOTICE 未决、项目
   LICENSE 未选择，以及所有需要 PO/TL/QA 签署的事项都仍是未关闭的发布门禁。
4. at-most-once best-effort 的三类崩溃窗口（外部 Provider→SQLite、文件 replace→SQLite、音频 cleanup 最终 CAS）
   仍被清楚披露；不得夸大为 strict/exactly-once 或已接受的发布风险。
5. smoke 矩阵严格是未来四阶段授权设计：公开 YouTube/字幕、受控媒体+ffmpeg+Whisper、本机 Ollama+固定模型、
   OpenAI+临时 Vault；每阶段的授权、数据范围、证据与停止条件完整，全部真实 smoke 未执行，且真实 Vault 从未获
   本阶段授权。
6. `.gitignore` 对运行时目录的修改仅为根目录锚定 `/data/` 与 `/logs/`，不扩大或引入其他忽略语义。

发现风险被弱化、范围错误、证据不一致或将未决门禁标记关闭时，Verdict 必须为 `REJECT` 并给出 P 级、文件/行和
可执行的最小修复建议；不得自行修复 source。若全部满足，也只能给出资料审查 `APPROVE`，不构成发行批准、法律意见、
真实 smoke 授权或最终 Go。

## 禁止事项

- 不发布、合并、push、rebase、reset、清理或删除任何真实文件。
- 不联网，不访问 YouTube、OpenAI、Ollama、ffmpeg、Whisper、launchd 或其他服务。
- 不读取 `.env`、环境变量值、凭据、Keychain、Vault、SQLite、日志、缓存、媒体或用户数据。
- 不新增/升级依赖，不修改 `pyproject.toml`、`uv.lock`、源码、测试、配置、ADR、任务卡、状态文档或构建配置。
- 不执行真实资源、真实 smoke、测试、构建、安装、打包、模型/API 调用或许可证扫描工具。

## 审查交接

仅在 `handoffs/TASK-014.md` 末尾追加：固定 base/source HEAD/parent、七路径和清洁度结果、逐项文档与元数据核验、
未运行命令/资源、所有 P0–P3 发现或明确“无 P0–P3”、以及 `APPROVE` 或 `REJECT`。追加后只可用 Git/文本检查
确认该 handoff 是唯一工作树改动；不得提交、启动其他角色、改变任务状态或宣称任务完成。
