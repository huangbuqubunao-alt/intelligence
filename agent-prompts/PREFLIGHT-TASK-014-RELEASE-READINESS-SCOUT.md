# TASK-014 — Release Readiness Read-only Scout

你是全新的 Codex Read-only Scout。目标是为产品负责人盘点 V1 发布前的证据、许可证/NOTICE 义务、未验证真实资源和待决产品选择，形成一份 **Go/No-Go 输入报告**。你不得修改仓库、启动 TASK-014、创建 worktree/branch、运行测试或接触任何真实资源。

## 固定授权与状态

- 授权基线：`main@5c5f60abef53d257dd6205456463b03600f0c47c`。
- 本 prompt 的控制面提交是唯一授权来源；开始时只读确认 main、index 和工作树干净，并在报告中记录实际观察到的 main SHA。
- `TASK-013` 已 `DONE`；`TASK-014` 必须保持 `BLOCKED/UNASSIGNED`。本包不构成 TASK-014 的实现、发布、worktree、分支、Reviewer、依赖或真实资源授权。
- 只读取 main 中的已跟踪文件和 Git 元数据。不得读取忽略/未跟踪文件、用户配置、`.env`、凭据、Keychain、`data/`、`logs/`、任何 Vault 路径或其他 worktree。

## 必读材料

完整阅读：`AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/ACCEPTANCE_REPORT.md` 与本 prompt。

随后只读检查已跟踪的发布相关元数据：`pyproject.toml`、`uv.lock`、包资源清单/构建配置、`src/youtube_intel/resources/o200k_base.tiktoken` 的受控来源与打包引用，以及相应 handoff/审查证据。仅为定位已跟踪文本可使用 `git`、`rg`、`sed` 和 `git ls-files`；不运行会建立索引或生成本地工件的工具。

## 只读预检范围

1. **依赖、许可证与 NOTICE 清单。** 盘点直接与传递依赖、锁定版本、许可证证据、归属/NOTICE 义务和缺口。必须单列：
   - `yt-dlp[default,deno]` 所带 `mutagen`（GPL-2.0-or-later）及其对源码、二进制和捆绑依赖分发形态的影响；
   - `Jinja2`（BSD-3-Clause）与 `MarkupSafe`；
   - OpenAI SDK（Apache-2.0）与其传递依赖；
   - `tiktoken`（MIT）及固定 `o200k_base.tiktoken` 资源。
   不得猜测文件级许可或宣称分发兼容；证据不足必须标为 No-Go/`DECISION NEEDED`。
2. **包内容与固定 BPE 资源。** 只读核对 sdist/wheel 预期包含的 migration、templates、prompts 与 `o200k_base.tiktoken`。对于 BPE 资源，明确记录固定 SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`、官方 Blob 来源、运行时禁止网络回退，以及尚未闭合的文件级 license/NOTICE/attribution 决策。
3. **已接受的可靠性边界。** 汇总已接受、但非严格 exactly-once 的 at-most-once best-effort 风险：外部 Provider 成功与 SQLite 提交之间、文件原子替换与 SQLite 提交之间、以及音频清理的最终 CAS 窗口。区分已由离线证据覆盖的恢复行为与仍无法由离线证据消除的崩溃窗口；不得把它们描述为已达到严格 exactly-once。
4. **未运行真实资源验证。** 从现有证据中列出仍未授权/未执行的真实 YouTube/字幕、媒体下载、ffmpeg、Whisper 模型加载、Ollama/模型、OpenAI API/真实密钥/付费调用、真实 Vault/用户笔记和 launchd 操作。离线验收只能作为离线服务边界证据，不能替代这些验证。
5. **发布前产品决策。** 给 PO/TL/QA 列出最小且可签署的决策：发布形态（仅源码 vs 二进制/捆绑依赖/模型或资源）、GPL/NOTICE 处置、固定 BPE 文件级归属、哪些可选 Provider/模型能力随 V1 发布、是否以及如何单独授权真实资源 smoke、已知 at-most-once 风险的接受/披露，以及最终 Go/No-Go 签署责任。
6. **复用结论。** 仅复核已有登记，使用 `DIRECT`、`ADAPT`、`REFERENCE`、`REJECT/DEFER`；不得新增、安装、升级或推荐未经审批的依赖。

## 绝对禁止

- 不运行 `uv`、Python/import、pytest、mypy、Ruff、build、安装、打包、hash 生成、数据库或任何产品 CLI 命令。
- 不访问网络，不执行真实 API/模型/token-count、YouTube/字幕/媒体、ffmpeg、Ollama、OpenAI、launchd 或任何外部服务。
- 不读取凭据、环境变量值、用户配置、真实/临时 Vault、SQLite、日志、缓存或媒体。
- 不修改、暂存、提交、推送、合并、rebase、reset、checkout、清理或删除任何文件；不创建任务、ADR、报告或其他仓库工件。
- 不把许可证盘点、既有离线测试或文档描述误表述为发布批准、真实资源验证或正式 Go。

## 回传格式

```text
Preflight: TASK-014 release readiness
Authorization base: 5c5f60abef53d257dd6205456463b03600f0c47c
Observed main / Git state: <SHA> / clean | blocked
Task state: BLOCKED / UNASSIGNED (unchanged)
Dependency, license, NOTICE inventory: <component/version/license/evidence/gap>
Package contents and o200k_base: <included evidence, SHA, source, NOTICE decision gap>
Accepted at-most-once risks: <risk, current mitigation, residual release disclosure>
Real-resource verification: <not run / separate authorization required>
Release decisions for PO/TL/QA: <decision owner, required written outcome>
Reuse: <DIRECT/ADAPT/REFERENCE/REJECT/DEFER>
Recommended release gate: Go | No-Go | Decision Needed, with reasons
Commands run: <read-only Git/document/text inspection only>
Decision needed: <explicit list or None>
```
