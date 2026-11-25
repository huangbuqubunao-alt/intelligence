# 独立整改与集成验收断点检查点（Remediation Checkpoint）

> 主线规格：`docs/validation/ux-redesign-2026-11-25/04_INDEPENDENT_CODE_REVIEW_AND_AGY_REMEDIATION.md`  
> 当前分支：`antigravity/remediation-20261125`（从 `origin/main@d1b58f73` 线性创建）  
> 候选基准：`beea3a53`（完整线性重放 `5cc76ab8..9cee10df`，共 16 个提交；`HEAD^{tree} == 9cee10df^{tree}` 已验证）  
> 检查点状态：Batch D（Gates U1/U2：`P1-05`, `P2-04`, `P2-05`, TOP 1–3）已完成并通过验证，正在进入 Phase 3（Gates E1/E2/R1：全量自动化回归 + 实机浏览器验收 + 终审报告与推送）

## 1. Phase 0 / Gate M1 验证结论

| 检查项 | 实测命令 / 结果 | 结论 |
|---|---|---|
| `origin/main` 与 `5cc76ab8` tree 等价性 | `git diff --stat origin/main 5cc76ab8` 为空（共同 tree `5953e737`） | ✅ 可线性重放，无需产生历史无意义合并冲突 |
| 线性祖先校验 | `git merge-base --is-ancestor origin/main HEAD` 返回 `0` (`ANCESTOR_OK`) | ✅ `P1-07`（拓扑线性化）已闭环 |
| 内容等价校验 | `HEAD^{tree} == 9cee10df^{tree}` (`TREE_PARITY_OK`) | ✅ 与评审提交树逐字节一致 |
| 独立工作区导入隔离 | `.venv/bin/python -c "import youtube_intel; print(youtube_intel.__file__)"` 指向 `remediation-20261125/src/youtube_intel/__init__.py` | ✅ 无跨 worktree 污染 |

## 2. 独立复核清单（Phase 0 源码复核结果）

| ID | 优先级 | 复核状态 | 核心根因核实 |
|---|---|---|---|
| `P1-01` | P1 | CONFIRMED | `fast_read_api.backup_download` 与 `/api/*` 读取路径缺少统一 loopback `Host` 允许列表与 `Sec-Fetch-Site: cross-site` 拦截；`local_api._send` 缺少 `Cross-Origin-Resource-Policy: same-origin` |
| `P1-02` | P1 | CONFIRMED | `fast_read_api._resolve_local_media_file` 接受未知 `storage_root` 回退且返回裸 `Path`，导致 `_send_file` 调用 `open_managed(path.parent, path.name)` 而跳过根祖先符号链接遍历与资产 SHA-256 校验 |
| `P1-03` | P1 | CONFIRMED | `workspace_intelligence_hub._prune_ungrounded_ref_clauses` 仅校验 `[E1]` 引用存在与子句非空，未对数字/百分比/货币/年份/数量与否定极性做基于引用片段的一致性核验 |
| `P1-04` | P1 | CONFIRMED | `youtube_auth_fallback.can_attempt()` 仅在持锁检查后释放锁再执行网络拉取与 `_record_usage()`，多实例/并发请求存在最后配额与冷却槽位竞态 |
| `P1-05` | P1 | CONFIRMED | `App.tsx` 中 `.reader-ref-drawer` 关闭态仍保留在无障碍树与 Tab 焦点链中，缺少 `inert`、`tabIndex={-1}`、`role="dialog" aria-modal="true"`、焦点循环与关闭回焦 |
| `P1-06` | P1 | CONFIRMED | `local_api._send_bytes` 在 `HEAD` 请求仍写响应体；`_handle` 吞掉发送前异常且未区分发送前后错误状态码 |
| `P1-07` | P1 | FIXED_IN_M1 | 已基于 `origin/main@d1b58f73` 创建线性分支 `antigravity/remediation-20261125` 并完成无冲突重放 |
| `P2-01` | P2 | CONFIRMED | `local_api._parse_byte_range` 使用 `int()`（允许 `+4`），且遇到逗号分隔多区间时静默回退 `None` 而非规范处理 |
| `P2-02` | P2 | CONFIRMED | `youtube_auth_fallback.validate_netscape_cookies_txt` 域名后缀校验过宽，且保留未过滤的第三方非 YouTube/Google Cookie 行 |
| `P2-03` | P2 | CONFIRMED | `_build_research_scope_options` 统计本地/B 站资料未校验 `verify_source`，UI 误标为「全库可核验资料」 |
| `P2-04` | P2 | CONFIRMED | `ContentDetailPanel` 本地媒体加载失败未按 `MediaError.code` 区分清晰原因与一键重试恢复动作 |
| `P2-05` | P2 | CONFIRMED | `ContentDetailPanel` 在 `App.tsx` 中超过 1,200 行，需拆出 `ReaderMediaStage.tsx` 与 `ReaderReferenceDrawer.tsx` |

## 3. 批次进度

- 已完成：
  - `Phase 0 / Gate M1`（`75da5130`）：基于 `origin/main@d1b58f73` 创建线性分支 `antigravity/remediation-20261125` 并完成树等价重放（闭合 `P1-07` 拓扑要求）。
  - `Batch A / Gate S1`（`P1-01`, `P1-02`, `P1-06`, `P2-01`）：
    - `local_api.py`：统一全站与 `/api/*` loopback `Host` 允许列表（含 `[::1]`、`localhost`、`127.0.0.1` 动态端口及桌面桥 `origins`）、拦截跨站 `Sec-Fetch-Site` 与非本机 `Origin`、为 `/api/*` 响应统一附加 `Cross-Origin-Resource-Policy: same-origin`、`do_HEAD` 统一接入 `_handle` 且 `_send_bytes` / `416` 对 `HEAD` 严格零正文、严格 RFC 9110 ASCII `Range` 解析（拒绝 `+4`/Unicode 数字/空格/多区间 `416`）、`_send_file` 区分发送前 `404`/`409`/`413` 与发送后安全断流及脱敏 warning 日志。
    - `source_authority.py` + `fast_read_api.py`：新增 `ManagedMediaFile` 保留 `(root, relative_path, expected_size, expected_sha256, expected_stat)` 进入 `open_managed` 逐级 `O_NOFOLLOW` 校验，严格限制 `storage_root in {'SOURCE_DATA', 'DATA'}`，并建立基于不变 `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` 的 bounded SHA-256 校验缓存。
    - 实测命令：`.venv/bin/pytest -q tests/integration/test_local_video_post_import_resilience.py tests/integration/test_local_content_adversarial.py tests/integration/test_dogfood_day2_native_import.py tests/unit/test_bigmodel_settings.py tests/unit/test_qa_launch_isolation.py` → `149 passed in 115.81s`；`ruff check` → `All checks passed!`。
  - `Batch B / Gate S2`（`P1-04`, `P2-02`）：
    - `youtube_auth_fallback.py`：新增 SQLite `BEGIN IMMEDIATE` 原子预留 `_reserve_attempt_slot`（写入 `'RESERVED'` 并在异常/中断下保守占用当日配额与冷却时间）及 `_finalize_attempt_slot`（按 `usage_id` 结算结果并跨实例持久化 30 分钟熔断），彻底消除跨线程/跨服务实例竞态；收紧 `validate_netscape_cookies_txt` 为严格 DNS 子域边界校验并主动剥离非 `youtube.com`/`youtu.be`/`google.com`/`googlevideo.com`/`ytimg.com` 第三方 Cookie 行。
    - `tests/unit/test_manual_ux_remediation.py`：新增跨实例并发 Barrier 抢占测试、异常中止保守扣额测试、误导域名/无关站点过滤测试及假凭据（status/SQLite/backup/日志）零泄漏测试。
    - 实测命令：`.venv/bin/pytest -q tests/unit/test_manual_ux_remediation.py` → `9 passed in 6.41s`；`ruff check` → `All checks passed!`。
  - `Batch C / Gate S3`（`P1-03`, `P2-03`）：
    - `workspace_intelligence_hub.py`：新增 `_check_clause_against_cited_evidence` 确定性数字/百分比/货币/年份/中阿拉伯等价数量词及分句级否定极性一致性校验，统一覆盖实时问答 `ask_research_question`、历史会话重读 `_row_to_research_session_dto`、备份恢复 `restore_research_backup` 与 Obsidian ZIP 导出，发现矛盾时拒绝或降级并暴露 `CITATION_FACT_CONFLICT` 受控拒答码；同时为 `_build_research_scope_options` 补充受管快照 `verify_source` 门禁。
    - `WorkspaceAiWidgets.tsx`：将 Research 范围条文案修正为「候选资料 N 篇（提问时将实时核验原文）」，并在问答头补充「有效引用 / 覆盖来源」事实计数标签。
    - 实测命令：`.venv/bin/python -m pytest -q tests/integration/test_codex_round3_remediation.py tests/integration/test_workspace_intelligence_hub.py` → `30 passed in 78.15s`；`ruff check` → `All checks passed!`；`npx tsc --noEmit && npx vitest run --minWorkers=1 --maxWorkers=1 src/workspace/CodexReviewRemediation.test.tsx src/workspace/ManualUxRemediation.test.tsx` → `23 passed in 13.58s`。
  - `Batch D / Gates U1 & U2`（`P1-05`, `P2-04`, `P2-05`, TOP 1–3）：
    - 模块拆分：`ReaderMediaStage.tsx`（含 `MediaError.code` 1–4 分类诊断与 1-click 重试）、`ReaderReferenceDrawer.tsx`（关闭态 `inert` + `tabIndex=-1`、开启态 `role="dialog" aria-modal="true"` 焦点引入与 `Tab`/`Shift+Tab` 环绕、关闭焦点还原、`role="tablist"`/`tab`/`tabpanel` 与键盘导航）、`ReaderRecoveryPanel.tsx`（`InlineYouTubeAuthRecovery` 明确授权页内同意/取消及立即重试，消除跳设置死循环）。
    - 产品润色：`AiScoreBadge` 增加「排序分 · 非事实核验」提示语义（TOP 2）。
    - 实测命令：`cd frontend && npx tsc --noEmit && npm run build && npx vitest run --minWorkers=1 --maxWorkers=1 src/workspace/ManualUxRemediation.test.tsx src/workspace/App.test.tsx src/workspace/GroundingAndRecovery.test.tsx src/workspace/OssUiSystem.test.tsx` → `202 passed in 22.94s`（vite 生产构建 977ms/1.17s 通过）。
- 待执行：`Phase 3 (E1/E2/R1)`
- 下一步动作：运行全量 Python `pytest` 与全量串行 Vitest + `ruff` + `git diff --check`（Gate E1），启动双端实例完成实机 Chromium 无障碍与多媒体验收（Gate E2），输出最终验收报告并推送分支。
