# TASK-READINESS-NATIVE-DIRECTORY-SCAN-V2 交接报告

## 元数据

- Task: `TASK-READINESS-NATIVE-DIRECTORY-SCAN-V2`
- Role: Implementer，恢复中断实现；独立 Reviewer 由 root 安排。
- Base: `68fb4468ad4114699debc05741471c9aa47c3f76`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-native-directory-scan-v2`
- Branch: `codex/task-readiness-native-directory-scan-v2`
- 报告日期: 2026-10-15；实现和本交接同一提交，精确 SHA 由最终回传的 `git rev-parse HEAD` 记录。
- 任务/授权: task card、对应 agent-prompts、`NATIVE_DIRECTORY_BOUNDED_SCAN_V2_PLAN.md`、`CONTINUING_AUTHORIZATION_2026_10_15.md`。未修改公共任务状态或自行接受/合并。

## 目标与实际范围

真实单次 metadata 测量为 23,086 raw、301 native、129 supported native、
22,785 tlang、10,966,987 canonical UTF-8 bytes；旧 raw 4,096 规则拒绝合法目录。
这些是 root 既有测量，不是本作者新联网，也不是字幕正文成功证据。

- `providers/subtitles.py`: 明确将 raw 策略从 4,096 改为 32,768；新增 manual/automatic 共享的完整目录 16 MiB UTF-8、524,288 节点、depth 8、5 秒 monotonic 映射预算。
- 对标点、键、值、转义、多字节字符和未知字段增量计费。字符串最多按 2,048 code points 分块编码，不先序列化整个不可信目录。重复引用每次计费；活动递归检测循环；非 JSON 值、非字符串键、非有限数值和未知 Python Sequence 拒绝。
- 名称 runs 仍单次按既有 1,000 runs/字符边界处理，未知元数据纳入完整预算。中断补丁曾允许未知 `range`，本次以先红后绿测试修正；保留既有 name.runs Sequence 兼容。
- 保持 native 1,024/buckets 512 和既有 lang/ext/name/URL/HTTPS/host/no-userinfo/no-fragment 校验。每个 translated 条目完整校验/计费后才丢弃；任一上限耗尽整目录失败，无 partial listing。
- `test_subtitle_directory_limits.py` 和 `test_subtitle_provider.py`: 新预算、原安全负控及必要大目录 capture 集成覆盖；仅对应原 4,097 策略断言按已批准 v2 更新，未跳过/降低其它测试。
- 未修改 App、state、Schema、其他 metadata、Provider 配置/选项、依赖/锁文件、owner/正式数据/凭据/模型资格；没有真实正文/网络/模型调用。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 合法大目录 | PASS | 明确合成 23,086 raw/301 native/129 supported/178 buckets；包含 5 个测量字段、391 URL 长度、21 名称长度，完整字节不少于真实测量且小于 16 MiB；保留原位置 0..300 和 URL 字节身份 |
| raw 32,768/32,769 | PASS | unit 跨两来源累计；integration 支持/unsupported 混合；原 4,096/4,097 都保留为兼容正控 |
| 16 MiB 精确边界 | PASS | exact 接受、+1 拒绝；UTF-8/引号/换行/未知大字段；manual/automatic 各自低于总限但合计溢出仍拒绝；simpleText/runs 未知子字段同样计费 |
| 深度/节点/循环/非 JSON | PASS | depth 8 接受/9 拒绝；共享 524,288 exact 接受/+1 拒绝；循环、object/bytes/NaN/Infinity/非字符串 key/range 拒绝 |
| monotonic deadline | PASS | 同一预算跨来源，fake elapsed 4.999 接受/5.0 拒绝；不使用真实 sleep |
| 原安全门禁与 retention | PASS | native 1,025、bucket 513 保持拒绝；恶意 translated 在 4,500 前缀后仍走原具体 URL/name/ext 失败；原惰性 runs/buckets、异常安全化测试保留 |
| 目录/正文请求与缓存/capture | PASS | unit opener 禁止正文；新增 23,085 translations +1 native 的正常 SQLite acquisition，只请求原生正文一次/目录一次，保留可信 timing/capture；既有 signed query/格式/来源/选择/恢复断言保留 |
| 源码范围 | PASS | AST 对比 base：仅改既有 `_track_name`、`_map_directory`、`YtDlpSubtitleAdapter.enumerate_tracks`；其余 38 个函数完全相同，无删函数，新增仅私有 budget；选中正文 transport/URL 校验/yt-dlp 选项均相同 |

## 检查结果

所有本次日志位于 worktree 内忽略目录 `.var/native-scan-v2-resume/`。

| 命令/检查 | 结果 | 日志 |
|---|---|---|
| 三个修改 Python 文件 `py_compile` | PASS | 实际运行成功，无语法错误 |
| `.venv/bin/ruff check src tests scripts` | PASS | `full-ruff.log` |
| `MYPYPATH=src .venv/bin/mypy --strict src` | PASS，102 source files | `full-mypy.log` |
| `PYTHONPATH=src:. .venv/bin/python -m pytest tests/unit/test_subtitle_directory_limits.py tests/integration/test_subtitle_provider.py -q` | PASS，252 tests/35.24s | `expanded-focused-pytest.log` |
| 11 文件完整受影响 pytest | PASS，568 tests/256.93s，1 既有 duplicate-ZIP 负控 warning | `affected-full-pytest.log` |
| base→candidate AST scope review | PASS | `ast-scope-review.log` |
| `git diff --check`/范围复核 | PASS | 无格式噪声/范围外文件 |

完整受影响命令：

```text
PYTHONPATH=src:. .venv/bin/python -m pytest -q
 tests/unit/test_subtitle_directory_limits.py tests/unit/test_subtitle_policy.py
 tests/integration/test_subtitle_provider.py tests/integration/test_runtime_composition.py
 tests/integration/test_provider_dispatch_crash_recovery.py
 tests/integration/test_retained_subtitle_derivations.py
 tests/integration/test_retired_subtitle_failures.py
 tests/integration/test_caption_repair_completion_clock.py tests/unit/test_backup_restore.py
 tests/integration/test_public_subtitle_smoke.py tests/integration/test_verified_timed_transcript.py
```

## 中断保存、TDD 与失败证据

- 写入前保存原 dirty 二文件完整 binary diff：`interrupted-exact.patch`。复用已有 `.venv` symlink，不安装依赖；无 reset/clean/delete。
- 原作者证据从 `/tmp` 原样复制到本忽略目录：`native-scan-v2-tdd-red.log` 为旧实现 13 FAIL/46 PASS；`native-scan-v2-green-focused.log` 为 220 PASS/1 FAIL（旧 4,097 拒绝断言），没有把历史失败改写为 PASS。
- 恢复后的无 `PYTHONPATH` 命令误导入 `/Users/hua/youtube-intel`，221 个 fixture setup errors：`ModuleNotFoundError: No module named 'youtube_intel.model_settings'`，`tests/conftest.py:18`；见 `initial-focused-pytest.log`。明确绑定当前 `src` 后解决，未改 fixture/配置/依赖。
- 绑定当前源码后的首次 220 PASS/1 FAIL：`test_directory_raw_entry_scan_remains_finitely_bounded`、原 line 918、`DID NOT RAISE TranscriptError`，见 `focused-pytest.log`。旧策略断言与批准的 v2 冲突，停止重复同一断言，按方案改为 32,769 负控并保留 4,097 正控。
- 基于 `git show HEAD:.../subtitles.py` 在独立测试进程加载 base 模块，新增场景确认 14 FAIL/6 PASS：`baseline-red.log`；不覆盖 worktree 文件、不改历史。
- 本次发现未知 `range(3)` 被继承补丁接受：先红 1 FAIL/5 PASS，收紧未知数组后 6 PASS；日志 `non-json-sequence-red.log`、`non-json-sequence-green.log`。

## 复用与许可证

- `DIRECT`: 既有锁定 `yt-dlp==2026.7.4`、SubtitleAdapter/选择/URL 校验/字幕与 capture 测试；Python 标准库 `json`、`math`、`time.monotonic`（PSF）。本地安装 metadata 确认 yt-dlp `License-Expression: Unlicense`，与 `docs/THIRD_PARTY_NOTICES.md` 一致；未 vendor 或复制第三方源码。
- `ADAPT`: 仅项目既有私有映射/名称处理加入有界计费，无外部代码移植。
- `REJECT/DEFER`: 官方 `skip=['translated_subs']` 对 automatic 无效（root 既有 8-case AST 证据）；不使用伪修复 flag、不 patch producer、不升级依赖、不引入另一字幕库。
- Jev 路由 HTTP 451，继续既有 strong/default 和独立安全审查，未降低审查要求。

## 风险、剩余门禁与实现者结论

- 预算是 `extract_info` 返回后的 Adapter 扫描/复制/retention 防护，不限制 yt-dlp 的预解析峰值或已分配对象；真实 root 测量约 14.27 MB 不能被称为本 guard 的上游 RSS 保证。
- 尚未运行全 backend/前端/build/macOS GUI。本次完整受影响后端范围如上；真实普通 UI 导入、字幕→Summary→Evidence→Backup 门禁仍由 root 在独立 APPROVE/接受后执行。
- 全部真实失败、429、旧 FAILED_FINAL 无 retry、Schema/模型资格仍按原记录；本修复不复活旧失败、不放开模型、不代表全链路已可用。
- 实现者建议：本次检查全通过，提交为 `IN_REVIEW`，作者 clean STOP；独立 Reviewer 的 APPROVE、root ACCEPT/整合均未自行填写。`DECISION NEEDED: None`。
