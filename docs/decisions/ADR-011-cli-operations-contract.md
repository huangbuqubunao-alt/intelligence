# ADR-011：CLI、日志与静态 launchd 契约

## 状态

Accepted

## 日期

2026-07-23

## 背景

现有入口仅有最小 argparse parser，没有稳定命令语义、结构化日志或安全 launchd 样例。CLI 必须可诊断和恢复，且不能绕过既有任务、隐私或真实资源门禁。

## 决策

### O-01：命令和退出码冻结

提供 `check`、`process`、`retry`、`doctor`；`weekly` 仅在 TASK-011 整合后接入。退出码固定为：`0` 全部成功、`1` 至少一个已执行项目失败或部分失败、`2` 用法/配置/前置条件错误、`3` 本地资源或持久化不可用。不得以部分失败伪装成功。

### O-02：doctor 严格零昂贵副作用

`doctor` 只检查配置结构、项目内目录边界、SQLite 可打开/迁移一致性、Vault 路径边界和启用 Provider 配置。它不得创建 Job、处理视频、调用 Provider、探测 loopback 服务、读取密钥值、访问网络或 Vault 内容。

### O-03：结构化 JSONL 与安全 run_id

每次命令生成 UUID4 `run_id`。JSONL 必填 `timestamp`、`level`、`event`、`run_id`、`stage`、`safe_message`，可选 `video_id`、`job_id`、`error_code`、`duration_ms`。禁止记录密钥、字幕全文、原始模型响应、本地绝对路径、用户笔记或自由异常 traceback。

### O-04：不自动删除日志

记录 30 天保留策略，但 TASK-012 不自动清理或删除日志；任何未来清理必须单独授权并限制在已配置 `logs_dir`、无 symlink、受锚定目录和安全相对路径内。

### O-05：launchd 仅为静态可选样例

提供互斥的有效 daily 和 weekly plist examples，配套安装/卸载说明。用户在安装前选择一个计划；示例必须可通过 `plutil -lint`，但 TASK-012 不执行 `launchctl`、不注册、加载或启动服务。daily/weekly 计划和 WorkingDirectory 只能通过明确文档占位符/示例值配置，不能由应用自动改写。

### O-06：TASK-012 分阶段接入

TASK-012 的 `weekly` 命令依赖 TASK-011 的已整合周报服务；在此之前 TASK-012 保持 `BLOCKED`。后续范围可包括 `__main__.py`、`cli.py`、`logging.py`、daily/weekly static plist examples、安装说明、operations tests 与 handoff；不得新增依赖、Schema/migration、真实服务或资源操作。

## 后果

- CLI 与 launchd 不会隐式扩大网络、Provider、Vault 或密钥权限。
- 周报服务先完成，避免 TASK-011 与 TASK-012 在未冻结接口上并行冲突。
- Python 标准库优先承担 argparse、JSONL、logging、UUID 与文件边界；无需新增依赖。
