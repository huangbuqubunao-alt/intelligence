# TASK-016 交接报告

## 元数据

- Task: `TASK-016` deterministic local model qualification protocol
- Role: Implementer
- Agent/session: Codex
- Base branch/commit: `main@1d8caf39630b1af4fe47212121cf9fc9b9694ab4`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-main-integration`
- Branch: `main`
- Head commit: pending final evidence commit
- Started: 2026-08-28
- Reported: 2026-08-28

## 目标与范围

- 任务目标：按用户固定顺序和固定门禁机械执行本地模型资格测试；不作推荐或实现。
- 允许修改：`docs/TASK-016-LOCAL-DEEP-ANALYSIS-DETERMINISTIC-MODEL-QUALIFICATION.md` 与本交接报告。
- 实际修改：新增资格矩阵和本报告；C3 的 Ollama artifact acquisition 发生在用户授权的本地 Ollama 存储中，不属于仓库文件。
- 明确未做：未修改 `src/`、`tests/`、migration、`pyproject.toml`、`uv.lock`、配置、真实 Vault 或任务状态；未重测 Qwen3/Qwen2.5；未实现 TASK-016D/E/F；未 push、merge、tag、rebase 或修复模型输出。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 固定候选顺序 | PASS | C1 → C2 → C3 → C4；详见资格矩阵。 |
| C1 A2 | BLOCKED | Gemma upstream tokenizer access is gated; local metadata also declares automatic BOS. No generation sent. |
| C2 Phase A | FAIL | 3/3 raw parity passed; the sole TINY raw response failed strict whole-document JSON. |
| C3 A2 | BLOCKED | One authorized direct acquisition completed, but Meta upstream tokenizer access is manual-gated. No generation sent. |
| C4 acquisition | BLOCKED | One listed-tag direct pull returned `pull model manifest: file does not exist`; one-pull limit precluded a second corrected-tag pull. |
| Final rule | PASS | All four predefined candidates were mechanically exhausted; `QUALIFIED_LOCAL_MODEL=NONE`. |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `git branch --show-current; git rev-parse HEAD; git status --short` | PASS | Initial preflight: `main`, expected `1d8caf…`, clean. |
| C2 three raw `/api/generate` parity probes | PASS | Exact application/Ollama counts: `4/4`, `11/11`, `36/36`. |
| C2 single TINY raw `/api/generate` | FAIL | HTTP 200 and `1186/1186` parity, then strict parser: `JSONDecodeError: Expecting ',' delimiter: line 2 column 407 (char 408)`. |
| C3 one direct no-proxy `ollama pull llama3.1:8b` | PASS | Exact acquired digest `sha256:46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`. |
| C4 one direct no-proxy listed-tag pull | BLOCKED | `Error: pull model manifest: file does not exist`. |
| `git diff --check` | pending | Run immediately before final commit. |

## Diff 复核

- 修改文件：资格证据 Markdown 与本交接报告。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。临时 tokenizer/capture files remain under `/tmp`; one local model acquisition was explicitly authorized by the protocol and was not added to the repository.

## 失败、跳过与风险

- 已解决失败：无；本任务记录机械门禁结果，而非修复模型行为。
- 跳过检查及原因：无代码改动，未运行不相关的 product test/type/lint suite。
- 剩余风险：C1/C3 are tokenizer-proof blocks; C4 is an acquisition block under the one-pull rule. These are protocol outcomes, not model-quality findings.
- `DECISION NEEDED`：None.

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：pending final evidence commit
- 复现/验证说明：按 `docs/TASK-016-LOCAL-DEEP-ANALYSIS-DETERMINISTIC-MODEL-QUALIFICATION.md` 的 matrix、request hashes and `/tmp/task016-c2-phi4-mini-phase-a/` durable capture paths.
