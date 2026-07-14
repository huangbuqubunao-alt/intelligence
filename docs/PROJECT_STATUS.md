# YouTube Intelligence Agent 项目状态

- 更新时间：2026-07-15
- 当前阶段：Phase 0 — 审批与基础
- 主控状态：ACTIVE
- 规划基线 commit：`c0f1f553db52b1cb4eb354e5c689c2abc5556223`
- 实现任务基线：分配时取最新已验收的 `main` commit，并写入任务包
- 活动 worktree：`/Users/hua/Documents/yia-worktrees/task-002`（`grok/task-002-config-domain-contracts`）；`/Users/hua/Documents/yia-worktrees/task-001` 只保留待后续清理
- 活动任务：`TASK-002` 为 `IN_REVIEW`；Grok 已停止写入，Codex Reviewer 等待控制面授权提交后启动

## 已完成或已批准

- DEC-01 至 DEC-10 已由产品负责人全部批准。
- `docs/PRD.md`、`docs/SYSTEM_DESIGN.md` 和 `docs/IMPLEMENTATION_ROADMAP.md` 已批准。
- 多 Agent 协作模式 ADR-001 已接受并生效。
- C-01 至 C-08 已由产品负责人批准，配置与领域契约 ADR-002 已接受并同步到 System Design；当前系统设计版本为 V1.2。
- `TASK-000` 已整合到 `main` 并通过整合后检查，状态为 `DONE`。
- `TASK-001` 已由 Codex 实现、Grok 独立审查、主控验收，并以 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 整合到 `main`；整合后全部门禁通过，状态为 `DONE`。
- 产品负责人已批准 `TASK-002` 使用 `pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`，并允许必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 写入以及任务卡中的 uv 命令；实现与预审修复证据已提交，`TASK-002` 状态为 `IN_REVIEW`。
- `TASK-003`/`TASK-004` 只读预检已完成且未修改仓库；产品负责人已批准 ADR-003 S-01 至 S-08 与 ADR-004 D-01 至 D-08。
- `TASK-004` 已获任务级授权：`yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令；真实 YouTube 冒烟、Cookie、账号登录、remote components、ffmpeg 仍未授权。
- 产品负责人已授权“复用优先”交付策略，ADR-005 已接受；附件候选和其他组件的 `DIRECT/ADAPT/REFERENCE/REJECT` 结论记录于 `docs/REUSE_REGISTER.md`。

## 当前阻塞

- `TASK-002` 已完成原实现 `4355a59f6f95e409bcf15b3b8004bb112d0033b3`、追加修复代码 commit `8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a` 和交接证据 head `8f50df2f7e93d778f32947ca471740b6713c9aff`；主控只读核对分支、父链、8 文件总范围、干净状态和密钥哨兵探针后将任务转为 `IN_REVIEW`。
- `TASK-003` 的 Schema/迁移审批已满足；仅等待 `TASK-002` 完成、审查、整合并关闭为 `DONE`。
- `TASK-004` 的发现契约和依赖审批已满足；仅等待 `TASK-002` 完成、审查、整合并关闭为 `DONE`。

## 下一步

1. Status Integrator 提交 TASK-002 修复记录、`IN_REVIEW` 状态和 Codex Reviewer 包；不得改动已准备内容或产品分支。
2. 控制面提交完成后，在独立 Codex Reviewer 会话执行 `agent-prompts/TASK-002-REVIEWER-CODEX.md`；Reviewer 只可补充交接报告。
3. Reviewer 返回 `APPROVE` 后由主控逐项验收；`REJECT` 则退回原 Grok Implementer。
4. `TASK-002` 验收、整合并关闭为 `DONE` 后，从同一最新 main 基线并行创建 TASK-003/TASK-004 worktree；开工包必须包含 `Reuse decision`。

## 当前并行调度

| 分组 | 工作 | 写入权限 |
|---|---|---|
| 立即启动 | Status Integrator 同步 TASK-002 修复记录与 Reviewer 授权 | 只提交指定 6 个 Markdown，不触碰产品分支 |
| 可并行启动 | 无需新增 Scout；Grok Implementer 保持停止写入 | Reviewer 必须等状态同步 commit 后启动 |
| 等待依赖 | `TASK-003`、`TASK-004` 写入实现及后续任务 | 只等 `TASK-002` `DONE` |

## 授权边界

- `TASK-001` 已授权：本机 Python 3.12、uv、`uv_build>=0.11.28,<0.12`、`pytest>=9.1.1,<10`、`ruff>=0.15.21,<0.16`、`mypy>=2.3,<3`、必要传递依赖、网络下载和锁文件/工具链写入。
- `TASK-002` 已授权：`pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`、uv 解析出的必要传递依赖、网络下载、修改 `pyproject.toml`/`uv.lock`，以及执行 `uv add`、`uv lock --check`、`uv sync --locked` 和任务卡验证命令；不包含可选 extras 或其他运行时依赖。
- 已批准 OpenAI 作为 V1 首个云 Adapter；尚未授权写密钥或真实付费调用。
- 已批准 MLX Whisper；尚未授权下载模型。
- `TASK-003` 已批准 ADR-003 最终 SQLite Schema、migration、租约、逐次尝试审计和任务卡验证；授权在正式开工包后生效。
- `TASK-004` 已批准 ADR-004 与 `yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令；不含真实网络冒烟、Cookie、账号、remote components 或 ffmpeg。
- ADR-005 允许主控决定普通复用方式，但新增依赖、系统工具、远程服务、密钥、付费、许可证义务和真实数据操作仍需原有具体审批。
- 真实 Obsidian Vault 和 launchd 操作均未授权。

## 当前风险

- TASK-001 的 `.gitignore` 使用未锚定 `data/`、`logs/`，会忽略任意同名嵌套目录；不违反当前 AC-3，已登记为 `TASK-014` 发布门禁检查项。
- TASK-001 的 build backend 由隔离构建环境按批准范围解析，不作为运行依赖写入 `uv.lock`；实现者、主控和 Reviewer 均实测为 `uv-build==0.11.28`。
- TASK-002 同时冻结配置与跨模块领域接口；Implementer 不得为了减少文件量退回自由形状 `dict`，Reviewer 需重点检查边界校验、错误脱敏和状态职责分离。
- TASK-002 修复提交已关闭原预审发现的密钥错误回显、公共自由 `dict`、可变公共状态表和额外 `ErrorCode`；Reviewer 必须独立重跑哨兵、公开 API、运行时不可变性及完整 AC-1 至 AC-8，而不能只信实现者报告。
- TASK-002 的 Provider request correlation/调用元数据仍需 Reviewer 对照 System Design §5.1/§5.2 判断；若必须新增 Wrapper 或公共字段才能满足，不得由 Reviewer 修改代码，应以 `REJECT`/`DECISION NEEDED` 返回主控。
- TASK-003 将使用已批准的 `scope_key + job_attempts`；Reviewer 需重点验证全局 Job 去重、租约 CAS 和逐次审计，而非只检查建表成功。
- TASK-004 将候选/游标提交与元数据成功解耦，并由 TASK-005 重查字幕轨道；Reviewer 需防止实现者为了复用外部工具而改变该边界。
- `video-to-subtitle-summary-skill`、`yt2md` 只能按复用登记选择性参考；其中存在 faster-whisper/ffmpeg/付费 API/直接 Vault 写入或 TLS 风险，不能整套引入。
- `youtube-skills` 依赖 TranscriptAPI 账号、密钥和 credits，与 V1 本地优先边界冲突，已标记为 V1 `REJECT`。
- MLX Whisper 的安装、模型下载和资源兼容性属于 `TASK-006`，不扩入 `TASK-001`。
- 初始 commit 使用本机自动推导作者身份 `华 <hua@huadeMacBook-Pro.local>`；不影响当前基线，但正式协作前可由用户决定是否配置显式 Git 身份。

## 主控接收执行结果的最小格式

```text
Task:
Role:
Branch/worktree:
Base commit:
Head commit:
Checks: <command + result summary>
Reviewer verdict:
Remaining risks:
Decision needed: None | details
```

不要把完整构建日志或长篇思考过程粘贴到主控对话；把证据保存到交接文件，只回传摘要和可定位路径。
