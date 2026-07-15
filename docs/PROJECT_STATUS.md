# YouTube Intelligence Agent 项目状态

- 更新时间：2026-07-15
- 当前阶段：Phase 0/1 — 状态基础与采集主链并行准备
- 主控状态：ACTIVE
- 规划基线 commit：`c0f1f553db52b1cb4eb354e5c689c2abc5556223`
- 实现任务基线：分配时取最新已验收的 `main` commit，并写入任务包
- 活动 worktree：`/Users/hua/Documents/yia-worktrees/task-003`（`codex/task-003-state-store`）与 `/Users/hua/Documents/yia-worktrees/task-004`（`grok/task-004-discovery-metadata`），共同 base 为 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`；TASK-001/TASK-002 worktree 只保留审计证据
- 活动任务：`TASK-003` 已以 merge commit `072511f...` 整合并为 `DONE`；`TASK-004` 为 `IN_REVIEW`，correction 4 `54c0ab2...` 等待全新独立 Grok Reviewer

## 已完成或已批准

- DEC-01 至 DEC-10 已由产品负责人全部批准。
- `docs/PRD.md`、`docs/SYSTEM_DESIGN.md` 和 `docs/IMPLEMENTATION_ROADMAP.md` 已批准。
- 多 Agent 协作模式 ADR-001 已接受并生效。
- C-01 至 C-08 已由产品负责人批准，配置与领域契约 ADR-002 已接受并同步到 System Design；当前系统设计版本为 V1.2。
- `TASK-000` 已整合到 `main` 并通过整合后检查，状态为 `DONE`。
- `TASK-001` 已由 Codex 实现、Grok 独立审查、主控验收，并以 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 整合到 `main`；整合后全部门禁通过，状态为 `DONE`。
- 产品负责人已批准 `TASK-002` 使用 `pydantic>=2.13.4,<2.14`、`PyYAML>=6.0.3,<7`；实现、修复、独立审查及整合后检查均通过，并以 merge commit `823d68a2dffc1745e04cbbe54c817bf0c117a6fa` 进入 `main`，状态为 `DONE`。
- `TASK-003`/`TASK-004` 只读预检已完成且未修改仓库；产品负责人已批准 ADR-003 S-01 至 S-08 与 ADR-004 D-01 至 D-08。
- `TASK-004` 已获任务级授权：`yt-dlp[default,deno]>=2026.7.4,<2026.8`、必要传递依赖、网络下载、`pyproject.toml`/`uv.lock` 和所列 uv 命令；真实 YouTube 冒烟、Cookie、账号登录、remote components、ffmpeg 仍未授权。
- 产品负责人已授权“复用优先”交付策略，ADR-005 已接受；附件候选和其他组件的 `DIRECT/ADAPT/REFERENCE/REJECT` 结论记录于 `docs/REUSE_REGISTER.md`。

## 当前阻塞

- `TASK-004` 已无实现或审批阻塞，当前仅等待 correction 4 的全新独立 Grok Reviewer；审查通过前不得合并或设为 `ACCEPTED`。
- `TASK-005` 及后续任务仍按任务图等待 TASK-004 完成。

## 下一步

1. 全新独立 Grok Reviewer 在 TASK-004 source worktree 复核 `dcc7d85...54c0ab2...`，重新运行全部任务门禁，重点独立验证非法 age_limit 的请求 ID 保留及 RSS 缺 channelId 的全批原子失败。
2. TASK-004 Reviewer 返回 `APPROVE` 后，主控逐项验收并决定 `ACCEPTED`；若 `REJECT`，只退回原 Grok Implementer 做最小修复。
3. TASK-004 整合后，才开始 TASK-005 的最新基线分配和字幕链路预检。
4. TASK-004 继续禁止真实 YouTube 冒烟、Cookie、账号、remote components、ffmpeg 及媒体/字幕下载。

## 当前并行调度

| 分组 | 工作 | 写入权限 |
|---|---|---|
| 立即启动 | TASK-004 全新独立 Grok Reviewer | 仅 TASK-004 handoff 审查证据 |
| 等待审查 | TASK-004 主控验收与 Integrator 包 | Reviewer 结论返回后才决定 |
| 等待 TASK-004 `DONE` | TASK-005 预检与分配 | 不提前实现字幕链路 |
| 等待依赖 | `TASK-005` 及后续写入任务 | 按任务图等待上游 `DONE` |

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
- TASK-002 已冻结配置与跨模块领域接口；后续任务不得为了减少文件量退回自由形状 `dict`，如需改变公共契约必须先回到主控决策。
- TASK-002 修复提交已关闭原预审发现的密钥错误回显、公共自由 `dict`、可变公共状态表和额外 `ErrorCode`；Reviewer 已独立重跑哨兵、公开 API、运行时不可变性及完整 AC-1 至 AC-8。
- TASK-002 的 Provider request correlation/调用元数据已由 Reviewer 对照 System Design §5.1/§5.2 复核，未发现必须新增 Wrapper 或公共字段的冲突。
- TASK-002 Reviewer 已判定 Provider request correlation/调用元数据与冻结字段一致；剩余 P3 为 `MappingProxyType` 对私有 backing dict 的 live view，公共写入仍被拒绝，不阻断 V1 整合。
- TASK-003 已通过独立 Grok 审查并以 merge commit `072511f20b587f973b29437d79080f6cb7863f1a` 整合到 main：两组 focused tests、全量 86、mypy、Ruff、`uv build` 及 migration SQL 包含性全部通过。无 P0/P1/P2；非阻断 P3 为路径脱敏可能裁去 URL 片段、周报 `scope_key` 的周号正则略宽但表级 `iso_week` 仍限制 `1..53`。TASK-003 仅提供 at-most-once best effort，不声称跨外部 Provider 与数据库提交的严格 exactly-once；这些风险随发布门禁保留。
- TASK-004 独立 Reviewer 证据 `f34cbb...` 为 `REJECT`：P1 包括 yt-dlp 畸形 payload 逸出 `ValueError`、请求/响应 video ID 不一致、RSS 不完整 entry 静默跳过且推进游标、HTTP 404/403/503 的终态/重试语义反转；P2 包括 RSS read 失败未关闭 response 与 `needs_auth` 误标 PUBLIC，P3 为公开注解测试遗漏 `Any`。范围、依赖、公开 Surface 和安全 options 均通过，但上述 P1 阻断合并。
- TASK-004 第三轮修复 `30932e1...` 已关闭 Reviewer 列出的 4 个 P1、2 个 P2 与 1 个 P3：静态核验确认 malformed mapping 在 Adapter 边界安全封装、返回 ID 与请求 ID 交叉校验、RSS 不完整 entry 使全批失败并不推进 cursor、HTTP 状态在宽泛文本前分类、response 在 finally 关闭、`needs_auth` 为 `RESTRICTED`、公开注解哨兵拒绝 `Any/object`。完整 17 文件范围与 correction 5 文件范围均通过；该结论不替代第二次独立审查。
- TASK-004 第二次独立 Codex 审查 `5d66c28...` 重新运行全部门禁仍发现两个 P1：`_coerce_age_limit()` 处理非法值时虽返回 `INVALID_RESPONSE`，但 `AppError.video_id` 为 `None` 而未保留请求身份；RSS entry 缺 channelId 时实现以请求 channel 回填，仍保存候选并推进 cursor。其他 correction 3 覆盖项均通过。TASK-004 回到 `IN_PROGRESS`，correction 4 必须只修复这两项及其离线回归。
- TASK-004 correction 4 `54c0ab2...` 仅改原允许的 5 文件：静态核验确认 age_limit 映射路径将请求 ID 传入安全错误，RSS entry channelId 不再回填且缺失/不匹配立即整批失败；unit/integration 回归覆盖候选/游标不变和较旧条目修复后可发现。该结论不替代全新独立 Grok Reviewer 的复跑与探针。
- TASK-004 将候选/游标提交与元数据成功解耦，并由 TASK-005 重查字幕轨道；Reviewer 需防止实现者为了复用外部工具而改变该边界。
- TASK-004 首个实现将 `SAFE_YDL_OPTS`、`build_ydl_opts` 和含 `Mapping`/`dict` 的 Adapter helper 显式置入 `__all__`，且 `YtDlpMetadataProvider` 公开了 `last_opts: list[dict[str, Any]]` 注入/属性。首个修复 `10f5ffa...` 虽隐藏了这些注解，却仍保留非私有 `map_info_dict_to_video_metadata(info: object)` 以及公开的 `ydl_factory`/`last_opts` 注入参数；以 `object` 包装自由结构不符合修复包。第二轮修复 `9db800f...` 已移除残余公开 mapper 与所有公开测试钩子，改为私有 `_map_*` / `_bind_test_hooks`；主控静态核验其构造面、模块符号、修复 commit 的 4 文件范围和完整 17 文件范围均通过。独立 Reviewer 仍须重跑门禁并独立判断。
- `video-to-subtitle-summary-skill`、`yt2md` 只能按复用登记选择性参考；其中存在 faster-whisper/ffmpeg/付费 API/直接 Vault 写入或 TLS 风险，不能整套引入。
- `youtube-skills` 依赖 TranscriptAPI 账号、密钥和 credits，与 V1 本地优先边界冲突，已标记为 V1 `REJECT`。
- MLX Whisper 的安装、模型下载和资源兼容性属于 `TASK-006`，不扩入 `TASK-001`。
- 早期 commit 曾使用本机自动推导作者身份 `华 <hua@huadeMacBook-Pro.local>`；仓库现已固定 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`，后续提交必须保持该已验证身份。

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
