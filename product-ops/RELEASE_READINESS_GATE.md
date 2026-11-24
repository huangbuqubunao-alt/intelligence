# 阶段退出检查单与合流门禁（Release & Stage Exit Readiness Gate）

- **更新日期**：2026-11-24（`Asia/Shanghai`）
- **评估对象分支与主线**：`main@4f3fe70` & `antigravity/task-user-readiness-20261112`（`FD-009` 已按选项 A 线性合流并获 GitHub Actions [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 双端全绿验收，严守被动 `PUBLIC`、零外宣、无 GitHub Release、保留 4 个历史 tag）
- **门禁用途**：用于记录 Iteration #10（`BL-013` + Claude 3 轮复核 + 实机浏览器双端口验收 + `main@4f3fe70` 云端绿标）的完整内部退出就绪度，并为未来何时批准启动 `EXP-001` 小范围真人试跑提供依据。

---

## 一、六维退出检查单（严格四态与实测归因）

| 检查维度 | 当前状态 | 核验依据与实测数据 | 已知边界 / 未关闭风险 |
|---|---|---|---|
| **1. 核心多源研究闭环** | **PASS** | `youtube-intel start` 零配置冷启动 + `--check-only` 全量识别本地模型并用 `/api/show` 精准标出 Vision 能力与受限提示；支持 YouTube、B 站 `BV`、本地音视频（`<=4h` / `<=2GiB`）与本地 `.md`/`.txt`（`<=2MiB`）；跨源 FTS5 启用 CJK 2-gram 索引与全库召回；内容页支持 `?q=` 全库检索（含 `>100` 结果点击加载更多）与 `>200` 分页，`⌘K` 在全库检索截断时明示库内命中总数并在切专题时自动清除旧多视频对比锁；同页会话切换即时更新。 | 非 WSL 原生 Windows 受限于 `fcntl` 不可用（已有明确错误引导，非静默崩溃）。 |
| **2. 反幻觉防线与 Fail-Closed 安全隔离** | **PASS** | 混合答案若夹带未签发引用（含 `[E88]`、`【E77】`、`[ E88 ]`、`[E88,E1]`、`(E88)` 与裸 `E88`）对纯无据句整句删除，对同句多逗号杂糅仅保留带真实有效引用且含实质论据的子句，悬空无据从句与存根一律剥离，零剩余有效依据整答拒答；文本笔记要点精确匹配单段失败时明确留空证据链并标为 `NEEDS_REVERIFICATION`（绝不误绑首段）；跨库恢复记录（含拒答会话 `related_excerpts`）与导出 Obsidian Markdown / ZIP 统一经主库权威复核，未过核验摘录彻底脱敏并显式插入 `NEEDS_REVERIFICATION` 告警；Demo 移除 `0.65` 放行阈值确保混合前提严格拒答，同时实测全部 59 条中英文 UI 推荐提问胶囊全部 `GROUNDED`；BYOK 双路无例外走 `_NoCloudRedirect`，双实例多线程竞争 `BEGIN IMMEDIATE` 原子锁死每日调用预算，`data_root` 与关键帧读盘均走 `dir_fd` + `O_NOFOLLOW`；`scripts/security_scan.sh` 对本轮改动 **0 告警**。 | 真实长视频在多变外网字幕格式下的真实模型幻觉率：**`当前不可评估`**（内部本机仅实测 `EXP-002` `qwen3.5:9b` 5 问样本；Round 2 / Round 3 均用合成测试替身验证）。 |
| **3. 大库容量、4 小时课程、关键帧备份还原与导出可靠性** | **PASS** | · **备份与关键帧持久化（`N3` 修复）**：导出包按 `40 MiB` 关键帧原始体积与 `64 MiB` 序列化 JSON 总上限自动分级降级并记录 `skipped_visual_assets` + `warnings`，超限关键帧优雅略过、100% 保留所有摘要/问答/配置且保证导出的备份可通过 `64 MiB` 导入通路成功恢复（SHA-256 校验离线资产）；关键帧重分析采用单视频锁 + `gen-<uuid>` 提交后清理过期目录；旧无图备份还原明确告警并过滤无效 `![[assets/...]]`；<br>· **全库规模、同步与冷读**：移除同步队列 300 条上限；`/api/v1/videos` 读屏障阻止并发脏缓存发布，`get_video_briefs_map` 复用 `repo_conn` 使冷读 `/api/v1/dashboard` 连接保持 `<= 3`（实测达标）且 40 篇冷读低于 `120ms` 预算；<br>· **尾段直达与 `.zip` 安全**：`/api/v1/videos/<id>/evidence?evidence_id=` 按需直达第 31 段及任意尾段（失效 ID 显式 `MISSING_OR_STALE`）；4h/`300KB+`、`_CON`/`_AUX`/`_NUL` 与 `<=180B` 中文命名全部实测通过。 | Windows 物理机及真实超大百集视频长期磁盘占用清理策略尚未在实机实测。 |
| **4. 前端可用性、双主题与响应式无障碍** | **PASS（云端 57 文件 + `8793`/`8794` 实机全通）** | 云端 CI [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) `vite build` `1.37s` 零报错 + Vitest **`57/57` 文件 / `1257/1257` tests passed**；同时在最新交付代码（`b28ba5d`）通过真实 Chromium 双端口实机走查：<br>· `8793`（Demo）：3 条默认 `#Research` 推荐胶囊 + 专题推荐均 `GROUNDED`，越域陷阱拒答，历史会话切换、`⌘K`、视频/Markdown 详情导出、Obsidian Dark/Warm Paper Light 切换及 `375×812` 移动布局 `0px` 溢出；<br>· `8794`（355 条内容库）：`#Content` 远程搜索 `100 / 135` 续拉至 `135 / 135`，`⌘K` 明确提示 `库内命中共 135 条`；全程 `0` console error / `0` HTTP `>=400` / `0px` 溢出。 | 真视觉模型 `ollama/gemma3:4b` 对低分辨率或强遮挡复杂课件的 OCR 精细度依赖本机视觉模型能力上限。 |
| **5. 跨平台及外部受控环境兼容性** | **PARTIAL / KNOWN LIMIT** | 云端 GitHub Actions `ubuntu-latest`（[`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) on `main@4f3fe70`）：`ruff` / `mypy`（137 文件）0 错，14 组 CI **`175 passed in 309.20s (0:05:09)`** + 前端 **`57/57` / `1257/1257`** 一次性全绿；本地 16 组全套 **`202 passed in 627.10s`**（随后 1 行纯测试断网隔离修正亦已通过 `23/23` 与云端 14 组复核）。 | ① **Windows WSL2 实机：`NOT_TESTED`**（无物理环境）；<br>② **公网免 Cookie YouTube 抓取：`BLOCKED`**（触发平台反机器人核验，严格不绕过）；<br>③ **安装包分发 (`BL-009`)**：维持 `HOLD`，待未来真人首测明确安装卡点后再决策。 |
| **6. 创始人 L3 治理与零隐私遥测边界** | **PASS（`FD-009` 已完结 · `EXP-001` 维持 `HOLD`）** | `product-ops/` 全部台账零个人主目录绝对路径泄漏且保留历史日报 `2026-11-23.md` 一致性；Zero-Telemetry 无任何外部埋点上报；**`FD-009` 已完结归档，仓库维持被动 `PUBLIC`（0 Stars / 0 Forks / 无 GitHub Release / 保留 4 个历史 tag）**。 | **外部首批真人试跑（`EXP-001`）**：在创始人明确批复退出内部完善阶段前严格维持 `HOLD`。 |

---

## 二、真实外部指标清单（严守零伪造）

- **真实外部用户激活率 / Day-7 留存率 / NPS / 真实付费转化率**：**`当前不可评估`**（内部迭代阶段禁止接触或招募任何真实用户）。
- **结论摘要**：当前产品在**内部工程质量、反幻觉与 Fail-Closed 安全、600 条大库与 4 小时课程/300KB 长文本扩展、以及 Obsidian `.zip` 真实解压可用性**上均已达到 **内部完备标准（Internal Exit Ready）**；下一步产品价值是否成立，取决于后续获批进入真实用户测试（`EXP-001`）后的实际留存反馈。
