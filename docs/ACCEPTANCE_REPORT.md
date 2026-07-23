# TASK-013 MVP 验收报告

- 范围：固定夹具、现有 Fake/服务和 pytest 临时 SQLite/data/Vault 目录的离线服务组合。
- 非范围：真实 CLI、YouTube、Whisper/ffmpeg、Ollama、OpenAI/API/密钥、网络、真实 Vault 和 launchd。
- 真实冒烟：`NOT AUTHORIZED`；未执行，也未写入真实资源。

## PRD §10 验收矩阵

| 条目 | 状态 | 离线证据 |
|---|---|---|
| 1. 五个样例 | PASS | `tests/e2e/test_mvp_flow.py` 的固定 `mvp_scenarios.json` 覆盖人工、自动、Whisper、低价值和高价值。 |
| 2. 连续两次无重复 | PASS | 同一测试断言 SQLite 行数、阶段调用、笔记和周报在第二次运行后不变。 |
| 3. 分阶段失败恢复 | PASS | `tests/e2e/test_failure_recovery.py` 注入字幕、Whisper、评分、云分析与笔记写入失败，并验证仅失败阶段重试。 |
| 4. 云关闭/低价值本地产物 | PASS | 低价值固定情形断言云分析调用为零并完成本地流程。 |
| 5. 恢复不重复昂贵步骤 | PASS | 恢复测试逐阶段断言先前成功阶段调用次数保持为一。 |
| 6. 质量门禁 | PASS | `uv lock --check`、locked offline sync、E2E（6）、全量 pytest（427）、mypy、Ruff、CLI help 和 offline build 均通过；详情见交接报告。 |
| 7. 无真实密钥或日志正文 | PASS | 夹具仅含合成数据；测试阻断网络，所有路径位于 pytest 临时目录。仓库扫描属于质量门禁。 |
| 8. Frontmatter、双链与用户区 | PASS | E2E 测试解析高价值笔记 Frontmatter、核对周报双链并验证 `我的思考` 保留。 |

## 资源与风险

- 每个测试只使用 `tmp_path` 下的 SQLite、`data` 和 `vault`；不读取用户 Vault 或环境凭据。
- 固定来源、评分和分析结果只是离线 Fake 证据，不代表真实 Provider 或生产 CLI 冒烟。
- 真实冒烟仍需单独授权、脱敏结果、清理方法和剩余风险记录。

## 执行结果

- `uv lock --check`：PASS。
- `uv sync --locked --offline`：PASS；未联网下载。
- `uv run python -m pytest tests/e2e -m 'not network and not cloud'`：PASS（6 passed）。
- `uv run python -m pytest`：PASS（427 passed）。
- `uv run mypy src` 与 `uv run ruff check .`：PASS。
- `uv run python -m youtube_intel --help` 与 `uv build --offline`：PASS。
- `git diff --check 9462b6a162a1e9a738b4073fa5e8b2252101f6af...HEAD`：PASS；最终 staged diff 也会在提交前复核。
