# ADR-012 acceptance / TASK-013A proposal sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 ADR-012 与 TASK-013A 控制面 Markdown；不得创建 worktree/branch、启动 Worker、运行产品命令、修改 source、推送或合并。

## 固定对象

- Main base：`main@2130452835e838f08ae4b2d2329870ebea1c2a32`；HEAD 必须精确匹配，且新提交必须以它为唯一父提交。
- 产品负责人已批准“方案 2”：将本地 Whisper 转写作为正式、可恢复的 TRANSCRIPT 阶段能力接入后续评分/知识流程；这不是在 TASK-013 测试中伪造状态推进。
- 此次只接受 ADR 和创建任务卡：不授权模型下载/加载、ffmpeg、媒体/YouTube、网络、真实 Vault、凭据、付费/云端调用或 CLI production composition。

## 唯一允许提交范围

1. `agent-prompts/ADR-012-TASK-013A-ACCEPTANCE-INTEGRATOR.md`
2. `docs/PRODUCT_DECISIONS.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/SYSTEM_DESIGN.md`
5. `docs/IMPLEMENTATION_ROADMAP.md`
6. `docs/decisions/ADR-012-local-transcription-continuation-contract.md`
7. `docs/decisions/README.md`
8. `tasks/README.md`
9. `tasks/TASK-013-e2e-acceptance.md`
10. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main identity 为 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree 与精确十文件范围。
2. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；任何字节漂移立即停止，不覆盖并发改动。
3. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、Vault、云端、模型、凭据、launchctl 或任何产品文件 I/O 命令。
4. ADR-012=`Accepted`；TASK-013A=`READY/UNASSIGNED`，仅等待独立 worktree/Implementer/Reviewer 分配；TASK-013=`BLOCKED/UNASSIGNED`，等待 TASK-013A 整合后重新开始离线验收；TASK-014 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: accept local transcription continuation contract`。提交后 main 必须干净；不得创建 TASK-013A source worktree 或预写 Implementer/Reviewer 包。

## 回传格式

```text
Task: ADR-012 acceptance / TASK-013A proposal sync
Base / Head: <base> -> <head>
Committed files: <exact ten>
States: ADR-012=Accepted; TASK-013A=READY/UNASSIGNED; TASK-013=BLOCKED/UNASSIGNED
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
