# YouTube Intelligence Agent

一个面向单个操作者的、本地优先的 YouTube 知识采集工具：发现频道视频、取得字幕或在
获批条件下本地转写、进行本地评分，并仅在明确启用时使用云端分析，最后写入 Obsidian
笔记与周报。

## 发布状态：No-Go

本仓库已有固定夹具、临时 SQLite/DATA/Vault 和 Fake Adapter 的离线验收证据；它**不等于**
真实环境验证。当前没有获得正式发布、真实 smoke、二进制或捆绑依赖分发的批准。完整
原因和签署门禁在 [发布检查表](docs/RELEASE_CHECKLIST.md)、
[SBOM](docs/SBOM.md)、[第三方 NOTICE 清单](docs/THIRD_PARTY_NOTICES.md) 和
[四阶段 smoke 授权矩阵](docs/SMOKE_AUTHORIZATION_MATRIX.md)。

尤其不得把本 README 视为以下任何操作的授权：真实 YouTube/字幕或媒体访问、ffmpeg、
Whisper 模型、Ollama/模型、OpenAI API/密钥/付费调用、真实 Obsidian Vault 或 launchd。

## 已有的离线证据与边界

- TASK-013 的离线验收报告记录了固定样例、恢复路径、临时 Vault 和 Fake 外部 Adapter
  的结果；详见 [验收报告](docs/ACCEPTANCE_REPORT.md)。
- 云端分析默认关闭。正式实现的 OpenAI SDK 导入必须在白名单环境的隔离子进程中完成，
  密钥只可在导入握手后通过匿名管道传入；详见 ADR-008。
- `o200k_base.tiktoken` 是固定的包内资源，运行时无网络回退，且其哈希固定为
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。文件级
  许可证、归属和 NOTICE 尚未决，因此任何包含它的发行物仍被阻断。
- 恢复语义是 **at-most-once best effort**，不是严格 exactly-once：外部 Provider
  成功到 SQLite 提交、文件原子 replace 到 SQLite 提交、以及音频清理的最终 CAS 都仍有
  崩溃窗口。不得将离线恢复测试表述为消除了这些窗口。

## 计划中的本地安装与初始化（尚未作为发行验证）

目标环境为 macOS Apple Silicon 与 Python 3.12+。锁定的依赖和构建元数据在
`pyproject.toml` 与 `uv.lock` 中；在发布签署和对应环境授权完成后，操作者应从干净
工作目录按以下顺序执行并保留证据：

1. 从 `config/settings.example.yaml` 和 `config/channels.example.yaml` 创建本地配置副本；
   不提交配置副本、密钥或 Vault 路径。
2. 使用锁定依赖完成安装；发布前必须重新核对锁文件、SBOM、许可证和分发形态。
3. 在受控的、非真实 Vault 环境初始化 `data/` 与 `logs/`；这两个路径现在只会在仓库根
   匹配，嵌套的源码、测试夹具和文档目录不会被此规则静默忽略。
4. 先运行 `youtube-intel doctor`。它检查 YAML、项目相对存储路径、已有 SQLite migration
   记录、Vault 路径边界和启用 Provider 配置；它不读取密钥值、Vault 内容，不访问网络，
   也不探测 Provider。

`doctor` 需要已有的 `data/state.sqlite`。若该文件不存在或 migration 记录不一致，它会以
本地资源/持久化失败退出，而不是创建或修复数据。实际命令、退出码和运行边界见
[运维说明](docs/operations.md)。

## 手动运行与调度

可用命令语义由 [运维说明](docs/operations.md) 冻结：`check`、`process`、`retry`、
`weekly` 与 `doctor`。`check`/`process`/`retry` 可能进入外部资源路径；只有在适用的
smoke 阶段获得书面授权后才能使用。

仓库只提供两个静态 launchd 示例。操作者必须择一复制到仓库外、替换项目根占位符，并
在人工确认后自行执行 `plutil -lint` 和任何 `launchctl` 操作；本项目不会安装、加载、
卸载或注册 launchd 服务。

## 备份与恢复发布门禁

发布前必须在**临时数据与临时 Vault**上完成并记录一次恢复演练。建议的受控步骤是：

1. 停止该临时环境的处理命令，并保存同一时点的 SQLite 状态、其 WAL/SHM 伴随文件（如有）、
   受管 DATA 和临时 Vault 内容。
2. 仅恢复到新的隔离临时位置；不得覆盖用户真实 Vault 或真实运行数据。
3. 对恢复副本运行 `doctor`，然后执行已授权的离线恢复检查，比较迁移记录、Artifact
   哈希、受管笔记/周报与预期 Job/Pipeline 状态。
4. 记录命令、版本、Schema 版本、输入范围、结果和失败处置。任何不一致均为 No-Go，
   应创建范围明确的修复任务。

本阶段没有执行上述步骤，因而没有备份/恢复通过声明。

## 重要操作边界

- 不提交 `.env`、密钥、私人字幕、用户笔记、SQLite、运行 DATA 或日志。
- 云端关闭、预算耗尽、缓存命中、低价值或凭据缺失时不得调用 OpenAI。
- 真实 Vault 始终需要单独授权；临时 Vault 也只可按任务/检查表明确授权使用。
- 发布前的签署人和阻断条件以 [发布检查表](docs/RELEASE_CHECKLIST.md) 为准，而非本
  README 的描述。
