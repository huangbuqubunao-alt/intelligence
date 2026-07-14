# TASK-002 Authorization Sync — Status Integrator Packet

## 身份

你是原 `main` 控制面终端中的 Status Integrator。你只核对并提交主控已经准备好的 `TASK-002` 依赖授权与 `READY` 状态，不修改内容、不安装依赖、不创建实现 worktree，也不实现产品代码。

## 固定上下文

- Task: `TASK-002 authorization sync`
- Role: `Status Integrator`
- Target branch: `main`
- Repository: `/Users/hua/Documents/youtubek agent`
- Required base: `main@913020b5dd0b94f93dc3539b23f2a8af2893a53e`
- Suggested commit message: `docs: authorize task 002 contracts`

开始前按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRODUCT_DECISIONS.md` 的 DEC-02
5. `tasks/README.md`
6. `tasks/TASK-002-config-domain-contracts.md`

任一文件冲突、基线不符或范围异常时立即停止，不自行选择解释或修订内容。

## Expected files

初始 `git status --short` 必须只包含以下 5 个文件：

- `agent-prompts/TASK-002-AUTHORIZATION-INTEGRATOR.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`

不得包含产品代码、`pyproject.toml`、`uv.lock`、缓存、构建产物或其他任务文件。出现任何额外文件、并发写入或文件在检查期间变化，立即输出 `BLOCKED`；不得清理、覆盖、取消暂存或吸收其他人的修改。

## 必须确认的内容

1. `TASK-001` 保持 `DONE`，其 merge commit 保持 `5273e069aa34392db957e82b8803a709bdd1ab1f`。
2. `TASK-002` 为 `READY`、`Assignee: UNASSIGNED`，依赖仍为 `TASK-001`。
3. 直接依赖范围精确为 `pydantic>=2.13.4,<2.14` 与 `PyYAML>=6.0.3,<7`。
4. 授权仅覆盖必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 写入，以及 `uv add`、`uv lock --check`、`uv sync --locked` 和任务卡验证命令。
5. 可选 extras、其他运行时依赖、云调用、真实密钥、真实 Vault、launchd、数据库 Schema 和范围外文件仍未授权。
6. YAML 安全边界明确要求 `yaml.safe_load` 或等价 `SafeLoader`，禁止不安全 Loader。
7. `TASK-003`、`TASK-004` 及后续任务继续为 `BLOCKED`；不得在本轮提前分配。

## 执行步骤

1. 运行并核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   ```

2. 检查完整 Diff 和空白：

   ```bash
   git diff --check
   git diff --name-status
   git diff -- agent-prompts/TASK-002-AUTHORIZATION-INTEGRATOR.md docs/PRODUCT_DECISIONS.md docs/PROJECT_STATUS.md tasks/README.md tasks/TASK-002-config-domain-contracts.md
   ```

3. 逐项确认“必须确认的内容”。只读核对；不得编辑文件。
4. 仅暂存 Expected files：

   ```bash
   git add agent-prompts/TASK-002-AUTHORIZATION-INTEGRATOR.md docs/PRODUCT_DECISIONS.md docs/PROJECT_STATUS.md tasks/README.md tasks/TASK-002-config-domain-contracts.md
   ```

5. 确认暂存范围与内容：

   ```bash
   git diff --cached --check
   git diff --cached --name-status
   git diff --cached
   git diff --name-only
   git status --short
   ```

   `git diff --name-only` 必须无输出；`git status --short` 必须只显示 5 个 Expected files 且均已暂存；暂存文件必须精确等于 Expected files。

6. 创建一个 commit：

   ```bash
   git commit -m "docs: authorize task 002 contracts"
   ```

7. 提交后运行：

   ```bash
   git status --short
   git rev-parse HEAD
   ```

   工作区必须干净。不要安装依赖、运行产品测试、创建 worktree、改变 Assignee 或把任务设为 `IN_PROGRESS`。

## 最终输出

```text
Task: TASK-002 authorization sync
Role: Status Integrator
Base: main@913020b5dd0b94f93dc3539b23f2a8af2893a53e
Head commit:
Checks:
- Initial and staged scope:
- TASK-002 READY and dependency approval:
- TASK-001/TASK-003/TASK-004 states:
- git diff --check:
- git diff --cached --check:
- Post-commit status:
Committed files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
