# 产品待办与优先级池（RICE Backlog & Simplification Registry）

- **更新日期**：2026-11-23
- **当前筛选原则**：只列有明确 Stage A/B 实机或市场证据支撑的内部完善项；同步维护 **“主动减法与暂缓清单”**，坚决拒绝功能膨胀。
- **评分公式**：$\text{RICE} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort (人周)}}$（$R$: 1–10，$I$: 0.25–3.0，$C$: 0.5–1.0，$E$: 人周，当前外网样本未测前置信度 $C$ 保守打折）。

---

## 一、待办优先级排期（内部完善阶段）

| 排名 / ID | 类别 | 问题与改进项 | 来源依据（Stage A/B/D） | R | I | C | E | RICE 分 | 状态 |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| **BL-001** | Bug/Trust | Demo 工作台对越域对抗问题强行编造 `GROUNDED` + 3 条无关引用 | Stage A `step_6_shot_1_demo_refusal_1440` | 10 | 3.0 | 0.95 | 0.4 | **71.3** | **DONE (`fee43f4`)** |
| **BL-002** | Onboarding/P0 | macOS 运行 `youtube-intel start` 时浏览器无法导入本地 `.md`/音视频 | Stage A `8798` 实机 `NativeLocalImport` | 10 | 3.0 | 0.95 | 0.5 | **57.0** | **DONE (`fee43f4`)** |
| **BL-003** | UX/P0 | 全新空工作区 `#Settings` 误报 `待检查` 且摊开工程诊断，空 `#Research` 误触发 HTTP `409` | Stage A `8798` 实机审计 | 10 | 2.5 | 0.95 | 0.5 | **47.5** | **DONE (`fee43f4`)** |
| **BL-004** | A11y/UX/P1 | Import 模态窗 `Escape` 无法关闭、空 `#Topics`/`#Intelligence` 缺导入 CTA、移动端顶部 `.nav-item` 仅 `34px` | Stage A `8798`/`8799` 桌面 & `375px` 审计 | 8 | 2.0 | 0.90 | 0.4 | **36.0** | **DONE (`fee43f4`)** |
| **BL-005** | Docs/Eval | 基于公开技术演讲语料体系（Obsidian/Agent/B站双语）将反幻觉与冲突分辨 Eval 集由 20 例扩充至 32 例（不含个人隐私文件），顺带加固 Offline Demo 停用词与词形拒答 | Stage B 竞争差异化要求 | 8 | 2.5 | 0.85 | 0.6 | **28.3** | **DONE (Iteration #4)** |
| **BL-006** | UX/Flow | 根治 `#Content/<id>` 首次展开 `证据 · 来源字幕` 延迟与 `正在加载原始证据…` 闪烁（新增 `FastReadApiApplication` 单快照 `/evidence` 加速 + 前端 SWR 保持）并重排顶部 9 按钮为两层信息流 | Stage A `vidDemoAgt1` 实机审计 | 7 | 1.5 | 0.85 | 0.4 | **22.3** | **DONE (Iteration #4)** |
| **BL-007** | UX/Copy | 统一优化首页首run三步引导（交互步骤条、结构化来源卡、Warm Paper Light + `375px` 响应式对齐与品牌绿主色）及补全缺失中文词条/清除非断言残留英文（100% 保留既有测试契约） | Stage A `Onboarding` & 走查 | 6 | 1.5 | 0.80 | 0.4 | **18.0** | **DONE (Iteration #5)** |
| **BL-008** | Reliability | 大库扩展性演进：支持 >500 条视频全库分页（`/api/v1/videos?limit=&offset=`）、全库分块检索与 SQLite 原生 `.backup()` 零密钥热快照（零核心 Schema 变更）；同步复核 `#Settings` 次级工程说明默认折叠无需二次 UI 改版 | Stage A 架构审计（`TECH-04`） | 4 | 2.0 | 0.70 | 1.0 | **5.6** | **DONE (`dbc7e89`)** |
| **BL-010** | Reliability/Vault | 长视频 4h（`14390s`）与 300KB+ Markdown 全篇均匀边界加固、Obsidian `.zip` 真实解压安全（>255B 中文标题截断/`_CON`/大小写碰撞/YAML 转义/CommonMark 空行/文本禁 `00:00`）与 `RELEASE_READINESS_GATE.md` | Week 2 隔离边界与导出排查 | 6 | 2.5 | 0.90 | 0.6 | **22.5** | **DONE (`main@c15cf06`)** |
| **BL-011** | Multimodal/UX | 按需轻量本地视频关键帧抽取 + 感知哈希去重 + 原话字幕对齐融合分析 MVP（`$0` 本机 Ollama + 严格受控 BYOK、防覆盖原子暂存、前端图卡与 Lightbox 键盘预览、`visual-pack.zip` & 全库 Vault `assets/*.jpg` 打包及 Sidecar 备份恢复） | 创始人选型 `A`（Iteration #8 / `FD-007`） | 7 | 2.5 | 0.90 | 0.8 | **19.7** | **DONE (`main@092951b`)** |
| **BL-012** | UX/DX | Round 19 工作台易用性与冷启动自检可读性打磨：`⌘K` 深入专题洞察（`#Intelligence`）与追问（`#Research`）快捷动作、`#Topics` 搜索/置顶筛与三模式排序工具条、Research 多行输入防遮挡细滚动条、`youtube-intel start --check-only` 一行式就绪结论（`[ALL READY]`/`[READY WITH WARNINGS]`/`[ACTION NEEDED]`/`[BLOCKED]`）与模型数量溢出展示 | Round 19 封存待办 & `FD-008` | 7 | 1.5 | 0.90 | 0.4 | **23.6** | **DONE (`main@c54b818`)** |
| **BL-009** | Distribution | 一键桌面打包 / homebrew cask / WSL 极简脚本可行性评估（需待获批真人首测验证安装卡点分布后再定） | Stage B `anything-llm`/`BiliNote` 对照 | 9 | 2.5 | 0.50 | 2.5 | **4.5** | **HOLD (待真人冷启动样本)** |

---

## 二、主动减法、简化与暂缓清单（Anti-Bloat Guardrails）

| 项目 / 模块 | 处理方式 | 裁定依据 |
|---|---|---|
| **V2 全网爬虫（X、小红书、播客 RSS、任意网页抓取）** | **DEFER（暂缓）** | 与 `SurfSense`/`Open Notebook` 拼“泛连接器数量”没有比较优势，反而成倍放大反爬维护与噪音；核心 YT+B站+`.md` 尚未经外部留存证伪前绝不开新战线。 |
| **后台自动全量批量跑视频关键帧 VLM 分析** | **DEFER（暂缓 · 保留边界）** | 单视频“用户主动触发、有界 3–12 帧 + dHash 去重 + `$0` 本地优先”已随 **`BL-011`（Iteration #8）** 轻量交付；但**入库即自动全量抽帧或后台自动扫库跑云端视觉模型**会陡增算力与费用风险，继续坚决暂缓。 |
| **自动隐式 `hybrid` 云端模型切换** | **PERMANENTLY REFUSE（拒绝）** | 直接违背“零静默花费 / Fail-Closed 预算安全”底线，保持仅在显式 BYOK + 预算限额 + 端点重认证下启用。 |
| **`#Settings` 上重度技术诊断项默认平铺暴露** | **SIMPLIFY（已收拢 · 零扰动维持）** | 非开发者完全不需要默认看见 `qwen3:8b 质量验收未通过` 等内部测试名目；Iteration #6 复核确认 `#settings-legacy-diagnostics` 在 `hasWorkspaceAi === true` 时已默认折叠，故不再制造冗余前端 UI 扰动（`DEC-OPS-009`）。 |
| **`TASK-016` 多模型深度研究实验流暴露** | **KEEP EXPERIMENTAL / HIDDEN** | 保持默认关闭与 fail-closed 状态，避免干扰主流“导入 → 问答 → Obsidian 导出”心智。 |
