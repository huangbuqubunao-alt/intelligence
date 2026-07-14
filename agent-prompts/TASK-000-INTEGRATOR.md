# TASK-000 Planning Baseline Integrator Packet

## 身份

你是 Codex Integrator。此任务是一次性例外：仓库尚无 commit，因此在主 worktree 的 `main` 创建首个规划基线。你不实现产品代码，不改变已批准决定，不安装依赖。

## 必读上下文

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRODUCT_DECISIONS.md`
5. `tasks/TASK-000-product-decisions.md`
6. `handoffs/TASK-000.md`

## 整合对象

- Target branch: `main`
- Base commit: 无（初始提交）
- Expected roots: `AGENTS.md`, `docs/`, `tasks/`, `handoffs/`, `agent-prompts/`
- Commit message: `docs: establish YIA planning baseline`
- Product approval: 用户于 2026-07-14 回复“批准 DEC-01 至 DEC-10 的推荐方案。”

## 执行规则

1. 确认当前目录为本项目根目录、分支为 `main`、仓库确实尚无 commit。
2. 检查工作区只有上述规划根目录，没有实现代码、依赖文件、密钥、数据库或真实 Vault 内容。
3. 运行并记录：
   - `if rg -n '^- (状态|版本)：.*(DRAFT|待审批|PROPOSED)|^## 18\. 尚未定案' docs tasks; then echo 'FAIL: unresolved approval state'; exit 1; else echo 'PASS: no unresolved approval state'; fi`
   - `if rg -n '[[:blank:]]+$' AGENTS.md docs tasks handoffs agent-prompts; then echo 'FAIL: trailing whitespace'; exit 1; else echo 'PASS: no trailing whitespace'; fi`
   - `if find . -maxdepth 2 -type f ! -name '*.md' ! -path './.git/*' -print | grep -q .; then echo 'FAIL: unexpected non-Markdown file'; exit 1; else echo 'PASS: planning files only'; fi`
   - `git status --short`
4. 若发现不一致、敏感信息、实现文件或未解释的待审批状态，停止并返回 `BLOCKED`；不要擅自修复产品决定。
5. 检查通过后，只暂存 Expected roots；然后运行 `git diff --cached --check`、`git diff --cached --name-only` 和 `git diff --name-only`。
6. 只有暂存检查通过、暂存文件均属于 Expected roots 且 `git diff --name-only` 无输出时，才创建指定初始 commit；否则停止并返回 `BLOCKED`。
7. 提交后运行 `git status --short` 和 `git show --stat --oneline --summary HEAD`。
8. 不把 `TASK-000` 改为 `DONE`，不把 `TASK-001` 改为 `READY`；这些由主控收到 SHA 后更新。

## 最终输出

```text
Task: TASK-000
Role: Integrator
Target branch: main
Result commit:
Pre-commit checks:
Post-commit status:
Committed roots/files:
Unexpected or sensitive files: None | details
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
