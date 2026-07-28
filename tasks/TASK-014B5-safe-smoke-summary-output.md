# TASK-014B5：安全 smoke 摘要输出

- Status: `ACCEPTED`
- Assignee: `Codex Product Integrator（已授权，尚未启动）`
- Reviewer: `独立 Codex Reviewer（APPROVE；P0--P3=0）`
- 依赖：TASK-014B0 `DONE`、TASK-014B3 `DONE`、TASK-014B4 `DONE`
- 实施基线：`main@b1ea7a66aaf513aa0fa8262780f9c59072cc18b4`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b5-safe-smoke-summary`
- Branch：`codex/task-014b5-safe-smoke-summary`
- 已接受 source / Reviewer evidence：`72322e213c0aae604b53ec4addae98031885ed0f`（唯一父
  `ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1`；后者唯一父为
  `b1ea7a66aaf513aa0fa8262780f9c59072cc18b4`）
- Reuse decision：`DIRECT` — 既有受限 CLI、`PublicSubtitleSmoke`、固定安全错误码、ADR-015
  `directory_diagnostic`、JsonlLogger 和离线 Fake/integration 基础设施；不新增依赖或复制第三方代码。

## 目标

为仅受限的 `smoke-public-subtitles` 增加每个目标一条安全摘要输出，使一次 directory-only 真实 smoke 即使以非零
退出码结束，也能在不记录敏感内容的前提下审计每个已处理目标的调用计数与最终安全诊断。

## 冻结摘要契约

- 只在 `smoke-public-subtitles` 路径输出每个目标的摘要；非 smoke 子命令、默认 CLI 结构和退出码语义不得改变。
- 每条摘要字段严格且仅可为：公开目标稳定标识、`metadata`/`enumerate`/`read` 的非负整数计数、最终固定安全错误码，及
  目录 `INVALID_RESPONSE` 时的固定 `directory_diagnostic`。不得增加 JSONL schema 或修改 `logging.py`。
- 输出必须使用固定字段名和稳定顺序；成功的错误码显式为固定安全成功值，不得以自由文本代替。目录 diagnostic 只在
  `INVALID_RESPONSE` 时出现。
- 严禁 URL、字幕正文、标题、语言、字段值、原始异常、路径、Cookie、token、payload、用户数据、凭据形状或其他
  派生内容；不得将完整 CLI 参数、临时根或响应打印到 stdout/stderr/JSONL。
- directory-only 成功或目录失败均必须能审计为每目标 `metadata=1 / enumerate=1 / read=0`。默认 smoke 保持既有一份正文
  读取；既有非 smoke 标志拒绝、全局配置参数早拒绝、1--3 唯一 ID、临时根、timeout、无重试和所有 fail-closed 边界不得改变。

## 唯一允许实现范围

1. `src/youtube_intel/public_subtitle_smoke.py`
2. `src/youtube_intel/cli.py`
3. `tests/integration/test_public_subtitle_smoke.py`
4. `tests/integration/test_operations.py`
5. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、domain/config、Provider Adapter、默认 CLI 结构、发布状态、
 README、B-1 evidence 或任何其他路径。

## 验收与整合控制面

- Reviewer evidence `72322e…` 仅追加 `handoffs/TASK-014.md`，Verdict=`APPROVE`，P0--P3 均为 `0`。
  完整产品 Diff `b1ea7a66…...ce4b472…` 严格为
  `src/youtube_intel/public_subtitle_smoke.py`、`tests/integration/test_public_subtitle_smoke.py` 与
  `handoffs/TASK-014.md`，属于上述五条允许路径。
- 后续唯一授权的 Product Integrator 只能在干净 main 对 accepted source 执行
  `git merge --no-ff 72322e213c0aae604b53ec4addae98031885ed0f`；不得修复、修改 source、重写历史或执行任何其他
  产品命令。整合后才可运行授权的离线 Fake 测试、mypy、Ruff、CLI help、离线 build、范围与 stdout/stderr/JSONL
  泄漏扫描。
- 不得预写 `DONE`、真实 smoke 成功、真实服务验证或发行批准。TASK-014 始终为 `IN_PROGRESS / No-Go`。

## 验收与离线检查

- 离线 Fake 覆盖 directory-only 成功与目录 `INVALID_RESPONSE` 的每目标 1/1/0 安全摘要，且仅含允许字段和固定 code；
  覆盖默认 smoke 的既有单正文读取及安全摘要，不能改变其退出码。
- 覆盖非 smoke `--directory-only` 拒绝、smoke 全局配置参数在 runner/Adapter/temporary-root 前拒绝、超限/重复 ID 和
  无敏感 stdout/stderr/JSONL 回归。
- Implementer 只可先运行一次 `uv sync --locked --offline`；缓存缺失、任何下载/网络迹象或失败立即停止，禁止其他 `uv` 命令、
  安装、锁文件变更或替代环境。
- 仅在已有离线 `.venv` 可用时，允许运行：

```text
.venv/bin/pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py
.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py tests/integration/test_public_subtitle_smoke.py tests/integration/test_operations.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、launchd、push、合并、source 清理和任何额外产品命令。
- 完成时仅提交上述五条允许路径的一个 Implementer commit，更新 handoff 并报告 SHA；不得自行 `ACCEPTED`、`DONE`、
  合并、push 或启动 Reviewer。TASK-014 始终为 `IN_PROGRESS / No-Go`；B5 离线完成不构成真实服务验证或发行批准。
