# ADR-028：外部预置的 `o200k_base` 本地资源

## 状态

Accepted

## 日期

2026-08-31

## 背景

ADR-008 A-16 曾要求把 OpenAI Blob 的 `o200k_base.tiktoken` 作为固定包内资源
随 source、sdist 和 wheel 分发。`docs/O200K_BASE_REDISTRIBUTION_EVIDENCE.md`
已确认该 Blob 的身份和 SHA-256，但其下游文件级再分发权为 classification `C`：
权利人公开分发不等于项目获准再分发。

产品负责人已授权停止分发该文件，同时要求保持 ADR-008 的本地、精确、离线和失败
关闭语义。

## 决策

本 ADR 仅取代 ADR-008 A-16 的**包内存放和分发细节**；A-16 的其余安全与语义要求
继续有效。

- wheel、sdist 和项目可分发源不得包含 `o200k_base.tiktoken` 或其重命名、编码或
  变形副本。
- 合法取得该文件的用户或管理员必须在正常运行前，显式放置其副本于项目已验证
  `storage.data_dir` 下的固定路径 `tokenizers/o200k_base.tiktoken`。应用不创建、
  下载、镜像、复制或代理该文件。
- 运行时只接受普通、非符号链接文件；其长度和 SHA-256 必须分别精确为
  `3,613,922` bytes 和
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。
  期望身份固定在第一方代码中，不能由配置、环境变量、相邻元数据或网络响应修改。
- 缺失、不安全、大小错误、哈希错误或解析失败均在任何 Provider、凭据读取或网络
  副作用前以安全、可操作且不含绝对路径的本地配置错误失败。不得退回到另一编码、
  `tiktoken.get_encoding()`、缓存下载或任何近似计数器。
- 通过校验后，tokenization 仍在本地使用相同的 o200k ranks 和特殊 token 定义；正常
  运行不产生 tokenizer 网络请求，且预置后可离线运行。

## 备选方案

本决定采用 `O200K_BASE_REDISTRIBUTION_EVIDENCE.md` 的 Option 1。

- Option 2（安装器下载）增加获取、同意和供应链边界，且无法补足再分发权。
- Option 3（替代 tokenizer）不能证明与既有 o200k token 语义、预算和缓存条件相同。
- Option 4（仅作抽象修订）不单独提供可运行的安全预置边界；本 ADR 是该修订所需的
  最小实现化决定。

## 后果

- 新安装必须由用户或管理员完成一次显式资源预置；应用的 `doctor` 会报告资源的
  `READY`、`MISSING` 或 `INVALID` 状态而不泄露绝对路径。
- 既有开发安装不得被应用自动复制或迁移；升级说明只描述管理员的显式预置步骤。
- `o200k_base` 仍被产品本地使用，但不由项目再分发。历史 classification `C` 和
  权利不明结论保持不变。
- 请求、缓存、Provider、DACS、评分和 provenance 身份不因资源位置改变；仅同一
  固定身份的 ranks 被允许参与原有本地计数。
