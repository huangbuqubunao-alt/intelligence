# TASK-007：Ollama 本地评分

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Owner role: Codex Implementer（离线实现）
- Size: M
- Risk: Medium
- Depends on: TASK-005A

## 2026-07-16 只读预检

- Scout observed main：`b335b12358bbbc9dada1abfafc5a2fe9a68494be`
- Repository changes：None
- 结论：`DECISION NEEDED`
- ADR-007 L-01 至 L-15 已于 2026-07-17 接受；本任务仍为 `BLOCKED/UNASSIGNED`，
  不得创建 worktree、安装 Ollama 或拉取模型。
- 共享配置、采样、决策对象与评分摘要原子持久化必须先由 TASK-005A 整合为 `DONE`；
  TASK-007 继续不修改依赖或锁文件。Ollama 安装/启动、模型拉取与本机文本冒烟仍须
  独立任务级授权。

## 2026-07-19 离线实现分配与边界

- Main control-plane base：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。worktree：
  `/Users/hua/Documents/yia-worktrees/task-007`；branch：
  `codex/task-007-local-scoring`；Implementer：Codex；完成后由全新独立 Codex
  Reviewer 审查。
- 仅允许本卡“预计触达文件”列出的 `scoring.py`、`providers/ollama.py`、
  `prompts/scoring.md`、两份测试、`tests/fixtures/scoring/**` 和
  `handoffs/TASK-007.md`。复用 Python 标准库 HTTP/JSON 与既有锁定依赖；不得修改
  `pyproject.toml`、`uv.lock`、Schema/migration、共享 `config.py`/`domain.py`/`state.py`
  或任务状态。
- 所有验证必须离线：允许 Fake transport/本地测试替身，不得请求实际 `127.0.0.1:11434`
  或任何外部地址。若环境缺少已锁定包，只允许 `uv sync --locked --offline`；它失败时停止，
  不得联网补包。
- 继续禁止：Ollama 安装或启动、`qwen3:8b` 拉取、真实模型/服务调用、cloud tag、模型
  下载、媒体/YouTube、Cookie/登录、remote components、ffmpeg、真实 Vault/密钥或文件
  删除。真实文本冒烟属于后续单独授权。

## 目标

使用可配置的 Ollama Provider 对元数据和规范文本做本地价值评分，严格解析结构化结果，并由应用策略决定是否进入深度分析。

## 范围

- 实现评分输入采样、Prompt 版本、Provider 调用、Schema 校验和一次格式修复。
- 记录总分、理由、主题、建议值、应用阈值结果和不一致诊断。
- 建立输入/模型/Prompt/Schema 版本感知的评分缓存。

## 范围外

- 不调用云端模型。
- 不写 Obsidian 或周报。
- 不把模型输出直接当可信对象或让模型绕过配置阈值。
- 不自动安装/启动 Ollama、不自动拉取模型、不访问 cloud tag 或远程地址。

## 验收标准

- [ ] 固定响应覆盖合法评分、越界分数、缺字段、非法 JSON、修复成功和修复失败。
- [ ] 字幕采样覆盖开头/正文/结尾且受长度限制；同一规范输入重复评分命中缓存。
- [ ] `should_summarize` 的最终值由批准阈值策略决定，模型建议冲突会被记录。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_scoring.py`
- [ ] `uv run python -m pytest tests/integration/test_ollama_provider.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build`
- [ ] `git diff --check`
- [ ] 可选本地冒烟：对一个固定文本运行已批准模型，记录模型名、版本、耗时和结构化结果，不记录全文。

## 预计触达文件

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

本任务使用 Python 标准库 HTTP，不新增 `httpx`/Ollama SDK，不修改
`pyproject.toml`/`uv.lock`。共享 `config.py`、`domain.py`、`state.py`、示例配置和
既有契约/状态测试必须由 TASK-005A 先行完成。

## 交付证据

- 测试和可选冒烟结果。
- Prompt/Schema 版本示例。
- 黄金样例人工评分偏差说明。
- Ollama 版本、模型 tag/digest/许可证、Fake HTTP、安全读取和 no-cloud 边界证据。
