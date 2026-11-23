# 产品决策记录（Product Decision Log）

- **决策原则**：任何重要产品、技术与运营决策必须比较至少三种候选方案（A 当前实施 / B 轻量或替代路径 / C 延后或取消），附带 RICE 评分、成本收益、风险与回滚条件；严禁在无证据下“为了做而做”。

---

## 决策总览索引

| 决策 ID | 决策主题 | 审批层级 | 当前状态 | 结论 | RICE 评估 (`R·I·C/E`) |
|---|---|---|---|---|---|
| **DEC-OPS-001** | 导出笔记与问答卡片补齐安全 HTTPS `?t=` 原片深链与出处指纹 | L1 | **EXECUTED (`09f98d4`)** | 已上线，测试全绿 | `8 × 3 × 0.85 / 0.5 = 40.8` |
| **DEC-OPS-002** | 将安全加固提交同步上 `main` 并激活 GitHub Actions | L3 (`FD-001`) | **COMPLETED (`main@9f65417`)** | CI `#45132090574` 全绿 | `10 × 3 × 0.95 / 0.3 = 95.0` |
| **DEC-OPS-003** | 坚决延后 V2 全网爬虫、自动 `hybrid` 路由与多图 VLM | L1 | **DECIDED (DEFER)** | 内部完善期冻结，防功能膨胀 | `—` |
| **DEC-OPS-004** | 用真实本机 `ollama/qwen3.5:9b` 跑通陌生双语对照基准 (`EXP-002`) | L2 | **EXECUTED (`2026-11-23`)** | 3/3 有据 + 2/2 拒答 (`227.6s`) | `9 × 3 × 0.70 / 1.0 = 18.9` |
| **DEC-OPS-005** | 推出零配置 `youtube-intel start` 启动器消除首次冷启动必崩 | L1 + L3 (`FD-004`) | **COMPLETED (`main@a820152`)** | CI `#45137542384` 全绿 | `10 × 3 × 0.95 / 0.8 = 35.6` |
| **DEC-OPS-006** | **Stage D Iteration #3**：根治 Demo 越域假问答、macOS 浏览器本地上传死路、空库 409 与冷启动 Settings 误报 | L1 | **EXECUTED (`fee43f4`)** | **实测全绿（140 pytest + 1240 Vitest + Chromium 复检）** | `10 × 3 × 0.95 / 0.7 = 40.7` |

---

## 详细决策记录

### DEC-OPS-001 ~ DEC-OPS-005（历史已执行决策摘要）
- **`DEC-OPS-001` (`09f98d4`)**：在单视频/跨源问答导出 Markdown、纯文本与 UI 中植入经过 `https://` 白名单校验的 YouTube/B 站秒级跳转链接与 `ev:` ID 前缀，同时保护本地 Markdown `TEXT_RANGE` 免受 `00:00` 假时间戳污染。
- **`DEC-OPS-002` (`9f65417`)**：合并提交并补齐 Linux inode 复用守护、`mlx_whisper` 动态类型兼容、timer 1ms 抖动修复与 CI `ffmpeg`，达成双端 CI 全绿。
- **`DEC-OPS-003` (DEFER)**：针对 `Open Notebook` (42k★) 与 `SurfSense` (17k★) 的广连接策略主动做减法，冻结 V2 全网抓站，集中打穿核验闭环。
- **`DEC-OPS-004` (`EXP-002`)**：隔离验证 `qwen3.5:9b`（`$0`）在中英对照与诱导性问题上的 JSON Strict 遵守能力，验证默认零花费路线可行。
- **`DEC-OPS-005` (`a820152`)**：根治按 `settings.example.yaml` 启动 `serve-api` 因占位路径 `Exit Code 2` 崩溃的问题，交付 `youtube-intel start` 与 `--check-only` 检查表。

---

### DEC-OPS-006：解决 Stage A 实机审计暴露的四大体验断裂点（2026-11-23 · Iteration #3）

| 评估维度 | 详细分析与证据 |
|---|---|
| **触发问题（Stage A 实机实证）** | ① Offline Demo 对跨领域无解问题（“量子引力场在火星大气层实测数值”）误返回 `GROUNDED` + 3 条无关引用；<br>② 通过 CLI `youtube-intel start` 在 macOS 浏览器打开工作台时，因 `/local/native/capability = false` 导致用户彻底无法上传任何 `.md`/`.txt`/音视频文件；<br>③ 全新工作区因 `hub.sqlite3` 尚未懒建，导致 `#Settings` `AI 能力总览` 误报 `⚪ 待检查模型就绪状态` 且强行摊开底层工程诊断壁；<br>④ 空库访问 `#Research`/`#Topics`/`#Intelligence` 缺导入引导且空提交触发 HTTP `409`、模态窗 `Escape` 键无效、移动端 `.nav-item` 偏矮（`34px`）。 |
| **用户价值与预期收益** | 把“新用户体验 Demo 立即打穿反幻觉认知”及“首次跑起 `youtube-intel start` 亲手传入第一份本地 `.md`、看清 Ollama 状态、在各空页顺畅行动”从阻断拉回流畅可用；预期大幅降低未来真人体检期的首次掉队风险（具体留存转化影响：`[待真实用户验证假设]`）。 |
| **三方案对比** | **方案 A（已选并执行，RICE `40.7`）**：<br>1. Demo 问答 `_DemoShowcaseCompleter` 增加全词边界匹配与中文停用/虚词切分（`_demo_question_has_evidence_support`），无直接证据即显式拒答并保留分离 `related_excerpts`；<br>2. `WorkspaceIntelligenceHub.ensure_ready()` 在 `prepare_local_workspace()` 时幂等建表，保证全新工作区首开 `#Settings` 即亮绿且收起工程诊断，同时仅在 `save()` 时同步 `liveWorkspaceAi` 防止打断表单编辑态；<br>3. `NativeLocalImport` 在 `available === false` 时保持原有原生警告不变，下方额外提供一键“使用浏览器本地上传（`.md / .txt / 音视频`）”切入现有 `/api/v1/local/imports` 回环上传器，兼顾 `AddEntry` / `LocalImport` / `NativeLocalImport` `Escape` 关窗；<br>4. `#Research`/`#Topics`/`#Intelligence` 配备空库引导与直达导入 CTA，移动端导航按钮最低 `40px`。<br>**方案 B（轻改文档说明）**：只在 README 说明“CLI 启动下 macOS 无法传本地文件、Demo 遇到无关问题不会拒答”——会直接摧毁第一次试用的直觉口碑，**拒绝**。<br>**方案 C（在浏览器强行屏蔽所有 macOS 原生桥接代码）**：会破坏既有 macOS 打包原生文件选择器契约及 8 个既有单测，**拒绝**。 |
| **工程成本与副作用** | 修改 3 个后端文件 + 8 个前端组件/样式文件 + 5 个测试文件（共 16 文件）；严格不修改核心 DB Schema、不引入新外部依赖、不影响 `.var/owner`。 |
| **验证结果与回滚条件** | 提交 **`fee43f4`**：`ruff` / `mypy` (136 文件) 0 错、`11` 组 CI `pytest` **140/140 passed**、`npm run build` 成功、Vitest **54/54 文件 / 1240/1240 passed**；Chromium 实机双端口（`8799` & `8798`）全部 4 项修复目测与接口 `200`/`201` 确认且 `0` console error / `0` 横向溢出。<br>回滚条件：若未来任一场景暴露 macOS 原生文件选择与回环上传回退冲突，可按 Commit `fee43f4` 精准撤回对应片段。 |
