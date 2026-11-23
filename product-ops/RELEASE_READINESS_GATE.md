# 阶段退出检查单与合流门禁（Release & Stage Exit Readiness Gate）

- **更新日期**：2026-11-24（`Asia/Shanghai`）
- **评估对象分支**：`antigravity/task-user-readiness-20261112`（已完成 Iteration #10 / `BL-013` 全部 15 P1 + 7 P2 缺陷修复与 14 组 CI + 2 组恢复 + 前端 57 文件局部全绿验证，待 `FD-009` 批复合流）
- **公开主线对照**：`main@ca4e17f`（对应 Iteration #9 收口基线，无 GitHub Release，本轮未新增发布标签，仓库保留 4 个历史 tag；严格被动 `PUBLIC`、零外宣）
- **门禁用途**：供创始人裁决将 Iteration #10 缺陷修复合流 `main`（`FD-009`），以及未来何时开启首批小范围真人试跑（`EXP-001`）的客观就绪度盘点。

---

## 一、六维退出检查单（严格四态与实测归因）

| 检查维度 | 当前状态 | 核验依据与实测数据 | 已知边界 / 未关闭风险 |
|---|---|---|---|
| **1. 核心多源研究闭环** | **PASS** | `youtube-intel start` 零配置冷启动 + `--check-only` 预检（识别仅纯文本 Ollama 时显式提示 Vision 受限）；支持 YouTube、B 站 `BV`、本地音视频（`<=4h` / `<=2GiB`）与本地 `.md`/`.txt`（`<=2MiB`）；跨源 FTS5 启用 CJK 2-gram 索引与全库召回；内容页支持 `?q=` 全库检索与 `>200` 分页，`⌘K` 切换专题时自动清除旧多视频对比锁；同页会话切换即时更新。 | 非 WSL 原生 Windows 受限于 `fcntl` 不可用（已有明确错误引导，非静默崩溃）。 |
| **2. 反幻觉防线与 Fail-Closed 安全隔离** | **PASS** | 混合答案若夹带未签发引用立即剥离无依据从句/条目并在零剩余依据时整答拒答；文本笔记要点按精确单段签发 `TEXT_RANGE` ID；跨库恢复的引用在主库权威复核前显式标为 `NEEDS_REVERIFICATION`；Demo 对“已知实体+无依据属性”复合前提直接拒答；BYOK 文本/视觉双路均拒绝 HTTP 重定向，`BEGIN IMMEDIATE` 原子锁死每日调用预算；`data_root` 令牌校验与关键帧读盘均走 `dir_fd` + `O_NOFOLLOW`；`scripts/security_scan.sh` 新增/修改项 **0 告警**。 | 真实长视频在多变外网字幕格式下的真实模型幻觉率：**`当前不可评估`**（内部本机仅实测 `EXP-002` `qwen3.5:9b` 5 问样本）。 |
| **3. 大库容量、4 小时课程、关键帧备份还原与导出可靠性** | **PASS** | · **备份与关键帧持久化**：Sidecar 恢复通道扩容至 `64 MiB`，导出包通过 SHA-256 校验打包离线 JPEG 资产（`visual_keyframe_assets`，原始体积上限 `40 MiB`）并在新库还原；重跑失败时 `gen-<uuid>` 原子代数保留旧图不断链；旧版无图包还原时明确告警并跳过破损 `![[assets/...]]` 嵌入；<br>· **全库规模、同步与冷读**：移除同步队列 300 条上限；`/api/v1/videos` 读屏障阻止并发脏缓存发布，`get_video_briefs_map_for_ids(..., include_markdown=False)` 优化后 40 篇含摘要库 5 轮冷读中位数 `41.393ms`（`38.435–53.153ms`）；<br>· **尾段直达与 `.zip` 安全**：`/api/v1/videos/<id>/evidence?evidence_id=` 按需直达第 31 段及任意尾段（失效 ID 显式 `MISSING_OR_STALE`）；4h/`300KB+`、`_CON`/`_AUX`/`_NUL` 与 `<=180B` 中文命名全部实测通过。 | Windows 物理机及复杂压缩包环境未在本机实测。 |
| **4. 前端可用性、双主题与响应式无障碍** | **PASS（Iteration #10 分支）** | `vite build` `814ms` 零报错；全量 Vitest **`57/57` 文件 / `1256/1256` tests passed in `61.23s`**（含 `CodexReviewRemediation.test.tsx` `7/7`）；隔离端口 `8794` Chromium 实机验证 `#Research` 会话即时切换、`⌘K` 切专题清锁、`#Content` 全库搜索、第 31 段尾段直达聚焦、Visual Keyframe Lightbox 状态稳定及 `Escape` 关闭后焦点归还，`0` console error / `0` HTTP `>=400` / `0px` 横向溢出。 | 真视觉模型 `ollama/gemma3:4b` 对低分辨率或强遮挡复杂课件的 OCR 精细度依赖本机视觉模型能力上限。 |
| **5. 跨平台及外部受控环境兼容性** | **PARTIAL / KNOWN LIMIT** | 本地分支（Iteration #10 最新代码后）：`ruff` / `mypy` (137 文件) 0 错，14 组 CI + 2 组备份恢复 Python 套件一次性 **`193 passed in 422.38s (0:07:02)`**，`57/57` / `1256/1256` 前端全绿；公开主线对照 `main@ca4e17f` 云端 GitHub Actions 绿灯（Iteration #10 待 `FD-009` 合流后上云触发 14 组 CI）。 | ① **Windows WSL2 实机：`NOT_TESTED`**（无物理环境）；<br>② **公网免 Cookie YouTube 抓取：`BLOCKED`**（触发平台反机器人核验，严格不绕过）；<br>③ **安装包分发 (`BL-009`)**：维持 `HOLD`，待未来真人首测明确安装卡点后再决策。 |
| **6. 创始人 L3 治理与零隐私遥测边界** | **PASS（`FD-009` 待批复 · `EXP-001` 维持 `HOLD`）** | `product-ops/` 全部台账零个人路径泄漏；Zero-Telemetry 无任何外部埋点上报；**`FD-009`（Iteration #10 合流 `main`）待创始人裁决，仓库维持被动 `PUBLIC`（0 Stars / 0 Forks / 无 GitHub Release / 保留 4 个历史 tag）**。 | **外部首批真人试跑（`EXP-001`）**：在创始人明确批复退出内部完善阶段前严格维持 `HOLD`。 |

---

## 二、真实外部指标清单（严守零伪造）

- **真实外部用户激活率 / Day-7 留存率 / NPS / 真实付费转化率**：**`当前不可评估`**（内部迭代阶段禁止接触或招募任何真实用户）。
- **结论摘要**：当前产品在**内部工程质量、反幻觉与 Fail-Closed 安全、600 条大库与 4 小时课程/300KB 长文本扩展、以及 Obsidian `.zip` 真实解压可用性**上均已达到 **内部完备标准（Internal Exit Ready）**；下一步产品价值是否成立，取决于后续获批进入真实用户测试（`EXP-001`）后的实际留存反馈。
