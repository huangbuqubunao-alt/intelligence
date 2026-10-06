# V1X-PHASE11R1 交接报告

## 元数据

- Task: `V1X-PHASE11R1` — Final Polish + Capability Truthfulness Fix
- Role: `Implementer`
- Agent/session: DeepSeek Harness, `space-bunny-free`
- Base branch/commit: `e0841854adfe51dafcded7d1adbf3519c335cba2`（Phase 11R accepted HEAD）
- Worktree: `/Users/hua/Documents/yia-worktrees/v1x-bilibili-final-polish`
- Branch: `deepseek/phase11r1-bilibili-final-polish`
- Head commit: 见 §Commit
- Started: 2026-10-06
- Reported: 2026-10-06

## 目标与范围

- 任务目标：修复独立复验发现的 1 个剩余 P1（F-01 状态本地化 + 320px 溢出）与 2 个
  范围内 P2（公开字幕能力过度声明、`-40003` 决策记录与代码不一致）。
- 允许修改：Content 状态投影、状态标签 CSS、`/settings` 能力投影、Phase 11R 决策记录、
  对应测试。
- 明确未做：未添加产品功能；未重新设计 Bilibili；未恢复 Phase 12；未新增迁移；
  未引入 ASR；未修改转录／证据权威；未改动 creator Following 撤回。

### F-01 根因确认（独立复现）

`Status` 组件有明确的双参数契约（`App.tsx:429-446`）：`value` 是枚举，决定色调并按枚举
查表；`label` 是已经成句的文案，直接交给 `t()`。Creator Following 一直正确使用该契约
（`App.tsx:2425-2428`）。但所有非 creator 的 Content 分支把**已解析的英文句子传给了
`value`**：

```tsx
<Status value={... ? bilibiliStatus(item.processing_status) : ...} />   // 旧 App.tsx:1469
```

`Status` 于是把整句走 `statusLabel()` 的 `replaceAll("_"," ").toLowerCase()` 反驼峰分支，
产出 `"The stored bilibili source failed verification. its evidence is unavailable."`。
该字符串不是 `uiLanguage.tsx` 中文表里的键（表里是首字母大写的正确句子），`t()` 的
`chinese[text] ?? text` 回退把被破坏的英文原样显示在中文界面里。

`localStatus()` 的同类缺陷是 `?? status`——未知状态直接回落到原始枚举，`LOCAL_SOURCE_UNTRUSTED`
以 backend 词汇显示。

### 实际修改

| 文件 | 修改 |
|---|---|
| `frontend/src/workspace/App.tsx` | 新增 `contentStatus()`，4 个 Content 分支改为传 `label=`（`value=` 保留枚举用于色调） |
| `frontend/src/workspace/LocalImport.tsx` | `localStatus` 改为显式 `statusCopy` 表 + `SOURCE_UNTRUSTED` / `LOCAL_SOURCE_UNTRUSTED` 文案；`?? status` 原始枚举回退改为诚实未知态文案 |
| `frontend/src/workspace/uiLanguage.tsx` | 新增 1 条 zh-CN 键（未知态文案） |
| `frontend/src/workspace/styles.css` | `.status` 允许换行 + `max-width:100%` + `overflow-wrap:anywhere`；`.list-row` / `.reading-meta` 允许换行 |
| `src/youtube_intel/local_api.py` | `public_captions.available` → `False`，code → `PUBLIC_CAPTIONS_NOT_OBSERVED` |
| `docs/decisions/V1X-PHASE11R-BILIBILI-REALWORLD-REMEDIATION.md` | 删除无证据支持的 `-40003` 映射声明；补齐实际已实现的 `-403/-101/-111`；新增 unknown code → `METADATA_FAILED` 行；新增字幕能力声明小节 |

## 复用决策

- **DIRECT**：沿用 `CreatorFollowing.tsx` 已有的 `Status value/label` 本地化架构，未引入新机制。
- **DIRECT**：沿用 `transcriptionCopy()`（`LocalTranscription.tsx:41`）已有的「解析为文案而非
  原始枚举」回退模式。
- **DIRECT**：沿用 `v1x-phase1b/1c.e2e.mjs` 已有的 Playwright `page.route` 拦截式 e2e 模式，
  新回归测试不依赖任何真实后端或网络。
- **REJECT**：为中文界面做「英文句子替换式」修复 —— 明确被任务禁止，且脆弱。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| F-01 zh-CN 不再显示 backend 句子 | PASS | `ContentStatusLocalization.test.tsx`；e2e 断言 `The stored bilibili source failed verification. its evidence is unavailable.` 不出现 |
| F-01 en 保持自然 | PASS | 同上 |
| `LOCAL_SOURCE_UNTRUSTED` 双语 | PASS | `LocalImportStatus.test.tsx` + `ContentStatusLocalization.test.tsx` |
| 无原始枚举回落 | PASS | `localStatus()` 对任意输入均不含 `_`；e2e 断言 `SOURCE_UNTRUSTED` / `LOCAL_SOURCE_UNTRUSTED` 不出现 |
| 320px 无溢出 | PASS | `status-responsive.e2e.mjs`；`documentElement.scrollWidth > innerWidth === false` |
| 768/1024/1440 不受影响 | PASS | 同上；几何实测 ≥768px 时 pill 保持单行 395px，与修复前固有宽度一致 |
| 字幕能力不再过度声明 | PASS | `test_settings_does_not_claim_a_public_caption_capability` |
| 手动 Bilibili 导入仍可用 | PASS | `test_withdrawing_the_caption_capability_leaves_bilibili_import_available` |
| 无字幕语义不变 | PASS | `test_a_bilibili_content_without_a_public_caption_stays_an_honest_metadata_only_record` |
| 无 ASR 回退 | PASS | `bilibili_content.py` / `providers/bilibili.py` 中零 `transcribe`/`whisper`/`asr` 引用 |
| `-40003` 决策与代码一致 | PASS | 决策记录改为记录真实实现；代码未新增无证据映射 |
| creator Following 仍撤回 | PASS | `CREATOR_FOLLOWING_AVAILABLE = False` 未改动 |
| Schema 仍 34 | PASS | `check_phase11r1_database.py`：`user_version=34`、33 条迁移 |

## 检查结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `uv run python -m pytest -q`（全量后端） | PASS | **3596 passed, 1 skipped**，0 failed（基线 3594 + 本任务新增 2） |
| Phase 11R 回归 | PASS | 49 passed |
| Phase 11 回归 | PASS | 49 passed |
| Phase 10B Bilibili 回归 | PASS | 172 passed |
| Local provider 回归 | PASS | 84 passed |
| YouTube manual ingestion 回归 | PASS | 25 passed |
| Backup/Restore 回归 | PASS | 37 passed |
| 集成 V1.x 回归 | PASS | 27 passed |
| `uv run ruff check .` | PASS | All checks passed |
| `uv run mypy src`（strict） | PASS | Success: no issues found in 94 source files |
| `uv run python -m compileall -q src scripts tests` | PASS | exit 0 |
| `git diff --check` | PASS | 无输出 |
| `python scripts/check_phase11r1_database.py` | PASS | `quick_check`/`integrity_check` = ok，`foreign_key_check` 空，`user_version` = 34，33 条迁移 |
| `npx vitest run`（前端全量） | PASS | 11 files / **196 tests**（基线 189 + 新增 7） |
| `npx tsc -b --pretty false` | PASS | exit 0，无错误 |
| `npx vite build` | PASS | 47 modules transformed |
| `node frontend/status-responsive.e2e.mjs` | PASS | **8 场景**（zh-CN/en × 320/768/1024/1440），每场景 6 个状态，`offenders: []`，`rawVocabularyLeaks: 0` |

> 注意：必须使用 `uv run python -m pytest`。裸 `uv run pytest` 不会把仓库根目录加入
> `sys.path`，导致 `tests/unit/test_acoustic_remediation.py` 的
> `from scripts.phase9r_profiles import ...` 报 `ModuleNotFoundError`。这是调用方式
> 问题而非回归：在未改动的基线 e084185 上同样如此，改用 `python -m pytest` 即 16 passed。

## Diff 复核

- 修改文件：7 个已跟踪文件 + 4 个新增文件（2 个 vitest、1 个 e2e、1 个数据库检查脚本）。
- 是否存在任务范围外修改：否。后端仅 `/settings` 能力投影一处展示层改动。
- 是否存在生成文件或格式化噪声：否。`frontend/node_modules` 为本地依赖软链，提交前移除。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。无新增/升级依赖，
  无迁移（仍 33 条迁移文件，schema 34），无网络调用，无凭据。

## 失败、跳过与风险

- 已解决失败：
  - 首次运行 e2e 在 `zh-CN/320/detail-local-untrusted` 复现横向溢出，确认 P1 成立；
    修 CSS 后 8 个场景全部通过。
  - `tsc` 报 4 处类型错误（`provider` 可选导致 `string | undefined`），已修。
- 跳过检查及原因：
  - `uv run ruff format --check .` 报告 235 个文件需要格式化；在**未改动的基线
    e084185** 上运行结果完全相同（同样 235 个），属仓库既有状态，本任务不引入、
    不修复（贸然格式化会产生巨大的无关 diff）。
- 剩余风险：
  - `.status` 色调现在取自枚举而非句子。绝大多数状态结果一致；`CAPTION_INVALID`、
    `SOURCE_UNAVAILABLE` 等由 neutral 变 warning，属**语义更正**（未通过验证的来源
    本就是警告态）。无任何测试或 e2e 断言色调 class。
  - `localStatus()` 新增 `UNAVAILABLE` / `NOT_PROCESSED` 两个映射，用于替代原先靠
    `statusLabel` 偶然命中的行为，渲染结果不变。
- `DECISION NEEDED`：None

## 延期项（本任务范围外，记录备查）

`Loading Home…` / `Loading Sources…` / `Loading Source…` / `Loading verified Intelligence…`
通用文案；`NEEDS_ATTENTION` 的人工处置 UI；multipart；`last_success_at` 与
`CAPTION_UNAVAILABLE` 语义；Bilibili Creator Following 重新启用；新字幕端点；字幕刷新；
ASR；YouTube Following；后台检查；通知；其他 Provider；Deep Analysis；Research 功能。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA: 见 §Commit
- 复现／验证说明：`frontend/status-responsive.e2e.mjs` 为确定性复现，使用 Playwright
  拦截 `/api/v1/**`，不接触真实 Bilibili、后端或网络。