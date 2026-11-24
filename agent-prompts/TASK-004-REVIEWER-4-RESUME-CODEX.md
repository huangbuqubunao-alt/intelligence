# TASK-004 第四次独立 Codex Reviewer 恢复授权

你是此前因 main 出现并发未提交 ADR-006 文档而按门禁停止的 TASK-004 第四次独立 Codex Reviewer。该停止发生在任何产品检查、探针、handoff 写入或 review evidence commit 之前；source worktree 未修改。你可以在同一 Reviewer 会话恢复，不需要更换 Reviewer，也不得把这次环境阻塞记为产品缺陷。

本包只替换 `agent-prompts/TASK-004-REVIEWER-4-CODEX.md` 的 **main authorization/cleanliness 启动门禁**；原包的 reviewed source、范围、必读材料、全部检查、四组独立探针、AC/D 矩阵、P0-P3、红线、handoff 和提交要求全部保持不变，必须完整执行。

## 恢复授权基线

- Main worktree: `/Users/developer/Documents/youtubek agent`
- Prior review authorization: `5f8646645bbaad274c094777261deff4636521fc`
- Resume authorization: 用本文件在 main 的最近添加提交动态解析
- Source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Reviewed source head: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`
- Git identity: `Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

只有提交本包的 Status Integrator 返回 `INTEGRATED` 后才能恢复。先运行：

```bash
main_repo='/Users/developer/Documents/youtubek agent'
resume_authorization="$(git -C "$main_repo" log -1 --format=%H -- agent-prompts/TASK-004-REVIEWER-4-RESUME-CODEX.md)"
test -n "$resume_authorization"
test "$(git -C "$main_repo" rev-parse HEAD)" = "$resume_authorization"
test "$(git -C "$main_repo" rev-parse HEAD^)" = "5f8646645bbaad274c094777261deff4636521fc"
test -z "$(git -C "$main_repo" status --short)"
```

确认 `5f864664...resume_authorization` 只包含以下 10 个控制面 Markdown 文件：

- `agent-prompts/ADR-006-ACCEPTANCE-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-4-RESUME-CODEX.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/REUSE_REGISTER.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/decisions/ADR-006-subtitle-acquisition-contract.md`
- `docs/decisions/README.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

该提交只能接受 ADR-006、同步 System Design V1.3 和 TASK-005 门禁；不得修改 TASK-004 任务卡、产品代码、测试、依赖、锁文件或 handoff。确认 TASK-004 在 main 仍为 `IN_REVIEW`，reviewed source 仍为 `9750df...`，没有预写 Reviewer 结论。

然后在 source worktree 确认：

```bash
test "$(git branch --show-current)" = 'grok/task-004-discovery-metadata'
test "$(git rev-parse HEAD)" = '9750df2503a1aee135fdfbcca9f1706bcc9bd8de'
test -z "$(git status --short)"
test "$(git config user.name)" = 'Mozhu'
test "$(git config user.email)" = 'maintainer@example.invalid'
test "$(git config --bool user.useConfigOnly)" = 'true'
```

若 main 或 source 任一门禁失败，再次停止并报告 `BLOCKED`；不得自行 stash、reset、merge、清理或更换 SHA。

## 恢复执行

门禁通过后，完整读取并严格执行：

```text
/Users/developer/Documents/youtubek agent/agent-prompts/TASK-004-REVIEWER-4-CODEX.md
```

执行时采用以下唯一替换：

- 原包要求 main HEAD 等于 `5f864664...` 的启动检查，替换为本包的 `resume_authorization` 检查。
- 原包所有 source SHA、Diff anchor `58c79af...`、检查命令、四组探针和 handoff 父提交 `9750df...` 均不变。
- ADR-006 acceptance commit 只改变 main 文档，不成为 TASK-004 source Diff anchor，也不需要 merge 到 source。

真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载仍不得运行。完成后仍只允许修改并提交 `handoffs/TASK-004.md`；review evidence commit 的父提交必须精确为 `9750df...`。

## 返回主控

沿用原 Reviewer 包返回格式，并额外包含：

```text
Prior BLOCKED reason: concurrent uncommitted main documentation, cleared
Main resume authorization:
Main control diff: exact 10 Markdown files, no TASK-004 product/source change
```
