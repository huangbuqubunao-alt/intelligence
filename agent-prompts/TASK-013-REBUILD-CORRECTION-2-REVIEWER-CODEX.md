# TASK-013 rebuild — Correction 2 独立 Codex Reviewer

你是全新、独立的 Codex Reviewer。只能审查固定 source，并且只允许向 source 的 `handoffs/TASK-013.md` 追加审查证据。不得修改业务代码、测试、夹具、验收报告、任务卡、main 或其他 source 文件；不得合并、推送、rebase、reset、清理 worktree 或启动其他 Agent。

## 动态授权与唯一谱系

- 先解析 main 授权：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-CORRECTION-2-REVIEWER-CODEX.md` 必须等于本 Reviewer 授权提交，且 main 的 TASK-013=`IN_REVIEW`。
- 唯一 source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild`，分支 `codex/task-013-e2e-acceptance-rebuild`，待审 HEAD 精确为 `f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28`，唯一父提交精确为 `4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`。
- 审查证据提交只能以 `f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28` 为唯一父提交，且只追加 `handoffs/TASK-013.md`。开始与结束均检查 source 清洁（交接报告写入前后除外）。
- 禁止访问、修改、清理或复用历史 `/Users/hua/Documents/yia-worktrees/task-013` worktree/branch。

## 冻结范围与资源边界

相对 rebuild 基线 `2a59dfe3860161a5989f2c08161f03c73aa4ca86`，实现产品改动仅可在：

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

检查范围、锁文件、秘密扫描和复用/许可证说明。Reuse decision 为 `DIRECT`：既有项目服务、锁定依赖与 Python 标准库，外部边界仅使用 Fake Adapter；不复制第三方代码或新增依赖。真实 YouTube、Whisper/ffmpeg、Ollama/模型、OpenAI/云 API、网络、媒体、凭据、真实 Vault/用户笔记、付费服务均不授权。

## 必须独立证明的恢复语义

1. 注入评分失败后，第一次组合的 Flow、服务、Repository、Fake Provider 与内存状态被彻底销毁；在**同一临时 SQLite/DATA/Vault**上重建一个全新的完整组合。
2. 新组合不得读取、引用或依赖旧 `_OfflineMvpFlow` 的 `transcripts`、`scores`、`analyses`，以及任何旧 Repository、Fake Provider、计数器或其他进程内缓存；恢复依据只能是持久 SQLite 与 Artifact，以及由新组合读到的 Provider-call、Job/Pipeline、用户可见文件。
3. 评分失败恢复路径中，新组合的字幕和 Whisper 昂贵调用必须均为 `0`；评分与必要分析必须各恰好一次；随后笔记和周报均完成。
4. 验证稳定重跑不重复生成 Artifact、Provider-call、笔记或周报；检查其他适用失败边界也以新组合恢复或明确终态，不能只保留同进程 retry。
5. 不得以通用 handler、直接 `complete_stage`、直接 SQL 更新、直接推进 SQLite 状态或伪造最终 Job/Pipeline 代替真实服务路径。

## 审查与交付

独立执行授权的离线质量门禁和针对失败恢复的探针；先检查类型/语法错误。发现 P0/P1 时停止通过性结论，写明命令、关键错误、受影响文件和已验证事实。不得运行真实资源命令。

向 `handoffs/TASK-013.md` 追加：谱系与范围核验、每项命令及结果、评分失败后销毁/新组合/持久恢复证据、调用计数、笔记/周报和稳定重跑结果、PRD 10.1–10.8、秘密扫描、复用/许可证、未授权路径和风险，以及唯一明确 Verdict=`APPROVE` 或 `REJECT`（含 P0–P3）。提交前检查仅该 handoff 改动、父提交精确、`git diff --check` 和工作区状态；提交后报告 evidence SHA，绝不修改 main 状态。
