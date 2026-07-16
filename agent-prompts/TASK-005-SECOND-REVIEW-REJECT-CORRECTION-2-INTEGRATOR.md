# TASK-005 第二次审查拒绝与 Correction 2 同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的第二次 Reviewer REJECT、
3 个 P1 和 Correction 2 授权控制面。不得修改准备内容、产品 source 或 handoff，
不得运行 uv、测试、构建、数据库、网络或真实路径，不得启动 Implementer/Reviewer、
合并、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@a3954bf782430678fa5e0040084bf0d907a52d05`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Correction 1：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Second review evidence / source HEAD：
  `5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Review evidence parent：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`

任一 main/source 基线、身份、父链、分支、洁净度或证据范围不符，立即报告
`BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、
清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-SECOND-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
- `agent-prompts/TASK-005-CORRECTION-2-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为 5 个文件，暂存区为空；不得有其他 tracked、
untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. review evidence 唯一父提交为 Correction 1，且只修改
   `handoffs/TASK-005.md`；source worktree 干净。
2. Correction 1 相对 first review evidence 精确修改 5 个允许文件；完整
   `b28f52d...5bb750e8...` 产品范围仍精确属于原批准的 8 个路径组/11 个文件，
   `pyproject.toml` 与 `uv.lock` 相对 base 字节不变。
3. handoff Verdict=`REJECT`，P0=0、P1=3、P2=2、P3=0；规定离线命令 50/30/53、
   全量 219、两项 mypy、Ruff、CLI、offline build、包内容和 Diff 均 PASS。拒绝来自
   R1/R4/R5 独立反例，不是范围、依赖、许可证、行数或测试数量自动触发。
4. 三个 P1 精确为：
   - Adapter/Service 与 canonical decode 的异常图仍持有正文、临时 URL 或绝对路径；
   - 非 all-invalid 终态错误码漂移、reservation 后文件失败遗留 lease、真实并发
     重复目录枚举；
   - raw metadata token/current language、canonical model 与 symlink cache 分类验证
     不完整。
5. R2 VTT 语义与 R3 HTTP/目录 fail-closed 已独立 PASS；Correction 2 不得回退或
   无关重写这些已关闭路径。
6. 控制面统一把 TASK-005 退回 `IN_PROGRESS`；第二次 Reviewer 已结束，原 Codex
   Implementer 等待 Correction 2。不得写为 BLOCKED、IN_REVIEW、ACCEPTED 或 DONE。
7. Correction 2 从 `5bb750e8...` 开始，不 amend/rebase；只允许
   `transcripts.py`、`providers/subtitles.py`、policy/integration tests、
   subtitle fixtures 和 handoff。
8. Correction 包要求在任何远端目录枚举前取得稳定 raw request reservation，完整
   终态重放/失败释放，所有异常图真正脱敏，以及 raw/canonical provenance 与当前
   request 严格绑定；不得修改 `state.py`、domain、Schema、migration、
   `complete_stage`、依赖/锁或 main。
9. 两个 P2 继续明确登记：职责/私有 hook 聚合与嵌套 metadata 资源放大。本轮不得
   扩成新公共模块、依赖或未冻结产品阈值；若其形成正确性/安全缺陷才按 P1 处理。
10. ADR-007 仍为 `Proposed`；TASK-006/TASK-007 仍为
   `BLOCKED/UNASSIGNED`，TASK-005A 不存在。
11. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
    真实 Vault/密钥继续未授权。
12. 本轮不运行产品命令，不修改 source，不启动 Worker，不生成第三次 Reviewer 包，
    不预写修复成功或审查结论。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

确认 5 文件范围、状态、SHA、Finding、禁令、空白、EOF 与文件 hash。全部通过后精确
暂存 5 文件，并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: return TASK-005 for second correction
```

提交后确认：

- 新提交唯一父提交为 `a3954bf782430678fa5e0040084bf0d907a52d05`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `5bb750e8...`；
- 新提交可由
  `git log -1 -- agent-prompts/TASK-005-CORRECTION-2-CODEX.md`
  动态解析为 correction authorization；
- TASK-005=`IN_PROGRESS`，第二次 Reviewer=`REJECT`，Correction 2 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 second review reject / Correction 2 sync
Role: Status Integrator
Base: main@a3954bf782430678fa5e0040084bf0d907a52d05
Head commit:
Git identity:
Committed files:
Checks:
Review evidence/findings:
TASK-005 source/status/roles:
Correction authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
