# MVP 离线验收报告

- Task: `TASK-013`
- Evidence mode: 固定夹具、pytest 临时 SQLite/DATA/Vault、Fake 外部 Adapter
- Real-resource status: `NOT AUTHORIZED`

## 可复现命令

```bash
uv run python -m pytest tests/e2e -m 'not network and not cloud'
uv run python -m pytest tests/e2e/test_mvp_flow.py
uv run python -m pytest tests/e2e/test_failure_recovery.py
```

测试不访问网络、真实 YouTube、Whisper/ffmpeg、Ollama、OpenAI、真实密钥或真实 Vault。
临时 Vault、SQLite、DATA 与所有伪造音频均由 pytest `tmp_path` 创建并在测试结束后清理。

## PRD 10 验收矩阵

| PRD 项 | 结果 | 离线证据 |
|---|---|---|
| 10.1 五类样例 | PASS | `test_mvp_service_flow_covers_five_user_scenarios_and_is_idempotent` 经 `SubtitleAcquisitionService` 覆盖人工/自动字幕，经 `LocalTranscriptionService` 覆盖无字幕转写；另有低价值与高价值视频。 |
| 10.2 重复运行无重复 | PASS | 首次完整服务流后销毁全部组合对象；同一 SQLite/DATA/Vault 上新建组合重跑和重建周报，Provider-call、Artifact、Report、Job 总数和周报字节均不变。 |
| 10.3 分阶段失败恢复 | PASS | `test_service_boundary_failures_recover_without_duplicate_outputs` 分别在字幕、转写、评分、分析、笔记、周报边界注入一次失败；重跑恢复，随后再次运行不新增输出。 |
| 10.4 云关闭仍可完成本地流程 | PASS | `test_cloud_disabled_keeps_the_offline_flow_complete_without_cloud_side_effects` 断言高价值流程完成、Fake 云 Provider 与凭据解析器均为零调用。 |
| 10.5 重启恢复不重复昂贵步骤 | PASS | `test_mvp_service_flow_covers_five_user_scenarios_and_is_idempotent` 在首次完整服务流后删除 `_OfflineMvpFlow`、Repository、Fake Provider 和内存缓存并执行 `gc.collect()`；它仅用相同 pytest SQLite/DATA/Vault 重建第二套完整组合。第二套组合的缓存初始为空，重跑由持久 Artifact、Provider-call、Job/Pipeline 和 Vault 文件驱动，所有新 Fake 的字幕、Whisper、评分、分析与凭据调用均为 `0`，且不会新增 Artifact、Provider-call、笔记或周报。 |
| 10.6 质量门禁 | PASS | e2e 9 passed；全量 pytest、mypy、Ruff、CLI help、锁检查与离线构建见交接报告。 |
| 10.7 无真实密钥/敏感内容 | PASS | 见本报告的凭据扫描；所有凭据值为固定 `offline-test-credential`，只在 Fake Adapter 内存中使用。 |
| 10.8 笔记可见性和用户区 | PASS | 临时 Vault 验证 Frontmatter 的 `video_id`、周报双链与 `我的思考` 原始用户内容保留。 |

## 用户可见结果

- 低价值视频完成到 `COMPLETE`，不调用云分析或凭据解析。
- 高价值视频经离线 Fake 分析生成 Videos 笔记；周报稳定写入 `Weekly/YYYY-Www.md`。
- 人工、自动与 Whisper 规范文本都由生产字幕/转写服务保存并供评分服务消费。
- 重建的第二套组合从同一持久 SQLite、DATA 和临时 Vault 恢复；其新建内存缓存为空，依然保留既有 Artifact、Provider-call、Job/Pipeline 与用户可见笔记/周报，且不调用昂贵 Fake。
- 已登记 NoteRef 的内容哈希遭用户编辑后，周报服务会 fail-closed；本验收先完成周报幂等验证，再验证笔记服务保留 `我的思考`。这是用户编辑完整性保护，不表述为周报可忽略内容变更。

## 真实环境状态

以下均为 `NOT AUTHORIZED`，未执行，也不由本报告的离线证据替代：真实 YouTube/频道、网络、媒体下载、ffmpeg、Whisper 模型加载、Ollama/模型、OpenAI/API/密钥/付费调用、真实 Vault/用户笔记与 launchd。

## 凭据扫描

执行：

```bash
rg --pcre2 -n '(?i)(sk-[a-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})' \
  tests/e2e docs/ACCEPTANCE_REPORT.md handoffs/TASK-013.md
```

结果：无匹配（退出码 `1`，表示未发现该两类常见真实密钥格式）。

## 剩余风险

- 离线 Fake 只能证明服务边界、状态恢复和用户可见文件语义；不能证明真实 Provider、网络、模型质量或资源占用。
- 用户编辑后应通过后续已批准的 NoteRef/周报刷新策略更新可信哈希；当前周报故意拒绝陈旧哈希。
