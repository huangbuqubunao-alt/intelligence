# TASK-004 Grok Pre-review Correction 2 Packet

## 身份与范围

你是 TASK-004 的原 Grok Implementer。首轮预审修复未满足既定 P1 任务包：它仅隐藏了类型标注，却仍向跨模块调用者公开残余映射入口和测试注入入口。你只完成本轮最小收口、更新离线测试和交接；不领取 TASK-003、不启动 Reviewer、不合并 main、不更改公共任务状态。

## 固定上下文

完整读取：

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/SYSTEM_DESIGN.md` 第 3、5、5.2、12 节
4. `docs/decisions/ADR-002-config-domain-contracts.md` C-05
5. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-05、D-08
6. `tasks/TASK-004-discovery-metadata.md`
7. `handoffs/TASK-004.md`
8. 首轮修复包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-004-CORRECTION-GROK.md`
9. 本修复包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-004-CORRECTION-2-GROK.md`

如冻结契约仍无法满足、修复需要增加公共领域类型/错误码、修改范围外文件或改变依赖，立即输出 `DECISION NEEDED`，不得自行扩大设计。

## 固定基线

- Task: `TASK-004` pre-review correction 2
- Role: original `Grok Implementer`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Required source head before correction: `10f5ffaaa3e8651a02e2f94c1736b8417acf3021`
- Main control-plane baseline: `main@290b8a27e21e1c1dcb6022c57205acaf7e17713e`
- Reviewer: Codex，尚未启动；只有新的修复证据通过主控核对后才可启动
- Parallel work: TASK-003 Codex Implementer，继续运行；不得读取、写入、清理或等待 TASK-003

## 唯一允许修改的 4 个文件

- `src/youtube_intel/providers/youtube.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `handoffs/TASK-004.md`

`tests/integration/test_discovery_adapter.py` 是原 TASK-004 批准范围内的文件，本轮只允许为移除残余公开入口/公开注入而做最小改动。不得改动 `pyproject.toml`、`uv.lock`、`discovery.py`、`domain.py`、`state.py`、fixtures、任务状态或任何其他文件。若四文件不足以安全修复，停止并报告。

## P1 必须完整修复

System Design §5.2 与 ADR-002 C-05 冻结了“跨模块公共接口不得使用自由形状 `dict`”。TASK-004 可以在 yt-dlp Adapter 内部临时接收/构造原始映射，但不得把它作为公开 API 交给其他模块。

首轮修复仍有两项不合格：

1. `map_info_dict_to_video_metadata(info: object)` 是非私有模块级 callable。`__all__` 仅影响通配导入，不是访问控制；该非私有名称仍邀请跨模块调用者传入 yt-dlp 原始 payload。
2. `YtDlpMetadataProvider.__init__` 仍公开 `ydl_factory: object | None` 与 `last_opts: object | None`。它们是对自由 dict 的测试注入/捕获入口；将类型写成 `object` 不符合“不得用 Any、别名或无类型包装伪装为公开接口”。

修复要求：

1. 公开跨模块 Provider Surface 只能是 `YtDlpMetadataProvider` 的领域构造/`fetch(video_id: str) -> VideoMetadata`；构造参数不得包含 `ydl_factory`、`last_opts`、`clock` 或任何测试 callback/sink/raw payload 入口。既有无自由结构的 `last_call: ProviderCallMetadata | None` 可保留。
2. 删除残余非私有 `map_info_dict_to_video_metadata`；所有 yt-dlp 原始 dict/Mapping、选项构造、字段映射与 factory/时钟/选项捕获等测试机制都必须是 Adapter 内部的私有名称。不要用 `object`、`Any`、别名或无注解 wrapper 暴露它们。
3. 以私有模块 hook 的测试期替换（例如对私有 factory/时钟做 test-scoped monkeypatch）或等价私有方案，保留安全 options 与实际 Provider fake 路径。更新集成测试，使它不再从 `youtube.py` 导入任何非私有 mapping helper。
4. 回归测试必须真正验证：
   - `__all__` 只有 `YtDlpMetadataProvider`；
   - 不存在非私有的 `map_*`、`build_*`、`SAFE_*` 等 raw-boundary callable/value；
   - `YtDlpMetadataProvider.__init__` 只含 `self` 与已批准的领域配置参数，且没有 callback/sink/raw payload 注入；
   - 保留真实 Provider fake 路径，证明 mapping 和安全 options 仍有效。
5. 不改变 Adapter 行为、错误码、语言排序、依赖锁、未授权边界或原始任务的 17 文件范围。不得删除或削弱既有断言；只可为私有化改写测试支撑。

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

worktree 必须干净，HEAD 必须为 `10f5ffa...`，身份必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。否则立即停止。

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

再完整核对 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...HEAD`：总范围仍只能属于原批准的 TASK-004 17 文件集合，修复 commit 自身只能是以上 4 文件；无密钥、Cookie、真实响应、媒体、缓存或范围外修改。

不 amend 已有提交。创建一个新的 commit，建议消息：

```text
fix: make yt-dlp test hooks private
```

在 `handoffs/TASK-004.md` 增加“二次预审修复”段，说明未通过点、私有化方式、更新的集成测试、回归测试、检查结果、新 code evidence SHA 与剩余风险。不得将任务改为 `IN_REVIEW` 或 `DONE`。

## 返回格式

```text
Task: TASK-004
Role: Implementer (pre-review correction 2)
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
