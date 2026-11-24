# TASK-013A closure — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、合并、推送、删除工作区或启动任何 Worker。

## 固定对象

- Main base：`main@8f70fe34fdaf0788296cdb5aba22f70358462aac`，必须干净且为唯一父基线。
- 已整合 source：`codex/task-013a-local-transcription-continuation@62d87067af84171a2ee7195f3e7d4c4fddcb9980`；source worktree 必须保持干净。
- Merge 必须恰有两个父，顺序为 `ef64d2c58c657cfa8bc590c68df16fa026f14e80` 和 `62d87067af84171a2ee7195f3e7d4c4fddcb9980`；accepted source 必须是 merge 祖先。
- first-parent Diff 必须精确为 `handoffs/TASK-013A.md`、`src/youtube_intel/transcripts.py`、`tests/integration/test_local_transcription_service.py`；锁文件不变。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-013A.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main/source identity `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、merge 父链/祖先、first-parent 范围、锁文件、main/source 洁净度和所有 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围、`git diff --cached --check`；任何字节漂移立即停止。
3. 将 TASK-013A 在任务卡、任务索引、项目状态和 handoff 一致标为 `DONE`，记录 merge `8f70fe34...` 及既有 Integration evidence。不得重跑产品门禁。
4. TASK-013 继续 `BLOCKED/UNASSIGNED`，直到主控创建新的正式分配包以基于真实服务流重新建立 E2E；TASK-014 保持 BLOCKED。
5. 提交信息：`docs: close TASK-013A after integration`。提交后 main/source 必须干净；不得 push、删除或清理 worktree。

## 回传格式

```text
Task: TASK-013A closure
Base / Head: <base> -> <head>
Merge/source/status: 8f70fe34... / 62d87067... / TASK-013A=DONE
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
