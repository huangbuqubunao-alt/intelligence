# YouTube Intelligence Agent 复用登记表

- 状态：`ACTIVE`
- 初次核实：2026-07-14
- 决策规则：`docs/decisions/ADR-005-reuse-first-delivery-policy.md`
- 维护者：主控对话；Implementer 提出证据，Reviewer 独立复核

## 1. 使用方法

本文件记录“是否复用”的事实和取舍，不替代任务级依赖授权。候选首次进入实现前必须重新核实版本、许可证、依赖和安全边界。

| 等级 | 含义 | 落地要求 |
|---|---|---|
| `DIRECT` | 直接作为标准库、锁定包、SDK 或 CLI 使用 | Adapter 隔离、版本锁定、任务级授权、离线 Fake |
| `ADAPT` | 选择性移植兼容许可证的小型实现/测试 | 固定来源 commit、归属、改造成项目契约、补测试 |
| `REFERENCE` | 只借鉴设计、模板、测试或 UX | 不复制代码，不新增运行依赖 |
| `REJECT/DEFER` | 当前不采用或等待证据 | 记录否决原因和重新评估触发条件 |

## 2. 已批准直接复用

Phase 10B (2026-10-04): `DIRECT` Python standard-library HTTPS/TLS,
DNS/IP validation, JSON and SQLite; accepted source snapshot, timed transcript,
Summary, Evidence, Intelligence, Topic, Research, Delta and backup contracts.
`SourceContentPublisher` extracts the existing Local publisher without changing
its artifact/authority contracts. No production dependency or lockfile changes.
`REJECT/DEFER` browser login/cookies, generic scraping, yt-dlp Bilibili extraction,
media download, unqualified ASR, short-link resolution and creator polling.
Public adapter retrieval is bounded and fixture-tested; the actual public check
is recorded separately in `validation/phase10b/live-public-check.json`.

| 组件 | 等级 | 用途 | 所属任务 | 边界 |
|---|---|---|---|---|
| Python `sqlite3` / `importlib.resources` | `DIRECT` | SQLite、migration 资源 | TASK-003 | 不引入 ORM；项目自有 Schema/事务语义 |
| `pydantic>=2.13.4,<2.14` | `DIRECT` | 配置和领域边界校验 | TASK-002 | 不泄露密钥；公共对象以 ADR-002 为准 |
| `PyYAML>=6.0.3,<7` | `DIRECT` | YAML 配置 | TASK-002 | 只用安全加载；未知字段拒绝 |
| `yt-dlp[default,deno]>=2026.7.4,<2026.8` | `DIRECT` | YouTube 元数据、字幕目录、选中字幕正文、EJS challenge | TASK-004/005 | Python Adapter、只取选中字幕正文、无媒体下载/Cookie/remote components/ffmpeg；真实网络另批 |
| Python `json` / `html` / `unicodedata` / `hashlib` / `pathlib` / `tempfile` / `os` / `re` | `DIRECT` | JSON3/VTT/SRT 解析、NFC 规范化、哈希与原子文件处理 | TASK-005 | 按 ADR-006 的格式、质量、路径和日志边界实现；不新增解析依赖 |
| `mlx-whisper>=0.4.3,<0.5` | `DIRECT-PENDING` | Apple Silicon 本地转写 | TASK-006 | PyPI 0.4.3、MIT、Python >=3.8；含 MLX/torch 等传递依赖，安装与锁定仍须任务级批准 |
| Ollama `>=0.32.1,<0.33` HTTP API | `DIRECT-PENDING` | 本地评分 | TASK-007 | MIT；只允许 loopback 标准库 HTTP、固定模型 digest、无自动拉取；安装/服务/模型另批 |
| `openai>=2.46.0,<2.47` | `DIRECT` | Responses Structured Outputs | TASK-008A/008 | Apache-2.0；依赖动作已批但须固定任务包；禁止主进程导入，密钥和真实调用另批 |
| `tiktoken>=0.13.0,<0.14` | `DIRECT` | 本地 token 采样与保守预算 | TASK-008A/008 | MIT；显式 model/encoding 映射；ADR-028 下只读管理员显式预置的 `o200k_base`，不调用云端计数或网络回退 |
| OpenAI 官方 `o200k_base.tiktoken` Blob | `DIRECT` | `o200k_base` rank 表；固定 SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` | ADR-028：用户/管理员在 `data_dir/tokenizers` 显式预置；项目不再携带或分发 | classification C 保留；哈希/缺失失败关闭，不使用 tiktoken HTTP cache fallback |
| `Jinja2>=3.1.6,<3.2` | `DIRECT` | 固定 Markdown 模板 | TASK-009A/009/011 | BSD-3-Clause；依赖动作已批，使用不可变 sandbox/StrictUndefined，无用户模板或任意 loader |
| `spacy==3.8.15` / `en_core_web_sm==3.8.0` | `DIRECT` | TASK-016B 保守英文依存结构验证 | TASK-016B | MIT；固定官方模型 wheel/hash；只从已安装包加载，缺失或失败返回 `UNCERTAIN`；禁止下载、网络 fallback 与远程模型地址；公开分发前仍须完成模型来源 NOTICE 复核 |
| Python `argparse` / `json` / `logging` / `uuid` / `zoneinfo` | `DIRECT` | CLI、JSONL、run_id、ISO 周与日志边界 | TASK-011/012 | 标准库；不引入 CLI/调度框架，不记录敏感内容 |

## 3. 附件候选评估

### 3.1 `imlewc/video-to-subtitle-summary-skill`

- 来源：[GitHub](https://github.com/imlewc/video-to-subtitle-summary-skill)，MIT；调研快照 commit `2c794d74`，2026-07-14 调研时 124 stars，最近代码提交 2026-05-26。
- 结论：`ADAPT/REFERENCE`，不作为运行时依赖。
- 可复用：yt-dlp `--ignore-config`/`--skip-download` 防御性选项、语言偏好测试、VTT→SRT/纯文本夹具和无视频下载断言。
- 不直接采用：以 Skill + subprocess 为核心；默认 `faster-whisper` 在 Apple Silicon 走 CPU；还包含 ffmpeg、付费视频代理、`.env` 与直接文件输出，均与 V1 已批准的 MLX、Provider、密钥和 Artifact 边界不一致。
- 落地：TASK-005 可在固定 commit 上复核字幕清洗测试；如复制实质代码必须保留 MIT 来源和修改说明。TASK-004 不下载字幕，不能提前移植。

### 3.2 `hailanlan0577/yt2md`

- 来源：[GitHub](https://github.com/hailanlan0577/yt2md)，MIT；调研快照 commit `8a845642`，2026-07-14 调研时 1 star、单次初始提交（2026-04-11）、单文件实现且路线图仍标注缺少 pytest。
- 结论：`REFERENCE`；仅在小范围测试充分时允许升级为 `ADAPT`。
- 可参考：URL/ID 规范化、缓存版本字段与原子临时文件思路、安全文件名、时间戳 Markdown 和无云密钥时降级。
- 不直接采用：依赖 `youtube-transcript-api`、requests、BeautifulSoup 和 DashScope；自动读取 macOS Obsidian 配置并直接写 Vault；没有本项目的边界检查、状态恢复、用户区保留和任务审计。
- 落地：TASK-009 可参考输出结构，但模板和安全 upsert 必须由本项目实现并测试。

### 3.3 `Xpos587/yt2md`

- 来源：[GitHub](https://github.com/Xpos587/yt2md)，MIT；调研快照 commit `ad9775fb`，最近代码提交 2025-05-14。
- 结论：`REJECT` 直接或代码适配；只允许参考时间戳链接的产品表现。
- 原因：新增未批准的 `aiohttp/aiohttp_socks`；直接正则解析 YouTube 内部页面；源码显式关闭 TLS hostname 和证书校验；无对应测试目录。该安全实现不能进入本项目。

### 3.4 `ZeroPointRepo/youtube-skills`

- 来源：[GitHub](https://github.com/ZeroPointRepo/youtube-skills)，MIT；调研快照 commit `d4b7a18f`，2026-07-14 调研时 329 stars，最近代码提交 2026-05-20。
- 结论：V1 `REJECT` 运行时复用。
- 原因：所有能力依赖 TranscriptAPI 远程服务、账号、API key 和 credits；安装说明包含把密钥写入 shell/Agent 配置的流程。它与 DEC-01 的 RSS + yt-dlp、云端最小化和本地优先边界冲突。
- 重新评估条件：只有本地 yt-dlp 在真实验收中持续不可用，且产品负责人批准新的远程 Provider、数据发送、密钥和成本 ADR 后，才能作为可选 fallback。

### 3.5 “YouTube & Podcast Transcript Summaries to Obsidian”

- 来源：仅附件中的显示名称；截至 2026-07-14，GitHub 精确代码/仓库搜索未定位到可验证的唯一仓库。
- 结论：`DEFER`。
- 原因：缺少 URL、许可证、代码、依赖和维护证据，不能仅凭截图引入。
- 重新评估条件：获得项目 URL 或准确作者/仓库名后，按 ADR-005 完整评估。

## 4. 其他相关候选

| 候选 | 结论 | 依据 |
|---|---|---|
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | `REFERENCE/DEFER` | MIT、活跃，但其 YouTube converter 的短链/API 兼容问题 [#1704](https://github.com/microsoft/markitdown/issues/1704) 在 2026-07-14 仍为 open；不作为 YouTube 核心 |
| [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | `DEFER` | MIT、活跃、无需 API key；仅当 TASK-005 证明 yt-dlp 字幕路径不足时再申请依赖批准，不与 yt-dlp 重复引入 |

## 5. 本项目应自有的部分

以下能力不能被外部端到端工具替代：

- 配置、领域对象和三层状态契约。
- SQLite Schema、Job 租约、恢复、Provider call 缓存和审计。
- 价值评分策略、云端开关、预算和隐私。
- Obsidian 路径边界、原子 upsert、Frontmatter 与 `我的思考` 保留。
- 周报幂等、CLI 编排、结构化日志和发布验收。

这不是“重复造轮子”，而是产品的差异化控制面；底层抓取、模型和模板能力继续优先复用成熟组件。

## 6. TASK-005 已批准复用边界

- ADR-006 T-12 已批准在 TASK-004 整合后复用锁定的 `yt-dlp==2026.7.4` Python API 和 Python 标准库；不新增或升级生产依赖，不修改 `pyproject.toml`/`uv.lock`。
- `imlewc/video-to-subtitle-summary-skill@2c794d74` 仅 `ADAPT/REFERENCE` 语言排序、清洗夹具和无下载断言；不得复制其 subprocess、ffmpeg、代理、付费 API、`.env` 或直接文件输出架构。
- `youtube-transcript-api` 继续 `DEFER`；只有 yt-dlp 经正式实现/审查证明不足时，才重新提交依赖和许可证审批。
- 真实 YouTube/字幕、Cookie/登录、`.netrc`、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权；ADR-006 接受不改变这些门禁。

## 7. ADR-007 已接受的 TASK-006/TASK-007 复用边界

以下为 ADR-007 已接受的设计与复用结论，不是安装、下载、服务启动或真实调用授权。
TASK-005A 只直接复用现有 `pydantic`、SQLite Repository 和 Python 标准库，不新增
第三方组件；TASK-006/TASK-007 的首次实际使用仍须在实施时重新复核版本、许可证和
维护状态。

| 组件 | 推荐等级 | 已核实证据 | 待批准/剩余风险 |
|---|---|---|---|
| `mlx-whisper>=0.4.3,<0.5` | `DIRECT-PENDING` | PyPI 最新稳定 0.4.3（2025-08-29）、MIT、Python >=3.8、pure Python wheel；官方包依赖 MLX、numba、numpy、torch、tqdm、more-itertools、tiktoken、huggingface_hub、scipy | Python 3.12/arm64 实际解析、传递版本、安装体积与资源冒烟 |
| `mlx-community/whisper-large-v3-turbo` | `DIRECT-PENDING` | revision `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`；权重 1,613,977,612 bytes；LFS SHA-256 `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6` | 转换仓库 model card 无 license metadata；网络下载、磁盘、缓存和本机推理另批 |
| FFmpeg 8.1.2（Homebrew） | `DEFER` | mlx-whisper 官方文件加载调用 ffmpeg；Homebrew 当前公式提供 Apple Silicon bottle | Homebrew build 标记 GPL-3.0-or-later；安装、调用、压缩音频冒烟与分发决策另批 |
| Python `urllib.request` / `json` | `DIRECT` | 标准库足够完成单机低并发 Ollama HTTP、响应限流、关闭与 Fake transport | 由共享契约冻结 loopback、安全读取和错误映射 |
| Ollama `>=0.32.1,<0.33` | `DIRECT-PENDING` | 官方项目 MIT；API 默认本地 `11434`；支持 `/api/tags` 与 `/api/generate` JSON Schema/`stream=false`/`think=false` | 安装、启动、本机服务访问、no-cloud 运行与版本验证另批 |
| `qwen3:8b` | `DIRECT-PENDING` | Ollama digest `sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`；model layer 5,225,374,496 bytes、Q4_K_M；上游 Qwen3-8B 为 Apache-2.0 | 模型拉取、磁盘/内存、中文评分基线与黄金样例另批 |
| `httpx` / Ollama Python SDK | `DEFER/REJECT` | 当前低并发本地接口不需要额外运行依赖 | 若未来标准库证据不足，必须另提版本、锁文件与下载审批 |

官方来源记录在 `docs/decisions/ADR-007-local-model-pipeline-contracts.md`。首次实施前
Implementer 仍须重新核实版本、许可证和维护状态，Reviewer 独立复核。

## 8. ADR-008/ADR-009 已批准复用边界

以下结论来自 2026-07-20 的两份只读 Scout 和官方资料复核。产品负责人已批准三项
精确依赖范围、必要传递依赖、网络包下载、锁文件和共享任务离线命令；实际动作仍须
在固定 TASK-008A/TASK-009A 分配包内执行。真实密钥、付费调用、云端 token-count
和 Vault 写入继续未授权。

| 组件 | 推荐等级 | 已核实证据 | 冻结建议/剩余门禁 |
|---|---|---|---|
| `openai>=2.46.0,<2.47` | `DIRECT` | PyPI 2.46.0（2026-07-17）、Apache-2.0、Python >=3.9；官方 SDK 以 Responses 为主 API，支持 Structured Outputs；2.46.0 顶层导入会读取 OpenAI/Azure 环境变量 | TASK-008A 显式锁定；TASK-008 禁止主进程导入，只可在清空/白名单化环境的隔离子进程导入，导入后由匿名管道接收密钥；真实密钥/API 另批 |
| `tiktoken>=0.13.0,<0.14` | `DIRECT` | PyPI 0.13.0（2026-05-15）、MIT、Python >=3.9，提供 CPython 3.12 macOS arm64 wheel；当前已由 mlx-whisper 传递锁定 | TASK-008A 提升为直接依赖；只做本地 28k 保守计数和显式 encoding 映射，未知模型失败关闭 |
| OpenAI 官方 `o200k_base.tiktoken` | `DIRECT` | 官方 Blob URL；tiktoken 0.13.0 映射的 expected hash 为 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` | ADR-028：运行时只接受管理员显式预置到固定 `data_dir/tokenizers` 路径且匹配 expected hash 的本地资源；空资产/断网不得触发下载；项目不再分发该 Blob，classification C 保留 |
| `Jinja2>=3.1.6,<3.2` | `DIRECT` | PyPI 3.1.6、BSD-3-Clause、Python >=3.7；当前已由 torch 传递锁定 | TASK-009A 提升为直接依赖；只加载固定包内模板，使用 `ImmutableSandboxedEnvironment` + `StrictUndefined`；sandbox 不用于执行用户模板 |
| OpenAI `/v1/responses/input_tokens` | `REJECT` 默认路径 | 官方提供精确请求 token 计数 | 计数本身会发送最小化字幕 payload 并消耗调用/隐私预算；V1 默认改用本地保守计数 |
| 手写 OpenAI HTTP / 手写 Markdown 模板 | `REJECT` | 官方 SDK/Jinja2 已覆盖通用协议和模板能力 | 项目只实现隐私、预算、领域、路径、原子写和恢复控制面 |
| 已登记 yt2md 候选 | `REFERENCE` | 输出结构、文件名和原子临时文件思路可参考 | 不复制代码、不读取 Obsidian 配置、不直接访问真实 Vault |

官方来源：

- OpenAI Responses：<https://platform.openai.com/docs/api-reference/responses>
- OpenAI Structured Outputs：
  <https://platform.openai.com/docs/guides/structured-outputs>
- OpenAI SDK：<https://pypi.org/project/openai/>
- tiktoken：<https://pypi.org/project/tiktoken/>
- OpenAI 官方 `o200k_base` Blob：
  <https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken>
- tiktoken 0.13.0 官方 encoding 映射：
  <https://github.com/openai/tiktoken/blob/0.13.0/tiktoken_ext/openai_public.py>
- OpenAI Python 2.46.0 顶层导入：
  <https://github.com/openai/openai-python/blob/v2.46.0/src/openai/__init__.py>
- Jinja sandbox：<https://jinja.palletsprojects.com/en/stable/sandbox/>
- Jinja2：<https://pypi.org/project/Jinja2/>

## 9. 前端开源 UI/UX 设计系统与阅读工作台复用登记（2026-11-12）

本节登记普通用户完整链路 UI/UX 改造的开源组件评估、许可证审计与适配边界。严格遵守
`AGENTS.md` 第 4.1 与第 5 节：优先适配（`ADAPT`）MIT 开源组件源码，**不新增生产运行时依赖、
不修改 `frontend/package.json` 或 `frontend/package-lock.json`**；对 AGPL-3.0 协议的整套端到端阅读器
产品仅作交互布局参考（`REFERENCE`），严禁复制任何代码。

| 组件 / 仓库 | 复用决策 | 上游精确基线与许可证证据 | 适配位置与修改说明 |
|---|---|---|---|
| `shadcn-ui/ui` | `ADAPT` | <https://github.com/shadcn-ui/ui>，commit `dd41d19e2f80ff6891951f7ced74c2c9a650b065`（2026-11-11），SPDX **MIT**；参考 `apps/v4/app/(app)/(styles)/sera/style.css`、`apps/v4/registry/styles/style-nova.css`、`apps/v4/registry/new-york-v4/ui/command.tsx` | 适配至 `frontend/src/workspace/styles.css` 与 `frontend/src/workspace/ui/theme.tsx`：引入三层语义化 Token（OKLCH + sRGB 回退），提供默认深色「黑曜石（Obsidian Dark）」与护眼浅色「暖纸阅读（Warm Paper Light）」双主题，并对齐 Card、Badge、Segmented Tabs 与 Command 浮层视觉层级 |
| `phosphor-icons/core` | `ADAPT` | <https://github.com/phosphor-icons/core>，commit `2b75f3ad12b420c9504ef05df8d2564a28f8500e`（2026-01-06），SPDX **MIT**；直接提取 `assets/regular/*.svg` 与 `assets/fill/*.svg` 官方 256×256 几何矢量路径 | 适配至 `frontend/src/workspace/ui/phosphorIcons.tsx`（及 `motion.tsx` 导出桥接）：全面替换手写 SVG 占位图形，主导航未激活态采用 `regular` 字重、激活态切换为 `fill` 实心字重，统一所有图标 `aria-hidden="true"` 装饰契约 |
| `dip/cmdk` (`pacocoursey/cmdk`) | `ADAPT` | <https://github.com/dip/cmdk>，commit `dd2250ed608443e8f32bafc5fa2d1d07a3746aa3`（2025-10-29），SPDX **MIT**；适配 `cmdk/src/command-score.ts` 连续字符/词首跳跃/转置模糊打分算法与无障碍列表键盘状态机 | 适配至 `frontend/src/workspace/ui/CommandPalette.tsx`：零依赖实现全局 `⌘K` / `Ctrl+K` 命令与内容库瞬时检索面板，补充中文/CJK 子串权重增强，支持一键直达六大视图、已加载视频 Content、已验证洞察、Topic、导入入口与中英/深浅色切换 |
| `argyleink/open-props` | `ADAPT` | <https://github.com/argyleink/open-props>，commit `f39ab7c377a0e047f930982e3611bbc95254a260`（2026-10-11），SPDX **MIT**；参考 `src/props.easing.css` 与 `src/props.shadows.css` | 适配至 `frontend/src/workspace/styles.css`：引入 `--ease-out-3`、`--ease-out-4`、`--ease-out-5` 自然减速曲线与多层环境光阴影梯度（`--shadow-1`、`--shadow-2`），消除生硬过渡并严守 `prefers-reduced-motion: reduce` |
| `RSSNext/Folo` / `karakeep-app/karakeep` | `REJECT`（代码）/ `REFERENCE`（UX） | Folo commit `577846bd1db5c5c8341c96709219d2b72f34a027`（**AGPL-3.0**）；Karakeep commit `f7119ca01004f4840b8a7189d2899945ea3966a3`（**AGPL-3.0**） | 因 AGPL-3.0 传染性协议明确拒绝任何代码复制与嵌入；仅借鉴现代知识阅读器信息架构：桌面双栏非对称工作台、长文详情吸顶章节速跳栏（Sticky TOC）、内容列表即时筛选栏与纸感浅色阅读模式 |
