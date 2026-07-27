# TASK-014B0 — Codex Product Integrator（受限公开字幕 smoke 入口）

你是 TASK-014B0 的唯一 Codex Product Integrator。本授权包只登记未来整合的边界；它本身不启动 Integrator。开始前完整
阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、
`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、
`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、ADR-013、全部 B0 Implementer/Reviewer 包、source
`handoffs/TASK-014B0.md` 与本包。如任一文件冲突，停止并报告。

## 固定整合对象

```text
Task: TASK-014B0 — Restricted public subtitle smoke entry
Role: Product Integrator
Agent: Codex
Main integration base: main@79dabb5ab0595d2146bed186388997c0907da5e1
Only accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Source branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Accepted source/review evidence: 010fb7faf6280cd83350315ba66f70b5e785b41f
Required sole parent of evidence: b7cb846e650eb02b64321ef566991123d319f310
Required complete B0 source range: c62310ab79f01f5f311c9f54bb28365905f5a81a...010fb7faf6280cd83350315ba66f70b5e785b41f
Required merge: git merge --no-ff 010fb7faf6280cd83350315ba66f70b5e785b41f
Reuse decision: DIRECT — integrate the accepted locked argparse/smoke composition, adapters, SQLite migration, JsonlLogger, Python standard library and offline Fake evidence; do not add or copy third-party code
```

## 整合前门禁

在 main 和 source 都清洁时，确认 accepted source/父链、Reviewer `APPROVE`、P0–P3 均无。`c62310…...010fb7…` 的完整 B0
范围必须严格且仅为：

1. `docs/operations.md`
2. `handoffs/TASK-014B0.md`
3. `src/youtube_intel/cli.py`
4. `src/youtube_intel/public_subtitle_smoke.py`
5. `tests/integration/test_operations.py`
6. `tests/integration/test_public_subtitle_smoke.py`

确认没有 `pyproject.toml`、`uv.lock`、Schema/migration、`state.py`、domain/config、Provider Adapter、任务/状态控制面、
LICENSE、B-1 evidence 或其他路径改动。范围、父链、审查结论或清洁度任一不符则停止，不自行修复、rebase 或扩大范围。

## 唯一授权的整合与检查

仅在上述门禁通过后，使用固定 accepted source 做一次 `--no-ff` 合并。合并后只允许以下离线检查；若任一命令需要网络、
真实资源或未缓存依赖，停止并保留证据：

```text
uv run --offline python -m pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
uv run --offline python -m pytest
uv run --offline mypy src
uv run --offline ruff check .
uv run --offline python -m youtube_intel --help
uv build --offline
git diff --check
git status --short
```

还必须核验 merge 为双父、第二父是 accepted source、first-parent Diff 严格为六条完整 B0 路径且无依赖/Schema 变化。
记录每项结果，但不要修改 source handoff、任务状态或其他控制面；整合后 B0 仍由主控后续同步状态，不能自行标 `DONE`。

## 严禁事项

- 不运行真实网络、YouTube、B-1 smoke、真实 Vault/用户数据、Cookie/登录/API key/凭据。
- 不下载媒体，不调用 ffmpeg、Whisper、模型、Ollama、OpenAI、付费服务或 launchd。
- 不 push、rebase、reset、清理或删除 accepted source/worktree；除指定 `--no-ff` merge 外，不改依赖、锁文件、Schema/
  migration、项目 LICENSE 或产品代码。
- 不将离线测试/审查/整合写成真实 smoke、发布批准、法律结论、严格 exactly-once 证明、风险接受或 TASK-014 Go/No-Go。
