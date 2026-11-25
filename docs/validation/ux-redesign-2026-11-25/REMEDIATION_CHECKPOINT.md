# 独立整改与集成验收断点检查点（Remediation Checkpoint）

> 主线规格：`docs/validation/ux-redesign-2026-11-25/04_INDEPENDENT_CODE_REVIEW_AND_AGY_REMEDIATION.md`
> 当前分支：`antigravity/remediation-20261125`（从 `origin/main@d1b58f73` 线性创建）
> 候选基准：`beea3a53`（完整线性重放 `5cc76ab8..9cee10df`，共 16 个提交；`HEAD^{tree} == 9cee10df^{tree}` 已验证）
> 已验证代码基准（VERIFIED_CODE_SHA）：`913b2c06030caf7fa9a69e5f07737cc5269e57f2`（短哈希 `913b2c06`）
> 检查点状态：**COMPLETED** — Phase 0 ~ Phase 3（全部 9 道验收门禁 `M1, S1, S2, S3, U1, U2, E1, E2, R1`）已全部闭环验证并交付最终验收报告 [05_INTEGRATION_REMEDIATION_ACCEPTANCE_REPORT.md](./05_INTEGRATION_REMEDIATION_ACCEPTANCE_REPORT.md)

## 1. Phase 0 / Gate M1 验证结论

| 检查项 | 实测命令 / 结果 | 结论 |
|---|---|---|
| `origin/main` 与 `5cc76ab8` tree 等价性 | `git diff --stat origin/main 5cc76ab8` 为空（共同 tree `5953e737`） | ✅ 可线性重放，无需产生历史无意义合并冲突 |
| 线性祖先校验 | `git merge-base --is-ancestor origin/main 913b2c06` 返回 `0` (`ANCESTOR_OK`) | ✅ `P1-07`（拓扑线性化）已闭环 |
| 内容等价校验 | `beea3a53^{tree} == 9cee10df^{tree}` (`TREE_PARITY_OK`) | ✅ 与评审提交树逐字节一致 |
| 独立工作区导入隔离 | `.venv/bin/python -c "import youtube_intel; print(youtube_intel.__file__)"` 指向 `remediation-20261125/src/youtube_intel/__init__.py` | ✅ 无跨 worktree 污染 |

## 2. 独立复核清单（Phase 0 源码复核结果）

| ID | 优先级 | 复核与闭环状态 | 核心根因核实 |
|---|---|---|---|
| `P1-01` | P1 | CLOSED (`812d638a`) | `fast_read_api.backup_download` 与 `/api/*` 读取路径缺少统一 loopback `Host` 允许列表与 `Sec-Fetch-Site: cross-site` 拦截；`local_api._send` 缺少 `Cross-Origin-Resource-Policy: same-origin` |
| `P1-02` | P1 | CLOSED (`812d638a`) | `fast_read_api._resolve_local_media_file` 接受未知 `storage_root` 回退且返回裸 `Path`，导致 `_send_file` 调用 `open_managed(path.parent, path.name)` 而跳过根祖先符号链接遍历与资产 SHA-256 校验 |
| `P1-03` | P1 | CLOSED (`69dd2858`, `1d97f61d`) | `workspace_intelligence_hub._prune_ungrounded_ref_clauses` 仅校验 `[E1]` 引用存在与子句非空，未对数字/百分比/货币/年份/数量与否定极性做基于引用片段的一致性核验 |
| `P1-04` | P1 | CLOSED (`0a778a07`) | `youtube_auth_fallback.can_attempt()` 仅在持锁检查后释放锁再执行网络拉取与 `_record_usage()`，多实例/并发请求存在最后配额与冷却槽位竞态 |
| `P1-05` | P1 | CLOSED (`192847d6`, `913b2c06`) | `App.tsx` 中 `.reader-ref-drawer` 关闭态仍保留在无障碍树与 Tab 焦点链中，缺少 `inert`、`tabIndex={-1}`、`role="dialog" aria-modal="true"`、焦点循环（含闭合 `<details>` 过滤）与关闭回焦 |
| `P1-06` | P1 | CLOSED (`812d638a`) | `local_api._send_bytes` 在 `HEAD` 请求仍写响应体；`_handle` 吞掉发送前异常且未区分发送前后错误状态码 |
| `P1-07` | P1 | CLOSED (`75da5130`) | 已基于 `origin/main@d1b58f73` 创建线性分支 `antigravity/remediation-20261125` 并完成无冲突重放 |
| `P2-01` | P2 | CLOSED (`812d638a`) | `local_api._parse_byte_range` 使用 `int()`（允许 `+4`），且遇到逗号分隔多区间时静默回退 `None` 而非规范处理 |
| `P2-02` | P2 | CLOSED (`0a778a07`) | `youtube_auth_fallback.validate_netscape_cookies_txt` 域名后缀校验过宽，且保留未过滤的第三方非 YouTube/Google Cookie 行 |
| `P2-03` | P2 | CLOSED (`69dd2858`) | `_build_research_scope_options` 统计本地/B 站资料未校验 `verify_source`，UI 误标为「全库可核验资料」 |
| `P2-04` | P2 | CLOSED (`192847d6`) | `ContentDetailPanel` 本地媒体加载失败未按 `MediaError.code` 区分清晰原因与一键重试恢复动作 |
| `P2-05` | P2 | CLOSED (`192847d6`) | `ContentDetailPanel` 在 `App.tsx` 中超过 1,200 行，已拆出 `ReaderMediaStage.tsx`、`ReaderReferenceDrawer.tsx`、`ReaderRecoveryPanel.tsx` |

## 3. 全流程批次记录

- `Phase 0 / Gate M1`（`75da5130`）：基于 `origin/main@d1b58f73` 创建线性分支 `antigravity/remediation-20261125` 并完成树等价重放（闭合 `P1-07` 拓扑要求）。
- `Batch A / Gate S1`（`812d638a`）：闭合 `P1-01`, `P1-02`, `P1-06`, `P2-01`（`149 passed in 115.81s`）。
- `Batch B / Gate S2`（`0a778a07`）：闭合 `P1-04`, `P2-02`（`9 passed in 6.41s`）。
- `Batch C / Gate S3`（`69dd2858`, `1d97f61d`）：闭合 `P1-03`, `P2-03`，并在全链路运行后补全 `#编号` 与中文「一人/一家」习惯用语规则。
- `Batch D / Gates U1 & U2`（`192847d6`）：闭合 `P1-05`, `P2-04`, `P2-05`, TOP 1–3。
- `Hygiene / Typing`（`e7118b2b`）：修复 `mypy` 严格类型与行尾/文件尾空格。
- `Gate E1`（`1d97f61d`）：独立无并发运行核心公测全链路 17 文件 **`205 passed in 1021.58s`** + 补充核心回归 6 文件 **`290 passed, 1 warning in 357.23s`** + `ruff check` / `mypy` (138 files) / `ci_test_manifest.py verify` (7,388 collected / 7,177 runnable) / `git diff --check` 全部 0 错。
- `Gate E2 & UI Defect Closure`（`913b2c06`）：
  - 首轮实机（`8795`）抓出模态抽屉内收起 `<details>` 导致第 4 步 `Tab` 逸出焦点陷阱问题；已在 `ReaderReferenceDrawer.tsx` 增加 `isInsideClosedDetails` 与可见性过滤及 `ManualUxRemediation.test.tsx` 单元测试。
  - 重建前端产物 `assets/index-BFMi-sz-.js`，全量前端 Vitest 实测 **`58 test files passed (58), 1276 passed (1276) in 428.92s`**。
  - 在全新无缓存端口 `8796` 与 `8792` 完成全部 5 项 Chromium 实机核验（`0` Console errors，`0` HTTP>=400，MP4 HTTP `206`，closed `inert=""` `0/20` Tab，open dialog `0/15` Tab/Shift+Tab 逸出，`390x844` 零横向溢出，`YtAuthGate1` 取消 `0` 请求，`#Research` 范围条实拍）并存档 7 张脱敏截图。
- `Gate R1`：输出 `05_INTEGRATION_REMEDIATION_ACCEPTANCE_REPORT.md` 并推送 `origin/antigravity/remediation-20261125`。
