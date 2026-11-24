# TASK-014B3 — 公开字幕目录诊断 Reviewer

你是全新独立的 Codex Reviewer。你只审查已经提交的 TASK-014B3 source；本包不授权实现、修复、真实验证、整合或发布。

## 固定审查对象

```text
Task: TASK-014B3 — public subtitle directory diagnostics
Role: Independent Reviewer
Control-plane baseline: main@952014f7a09414cf506958d5e9845ba7f078763b
Source worktree: /Users/developer/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics-implementation
Source branch: codex/task-014b3-public-subtitle-diagnostics-implementation
Review HEAD: 77f2690c28ab80eb9886e8ca8eadb0e47481cd51
Required sole parent: 9c5f08ec829629591b095bd68841ca3ce0b22532
```

开始前确认 source 分支、HEAD、唯一父提交和工作树干净。任一不符即停止并报告；不得修复、切换、清理、rebase 或重写 source。

## 唯一可写范围

只有在审查完成后，才可**追加** `handoffs/TASK-014B3.md` 的 Reviewer 证据和 `APPROVE` / `REJECT` 结论。不得修改、格式化或创建任何其他 source 文件；不得改任务状态、代码、测试、fixture、配置、依赖、锁文件、Schema、CLI、B-1 evidence 或控制面文档。

## 独立审查要求

审查 `9c5f08ec...77f2690c...`，并独立确认：

1. ADR-015 的九类固定、脱敏目录分类及其固定 unknown 回退集合稳定；不接受动态 code、异常文本或响应片段。
2. 仅在目录枚举为 `INVALID_RESPONSE` 且正文读取为零时，才将既有 JSONL `safe_message` 追加 `directory_diagnostic=<fixed-code>`；不新增结构化 JSONL 字段。
3. 该出口不泄漏 URL、正文、标题、字段值、Cookie、token、payload、原始异常或用户数据。
4. 危险 URL、缺字段、超限和不支持格式仍 fail-closed；调用顺序、最多一次正文读取、退出码、临时根、正文不持久化与无自动重试边界不变。
5. 离线 fixture/Fake 覆盖每个固定分类和 unknown，以及目录失败时 `metadata=1 / enumerate=1 / read=0` 的审计语义。
6. Diff 仅限 TASK-014B3 已授权的六条实现路径；无依赖/锁文件、Schema/migration、默认 CLI、安全边界或真实资源改动。

## 允许验证与禁止项

- 仅在预先存在的离线环境可用时，可运行 `uv run --offline python -m pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py`，以及 `git diff --check 9c5f08ec...77f2690c...`。
- 环境不可用或任一命令失败时，立即停止并在 handoff 记录；禁止 `uv sync`、安装、下载、网络重试或修改依赖/锁文件。
- 禁止真实 YouTube/网络、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、合并、push 或启动后续角色。
- 离线通过不等于 B-1 成功、真实兼容性、发布批准或 TASK-014 Go。TASK-014 继续 `IN_PROGRESS / No-Go`。

## 审查回传

在 `handoffs/TASK-014B3.md` 追加固定 base/HEAD/父提交、审查范围、实际离线命令与结果、P0–P3、泄漏/安全边界核验、`APPROVE` 或 `REJECT`。完成后只报告 evidence commit SHA；不得自行设为 `ACCEPTED`、`DONE` 或整合。
