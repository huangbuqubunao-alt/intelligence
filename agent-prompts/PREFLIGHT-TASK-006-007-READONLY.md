# TASK-006 / TASK-007 并行只读预检 — Read-only Scout

你是一个全新的 Codex 只读 Scout。你只为主控盘点 TASK-006 本地 Whisper 转写与 TASK-007 Ollama 本地评分的规格、依赖、复用、文件范围、离线测试和任务级审批空白；不得实现、安装、下载、写文件、提交或改变任何任务状态。

## 固定入口与并行隔离

- Main repository：`/Users/developer/Documents/youtubek agent`
- 只允许在本包已提交后的干净 main 上运行。
- 动态观察基线：`git log -1 --format=%H -- agent-prompts/PREFLIGHT-TASK-006-007-READONLY.md`；该提交必须是 `b28f52d0e4950f78dba315d4afe211ea5f75b93c` 的单父直接后继。
- TASK-005 Implementer 将在 `/Users/developer/Documents/yia-worktrees/task-005` 并行写入。严禁读取、检查、等待、清理或以任何方式访问该 live worktree。
- TASK-005 尚未完成的领域变更只能视为未来依赖；不得猜测、复制或围绕未整合代码设计实现。需要参考已冻结字幕契约时只读 ADR-006 与 main 当前 Git 对象。

## 严格只读边界

禁止创建、编辑、删除、暂存或提交文件；禁止创建分支/worktree/stash/tag/merge；禁止运行会写 `.venv`、cache、数据库、构建产物或配置的命令；禁止 `uv sync`、依赖/模型/二进制下载、pytest、mypy、Ruff、CLI、build；禁止真实 YouTube、音频、Ollama、模型服务、Vault 或密钥访问。

允许 `git show`、`git diff`、`git ls-tree`、`rg`、`sed`、`python --version` 等只读命令。开始与结束均确认 main HEAD 不变、`git status --short` 无输出。

## 必读材料

按 `AGENTS.md` 顺序读取事实源，并重点检查：

- `docs/PRD.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/PRODUCT_DECISIONS.md` 的 DEC-02/03/05/06/07/09
- `docs/REUSE_REGISTER.md`
- ADR-002、ADR-003、ADR-005、ADR-006
- `docs/IMPLEMENTATION_ROADMAP.md`
- `tasks/TASK-006-local-transcription.md`
- `tasks/TASK-007-local-scoring.md`
- main 当前 `config.py`、`domain.py`、`state.py`、`pyproject.toml`、`uv.lock`

任一文档冲突时输出 `DECISION NEEDED`，不得自行选择。

## TASK-006 必须回答

1. `mlx-whisper` 的推荐精确版本范围、Python 3.12/macOS arm64 兼容性、直接/传递依赖、许可证和安装/模型下载体积；哪些动作需要产品负责人任务级批准。
2. 默认模型与可配置参数如何映射既有 `TranscriptArtifact`/Artifact/Provider-call 契约；哪些字段必须等待 TASK-005 最终整合后复核。
3. 音频获取在“无 Cookie/登录/remote components、ffmpeg 未授权”下的可行边界：yt-dlp 选择、允许容器/编码、是否必须新增 ffmpeg 或其他系统工具审批。
4. 180 分钟上限、`--force`、短音频夹具、超时、内存/磁盘、成功立即删除与失败 7 天保留的确定性策略和缺失配置。
5. 音频哈希 + Provider/模型/参数版本缓存、崩溃恢复、清理失败、错误映射和真实本机冒烟的授权矩阵。
6. 最小文件范围、统一 `uv run` 离线门禁、模型下载与本机冒烟的独立门禁；不得提前建议写实现。

## TASK-007 必须回答

1. Ollama 使用标准库 HTTP 还是新增已白名单 `httpx` 的推荐路径、版本/许可证/安装审批；本地服务地址、模型名、超时和可用性预检的冻结空白。
2. `ScoringInput`、`ScoreResult`、Prompt/Schema 版本、一次格式修复与阈值策略是否足够；不得新增自由 `dict` 或让模型决定最终策略。
3. `max_transcript_chars=30000` 下开头/正文/结尾的确定性采样算法、边界值、语言/元数据组合和 input hash 维度。
4. Provider-call 预留/缓存/恢复、合法/非法 JSON、修复成功/失败、错误码/重试归属和日志脱敏契约。
5. Prompt 文件版本、黄金夹具、Fake HTTP、可选本地 Ollama 冒烟的文件范围和任务级授权；不得访问真实服务。
6. 统一 `uv run` 检查和 TASK-006/007 在 TASK-005 `DONE` 后的安全并行 worktree/锁文件冲突策略。

## 复用与交付要求

分别给出 `DIRECT / ADAPT / REFERENCE / REJECT / DEFER` 矩阵、来源、版本/commit、许可证和拒绝理由。优先标准库与已批准官方组件；不得联网调研、克隆或复制候选代码。明确哪些结论现在可冻结，哪些必须在 TASK-005 source 审查/整合后复核。

## 输出格式

只在终端返回：

```text
Preflight: TASK-006 / TASK-007
Role: Read-only Scout
Observed main commit:
Repository changes: None
Spec consistency: PASS | DECISION NEEDED
TASK-006 contract/dependency matrix:
TASK-006 reuse/license matrix:
TASK-006 approvals still needed:
TASK-006 suggested file/check scope:
TASK-007 contract/dependency matrix:
TASK-007 reuse/license matrix:
TASK-007 approvals still needed:
TASK-007 suggested file/check scope:
Parallelization and lockfile strategy:
Items requiring TASK-005 final-contract recheck:
Risks/blockers:
Recommended decisions:
Recommended next action:
Postflight git status:
```

最后再次确认 `Repository changes: None`、main HEAD 未变化、工作区无变更。TASK-006/007 必须保持 `BLOCKED/UNASSIGNED`。
