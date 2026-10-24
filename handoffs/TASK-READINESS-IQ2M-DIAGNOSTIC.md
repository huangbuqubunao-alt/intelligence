# TASK-READINESS-IQ2M-DIAGNOSTIC 交接

## 元数据与范围

- Role: QA Implementer `/root/model_setup_catalog_bound`。
- Base: `d61752bec647a93e7d255a51c639bbd1d85894a3`。
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic`。
- Branch: `codex/task-readiness-iq2m-diagnostic`。
- Reported: 2026-10-25 Asia/Shanghai；建议 IN_REVIEW，作者 clean STOP。
- 实际修改仅 own `.var/model-diagnostic-iq2m/` 私有 QA 与本 tracked handoff；Git没有业务代码差异，不合并/发布/改任务状态。

用户持续授权的小资源单例实验：同一9B/base/revision改用较小固定第三方Unsloth动态IQ2_M，原完整英文18cue/2Evidence、消息/schema/关注、正向语义门、think=false、全部OPTIONS8192/16384/300秒不变。前Q3模式实验实际fresh资源拒绝，零load/零gen，原raw/FAIL_STOP/marker状态保持。IQ2真实兼容性及质量仍未证明；一次实际失败即停止，不授后续样例/资格。

## 复用与最小差异

DIRECT 复制原已审 Q3 nonthinking135测试/harness，源 `/Users/hua/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic/.var/model-diagnostic-q3ks-nonthinking/diagnostic.py` SHA `3fd9a63a6abdbd050552d2d980a36a2030f732ec415f967284fa23b85d8aa9fe`。原文件、两测试、实际ARM64 header与旧配对owner共5项hash完全保留；仅在本WT复制，不编辑原实验。

沿用标准库和已批准 pytest/Ruff/.venv，未安装依赖或复制新第三方代码。原四权重/blob/manifest/config/relative-reference、文件identity、真实ARM64/main映射、PS日期padding但完整owner、version/source/三binary、runner flags/parent/listener/slot/lease/once/TTL/boundedHTTP/原始失败body/无隐式重试全部保留。原生false common-prefix及精确assistant suffix、完整新tokenize N、N+8192+2<=实际16384保持，不能复用720/722。

最小改动为实际artifact常量及严格config标签/manifest大小、独立scope/experiment、明确prior请求绑定。新package仍严格9字段；`prior_candidate`改为准备过但未执行的Q3 think=false `8677a347...`，candidate仅换model。original仍官方9B think=true `228c...`；candidate相对original仅model+think变化。canonical比较、strict bool和MODEL!=PRIOR_MODEL明确拒绝旧Q3/其他权重/旧mode/旧包。原135case、test函数名/顺序及55+8条assert数量全部保留，仅适配声明的candidate元数据；旧PS实际header与其对应owner固定为私有成对fixture，避免新STORE的当前daemon污染旧格式反控。

## 实际artifact来源与验证边界

采用root已经完整验证的 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/qwen35-9b-udiq2m-20261025/root-artifact-verification.json`、actual-show.json、actual-tags.json、daemon-owner.json、download-verified.json；本作者仅读取并hash绑定小元数据文件，零HTTP/零加载/零生成。原下载部分不作为权威，未用quantizer help猜标签。

- MODEL：`intelligence-qwen35-9b-udiq2m:3885219b`；STORE：同目录 `/models`。
- Manifest：SHA `2bd925165e77bf81c231c7f777503d86900f37ba8c42ae8f2082a699a8327f98`，**782B**（旧780不可复用）。
- Config：SHA `ff6fbef0d964942903aef3247b6a0e933e1505c8e348f40ccd6b66dafbc4b1c3`，176B，实际 `file_type=IQ2_M`、9.0B/qwen35/gpt2/qwen35/0409；GGUF general.file_type=29为root实际show证据。
- Weight：SHA `a31b6b4c603ddd66b5496ee065c9dd13b2b6de77dce9e5d59609aef8d39868e7`，3649365216B；固定repo commit3885219b6810b007914f3a7950a8d1b469d598a5；Apache2。
- 四payload总3649376748B，无projector；同一 **payload+2GiB=5796860396B** fresh下界，disk>=10GiB；不是峰值保证、没有降低margin。
- Template b507b9c2…13B、license50cbab8a…11343B实际与原相同，保留严格hash。
- 新root候选请求SHA `5f268ef04fe7930ef3e4e72f6f55f4b079c9607cca23abd93cef08ab7e50c387`/6809B，位于同目录candidate-request.json；对Q3false只改model。

## 检查与证据

| 检查 | 实际结果 |
|---|---|
| 新6项量化反控，适配前 | RED 3 FAIL / 3 PASS，原日志保留 |
| 全部原135 + 新6 | **141 PASS / 0.69s**，不跳过/删断言 |
| py_compile harness及3测试 | PASS |
| Ruff harness + 新mode/quant测试 | PASS |
| 继承compact test_diagnostic.py额外lint | 106继承E701/E702，原样披露；未称全lint绿 |
| 603项当前源/QA/原实验/实际元数据冻结 | 检查前后全部hash精确相等 |
| Git业务diff与diff check | 无业务diff；PASS |

本次不跑无关产品完整后端/前端：root既有固定6003/1026证据不受本私有QA变动影响，不借此声称实际模型通过。新增6例验证固定IQ2完整weight身份、独立experiment/marker、Q3/Q4/4B权重拒绝、margin与原完整OPTIONS/容量边界。原135保护均通过，额外原始失败、WIP plan、全部adaptation diff保留。

全部下列相对路径位于本WT `.var/model-diagnostic-iq2m/`；`source-before-final.json` 与 `source-after-final.json` hash完全一致。

| 文件 | SHA256 |
|---|---|
| `diagnostic.py` | `4b82152a2db2a53ac1c9c4c639193241535321be8a1f58c0206db25256403bec` |
| `test_diagnostic.py` | `7545f2bcccbde839cdfad067b833d4e13bdc94f266bc408cd1da1e76c92b62f4` |
| `test_mode_guards.py` | `c2f78e142242c7dcb55b6090859416749276f946f881996c291b3441eb914f2e` |
| `test_quant_guards.py` | `7dd2b55375523d3135aae98db1d99c8b173a3c3d68895ddeb13b37e26c936e39` |
| `offline-final.log` | `56ce82ccc4974cc1b4961d22e6045f0aa6923f5e4d5e7dee41efddd0db2e941c` |
| `quant-red.log` | `41a122cad91d5523dba0bfad3e4588edc403e71bc8259da2e2bba7b87ec6a6e4` |
| `compile-final.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-final.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `inherited-test-lint.log` | `49e04ed8e1dcc1d0662bd18aecfb6fa56cb005c44856b8f3bfe5c7a715a88c0e` |
| `source-before-final.json` | `000ed84f923dd45173eef490727262e5de06e219a3571ba2d5103728a33466c9` |
| `source-after-final.json` | `000ed84f923dd45173eef490727262e5de06e219a3571ba2d5103728a33466c9` |
| `actual-artifact-source-bindings.json` | `09795b3c4db1f8229561e00398a51864d4208d0ddb0d64a9e648ebd8076b148f` |
| `implementation-checks.json` | `8ceca074ecefdbf85d03c323d7add12cbba371e96717523204490c1cb9847254` |

## Root具体freeze、独审与唯一CLI

必须新包严格9字段：kind=DIAGNOSTIC_ONLY、case=real-deepthink-en、experiment=IQ2M_NONTHINKING_0409_EN_V1、harness_sha256、original、prior_candidate、candidate、frozen_inputs、daemon_owner。所有file binding为严格 `{path,sha256,bytes}`，绝对resolve正规文件。prior_candidate必须Q3false原8677a347…；candidate是上述5f268ef0…；旧Q3源/marker/raw/失败和完整原输入/政策/Evidence/语义预期均单独保留绑定。frozen_inputs还须包含当前harness/3tests/配对PSfixtures、当前产品helper/imports、原生renderer与官方来源/第三方来源区分、实际四payload/manifest/config/import证据、新任务/prompt/decision。root制作新具体包并独审 APPROVE_DIAGNOSTIC_ONLY 前，不能执行。

当前daemon-owner读得PID25107/新完整psline/固定ROOT；实际运行前fresh复核完整owner，不能仅信PID或此前内存。实际资源前置>=5796860396B/disk10GiB、无预加载runner、全文件/metadata/0409身份、lease、实际新N与slot等原门均须通过。新globalmarker只在本WT `.var/model-diagnostic-iq2m/generation-start.json`，最多1空preload+1真实generation；失败无重试。

Root唯一实际命令模板（包路径与完整hash替换为独审冻结的具体值，作者未执行）：

```sh
PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic/src \
/Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic/.venv/bin/python \
/Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic/.var/model-diagnostic-iq2m/diagnostic.py \
--package <ROOT_NEW_CONCRETE_PACKAGE_ABSOLUTE_PATH> \
--package-sha256 <ROOT_NEW_CONCRETE_PACKAGE_FULL_SHA256> \
--output /Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic/.var/model-diagnostic-iq2m/real-once-20261025 --execute
```

## 风险、审查与停止

没有产品/src/tests/scripts/frontend/config/Schema/依赖/凭据/owner/main改动；零真实网络/模型。更强量化可能无法正确输出/ground，仍受原完整正向语义要求约束：正确归因、相似非同一、人类核验等不能靠修补通过；NO_NEW合法但不满足该正向样例。结构化JSON仅AWAITING_INDEPENDENT_SEMANTIC_REVIEW，不产生CaseReceipt/资格。任何实际失败立即停止，未知保持closed；root须另证native cancellation/idle，再正常关闭自有daemon。不授权后续样例、profile、registry或生产采用。

实现无剩余阻塞，DECISION NEEDED=None；待独审具体包及root一次实际。WIP pending说明仅保留历史，不代表最终源码仍缺metadata；本交接及当前implementation-checks.json为最终QA事实。Reviewer/主控验收/整合由对应角色后填，作者clean STOP。
