# TASK-004 Grok Pre-review Correction Packet

## 身份与范围

你是 TASK-004 的原 Grok Implementer。主控预审发现一个 P1 公共契约问题；你只修复该问题并补充回归测试/交接，不领取 TASK-003、不启动 Reviewer、不合并 main、不更改公共任务状态。

## 固定上下文

完整读取：

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/SYSTEM_DESIGN.md` 第 3、5、5.2、12 节
4. `docs/decisions/ADR-002-config-domain-contracts.md` C-05
5. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-05、D-08
6. `tasks/TASK-004-discovery-metadata.md`
7. `handoffs/TASK-004.md`
8. 原 Implementer 包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-004-IMPLEMENTER-GROK.md`
9. 本修复包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-004-CORRECTION-GROK.md`

如冻结契约仍无法满足、修复需要增加公共领域类型/错误码、修改范围外文件或改变依赖，立即输出 `DECISION NEEDED`，不得自行扩大设计。

## 固定基线

- Task: `TASK-004` pre-review correction
- Role: original `Grok Implementer`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Required source head before correction: `392edfb897003c1583b538667d10a2a89926a94b`
- Reviewer: Codex，尚未启动；只有新的修复证据通过主控核对后才可启动
- Parallel work: TASK-003 Codex Implementer，继续运行；不得读取、写入或等待 TASK-003

## 唯一允许修改的 3 个文件

- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `handoffs/TASK-004.md`

不得改动 `pyproject.toml`、`uv.lock`、`discovery.py`、`domain.py`、`state.py`、fixtures、集成测试、任务状态或任何其他文件。若三文件不足以安全修复，停止并报告。

## P1 必须修复

System Design §5.2 与 ADR-002 C-05 冻结了“跨模块公共接口不得使用自由形状 `dict`”。TASK-004 可以在 yt-dlp Adapter 内部临时接收/构造原始映射，但不得把它作为公开 API 交给其他模块。

首个实现当前问题：

- `SAFE_YDL_OPTS` 与 `build_ydl_opts()` 在 `__all__` 中公开 `dict[str, Any]`。
- `map_info_dict_to_video_metadata`、语言/状态 Mapping helper 等含 `Mapping[str, Any]` 的 yt-dlp 原始边界被公开。
- `YtDlpMetadataProvider` 公开了 `last_opts: list[dict[str, Any]]` 注入/属性，且公开构造参数不应泄漏自由 dict。

修复要求：

1. 对跨模块调用者，`youtube.py` 的公开 API 只能保留满足冻结 Provider 契约的具名 `YtDlpMetadataProvider`（如确有另一个不含自由 dict 的公开类型，必须在交接中说明；默认不要新增）。
2. 所有 yt-dlp 原始 dict/Mapping、选项构造、字段映射和测试注入机制必须为 Adapter 内部实现（私有命名且不在 `__all__`）；不得把自由 dict 用 `Any`、别名或无类型包装伪装为公共接口。
3. 重构测试注入/选项捕获，使测试仍能证明 `skip_download`、无 Cookie/登录态、无 remote components、无 ffmpeg、无媒体/字幕写入，但公开 `YtDlpMetadataProvider` 构造函数/属性不泄漏自由 dict。
4. 不改变 Adapter 行为、错误码、语言排序、依赖锁、未授权边界或原始任务的 17 文件范围。
5. 增加真正会失败的回归测试：公共导出/公开方法/公开属性的注解均不含自由 `dict`、`Mapping[str, Any]` 或等价未校验结构；同时保留实际 Provider fake 路径证明映射和安全 options 仍有效。

可保留 task-scope 的私有协议、私有 dataclass 或私有 factory 以服务离线测试；不要为此修改 `domain.py` 或新增领域契约。不得删除既有测试或把断言改弱。

## 执行与验证

开始前必须确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
```

worktree 必须干净，HEAD 必须为 `392edfb...`，身份必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。否则立即停止。

修复后运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
git diff --check
git status --short
```

再完整核对 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...HEAD`：总范围仍只能属于原批准的 TASK-004 17 文件集合，修复 commit 自身只能是以上 3 文件；无密钥、Cookie、真实响应、媒体、缓存或范围外修改。

不 amend 首个实现 commit。创建一个新 commit，建议消息：

```text
fix: hide yt-dlp raw mapping internals
```

在 `handoffs/TASK-004.md` 增加“预审修复”段，说明原 P1、封装方式、回归测试、检查结果、新 code evidence SHA 与剩余风险。不得将任务改为 `IN_REVIEW` 或 `DONE`。

## 返回格式

```text
Task: TASK-004
Role: Implementer (pre-review correction)
Branch/worktree:
Base commit:
Prior head:
Code evidence commit:
Branch head:
Changed files in correction commit:
P1 resolution evidence:
Checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
