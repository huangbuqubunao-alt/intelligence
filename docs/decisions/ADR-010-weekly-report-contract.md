# ADR-010：确定性周报契约

## 状态

Accepted

## 日期

2026-07-23

## 背景

TASK-011 依赖 TASK-009 与 TASK-010，二者已整合。现有 `reports` 唯一键可以保存每周结果，但 Repository 缺少候选查询，Knowledge Sink 的周报写入仍是 stub；周报任务卡的原五路径不足以安全实现可重复更新与临时 Vault 测试。

## 决策

### W-01：以完成时间归入本地 ISO 周

视频按 `completed_at` 转为配置时区后归入 ISO 年/周。窗口为本地周一 00:00（含）至下一周一 00:00（不含）；跨年路径固定为 `Weekly/YYYY-Www.md`。

### W-02：候选、排序和唯一键保持确定性

候选必须同时是 `COMPLETE`、高价值、具有受管视频 `NoteRef`，并落在周窗口内。按 `score DESC, video_id ASC` 排序，取配置 Top N。报告使用既有 `(timezone, iso_year, iso_week, report_type)` 唯一 upsert，不新增 Schema。

### W-03：只聚合已验证本地事实

趋势、关键词和持续关注方向只读取已验证的 `ANALYSIS_STRUCTURED`、`ScoreResult` 与 `NoteRef`。不得隐式调用云模型、Provider 或网络；关键词规范化、并列规则与持续方向算法必须完全确定性并由测试冻结。

### W-04：空周仍生成稳定报告

空周写入同一唯一报告，含零计数、空 Top N 和固定无内容说明；重复执行只更新同一受管报告，不产生重复记录或文件。

### W-05：模板使用包内固定 Jinja2 模板

周报模板固定为 `src/youtube_intel/templates/weekly.md`，只可由 `ImmutableSandboxedEnvironment` 与 `StrictUndefined` 加载。不得接受用户模板、任意 loader 或动态代码。

### W-06：周报不是 video_id=None Pipeline Job

V1 不扩展 Pipeline/Job 以承载 `video_id=None`。TASK-011 直接编排周报服务、Repository 查询和既有 reports upsert；不得改 `complete_stage`、Schema 或全局 Job 语义。

### W-07：仅临时 Vault 原子写测试

仅 pytest 临时目录的最小 Vault 可写。周报写入复用受锚定根目录、相对路径、无 symlink、同目录临时文件、fsync/replace 和 fail-closed 边界；禁止真实 Vault、用户笔记、外部删除或移动。

### W-08：TASK-011 正式范围

后续分配可修改 `reporting.py`、`state.py` 的只读候选查询、`providers/obsidian.py` 的周报 upsert、包内 weekly 模板、既定周报 unit/integration tests、fixtures 与 handoff。不得新增依赖、锁、Schema/migration、`complete_stage`、云调用或真实资源。

## 后果

- TASK-011 可在正式 worktree/角色/命令授权后变为 `READY`。
- Jinja2 继续直接复用；许可证证据保留 TASK-014 发布门禁。
- CLI 的 `weekly` 入口只能在 TASK-011 整合后由 TASK-012 接入。
