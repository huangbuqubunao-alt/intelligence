# TASK-003/004 Decisions + Reuse Policy Sync — Status Integrator Packet

## 身份

你是原 `main` 控制面终端中的 Status Integrator。你只核对并提交主控已经准备好的 ADR-003/004 批准同步、ADR-005 复用优先策略和任务卡更新；不修改内容、不安装依赖、不克隆候选仓库、不实现产品代码。

## 固定上下文

- Task: `TASK-003/004 decisions and reuse policy sync`
- Role: `Status Integrator`
- Target branch: `main`
- Repository: `/Users/developer/Documents/youtubek agent`
- Required base: `main@e1e7b7c968c8b3fb2216a80a53a7176de615524a`
- Active implementation: TASK-002 remains `IN_PROGRESS` in `/Users/developer/Documents/yia-worktrees/task-002`
- Suggested commit message: `docs: accept storage discovery and reuse decisions`

开始前按顺序完整读取 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/SYSTEM_DESIGN.md`、ADR-003、ADR-004、ADR-005、`docs/REUSE_REGISTER.md`、TASK-003、TASK-004 和本任务包。任一文件冲突、基线不符或范围异常时立即停止，不自行修订内容。

## Expected files

初始 `git status --short` 必须只包含以下 15 个文件：

- `AGENTS.md`
- `agent-prompts/TASK-003-004-DECISIONS-REUSE-INTEGRATOR.md`
- `docs/COLLABORATION.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/REUSE_REGISTER.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/decisions/ADR-003-sqlite-state-store-contract.md`
- `docs/decisions/ADR-004-discovery-ytdlp-contract.md`
- `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
- `docs/decisions/README.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

出现额外文件、并发写入或文件在检查期间变化，立即输出 `BLOCKED`；不得清理、覆盖、取消暂存或吸收其他人的修改。

## 必须确认的内容

1. `main` 精确位于 `e1e7b7c968c8b3fb2216a80a53a7176de615524a`，初始范围只有 15 个 Expected files。
2. ADR-003 为 `Accepted`，包含产品负责人对 S-01 至 S-08 的批准；Schema、`scope_key`、`job_attempts`、迁移、CAS 和任务范围一致。
3. ADR-004 为 `Accepted`，包含产品负责人对 D-01 至 D-08 和 `yt-dlp[default,deno]>=2026.7.4,<2026.8` 的批准；必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令已授权。
4. 真实 YouTube 冒烟、Cookie、账号登录、remote components 和 ffmpeg 在 ADR、任务卡、System Design 与 Project Status 中仍明确未授权。
5. ADR-005 为 `Accepted`，规定 `DIRECT/ADAPT/REFERENCE/REJECT` 四级复用；复用优先没有取消依赖、密钥、付费、许可证、真实 Vault 或系统工具门禁。
6. `docs/REUSE_REGISTER.md` 对附件候选的结论一致：yt-dlp 直接复用；video skill/yt2md 仅适配或参考；TranscriptAPI youtube-skills 在 V1 拒绝；来源不明项目延期。
7. `AGENTS.md`、协作协议和路线图要求开工包包含 `Reuse decision`，Reviewer 检查来源、许可证和边界。
8. TASK-003、TASK-004 仍为 `BLOCKED`，审批均已满足但依赖 TASK-002；不得在本轮设为 `READY` 或创建 worktree。
9. TASK-002 仍为 `IN_PROGRESS`，本轮不触碰其实现 worktree、分支、任务包、代码或锁文件。
10. 15 个文件全部是控制面 Markdown；没有依赖安装、候选仓库代码、图片、密钥、产品代码或生成物。

## 执行步骤

1. 运行并核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   git -C /Users/developer/Documents/yia-worktrees/task-002 branch --show-current
   git -C /Users/developer/Documents/yia-worktrees/task-002 status --short
   ```

2. 运行：

   ```bash
   git diff --check
   git diff --name-status
   rg -n '^Accepted$' docs/decisions/ADR-003-sqlite-state-store-contract.md docs/decisions/ADR-004-discovery-ytdlp-contract.md docs/decisions/ADR-005-reuse-first-delivery-policy.md
   rg -n 'Status: `BLOCKED`' tasks/TASK-003-state-store.md tasks/TASK-004-discovery-metadata.md
   rg -n 'yt-dlp\[default,deno\]>=2026\.7\.4,<2026\.8' docs tasks
   ```

   完整读取并核对 15 个 Expected files；不得编辑。`git diff --name-status` 不显示 untracked 文件是正常现象，必须结合 `git status --short` 检查全部范围。

3. 仅暂存 Expected files：

   ```bash
   git add AGENTS.md agent-prompts/TASK-003-004-DECISIONS-REUSE-INTEGRATOR.md docs/COLLABORATION.md docs/IMPLEMENTATION_ROADMAP.md docs/PRODUCT_DECISIONS.md docs/PROJECT_STATUS.md docs/REUSE_REGISTER.md docs/SYSTEM_DESIGN.md docs/decisions/ADR-003-sqlite-state-store-contract.md docs/decisions/ADR-004-discovery-ytdlp-contract.md docs/decisions/ADR-005-reuse-first-delivery-policy.md docs/decisions/README.md tasks/README.md tasks/TASK-003-state-store.md tasks/TASK-004-discovery-metadata.md
   ```

4. 确认暂存范围与内容：

   ```bash
   git diff --cached --check
   git diff --cached --name-status
   git diff --cached
   git diff --name-only
   git status --short
   ```

   `git diff --name-only` 必须无输出；`git status --short` 必须只显示 15 个 Expected files 且均已暂存。确认没有非 Markdown 文件、产品代码、依赖或锁文件。

5. 创建一个 commit：

   ```bash
   git commit -m "docs: accept storage discovery and reuse decisions"
   ```

6. 提交后运行：

   ```bash
   git status --short
   git rev-parse HEAD
   git -C /Users/developer/Documents/yia-worktrees/task-002 status --short
   ```

   `main` 必须干净；TASK-002 worktree 状态不得被本轮改变。不要运行 `uv add`、`uv sync`、候选代码、真实网络冒烟或 TASK-003/004 Implementer。

## 最终输出

```text
Task: TASK-003/004 decisions and reuse policy sync
Role: Status Integrator
Base: main@e1e7b7c968c8b3fb2216a80a53a7176de615524a
Head commit:
Checks:
- Initial and staged scope:
- ADR-003/004 approval records:
- ADR-005/reuse register consistency:
- TASK-003/TASK-004 states and dependency:
- TASK-002 unchanged:
- Unapproved operations remain blocked:
- git diff --check:
- git diff --cached --check:
- Post-commit statuses:
Committed files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
