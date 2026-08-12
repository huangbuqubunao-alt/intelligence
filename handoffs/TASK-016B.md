# TASK-016B 交接报告

## 元数据

- Task: `TASK-016B`
- Role: `Implementer`
- Agent/session: `Codex primary`
- Base branch/commit: `main@60551f2b8606e50ed8e4bd8d161ac5636a8a9266`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016b-scoring-output-language`
- Branch: `codex/task-016b-scoring-output-language`
- Head commit: `本实现提交（SHA 见最终 Implementation Report）`
- Started: `2026-08-13`
- Reported: `2026-08-13`

## 目标与范围

- 任务目标：让 Local Scoring 的用户可见 `ScoreResult.reason` 遵守
  `general.output_language`，并将语言纳入输入、Prompt、缓存身份、结构化结果与
  持久恢复 provenance。
- 允许修改：评分领域契约、评分服务、Ollama Adapter、Runtime provenance、固定
  Prompt、相关文档、任务卡、handoff 与测试。
- 实际修改：新增 `zh-CN | en` 可信语言字段；Prompt/Schema/Artifact producer 升为
  v2；加入保守错语种校验和既有一次 repair；跨语言缓存、旧 Artifact 与当前配置
  不匹配时 fail-closed。
- 明确未做：未实现或启动 TASK-016C；未实现 Deep Analysis、Knowledge Provider、
  Hybrid/Cloud Router、Note/Weekly V2、UI、migration 或 TASK-015 Remaining P2。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1：中文/英文理由遵守配置 | PASS | Prompt 指令、`ScoreResult.output_language`、保守语言校验及双向 repair 测试 |
| AC-2：语言进入缓存与持久身份 | PASS | `ScoringInput`、normalized input hash、结构化 Artifact、Runtime/current-config provenance 与跨语言缓存测试 |
| AC-3：旧缓存和错语言 fail-closed | PASS | v2 版本隔离、缺少/篡改语言的 provenance 回归、错误语言不写缓存 |
| AC-4：真实 Local-only smoke | PASS | 固定视频 `5ljV0Vxu00M`、`qwen3:8b`、`zh-CN` 返回中文 reason；无 Deep Analysis、Cloud、DB 或 Vault |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| TDD RED | PASS | 新语言契约初始 `5 failed, 2 passed`，证明字段、参数与验证缺失 |
| Focused pytest | PASS | `185 passed` |
| `uv lock --check`（sync 前后） | PASS | `84 packages`，锁文件未变 |
| `uv sync --locked --offline` | PASS | `61 packages` checked，无下载 |
| `uv run pytest -x -q` | PASS | `704 passed in 35.15s` |
| `uv run mypy src` | PASS | `27 source files` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run youtube-intel --help` | PASS | CLI help 正常，仅帮助命令 |
| `uv build --offline` | PASS | sdist/wheel 成功，wheel 内含 `scoring-prompt-v2` |
| `bash scripts/security_scan.sh` | PASS | `status=clean`；既有 WARN 不阻断 |
| `git diff --check` | PASS | 无 whitespace error |

## Real Local Scoring Smoke

- 视频：`5ljV0Vxu00M`
- 输出语言：`zh-CN`
- Provider / model：`ollama / qwen3:8b`
- Contract：`scoring-prompt-v2 / score-result-v2`
- 真实 scoring reason：`该视频详细解释了国际空间站如何维持氧气供应，涉及电解水制氧、气体分离技术以及未来可能的磁流体制氧方法（MOGA），内容科学严谨，具有较高的学习价值和产品应用价值。视频通过实际案例和未来技术展望，激发了观众对航天工程的兴趣，同时提供了实用知识。`
- 隔离边界：使用公开 metadata/一条公开字幕与 loopback Ollama；未读取项目配置或
  Key，未写数据库、Vault，未调用 Cloud，未继续 Deep Analysis。

## Diff 复核

- 修改文件：评分契约/服务/Adapter/Runtime、双份固定 Prompt、System Design、任务
  卡/索引/handoff，以及直接受字段升级影响的 scoring/runtime/note/weekly/E2E 测试。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否；`dist/` 与 `.venv/` 为 ignored 本地门禁产物，
  未纳入提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：新增契约的预期 RED；字段升级后旧测试夹具缺少语言的 7 个回归；4 个
  Ruff import-order 问题。均经对应测试和全量门禁复核。
- 辅助检查：首次 wheel Prompt 核验误用不可用的系统 `python`，随后仅以锁定环境的
  `uv run python` 重跑并通过；正式安全扫描在此前已经独立返回 `status=clean`。
- 跳过检查及原因：未运行真实 Cloud/Deep Analysis/真实 Vault，均不在 TASK-016B
  范围且未获授权。
- 剩余风险：语言校验是刻意保守的明显错语种拦截，不是通用自然语言识别器；真实 smoke
  仅证明固定视频与本机 `qwen3:8b` 的 Local Scoring，不代表 TASK-016C 或生产发布。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`见最终 Implementation Report`
- 复现/验证说明：使用上述 Full Gates；真实 smoke 只允许固定视频、本地模型和评分
  reason，不得扩展到 Deep Analysis。

## Final Correction Round 2（2026-08-13）

### Root cause 与修复

- P1-1：旧启发式只检查目标字符是否出现，单个汉字可掩盖英文主体，且小写技术词会
  被误当英文自然语言。现先剥离固定技术词，再分别要求最小汉字主体或英文自然语言
  主体；不使用字符比例，单字符和纯技术词均不能通过，中文技术混排与英文中的短中文
  专名仍保留。
- P1-2：Pydantic 的 deprecated `copy(update=...)` 和 `model_construct()` 可生成
  未重验实例。新增单一 `validate_score_result()` / JSON 入口，把模型实例重新转为
  data 后执行完整 schema + language validators；内存 Cache、Provider/repair、
  Artifact 写入、stage completion 与 Runtime persisted load 均接入可信入口。
- P1-3：Repository cache 只校验 request/provider/model/language，未同时绑定
  `prompt_version` 与 `schema_version`。现 Result 与 ProviderCall 都必须匹配当前
  request 的 request hash、provider、model、output language、prompt 与 schema；
  任一错配均不得返回 `PERSISTED_CACHE_HIT`。

### 对抗与 provenance 证据

- 真实 Ollama Fake-transport 路径覆盖 `zh-CN` 英文主体加单字绕过，以及 `en` 中文
  主体加小写 `api/sdk/llm` 绕过；均进入一次 repair，修复后仍错误则 fail-closed。
- Domain 覆盖短单字、纯技术词、中文+英文技术词、英文主体和英文+中文专名。
- `copy(update=...)`、`model_construct()`、Provider 返回与内存 Cache 注入均在
  trusted boundary 重新验证，不会持久化或返回为有效结果。
- SQLite repository-backed 恢复矩阵分别篡改 Result 的六项 provenance，以及
  ProviderCall 的 prompt/schema version；Provider 调用计数保持 1，证明没有把错版
  Artifact 当作 persisted cache hit。

### Final gates

- Focused contracts/runtime/provider/provenance/weekly：`248 passed`；周报安全与
  Unicode 回归单独为 `41 passed`。
- Full pytest：`729 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS，锁文件未变且无下载。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS，sdist/wheel 成功。
- `git diff --check`：PASS。
- 本轮未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge 或 push。

## Reviewer 结论

- Reviewer agent/session：
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## Final Correction Round 3（2026-08-13）

### Root cause

- P1-1：Round 2 仍把整段文本压平成英文词计数；中文主体后追加若干英文词即可达到
  阈值，无法表达用户真正看到的首个自然语言主体。
- P1-3：SQLite 中成功的 `ProviderCall` 与 Artifact key 都是不可原位覆盖的审计
  记录。旧实现把 prompt/schema provenance mismatch 当作持久化错误，没有把它解释
  为可重算的 cache miss。

### Fixes 与对抗证据

- 语言校验先按换行及中英文句末符切分，再剥离固定技术词；逐段寻找首个可辨识自然
  语言主体。英文主体由谓词/关系结构识别，不再使用固定英文词数或字符比例；单汉字、
  技术缩写及无谓词英文尾巴都不能改变主体语言。
- Domain 与真实 Ollama Fake transport 的 primary/一次 repair/fail-closed 路径覆盖：
  `en` 中文主体加英文短尾、`zh-CN` 英文主体加中文短尾均拒绝；中文主体混排
  API/SDK/LLM/MLX 与英文主体混排 API/SDK/LLM 均通过。
- prompt/schema 版本失配现在建立确定性的 `scoring-cache-recompute-v1` 请求身份，
  调用 Provider 重新计算并写入新的 ProviderCall 与 raw/structured Artifact；旧
  ProviderCall、Artifact 记录和文件均保留。第三次相同恢复命中新可信缓存，不会反复
  调用 Provider。
- SQLite 对抗测试分别覆盖 Result Artifact 与 ProviderCall 的 wrong
  `prompt_version` / `schema_version`：Provider 调用由 1 增至 2、ProviderCall 表由
  1 增至 2、新 Artifact ID/路径生成，旧审计证据不变；request/provider/model/
  output_language 的非版本篡改仍保持 fail-closed，未削弱原有边界。

### Final gates

- TDD RED：`7 failed, 15 passed`，分别证明语言绕过仍被接受、版本失配仍直接失败。
- Focused scoring/domain/Ollama/repository：`71 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS（84 resolved / 61 checked，
  无下载，锁文件未变）。
- Full pytest：`734 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge 或 push。

### Round 3 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 Final Correction Round 3 Report。

## 主控验收

- Orchestrator：
- Verdict：`ACCEPT | REJECT`
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：`DONE | BLOCKED`
