# TASK-014B3 — Product Integrator

你是 TASK-014B3 的 Codex Product Integrator。你只可整合已接受的 review evidence；本包不授权修改 source、修复代码、重新设计、真实验证、推送或发布。

## 固定整合对象

```text
Task: TASK-014B3 — public subtitle directory diagnostics
Role: Product Integrator
Control-plane base: main@e3dec4bad02c59bff6e42f357aa3fdb666575efb
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics-implementation
Accepted source branch: codex/task-014b3-public-subtitle-diagnostics-implementation
Accepted review evidence: b0ddf9d7749840fbf507426f67ba38a28b7030f8
Required sole parent of evidence: 77f2690c28ab80eb9886e8ca8eadb0e47481cd51
```

- 开始前核验 main HEAD、main/source 工作树干净、source 分支/HEAD/唯一父提交精确匹配，以及 review evidence 的 `APPROVE`、P0–P3 均无。
- 发现任何提交关系、范围、洁净度或门禁冲突时立即停止并报告；不得改写 source、补修、rebase、cherry-pick、清理 source 或自行重新设计。

## 唯一整合动作

在干净的 main 上仅执行一次固定的 `--no-ff` 整合，目标为 `b0ddf9d7749840fbf507426f67ba38a28b7030f8`。冲突时停止，不手工解决或修改额外文件。

整合后的 first-parent Diff 必须精确限于任务卡的六条路径：

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `tests/fixtures/subtitles/**`
6. `handoffs/TASK-014B3.md`

不得新增或改动依赖/`uv.lock`、Schema/migration、domain 公共契约、默认 CLI、`logging.py`、README/发布结论、B-1 evidence、任务状态或任何其他路径。

## 整合后离线门禁

仅在已有离线环境可用时运行：

```text
uv run --offline python -m pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
uv run --offline mypy src
uv run --offline ruff check .
git diff --check HEAD^1..HEAD
```

还必须人工核验 first-parent 文件范围和泄漏扫描：固定九类加 unknown code 稳定，`directory_diagnostic=<fixed-code>` 只在目录 `INVALID_RESPONSE`、`metadata=1 / enumerate=1 / read=0` 时进入既有 JSONL `safe_message`；没有新增结构化字段，也没有 URL、正文、标题、字段值、Cookie、token、payload 或原始异常泄漏。危险 URL、缺字段、超限与不支持格式必须继续 fail-closed。

环境缺失、任何离线门禁失败、范围不精确或疑似泄漏时立即停止并报告；不得 `uv sync`、安装、下载、联网或修改依赖/锁文件。

## 绝对禁止与回传

- 禁止真实 YouTube/网络、B-1 重试、真实资源、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、push 和 source 清理。
- 不得将离线成功表述为 B-1 成功、真实兼容性、发布批准或 TASK-014 Go；TASK-014 必须保持 `IN_PROGRESS / No-Go`。
- 成功后只报告 merge SHA、双父顺序、first-parent 范围、每个离线门禁、泄漏扫描、main/source 洁净度及未运行的真实资源。不得自行设置 `DONE`。
