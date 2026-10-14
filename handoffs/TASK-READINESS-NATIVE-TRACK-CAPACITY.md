# TASK-READINESS-NATIVE-TRACK-CAPACITY 交接报告

## 元数据

- Role: Implementer / caption_resume。
- Base: `05f31372d0b05ecdecaa711aead19ab7a3ad71db`。
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-native-track-capacity`。
- Branch: `codex/task-readiness-native-track-capacity`。
- 用户精确批准 NATIVE_TRACK_CAPACITY_PROPOSAL.md，2026-10-14任务恢复/分配。
- 建议 IN_REVIEW；提交后 STOP，Reviewer intel_bounded_review；不自审或采用。

## 目标、复用与实际范围

真实跟踪新Content目录失败的根因：支持格式的`tlang`机器翻译轨先计入1024额度，
到最终listing才被排除。大量本来不允许Original authority的衍生轨使少量真实原生
候选不能进入。修复只将现精确tlang判定移动到_map_directory **全部校验之后**，
支持格式且无tlang的原生候选才计数/保留。不要改变目录安全边界或重试生命周期。

DIRECT Python标准库原urlsplit/parse_qsl（keep_blank_values=True）和现URL/name/
结构validator、SubtitleTrack；yt-dlp固定依赖仅经现adapter枚举。graph-first复核
provider模块（索引旧文件）、再按本工作树具体_map_directory定位；复核ADR-006/
现Reuse Register，不新增组件、依赖、下载、auth、外部协议或权力。

实际产品仅 `src/youtube_intel/providers/subtitles.py`：

- 原URL/语言/entry/name/ext全部校验完成后，支持格式的精确`tlang`key被排除，
  然后按原1024native上限计数。URL、语言、source_type、格式和原位置不改写。
- 私有 `_MappedDirectory.has_supported_format` 仅boolean bookkeeping。
  充分验证后的支持格式（包含翻译）让原“纯合法翻译目录”继续返回空listing；
  真正只含unsupported格式的非空目录仍拒绝。root明确确认这是已批准必要private
  helper范围。标记不成为候选/Transcript/Evidence/持久化authority或publicDTO。
- enumerate最终直接返回已验证native tuple；无额外请求/候选回退/模型等处理。

测试：原unit仅追加33案例（40含原7完整），integration追加一个正常SQLite获取
流程。其余生产文件、旧断言/测试、门禁、Schema/state/runtime、网络/URL验证、
512桶/4096raw/1024native限制及selection/format policy versions均无变化。

## 验收证据

| 项目 | 结果与证据 |
|---|---|
| 1024合法派生轨+少量原生、空/重复/encoded精确tlang | PASS；保留3原生、manual先于auto、原位置512/513/1027、原signed普通query字节完整 |
| 非tlang的Tlang/tlangx普通query | PASS；不误排除，不改签名/URL或轨身份 |
| 1024native+翻译/cumulative来源 | PASS；真正1025native仍同原supported-limit错误 |
| 所有raw及language桶均继续计数 | PASS；4096entry含4095翻译+1native合法/position4095，4097仍拒绝；512translated桶为空合法，513拒绝 |
| malformed翻译仍充分验证 | PASS；支持/unsupported格式的恶意host、credentials、fragment、HTTP、超长/nullURL、超长/畸形name、缺ext/url、坏ext均拒绝；先有1024合法翻译不能遮住后续坏字段 |
| 纯合法translatedsupported/純unsupported区别 | PASS；1025translatedjson3为空无authority；1025ttml仍no-supported-formats拒绝；原translation-only测试不改 |
| 元数据枚举、零翻译bodyreads | PASS；所有unit adapter sentinel禁止正文，目录调用1，不新增网络 |
| 正常SQLite获取 | PASS；1024manual翻译+1auto原生只读原生JSON3正文1次/目录1次且download=false，真实job SUCCEEDED/TRANSCRIPT_READY、verifiedtimedcue与文件存在，响应正常关闭 |
| 原字幕policy/native capture/恢复与Backup边界 | 下述9文件474PASS，另新增integration1PASS；旧来源/CAS/raw/归档38/restart/Backup规则保持 |

## 检查与失败保留

先py_compile/Ruff，再TDD：原实现+31新增负控 **29FAIL/9PASS /0.93s**，
`/tmp/native-track-capacity-tdd-red.log`。关键原错误
`subtitle track directory exceeds its supported track limit`，包括合法native无法保留
及过早容量错误遮蔽后续malformed的具体校验；没有删除/weak/skip旧测试。另2纯目录
合同随后追加，最终unit **40PASS /0.70s**，
`/tmp/native-track-capacity-green-focused.log`。

| 检查 | 实际结果 |
|---|---|
| py_compile provider/unit/integration | PASS |
| Ruff全src/tests/scripts | PASS；/tmp/native-track-capacity-final-ruff.log |
| MYPYPATH=src strict mypy src | **102files PASS**；/tmp/native-track-capacity-green-mypy.log |
| 9文件受影响完整回归 | **474PASS /240.49s /1既有duplicateZIP warning**；/tmp/native-track-capacity-regression.log |
| 新正常获取integration（后补收集，单独验证） | **1PASS /1.28s**；/tmp/native-track-capacity-new-integration.log |
| git diffcheck/范围 | PASS；仅provider、原unit追加、原integration追加、本handoff |

9文件准确命令：`PYTHONPATH=src:. .venv/bin/python -m pytest -q
 tests/unit/test_subtitle_directory_limits.py tests/unit/test_subtitle_policy.py
 tests/integration/test_subtitle_provider.py tests/integration/test_runtime_composition.py
 tests/integration/test_provider_dispatch_crash_recovery.py
 tests/integration/test_retained_subtitle_derivations.py
 tests/integration/test_retired_subtitle_failures.py
 tests/integration/test_caption_repair_completion_clock.py tests/unit/test_backup_restore.py`。
该命令collection后才添加最后一个integration，因此准确报告474+独立1；没有称同一
命令475或后端全部PASS。最后一个只增加测试，产品及已检查行为不再修改。

## 限制、门禁与剩余项

- 根主控只有 FOLLOWING_NEW_CONTENT_DIRECTORY_PROBE.json 的真实supported-limit
  错误和元信息，没有完整目录payload。未冒充真实完整回放，本作者只用明确fixture
  严格重现目录形状；真实失败与任何429原证据不改。
- 未真实公网/模型/Cloud调用、不获取翻译/媒体、不读Cookie/凭据/owner/正式数据。
  .venv是已批准现运行时的ignored symlink，未安装/改依赖或stage该链接。
- 未运行全backend/前端/build或macOS GUI：本有界provider改动完成上述受影响回归/
  static；root最终全量门禁及独立接受后的真实普通新导入/目录/备份恢复仍必需。
  真实provider若429或失败须如实保留，不以fixture成功替代。
- 本修复不赋模型资格或Evidence authority，不改变历史FAILED_FINAL重试或退休/
  归档语义；既有入口能否恢复旧失败是主控独立后续范围，不借本任务写生命周期。
- Schema38、普通UI各树STOP未写；新LOCAL_TEXT作者范围与本provider隔离。旧审查
  拒绝/全部实际模型FAIL与production资格关闭仍保留。没有main合并/push/部署。

## Reviewer与主控

待独立Reviewer审查提交、完整差异及负控；Implementer不填写APPROVE/ACCEPT。
提交后STOP。没有DECISION NEEDED或新增敏感审批范围。
