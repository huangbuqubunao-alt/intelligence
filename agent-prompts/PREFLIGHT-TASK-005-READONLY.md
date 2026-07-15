# TASK-005 字幕链路只读预检包

你是全新独立的 Read-only Scout。你的任务是为主控冻结 TASK-005 的字幕选择、下载、规范化、产物与错误契约提供证据。你不是 Implementer，不得修改仓库、安装依赖或运行真实网络。

## 启动条件与观察基线

- Repository: `/Users/hua/Documents/youtubek agent`
- Branch: `main`
- 本包只有在提交它的 Status Integrator 返回 `INTEGRATED` 后才能执行。
- 用以下只读命令取得添加本包的确定控制面 commit：

```bash
control_sync_head="$(git log -1 --format=%H -- agent-prompts/PREFLIGHT-TASK-005-READONLY.md)"
test -n "$control_sync_head"
printf '%s\n' "$control_sync_head"
```

开始时 main HEAD 必须等于 `control_sync_head`，工作树和暂存区必须干净，Git 身份必须为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。若不一致，停止并报告 `BLOCKED`。

TASK-004 correction 5 可能在另一 worktree 并行写入。你不得读取、检查、等待、清理或以任何方式访问 `/Users/hua/Documents/yia-worktrees/task-004` 的 live filesystem。需要参考 TASK-004 时，只能读取固定 Git 对象 `1883367d313623c42d9d3624b16307ca8d502709`，例如 `git show 1883367d313623c42d9d3624b16307ca8d502709:src/youtube_intel/discovery.py`；该对象不会随并行写入变化。

## 严格只读边界

禁止：

- 创建、编辑、删除、暂存或提交任何文件；
- 创建/切换分支、worktree、stash、tag 或 merge；
- 运行会写 `.venv`、lock、cache、数据库、构建产物或配置的命令；
- `uv add`、`uv sync`、依赖/模型/二进制下载；
- 真实 YouTube/RSS/字幕请求、Cookie、账号登录、remote components、ffmpeg、媒体或字幕下载；
- 读取 `.env`、真实密钥、真实 Vault 或其他任务 live worktree。

允许使用 `git show`、`git diff`、`git ls-tree`、`rg`、`sed`、`python --version` 等不写入命令。不要运行 pytest、mypy、Ruff 或 CLI；本轮目标是契约/审批盘点，不是验证产品实现。

## 必读材料

按 `AGENTS.md` 顺序阅读，并重点检查：

- `docs/PRD.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/REUSE_REGISTER.md`
- `docs/decisions/ADR-002-config-domain-contracts.md`
- `docs/decisions/ADR-003-sqlite-state-store-contract.md`
- `docs/decisions/ADR-004-discovery-ytdlp-contract.md`
- `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
- `tasks/TASK-005-subtitle-pipeline.md`
- main 的 `src/youtube_intel/config.py`、`domain.py`、`state.py`、`pyproject.toml`、`uv.lock`
- 固定 TASK-004 evidence 中的 `src/youtube_intel/providers/youtube.py`、`src/youtube_intel/discovery.py`、`pyproject.toml`、`uv.lock`、`handoffs/TASK-004.md`

若文档相互冲突，不要自行选择；逐项报告 `DECISION NEEDED`。

## 必须回答的契约矩阵

### 1. 输入、输出与领域对象

盘点现有 `TranscriptArtifact`、`NotAvailable`、`ArtifactKind`、`VerifiedArtifact` 和相关 Provider Protocol 是否足以表达：

- 人工字幕、自动字幕、无有效字幕需本地转写；
- 选中语言、实际语言、来源类型、格式、内容哈希、字符/segment 计数；
- 原始字幕产物与规范文本产物的关系；
- 失败与 `transcription_required` 是返回值、领域错误还是具名判别联合。

不得建议公共自由 `dict`。列出缺失字段、类型、基数、默认值和必须由主控冻结的命名。

### 2. 轨道发现与选择策略

给出确定性选择矩阵，至少覆盖：

- 人工 > 自动；配置语言偏好顺序；精确语言、基础语言和地区变体的匹配次序；
- 同语言多格式/多轨道时的稳定 tie-break；
- TASK-004 `available_languages` 只能作能力摘要，TASK-005 必须重新查询轨道明细；
- 空列表、URL 过期、轨道 404/403/429/5xx、损坏内容及多次运行。

指出 PRD/设计中尚未冻结的规则，并提出编号为 `T-01...` 的推荐方案。

### 3. Provider、安全和复用

优先评估直接复用已锁定的 `yt-dlp[default,deno]==2026.7.4` Python API，是否无需新增生产依赖即可完成字幕轨道枚举与下载。必须保持 Adapter 隔离，并检查：

- 不使用 shell、Cookie/浏览器登录、账号、`.netrc`、remote components 或 ffmpeg；
- 只下载选中的字幕正文，不下载音频/视频/缩略图；
- 有限响应大小、timeout、重试归属、临时文件和响应关闭；
- 原始 URL、响应正文、字幕全文、本机绝对路径不进入日志/异常/SQLite。

对 `video-to-subtitle-summary-skill`、`yt2md` 等登记候选只作 `ADAPT/REFERENCE` 复核；不要联网、克隆或复制代码。给出 `DIRECT/ADAPT/REFERENCE/REJECT/DEFER`、来源、已知许可证和拒绝理由。特别说明 TASK-004 的依赖安装授权是否能覆盖 TASK-005 的**使用**，以及哪些网络/真实内容动作仍需新的任务级授权。

### 4. 规范化与质量规则

提出可测试、确定性的最小规则，至少覆盖：

- VTT/SRT/JSON3 等允许格式与优先级；时间戳、样式、HTML entity、重复滚动字幕、空白和 Unicode 规范化；
- 保留/丢弃说话人、音乐/音效标记和换行的规则；
- 空文本、乱码、最小有效长度、重复率、异常压缩比或超大正文的边界；
- 规范文本哈希和同输入幂等键所含维度；
- 规则版本变化时旧缓存是否失效。

不得凭直觉给出模糊“合理阈值”；每个数值必须标为“已有批准”或 `DECISION NEEDED + 推荐值`。

### 5. 文件、SQLite 与事务边界

对照 ADR-002 路径边界和 ADR-003 Artifact Repository，明确：

- 原始字幕和规范文本分别使用哪个已批准 `ArtifactKind`、`StorageRoot`、relative path 与 retention class；
- 写临时文件、fsync/原子替换、计算 SHA-256、`VerifiedArtifact` 和 SQLite upsert 的顺序；
- 文件写成功但 DB 失败、DB 预留后进程崩溃、重复运行和内容变更的恢复策略；
- SQLite 不保存字幕正文；日志只保留 ID、语言、来源、相对路径/哈希和计数；
- 是否需要新的 Schema/Artifact kind。若需要，必须标记红线 `DECISION NEEDED`，不得在 TASK-005 自行修改。

### 6. 错误、重试与预算

把轨道不存在、内容不可用、权限、限流、临时网络、Provider 不可用、非法响应、路径/磁盘/权限和配置错误映射到 ADR-002 已批准的 8 个 `ErrorCode`，说明 retryable、Retry-After、最大次数和最终 `transcription_required`/失败行为。不得新增 ErrorCode。

### 7. 文件范围、门禁与授权清单

给出最小实现文件范围，并纠正任务卡当前裸 `python`/`mypy`/`ruff` 命令为统一 `uv run` 形式。提出离线 unit/integration/全量/mypy/Ruff/CLI/build/Diff 检查，明确哪些测试使用固定夹具和临时目录。

列出：

- 已由现有决策覆盖的事项；
- 仍需产品负责人任务级批准的依赖、网络、真实字幕、系统工具、Schema/公共契约或许可证事项；
- correction 5 完成并 TASK-004 `DONE` 后才能满足的依赖门禁。

## 输出格式

只在终端返回报告，不写文件：

```text
Preflight: TASK-005
Role: Read-only Scout
Observed main commit:
Fixed TASK-004 evidence inspected:
Repository changes: None
Spec consistency: PASS | DECISION NEEDED
Domain/output matrix:
Track selection matrix:
Normalization/quality matrix:
Artifact/transaction matrix:
Error/retry matrix:
Reuse/license matrix:
Suggested minimal file scope:
Required offline checks:
Already approved:
Task-level approvals still needed:
Risks/blockers:
Recommended decisions T-01...:
Recommended next action:
Postflight git status:
```

最后再次确认 main HEAD 未变化、`git status --short` 无输出；报告中必须写 `Repository changes: None`。TASK-005 状态保持 `BLOCKED`。
