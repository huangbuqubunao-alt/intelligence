# TASK-013 rebuild — Product Integrator

你是独立 Codex Product Integrator。只整合已验收的固定 source，并复跑本授权的离线门禁；不得修改产品代码、测试、任务状态或 source，不得修复合并冲突以外的问题。若有冲突、范围扩大、门禁失败、身份/谱系不符或任一工作区不干净，停止并报告；不得推送、rebase、cherry-pick、reset 或清理 source。

## 动态授权与固定对象

- Execution base：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-INTEGRATOR.md` 必须解析为本授权提交；main 中 TASK-013 必须是 `ACCEPTED`。
- Accepted source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@d76307fcde73631931f61493c30c75dbda02f028`，必须干净。
- `d76307fcde73631931f61493c30c75dbda02f028` 是最新 handoff-only Reviewer evidence，唯一父提交精确为 `f6697fa3064c288a7b688d7dd1fdf82f5d3e2c28`，其 Verdict=`APPROVE`、P0–P3=0。
- 禁止访问、修改、清理或复用历史 `/Users/hua/Documents/yia-worktrees/task-013` worktree/branch。

## 固定范围

相对 rebuild base `2a59dfe3860161a5989f2c08161f03c73aa4ca86`，完整允许范围仅为：

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

当前 accepted source 实际修改前两份 E2E、验收报告与 handoff；fixtures 未改。不得修改依赖/锁文件、生产代码、CLI/编排、配置、Schema/migration、测试配置、任务状态或其他任务。Reuse decision=`DIRECT`：既有项目服务、锁定依赖与 Python 标准库；外部边界仅为测试 Fake Adapter，不复制第三方代码或新增依赖。

## 合并、验证与收尾

1. 合并前核验 identity `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、main/source SHA、source evidence 父链、两个工作区清洁、完整范围、锁文件不变与 `git diff --check`。
2. 在 main 使用 `git merge --no-ff d76307fcde73631931f61493c30c75dbda02f028` 创建 merge commit；即使无冲突也必须保留双父 merge。不得预写或修改 TASK-013 状态。
3. 在 merge 结果仅执行以下离线门禁：

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/e2e -m 'not network and not cloud'
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
rg --pcre2 -n '(?i)(sk-[a-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})' tests/e2e docs/ACCEPTANCE_REPORT.md handoffs/TASK-013.md
```

凭据扫描无匹配时 `rg` 的 exit `1` 是通过结果；其余命令必须成功。若构建产生本轮可识别的 `dist/` 忽略文件，只可清理该本轮产物。

4. 合并后验证 merge 恰有两个父，父顺序为 execution base + accepted source；accepted source 成为 main 祖先；first-parent Diff 只在上述五组范围（实际四个路径）且锁文件不变；`git diff --check` 通过，main/source 均干净。

## 资源边界与回传

仅限离线 Fake、pytest 临时 SQLite/DATA/Vault 与锁定依赖。不得运行真实 YouTube/网络/媒体、ffmpeg、Whisper/Ollama/OpenAI 模型或 API、凭据、付费服务、真实 Vault/用户笔记或 launchd。

```text
Task: TASK-013 rebuild
Role: Product Integrator
Execution base: <sha>
Accepted source: d76307fcde73631931f61493c30c75dbda02f028
Merge commit / parents: <sha> / <base>, <source>
Checks: <results>
Post-merge task status: ACCEPTED (not DONE)
Verdict: INTEGRATED | BLOCKED
```
