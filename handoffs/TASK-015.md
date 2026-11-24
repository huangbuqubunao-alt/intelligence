# TASK-015 Handoff

## 状态

`READY_FOR_INDEPENDENT_REVIEW` — 实现和隔离真实 Local Smoke 已完成；未合并或推送。

## 调查结论

- 正式 CLI 默认 `_UnavailableOperations`，真实业务命令必然静默失败。
- 现有 E2E 直接组合服务、手动推进元数据并登记音频，不覆盖 production composition。
- 可直接复用现有服务；缺口是 bootstrap、应用查询、持久 Artifact 恢复、真实 handlers
  与用户反馈。
- 无字幕生产转写仍缺受管媒体/音频获取层；不得用测试 fixture 代替。

## Reuse

`DIRECT`：既有锁定 Provider、Repository、Pipeline、Obsidian、weekly 和标准库。
无新增第三方依赖。

## 验证

### 产品结果

- 正式 CLI 默认构造 `RuntimeOperations`，不再使用不可用占位实现。
- 首个业务命令幂等创建项目内 DATA/logs/SQLite migration 与已存在 Test Vault 根下的
  受管子目录；`doctor` 保持只读并给出逐项人类可读结果。
- `check --limit` 真实读取公开 RSS，并把持久候选严格限制到用户上限。
- `process` 通过 Planner/Orchestrator、真实 yt-dlp 字幕、真实本地 Ollama、Cloud-off
  policy 和 Obsidian sink 完成一条公开视频。
- Cloud 关闭时，视频笔记保留本地评分标签；周报收录成功笔记和 wiki link，但不伪造
  深度分析趋势。
- 无可用字幕且没有受管音频时，明确停止在 transcript prerequisite；未下载约 1.50 GiB
  的固定 Whisper 模型。

### Production Composition Test

`tests/integration/test_runtime_composition.py` 从真实 CLI 默认入口进入 production
composition；只替换 RSS/metadata/subtitle/scoring/cloud 外部边界，不注入 Fake
`Operations`。覆盖首次 bootstrap、只读 doctor、完整字幕到笔记/周报链路，以及无字幕
失败与跨 invocation retry generation。

### 真实隔离 Smoke（2026-08-12）

- Project root：`/tmp/youtube-intel-task015-final`
- Vault：`/Users/developer/Documents/YouTube-Intel-Test-Vault/YouTube Intel TASK-015 Final`
- `doctor` 首次 exit 3：明确报告 DATA/SQLite/受管 Vault 尚未初始化；yt-dlp、MLX
  package、Ollama 与固定 `qwen3:8b` digest 通过；Cloud=OFF。
- `check --channel UCsooa4yRKGN_zEE8iknghZA --limit 1` exit 0，并完成首次 bootstrap。
- `process --video 5ljV0Vxu00M` exit 0；视频 `COMPLETE`、score=9、字幕/转写/评分/
  AnalysisSkipped/笔记 Job 均成功；未读取凭据或调用云端。
- `weekly` exit 0；`Weekly/2026-W33.md` 含 1 条受管视频 wiki link、本地-only 说明和
  空深度趋势说明。
- 笔记包含标题、来源、手工字幕语言、本地评分主题、受保护用户区；日志仅含安全的
  command started/finished 事件。

### 自动化门禁

- `uv lock --check`：PASS，lock 未变化。
- focused：221 passed（最终局部回归另为 17 passed）。
- full pytest：634 passed。
- `mypy src`：27 source files，PASS。
- `ruff check .`：PASS。
- CLI help：PASS。
- `uv build --offline`：sdist/wheel PASS；migration、video/weekly templates、summary/
  scoring prompts 均包含。
- `scripts/security_scan.sh`：clean；project LICENSE 仍为发布级 warning。
- `scripts/backup_recovery_drill.sh`：17 PASS / 1 expected Vault warning / 0 FAIL。
- `git diff --check`：PASS。

## 尚未完成与风险

- 无字幕视频的 production 媒体获取/音频 Artifact 编排尚未实现；这是明确的功能限制，
  不是静默降级。固定 Whisper 权重未下载。
- 某些公开自动字幕目录会因 yt-dlp 翻译展开超过 512 条安全上限而 fail-closed；未放宽
  安全上限或使用 Cookie/认证。
- Cloud 深度分析未运行；真实用户 Vault、用户笔记、凭据和付费 API 均未接触。
- 外部 Provider 成功与 SQLite 提交之间仍是既有 at-most-once best-effort 风险。
- 项目 LICENSE、mutagen GPL 与 tokenizer NOTICE 仍阻断公开分发；本任务只证明本地
  Demo，不构成 release Go。
