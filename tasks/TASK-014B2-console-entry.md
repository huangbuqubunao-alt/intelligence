# TASK-014B2：正式 console entry

- Status: `DONE`
- Assignee: `Codex Product Integrator (integrated; closure recorded)`
- Owner role: PO + TL + QA
- Size: S
- Risk: Medium
- Depends on: TASK-014B0 `DONE`; ADR-011; ADR-014 Accepted

## 目标

为已安装项目提供正式 `youtube-intel` 命令，精确映射到既有 `youtube_intel.cli:main`。该任务只补齐打包入口，
不得产生第二套 CLI、修改命令语义或扩大任何真实资源权限。

## 固定分配

- 控制面基线：`main@820ff34fbd481e31b50d9d9d54828810d8ab7ca4`。
- 实施 worktree：`/Users/developer/Documents/yia-worktrees/task-014-phase-b2-console-entry`。
- 分支：`codex/task-014-phase-b2-console-entry`。
- 正式 Implementer 包：`agent-prompts/TASK-014B2-CONSOLE-ENTRY-IMPLEMENTER-CODEX.md`。
- Reviewer：全新独立 Codex Reviewer（本包不启动）。
- Reuse decision：`DIRECT` — 复用既有 `youtube_intel.cli:main`、uv build backend、锁文件和现有 CLI/operations 契约；
  不新增第三方代码或依赖。

## B-1 阻断证据隔离

B-1 source 的 `4a349055…` 是“正式 console entry 缺失”的阻断证据。它不得合并、不得当作 smoke 成功 evidence，
也不得据此自行重试真实 smoke；B-2 只解决安装入口前置条件，TASK-014 仍为 `IN_PROGRESS / No-Go`。

## 独立 Reviewer 授权

- 主线控制面基线：`main@b4d6981e56da8366f0c512a8f0544396d47cd209`。
- 唯一 source：`/Users/developer/Documents/yia-worktrees/task-014-phase-b2-console-entry`，分支
  `codex/task-014-phase-b2-console-entry`，审查 HEAD `f6e71e027c86f16cc34e062fef0a753c73b42d05`，唯一父提交
  `b4d6981e56da8366f0c512a8f0544396d47cd209`。
- 正式 Reviewer 包：`agent-prompts/TASK-014B2-CONSOLE-ENTRY-REVIEWER-CODEX.md`。Reviewer 只可向 source
  `handoffs/TASK-014B2.md` 追加证据；不得修改 source 其他路径、main 或任务状态。
- 审查必须独立确认正式 console entry、离线 wheel 安装、原有 CLI 行为、依赖图与 README/operations 一致；禁止
  真实 YouTube/B-1、网络、真实资源和发布。

## 主控验收与 Product Integrator 授权

- accepted reviewer evidence：`835f5ff507308f08b7b88c794a6d7d11b3a9dd74`，唯一父提交
  `f6e71e027c86f16cc34e062fef0a753c73b42d05`；Verdict=`APPROVE`，P0–P3 均无。
- Product Integrator 包：`agent-prompts/TASK-014B2-CONSOLE-ENTRY-PRODUCT-INTEGRATOR-CODEX.md`。它固定
  accepted source、`--no-ff`、五路径范围、`uv.lock`/依赖图不变，并只授权整合后的离线 lock、focused test、CLI、
  mypy、Ruff、build 和 wheel-entry 核验。
- 本验收只接受离线正式入口资料；不代表 B-1 smoke、发布批准、许可证/NOTICE 结论、风险接受或 TASK-014 Go。
  TASK-014 继续 `IN_PROGRESS / No-Go`；B2 的 `DONE` 只在整合后由本 closure 记录。

## 整合与 closure

- Product Integrator 已以 `--no-ff` merge `main@99a22d29922e16c26b86ebe2ecfba9d91e8ac5a2` 整合 accepted source。
  双父顺序为 `8aa5be6...`、`835f5ff...`；accepted source 是 merge 祖先，first-parent Diff 严格为 B2 五路径，
  `uv.lock` 与依赖图无差异，source 保持干净。
- 既有整合后离线证据：locked lock/sync、focused console-entry test（`1 passed`）、console/module CLI help、mypy、
  Ruff、offline build 与临时离线 wheel-entry 安装核验均通过。
- B2 因此关闭为 `DONE`；这只关闭正式 console entry 前置条件，不等于真实 B-1 通过、发布批准或 TASK-014 Go。

## 唯一允许修改范围

1. `pyproject.toml`（仅 `[project.scripts]` 的 `youtube-intel = "youtube_intel.cli:main"`）
2. `uv.lock`（仅当 `uv lock --check` 要求重生成；锁定依赖集合、版本、来源和依赖关系不得变化）
3. `tests/integration/test_console_entry.py`（可新建；仅离线入口/安装后命令回归）
4. `README.md`（正式安装命令说明）
5. `docs/operations.md`（正式命令说明；不改命令语义）
6. `handoffs/TASK-014B2.md`（可新建）

不得修改 `src/`、既有测试、Schema/migration、配置、业务能力、任务状态、控制面、项目 LICENSE 或任何 B-1
evidence。范围不足时停止并报告 `DECISION NEEDED`。

## 验收标准

- [ ] 安装元数据只新增一个 `youtube-intel` console entry，目标精确为 `youtube_intel.cli:main`。
- [ ] `youtube-intel --help` 与 `python -m youtube_intel --help` 在离线已安装环境均可运行，且没有网络/Provider/Vault/
  媒体/模型副作用。
- [ ] 既有退出码、参数解析、默认 fail-closed 和 `smoke-public-subtitles` 的受限边界不变；B-2 不执行真实 smoke。
- [ ] 若 `uv.lock` 重生成，包集合、版本、来源和依赖关系经 Diff/文本证据确认不变。
- [ ] README、operations 与 handoff 不将入口可用写成 B-1 通过、发布批准或 TASK-014 Go。

## 后续 Implementer 授权的离线验证

- `uv lock --check`；仅必要时 `uv lock`，随后再次 `uv lock --check`。
- `uv sync --locked`、`uv run python -m pytest tests/integration/test_console_entry.py`。
- `uv run youtube-intel --help`、`uv run python -m youtube_intel --help`，以及经批准的离线安装包入口检查。
- `uv run mypy src`、`uv run ruff check .`、`uv build --offline`、`git diff --check`。

禁止任何网络、真实 YouTube/字幕 smoke、依赖增删升级、真实 Vault/凭据、媒体/ffmpeg、模型/Ollama/OpenAI、发布、
push、merge、rebase、reset 或清理。
