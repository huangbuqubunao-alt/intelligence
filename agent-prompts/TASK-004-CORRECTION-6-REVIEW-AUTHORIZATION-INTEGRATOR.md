# TASK-004 Correction 6 审查授权同步 — Status Integrator

你是 Status Integrator，只负责校验、暂存并提交主控准备的控制面 Markdown。不得修改准备内容，不得实现或审查产品代码，不得运行 uv、pytest、mypy、Ruff、build、数据库或网络命令，不得合并 source，不得启动 Reviewer/TASK-005。

## 固定基线

- Repository: `/Users/hua/Documents/youtubek agent`
- Branch: `main`
- Base HEAD: `091a591f56c9aec73d4e7d979635b866493326a9`
- Git identity: `Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- TASK-004 source worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Expected source HEAD: `7272528a3c5603087446251ee96ae4766fedeb96`
- Source HEAD parent: `d510794ffccf54948f967f010685aef1c0a02f3d`

任一 main/source 基线、分支、父链、身份或洁净度不符，立即停止并报告 `BLOCKED`。不得 stash、reset、merge、rebase、清理或选择新 SHA。

## 唯一允许提交的文件

初始 `git status --short` 必须精确为以下 5 个由主控准备的 Markdown 文件，且暂存区为空：

- `agent-prompts/TASK-004-CORRECTION-6-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-5-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

不得存在其他已跟踪、未跟踪或暂存文件。检查期间若文件 hash 变化或出现并发写入，停止且不暂存、不提交。

## 只读证据核验

只用 Git 和文本检查：

1. source worktree 干净，HEAD/父提交精确；correction 6 commit `7272528...` 只修改 `discovery.py`、两份 discovery 测试和 handoff 四个允许文件。
2. `58c79af...7272528...` 完整产品差异仍为原批准 17 路径，`git diff --check` 通过；无 state/migration/domain/provider/dependency/lock/control-plane 变化。
3. 实现静态证据与代码一致：只读 Protocol fields 改为 property；两条 Service 路径在任何 Provider/Repository 调用前使用 `pipeline_version.strip()` 拒绝纯空白；没有 Any/object/cast/ignore/wrapper/具体 SQLite import。
4. Implementer 自报 state 30、unit 36、integration 10、全量 132、mypy src、独立 wiring probe、Ruff、CLI、build/migration 全 PASS；准备内容必须明确这些仍需 Reviewer 独立复跑。
5. 主控聚焦预核验只记录：精确 mypy wiring probe PASS；whitespace unit `1 passed`。不得把它写成 Reviewer `APPROVE` 或完整验收。
6. TASK-004 在所有当前控制面统一为 `IN_REVIEW`，reviewed source 为 `7272528...`，第五次全新独立 Codex Reviewer 尚未启动；不得预写其 Verdict、`ACCEPTED` 或 `DONE`。
7. Reviewer 包要求完整全量门禁、两个独立探针、AC-1 至 AC-5、D-01 至 D-08、P0-P3、范围/红线/复用复核；最终只允许修改 handoff。
8. TASK-005 保持 `BLOCKED/UNASSIGNED`；不得创建 worktree、安装依赖或启动真实网络路径。
9. 真实 YouTube/字幕、Cookie/登录、`.netrc`、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权。

## Diff 与提交门禁

```bash
git diff --check
git diff --name-status
git diff -- agent-prompts/TASK-004-CORRECTION-6-REVIEW-AUTHORIZATION-INTEGRATOR.md agent-prompts/TASK-004-REVIEWER-5-CODEX.md docs/PROJECT_STATUS.md tasks/README.md tasks/TASK-004-discovery-metadata.md
```

完整读取两个新包，人工确认无占位符、错误 SHA/角色/路径、冲突状态、尾随空白或多余 EOF 空行。检查前后准备文件 hash 必须一致。

全部通过后，精确暂存上述 5 文件并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-004 correction 6 independent review
```

提交后确认：

- 新提交唯一父提交为 `091a591f56c9aec73d4e7d979635b866493326a9`；
- 提交范围精确为上述 5 文件；
- main 与 source 均干净，source 仍为 `7272528...`；
- 新提交是 `TASK-004-REVIEWER-5-CODEX.md` 的最近添加提交；
- 未运行产品命令、未修改/合并 source、未启动 Worker、未 push/清理。

## 返回主控

```text
Task: TASK-004 correction 6 review authorization sync
Role: Status Integrator
Base: main@091a591f56c9aec73d4e7d979635b866493326a9
Head commit:
Git identity:
Committed files:
Checks:
TASK-004 source/scope/status/reviewer:
Pre-review evidence:
TASK-005 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
