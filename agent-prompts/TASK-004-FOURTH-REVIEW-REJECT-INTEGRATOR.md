# TASK-004 第四次审查拒绝与 Correction 6 同步 — Status Integrator

你是 Status Integrator，只负责校验、暂存并提交主控已准备的控制面 Markdown。不得修改准备内容，不得实现或审查产品代码，不得运行 uv、测试、mypy、Ruff、build、数据库或网络命令，不得合并 source，不得启动 Implementer/Reviewer/TASK-005。

## 固定基线

- Repository: `/Users/developer/Documents/youtubek agent`
- Branch: `main`
- Base HEAD: `6c24f4341f98cad961fa3d442d49e5982a0d97cf`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- TASK-004 source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Expected source HEAD: `d510794ffccf54948f967f010685aef1c0a02f3d`
- Source HEAD parent: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`

开始时任一基线、分支、身份、父链或洁净度不符，立即停止并报告 `BLOCKED`。不得自行修复、stash、reset、清理、merge 或选择新 SHA。

## 唯一允许提交的文件

初始 `git status --short` 必须精确显示以下 5 个由主控准备的 Markdown 文件，且暂存区为空：

- `agent-prompts/TASK-004-CORRECTION-6-GROK.md`
- `agent-prompts/TASK-004-FOURTH-REVIEW-REJECT-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

不得有任何其他已跟踪、未跟踪或暂存文件。若范围不精确、文件 hash 在检查期间变化或出现并发写入，停止且不暂存、不提交。

## 只读证据核验

只使用 Git 和文本检查：

1. source worktree 干净，分支/HEAD/身份精确；`d510794...` 的唯一父提交为 `9750df...`，review evidence commit 只修改 `handoffs/TASK-004.md`。
2. Reviewer 明确记录：state integration 30、discovery unit 35、discovery integration 10、全量 131、`mypy src`、Ruff、CLI、build、migration 包含性与固定 Diff 均 PASS；真实 YouTube、Cookie/登录、remote components、ffmpeg 和媒体/字幕下载均未运行。
3. Reviewer verdict 为 `REJECT`，P0/P2/P3 均为 0，P1 精确为 2：
   - 真实 `SQLiteStateRepository` 运行时匹配，但 frozen record 返回类型因可变 Protocol attributes 无法通过真实 mypy wiring；
   - 纯空白 `pipeline_version` 在 Service 边界未被拒绝，先调用 Provider 后泄漏 `sqlite3.IntegrityError`。
4. AC-1 至 AC-5 与 D-01 至 D-06 记录为 PASS；D-07/D-08 因上述两个 P1 为 FAIL。不得把全量测试通过误写成 Reviewer `APPROVE`。
5. 所有控制面统一为 TASK-004 `IN_PROGRESS`、原 Grok Implementer 执行 Correction 6、Reviewer 已结束；不得出现 `ACCEPTED/DONE` 或正在审查。
6. Correction 6 只允许修改 `discovery.py`、两份 discovery 测试和 handoff；禁止修改 state/migration/domain/provider/dependency/lock/main，并强制真实静态 mypy wiring probe 与纯空白零副作用回归。
7. TASK-005 保持 `BLOCKED/UNASSIGNED`；ADR-006 虽已 Accepted，但在 TASK-004 `DONE` 前不得创建 worktree、分配实现、安装依赖或启动网络路径。
8. 真实 YouTube/字幕、Cookie/登录、`.netrc`、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权。

## Diff 与提交门禁

依次运行：

```bash
git diff --check
git diff --name-status
git diff -- agent-prompts/TASK-004-CORRECTION-6-GROK.md agent-prompts/TASK-004-FOURTH-REVIEW-REJECT-INTEGRATOR.md docs/PROJECT_STATUS.md tasks/README.md tasks/TASK-004-discovery-metadata.md
```

人工确认：无未替换 SHA、错误角色/路径/状态、尾随空白或多余 EOF 空行；准备文件 hash 在检查前后不变。

只有全部通过后，精确暂存上述 5 个文件并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: return TASK-004 static repository contract for correction
```

提交后确认：

- 新提交唯一父提交为 `6c24f4341f98cad961fa3d442d49e5982a0d97cf`；
- 提交范围精确为上述 5 文件；
- main 与 source `git status --short` 均无输出；
- source HEAD 仍为 `d510794...`；
- 新提交是 `TASK-004-CORRECTION-6-GROK.md` 最近添加提交，可供 Implementer 动态解析；
- 未运行产品命令、未修改 source、未启动任何 Worker、未 push/merge/清理。

## 返回主控

```text
Task: TASK-004 fourth review reject / correction 6 sync
Role: Status Integrator
Base: main@6c24f4341f98cad961fa3d442d49e5982a0d97cf
Head commit:
Git identity:
Committed files:
Checks:
TASK-004 review evidence/source/status:
P1 correction scope:
TASK-005 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
