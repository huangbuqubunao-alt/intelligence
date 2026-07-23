# TASK-012 — Product Integrator

你是全新的 Codex Product Integrator。只整合已验收的 TASK-012 source；不得开发、修复、重写历史、推送或清理 source worktree。

## 动态授权与固定对象

- Execution base：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-012-INTEGRATOR.md` 必须解析为本授权提交，且 main 中 TASK-012=`ACCEPTED`。
- Source：`/Users/hua/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@4333b1d2bcd0a4b32162ab2d67f112c92fa7d0a3`，必须干净。
- Accepted evidence 唯一父为 Correction 1 `d046c394e3c6bcf47c05231f71dbf50db4c1f5f8`；original base 为 `8e322f362d2ff0972ee987b7c06c8453a9dce73d`。
- 完整 source Diff 只能为 12 个批准路径：三份 CLI/logging/entry、`pyproject.toml` source-include、root plist/docs、三份相同 package resources、operations test 与 handoff；依赖、`uv.lock`、build backend 不得变化。

## 前置门禁与整合

1. 核验 main/source 分支、HEAD、父链、身份、initial clean、accepted verdict、handoff-only review evidence 与全范围；敏感扫描不得发现凭据、真实用户内容或 `launchctl` 调用。
2. 重跑 locked check/sync、operations tests、full pytest、mypy、Ruff、顶层/五个子命令 help、两份 `plutil -lint`、offline build；核验 sdist 含 migration/root plist/docs，wheel 含 migration/三份 package resources，且每对静态文件字节/SHA-256 相同。
3. 使用 `git merge --no-ff --no-commit 4333b1d2bcd0a4b32162ab2d67f112c92fa7d0a3`；复核 cached scope 与 `git diff --cached --check`。冲突或范围异常立即终止，不解决冲突或修改代码。
4. 创建双父 merge commit，第一父为 execution base、第二父为 accepted source；提交信息 `merge: integrate TASK-012 CLI operations`。
5. 合并后复跑上述离线门禁；确认 first-parent Diff 精确为 12 路径、依赖/锁/build backend 边界正确、main/source 干净并保留 source。TASK-012 保持 `ACCEPTED`，不得自行写 DONE；TASK-013/014 保持 BLOCKED；不得 push、launchctl 或清理。

## 回传格式

```text
Task: TASK-012
Role: Product Integrator
Execution base: <sha>
Source head: 4333b1d...
Merge commit: <sha>
Merge parents: <base>, <source>
Checks: <results>
Post-merge task status: ACCEPTED
Verdict: INTEGRATED | BLOCKED
```
