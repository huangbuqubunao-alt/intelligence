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

| 组件 | 等级 | 用途 | 所属任务 | 边界 |
|---|---|---|---|---|
| Python `sqlite3` / `importlib.resources` | `DIRECT` | SQLite、migration 资源 | TASK-003 | 不引入 ORM；项目自有 Schema/事务语义 |
| `pydantic>=2.13.4,<2.14` | `DIRECT` | 配置和领域边界校验 | TASK-002 | 不泄露密钥；公共对象以 ADR-002 为准 |
| `PyYAML>=6.0.3,<7` | `DIRECT` | YAML 配置 | TASK-002 | 只用安全加载；未知字段拒绝 |
| `yt-dlp[default,deno]>=2026.7.4,<2026.8` | `DIRECT` | YouTube 元数据、字幕目录、选中字幕正文、EJS challenge | TASK-004/005 | Python Adapter、只取选中字幕正文、无媒体下载/Cookie/remote components/ffmpeg；真实网络另批 |
| Python `json` / `html` / `unicodedata` / `hashlib` / `pathlib` / `tempfile` / `os` / `re` | `DIRECT` | JSON3/VTT/SRT 解析、NFC 规范化、哈希与原子文件处理 | TASK-005 | 按 ADR-006 的格式、质量、路径和日志边界实现；不新增解析依赖 |
| `mlx-whisper>=0.4.3,<0.5` | `DIRECT-PENDING` | Apple Silicon 本地转写 | TASK-006 | PyPI 0.4.3、MIT、Python >=3.8；含 MLX/torch 等传递依赖，安装与锁定仍须任务级批准 |
| Ollama `>=0.32.1,<0.33` HTTP API | `DIRECT-PENDING` | 本地评分 | TASK-007 | MIT；只允许 loopback 标准库 HTTP、固定模型 digest、无自动拉取；安装/服务/模型另批 |
| OpenAI SDK/API | `DIRECT-PENDING` | 可选云端分析 | TASK-008 | 默认关闭；依赖、密钥和真实调用分别审批 |
| Jinja2 | `DIRECT-PENDING` | Markdown 模板 | TASK-009/011 | 首次安装仍需任务级版本和锁文件批准 |

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
