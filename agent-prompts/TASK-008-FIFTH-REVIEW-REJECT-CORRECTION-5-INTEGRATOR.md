# TASK-008 第五轮审查拒绝与 Correction 5 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@8b2bdc57076769b6d0efe246430ebfda37aa0b6b`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@78ae101786ada5f04d2b7c734c84a216f8820803`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-5 evidence：`78ae101786ada5f04d2b7c734c84a216f8820803` 唯一父为 Correction 4 `bb195a59ddee25cb804b0078676c504e94c44441`；evidence 只改 `handoffs/TASK-008.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0、P1=1。Reviewer 在首个 P1 停止；其余门禁和探针未运行，不得写为通过。
- P1：`providers/cloud_llm.py` 的隔离 SDK 子进程用无期限 `readline()` 读取握手和响应，仅在读取之后调用 `wait(timeout=120)`。若 child 卡住，Job 会无限阻塞，违反 ADR-008 A-17 的 timeout/退出收口。
- 修复必须让 handshake、请求写入/flush、响应读取及退出共享有限 deadline；任何 timeout、EOF、格式错误或异常都必须关闭管道、终止并 reap child，映射到既有安全错误，不泄露子进程或响应正文。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-FIFTH-REVIEW-REJECT-CORRECTION-5-INTEGRATOR.md`
2. `agent-prompts/TASK-008-CORRECTION-5-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 5；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: return TASK-008 for subprocess timeout correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 5 边界

- 只授权 source `src/youtube_intel/providers/cloud_llm.py`、`tests/integration/test_summary_provider.py` 和 `handoffs/TASK-008.md`。
- 不得修改隔离策略、SDK 版本、子进程环境白名单、匿名管道边界、Provider 公共契约、请求 payload、缓存/预算逻辑或真实资源权限。仅补有限时读写/退出收口。
- 用离线 Fake child/Popen seam 验证：永不 handshake、handshake 后永不响应、EOF、畸形 JSON、非零退出和正常响应；每个非成功分支都在有限 deadline 内终止并 reap child，映射为现有安全 `AppError`，不泄露 body/path/credential。不得以线程遗留、孤儿 child 或扩大全局 timeout 代替收口。
- 保留现有 Structured Outputs、错误脱敏、缓存完整性、A-03 零调用门禁与原子恢复回归；不得新增依赖/锁、配置/共享契约、`analysis.py`、`state.py`、Schema/migration、CLI 或真实 OpenAI/密钥/付费/API/网络/云端 token-count/用户内容/媒体/YouTube/Vault/测试目录外 I/O。

## 回传格式

```text
Task: TASK-008 fifth review reject / Correction 5 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-008=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
