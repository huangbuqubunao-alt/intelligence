# TASK-008A Correction 1 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-008A Correction 1
实现证据、`IN_REVIEW` 控制面和第二轮独立 Reviewer 包；不得实现、审查或修改产品
source，不得运行 `uv`、pytest、mypy、Ruff、build、import、数据库、网络或真实资源
命令，不得启动 Worker、merge、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@4eec2e186fce6dedbb105234f624fcb93274c938`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- First review evidence：`0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`
- Correction 1 source：`d95745fd04b115369a9fd70362cd735d1eb70917`
- Original task base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；
  `user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确且暂存区为空；工作区必须恰有下列
5 个准备 Markdown 文件且没有其他修改/未跟踪路径。source 必须位于 Correction 1
source、分支正确且干净。任一条件不符立即 `BLOCKED`；不得 stash、reset、checkout、
merge、rebase、cherry-pick、pull、清理、下载文件或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-008A-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008A-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`

## 必须核验

1. Correction 1 的唯一父提交为 first review evidence，非 merge commit，source 干净。
2. Correction Diff 精确为以下 5 路径：
   - `handoffs/TASK-008A.md`
   - `src/youtube_intel/config.py`
   - `src/youtube_intel/domain.py`
   - `src/youtube_intel/resources/o200k_base.tiktoken`
   - `tests/unit/test_contracts.py`
3. original base...Correction 1 的完整产品范围精确为 8 个已批准路径；
   `pyproject.toml`/`uv.lock` 的 blob 与 reviewed implementation 一致，未新增、删除或
   升级依赖；无 Provider、Prompt、Schema/migration、`state.py`、`complete_stage`、
   CLI 或任务状态 source 改动。
4. A-16 资源存在于 source，字节数 `3,613,922`，SHA-256 精确为
   `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；Correction
   只记录一次官方 Blob GET，不构成其他网络授权。
5. Implementer 自报 contracts `72 passed`、全量 `324 passed`、mypy、Ruff、CLI、
   locked offline sync/build、sdist/wheel 中 migration 与 BPE 资源哈希均 PASS；
   这是待 Reviewer 独立复跑的证据，不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。
6. main 控制面将 TASK-008A 标为 `IN_REVIEW`，全新独立 Codex Reviewer 2 获唯一审查
   权；原 Implementer 已结束。TASK-009A、TASK-008、TASK-009 继续
   `BLOCKED/UNASSIGNED`。
7. 真实 OpenAI/API、密钥读取、付费调用、cloud token-count、Vault/用户内容、媒体、
   模型和所有非 A-16 网络仍未授权；Reviewer 必须离线运行，绝不因 cache 缺失而联网。

## 执行与提交

记录 5 个准备文件 SHA-256，完整检查前后必须一致。检查 main/source 分支、HEAD、
身份与洁净度、source 父链和两种范围、`git diff --check`、prepared LF/EOF/whitespace、
cached Diff/精确 scope 和敏感字面量。只暂存上述 5 个文件，创建单一非 merge commit：

```text
docs: authorize TASK-008A correction 1 review
```

提交后确认唯一父为 Required main base、main/source 均干净，且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-008A-REVIEWER-2-CODEX.md
```

解析为新 commit。不得运行产品命令、写 source、启动 Reviewer、merge、push 或清理。

## 回传格式

```text
Task: TASK-008A Correction 1 review authorization sync
Role: Status Integrator
Base: main@4eec2e186fce6dedbb105234f624fcb93274c938
Head commit:
Git identity:
Committed files:
Checks:
Correction source/scope/status:
Reviewer authorization:
TASK-009A/TASK-008/TASK-009 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
