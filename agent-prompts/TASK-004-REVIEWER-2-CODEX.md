# TASK-004 Second Independent Codex Reviewer Packet

你是与 TASK-004 Grok Implementer、首个 TASK-004 Codex Reviewer 都独立的**全新 Codex Reviewer 会话**。你的职责是审查 correction 3 是否真正修复首轮 `REJECT` 的 4 个 P1、2 个 P2 与 1 个 P3。不得修改业务代码、测试、依赖、锁文件、任务状态或 main；只有在全部审查结束后，才可写入并提交 `handoffs/TASK-004.md` 的 Reviewer 部分。发现任一 P0/P1/P2 时不得自行修复，输出 `REJECT` 并退回原 Grok Implementer。

## 固定上下文

- Task: `TASK-004`
- Role: `Reviewer`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Reviewed source head: `30932e1742e948683f9e1c0f63236451b8d731bd`
- Previous rejected review evidence: `f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- Main authorization commit: 主控将在 Status Integrator 成功提交后随启动指令提供；不要在自己的提交中自引用它
- Implementer 已停止写入；开始审查时 source worktree 必须干净
- TASK-003 已 `ACCEPTED`，不得读取、写入、检查、清理或等待其 worktree

控制面文档必须从 main `/Users/hua/Documents/youtubek agent` 读取；TASK-004 source worktree 只用于代码、测试和本任务 handoff。完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md`
5. `docs/SYSTEM_DESIGN.md` 第 3、5、5.2、12 节
6. `docs/REUSE_REGISTER.md`
7. `docs/decisions/ADR-002-config-domain-contracts.md` C-05
8. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-01 至 D-08
9. `tasks/TASK-004-discovery-metadata.md`
10. `handoffs/TASK-004.md`（特别是 `f34cbb...` 的 REJECT 结论与 correction 3 记录）
11. `agent-prompts/TASK-004-IMPLEMENTER-GROK.md`
12. `agent-prompts/TASK-004-CORRECTION-GROK.md`
13. `agent-prompts/TASK-004-CORRECTION-2-GROK.md`
14. `agent-prompts/TASK-004-CORRECTION-3-GROK.md`
15. 本包

## 开始前门禁

在 TASK-004 worktree 中确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git log --oneline --decorate -6
git diff --name-status dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...30932e1742e948683f9e1c0f63236451b8d731bd
git diff --name-status f34cbb09d628ebb256bf5f2895adfd10dbd61812...30932e1742e948683f9e1c0f63236451b8d731bd
```

必须处于 `grok/task-004-discovery-metadata`，HEAD 精确为 `30932e1...`，worktree 干净，身份为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。确认链 `392edfb... -> 10f5ffa... -> 9db800f... -> f34cbb... -> 30932e1...` 连续可达；correction 3 相对 `f34cbb...` 精确只改 5 个文件。任何条件不符即停止，不写 handoff。

## 范围、复用和红线

1. 全量 Diff `dcc7d85...30932e1...` 只能属于原批准范围：
   - `src/youtube_intel/discovery.py`
   - `src/youtube_intel/providers/youtube.py`
   - `tests/unit/test_discovery.py`
   - `tests/integration/test_discovery_adapter.py`
   - `tests/fixtures/youtube/**`
   - `pyproject.toml`
   - `uv.lock`
   - `handoffs/TASK-004.md`
2. correction 3 本身只允许 `discovery.py`、`providers/youtube.py`、两份 discovery 测试和 handoff。不得把修复扩展为重构、依赖修改或公共领域契约改变。
3. 复用决定仍是 `DIRECT`：批准范围内的 `yt-dlp[default,deno]` Python API；RSS 仅标准库；第三方项目只作 `REFERENCE`。重新核对没有额外直接运行依赖或已存在直接依赖升级。
4. 不得有真实 YouTube、Cookie/浏览器 Cookie、账号、remote components、ffmpeg、媒体/字幕下载、Vault、密钥、真实响应或缓存；`DiscoveryRepository` 必须仍是窄 Protocol，且不得改 `domain.py`、`state.py`、CLI 或 TASK-003 接口。

## 独立复跑

必须重新运行，不能仅相信 Implementer 输出：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
git diff --check dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...30932e1742e948683f9e1c0f63236451b8d731bd
```

## 必做独立、非写入探针

设计并运行至少 4 项探针；记录命令、预期、实际与相关代码/测试证据。探针不得写 main、不得写 source 或下载真实内容。

1. **畸形 payload 与身份边界：** 使用离线 fake 构造字段/日期/类型不合法的 yt-dlp info，以及返回 ID 与请求 ID 不相同的 info。两类都必须成为安全 `AdapterError(AppError)`，代码为 `INVALID_RESPONSE`、不可重试、阶段为 `METADATA`、诊断仅保留请求 video ID；不得逸出 `ValueError`/`TypeError`，不得泄漏 payload、路径、Cookie 或原始异常；错误输入不得到达 Repository。
2. **RSS 完整性、游标与资源关闭：** 对缺失/无效 `yt:videoId`、`published`、标题或必要频道字段的可解析 entry，必须使整批以安全 `INVALID_RESPONSE` 失败，既不保存 candidate 也不推进 cursor；随后修复同一较旧 entry 后必须仍可发现。分别在 read timeout/OSError/类型错误或 XML 失败中验证 response 最终会关闭。
3. **HTTP 与 availability 分类：** 用离线错误对象分别验证 404→`CONTENT_UNAVAILABLE`、403→`PERMISSION_DENIED`、429→`RATE_LIMITED`、503/5xx→`PROVIDER_UNAVAILABLE`，并在宽泛文本匹配之前处理；前两项不可重试、后两项可重试。验证 `needs_auth` 始终映射 `RESTRICTED`，并确认消息没有 response body。
4. **公开 Surface 与安全 yt-dlp options：** 不只检查 `__all__`。确认 Provider 构造面仅 `timeout_seconds`，没有非私有 raw `map_*`/`build_*`/`SAFE_*` 入口、factory/callback/sink/raw payload 参数，以及自由 `dict`、`Mapping[str, Any]`、`Any` 或宽 `object` 的公开注解。用离线 fake 捕获 `YoutubeDL` 参数与 `extract_info(..., download=False)`；确认 `skip_download`、`noplaylist`、`ignoreconfig`、无 Cookie/登录/remote components/ffmpeg/媒体或字幕写入，且 raw info 不跨 Adapter 边界。

逐项判定 TASK-004 AC-1 至 AC-5、ADR-004 D-01 至 D-08，特别审查错误映射/正文脱敏、游标原子性、元数据独立失败和候选保存边界。真实 YouTube 冒烟、Cookie/登录、remote components、ffmpeg、媒体/字幕下载仍**不得**运行，必须作为明确跳过项记录。

## 交接与提交

仅当全部审查、探针和检查完成后，才可修改 `handoffs/TASK-004.md` 的 Reviewer 部分。记录：

- 审查 base、source head、旧 REJECT evidence 与本次复跑命令；
- AC-1 至 AC-5、D-01 至 D-08 矩阵；
- 四项独立探针的命令、预期和实际；
- P0/P1/P2/P3、范围/红线/复用/许可证复核；
- `APPROVE` 或 `REJECT`、跳过项与剩余风险。

只允许提交 `handoffs/TASK-004.md`。review evidence commit 必须以 `30932e1...` 为父提交、范围仅一个 handoff 文件；不得 amend 任何实现、修复或旧审查提交。提交后回报 review evidence SHA、最终 branch HEAD、干净 worktree。

## 返回格式

```text
Task: TASK-004
Role: Second Independent Reviewer
Reviewed implementation head:
Review evidence commit:
Checks rerun:
Independent probes:
Acceptance matrix:
Findings: P0/P1/P2/P3
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Remaining risks:
Decision needed: None | details
Post-commit status:
```
