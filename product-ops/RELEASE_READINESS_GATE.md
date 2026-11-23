# 阶段退出检查单与合流门禁（Release & Stage Exit Readiness Gate）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **评估对象分支**：`antigravity/task-user-readiness-20261112`（含 Iteration #8 / `BL-011` 按需轻量关键帧融合 MVP + 第 13 组 CI 接线，**待按 L3 批准合流 `main`**）
- **公开主线对照**：`main@c15cf06`（已按 `FD-006` 完成 Iteration #4–#7 同步，GitHub Actions [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端绿灯，严格被动 `PUBLIC`、零外宣、零 Release Tag）
- **门禁用途**：供创始人裁决是否将 Iteration #8 合流 `main` 以及未来何时开启首批小范围真人试跑（`EXP-001`）。

---

## 一、六维退出检查单（严格四态与实测归因）

| 检查维度 | 当前状态 | 核验依据与实测数据 | 已知边界 / 未关闭风险 |
|---|---|---|---|
| **1. 核心多源研究闭环** | **PASS** | `youtube-intel start` 零配置冷启动 + `--check-only` 预检；支持 YouTube、B 站 `BV`、本地音视频（`<=4h` / `<=2GiB`）与本地 `.md`/`.txt`（`<=2MiB`）；跨源 FTS5 BM25 问答与近 7 天严格窗口周报全链路跑通。 | 非 WSL 原生 Windows 受限于 `fcntl` 不可用（已有明确错误引导，非静默崩溃）。 |
| **2. 反幻觉防线与 Fail-Closed 安全隔离** | **PASS** | 离线 Eval 集扩充至 `32/32 (100%)`；Demo 越界问题显式 `REFUSED_INSUFFICIENT_EVIDENCE` 拒答且隔离 `related_excerpts`；macOS Keychain BYOK 隔离、每日预算账本、反 SSRF 与路径锁定均已通过单测；`scripts/security_scan.sh` 源码/前端/脚本/运营区 **0 告警**。 | 真实长视频在多变外网字幕格式下的真实模型幻觉率：**`当前不可评估`**（内部本机仅实测 `EXP-002` `qwen3.5:9b` 5 问样本）。 |
| **3. 大库容量、4 小时课程与 Obsidian Vault 导出可靠性** | **PASS** | Iteration #6–#7 实测：<br>· **600 条库**：分页 3 页 `[97.9, 48.1, 53.8]ms` 全遍历、跨库问答命中第 561 条仅 `0.23s`、SQLite `.backup()` 零密钥热快照 `5.5ms`；<br>· **4 小时课程与 300KB 长文本**：`14390s` / `3200` 片段归一化并召回 `03:52` 锚点；`300KB+` / `2900+` 行 Markdown 均匀全篇采样并精确召回 96% 处段落（`> 14400s` 与 `> 2MiB` 均确定性拒绝）；<br>· **Obsidian `.zip` 实机解压**：超长中文（>340 字节安全截断至 `<=180` 字节防 `NAME_MAX` 崩溃）、`CON` 保留字隔离、大小写/重名防覆盖、全量 YAML Frontmatter 合法性、空行排版与全索引 `[[wikilinks]]` 闭合全部 `3/3` 实测通过；文本笔记不再带出 `00:00` 假时长。 | 单个内容页 `/api/v1/videos/<id>/evidence` 为控制首屏体积有意按前 21 条展示窗口切片截断，超长内容尾段由跨源问答全库 FTS5 检索引擎与后端权威校验直接触达（已建边界说明）。 |
| **4. 前端可用性、双主题与响应式无障碍** | **PASS（Iteration #8 最新分支）** | `vite build` `875ms` 零报错；全量 Vitest **`55/55` 文件 / `1247/1247` tests passed in `63.51s`**（含 `WorkspaceVisualKeyframes.test.tsx`）；隔离端口 `8796` Chromium 验证 Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 关键帧图卡、筛选、`ArrowRight`/`Escape` Lightbox、`visual-pack.zip`、空态/纯文本屏蔽 `0` 横向溢出、`0` console error、`0` HTTP `>=400`；叠加 `2be958f` 三步引导与 `#Settings` 零扰动折叠。 | 真视觉模型 `ollama/gemma3:4b` 对低分辨率或强遮挡复杂课件的 OCR 精细度依赖本机视觉模型能力上限。 |
| **5. 跨平台及外部受控环境兼容性** | **PARTIAL / KNOWN LIMIT** | Iteration #8 分支本地实测：`ruff` 与 `mypy` (137 文件) 0 错、13 组完整 CI 独跑 **`151 passed in 367.69s`**（含真 `ffmpeg` 关键帧与 `.zip` 专项）、Backup/Restore **`27 passed in 39.46s`**；云端 Ubuntu Linux CI 对照基线 `main@c15cf06` [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端全绿（`1244/1244` + 12 组 `146/146`）；新增第 13 组视觉套件已写入 `.github/workflows/ci.yml` 待合流 `main` 后验证云端 Linux。 | ① **Windows WSL2 实机：`NOT_TESTED`**（无物理环境）；<br>② **公网免 Cookie YouTube 抓取：`BLOCKED`**（触发平台反机器人核验，严格不绕过）；<br>③ **安装包分发 (`BL-009`)**：维持 `HOLD`，待未来真人首测明确安装卡点后再决策。 |
| **6. 创始人 L3 治理与零隐私遥测边界** | **PASS（主线同步已闭环 · `EXP-001` 维持 `HOLD`）** | `product-ops/` 全部台账零个人路径泄漏（`grep` 退出码 `1`）；Zero-Telemetry 无任何外部埋点上报；CPO 日报自动化检测 `pending_founder_decisions: 0`；**`FD-006` 已完成 Iteration #4–#7 合流 `main@aec26da` 且仓库保持 `PUBLIC`（0 Stars / 0 Forks / 0 Releases）**。 | **外部首批真人试跑（`EXP-001`）**：在创始人明确批复退出内部完善阶段前严格维持 `HOLD`。 |

---

## 二、真实外部指标清单（严守零伪造）

- **真实外部用户激活率 / Day-7 留存率 / NPS / 真实付费转化率**：**`当前不可评估`**（内部迭代阶段禁止接触或招募任何真实用户）。
- **结论摘要**：当前产品在**内部工程质量、反幻觉与 Fail-Closed 安全、600 条大库与 4 小时课程/300KB 长文本扩展、以及 Obsidian `.zip` 真实解压可用性**上均已达到 **内部完备标准（Internal Exit Ready）**；下一步产品价值是否成立，取决于后续获批进入真实用户测试（`EXP-001`）后的实际留存反馈。
