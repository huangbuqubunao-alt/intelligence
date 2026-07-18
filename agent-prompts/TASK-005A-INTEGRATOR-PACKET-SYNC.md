# TASK-005A 最终整合包同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-005A Product Integrator
授权包；不得运行产品命令、修改 source 或 handoff、启动 Integrator、merge、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@ce8e76c7ba51fd8f53bf63ebcfc6cf53fcc30b9d`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Original implementation base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Accepted source head：`e726656ffcc96b3c61d12f649c5574dc927add62`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确、暂存区为空；工作区必须恰有下列 2 个
准备 Markdown 文件且无其他修改/未跟踪路径。source 必须在 accepted head、分支正确且
干净。任一不符立即 `BLOCKED`；不得 stash、reset、checkout、merge、rebase、
cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-INTEGRATOR-PACKET-SYNC.md`
2. `agent-prompts/TASK-005A-INTEGRATOR.md`

## 必须核验

1. main base 记录 TASK-005A=`ACCEPTED`，review evidence=`e726656...`；不得改为
   `DONE` 或预写 merge SHA。
2. accepted source head 的唯一父为 Correction 1 `3a7df102...`；第二轮 reviewer evidence
   只修改 handoff；source clean。
3. original base...accepted source 的产品范围精确为 8 个路径：settings example、
   handoff、`config.py`、`domain.py`、`state.py`、指定 integration test 与两份 unit test；
   lockfiles 未变，`git diff --check` 通过。
4. Product Integrator 包固定 source/head、执行基线、非快进 merge、整合后全量离线门禁、
   migration package inclusion、first-parent 精确范围、双父与保留 source worktree/branch。
5. TASK-006/TASK-007 仍 `BLOCKED/UNASSIGNED`；任何模型、服务、网络、媒体、Cookie、
   登录、Vault/密钥与文件删除授权均不改变。

## 提交

记录 2 个准备文件 SHA-256，检查前后必须一致。运行 `git diff --check`、完整 Diff、
source Diff、`git diff --cached --check` 和 cached scope；只暂存两文件并创建：

```text
docs: authorize TASK-005A integration
```

提交后确认唯一父为 Required main base、main/source 都干净、范围精确，且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-005A-INTEGRATOR.md
```

解析为该新 execution base。不得运行产品命令、写 source、启动 Worker、merge、push 或
清理。

## 回传格式

```text
Task: TASK-005A integrator-packet sync
Role: Status Integrator
Base: main@ce8e76c7ba51fd8f53bf63ebcfc6cf53fcc30b9d
Head commit:
Git identity:
Committed files:
Checks:
Accepted source/status:
Integrator authorization:
TASK-006/TASK-007 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
