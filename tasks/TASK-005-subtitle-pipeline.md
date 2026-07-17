# TASK-005：字幕获取与规范化

- Status: `DONE`
- Assignee: `Codex`
- Reviewer: `Codex`（第四次全新独立审查 `APPROVE`；Product Integrator 已完成整合）
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004
- Decision gate: `ADR-006` 为 `Accepted`；产品负责人已于 2026-07-15 批准 T-01 至 T-15
- Execution gate: TASK-003/004 已在 main `DONE`；产品负责人已授权固定 worktree、角色、范围、既有锁定依赖的离线 `uv` 命令和构建。ADR-006 设计批准不授权真实产品网络

## 目标

为单个视频按语言偏好获取人工或自动字幕，保存原始产物并生成可供下游使用的规范文本；无有效字幕时明确返回本地转写需求。

## 范围

- 实现人工字幕 > 自动字幕的选择策略和语言偏好排序。
- 保存原始字幕，规范化为文本并执行空文本、乱码、重复率和最低长度质量检查。
- 以视频、字幕来源、语言和内容哈希建立幂等缓存。
- 在 `domain.py` 使用具名字幕格式、质量、转写原因和判别联合，不使用自由 `dict`。
- 使用现有 `SUBTITLE_SOURCE` / `TRANSCRIPT_CANONICAL`、Provider-call 缓存和 `complete_stage`；V1 不修改 Schema 或 Repository 语义。

## 范围外

- 不实现 Whisper 转写。
- 不做视频评分或总结。
- 不删除用户文件，不把字幕全文写入日志或 SQLite。
- 不修改 `state.py`、migration、`pyproject.toml` 或 `uv.lock`。
- 不访问真实 YouTube/字幕，不使用 Cookie、登录、`.netrc`、remote components、ffmpeg 或媒体下载，除非后续获得精确授权。

## 验收标准

- [ ] 固定夹具覆盖人工字幕优先、自动字幕回退、多语言选择、空字幕和损坏字幕。
- [ ] 同一输入重复处理不重复下载/规范化；原始字幕与规范文本均有哈希和来源元数据。
- [ ] 无有效字幕返回明确 `transcription_required` 结果，网络错误和“确实无字幕”可区分。
- [ ] 缓存命中时验证既有 Artifact 与文件哈希，以空 Artifact stage completion 完成当前 Job；不重新下载、不修改 TASK-003 Repository。
- [ ] 原始字幕与规范文本使用安全 DATA-relative 路径和原子写入；崩溃恢复不相信未验证文件，日志/错误/SQLite 不含临时 URL、正文或绝对路径。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run python -m pytest tests/unit/test_subtitle_policy.py`
- [ ] `uv run python -m pytest tests/integration/test_subtitle_provider.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工检查：日志只包含视频 ID、语言、来源、路径/哈希和计数，不含字幕全文。

## 预计触达文件

- `src/youtube_intel/domain.py`
- `src/youtube_intel/transcripts.py`
- `src/youtube_intel/providers/subtitles.py`
- `tests/unit/test_contracts.py`
- `tests/unit/test_subtitle_policy.py`
- `tests/integration/test_subtitle_provider.py`
- `tests/fixtures/subtitles/` 下最小夹具
- `handoffs/TASK-005.md`

除非新的 ADR 先获批准，预计范围不包含 `state.py`、`migrations/**`、`pyproject.toml` 或 `uv.lock`。

## 交付证据

- 测试矩阵和结果。
- 一个脱敏的 TranscriptArtifact 示例。
- 字幕质量规则的已知误判风险。
- 原始/规范幂等键、原子写入、缓存恢复和空 Artifact stage completion 的离线证据。
- `yt-dlp`/标准库的实际复用与许可证证据；未新增依赖的锁文件核对。

## 并行只读预检

- TASK-005 只读预检已完成；全程未修改仓库、安装依赖、下载字幕或访问真实 YouTube。
- Preflight packet: `agent-prompts/PREFLIGHT-TASK-005-READONLY.md`。
- Scout 输出已经主控收敛为 ADR-006；预检本身不改变依赖满足状态，不构成 `READY` 或实现授权。

## 只读预检结论与待批准决策

- Scout observed main: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`；全程只读，主线无变化。
- 预检确认既有领域对象不足以无歧义表达“字幕就绪”与“需要本地转写”，语言/格式/质量/缓存细则也尚未冻结。
- 主控已将建议收敛为 `docs/decisions/ADR-006-subtitle-acquisition-contract.md` 的 T-01 至 T-15；产品负责人已全部批准，ADR 状态为 `Accepted`。
- 主控不采纳预检中“直接新增 transcript manifest migration”和“修改 complete_stage 支持 job-neutral Artifact”的原建议。推荐方案使用现有两个 Artifact kind、稳定 key/path、Provider-call 记录、文件哈希验证和空 Artifact stage completion；若实现证据证明不足，再单独升级 Schema/Repository ADR。
- 2026-07-16 正式分配：base 为 `main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`；worktree 为 `/Users/hua/Documents/yia-worktrees/task-005`；branch 为 `codex/task-005-subtitle-pipeline`；Codex 为唯一 Implementer，完成后由全新独立 Codex Reviewer 审查，Reviewer 不得复用 Implementer 对话。
- 实施只允许任务卡列出的 8 个路径：`domain.py`、`transcripts.py`、`providers/subtitles.py`、三份既定测试、`tests/fixtures/subtitles/**` 与 `handoffs/TASK-005.md`。不新增/升级依赖，不改 `state.py`、migration、`complete_stage`、`pyproject.toml` 或 `uv.lock`。允许 `uv sync --locked` 仅为已有锁定依赖的缓存缺失下载，以及全部离线 `uv` 验证/构建命令。
- 真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权；Implementer 不得启动或访问这些路径。

## 实现证据与审查授权

- Implementation commit：
  `98d19700818bcae14efc412aaaaeb6eed97a1535`
- Parent/base：
  `b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Source branch/worktree：
  `codex/task-005-subtitle-pipeline` /
  `/Users/hua/Documents/yia-worktrees/task-005`
- 完整 Diff 精确为 11 个文件，全部属于批准的 8 个路径组；source worktree 干净，
  `git diff --check` 通过，身份为 `Mozhu <huangbuqubunao@gmail.com>`。
- Implementer 自报 contracts 50、policy 24、integration 31、全量 191、mypy、
  SQLite wiring、Ruff、CLI、lock/sync、offline build 全 PASS；该记录不是独立
  Reviewer 结论。
- 变更共 4,384 行，其中 `transcripts.py` 1,664 行、integration test 1,020 行。
  Reviewer 必须独立审查职责边界、复杂度、测试质量、安全与性能；不得只按行数拒绝，
  也不得只因测试通过而批准。
- Reviewer packet：`agent-prompts/TASK-005-REVIEWER-CODEX.md`。
- Reviewer 只可在 source handoff 记录结论并创建单文件 evidence commit；不得修改
  业务代码、测试或 main。

## 第一次独立审查结果

- Review evidence：
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Parent：
  `98d19700818bcae14efc412aaaaeb6eed97a1535`
- Review commit 只修改 `handoffs/TASK-005.md`，source/main 均干净。
- 规定门禁最终均通过：focused 50/24/31、全量 191、mypy、SQLite wiring、Ruff、
  CLI、offline build、lock/sync 和 Diff check。
- Verdict：`REJECT`；P0=0、P1=5、P2=1、P3=0。
- P1：
  1. JSON/Unicode 异常 cause/context 保留字幕正文；
  2. 合法 VTT 多 speaker 与 `NOTEworthy` cue identifier 发生语义丢失；
  3. 真实 HTTPMessage 短读、unsupported-only 格式与超长目录字段未 fail-closed；
  4. Provider reservation 顺序和失败释放破坏并发幂等、快速恢复与重复
     all-invalid 稳定结果；
  5. canonical-only 版本失效不能从 verified raw 离线重建。
- P2：`SubtitleAcquisitionService`/`fetch` 职责聚合且测试依赖私有 hooks；本身不
  单独阻断，但修复 P1 时不得继续扩大。
- Correction packet：`agent-prompts/TASK-005-CORRECTION-1-CODEX.md`。
- 任务退回原 Codex Implementer，状态为 `IN_PROGRESS`；不得启动 Reviewer 或后续
  TASK-006/007。

## Correction 1 实现证据与第二次审查

- Correction commit：
  `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Parent：
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Correction 精确修改 `transcripts.py`、`providers/subtitles.py`、policy/
  integration tests 与 handoff 5 文件；完整产品范围仍为原批准的 11 文件。
- Implementer 自报五个 P1 均有 RED/GREEN：异常链脱敏、VTT 语义、Adapter
  fail-closed、Provider-call 幂等/快速恢复、verified raw→canonical 重建。
- Implementer 自报 contracts 50、policy 30、integration 53、全量 219、两项 mypy、
  Ruff、CLI、lock/sync、offline build、包内容与 Diff 全 PASS；依赖/锁未变。
- Correction 新增/修改约 1,489 行；该自报和测试数量不构成独立验收。
- 第二次 Reviewer packet：`agent-prompts/TASK-005-REVIEWER-2-CODEX.md`。
- Reviewer 必须为全新独立 Codex 会话，复跑 R1-R5、原 A-F、AC/T/五轴；只可写
  source handoff。任务状态为 `IN_REVIEW`，未 ACCEPTED/DONE。

## 第二次独立审查结果与 Correction 2

- Review evidence：
  `5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Parent：
  `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Review commit 只修改 `handoffs/TASK-005.md`，source/main 均干净。
- 规定门禁全部通过：focused 50/30/53、全量 219、两项 mypy、Ruff、CLI、
  offline build、包内容、lock/sync 与固定 Diff check。
- Verdict：`REJECT`；P0=0、P1=3、P2=2、P3=0。
- 已独立关闭并须保持回归：R2 VTT speaker/cue 语义、R3 HTTP/目录 fail-closed。
- 未关闭 P1：
  1. 真实 Adapter/Service 与 canonical decode 的异常图仍通过 `__context__`
     持有正文 marker、临时 URL 或绝对路径；
  2. 非 all-invalid `FAILED_FINAL` 重放错误码漂移，reservation 后文件失败遗留
     active lease，两个真实 SQLite Service 竞态会重复目录枚举；
  3. verified raw metadata token 未严格绑定当前语言请求，canonical `model`
     不一致被掩盖，已索引越界 symlink 的 cache 失效分类不符合冻结契约。
- P2：Service/文件/cache/Provider 状态职责与私有 hook 聚合；嵌套 metadata 的
  name runs/空 language bucket 仍有资源放大面。P2 不单独扩大本轮范围，但不得因
  Correction 继续恶化。
- Correction 2 packet：`agent-prompts/TASK-005-CORRECTION-2-CODEX.md`。
- Correction 2 从 `5bb750e8...` 创建新的非 merge commit，继续由原 Codex
  Implementer 执行；只允许 `transcripts.py`、`providers/subtitles.py`、
  policy/integration tests、subtitle fixtures 与 handoff。
- 不修改 `domain.py`、contracts test、`state.py`、Schema/migration、
  `complete_stage`、配置、CLI、`pyproject.toml` 或 `uv.lock`；不得使用宽类型、
  wrapper、进程内锁或异常显示隐藏来绕过问题。
- 任务退回 `IN_PROGRESS`。Correction 2 提交前不得启动第三个 Reviewer；TASK-006/
  TASK-007 继续 `BLOCKED/UNASSIGNED`。

## Correction 2 实现证据与第三次审查

- Correction commit：
  `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Parent：
  `5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Correction 2 为单一非 merge 后继，精确修改 `transcripts.py`、
  `providers/subtitles.py`、policy/integration tests 与 handoff 5 文件；完整产品
  范围仍为原批准的 11 文件。
- Implementer 记录 Reviewer 2 三组反例先 RED `11 failed` 后 GREEN：
  1. Adapter/cache/Service 完整异常图脱敏；
  2. pre-enumeration reservation、终态重放、失败 lease 释放和真实双 Service 竞态；
  3. raw/canonical language/token/provider/model/quality/path/symlink provenance。
- Implementer 自报 contracts 50、policy 30、integration 68、全量 234、两项 mypy、
  Ruff、CLI、lock/sync、offline build、包内容与固定 Diff 全 PASS；依赖/锁不变。
- 上述证据仅为 Implementer 自报，不构成独立验收。两个 P2 仍保留：职责/私有 hook
  聚合与嵌套 metadata 资源放大。
- 第三次 Reviewer packet：`agent-prompts/TASK-005-REVIEWER-3-CODEX.md`。
- Reviewer 必须为全新独立 Codex 会话，不得复用 Implementer 或前两个 Reviewer；
  独立复跑 Q1-Q5、R2/R3、AC-1 至 AC-5、ADR-006 T-01 至 T-15 和五轴审查。
- Reviewer 只可追加并提交 source `handoffs/TASK-005.md`，不得修改业务代码、测试、
  fixture、依赖、锁文件、main 或任务状态。
- 任务状态为 `IN_REVIEW`，未 ACCEPTED/DONE；TASK-006/TASK-007 继续
  `BLOCKED/UNASSIGNED`。

## 第三次独立审查结果与 Correction 3

- Review evidence：
  `30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Parent：
  `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Review commit 只修改 `handoffs/TASK-005.md`，source/main 均干净。
- 规定门禁全部通过：focused 50/30/68、全量 234、两项 mypy、Ruff、CLI、
  offline build、包内容、lock/sync 与固定 Diff check。
- Verdict：`REJECT`；P0=0、P1=3、P2=1、P3=0。
- 已独立关闭并须保持回归：Q2 pre-enumeration reservation/CAS、终态重放、lease
  释放和 2 秒恢复；Q4 VTT、HTTPMessage、字段边界、redirect 与安全 options。
- 未关闭/新 P1：
  1. 公开 `SubtitleAdapter` 的敏感 message、错误 stage/video 可穿透 Service；
  2. raw `source_type`/仍可匹配的 `actual_language` 和 canonical
     `ROLLING_CUES_DEDUPED` token 可被自洽篡改后命中并推进；
  3. 500,000 name runs 全量复制后才拒绝，200,000 空 language buckets 绕过
     512-track 上限；原资源 P2 已升级为 P1。
- P2：Service/文件/cache/Provider 状态职责与 integration tests 私有 hook 聚合；
  不单独扩大本轮范围，但不得因 Correction 继续恶化。
- Correction 3 packet：`agent-prompts/TASK-005-CORRECTION-3-CODEX.md`。
- Correction 3 从 `30c6651...` 创建新的非 merge commit，继续由原 Codex
  Implementer 执行；只允许 `transcripts.py`、`providers/subtitles.py`、
  policy/integration tests、subtitle fixtures 与 handoff。
- 不修改 `domain.py`、contracts test、`state.py`、Schema/migration、
  `complete_stage`、配置、CLI、`pyproject.toml` 或 `uv.lock`。若现有字段无法实现
  可信 provenance，必须按 ADR-006 T-13 报 `DECISION NEEDED`，不得自行加 Schema。
- 任务退回 `IN_PROGRESS`。Correction 3 提交前不得启动第四个 Reviewer；TASK-006/
  TASK-007 继续 `BLOCKED/UNASSIGNED`。

## Correction 3 实现证据与第四次审查

- Correction commit：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Parent：`30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Correction 为单一非 merge 后继，精确修改 `transcripts.py`、`providers/subtitles.py`、integration tests 与 handoff 4 个允许文件；完整产品范围仍为原批准的 11 个文件，依赖/锁未变。
- Implementer 记录三个 P1 的 RED/GREEN：Service 对 enumerate/read 公共 Adapter 边界重建安全错误并强制当前 video/stage；verified cache 绑定成功 Provider-call、response Artifact、确定性 key、provenance ID 与 SHA；name runs/buckets 使用流式计数并在第 1001/513 项提前拒绝。
- Implementer 自报 contracts 50、policy 30、integration 77、全量 243、mypy、SQLite wiring、Ruff、CLI、lock/sync、offline build、包内容与固定 Diff 全 PASS；这些结论不构成独立验收。
- 既有 Service/私有 hook 聚合 P2 未宣称关闭；第四次 Reviewer 必须重新判断其严重性，且不得仅按测试数量或行数给出 Verdict。
- 第四次 Reviewer packet：`agent-prompts/TASK-005-REVIEWER-4-CODEX.md`。Reviewer 必须为全新独立 Codex 会话，仅可向 source handoff 追加 evidence，复跑三个 P1 探针、此前 Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15 和五轴审查。
- TASK-005 当前为 `IN_REVIEW`，未 ACCEPTED/DONE；TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`。

## 第四次独立审查结果与主控验收

- Review evidence：`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Parent：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Review commit 只修改 `handoffs/TASK-005.md`，source/main 均干净。
- Reviewer 独立复跑 lock/sync、focused 50/30/77、全量 243、mypy、SQLite wiring、Ruff、CLI、offline build、包内容与固定 Diff，结果全部 PASS。
- P1 probe A 公共 Adapter 边界、B 可信 provenance、C streaming bounds 全部 PASS；此前 Q2/Q4、AC-1 至 AC-5 与 ADR-006 T-01 至 T-15 全部 PASS。
- Verdict：`APPROVE`；P0=0、P1=0、P2=1、P3=0。唯一 P2 为 Service 职责/私有 test hook 聚合，非阻断但必须在交接与发布门禁中保持可见。
- 主控验收为 `ACCEPTED`，仅允许后续 Product Integrator 整合 source evidence；尚未合并或关闭为 DONE。TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`。

## Product Integrator 授权

- 已验收 source evidence 固定为 `d5268ef08b360e932b5dda9d0fb70d71b13587a4`；仅允许无冲突 `--no-ff --no-commit` 合并后重跑受影响离线门禁。
- Integrator 必须验证 first-parent Diff 精确为原批准的 11 个文件、依赖/锁未变、sdist/wheel 包含 migration 与字幕模块，并保留 source 分支/worktree。
- Integrator 不得实现、重审、修复 P2、修改任务状态、push 或清理；合并后状态仍为 `ACCEPTED`，只有独立 closure 同步才可设为 DONE。
- Product Integrator packet：`agent-prompts/TASK-005-INTEGRATOR.md`。TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`。

## 整合结果与关闭

- Merge commit：`cfc302ddc41cd908777f49de292327640b6f8314`
- Merge parents：`1e5e5f8ade1a9566e6ee32b6d720cbcc94f03bc8`、`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Product Integrator 确认 first-parent Diff 精确为批准的 11 个文件，`pyproject.toml`/`uv.lock` 无差异；整合后 lock/sync、focused 50/30/77、全量 243、mypy、SQLite wiring、Ruff、CLI、offline build 与 migration/字幕模块 package inclusion 全 PASS。
- source 分支/worktree 保留且干净；未 push、未清理，无意外文件。TASK-005 关闭为 `DONE`。
- 非阻断 P2（Service 职责/私有 test hook 聚合）、上游字幕 payload 漂移、真实网络/认证/媒体/Vault 未授权和 mutagen 分发许可证门禁继续由后续任务/发布门禁跟踪。TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`，等待 ADR-007 与 TASK-005A。
