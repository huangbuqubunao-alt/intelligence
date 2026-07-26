# TASK-014B0 — 独立 Codex Reviewer（受限公开字幕 smoke 入口）

你是 TASK-014B0 的独立 Codex Reviewer。本授权包只登记未来独立审查的边界；它本身不启动 Reviewer。开始前完整阅读
`AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、
`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、
`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、`docs/operations.md`、ADR-013、Implementer 包、source
`handoffs/TASK-014B0.md` 与本包。如任一文件与本包冲突，停止并报告。

## 固定审查对象

```text
Task: TASK-014B0 — Restricted public subtitle smoke entry
Role: Independent Reviewer
Agent: Codex Reviewer
Control-plane base: main@c62310ab79f01f5f311c9f54bb28365905f5a81a
Only source worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Source branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Source HEAD: 4e506847854f20a43011b0a15db3a1c8e320656d
Required sole parent: c62310ab79f01f5f311c9f54bb28365905f5a81a
Required change range: c62310ab79f01f5f311c9f54bb28365905f5a81a...4e506847854f20a43011b0a15db3a1c8e320656d
Reuse decision: DIRECT — review the locked yt-dlp adapters, SQLite migration, JsonlLogger, Python standard library and Git/text evidence; do not add or copy third-party code
```

## 唯一写入权限

只能向 source worktree 的既有 `handoffs/TASK-014B0.md` **追加** Reviewer 审查结论和证据。不得修改、替换或格式化
既有内容；不得修改 source 的任何其他路径，也不得修改 main 控制面。审查证据提交只能包含该 handoff 追加；不得
创建 worktree/branch、项目自身 `LICENSE`、任何许可证文本、依赖或 Schema 变更。

开始时和追加 handoff 前后，都必须确认 source 仍指向固定 HEAD、唯一父提交正确、范围恰为以下六路径且工作树没有
无关变更：

1. `docs/operations.md`
2. `handoffs/TASK-014B0.md`
3. `src/youtube_intel/cli.py`
4. `src/youtube_intel/public_subtitle_smoke.py`
5. `tests/integration/test_operations.py`
6. `tests/integration/test_public_subtitle_smoke.py`

只允许 Git 与文档/源码静态核验，例如 `git rev-parse`、`git log -1`、`git diff --name-status`、`git diff --check`、
`git status --short` 与针对上述文件、任务卡、ADR/锁文件元数据的 `git diff`/`rg`/`sed` 阅读。不得运行产品测试、构建、
安装、`uv`、Python/import、产品 CLI 或任何 smoke。

## 独立核验要求

独立审查完整 `base...HEAD` Diff、所有新增文件、任务 handoff 与 ADR-013。至少确认：

1. 现有 `check/process/retry/weekly/doctor` 参数、注入式 `Operations` 边界和默认 fail-closed 语义不变；新入口没有
   让默认命令获得真实组合能力。
2. 新入口只接受不存在的绝对临时根及 1–3 个互异、有效且由未来 B-1 授权预先列出的显式视频 ID；B0 不得自行
   选择、发现或扩展目标，也不得接受 channel、URL、playlist、YAML、环境或配置输入，且不会复用项目默认根。
3. 每个 ID 严格顺序执行至多一次 metadata、字幕目录与一条按既有候选排序选中的字幕正文读取；30 秒 timeout、无并发、
   无重试或替换目标。正文仅内存存在，不写 SQLite、DATA、JSONL、Vault、异常、测试夹具或 handoff。
4. 临时根只含已初始化 SQLite、DATA、空测试 Vault 和日志；不创建 Pipeline、Job、ProviderCall、Artifact 或任何业务
   记录。JSONL 审计只含脱敏的 run ID、video ID、阶段、结果、错误码、调用计数和耗时；不含正文、临时 URL、绝对路径、
   密钥或用户数据。
5. 所有登录、Cookie、API key、媒体/音频/视频/缩略图下载、ffmpeg、Whisper、Ollama、OpenAI、模型、付费服务、
   launchd、真实 Vault/用户数据与 B-1 网络 smoke 路径仍被拒绝；没有依赖、锁文件、Schema/migration、Provider Adapter、
   domain/config 或状态控制面改动。
6. 离线 Fake 覆盖确实覆盖输入上限、一次调用、失败不重试、临时根隔离、正文不落盘/不入日志、无业务记录、默认 CLI
   fail-closed 与既有 Adapter 安全选项；不得把 Implementer 自报检查或 Fake 结果误写成真实 B-1 smoke 证据。
7. handoff 的 commit、范围和验证陈述与 Git 事实一致；元数据不一致、未更新的占位符或任何范围/风险弱化必须按 P0–P3
   分类并决定 `REJECT` 是否必要。

发现缺陷、范围错误、证据不一致、泄露或被放宽的边界时，Verdict 必须为 `REJECT` 并给出 P 级、文件/行和最小修复
建议；不得自行修复 source。若全部满足，也只能给出 B0 离线实现审查 `APPROVE`，不构成真实 smoke 成功、发行批准、
法律结论、严格 exactly-once 证明、风险接受或 TASK-014 最终 Go。

## 禁止事项

- 不发布、合并、push、rebase、reset、清理或删除任何真实文件。
- 不联网，不访问 YouTube、OpenAI、Ollama、ffmpeg、Whisper、launchd 或其他服务。
- 不读取 `.env`、环境变量值、凭据、Keychain、真实 Vault、SQLite、日志、缓存、媒体或用户数据。
- 不运行测试、构建、安装、打包、`uv`、Python/import、产品 CLI、真实资源或任何 B-1 smoke。
- 不修改 source、main、依赖、锁文件、Schema/migration、Provider Adapter、任务状态、ADR、项目 LICENSE 或 B-1 evidence；
  唯一例外是本包已列出的 source handoff 追加。

## 审查交接

只在 `handoffs/TASK-014B0.md` 末尾追加：固定 base/source HEAD/parent、六路径和清洁度结果、依赖/Schema 无差异、
逐项边界与离线 Fake 静态核验、未运行命令/资源、所有 P0–P3 发现或明确“无 P0–P3”，以及 `APPROVE` 或 `REJECT`。
追加后只可用 Git/文本检查确认该 handoff 是唯一 source 工作树改动；不得启动其他角色、改变任务状态或宣称任务完成。
