# TASK-008A 第一轮审查拒绝、A-16/A-17 与 Correction 1 同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 ADR-008 A-16/A-17、
第一轮审查结论、`TASK-008A=IN_PROGRESS` 控制面和 Correction 1 Implementer 包；
不得实现、审查或修改产品 source，不得下载 tokenizer，不得运行 `uv`、pytest、
mypy、Ruff、build、import、数据库、网络或真实资源命令，不得启动 Worker、merge、
push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@3eac5f9897bdfb59e764afde411e632822dcfb66`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Reviewed implementation：`382251298af7fcbfadba66c1902af6de0a425179`
- First Reviewer evidence：`0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`
- Original task base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Required identity：`Mozhu <maintainer@example.invalid>`；
  `user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确且暂存区为空；工作区必须恰有下列
11 个准备 Markdown 文件且没有其他修改/未跟踪路径。source 必须位于 Reviewer
evidence、分支正确且干净。任一条件不符立即 `BLOCKED`；不得 stash、reset、
checkout、merge、rebase、cherry-pick、pull、清理、下载文件或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-008A-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-008A-CORRECTION-1-CODEX.md`
3. `docs/PRODUCT_DECISIONS.md`
4. `docs/PROJECT_STATUS.md`
5. `docs/SYSTEM_DESIGN.md`
6. `docs/REUSE_REGISTER.md`
7. `docs/decisions/ADR-008-cloud-analysis-contract.md`
8. `docs/decisions/README.md`
9. `tasks/README.md`
10. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`
11. `tasks/TASK-014-release-readiness.md`

## 必须核验

1. Reviewer evidence 的唯一父提交为 reviewed implementation，evidence Diff 只修改
   `handoffs/TASK-008A.md`，source worktree 干净。
2. original base...reviewed implementation 的产品 Diff 精确为原任务卡 7 个批准
   路径；review evidence 不增加产品路径。不得把 main 控制面文件误算入 source
   产品范围。
3. Reviewer Verdict=`REJECT`，P0=0、P1=6、P2=0、P3=0：
   - 三处审计哈希未限制为 64 位小写 SHA-256；
   - 多个出站和 grounding 语义字段接受纯空白；
   - `ConfigError` traceback 的 `load_settings.raw` frame local 保留 secret
     sentinel；
   - tiktoken 空 cache 会尝试联网获取 `o200k_base`；
   - 主进程 `import openai` 会读取 `AZURE_OPENAI_AD_TOKEN`；
   - `AnalysisCompleted` 未强制 result/call 的 provider/model 一致。
   Reviewer 复跑的 contracts `66`、全量 `318`、mypy、Ruff、CLI、lock、offline
   sync/build、migration package inclusion 和 Diff PASS 不抵消这些 P1。
4. ADR-008 A-16/A-17 的批准记录、System Design V1.6、复用登记和 TASK-014 发布门禁
   一致：
   - 资源路径固定为
     `src/youtube_intel/resources/o200k_base.tiktoken`；
   - 来源只允许 OpenAI 官方 Blob；
   - SHA-256 固定为
     `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；
   - 运行时本地只读、缺失/哈希不符失败关闭、无网络回退；
   - OpenAI SDK 禁止主进程导入，TASK-008 后续使用清空/白名单化环境的独立子进程，
     导入完成后密钥只经匿名管道传入。
5. main 控制面把 TASK-008A 退回原 Codex Implementer 的 `IN_PROGRESS`；第一轮
   Reviewer 已结束，下一 Reviewer 尚未启动，不得预写 `APPROVE`、`ACCEPTED`、
   merge 或 `DONE`。
6. Correction 1 的 source 最大范围精确为原 7 个路径加上述 tokenizer 资源文件。
   其中 `uv.lock` 不得改变；`pyproject.toml` 只可在构建系统确实需要时加入该固定
   资源的 package-data 配置，不得新增、删除或升级依赖。
7. A-16 只授权 Implementer 对精确官方 Blob URL 执行一次无认证 GET；本 Status
   Integrator 不得下载。A-17 只冻结/离线验证隔离策略，不授权 Provider、SDK 调用、
   真实环境变量/密钥、API、付费、云 token-count 或其他网络。
8. TASK-009A、TASK-008、TASK-009 继续 `BLOCKED/UNASSIGNED`；真实 Vault/用户笔记、
   最终文件删除/移动/重命名和其他真实资源权限均不改变。

## 执行与提交

记录 11 个准备文件 SHA-256，完整检查前后必须一致。检查：

- main/source branch、HEAD、clean/index 状态；
- `git diff --check`；
- 两个新提示词的 LF/EOF 和逐文件 whitespace；
- main 完整 Diff 与 source evidence/original-base Diff；
- `git diff --cached --check` 和精确 cached scope；
- 不得出现真实 key、token、用户数据或除固定 SHA-256 外的敏感值。

只暂存上述 11 个文件，创建单一非 merge commit：

```text
docs: authorize TASK-008A correction 1
```

提交后确认唯一父为 Required main base、提交范围精确、main/source 均干净，且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-008A-CORRECTION-1-CODEX.md
```

解析为新 commit。不得运行产品命令、写 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-008A first review reject / A-16/A-17 / Correction 1 sync
Role: Status Integrator
Base: main@3eac5f9897bdfb59e764afde411e632822dcfb66
Head commit:
Git identity:
Committed files:
Checks:
ADR-008 A-16/A-17 status:
Review evidence/findings:
Correction source/scope/status:
TASK-009A/TASK-008/TASK-009 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
