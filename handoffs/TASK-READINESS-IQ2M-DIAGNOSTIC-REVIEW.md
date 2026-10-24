# IQ2_M 独立诊断前审查

Reviewer `/root/long_completion_review_r1`；专用review WT `/Users/hua/Documents/yia-worktrees/readiness-model-diagnostic`，起点 `f72dc7fbe643053c91b901952881bd8668cc4d59`。作者独立WT `/Users/hua/Documents/yia-worktrees/readiness-iq2m-diagnostic` clean STOP `9ee9cd13aaf9a76568fc276092bc46f212fa04c0`，基线 `d61752bec647a93e7d255a51c639bbd1d85894a3`。阅读当前任务/交接/具体包，独立生成并完整审查相对已审Q3非思考harness及两测试的实际差异、新quant测试和实际导入元数据。复用此前f72dc7f完整保护审查，不重启三方全审。

**APPROVE_DIAGNOSTIC_ONLY**：只覆盖固定实验 `IQ2M_NONTHINKING_0409_EN_V1`，不授模型资格、receipt、后续样例或发布权限。

## 固定候选与契约

作者harness `.var/model-diagnostic-iq2m/diagnostic.py` SHA **`4b82152a2db2a53ac1c9c4c639193241535321be8a1f58c0206db25256403bec`**，25964B。具体包 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/qwen35-9b-udiq2m-20261025/diagnostic-freeze-iq2m-v1.json` SHA **`c54e8c2881ffb7294cfb1c727f4d2c8ff5d3476dd9c383c6d21b84748dc72231`**。严格9字段及experiment/case/原始与prior/candidate链均保留。独立验证980 frozen_inputs、984引用、**981唯一绑定文件**全部路径/大小/hash和末端identity；原Q3 v2的335文件全部原样包含，故旧owner/旧153、失败raw、marker与包未丢失或改写。

新candidate SHA `5f268ef04fe7930ef3e4e72f6f55f4b079c9607cca23abd93cef08ab7e50c387` 对准备过但未生成的Q3false `8677a347...` 仅替换top-level model；对原始官方9B请求 `228c663e...` 仅model+thinkfalse。完整18cue/2Evidence/关注/messages/schema、全部采样、8192输出/16384context/batch512/seed20261013/300秒不变。prior现在严格要求原Q3false，跨model/模式/旧experiment/旧7字段包均拒绝。

量化身份来自实际metadata：manifest **`2bd925165e77bf81c231c7f777503d86900f37ba8c42ae8f2082a699a8327f98`**/782B；config **`ff6fbef0d964942903aef3247b6a0e933e1505c8e348f40ccd6b66dafbc4b1c3`**/176B、`IQ2_M`/qwen35/9.0B/renderer-parser qwen3.5/requires0409；actual-show general.file_type29、parameter_count8953803264与quantization_level IQ2_M一致。实际新weight完整SHA **`a31b6b4c603ddd66b5496ee065c9dd13b2b6de77dce9e5d59609aef8d39868e7`**/3649365216B、四payload/相对tag symlink及lstat保护均独立通过。模板/license沿用各自固定hash，无projector。新资源下界按实际四payload3649376748B+2GiB=**5796860396B**计算，margin不变，旧Q3资源门和零生成拒绝记录保留。

原生false renderer/common-prefix未改，完整false文本SHA **`489a6962940e241fbf41181ba356c1966e15890669eaae87ed69b068419f9fa6`** 与prior相同。实际tokenize必须由新model的同一runner执行full add_special=true/parse_special=true，真实单slot idle/nonspeculative/16384及N+8192+2<=C均保留。**本审查没有新N；不能拿720/722代替。** 原完整owner/ARM64/main映射、版本/三binary、文件/reference、租约/TTL、独占新marker、空preload、response模式/usage/原始body先保存、绝对300秒和无重试保护均未弱化；未发现可复现阻断。

## 独立检查

语法先行：四QA文件compile PASS，仅写own review pyc。完整原135+新6：**141 PASS /0 FAIL /0 SKIP，0.67s**。harness、test_mode_guards、test_quant_guards Ruff PASS。继承compact test_diagnostic的106 E701/E702既有格式问题仍披露，未重复lint或冒称该文件全绿。原断言未删除或弱化，变动仅声明的artifact/scope/prior预期及成对旧PSfixture；原所有guard与新增IQ2反控运行通过。**603**源/QA/原实验/metadata冻结在独立检查后仍逐字全等；作者tracked diff仅自己handoff且WT clean；未碰root完整6003/1026运行证据。

实际只读daemon()/arm64_process()证明PID25107、完整原始owner、ARM64 launch `2026-10-25 06:22:44.603 +0800`、固定main映射与11438归属一致，runner空/新marker无。三个0409binary、四payload完整hash通过。一次资源快照RAM **6210568192B >=5796860396B**，disk185768243200B；这是当时快照，root实际脚本必须重新通过fresh资源/身份/slot/所有门，不可豁免。实际已捕获metadata的/api/ps空；reviewer自己**0 HTTP/0 load/0 generation**，未运行任何`--execute`、关闭进程或改作者文件。

## 后续边界与证据

Root仅可在所有fresh门通过后最多一次empty preload+一次原英文实际generation，任何实际结果后STOP。超时/失败保留raw并证明native cancellation/idle，否则unknown继续closed；不自动重试、修补输出、换样例或降低原正向/grounding语义门。IQ2更强量化的质量和实际兼容性尚未证明；结构化JSON只是待独立语义审查，无qualification/receipt/后续例或main权限。

自身ignored证据 `/Users/hua/Documents/yia-worktrees/readiness-model-diagnostic/.var/iq2m-diagnostic-review/`：actual差异、offline/compile/Ruff、package-artifact-host-resource、source-and-metadata-check及review-evidence。后者SHA **`d39c5d620e373ca4e047626ea0dc671da5a048b69f1acb8f9962a560344323d5`**。只新增本review handoff，未改被旧freeze绑定的文件。**Scoped commit 后 clean STOP。**
