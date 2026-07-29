# TASK-014B11：安全字幕目录契约状态诊断

- Status: `IN_PROGRESS`
- Assignee: `Codex Implementer`
- Reviewer: `待全新独立 Reviewer（本控制面不启动）`
- 依赖：TASK-014B4/B5/B6/B7/B8/B10 `DONE`、ADR-021 `Accepted`
- 实施基线：`main@80aff83fc033a8bd2950108cad2e34feea5d396f`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics`
- Branch：`codex/task-014b11-safe-directory-contract-diagnostics`
- Required source HEAD：`80aff83fc033a8bd2950108cad2e34feea5d396f`
- Reuse decision：`DIRECT` — 既有锁定 subtitle Adapter、B4 directory-only、B5 安全摘要、
  ADR-017--ADR-020 固定诊断、既有 JSONL `safe_message` 与离线 integration 基础设施；不新增
  第三方代码或依赖。

## 背景与目标

B10-classified 真实 evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` 是
`f00aa9cffa25dcb9b7165edf21a4d476263c1dc5` 的 evidence-only 唯一子提交，只修改正式
授权的三份 evidence 文档，且保持未合并、只读。它记录固定目标在 `1/1/0` 后以
`INVALID_RESPONSE` 停止；B7 origin 为 mapping，但现有安全诊断不能确定失败所在的项目契约层。

实现 ADR-021 的固定、无值六字段状态矩阵，帮助后续独立兼容任务区分顶层视频标识、人工/
自动字幕目录、字幕桶、轨道条目和必需成员边界。B11 不修复真实兼容性、不扩大解析接受面，
也不构成真实 smoke、正文读取或发行批准。

## 冻结契约

- 矩阵字段顺序严格为：`video_identity_shape`、`manual_directory_shape`、
  `automatic_directory_shape`、`caption_bucket_shape`、`track_entry_shape`、
  `required_members_shape`。
- 每个值必须来自 ADR-021 对应封闭枚举；前置层未安全到达只能为 `not_evaluated`，已到达但
  无法安全分类只能为 `unknown`。六字段完整输出，不得增加动态字段或自由文本。
- 只有 directory-only、`INVALID_RESPONSE`、metadata=`1`/enumerate=`1`/read=`0`、
  `directory_origin_mapping` 且未读取正文时，才可经既有 B5 stdout/JSONL `safe_message`
  出口附加矩阵；任一条件缺失必须省略整个矩阵。
- 字段名仅是项目内契约概念。B11 新增矩阵禁止视频 ID 值、任意外部响应 key、URL、标题、语言代码、
  轨道名、字段值、数量、顺序、类型名、异常原文、原始响应、路径、Cookie、token、payload、用户数据或
  凭据；既有 B5 安全目标标识与其他既有安全摘要语义保持不变，不属于 B11 矩阵。
- 不改变 B6/B7/B8/B10 的词表、触发条件或含义；不新增 JSONL schema 字段、`logging.py`、Provider
  metadata、CLI 参数、配置或持久化状态。
- 不扩大 Adapter 字幕解析接受面，不改变默认 smoke、退出码、metadata/enumerate/read 计数、
  默认一次正文读取、directory-only 零正文、无重试、临时根、ID 上限、零业务记录、认证或
  fail-closed 边界。
- 测试只能使用无值内部状态，或仅含 ADR-021 项目契约概念的合成替身；不得新增、恢复或读取
  真实/结构化目录 fixture。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

实际产品 Diff 必须是上述允许范围的最小子集；不得为凑范围修改无需变化的文件。不得修改
fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`、日志 schema、
任务状态、ADR/prompt 或任何 evidence 文档。

## 离线验收

- 先由测试覆盖六字段的全部固定状态、`unknown` 与 `not_evaluated`，再做满足契约的最小实现；
  不得只测试私有格式化出口而绕过生产 Adapter 校验到 safe smoke 的传递边界。
- 独立证明矩阵只在完整严格门禁出现；默认 smoke 仍读取一次正文，directory-only 保持 `1/1/0`，
  退出码、无重试和零业务记录不变。
- 回归 ADR-017--ADR-020 的 B6/B7/B8/B10 固定诊断、成功/其他错误码省略规则、CLI 边界、
  Adapter fail-closed 与解析接受面。
- stdout、stderr、JSONL `safe_message`、测试新增行和 handoff 必须通过全输出面泄漏扫描；不得包含
  禁止材料或新增 fixture。
- Implementer 只可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁变化、下载/网络迹象或失败立即停止。仅在已有离线 `.venv` 可用时按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## Git、交付与红线

- 首个且唯一产品提交的唯一父提交必须为
  `80aff83fc033a8bd2950108cad2e34feea5d396f`；控制面提交不进入 source 历史。
- 开始与提交前后核验 source 身份、父链、精确 Diff、允许范围、SHA-256、LF/EOF、
  `git diff --check` 和洁净度。只在 `handoffs/TASK-014.md` 追加实现 evidence。
- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、
  用户数据、模型、Ollama、OpenAI、付费/云端调用、push、合并、source 清理、测试/检查外产品命令
  和 `.codebase-memory` 工件。
- 不得修改任务状态、启动 Reviewer 或把 B11 写成真实成功。TASK-014 始终
  `IN_PROGRESS / No-Go`；完成后只报告 Implementer commit、检查、跳过项和剩余风险。
