# TASK-009：Obsidian 视频笔记

- Status: `DONE`
- Assignee: `Codex`
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-009A
- Approval: ADR-009、临时 Vault 文件探针与正式实施范围已批准；真实 Vault 另批
- Decision gate: ADR-009 N-01 至 N-15 已批准；TASK-009A 已 `DONE`，本卡已正式分配

## 2026-07-20 只读预检结论

- Read-only Scout 已在 `main@bb9c6b7bb66040b65b091d980f43281c4d9d6ba6`
  完成，仓库无变化；结论为 `DECISION NEEDED`。
- 已批准 `ADR-009` N-01 至 N-15 并建立 `TASK-009A`。TASK-009A 顺序消费 TASK-008A
  的 `AnalysisOutcome`，冻结 KnowledgeSink/NoteRef 并提升 Jinja2 直接依赖。
- TASK-008A/TASK-009A 均 `DONE` 前，本任务保持 `BLOCKED/UNASSIGNED`。真实 Vault
  和用户笔记继续未授权。

## 2026-07-22 正式分配

- Base：`main@473119704c7638d7afd4e68d84d00e85064ceabd`；Worktree：
  `/Users/developer/Documents/yia-worktrees/task-009`；Branch：`codex/task-009-obsidian-notes`。
- Codex 为唯一 Implementer；完成后由全新独立 Codex Reviewer 审查。允许范围严格为本卡
  七个路径组；不修改领域/配置契约、`state.py`、Schema/migration、依赖、锁文件、CLI、云 Provider 或任务状态。
- 只授权测试创建的临时目录内的原子写、替换、清理与 symlink 安全探针。真实 Obsidian Vault、
  真实用户笔记、工作树/测试目录外写入、外部文件删除/移动/重命名、凭据、云端和网络路径继续禁止。

## 2026-07-22 实现证据与审查授权

- Implementation source：`956e37a15ab29106f16c45873fccb813cc5a959f`，唯一父为固定 base
  `473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 落在本卡批准的七路径组内。
- Implementer 自报 focused `4/6`、full pytest `337`、mypy、Ruff、CLI、lock/sync、offline build、
  template/migration package inclusion、临时 Vault 原子写和 SQLite 补账均 PASS；这些只构成待独立复跑证据。
- 全新独立 Codex Reviewer 仅可向 source handoff 写审查证据，不得改业务代码、依赖、锁文件、main
  或任务状态。TASK-008 继续独立 `IN_REVIEW`，不得被本次审查触碰。

## 2026-07-22 范围工件清理后复审

- 首轮 Reviewer evidence：`d16498fe2a1939c6bec7babd03039e623782d027`，唯一父为 implementation
  `956e37a15ab29106f16c45873fccb813cc5a959f`，只修改 source handoff。
- 首轮 `REJECT` 唯一原因是未跟踪 `.codebase-memory/` 代码索引工件；实现 Diff 本身严格落在
  本卡七个批准路径组内，fixed diff check 通过，未记录业务代码 finding。
- 产品负责人已批准并执行只删除 `.codebase-memory/.gitattributes`、`artifact.json`、`graph.db.zst`；
  这些是非 Git 跟踪的本地索引。source 已恢复干净，现授权全新独立 Reviewer 2 完整复审。

## 2026-07-22 第二轮审查拒绝与 Correction 1

- Reviewer 2 evidence：`f778163dca83807f1baec5e568c4dbd734829171`，唯一父为 first-review evidence
  `d16498fe2a1939c6bec7babd03039e623782d027`，只修改 source handoff。
- Verdict：`REJECT`，P1=2、P2=1。标题变化使已完成笔记按新标题路径查找而失败；同 video_id 非受管候选
  仍会允许创建第二份笔记，均违反 ADR-009 N-03/N-05。`vault_subdir="C:"` 未被拒绝，违反 N-06。
- 原 Codex Implementer 只获 Correction 1：`notes.py`、Obsidian Adapter、两份既有测试和 handoff。必须
  恢复/验证首次稳定 NoteRef、在写入或补账前按 video_id 对所有候选 fail-closed，并拒绝盘符子目录；不得
  重命名、删除、移动或接管现有笔记，且不得新增 Schema/Repository 方法。
- 真实 Vault、用户笔记、测试目录外 I/O、依赖/锁、Schema/migration、`state.py`、CLI、TASK-008、
  云端、网络、凭据、媒体与模型路径继续不授权。

## 2026-07-22 Correction 1 实现证据与复审授权

- Correction source：`60ed077452faf5fe41b105b21b4221f89cb6e02c`，唯一父为 reviewer-2 evidence
  `f778163dca83807f1baec5e568c4dbd734829171`；Correction 仅修改 `notes.py`、Obsidian Adapter、
  `test_obsidian_sink.py` 与 source handoff，完整 Diff 仍在原批准范围内。
- Implementer 自报从既有 VIDEO_NOTE Artifact 恢复首次稳定路径，且在写入/验证/补账前对所有同
  video_id 候选 fail-closed、拒绝 `C:`；focused=`4/12`、full pytest=`343` 与其余离线门禁通过。
  这些均待独立 Reviewer 3 复跑。
- Reviewer 3 只可追加 source handoff；不得触及真实 Vault、用户笔记、测试目录外 I/O、网络、云端、
  凭据、媒体、模型、TASK-008 或任何范围外索引工件。

## 2026-07-22 第三轮审查拒绝与 Correction 2

- Reviewer 3 evidence：`f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`，唯一父为 Correction 1
  `60ed077452faf5fe41b105b21b4221f89cb6e02c`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。Vault 权限类 `OSError` 被一律映射为 `LOCAL_RESOURCE`；ADR-009 N-13 要求
  `EACCES`、`EPERM`、`EROFS` 映射为 `PERMISSION_DENIED`，资源失败才保留 `LOCAL_RESOURCE`。
- 原 Codex Implementer 只获 Correction 2：Obsidian Adapter、既有 note 集成测试与 handoff。必须补齐
  errno-aware 的安全映射和临时 Vault 回归，不得改变稳定身份、候选冲突、盘符、原子写、补账或既有公共契约。
- 真实 Vault、用户笔记、测试目录外 I/O、依赖/锁、Schema/migration、`state.py`、CLI、TASK-008、
  云端、网络、凭据、媒体与模型路径继续不授权。

## 2026-07-23 Correction 2 第四轮独立审查与整合授权

- Reviewer 4 evidence：`e675feef7f12d19561f1ca439e181a47f4a521b8`，唯一父为 Correction 2
  `22147b087157a6bbb0adc7e78f2f5d3eae700f8e`，只修改 source handoff。
- Verdict：`APPROVE`，P0–P3 均无。独立临时 Vault/SQLite N-13 矩阵证明权限 errno 映射为
  `PERMISSION_DENIED`，资源失败保持 `LOCAL_RESOURCE`；原笔记、Pipeline/Job/Artifact、临时文件清理
  与脱敏边界均通过。锁/sync、focused `4/17`、全量 `348`、mypy、Ruff、CLI、离线构建和包内容检查通过。
- TASK-009 进入 `ACCEPTED`，仅授权 Product Integrator 对固定 source 做 `--no-ff` 合并和整合后离线验证；
  不得自行设为 `DONE`。真实 Vault、用户笔记、网络、云端、凭据、媒体与模型路径仍未授权。

## 2026-07-23 整合结果

- Codex Product Integrator 已以 merge commit `1cb718b7e7e53705ae12792a3c2ba2d0f26b2476` 整合 source；
  双父为授权 main `777e5a65b74e719050d2d6d4979cccea9d4ccfba` 与 accepted source
  `e675feef7f12d19561f1ca439e181a47f4a521b8`。
- first-parent Diff 严格为六个实际使用的批准路径，fixtures 未改；lock/sync、focused `4/17`、全量 `382`、
  mypy、Ruff、CLI、离线构建和 sdist/wheel 模板、migration inclusion 全通过。source 已成为 main 祖先，
  两个 worktree 均干净，未 push 或清理 source。
- 本卡已收口为 `DONE`。剩余风险仍为 `os.replace` 成功至 SQLite 完成间的
  at-most-once best effort，以及未授权、未运行的真实 Vault 路径。

## 目标

将视频、最终评分和结构化分析完成/跳过结果幂等渲染为 Obsidian Markdown 笔记，
安全处理身份、路径、同名冲突和故障恢复，并逐字节保留用户的 `我的思考`。本任务
只使用临时 Vault；真实云分析集成由 TASK-010 完成。

## 范围

- 实现稳定 Frontmatter、文件命名、模板渲染、自动管理区和用户编辑区。
- 使用固定打包 Jinja2 模板、安全 primitive 和严格资源上限。
- 使用 anchored directory FD、同目录临时文件、fsync + 原子替换，确保目标始终是
  完整旧版或完整新版。
- 校验所有路径位于逻辑 Vault 子目录；同一 `video_id` 只对应一份稳定路径笔记。
- 复用现有 `complete_stage` 完成 VIDEO_NOTE Artifact、Pipeline/Job，并验证
  replace 后 SQLite 失败的补账恢复。

## 范围外

- 默认测试不得写用户真实 Vault。
- 不修改、移动或删除非本系统管理的笔记。
- 不实现周报。
- 不自动刷新已 `NOTE_WRITTEN`/`COMPLETE` 的成功笔记；不新增 Repository 方法。
- 不修改领域契约、`state.py`、Schema/migration、依赖、锁文件或云 Provider。

## 验收标准

- [ ] 临时 Vault 测试覆盖首次创建、失败重排、无变化、标题变化、Unicode/保留名、
  casefold 冲突、路径穿越、symlink、目录替换和短写/fsync/replace 失败。
- [ ] Frontmatter 顺序/类型、固定正文、analysis completed/skipped、低价值零写和
  Jinja StrictUndefined/资源上限符合 ADR-009。
- [ ] 用户修改 `我的思考` 后在合法失败重排中逐字节保留；marker/legacy/非法 UTF-8
  全部 fail-closed，原文件不变。
- [ ] 真实临时 SQLite 证明 `ANALYSIS_READY -> NOTE_WRITTEN`、VIDEO_NOTE Artifact、
  Job 完成、事务回滚和 replace 后补账；已完成普通调度零改写。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_note_rendering.py`
- [ ] `uv run python -m pytest tests/integration/test_obsidian_sink.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build --offline`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工检查：只在临时 Vault 解析样例 Markdown；确认 Frontmatter、标题、marker 和
  用户区，不打开或扫描真实 Vault。

## 预计触达文件

- `src/youtube_intel/notes.py`
- `src/youtube_intel/providers/obsidian.py`
- `src/youtube_intel/templates/video.md`
- `tests/fixtures/notes/**`
- `tests/unit/test_note_rendering.py`
- `tests/integration/test_obsidian_sink.py`
- `handoffs/TASK-009.md`

不包含 `domain.py`、`config.py`、`state.py`、Schema/migration、`pyproject.toml`、
`uv.lock`、云 Provider、CLI、任务状态或真实 Vault 文件。公共契约、模板打包或现有
Repository 不足时必须报告 `DECISION NEEDED`。

## 复用决定

- `DIRECT`：TASK-009A 锁定后的 Jinja2；固定包内模板、不可变 sandbox 和
  StrictUndefined。
- `DIRECT`：现有 PyYAML、Artifact/SQLite/Pydantic 与 Python 标准库安全文件能力。
- `REFERENCE`：已登记 yt2md 项目只参考输出结构，不复制代码、不读取 Obsidian 配置。
- `REJECT`：任意模板 loader、用户模板、自动接管/修复笔记、成功笔记 refresh 和
  真实 Vault。

## 交付证据

- 临时 Vault 的脱敏样例路径/内容摘要。
- ADR-009 N-01 至 N-15 追溯，以及原子写、路径边界、用户区、SQLite 补账测试结果。
- 真实 Vault 未触达声明；如触达则附用户授权和受控验证结果。
