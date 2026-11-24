# TASK-READINESS-Q3KS-MODE-ONLY-DIAGNOSTIC 交接

## 元数据

- Role: QA Implementer `/root/model_setup_catalog_bound`。
- Base: `3e24f965eb59abbe04a210fa3d5cbadfc3a4bbbc`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic`。
- Branch: `codex/task-readiness-q3ks-mode-only-diagnostic`。
- Reported: 2026-10-25 Asia/Shanghai。
- 建议状态：IN_REVIEW，仅 QA；不设任务 DONE、不整合/发布。

## 目标、范围与实际修改

本次仅准备单例新实验 `MODE_ONLY_NONTHINKING_Q3KS_0409_EN_V1`：固定已安装同一9B Q3_K_S、固定官方0409、完整原英文18cue/2Evidence、原消息/schema/OPTIONS/300秒，仅 top-level think=true→false；空消息 preload 同模式。旧Q3 thinking实际超时及原marker永久保留FAIL_STOP。本实验不重置旧尝试，不代表资格、case receipt 或后续样例授权。

实现仅在本 WT `.var/model-diagnostic-q3ks-nonthinking/` 新建私有 QA harness/测试/证据；Git 只提交本 handoff。没有改产品 src/tests/scripts/frontend/config、Schema、依赖、锁文件、正式数据、模型注册/描述；没有 HTTP、模型加载或生成。已有 approved .venv 只建 symlink，所有 Python 命令显式 `PYTHONPATH=$PWD/src`。

## 复用、来源与模式证据

DIRECT 复制 `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic/.var/model-diagnostic-q3ks/diagnostic.py`，原 SHA `3d7250d85d9307b7636497e8043cb2dd8e88c1f1c67cf219628c09e4a687e54b`，及原101测试和实际 ARM64 vmmap header。原三文件校验仍完全相同，见 original-input-hashes.json。原文件和失败证据未改。DIRECT 复用同 WT `.var/model-diagnostic-nonthinking/diagnostic.py` 已审 native false suffix 转换；不是从零新建执行框架。沿用本项目标准库/pytest/Ruff，未复制新第三方代码或增加许可负担。

原生 common text renderer 继续复用 `render_qwen35_prompt`；精确复用 system/user prefix，只把 assistant 后缀 `<think>\n` 替换为固定0409 primary qwen35.go349–355的 `<think>\n\n</think>\n\n`。这是 native false renderer 格式，不注入额外模型提示或修补输出。所有OPTIONS不变，未从不同官方 preset 混取参数。原第三方转载卡片不称官方原始；root 新官方 Jina 页面来源/限制单独记录，harness 不依赖页面指令。

保留所有 payload/tree/hash/symlink/lstat/runtime3binary、真实ARM64/main映射、PS日期padding但全owner严格、numeric listener、runner flags/slot/parent、实际完整 tokenize `add_special=true/parse_special=true`、fresh RAM/disk、once、跨进程lease、时限、响应结构/usage、失败原始body与无重试保护。没有增加强制x86-only impl映射。实际 false prompt 全新token数 N 由同一观测runner取得，不能复用旧720；N+8192+2<=实际16384不变。

新增 canonical 请求等价校验与 strict bool：original 必须官方9B+thinktrue；prior_candidate 必须该 original 只换成原固定Q3 tag；candidate 必须 prior 仅 thinkfalse。响应出现非空 thinking 拒绝。新输出/全局marker独占本 WT 新namespace，与旧失败marker完全分离。

## 离线验证

| 检查 | 真实结果 |
|---|---|
| 新模式反控，修改 harness 前 | RED 7 FAIL / 19 PASS，日志保留 |
| copied101 + 新模式33 | 134 PASS / 0.65s，594绑定文件检查前后hash完全一致 |
| 明确追加旧7字段package拒绝后完整组 | 135 PASS / 4.78s（原101 + 新34） |
| py_compile：harness/两测试 | PASS |
| Ruff：harness + 新增 test_mode_guards.py | PASS |
| copied compact test_diagnostic.py 额外lint | 106个继承 E701/E702，原已披露格式问题保留；没有称此文件全lint绿 |
| Git product diff | 空；唯一 tracked 改动为本 handoff |

原101所有case保留；仅相应candidate期望改为false、新namespace与新增freeze字段。完整native fake额外断言 preload=false/OPTIONS不变、tokenize完整false prompt、一次新N计数、无重复生成。新增覆盖true/ambiguous模式、原模式伪装、全部10个OPTIONS篡改、错误renderer后缀/输入、thinking正文、旧experiment/旧7字段package/缺prior及prior消息或预算篡改、candidate额外shift差异。原超时raw和源RED不删除。

134次检查有完整594前后hash证明；为root要求再加一项明确旧7字段package反控后，最终135组已真实通过，当前与前冻结仅新测试一文件差异，其余593包括全部harness/产品/原文件不变。两组证据及追加前完整源拷贝均保留，不把旧freeze冒充最终测试字节。最终当前hash清单 `source-current-final-r2.json` 供root正式freeze。

## Root必须冻结的具体包与CLI

根新候选已给定：`/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/q3ks-mode-only-diagnosis-20261025/candidate-request.json`，SHA `8677a347fc5577c7bf2f399406e11d393e6b330f4e5a099c474e19e78c7a9226`。新daemon owner在同目录 daemon-owner.json，root已独占PID19075/11438；本作者未调用它，review/实际前必须新验证其完整owner，不仅PID。

包严格为九字段：kind=`DIAGNOSTIC_ONLY`、case=`real-deepthink-en`、experiment=`MODE_ONLY_NONTHINKING_Q3KS_0409_EN_V1`、harness_sha256、original、prior_candidate、candidate、frozen_inputs、daemon_owner。所有文件binding严格 `{path:absolute-normal-resolved,sha256,bytes}`。original沿用原官方9B请求；prior_candidate必须原Q3 thinking请求原文件839ba08d…；candidate为上述8677a347…；不能改旧freeze/marker来装配新包。

frozen_inputs应绑定完整当前私有harness/测试、原Q3原冻结与marker/raw/FAIL_STOP、完整原输入/Evidence/政策/预期语义、当前任务及原生renderer/parser、官方与第三方来源区分证据、原本runtime/产品helpers/payload相关有限文件。保留此前hash树，使用本次新daemon owner。新包及hash由root制作并独审APPROVE_DIAGNOSTIC_ONLY后，root最多执行一次：

```sh
PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic/src \
/Users/developer/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic/.venv/bin/python \
/Users/developer/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic/.var/model-diagnostic-q3ks-nonthinking/diagnostic.py \
--package <新包绝对路径> --package-sha256 <新包完整SHA256> \
--output /Users/developer/Documents/yia-worktrees/readiness-q3ks-mode-only-diagnostic/.var/model-diagnostic-q3ks-nonthinking/real-once-20261025 --execute
```

本作者没有执行此命令。实际前必须 fresh RAM>=6464360941B、disk>=10GiB、无loaded runner、完整0409身份等所有原门通过；资源不够即停止，不降低门槛。发生超时/失败后 root 需另证实 native cancellation/idle或保持unknown closed，再正常关闭自有daemon，不默认已停止。成功结构化JSON仅进入独立语义审查：必须原positive substantive判断及正确归因、相似而非完全相同、人类核验；NO_NEW合法但不满足正向门。不得仅凭本诊断发资格或继续样例。

## 关键文件哈希

全部下列相对文件位于本 WT `.var/model-diagnostic-q3ks-nonthinking/`。

| 文件 | SHA256 |
|---|---|
| `diagnostic.py` | `3fd9a63a6abdbd050552d2d980a36a2030f732ec415f967284fa23b85d8aa9fe` |
| `test_diagnostic.py` | `b7f489baa5c8861f586bf61c5b07bb7f6677fea6900caceee5263fda5736033e` |
| `test_mode_guards.py` | `91bc16c3f5c9cc7979595ee6e5b1082f09a573408615507df65e6a47bcc19943` |
| `mode-red.log` | `47d1c6032b2058be620df6e5971886f4e5a053bdc8673b955d8ce6d09e1a4373` |
| `offline-final-r2.log` | `2c16dcac56d6e6cfb2ed4f05f586e345cdc34eb460b660562ec78eb71f4b50d7` |
| `compile-final-r2.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-final-r2.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `inherited-test-lint-final.log` | `27e31658833c0db1fd51fd542b53cad51594faf902a35231b7e69683bc60ccb8` |
| `source-current-final-r2.json` | `dcfdb05747a7af62c7299620571f30d630e5b9adbe56149547ee6b474926ca49` |
| `harness-adaptation.patch` | `4a23fb99d458a3cfce14aa091320068e227656c3845ac321c8545ef18bc794c1` |
| `tests-adaptation.patch` | `429b4d2ae8e481cc525af9ccab2d773d90f72a09dd347acfd2d123a38c6bdde5` |
| `implementation-checks-final-r2.json` | `b841c0d55c9da126e598e62b6b8fbfc66659c2a65096e3fe5d75e7c8f76457b7` |

## Diff、风险与交接

仅私有 QA + 本交接，无产品变更。旧101测试、原failures、原once全部保留；仅新实验预期模式适配，无删断言/改脚本/放宽标准。未新增依赖/模型下载/云调用/owner数据动作。真实模型结果、语义与资格均待root一次实际/独审，不能称Goal完成或允许main采用。当前无实现阻塞，DECISION NEEDED=None。建议root发独审包；作者clean STOP。Reviewer、主控验收、整合栏由对应角色后续填写。
