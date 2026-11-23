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
| **DEC-OPS-006** | **Stage D Iteration #3**：根治 Demo 越域假问答、macOS 浏览器本地上传死路、空库 409 与冷启动 Settings 误报 | L1 | **COMPLETED (`main@f23954f`)** | **CI `#45149288840` 双端全绿** | `10 × 3 × 0.95 / 0.7 = 40.7` |
| **DEC-OPS-007** | **Iteration #4 (`BL-006` + `BL-005`)**：单快照加速 `/evidence`（713ms→4ms 级）+ 两层详情动作栏 + 32 例多源冲突 Eval & Demo 词形拒答加固 | L1 | **EXECUTED (`6760028`)** | **本地全绿 + Chromium 桌面/移动复检** | `8 × 2.5 × 0.85 / 0.8 = 21.3` |
| **DEC-OPS-008** | **Iteration #5 (`BL-007`)**：首轮三步引导可跳转步骤条与来源矩阵 + 双主题移动端适配 + 补全缺失中文与移除 `UNKNOWN` 费用生硬词 | L1 | **EXECUTED (`2be958f`)** | **`54/54` (`1244/1244`) Vitest 全绿 + 双主题实机** | `6 × 1.5 × 0.80 / 0.4 = 18.0` |
| **DEC-OPS-009** | **Iteration #6 (`BL-008`)**：>500 大库全库分块检索与 `/videos` 分页 + SQLite `.backup()` 零密钥热快照 + 冷启动路径加速 + `#Settings` 零扰动复审 | L1 | **EXECUTED (`dbc7e89`)** | **`143/143` CI Pytest + `27/27` 备份全绿** | `4 × 2.0 × 0.70 / 1.0 = 5.6` |
| **DEC-OPS-010** | **Iteration #7 (`BL-010`)**：4h 音频与 300KB 长 Markdown 均匀边界加固 + Obsidian `.zip` 真解压安全与排版修复 + 阶段退出门禁清单 | L1 | **EXECUTED (Iteration #7)** | **`143/143` CI + `3/3` 边界真解压专项全绿** | `6 × 2.5 × 0.90 / 0.6 = 22.5` |

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
| **验证结果与回滚条件** | 提交 **`fee43f4`**：`ruff` / `mypy` (136 文件) 0 错、`11` 组 CI `pytest` **140/140 passed**、`npm run build` 成功、Vitest **54/54 文件 / 1240/1240 passed**；Chromium 实机双端口（`8799` & `8798`）全部 4 项修复目测与接口 `200`/`201` 确认且 `0` console error / `0` 横向溢出；随后在 **`FD-005`** 批复后整合 `b8759e0`/`fee43f4`/`256a058` 至 `main@f23954f`，GitHub Actions [`#45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端全绿。<br>回滚条件：若未来任一场景暴露 macOS 原生文件选择与回环上传回退冲突，可按 Commit `fee43f4` 精准撤回对应片段。 |

---

### DEC-OPS-007：加速单内容原始证据读取、精简详情动作层级并扩充至 32 例跨源反幻觉 Eval（2026-11-23 · Iteration #4）

| 评估维度 | 详细分析与证据 |
|---|---|
| **触发问题（Stage A + Eval 复盘）** | ① `GET /api/v1/videos/<id>/evidence` 未纳入 `FastReadApiApplication` 单快照缓存，单条内容打开耗时达 `583–713ms`，且刷新收藏/提炼态时无 SWR 保持导致闪烁 `正在加载原始证据…`；<br>② `#Content/<id>` 详情页顶部 9 个平铺按钮跨 3 行拥挤，`AI 重新提炼中文总结` 与主流程抢视觉焦点，且 `.kb-shortcut-hint` 在 `375px` 移动端被样式覆盖意外漏出；<br>③ 20 例 Eval 集未覆盖跨语言检索深链、Markdown+Video 混排冲突、混合非法引用清洗及 Demo “知识库展示+跨domain复合词”拒答盲区。 |
| **用户价值与预期收益** | 进入任意内容详情时原文证据几乎瞬间就位、操作收藏不闪白且阅读流 vs 导出组视觉清晰；同时用 32 例多维评测阻断 Demo 对“部分搭边关键词 + 无关财务/医学数值”的幻觉作答。 |
| **三方案对比** | **方案 A（已选并执行，RICE `21.3`）**：<br>1. `FastReadApiApplication` 新增 `_VIDEO_EVIDENCE_ROUTE` 与 `_fast_get_video_evidence()` 单事务快照投影，保留 100% fail-closed 校验 parity，接口从 `583–713ms` 降至冷读 `39.6ms` / 热读 `3.8–5.8ms`；<br>2. 前端 `ContentEvidencePanel` 开启 `retainOnRefresh + swr`，`ContentDetail` 与 `WorkspaceVideoAiActions` 拆成 `.reader-action-primary`（左侧阅读推进 + 右侧收纳导出组）与 `.reader-action-secondary`（原片外链 + 幽灵态重新提炼 + 仅桌面端快捷键提示），保留全部可访问标签与原有单测契约；<br>3. `tests/integration/test_grounding_refusal_eval.py` 保留原 20 例基准不动并追加 Cases 21–32（32 例全量评测），同步在 `demo_showcase.py` 加固元叙述词表及词干匹配，拦截复合域外伪前提提问。<br>**方案 B（把次要导出按钮藏进下拉菜单）**：会破坏已有高价值单测直接点击 `复制双链笔记` / `下载 .md` 习惯，且增加一步点击摩擦，**拒绝**。<br>**方案 C（在 `demo_showcase.py` 强设中文固定百分比阈值 `25%`）**：实际验证对正当中文综合题 `为什么生产级 AI Agent 要用状态机约束工具调用？` 产生误杀，**已实测淘汰**，改用纯净元叙述词扩展 + 词干对齐。 |
| **工程成本与副作用** | 改动 2 个后端模块 + 3 个前端源码 + 1 个样式文件 + 3 个测试文件；零数据库 Schema 迁移，零新依赖，无隐私数据写入。 |
| **验证结果与回滚条件** | `fast_read_api` 冷/热实测 `39.6ms`/`3.8–5.8ms`，32 例 Eval + Demo 测试全绿，Chromium `1440×900` & `375×812` 验证 9 条证据瞬载、收藏稳态保留与移动 0 溢出 0 console errors。可按单提交粒度安全回滚。 |

---

### DEC-OPS-008：优化首轮三步引导与双语 UI 文案精准度（2026-11-23 · Iteration #5 · `BL-007`）

| 评估维度 | 详细分析与证据 |
|---|---|
| **触发问题（Stage A + 词条全扫）** | ① 首轮引导 `.onboarding-progress span` 仍沿用旧版紫蓝渐变、缺少步骤跳转控件、第 3 步缺来源对照卡，跳过后空首页缺少格式提示；<br>② 词条全量扫描发现 `Organized` / `Review Content` / `Position unavailable` / `Loading current saved Intelligence…` 与 `Investigations` 专题提示缺失中文，偏好过期提示 `Expires` 仅英文，且计费提示直出 `UNKNOWN` 与多条长句冗长。 |
| **用户价值与预期收益** | 首次开启的新用户可在 3 步内直观理解“YouTube / Bilibili / 本地文件”输入路径并在 Obsidian Dark 与 Warm Paper Light 双主题下顺畅浏览，消除中文界面的生硬夹杂英文（具体首次完成率留待真人测试阶段验证：`[待真实用户验证假设]`）。 |
| **三方案对比** | **方案 A（已选并执行，RICE `18.0`）**：<br>1. `Onboarding.tsx` & `styles.css`：进度条改用唯一品牌绿 `--accent`，加入 3 步可跳转 pill 导航条与第 3 步 3 来源结构化卡片，`<=700px` 单列堆叠与全宽按钮；<br>2. `uiLanguage.tsx` & `App.tsx`：补全 5+ 项缺失中文词条（含 `Investigations` 专题页）、`Expires` 中文化、空首页补充支持格式提示，清理 `UNKNOWN` 等生硬残留英文，同时保留全部既有 Vitest 断言字符串不作弱化；<br>3. `Onboarding.test.tsx` 追加步骤跳转与中文化回归测试。<br>**方案 B（改写已有 `App.test.tsx` 断言强推全句重写）**：违背不弱化/不动历史单测红线，**拒绝**。<br>**方案 C（仅改文案不做引导视觉与移动布局对齐）**：留有紫蓝旧渐变与第 3 步空泛文案，**拒绝**。 |
| **工程成本与副作用** | 修改 `Onboarding.tsx`、`styles.css`、`uiLanguage.tsx`、`App.tsx` 与 `Onboarding.test.tsx` 共 5 个前端文件；后端零改动。 |
| **验证结果与回滚条件** | `npm run build` (`3.23s`) 零报错，全量 Vitest (`--minWorkers=1 --maxWorkers=2`) **`54/54` 文件 / `1244/1244` tests passed in `88.35s`**；未缓存空工作区（`8797` + `8798`）Chromium 实机验证 Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 全通过（0 console errors、0 HTTP `>=400`、0 横向溢出）。可按单提交安全回滚。 |

---

### DEC-OPS-009：突破 500 条视频大库上限、落地 SQLite `.backup()` 热快照及 `#Settings` 零扰动复审（2026-11-23 · Iteration #6 · `BL-008`）

| 评估维度 | 详细分析与证据 |
|---|---|
| **触发问题（架构审计 + 650 条基准压测）** | ① 650 条实机摸底（`state.sqlite3 = 4.94 MiB`）证实：`GET /api/v1/videos` 硬截断 200 条且缺少分页参数，`WorkspaceIntelligenceHub` 内部 8 处硬编码 `300`/`500` 条上限导致第 501 条之后的内容在跨库问答、周报汇总、专题与 Obsidian 导出中隐性失踪；<br>② Sidecar 库 `.workspace-ai/hub.sqlite3` 此前仅有 JSON 滚动快照而缺少原生 SQLite 在线一致性热备份，高并发读取路径（`/api/v1/sources`、`/api/v1/videos`、`/api/v1/intelligence`）在大库高负载下也存在重复扫描与整行反序列化冗余；<br>③ 需确认 `#Settings` 次级工程诊断区是否需要二次 UI 改版。 |
| **用户价值与预期收益** | 深度研究用户资料库突破 500–10,000 条后仍可零遗漏检索任意旧视频/本地笔记、分页拉取清单并获得 `PRAGMA integrity_check` 级零密钥热备份，同时不改变既有桌面/前端无参数契约、不新增重 UI 认知打扰（未来真实超大库长期表现待真实用户验证：`[待真实用户验证假设]`）。 |
| **三方案对比** | **方案 A（已选并执行，RICE `5.6`）**：<br>1. **向后兼容分页与全库分块读取（零 Schema 迁移）**：`SQLiteStateRepository` 扩展 `list_videos(*, limit=200, offset=0)`、`count_videos*` 与 `list_all_videos*`（默认 500/批、安全上限 10,000）；`LocalApiApplication` 与 `FastReadApiApplication` 在带查询串时返回 `pagination` 元数据与 `400 INVALID_QUERY` 参数校验，无查询串保持原 `{"videos": [...]}` 字节兼容；`WorkspaceIntelligenceHub` 通过 `_load_all_videos()` 替换全部 8 处 `300`/`500` 截断；<br>2. **SQLite 原生 `.backup()` 零密钥热快照**：新增 `create_sqlite_hot_snapshot()` 生成 `hub-snapshot.sqlite3`（`0o600` 原子替换 + `PRAGMA integrity_check == "ok"`），同步紧缩滚动 JSON 快照；<br>3. **冷读链路瘦身与 `#Settings` 零扰动复审**：优化 `compute_source_ai_signals` 4 列轻量查询、`FastReadApiApplication` 单次遍历 DA 解析与复用缓存指纹 `data_token` 的跨请求未篡改摘要内存索引（严格保留 fail-closed 篡改失效）；经代码复核 `#settings-legacy-diagnostics` 已在 `hasWorkspaceAi === true` 时默认折叠，决定对 `#Settings` 保持零前端改版；<br>**方案 B（修改 `videos` 核心 Schema 或强制改变无参 `/api/v1/videos` 结构）**：违背零迁移约束并会破坏已有前后端集成契约，**拒绝**；<br>**方案 C（把 `LIMIT` 简单改成硬编码 10000 并同步改写 `#Settings` 页面）**：单次全拉会拖慢首页加载并在无需求依据下平添 UI 波动，**拒绝**。 |
| **工程成本与副作用** | 修改 `state.py`、`local_api.py`、`fast_read_api.py`、`workspace_intelligence_hub.py` 4 个后端模块及 2 个集成测试文件；零 SQLite Schema 变更、零新依赖、零 `frontend/` 改动。 |
| **验证结果与回滚条件** | `ruff check` & `mypy src`（136 文件）0 错；**11 组 CI `pytest` 独立跑批 `143/143 passed in 505.13s`**（0 failed, 0 skipped）；Backup/Restore 专项 `27/27 passed in 59.89s`；600 条大库（`vidBig000–vidBig599`）实测分页 3 页 `[97.9, 48.1, 53.8]ms` 覆盖 600/600、跨库问答命中第 561 条（`vidBig560`）仅 **`0.23s`**、`obsidian-bundle?scope=all` & `.zip` 完整包含、核心库 `create_backup()` `1398.2ms`（600 篇）、`create_sqlite_hot_snapshot()` **`5.5ms`**（`53,248B`, `integrity_ok=True`, `zero_secret=True`）；cProfile 对比显示高负载下 `COLD /api/v1/videos` 从 `243.42ms` 降至 **`68.56ms`**（3.5x）、`COLD /api/v1/intelligence` 从 `48.92ms` 降至 **`21.90ms`**（2.2x）。可按单提交粒度安全回滚。 |

---

### DEC-OPS-010：长媒体（4 小时）与超长 Markdown 边界加固、Obsidian `.zip` 真解压修复与阶段退出门禁落地（2026-11-23 · Iteration #7 · `BL-010`）

| 评估维度 | 详细分析与证据 |
|---|---|
| **触发问题（实代码审计 + 真解压排雷）** | 针对“多小时本地课程 + 300KB+ Markdown 笔记 + Obsidian Vault 导出包”逐行审校并实测压测，发现 **5 项真实产品隐患**：<br>① `_safe_obsidian_title()` 仅截 120 字符，纯中文长标题可达 `360+` UTF-8 字节（超出 APFS/ext4 `255B NAME_MAX` 导致 `.zip` 解压报 `File name too long`），且未清理控制字符与 Windows 保留名（`CON`/`PRN`/`NUL`/`COM1–9`）；<br>② `_build_video_obsidian_markdown()` 使用 `line != ""` 粗暴清除全部空行，导致 `**关联主题双链**` 被误吸入引用块、`##` 标题粘连且文末缺换行，同时对纯文本笔记（`duration_seconds=None`）输出误导性的 `**时长**：`00:00``；<br>③ 5 处导出的 YAML Frontmatter 存在含引号/冒号/换行未转义漏洞；`build_obsidian_vault_zip()` `_alloc()` 仅做大小写敏感判重，在 macOS/Windows 解压 `"Guide"` 与 `"guide"` 时发生静默覆盖；<br>④ `_build_text_evidence_sections()` 对 >4,000 字长 Markdown 文档只顺次截取前 `~3,500` 字，导致 95%+ 长文尾段在 AI 提炼阶段静默丢失。 |
| **用户价值与预期收益** | 彻底保障深度研究者导入 4 小时长讲座（`<=14400s`）或 300KB+ 长 Markdown 手记时：AI 摘要全篇均匀覆盖、问答精确锚定末尾段落与 `HH:MM:SS` 时长，导出的 Obsidian `.zip` 在 macOS/Linux/Windows 任意真实 Vault 解压 0 崩溃、0 覆写、YAML 100% 合法、无 `00:00` 假时长；同步产出 [`RELEASE_READINESS_GATE.md`](./RELEASE_READINESS_GATE.md) 方便创始人评估合流与未来放行时机。 |
| **三方案对比** | **方案 A（已选并执行，RICE `22.5`）**：<br>1. `workspace_intelligence_hub.py`：新增 UTF-8 字节级安全截断（`<=180B`）、控制符剥离、`CON` 等 Windows 保留字加前缀 `_`、`json.dumps` 安全 YAML 标量引用 `_yaml_quoted`、视频/周报 CommonMark 空行修复、纯文本笔记去 `00:00` 改显 `载体：文本 / Markdown`、`used_paths_lower` 大小写不敏感增量防覆盖，以及 `_build_text_evidence_sections()` 超过预算后按全篇均匀多锚点采样（0%–96%+）；<br>2. 新增全链集成测试 [`test_long_media_and_obsidian_vault.py`](../tests/integration/test_long_media_and_obsidian_vault.py) 覆盖 4 小时讲座、300KB/2900 行 Markdown 与真实 `.zip` 落盘解压解析；<br>3. 梳理六维阶段退出检查单 [`RELEASE_READINESS_GATE.md`](./RELEASE_READINESS_GATE.md)。<br>**方案 B（放开单证据界面 `/evidence` 对 >21 片段的全量无上限加载）**：会直接拖垮首屏详情读性能且跨出既有前后端契约，**拒绝**（维持前 21 条展示有界，尾段由 FTS5 跨源问答直接检索与后端核验）。<br>**方案 C（把个人真实 Obsidian Vault 直接接入自动化测试目录）**：直接触犯零污染与隐私红线，**坚决拒绝**。 |
| **工程成本与副作用** | 修改 1 个后端模块 `workspace_intelligence_hub.py`，新增 1 套集成测试文件及 `RELEASE_READINESS_GATE.md`；零 DB Schema 变更，零依赖新增，零 `frontend/` 改动，零触碰个人真实 Vault。 |
| **验证结果与回滚条件** | `ruff check` & `mypy src`（136 文件）0 错；新增专项 [`test_long_media_and_obsidian_vault.py`](../tests/integration/test_long_media_and_obsidian_vault.py) **`3/3 passed in 19.04s`**；完整 11 组 Public Beta CI `pytest` 独跑 **`143/143 passed in 437.61s`**（0 failed, 0 skipped）；`security_scan.sh` 无新增告警、`product-ops/` 个人路径泄漏为 `0`。可按单提交粒度安全回滚。 |
