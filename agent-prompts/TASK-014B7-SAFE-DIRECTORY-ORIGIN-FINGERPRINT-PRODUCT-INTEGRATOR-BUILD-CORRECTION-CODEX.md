# TASK-014B7 — Product Integrator 构建命令更正与一次性继续执行

你是 TASK-014B7 P1 Correction 2 的 Codex Product Integrator。此包只更正离线 build 入口，并在固定不变基线上授予一次性继续执行窗口；
不得修复代码、修改 source、改变任务状态或扩大命令范围。

## 固定执行条件与可复用证据

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint
Role: Product Integrator continuation
Control-plane baseline: main@9e292ddf447f6a8b2219ba3e100f4fec9a67f823
Execution main: dynamic clean main at the single-parent build-correction authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Accepted source branch: codex/task-014b7-safe-directory-origin-fingerprint
Accepted source HEAD: 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
Required sole parent of Reviewer evidence: 4d4366f6a6403403a0d9bed65fbbf862a362eede
Required architecture base: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Only authorized merge: git merge --no-ff 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
```

- 开始前 main/source 分支、HEAD、父链、Correction/完整范围、fixture 删除状态和洁净度必须完全匹配；任一不符立即停止。
- 以下同一不变基线证据已完成且可复用，**禁止重跑**：`uv lock --check`、`uv sync --locked --offline`、Provider/Smoke pytest
  `114 passed`、mypy、Ruff、CLI help。
- 唯一失败命令是未获项目依赖支持的 `.venv/bin/python -m build --no-isolation`；不得重试该命令、不得新增 `build` 依赖或修改锁文件。

## 唯一允许的继续序列

再次确认 main/source 未变且干净后，只可按此顺序执行：

```text
uv build --offline
```

缓存缺失、下载/网络迹象、锁文件变化或 build 失败，立即停止并保留证据；不得合并、修复或重试。仅在 build 成功后，才可执行 Git 静态
检查：fixture 删除无重现、完整 B7 五路径范围、`git diff --check`，以及 stdout/stderr/JSONL/fixture 泄漏扫描。扫描不得输出或记录字段名、
字段值、URL、正文、标题、语言、轨道名、身份值、路径、原始异常、Cookie、token、payload 或用户数据。

所有允许门禁通过且 source 仍干净后，才可在 `main` 执行唯一合并：

```text
git merge --no-ff 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
```

合并后只可核验双亲顺序、accepted source 祖先、first-parent Diff 为 B7 允许五路径子集、锁文件未变和 main/source 洁净度。任何后置门禁
失败均停止并保留证据；不得在整合中修复代码。

## 绝对禁止与状态

- 禁止运行上述序列外的产品命令，包括已通过门禁、`.venv/bin/python -m build`、任何依赖/锁文件命令或修改。
- 禁止真实 YouTube、网络、真实 smoke、认证、媒体/ffmpeg、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、source 清理和任何额外命令。
- 不得修改任务/状态/ADR/prompt；TASK-014B7 保持 `ACCEPTED`，TASK-014 保持 `IN_PROGRESS / No-Go`。本窗口不等于 `DONE`、
  真实 B-1 成功、真实服务验证或发行批准。
