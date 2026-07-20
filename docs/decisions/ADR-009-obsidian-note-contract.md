# ADR-009：Obsidian 视频笔记契约

## 状态

Accepted

## 日期

2026-07-20

## 批准记录

- 批准日期：2026-07-20
- 决策人：用户（产品负责人）
- 批准范围：ADR-009 N-01 至 N-15，以及 TASK-009A 使用
  `Jinja2>=3.1.6,<3.2`、必要传递依赖、网络包下载、`pyproject.toml`/`uv.lock`
  修改和任务卡离线 uv 验证/构建命令。
- 执行顺序：TASK-009A 继续等待 TASK-008A `DONE`，之后仍须获得固定
  base/worktree/角色/文件范围才能执行。
- 继续未授权：真实 Vault、真实用户笔记、最终文件删除/移动/重命名、真实 OpenAI/
  密钥/付费调用和云端 token-count 请求。

## 背景

TASK-009 只读预检确认，现有 `KnowledgeSink`、`NoteRef`、`ArtifactWrite` 和
`complete_stage` 可以支撑首次笔记写入，但公共接口、文件身份、模板、用户区、路径
边界和故障恢复仍未冻结。当前 `analysis=None` 也无法区分云端关闭、预算耗尽、凭据
缺失或 Provider refusal。

本文在 ADR-008 的结构化 `AnalysisOutcome` 之上冻结共享契约和文件垂直切片。接受
本 ADR 不授权访问真实 Vault，也不授权删除、移动或接管任何真实笔记。

## 推荐决策

### N-01：TASK-009A 顺序消费 TASK-008A

新增 `TASK-009A：Obsidian 笔记共享契约与依赖基线`，依赖 TASK-008A。它只收紧
`KnowledgeSink`、`NoteRef` 和 Jinja2 依赖基线，不实现文件写入、不修改
`state.py`/Schema/migration。TASK-009A `DONE` 后，正式 TASK-008/TASK-009 才可
从同一最新 main 并行。

### N-02：KnowledgeSink 接收最终策略和稳定上下文

接口固定为 keyword-only：

```python
upsert_video_note(
    *,
    video: VideoMetadata,
    transcript: TranscriptArtifact,
    scoring: ScoringOutcome,
    analysis: AnalysisOutcome,
    processed_at: datetime,
    pipeline_version: str,
) -> NoteRef
```

`processed_at` 必须是稳定 Job 时间、UTC aware；`pipeline_version` 必须非空且去除
首尾空白。接口不得自行评分、调用云端、读取字幕 Provider 或使用自由 `dict`。

### N-03：资格、普通重跑与刷新边界

- 低价值或 `final_should_summarize=false`：sink 被调用即失败关闭，零 Vault 写入。
- 高价值：只在 `ANALYSIS_READY` 且持有有效 `NOTE_WRITE` Job 时首次写入/失败重跑。
- `AnalysisCompleted` 渲染完整分析；`AnalysisSkipped` 渲染明确原因，不编造内容。
- 已 `NOTE_WRITTEN`/`COMPLETE` 的普通重跑只验证并返回现有 NoteRef，零改写。
- 已成功笔记的主动刷新延期到 TASK-010 的新 pipeline version/显式产品动作。

V1 不为成功刷新新增 Repository 方法，不修改 `state.py` 或 Schema。

### N-04：NoteRef 必须证明逻辑相对身份

`NoteRef.relative_path` 必须是规范 POSIX 相对 `.md` 路径：禁止空/`.`/`..`、绝对
路径、反斜杠、盘符、NUL、空组件和首尾空白。`content_hash` 必须是 64 位小写
SHA-256。新/收紧的公共契约必须禁止未验证 `model_copy(update=...)`。

路径始终相对逻辑锚点 `vault_root/vault_subdir`；NoteRef 与 VAULT Artifact 使用
完全相同的相对路径，不记录绝对 Vault 路径。

### N-05：文件身份由 video_id 固定

文件名固定为 `<safe-title>--<video_id>.md`：

- video_id 匹配 `[A-Za-z0-9_-]{6,32}`；
- 标题先 NFC，只保留 Unicode 字母、数字、组合标记、空格、`-_.()`；
- 控制/路径/Obsidian/Windows 保留字符转为 `-`，连续空白/替换符合并；
- 去除首尾空格、点和横线，空结果回退 `video`；
- Windows 设备保留名大小写不敏感时加 `video-`；
- safe title 按完整 Unicode code point 截至 120 UTF-8 bytes 后再次清理。

首次路径固定后不因标题变化自动 rename/delete。多个 `--<video_id>.md` 候选、
NFC/casefold 冲突、非受管占位或 video_id 不匹配全部失败关闭，不生成递增后缀。

### N-06：Vault 边界采用 anchored directory FD

配置继续要求绝对 `vault_root` 和安全相对 `vault_subdir`。每次写入必须：

- 验证 root/subdir 为真实目录，只允许安全创建受管 `Videos`；
- 对 root 最终组件、subdir、Videos、临时和最终文件拒绝 symlink；
- 使用 directory FD、`O_DIRECTORY`、`O_NOFOLLOW`、`lstat/fstat`；
- replace 前后复核目录 inode/device 和目标身份；
- 拒绝绝对 child、反斜杠、盘符、`.`/`..`、非目录父级和目录替换竞态。

错误不得包含绝对 Vault 路径，也不得触碰任何其他笔记。

### N-07：管理区和用户区语法固定

四个 marker 精确为：

```text
<!-- youtube-intel:managed:start:v1 -->
<!-- youtube-intel:managed:end:v1 -->
<!-- youtube-intel:user:start:v1 -->
<!-- youtube-intel:user:end:v1 -->
```

它们必须各出现一次、独占一行、零缩进、LF、固定顺序且不嵌套。首次用户区内容精确
为 `## 我的思考\n\n`。更新时逐字节保留 user-start 行结束后到 user-end 行开始前
的内容。

缺失、重复、嵌套、畸形 marker，非法 UTF-8，Frontmatter/video_id 不符，
legacy/unmanaged 文件均失败关闭、原文件不变；不得自动修复或接管。

### N-08：Frontmatter 和正文结构稳定

Frontmatter 字段顺序固定为：

1. `type`
2. `video_id`
3. `title`
4. `channel`
5. `published`
6. `source`
7. `language`
8. `transcript_source`
9. `score`
10. `topics`
11. `processed_at`
12. `pipeline_version`

字符串使用双引号 YAML scalar，score 为 float，topics 为有序字符串列表，
`processed_at` 为 UTC RFC3339 微秒 `Z`。使用现有 PyYAML 安全专用 Dumper，禁止
Python tags、aliases 和自由对象。

正文固定包含总结、本地评分/理由、核心观点、关键事实、产品机会、商业机会、可落地
方向、待验证假设、行动建议、风险、证据、标签和用户区。分析被跳过时写入结构化、
诚实的跳过说明。

### N-09：Jinja2 只渲染固定打包模板

推荐 `Jinja2>=3.1.6,<3.2` 作为显式直接依赖，使用：

- `ImmutableSandboxedEnvironment`
- `StrictUndefined`
- `autoescape=False`
- 无任意 loader、include/import、用户模板、自定义 globals 或可调用对象

模板固定为包内 `src/youtube_intel/templates/video.md`，通过
`importlib.resources` 加载并进入 sdist/wheel。只传入预先转义和设限的 primitive。
Sandbox 是纵深防御，不被视为执行不可信模板的安全边界。

### N-10：模型文本和资源必须设限

模型文本先转换为安全 inline/list/blockquote 数据；任何 Frontmatter 分隔符或四个
marker 样式都不得形成结构控制行。topics/keywords 不自动拼成不可信 hashtag 或
wikilink，URL 用解析器生成。

- 单个模型字段沿用领域上限；
- 管理区渲染后最多 1 MiB；
- 读取的既有笔记最多 5 MiB；
- 超限、迭代异常或模板未定义变量均失败关闭，旧文件不变。

### N-11：文件提交采用同目录原子替换

固定算法：

1. 严格读取/验证旧文件，记录 inode、mode、哈希；
2. 渲染规范 UTF-8、LF、末尾换行 bytes 并计算 SHA-256；
3. 完全相同则不替换文件；
4. 同目录用随机名、`O_CREAT|O_EXCL|O_NOFOLLOW` 和 0600 创建临时文件；
5. 写入、flush、fsync、同 FD 回读校验；
6. 复核旧文件未被用户并发修改、目录链和目标身份；
7. `os.replace` 后重开验证并 fsync 目录。

失败只清理本次拥有的临时文件；replace 后不得回滚、删除最终笔记或覆盖用户后续
编辑。

### N-12：SQLite 完成与文件恢复沿用现有语义

文件成功后调用现有 `complete_stage`，写
`VIDEO_NOTE`/`VAULT`/`LONG_LIVED` Artifact，执行
`ANALYSIS_READY -> NOTE_WRITTEN` 并完成 Job；`provider_call=None`。

Artifact 身份覆盖 video_id、job_id、pipeline_version、relative_path、
producer_version 和全文件哈希（含用户区）。文件 replace 后、SQLite 提交前崩溃
时，重排验证现有完整文件并补账；SQLite 失败不删除最终笔记。V1 只承诺
at-most-once best effort，不声称文件系统和 SQLite 严格单事务。

### N-13：错误映射使用现有八类

- 静态配置/模板包错误：`CONFIG_INVALID`
- managed-file 冲突、marker/provenance/竞态：`INVALID_RESPONSE`
- `EACCES`/`EPERM`/`EROFS`：`PERMISSION_DENIED`
- `ENOSPC`/`EDQUOT`/`EIO`/fsync/replace 资源失败：`LOCAL_RESOURCE`

异常图必须安全化，不含绝对路径、旧/新笔记正文或用户区内容。不得新增
`NOTE_CONFLICT` 等 ErrorCode。

### N-14：依赖、复用与并行隔离

TASK-009A 独占把已锁定的 Jinja2 提升为直接依赖：

- `Jinja2>=3.1.6,<3.2`，BSD-3-Clause；
- 必要传递依赖只允许现有 `MarkupSafe` 解析结果。

TASK-009A 修改 `pyproject.toml`/`uv.lock` 并完成离线导入/许可证/包内容验证，不
实现 sink。正式 TASK-009 不再触碰依赖/锁文件。

两个 yt2md 候选继续仅 `REFERENCE`；不复制代码、不读取 Obsidian 配置、不直接写
Vault。标准库/PyYAML/Jinja2 负责通用能力，本项目保留路径、状态、恢复和用户区语义。

### N-15：离线矩阵与真实 Vault 门禁

测试只使用临时目录和临时 SQLite，至少覆盖：

- present/skipped analysis、低价值零写、Frontmatter 顺序/类型、StrictUndefined；
- Unicode/保留名/截断/标题变化/casefold 冲突；
- 用户 bytes 保留、marker/legacy/UTF-8 失败关闭、无变化 inode/hash；
- 路径穿越、中间/最终 symlink、目录替换、权限/短写/fsync/replace 故障；
- `ANALYSIS_READY -> NOTE_WRITTEN`、事务回滚、replace 后补账和失败 Job 重排；
- 固定模板进入 sdist/wheel。

接受本 ADR 不授权真实 Vault、真实用户笔记、删除/移动/重命名最终文件或任何真实
Vault 冒烟。

## 官方证据

- Jinja2 sandbox：
  <https://jinja.palletsprojects.com/en/stable/sandbox/>
- Jinja2 `StrictUndefined`：
  <https://jinja.palletsprojects.com/en/stable/api/#jinja2.StrictUndefined>
- Jinja2 PyPI：<https://pypi.org/project/Jinja2/>

## 不采用的方案

- 在 TASK-009A 增加成功笔记 refresh Repository 方法：当前 V1 不需要，且会扩大
  `state.py` 共享面。
- 依赖 Jinja2 的偶然传递安装：不可复现，正式任务并行时会争用锁文件。
- 接受用户模板或开放 loader：sandbox 不是运行不可信模板的完整安全边界。
- 手工字符串拼接 Markdown：条件章节、YAML 和转义规则易漂移。
- 自动修复/接管 legacy 或 marker 损坏笔记：可能覆盖用户内容。

## 后果

- ADR-008 已接受；TASK-008A 先完成，TASK-009A 再冻结最终 KnowledgeSink/NoteRef
  和依赖。
- TASK-008A/TASK-009A 均 `DONE` 后，正式 TASK-008/TASK-009 可安全并行。
- 真实 Vault 与成功笔记主动刷新继续独立审批，TASK-009 默认只使用临时 Vault。
