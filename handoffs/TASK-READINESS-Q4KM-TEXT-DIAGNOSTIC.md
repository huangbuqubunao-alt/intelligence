# TASK-READINESS-Q4KM-TEXT-DIAGNOSTIC 交接

QA实现基线 a798d4dbc54ac7e38c0c65507a07e209c50689ff；WT readiness-q4km-text-diagnostic。原作者 /root/model_setup_catalog_bound 在完成私有最小适配和141测试后因额度停止。root续作仅完成compile、Ruff、605输入hash核对及本交接，未再修改实现或测试。作者与root均没有HTTP、加载、生成或产品代码改动。建议IN_REVIEW，实际执行仍须独立具体包批准。

DIRECT复用最终IQ2私人141测试/harness4b82152a…，原135guards和新增6反控均保留，仅namespace/experiment/tag/store/reference/实际Q4四payload、794B manifest和177B config适配。完整patch保留于私人目录；未触旧IQ2/Q3输入、raw或marker。标准库与已装pytest/Ruff直接复用，无依赖动作。官方既有权重与license Apache2；固定Ollama/llama.cpp0409源码/二进制/许可证沿用已有冻结证据。

实际元数据来自root/.var/end-to-end-user-readiness/qwen35-9b-text-q4km-20261025/root-artifact-verification.json：model intelligence-qwen35-9b-text-q4km:02d45dc1，manifest cfc17e6f6530e659b95f467e069dbca236b75fdde37dec861b51e13fd15f2f4f/794B；config69de2371…/177B、Q4_K_M、9.0B/qwen35/0409；textweight02d45dc1…/5629109120B。四payload总5629120653B + 原2GiB =7776604301B，disk10GiB与全部fresh/ARM64/mainmap/owner/runner/nativefalse/newN/slot/lease/once/deadline保护保持。实际native N仍未知，不复用722。

复用已安装官方fullmanifest56671c2…的原textlayer，完整SHA/APFS独立clone、原blob不变，无下载。旧同9B0401/不同4096/914token请求语义FAIL保留；独立历史核对及root历史原始proof归档，不能因去掉921MB图像projector而重置质量。新纯文本包按其实际四payload求资源门，原完整模型门不改。隐藏defaults不导入；原已固定OPTIONS逐字保持。

新独立EXPERIMENT Q4KM_TEXT_NONTHINKING_0409_EN_V1，globalmarker own .var/model-diagnostic-q4km-text/generation-start.json。严格9字段包；prior_candidate=Q3false8677a347…，candidate5ecc84f9…仅换tag；original228c…真官方9B请求和18cue/2Evidence/语义要求不变。唯一首次实际最多空load1次+generation1次/300s，任何结果后停止独立语义审查，不授后续case/profile/资格。正向JSON、NO_NEW、速度或内存通过不能代替资格。

检查实际结果：原作者完整141 PASS/0.98s；root compile4文件PASS、harness+两个新测试Ruff PASS；605文件输入digest前后逐项相等。root将after-map按键排序，两个JSON快照文件hash不同，内容映射精确相等；不声称快照字节相同，详细note保留。继承compact test_diagnostic.py的106 E701/E702沿用，不称全私有QA lint绿；产品Ruff未改。Git无业务diff，旧实验文件保留。

| 文件 | SHA256 | bytes |
|---|---|---|
| diagnostic.py | d510aef83346bf1706f69a14fc7e9e10148d2e0614591f6b333c24a28f91e1ef | 26018 |
| test_diagnostic.py | 61d3e84f78f73b193d4622b71531918595c266220d505319257066e691c0fa56 | 28579 |
| test_mode_guards.py | 2be10563a0b2c5943da89b36b0b2aeac784499e21ed3c467f9c25ee33fca9db3 | 5595 |
| test_quant_guards.py | 5a16b6414539847b674ae9a13be0f1c26b4acb6da1efa4ea303be137f8f294a9 | 2101 |
| offline-final.log | 1ffc327853aaf414595f5e56868ab8445875ba79fe150d12a39e9c6dcda9e180 | 180 |
| compile-final.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 |
| ruff-final.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 | 19 |
| source-before-final.json | 9672968fad9f1aae4c11660b9c8688005537452f75ec13459a0bedab611e2dc3 | 110824 |
| source-after-final.json | 4168bca68905974a405f4b7a6d9f81f4015c59bb25f2971609b3f0fbf120bee2 | 110824 |
| actual-artifact-source-bindings.json | eae7e9dc1facb13fbe1f91bf9c5c08f3590aa23f1bc8de4914646630e8d05155 | 1780 |

私人目录 .var/model-diagnostic-q4km-text/。root下一步固定原来源/语义/历史失败/真实四payload/新冷owner/实现与tests的具体package，独立复核后才实际调用。CLI需显式PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-q4km-text-diagnostic/src，使用root既有 .venv/bin/python 执行本WT diagnostic.py --package <独审固定文件> --package-sha256 <完整SHA> --output <本WT私人目录下全新real-once> --execute；不得执行占位符或旧包。正式配置/用户数据/main/Schema/产品catalog/资格均未变，0付费云调用。剩余阻塞是具体包独审及真实模型质量未知，root继续负责实际验证；本交接不声称Goal完成。
