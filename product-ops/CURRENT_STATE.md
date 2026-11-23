# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-24（`Asia/Shanghai` · **Iteration #10 / `BL-013` Codex 审查 15 P1 + 7 P2 缺陷清零与本地全绿验收完成**）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（已在 `main@ca4e17f` 基础上完成 Iteration #10 / `BL-013` 缺陷修复，待 `FD-009` 批复合流）
- **最新公开主线对照基线（`main` & `origin/main`）**：`ca4e17f`（对应 Iteration #9 / `BL-012` 收口，仓库保持 `PUBLIC` 被动状态，零外宣、无 GitHub Release、本轮未新增发布标签、保留 4 个历史 tag、`Stars: 0`、`Forks: 0`）

---

## 核心运行状态快照

- **当前产品目标**：完成 Codex 独立审查指出的全部 15 项 P1 与 7 项 P2 缺陷的彻底清零、防线加固与实机双向验收，为随时合流主线（`FD-009`）或二轮复核扫清全部可信度、安全恢复与可用性障碍。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` ~ `FD-008` 主线同步（至 `main@ca4e17f`）**：Iteration #1–#9 依次获批合入 `main` 且严守被动 `PUBLIC`、零外宣与 `EXP-001` `HOLD`。
  2. **完成 Iteration #10（`BL-013` — Codex 独立审查 15 P1 + 7 P2 全量修复与 CI 回归扩容）**：
     - **可信度与证据链（`P1-01`~`P1-06`）**：混合答案发现未知引用时精确剥离对应从句/条目标记，零依据余项整答拒答；文本笔记要点按精确单段签发 `TEXT_RANGE` ID；跨库恢复引用在主库复核通过前显式标记 `NEEDS_REVERIFICATION`；Demo 混合无据前提直接拒答；CJK 2-gram FTS5 全库预检防止中文尾段漏召回；`/videos/<id>/evidence?evidence_id=` 按需拉取尾段并在缺失时返回 `MISSING_OR_STALE`；
     - **安全、恢复容量与视觉耐用性（`P1-07`~`P1-11`, `P2-01`, `P2-02`, `P2-06`）**：BYOK 文本/视觉双路均经拒绝重定向传输层派发，本地纯文本模型推理视觉请求前置 `LOCAL_VISION_MODEL_UNSUPPORTED` 拦阻且 `start --check-only` 诚实提示 Vision 受限；`BEGIN IMMEDIATE` 原子并发扣减每日预算；恢复接口扩至 `64 MiB`，SHA-256 打包恢复离线关键帧 JPEG（上限 `40 MiB`）且旧无图备份显式告警并过滤无效 `![[assets/...]]`；`gen-<uuid>` 原子代数切换与 `dir_fd`+`O_NOFOLLOW` 防符号链接越界；Windows `_CON`/`_AUX`/`_NUL` `.zip` 转义；
     - **全库容量、冷读并发与交互细节（`P1-12`~`P1-15`, `P2-03`~`P2-05`, `P2-07`）**：`#Content` 200+ 分页与 `?q=` 全库检索、`⌘K` 全库直达、移除同步 300 条截断、TOCTOU 缓存发布屏障 + `include_markdown=False` 列表提速；`⌘K` 切专题清除多视频对比锁、IME 组合键防误提交、Lightbox 稳定键 + `Tab` 陷阱 + `Escape` 焦点归还、同页会话即时切换。
- **质量验收快照（Iteration #10 最新分支改动后本地全量实测）**：
  - 后端：`uv run ruff check src tests scripts` 0 错、`uv run mypy src`（137 文件）0 错；14 组完整 CI（含新接入的第 14 组 `test_codex_review_remediation.py`）+ 2 组备份/恢复共 **16 组套件一次性 `193 passed in 422.38s (0:07:02)`**（`0 failed`, `0 skipped`）；隔离 40 视频含摘要库 5 轮 `/api/v1/videos` 冷读中位数 `41.393ms`（`38.435–53.153ms`）；
  - 前端：`cd frontend && npm run build`（`814ms`）零报错、全量 Vitest **`Test Files 57 passed (57) / Tests 1256 passed (1256)`**（耗时 `61.23s`，含 `CodexReviewRemediation.test.tsx` `7/7`）；
  - 实机：`http://127.0.0.1:8794` 隔离 Chromium 验证 `#Research` 会话切换、`⌘K` 切专题清锁、第 31 段尾段直达、`#Content` 搜索及 Keyframe Lightbox + `Escape` 全通（`0` console error / `0` HTTP `>=400` / `0px` 横向溢出）。
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **`FD-009`（PENDING — Iteration #10 合流 `main` 与触发云端 14 组 CI）**：`EXP-001` 与 `BL-009` 继续维持 `HOLD`，仓库维持被动 `PUBLIC`、零外宣、无 GitHub Release。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 在 `antigravity/task-user-readiness-20261112` 保留干净提交，等待创始人批复 `FD-009` 合流 `main` 或发起二轮 Codex 复查；
  2. 严守被动 `PUBLIC`、零外宣、无 Release 与零真人试验边界。
