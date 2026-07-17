# TASK-005 Correction 3 第四次独立审查授权同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的 Correction 3 实现证据、TASK-005 `IN_REVIEW` 状态和第四次全新独立 Codex Reviewer 授权。不得修改准备内容、产品 source 或 handoff，不得运行 uv、测试、构建、数据库、网络或真实路径，不得启动 Reviewer、合并、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@d783f705bd749b9e691456fd85f8af1635d9f32f`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Third review evidence：`30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Correction 3 / source HEAD：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Correction 3 parent：`30c665181db77607648aa1a6fdbb1d5502b71d7d`

任一 main/source 基线、身份、父链、分支、洁净度或范围不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-CORRECTION-3-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-005-REVIEWER-4-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为这 5 个文件，暂存区为空；不得有其他 tracked、untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. Correction 3 唯一父提交为 third review evidence，非 merge/amend/rebase；source worktree 干净。
2. Correction 3 Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
3. 完整 `b28f52d...abf2acb...` 产品范围仍只属于原批准的 8 个路径组/11 个文件；`state.py`、migration、`complete_stage`、配置、CLI、`pyproject.toml` 和 `uv.lock` 未被 Correction 3 修改。
4. handoff 记录 3 个 P1 的 RED/GREEN：公共 Adapter 安全边界、可信 cache provenance、streaming metadata 资源边界。Implementer 自报 contracts 50、policy 30、integration 77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容与固定 Diff 均 PASS；此处只记录自报，不得写成 Reviewer APPROVE。
5. 静态证据显示：Service 在 enumerate/read 两个公共 Adapter 边界重建安全错误；cache 绑定成功 Provider-call、response Artifact ID、确定性 key、provenance ID 和 SHA；name runs/buckets 在第 1001/513 项提前拒绝。不得以静态核验替代独立语义审查。
6. 既有 P2（Service 职责与私有 test hook 聚合）仍明确保留；不得预写为关闭或仅因 P2 自动拒绝。
7. 控制面统一把 TASK-005 设为 `IN_REVIEW`；Correction 3 source 固定为 `abf2acb...`，第四个全新独立 Codex Reviewer 已授权但尚未启动。不得写为 ACCEPTED 或 DONE。
8. Reviewer 包必须独立复跑所有离线门禁，验证 P1-1 公共 Adapter 安全边界、P1-2 可信 provenance、P1-3 streaming resource bounds，并复核此前 Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15 与五轴质量；Reviewer 只可修改 source handoff。
9. ADR-007 仍为 `Proposed`；TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`，TASK-005A 不存在。
10. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、真实 Vault/密钥继续未授权。
11. 本轮不运行产品命令，不修改 source，不启动 Reviewer，不预写 Verdict，不 merge、push 或清理。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

确认 5 文件范围、状态、SHA、Finding、禁令、空白、EOF 与文件 hash。全部通过后精确暂存 5 文件，并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-005 correction 3 review
```

提交后确认：

- 新提交唯一父提交为 `d783f705bd749b9e691456fd85f8af1635d9f32f`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `abf2acb...`；
- 新提交可由 `git log -1 -- agent-prompts/TASK-005-REVIEWER-4-CODEX.md` 动态解析为 review authorization；
- TASK-005=`IN_REVIEW`，第四次 Reviewer 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 Correction 3 review authorization sync
Role: Status Integrator
Base: main@d783f705bd749b9e691456fd85f8af1635d9f32f
Head commit:
Git identity:
Committed files:
Checks:
Correction source/scope/status:
Fourth Reviewer authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
