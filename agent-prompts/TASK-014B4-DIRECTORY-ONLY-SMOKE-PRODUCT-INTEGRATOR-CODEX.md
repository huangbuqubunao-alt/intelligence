# TASK-014B4 — 受限 directory-only 公开字幕 smoke Product Integrator

你是 TASK-014B4 的 Codex Product Integrator。只整合已接受的 source；不得开发、修复、修改 source、重新设计、真实验证、推送或发布。本包不启动 Integrator。

## 固定整合对象

```text
Task: TASK-014B4 — restricted directory-only public subtitle smoke
Role: Product Integrator
Control-plane base: dynamic clean main containing this authorization (must descend from 2dfa4dcec89f7abaa0c32d74334f3d766050da94)
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b4-directory-only-smoke
Accepted source branch: codex/task-014b4-directory-only-smoke
Accepted source / Reviewer APPROVE evidence: d211d62b89754683f00ec841c1774574003323a1
Required sole parent of evidence: 2959275b0f61a1fb3a7e9ac520a56fa89e4e2b14
Reviewed product range: bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d...2959275b0f61a1fb3a7e9ac520a56fa89e4e2b14
Complete accepted source range: bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d...d211d62b89754683f00ec841c1774574003323a1
Required merge: git merge --no-ff d211d62b89754683f00ec841c1774574003323a1
Reuse decision: DIRECT — existing locked CLI, PublicSubtitleSmoke, Adapter boundary, JsonlLogger, and offline Fake/integration test infrastructure; no dependency or third-party code change
```

## 整合前门禁

- 只读核验动态 main 与 source 的身份和洁净度；source HEAD/branch、evidence 的唯一父提交、Reviewer Verdict=`APPROVE` 及 P0--P3=0 必须精确匹配。main 在授权后若已有任何产品变动、source 不干净、拓扑或范围不符，立即停止并报告。
- `2959275…` 必须是唯一 Implementer 产品提交（唯一父 `bbd3fddd…`）；`d211d62…` 必须只追加 `handoffs/TASK-014B4.md`。完整 accepted source Diff 必须严格且仅为：

  1. `src/youtube_intel/cli.py`
  2. `src/youtube_intel/public_subtitle_smoke.py`
  3. `tests/integration/test_operations.py`
  4. `tests/integration/test_public_subtitle_smoke.py`
  5. `handoffs/TASK-014B4.md`

- 必须拒绝依赖/`uv.lock`、Schema/migration、domain/config、Provider Adapter、`logging.py`、默认 CLI 行为、README/发布结论、B-1 evidence、任务/状态控制面或任何额外路径变化。不得修改、暂存、提交、rebase、cherry-pick、清理或删除 source。

## 唯一整合与整合后门禁

仅在前述门禁均通过、main/source 均干净且无冲突时，执行一次固定命令：

```text
git merge --no-ff d211d62b89754683f00ec841c1774574003323a1
```

冲突、命令失败或任何额外文件出现时立即停止；不手工解决、不补修、不创建额外产品提交。合并后必须确认双父顺序（第一父为开始时的 main，第二父为 accepted source），accepted source 是 merge 祖先，且 first-parent Diff 严格为五条允许路径。

仅在已有离线环境可用时，按序运行下列授权检查；缓存缺失、锁变化、任何网络/下载迹象或任何失败立即停止并如实报告：

```text
uv lock --check
uv sync --locked --offline
uv lock --check
uv run --offline python -m pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
uv run --offline mypy src
uv run --offline ruff check .
uv run --offline python -m youtube_intel --help
uv build --offline
git diff --check HEAD^1..HEAD
```

还必须进行范围和泄漏扫描，确认 directory-only 对每个目标为 metadata=1 / enumerate=1 / read=0，默认模式仍读取一份正文；全局配置在 runner/Adapter/temporary-root 前拒绝，非 smoke 拒绝该标志；无新 JSONL 字段、业务记录或 URL、正文、标题、字段值、Cookie、token、payload、异常文本或用户数据。必须确认没有 Pipeline、Job、ProviderCall 或 Artifact 业务记录，也没有认证、媒体或重试路径。

## 绝对禁止与回传

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、Cookie/登录/API key/凭据、真实 Vault/用户数据、模型、Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、push、source 清理和后续合并。
- 不得将离线 Fake 测试、静态审查或整合表述为 B-1 真实验证、发布批准或 TASK-014 Go；TASK-014 必须保持 `IN_PROGRESS / No-Go`。TASK-014B4 `ACCEPTED` 仅表示可进行受控整合。
- 成功时只报告 merge SHA、双父顺序、first-parent 范围、每项离线门禁、范围/泄漏扫描、main/source 洁净度与未运行的真实资源。不得自行设置 `DONE`。
