# TASK-014B8：受限键名级字幕目录诊断

- Status: `ACCEPTED`
- Assignee: `Codex Product Integrator（已授权，尚未启动）`
- Reviewer: `独立 Codex Reviewer（APPROVE，P0--P3=0）`
- 依赖：TASK-014B3/B4/B5/B6/B7 `DONE`、ADR-019 `Accepted`
- 实施基线：`main@43f2c748c43215facb231f76a0c93ac45d350657`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic`
- Branch：`codex/task-014b8-restricted-directory-keyname-diagnostic`
- accepted source / Reviewer evidence: `96dee64ec7ab172d036e8472ffc3f65efa0cb6c4`（唯一父提交
  `2334374f66497546108d12be541ab137b4a8981a`；后者唯一父为
  `43f2c748c43215facb231f76a0c93ac45d350657`）
- Reuse decision：`DIRECT` — 既有 subtitle Adapter、B4 directory-only、B5 安全摘要、ADR-017/ADR-018 固定分类及离线 integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

未合并 B-1 B7 evidence `8f5dfce33ac77a45800f4ff53ff6e7054d8f68b0` 仅作只读失败 evidence；不得合并、重写、重跑或写成通过。实现 ADR-019 的单次、受限键名例外：仅在目录映射 `unknown` 边界向既有安全摘要提供可审计且无值的键名集合，不修复真实兼容性、不扩大解析。

## 冻结契约

- 仅同时满足 directory-only、目录 `INVALID_RESPONSE`、`directory_origin_mapping`、`directory_fingerprint_unknown` 且 `read=0` 时，可附加可选 `directory_key_names`。
- 只能输出完整通过 `[A-Za-z][A-Za-z0-9_]{0,63}` 的直接映射键名：去重、稳定 ASCII 字典序、最多 16 项。任一候选不合格、超过上限或候选集不可靠时，整个字段必须省略；不得截断、部分输出、哈希、替换或递归读取值。
- 禁止字段值、URL、正文、标题、语言值、轨道值、路径、原始异常、Cookie、token、payload、用户数据或凭据。仅可用合成安全键名覆盖允许/拒绝/上限；不得加入真实目录 fixture、URL、身份、语言、轨道或字段值。
- B6/B7 诊断与词表、默认/directory-only 计数、退出码、CLI、临时根、ID 上限、无重试、零业务记录与 fail-closed 边界必须不变；不得扩大目录解析接受面、增加兼容规则或真实资源权限。
- TASK-014 始终 `IN_PROGRESS / No-Go`；B8 不构成真实 B-1 成功、真实服务验证或发行批准。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence、fixture 路径或任何其他路径。

## 独立 Reviewer 控制面

- 审查范围严格为 `43f2c748c43215facb231f76a0c93ac45d350657...2334374f66497546108d12be541ab137b4a8981a`，且只能是上述五条路径。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，仅追加审查 evidence；该 evidence 必须以 `2334374…` 为唯一父提交。不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。
- 必须验证 `directory_key_names` 仅在 directory-only、目录 `INVALID_RESPONSE`、mapping、unknown、enumerate=`1`/read=`0` 同时满足时出现；最多 16、稳定排序/去重且仅为 ADR-019 规范 ASCII 合成安全键名。不合格、超限、疑似 URL/凭据/路径/控制字符必须 fail-closed 省略。
- 必须验证 B6/B7 诊断与 default/directory-only、退出码、CLI、临时根、ID 上限、无重试、零业务记录、解析接受面和 fail-closed 边界未退化；stdout/stderr/JSONL、测试与 handoff 除该授权例外外不得泄露字段名/值、URL、正文、标题、语言、轨道、路径、异常、Cookie、token、payload 或用户数据。

## 唯一离线检查

开始前核验 source 分支、HEAD 和洁净度；不符立即停止。Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止。只有已有离线 `.venv` 可用时才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、OpenAI、付费调用、push、合并、source 清理、测试/检查外产品命令与 `.codebase-memory` 工件。
- 只创建一个仅含允许路径的 Implementer commit，并追加 `handoffs/TASK-014.md`。不得改任务/状态/ADR/prompt，不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。

## 验收与 Product Integrator 控制面

- Reviewer evidence/accepted source `96dee64…` 的唯一父为 `2334374…`，且只修改 `handoffs/TASK-014.md`；Verdict=`APPROVE`，
  P0--P3 均为 `0`。source 已核验干净。完整 B8 Diff `43f2c748…...96dee64…` 严格且仅为本卡授权的五条路径。
- Reviewer 已独立通过 focused `119`、mypy、Ruff、CLI help、范围及 stdout/stderr/JSONL/test/handoff 泄漏检查；未运行 build 或全量 pytest。
  后两项不是通过证据，必须由 Product Integrator 在合并前完成。
- Product Integrator 只可对固定 accepted source 执行 `git merge --no-ff 96dee64…`。缓存缺失、locked offline sync、focused `119`、
  全量 pytest、mypy、Ruff、CLI help、offline build、五路径范围或泄漏扫描任一失败，均立即停止、不合并、不修复且不得重试。
- TASK-014B8 的 `ACCEPTED` 不等于 `DONE`、真实 B-1 成功、真实服务验证或发行批准；TASK-014 始终为 `IN_PROGRESS / No-Go`。
