# TASK-004 Independent Codex Reviewer Packet

## 角色与硬边界

你是与 Grok Implementer 独立的新 Codex Reviewer。你不重写业务代码、不改任务状态、不合并 main；只能在全部审查完成后向 `handoffs/TASK-004.md` 写入 Reviewer 部分，并单独提交该交接证据。发现 P0/P1/P2 时不要修复，输出 `REJECT` 并将问题交回原 Grok Implementer。

## 固定上下文

- Task: `TASK-004`
- Role: `Reviewer`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Reviewed source head: `9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- Main review-authorization baseline: 由主控在 Status Integrator 提交完成后、随启动指令提供；不在本提交内自引用 SHA
- Implementer 已停止写入，source worktree 在审查开始时必须干净
- Parallel work: TASK-003 Codex Implementer 继续运行；禁止读取、写入、检查、清理或等待 TASK-003

先完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md`
5. `docs/SYSTEM_DESIGN.md` 第 3、5、5.2、12 节
6. `docs/REUSE_REGISTER.md`
7. `docs/decisions/ADR-002-config-domain-contracts.md` C-05
8. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-01 至 D-08
9. `tasks/TASK-004-discovery-metadata.md`
10. `handoffs/TASK-004.md`
11. `agent-prompts/TASK-004-IMPLEMENTER-GROK.md`
12. `agent-prompts/TASK-004-CORRECTION-GROK.md`
13. `agent-prompts/TASK-004-CORRECTION-2-GROK.md`
14. 本 Reviewer 包

## 开始前门禁

在 TASK-004 worktree 中确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git log --oneline --decorate -4
```

必须在 `grok/task-004-discovery-metadata`，初始 HEAD 必须为 `9db800f...`，worktree 干净，身份为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。确认三个实现链提交 `392edfb...`、`10f5ffa...`、`9db800f...` 连续且可达；否则停止，不写交接。

## 范围与红线审查

1. 审查 `dcc7d85...9db800f...` 完整 Diff 只能属于以下原批准范围：
   - `src/youtube_intel/discovery.py`
   - `src/youtube_intel/providers/youtube.py`
   - `tests/unit/test_discovery.py`
   - `tests/integration/test_discovery_adapter.py`
   - `tests/fixtures/youtube/**`
   - `pyproject.toml`
   - `uv.lock`
   - `handoffs/TASK-004.md`
2. 核对直接依赖仍为批准范围的 `yt-dlp[default,deno]>=2026.7.4,<2026.8`，锁定版本和传递依赖合理；不得有额外直接运行依赖或既有直接依赖升级。
3. 检查没有真实 YouTube、Cookie/浏览器 Cookie、账号、remote components、ffmpeg、媒体/字幕下载、Vault、密钥、真实响应或缓存。
4. 确认不修改 `domain.py`、`state.py`、任务状态、CLI 或 TASK-003 接口，`DiscoveryRepository` 仍为窄 Protocol。

## 独立验收与探针

重新运行（不因 Implementer 报告而跳过）：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
git diff --check dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...9db800fc9f4d01a5b6348c5cc8b567f83dc442aa
```

另外设计并执行至少两个独立、非写入探针，并记录命令、预期和实际结果。必须覆盖：

1. **公开 Surface/私有钩子探针：** 不只检查 `__all__`。验证公开构造函数没有 factory/callback/sink/raw-payload 参数、没有非私有 raw `map_*`/`build_*`/`SAFE_*` 入口或自由 `dict`/`Mapping[str, Any]` 注解；私有 `_bind_test_hooks` 只服务测试，领域调用只产生 `VideoMetadata`/`ProviderCallMetadata`。
2. **安全 options 与离线路径探针：** 用离线 Fake/私有测试钩子捕获 `YoutubeDL` 参数和 `extract_info(..., download=False)`；验证 `skip_download`、`noplaylist`、无 Cookie/登录/remote components/ffmpeg/媒体或字幕写入，且原始 info mapping 不跨 Adapter 边界。

还要逐项判定任务 AC-1 至 AC-5、ADR-004 D-01 至 D-08、错误映射/正文脱敏、游标原子性与元数据独立失败语义。真实 YouTube 冒烟、Cookie/登录、remote components、ffmpeg、媒体/字幕下载仍**不得**运行；作为明确跳过项记录。

## 交接证据与提交

只有当所有审查、探针和检查完成后，才可以修改 `handoffs/TASK-004.md` 的 Reviewer 部分。记录：

- 审查 base、source head、复跑命令与结果；
- AC-1 至 AC-5、D-01 至 D-08 矩阵；
- 两个独立探针的命令/证据；
- P0/P1/P2/P3、范围/红线/复用与许可证复核；
- `APPROVE` 或 `REJECT`、跳过项和剩余风险。

只允许提交 `handoffs/TASK-004.md`。该 review evidence commit 必须以 `9db800f...` 为父提交、范围仅一个交接文件；不得 amend 实现提交。提交后回报 review evidence SHA、最终 branch HEAD 和干净 worktree。

## 返回格式

```text
Task: TASK-004
Role: Reviewer
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
