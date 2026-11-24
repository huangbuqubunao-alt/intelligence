# QA 缺陷台账 (Defects Ledger)

- 仓库工作树: `/Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112`
- 分支: `antigravity/task-user-readiness-20261112`
- 基线 Commit: `07a86fe624e82821f594231c78847cd603b00304`
- 分级说明:
  - `P0`: 数据丢失、安全边界失效、严重不可用 / 崩溃
  - `P1`: 核心功能失败、关键业务流程中断
  - `P2`: 普通功能异常、明显 UX 问题 / 参数校验缺陷
  - `P3`: 轻微视觉及体验问题
  - `ENV / GOV / SEC`: 环境资源约束、设计期 fail-closed 冻结门禁或历史/测试夹具告警（不伪造通过）

---

## Batch 1 发现缺陷与分类记录

### DEF-001 `[P1]` `popstate` 无条件复用 `onHashChange` 导致导入提示误清除与 4 项前端单测回归
- **模块**: `frontend/src/workspace/App.tsx`, `frontend/src/workspace/motion.tsx`, `frontend/src/workspace/App.test.tsx`
- **状态**: **FIXED & VERIFIED**
- **复现步骤**:
  1. 在 `frontend/` 执行 `npx vitest run`。
  2. 触发本地文件导入并程序化跳转至 `#Content/<id>` 后，或派发历史过时 `hashchange` / 标准 `location.hash` 双事件流程。
- **实际结果**: `frontend/src/workspace/App.tsx:1781` 新增的 `window.addEventListener("popstate", () => onHashChange(new HashChangeEvent("hashchange")))` 无条件将 `popstate` 当成 `hashchange` 处理，且 `new HashChangeEvent("hashchange")` 的 `newURL` 为 `""`；当程序化导航先后触发 `popstate` 与 `hashchange` 时，`popstate` 先消费并清空 `programmaticHash.current`，随后的 `hashchange` 误判为用户手动导航并调用 `setImported(false)`。
- **修复方案**:
  - 在 `motion.tsx` 新增并导出 `cancelPendingChromiumHashUpdate()`；
  - 在 `App.tsx` `onPopState` 中若 `programmaticHash.current === location.hash` 则直接跳过不提前消费标记，否则取消待刷新定时器并传递 `{ newURL: location.href }` 同步路由状态；
  - 在 `App.test.tsx` 新增 `popstate` 回归单测。
- **验证证据**: 修复后 `cd frontend && npx vitest run` → **53/53 文件全部通过，1227/1227 用例通过**（`qa/evidence/vitest_post_fix.log`）+ Playwright `quick_import_modal_invalid_close_and_local_md_import` PASS。

### DEF-002 `[P1]` `check-stale` 无操作检查清空 `/api/v1/sources` 等路由的 FastRead 缓存
- **模块**: `src/youtube_intel/fast_read_api.py`, `src/youtube_intel/local_api.py`
- **状态**: **FIXED & VERIFIED**
- **复现步骤**:
  1. 执行 `uv run --frozen python -m pytest tests/integration/test_fast_read_api.py -k test_fast_read_api_accelerates_sources_topics_dashboard_intelligence_and_noop_stale_check`。
  2. 预热 `/api/v1/sources` 后调用 `POST /api/v1/sources/check-stale`（返回 `202 {"checks": []}`）。
- **实际结果**: 随后的 `GET /api/v1/sources` 未命中热缓存（`connect_calls == 1`，`AssertionError: /api/v1/sources cache was wiped by no-op check-stale`）。
- **根因**:
  1. `local_api.py:952`、`967` 在 `check-stale` 只读 `SELECT` 中调用默认读写连接 `self._repository._connect()` 而非 `read_only=True`；WAL 模式下该连接关闭后导致 SQLite 清理了 0 字节 `-wal` 文件。
  2. `fast_read_api.py:169-190` 的 `_sqlite_state_token` 对 0 字节 `-wal` 文件仍返回 `(dev, ino, 0, mtime_ns, b'', b'')` 而非 `()`，使 `db_token` 在零数据变更下发生变化并击穿缓存。
- **修复方案**:
  - `_sqlite_state_token` 仅在 `wal_st.st_size > 0` 时构造非空 `wal_token`，0 字节 `-wal` 等价返回 `()`；
  - `local_api.py` `check-stale` 只读查询改用 `self._repository._connect(read_only=True)`。
- **验证证据**: `uv run --frozen python -m pytest tests/integration/test_fast_read_api.py tests/integration/test_offline_transcription_jobs.py tests/integration/test_v1x_phase2_obsidian.py --tb=short -q` → **65 passed in 170.88s**（`qa/evidence/pytest_targeted_post_fix.log`）+ `qa_backend_audit.py` **55/55 PASS**。

### DEF-003 `[P2]` 离线转写超长输出溢出测试夹具低于 `MAX_RESULT` 阈值
- **模块**: `tests/e2e/offline_fixture_worker.py`, `src/youtube_intel/offline_transcription.py`
- **状态**: **FIXED & VERIFIED**
- **复现步骤**: 执行 `uv run --frozen python -m pytest tests/integration/test_offline_transcription_jobs.py -k "flood-EXECUTOR_OUTPUT_LIMIT"`。
- **实际结果**: 抛出 `OfflineError('TRANSCRIPT_INVALID')` 而非预期的 `EXECUTOR_OUTPUT_LIMIT`。
- **根因**: 此前本地媒体上限扩至 4 小时时 `offline_transcription.py:30` 将 `MAX_RESULT` 设为 `8 * 1024 * 1024`（8 MiB），而 `tests/e2e/offline_fixture_worker.py:50` 的 `flood` 模式仅打印 `5,000,000` 个 `"x"`（< 8 MiB），未触发 `EXECUTOR_OUTPUT_LIMIT` 而进入 JSON 解析失败路径。
- **修复方案**: 将 `tests/e2e/offline_fixture_worker.py:50` 的 `flood` 输出调整为 `9 * 1024 * 1024` 字节（> 8 MiB `MAX_RESULT`）。
- **验证证据**: 同 `DEF-002` 目标集成回归套件 **65 passed, 0 failed**（`qa/evidence/pytest_targeted_post_fix.log`）。

### DEF-004 `[P1]` `<GlobalInterests key={JSON.stringify(globalPolicy)}>` 在后台 SWR 刷新时强行卸载编辑中的表单与草稿
- **模块**: `frontend/src/workspace/App.tsx`, `frontend/src/workspace/App.test.tsx`
- **状态**: **FIXED & VERIFIED**
- **复现步骤**:
  1. 打开 `#Settings`（`设置`），点击 `编辑兴趣`（`#settings-interests`）→ 不作修改点击 `保存偏好`（触发 `setRevision(r => r + 1)` 与 `useRemote(..., true)` 后台重新拉取 `/settings/source-policy`）。
  2. 紧接着再次点击 `编辑兴趣` 进入编辑态并尝试操作表单 / 点击 `取消`。
- **实际结果**: 当后台 `/settings/source-policy` 响应（含最新 `updated_at` / `policy_revision`）返回时，`JSON.stringify(globalPolicy)` 变化触发 `<GlobalInterests key={...}>` 强行卸载重挂，正被点击/编辑的按钮与草稿瞬间从 DOM 分离（Playwright 真实点击报 `element was detached from the DOM`），用户未保存输入与编辑态丢失。
- **根因**: `frontend/src/workspace/App.tsx:9008` 使用 `key={JSON.stringify(globalPolicy)}` 将服务端整份策略对象作为组件重建键，配合 `useRemote("/settings/source-policy", refresh + revision, undefined, true)` 的 SWR 后台刷新策略，导致非编辑态之外的任何数据重查都会销毁当前实例。
- **修复方案**:
  - 移除 `<GlobalInterests>` 上会随后台刷新变化而销毁实例的 `key={JSON.stringify(globalPolicy)}`；
  - 在 `GlobalInterests` 内部通过 `useEffect` 仅在 `!editing` 时同步外部 `policy` 变更，并在点击 `"编辑兴趣"` 时从当前最新 `policy` 初始化草稿；
  - 在 `App.test.tsx` 新增 SWR 后台刷新不打断开放表单与草稿的回归单测。
- **验证证据**: `cd frontend && npx vitest run`（**53/53, 1227/1227 PASS**）+ 修复后完整 Playwright `node qa/scripts/qa_playwright_e2e.mjs`（**12/12 PASS**，含 `10_settings.png` 实测备份与损坏 ZIP 拒绝、`Agent Safety QA` 刷新持久化与语言往返）。

---

## 环境、合规门禁与历史夹具记录 (非源码产品缺陷)

### ENV-001 宿主机磁盘剩余空间接近 `DISK_RESERVE_BYTES` 导致全量集成期间偶发空间不足
- **触发项**: `tests/integration/test_v1x_phase2_obsidian.py::test_restart_and_backup_restore_exclude_external_vault`
- **现象**: 全量集成测试运行至末尾时因宿主机 `/dev/disk3s5` 可用空间不足，触发 `src/youtube_intel/source_authority.py:61` (`DISK_RESERVE_BYTES = 256 MiB`) 抛出 `OSError(28, 'Insufficient local disk space')` → `BackupRestoreError`。
- **独立复验**: 在当前 `f_bavail` 约 `4.68 GiB` 环境下单独执行通过（`1 passed, 38 deselected in 21.80s`）。QA 审计期间需保持 `.var/qa-audit/` 精简并在结束后清理临时运行文件。

### GOV-001 历史冻结试运行包与密封资格凭证的 Fail-Closed 门禁失败（190 项）
- **触发项**: `tests/unit` 共 188 项 (`35 FAILED` in `test_bounded_synthesis_trial.py` + `153 ERROR` in `test_bounded_synthesis_v2/v3/v4/v4_r2_trial.py`, `test_bounded_trial_device_continuity.py`) + 2 项 (`test_synthesis_attribution_v2.py:248`, `test_synthesis_judgment_v5.py:114`)。
- **根因与裁定**:
  - 188 项均在 `scripts/validation/bounded_synthesis_trial.py:951` 因 `before['schema'] == 44` 与当前代码/Schema 演进后的清单不一致而主动拒绝（`ValueError: SOURCE_INVENTORY_CHANGED`）。
  - 2 项因 `resources/system_synthesis_judgment_qualification_v1.json` 密封绑定历史 `code_sha256=d90e2aa0...`，而当前工作树源码哈希已变为 `77bbdb7e...`，按设计自动吊销云端深研资格（`sealed.permits(...) == False`）。
- **处理**: **禁止修改测试或伪造清单**；作为系统安全 fail-closed 设计不变量记录于报告。

### SEC-001 `scripts/security_scan.sh` 静态扫描 17 条命中（均为测试夹具与历史报告）
- **现象**: `bash scripts/security_scan.sh` 返回 Exit 1，`status=findings count=17`：
  - `src/` 与 `frontend/` **0 条命中**；
  - 16 条为 `tests/` 下的合成测试密钥/含凭据 URL（`test_deep_analysis_persistence.py`, `test_workspace_intelligence_hub.py`, `test_kimi_deep_analysis_adapter.py`, `test_subtitle_directory_limits.py:222`, `test_youtube_network.py:216`）；
  - 1 条为历史验收日志 `docs/validation/dogfood-day2-d2-02/full-suite-collection.txt:3938`。
- **证据**: `qa/evidence/security_scan.log`。
