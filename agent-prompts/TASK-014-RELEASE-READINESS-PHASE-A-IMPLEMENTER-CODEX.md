# TASK-014 Phase A — Codex Implementer（发行资料与风险披露）

你是 TASK-014 Phase A 的唯一 Codex Implementer。当前 `main` 的本分配提交是唯一实时控制面；本 worktree
的任务卡和状态快照仅是固定基线。先完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、
`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/ACCEPTANCE_REPORT.md`、
`agent-prompts/PREFLIGHT-TASK-014-RELEASE-READINESS-SCOUT.md` 与本包。Scout 聊天回传是本包的产品输入：
离线证据不等于真实验证；许可证、NOTICE、BPE 文件级归属、真实资源和 at-most-once 风险均未获发布签署。
如文件与本包冲突，停止并报告。

## 固定分配

```text
Task: TASK-014 Phase A — Release Readiness:发行资料与风险披露
Role: Implementer
Agent: Codex
Base: main@54b5be8c28554b70b1e3f294d6ed6f9f6fee2c21
Worktree: /Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-a
Branch: codex/task-014-release-readiness-phase-a
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — 已锁定的项目元数据、现有许可/来源记录与 Python/Git 文本资料；不得新增或复制第三方代码
```

## Scout 已冻结输入

- 当前离线验收覆盖固定夹具、恢复和包内容，不能替代真实 YouTube、字幕、媒体、ffmpeg、Whisper、Ollama、
  OpenAI、真实凭据、真实 Vault 或 launchd 验证。
- 发行级许可证/NOTICE 清单尚不存在；`mutagen==1.48.1` 的 GPL-2.0-or-later 分发处置、OpenAI SDK/
  tiktoken/Jinja2/MarkupSafe 的发行 NOTICE，以及 84 个锁定包的逐组件证据都未获得发行签署。
- 包内 `o200k_base.tiktoken` 已有官方 Blob 来源、`3,613,922` bytes 与固定 SHA-256 的离线包内容证据；
  运行时禁止网络回退，但文件级许可证、归属和 NOTICE 未决，不能推定可分发。
- 已接受的恢复机制是 at-most-once best effort；外部 Provider 成功到 SQLite 提交、文件 replace 到 SQLite 提交、
  音频 cleanup 最终 CAS 都保留崩溃窗口，不能声称严格 exactly-once。
- `.gitignore` 的未锚定 `data/`、`logs/` 是既登记的发布门禁风险；README 与发行检查表尚未存在，
  因而没有干净环境发行/恢复证据。

## 产品目标与完成标准

为 PO/TL/QA 提供可签署的发行资料，不改变任何产品能力：

1. 建立发行级 SBOM 与第三方许可证/NOTICE 清单，区分已证实信息和待决项；不得推断文件级许可或分发兼容性。
2. 建立 README 与发布检查表，使用户明确离线已验证能力、未验证真实能力、发行前的签署责任和 No-Go 条件。
3. 用面向用户的文字披露 at-most-once best-effort 边界：外部 Provider→SQLite、文件 replace→SQLite、音频 cleanup 最终 CAS
   均不是严格 exactly-once；不能夸大为完全消除崩溃窗口。
4. 记录 `o200k_base.tiktoken` 的官方 Blob 来源、固定 SHA-256
   `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`、运行时无网络回退，且把其文件级
   归属/NOTICE 留为阻断性发布决策；同样记录 `mutagen` GPL-2.0-or-later 的分发门禁。
5. 设计但绝不执行四阶段 smoke 授权矩阵：公开 YouTube/字幕、受控媒体+ffmpeg+Whisper、本机 Ollama+固定模型、
   OpenAI+临时 Vault。每阶段必须列出数据范围、明确所需 PO 授权、成功证据和停止条件；真实 Vault 始终不在本阶段授权内。
6. 把 `.gitignore` 中的 `data/`、`logs/` 改成只匹配仓库根的规则，保护嵌套的源码、测试夹具和文档目录不被误忽略。

## 唯一允许修改范围

1. `.gitignore`
2. `README.md`
3. `docs/SBOM.md`
4. `docs/THIRD_PARTY_NOTICES.md`
5. `docs/RELEASE_CHECKLIST.md`
6. `docs/SMOKE_AUTHORIZATION_MATRIX.md`
7. `handoffs/TASK-014.md`

允许新建上述缺失路径；不得修改任何其他文件，包括 `pyproject.toml`、`uv.lock`、产品源码、测试、配置、ADR、任务卡、
项目状态、项目自身 `LICENSE`/`NOTICE`、构建配置或已有验收报告。范围不够时停止并输出 `DECISION NEEDED`。

## 发行资料边界

- SBOM 只能从提交的 `pyproject.toml`、`uv.lock`、现有 ADR/Reuse Register/handoff 生成；记录版本、直接/传递关系、
  已有许可证证据、证据位置和证据缺口。不得声称法律结论，且不能把“锁定”写成“已获分发许可”。
- 第三方清单必须单列 `yt-dlp[default,deno]` 与 `mutagen==1.48.1`、OpenAI SDK 及其传递项、
  `tiktoken` 及其传递项、Jinja2/MarkupSafe、`mlx-whisper`/模型/ffmpeg/Ollama 的条件性发行边界。
- 不得创建项目自身 LICENSE，也不得复制任何第三方 license 全文；只有被既有证据明确支持的 NOTICE/归属事实可以记录。
- README 不得宣称真实 YouTube、Whisper、Ollama、OpenAI、Vault 或 launchd 已验证；应链接 `docs/operations.md`，
  而非修改它或诱导用户在本阶段执行真实操作。
- 发行检查表必须把正式 Go、真实 smoke、二进制/捆绑分发和任何含 BPE 的发行物明确保持 blocked，直到 PO/TL/QA 签署。

## 绝对禁止

- 不发布、push、合并、rebase、reset、清理、删除真实文件或改任务状态。
- 不运行 uv、Python/import、pytest、mypy、Ruff、build、打包、安装、hash 生成、产品 CLI 或任何真实 smoke。
- 不访问网络；不调用 YouTube、ffmpeg、Whisper、Ollama、OpenAI、launchd 或其他服务。
- 不读取环境变量值、`.env`、凭据、Keychain、SQLite、日志、缓存、媒体、真实/临时 Vault 或用户笔记。
- 不新增/升级依赖、修改锁文件、构建配置、数据库 Schema/migration，或选择/创建项目自身 LICENSE。

## 仅允许的收尾检查与交接

只可执行不启动产品的 Git/文本检查：`git diff --check <base>...HEAD`、`git status --short`，以及对允许文件的
`git diff`/`rg`/`sed` 人工复核；不得把它们扩展为测试、构建或 smoke。

完成时按 `handoffs/TEMPLATE.md` 写 `handoffs/TASK-014.md`，逐项列出：SBOM/NOTICE 证据与缺口、BPE 与 mutagen
阻断、用户披露、四阶段授权矩阵、`.gitignore` 修正、未运行资源、范围/红线核验和 `DECISION NEEDED`。创建一个仅含允许路径
的 commit，报告 SHA；不得自行启动 Reviewer、整合、推送或把 TASK-014 设为 DONE。
