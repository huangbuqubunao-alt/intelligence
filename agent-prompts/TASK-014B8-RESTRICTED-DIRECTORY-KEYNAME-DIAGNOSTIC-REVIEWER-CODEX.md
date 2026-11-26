# TASK-014B8 — 受限键名级字幕目录诊断独立 Reviewer

你是 TASK-014B8 的全新独立 Codex Reviewer。只审查固定 source 的离线实现与审查 evidence；不得修复、重构、重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B8 — restricted directory keyname diagnostic
Role: Independent Reviewer
Control-plane baseline: main@a8ea95775f452203958ec2abb56b8eeb317917f3
Execution main: dynamic clean main at the single-parent Reviewer authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic
Reviewed source branch: codex/task-014b8-restricted-directory-keyname-diagnostic
Reviewed source HEAD: 2334374f66497546108d12be541ab137b4a8981a
Required sole parent of implementation: 43f2c748c43215facb231f76a0c93ac45d350657
Review range: 43f2c748c43215facb231f76a0c93ac45d350657...2334374f66497546108d12be541ab137b4a8981a
Read-only failed B-1 B7 evidence: 8f5dfce33ac77a45800f4ff53ff6e7054d8f68b0 (must not merge, rewrite, rerun, or call passing)
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017/ADR-018 diagnostics, ADR-019, and offline integration tests; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、唯一父链、完整五路径范围和双方洁净度；任一不符立即停止并报告。
- 完整产品 Diff 必须严格且仅为：`src/youtube_intel/providers/subtitles.py`、`src/youtube_intel/public_subtitle_smoke.py`、`tests/integration/test_subtitle_provider.py`、`tests/integration/test_public_subtitle_smoke.py`、`handoffs/TASK-014.md`。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，且只能追加审查 evidence；evidence 必须以 `2334374…` 为唯一父提交。不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。

## 必须审查与负向验证

- 验证 `directory_key_names` 仅在 directory-only、目录 `INVALID_RESPONSE`、`directory_origin_mapping`、`directory_fingerprint_unknown`、enumerate=`1`、read=`0` 同时成立时出现；default、目录成功、其他目录失败、正文失败和任一条件缺失时必须省略。
- 验证仅检查直接映射键名，最多 16、稳定 ASCII 字典序、去重且完整匹配 ADR-019 `[A-Za-z][A-Za-z0-9_]{0,63}`。不合格、超限、疑似 URL/凭据/路径/控制字符或不可靠候选集必须 fail-closed 省略整个字段，不得截断、替换、哈希或记录拒绝项。
- 验证 B6 `directory_diagnostic`、B7 origin/fingerprint 保持原语义和固定值；default/directory-only 读取计数、退出码、CLI、临时根、ID 上限、无重试、零业务记录、解析接受面与所有 fail-closed 边界不退化。
- 独立验证 stdout、stderr、JSONL、测试和 handoff：除 ADR-019 明确授权的合成安全键名外，不得含字段名/字段值、URL、字幕正文、标题、语言、轨道、路径、原始异常、Cookie、token、payload 或用户数据。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B8 聚焦 pytest、mypy Provider/smoke、Ruff B8 tests、`.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI 子命令、Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、登录、认证、Cookie、API key、真实 Vault、用户数据、模型、OpenAI、付费调用、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014B8 保持 `IN_REVIEW`，TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查不构成真实服务验证、发行批准或最终 Go。
