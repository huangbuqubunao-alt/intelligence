# TASK-014 Phase B-1 — directory-only Observability Read-only Scout

你是 TASK-014 B-1 directory-only observability 的只读 Scout。只定位可观测性缺口并回传结论；不得修复、写入、运行产品或触达真实资源。本包本身不启动 Scout。

## 固定对象

```text
Task: TASK-014 Phase B-1 — directory-only observability
Role: Read-only Scout
Control-plane base: main@280cf150ae699b21d2ad4b1c6a37103c3ca78cde
Evidence source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-directory-only-execution
Evidence source branch: codex/task-014-phase-b1-directory-only-execution
Evidence source HEAD: 1f5a1109fc306af9f3743da64c7268ca3b8111e0
Required sole parent: 9bffb29d84868c94fc8544395183c5472856e7c8
Evidence range: 9bffb29d84868c94fc8544395183c5472856e7c8...1f5a1109fc306af9f3743da64c7268ca3b8111e0
```

- 开始前只读确认 source 分支、HEAD、唯一父提交和洁净度；evidence range 必须严格且仅为：

  1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-DIRECTORY-ONLY-PUBLIC-YOUTUBE.md`
  2. `docs/RELEASE_CHECKLIST.md`
  3. `handoffs/TASK-014.md`

- 任一不符立即停止并报告。不得修改、暂存、提交、rebase、cherry-pick、清理 source 或创建任何工件。

## 唯一允许的只读范围

1. 对照 B3/B4 已整合的 static implementation、相关离线测试与 ADR-015/B4 约束，定位 directory-only 的
   `directory_diagnostic`、每目标 metadata/enumerate/read 计数、JSONL `safe_message` 和 CLI stdout/stderr 的产生与
   传递路径。
2. 只读检查 B-1 directory-only evidence 如何记录退出码、固定脱敏诊断 code 与逐目标 1/1/0 计数。
3. 解释本次 exit=1 为什么没有可安全审计的固定 directory diagnostic code 或逐目标 1/1/0 计数。每个结论必须明确归类为：
   - **信息实际存在但 evidence 未提取**；或
   - **产品根本未产生可审计的安全信息**；或
   - **证据不足，无法安全判断**。

不得推断或补写真实响应字段，或把未记录的 ID 级结果表述为事实。

## 方法、建议与验收输出

- 优先使用现有 codebase-memory 的只读查询（如 symbol/path search、call trace、snippet）；若不可用，仅用 Git/文本静态定位。
  不得索引仓库、创建 `.codebase-memory` 工件或执行代码。
- 输出最小后续任务建议：只选一条能够关闭已确认缺口的路径，列出精确可能修改范围。默认候选上限为：

  1. `src/youtube_intel/public_subtitle_smoke.py`
  2. `src/youtube_intel/cli.py`（仅在静态路径证明 CLI 输出/汇总是必要时）
  3. `tests/integration/test_public_subtitle_smoke.py`
  4. `tests/integration/test_operations.py`（仅在 CLI 输出/拒绝覆盖必要时）
  5. `handoffs/TASK-014.md`

  不得建议依赖、锁文件、Schema/migration、Adapter 安全边界、默认 CLI、JSONL schema、真实资源或通用下载能力变更。
- 给出离线验收条件：Fake 成功/目录失败均验证每目标 1/1/0；exit=1 的安全输出仅包含固定
  `directory_diagnostic` code 与计数；无 URL、正文、标题、字段值、Cookie、token、payload、异常原文或用户数据；
  既有默认 smoke 的一份正文读取保持不变；范围、mypy、Ruff、聚焦离线测试与 `git diff --check` 通过。
- 聊天回传简明证据位置、上述分类、建议范围与未决风险；不得写入文件或创建 commit。

## 绝对禁止

禁止联网、调用 YouTube、真实 smoke、uv、测试、构建、任何 CLI/`python`/import、数据库、媒体/ffmpeg、认证、Cookie、
凭据、真实 Vault、模型、Ollama、OpenAI、付费调用、推送、合并、source 清理、`.codebase-memory` 工件或任何 source 写入。
TASK-014 始终为 `IN_PROGRESS / No-Go`；Scout 结论不构成真实服务验证、发行批准或最终 Go。
