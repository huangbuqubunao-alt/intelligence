# TASK-014：发布准备

- Status: `IN_PROGRESS`
- Assignee: `PO + TL + QA (release gate)`
- Owner role: PO + TL + QA
- Size: S
- Risk: Medium
- Depends on: TASK-013

## 目标

在不新增功能的前提下完成 V1 文档、安装运行、备份恢复、安全检查和发布门禁，形成明确的 Go/No-Go 决策。

## Phase A：发行资料与风险披露（资料审查已通过；整体仍 No-Go）

- 控制面基线：`main@54b5be8c28554b70b1e3f294d6ed6f9f6fee2c21`。
- 正式实施包：`agent-prompts/TASK-014-RELEASE-READINESS-PHASE-A-IMPLEMENTER-CODEX.md`。
- 唯一审查 source：`/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-a`，分支
  `codex/task-014-release-readiness-phase-a`，提交
  `8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59`；其唯一父提交为本控制面基线。
- 正式 Reviewer 授权包：`agent-prompts/TASK-014-RELEASE-READINESS-PHASE-A-REVIEWER-CODEX.md`；Reviewer
  只可在上述 source 的 `handoffs/TASK-014.md` 追加审查证据，不能修改任何其他 source 路径或主线控制面。
- Reviewer evidence：`88f1b36fdef75146315e91f93b71c36463132ffb`，其唯一父提交为
  `8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59`，仅追加 `handoffs/TASK-014.md`；独立资料审查 Verdict 为
  `APPROVE`，无 P0–P3。
- 此 APPROVE 只确认 Phase A 七路径发行资料与风险披露的 Git/文档一致性；TASK-014 整体保持
  `IN_PROGRESS` / `No-Go`，不构成发布批准、法律结论、真实 smoke 授权、风险接受或最终 Go。
- Phase A accepted source 已由 Product Integrator 以 `--no-ff` merge
  `main@3165009df00c54f62c9b92a8f154bfd7ed664bea` 整合；双父顺序为 `225895a...`、`88f1b36...`，
  first-parent 严格为七条已审查路径，资料与 `/data/`、`/logs/` 根锚定均已核验。该资料整合不改变
  TASK-014 `IN_PROGRESS` / `No-Go`，也不构成发布批准。
- 本阶段只建立发行资料和风险披露，不构成正式发布、真实 smoke 或最终 Go/No-Go。
- 因原预计文件不能容纳发行级 SBOM、第三方 NOTICE、风险披露和 smoke 授权矩阵，控制面将本阶段允许范围精确扩展为该实施包所列路径；扩展理由是关闭 Scout 已发现的资料和门禁缺口，不改变产品功能、依赖或运行边界。

## Phase B-1：公开 YouTube 字幕 smoke 最终执行（刷新授权，尚未启动）

- 最终刷新控制面基线：`main@3165009df00c54f62c9b92a8f154bfd7ed664bea`；任务整体继续为
  `IN_PROGRESS` / `No-Go`。
- 正式 Smoke Executor 授权包：
  `agent-prompts/TASK-014-RELEASE-READINESS-PHASE-B1-PUBLIC-YOUTUBE-SMOKE-CODEX.md`。
- 新的唯一执行 worktree：`/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1-final`；分支：
  `codex/task-014-release-readiness-phase-b1-final`。本包只创建授权和 worktree，不启动 Executor。
- 旧 worktree `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1` 建立在 B0 合并前主线；不得访问、修改、
  合并、cherry-pick 或复用其 blocker evidence `be230490...`。
- 旧 worktree `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1-execution` 建立在 Phase A 合并前主线；
  不得访问、修改、合并、清理或复用。
- 仅授权一次、低频地对 2–3 个稳定官方频道的公开视频验证元数据、字幕发现和选中字幕读取；必须使用全新临时
  SQLite、DATA 与测试 Vault，并只记录目标选择理由、smoke 证据和发布检查表更新。
- 严禁登录、Cookie、API key、真实 Vault/用户笔记/用户数据、媒体下载、ffmpeg、模型、Ollama、OpenAI、
  付费调用、高频重试、产品代码/依赖/锁/Schema/任务状态改动。成功不构成发布批准；mutagen GPL、BPE
  文件归属/NOTICE 和 at-most-once 风险继续为 No-Go 门禁。
- 仅允许以已整合的 `smoke-public-subtitles` 入口执行；精确写入范围以授权包为准，只允许独立 smoke 证据、
  目标选择理由、发布检查表 B-1 记录与 handoff，不能改写其他发行资料。

## Phase B-0：受限公开字幕 smoke 组合入口（已整合并关闭为 `DONE`）

- B-1 blocker evidence `be230490a5b5779c7f1eb1e46c0fd717055fc28c` 证明默认 CLI 的非 doctor 命令在没有
  外部组合根时 fail-closed，且没有可限制为“元数据 + 字幕目录 + 一条选中正文”并使用临时根的入口；该 evidence
  留在 B-1 source，绝不合并到 main。
- ADR-013 已接受，正式任务卡为 `tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`；Implementer 包为
  `agent-prompts/TASK-014B0-RESTRICTED-PUBLIC-SUBTITLE-SMOKE-IMPLEMENTER-CODEX.md`。
- 第一轮 Reviewer evidence `f8e336a8c3b09a8c0c0e5857148495f2cb2281aa` 是唯一 source
  `/Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke` /
  `codex/task-014-phase-b0-restricted-public-subtitle-smoke` 的 HEAD，唯一父提交为实现 `4e506847854f20a43011b0a15db3a1c8e320656d`，
  且仅追加 handoff。Verdict=`REJECT`：P1 为 smoke 仍接受全局配置路径参数；P2 为 handoff 基线、提交 SHA 和状态过期。
- Correction 1 Reviewer evidence `48df2e2a0afb54d5f6252f197dddf32ff685f0db` 是 `cafcde…` 的唯一后继，且仅追加
  source handoff，Verdict=`REJECT`：P1 为 argv 字符串包含判断会误伤普通命令的合法值。Correction 2 Reviewer evidence
  `010fb7faf6280cd83350315ba66f70b5e785b41f` 是 `b7cb846…` 的唯一后继且仅追加 source handoff，Verdict=`APPROVE`，
  P0–P3 均无。Product Integrator 已以 `--no-ff` merge `main@e50b211c9214ef3e170c28d4f7bb6229c9f1c55b` 整合：双父顺序
  精确为 `175739c…`、`010fb7…`，accepted source 是 merge 祖先，first-parent Diff 严格为完整 B0 六路径，且无依赖、
  锁文件、Schema/migration 或 `state.py` 改动。既有整合后证据为离线 Fake `13`、全量 `451`、mypy、Ruff、CLI help 与
  离线 build 均通过；未 push、未真实网络/B-1 或清理 source。B0 因此为 `DONE`，但 TASK-014 整体继续
  `IN_PROGRESS` / `No-Go`，不构成发布批准。

## 已授权的只读 Scout 预检（不等于任务开工）

- 授权包：`agent-prompts/PREFLIGHT-TASK-014-RELEASE-READINESS-SCOUT.md`；授权基线为
  `main@5c5f60abef53d257dd6205456463b03600f0c47c`。
- 该包仅允许独立 Scout 对 main 中已跟踪的文档、包/锁定元数据、打包引用和既有 handoff 证据做只读盘点；
  Scout 尚未启动。
- 必须报告：直接/传递依赖的许可证和 NOTICE 义务（尤其 `mutagen`、Jinja2、OpenAI SDK、tiktoken 与
  固定 `o200k_base.tiktoken` 资源）、包内容、已接受的 at-most-once best-effort 风险、未运行真实资源
  验证，以及 PO/TL/QA 发布前需要签署的产品决策。
- 禁止 uv、测试、构建、网络、真实 API/模型、凭据/Vault 读取、推送、合并和清理；不得创建 worktree/branch、
  修改任务状态或把盘点结论视为 Go/No-Go。

## 范围

- 核对 README、配置示例、初始化、手动运行、doctor、launchd、备份/恢复和故障处理说明。
- 核对 PRD、System Design、实际 CLI、Schema 版本和验收报告一致。
- 由 PO/TL/QA/隐私 Reviewer 逐项签署发布清单。

## 范围外

- 不修复新发现缺陷；缺陷必须退回对应任务或新建范围明确的任务卡。
- 不新增依赖、重构、格式化全仓库或实现 V2 功能。
- 不自动部署、加载 launchd 或写入真实 Vault。

## 验收标准

- [ ] 从干净环境按 README 可安装并完成离线 smoke；备份/恢复说明在临时数据上验证。
- [ ] `docs/ACCEPTANCE_REPORT.md` 无未解释的 P0/P1 失败，所有剩余风险有负责人和处置决定。
- [ ] 复核 `.gitignore` 的 `data/`、`logs/` 边界：不得静默忽略实际使用的测试夹具、源码资源或文档目录；若届时仍存在误忽略风险，必须 No-Go 并退回范围明确的修复任务。
- [ ] 生成直接/传递依赖许可证清单并决定分发形态；特别复核 `yt-dlp[default]` 带入的 `mutagen` GPL-2.0-or-later 义务。未形成经 TL/发布负责人确认的兼容分发方案前不得发布二进制或捆绑依赖包。
- [ ] 若启用本地模型，复核 `mlx-whisper` 及其传递依赖许可证、MLX Community 转换模型
  card 缺失许可声明、Whisper 权重来源和缓存分发边界；若安装/调用 ffmpeg，确认其
  GPL 构建不被项目捆绑或重新分发。无明确处置不得把相关产物纳入发布物。
- [ ] 若启用 Ollama，复核程序版本、`qwen3:8b` 固定 digest、上游 Apache-2.0 证据和
  模型拉取/本机服务实际授权记录；不得把“本机 loopback”误记为无需供应链审查。
- [ ] 复核 TASK-008A/TASK-009A 的直接/传递依赖与分发边界：OpenAI SDK
  Apache-2.0、tiktoken MIT、Jinja2 BSD-3-Clause、MarkupSafe 及 OpenAI SDK 传递
  依赖；确认云端默认关闭、无真实密钥/响应进入发布物，固定 Jinja 模板不包含用户
  Vault 内容。
- [ ] 单独复核包内 `o200k_base.tiktoken` 的文件级来源、固定 SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`、分发许可和
  NOTICE/归属要求；未形成书面结论前，不得把该资源纳入二进制或捆绑分发物。
- [ ] 复核正式 TASK-008 未在主进程导入 OpenAI SDK；隔离子进程环境为新建白名单且
  不继承 OpenAI/Azure/代理/凭据变量，密钥只在 SDK 导入握手后经匿名管道传入，并在
  异常、argv、文件、日志和进程退出路径中保持不可见。
- [ ] 四类 Reviewer 完成清单并给出 Go；任一红线项不满足则明确 No-Go，不得标记 V1 完成。

## 验证

- [ ] `python -m pytest`
- [ ] `ruff check . && mypy src`
- [ ] `python -m youtube_intel doctor`（只使用临时/示例配置）
- [ ] `git diff --check && git status --short`
- [ ] 人工检查：无密钥、无真实 Vault 内容、无未审批依赖/Schema/调度改动。

## 预计触达文件

- `README.md`
- `docs/SBOM.md`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/SMOKE_AUTHORIZATION_MATRIX.md`
- `.gitignore`
- `handoffs/TASK-014.md`

## 交付证据

- Go/No-Go 记录和签署人。
- 干净环境 smoke、备份和恢复结果。
- 版本号、Schema 版本、已知限制和下一步任务链接。
- TASK-001 P2（未锚定 `data/`、`logs/`）的最终复核与处置记录。
- `yt-dlp` 全部直接/传递依赖的许可证证据、`mutagen` 分发处置与最终 Go/No-Go 结论。
- ADR-007 模型、ffmpeg、Ollama 与模型权重的来源/许可证/授权证据及最终处置。
- ADR-008/ADR-009 的 OpenAI/tiktoken/Jinja2/MarkupSafe 依赖清单、固定
  `o200k_base.tiktoken` 资源许可与哈希证据、SDK 隔离导入/匿名管道密钥门禁、云端
  隐私门禁和模板/Vault 分发边界。
- 发布 Scout 报告（如后续启动）：仅作为 PO/TL/QA 的许可证、分发形态、真实资源验证和残余
  at-most-once 风险决策输入；不替代实施、真实验证或正式 Go/No-Go 签署。
