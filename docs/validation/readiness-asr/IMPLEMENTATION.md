# READINESS-02 本地声学整改

目标是按已批准的隔离方案解决原 Whisper profile 在长停顿、混合语言和纯静音上的失败。正式 owner 数据、Schema、依赖、SDK、权重、云调用与正式资格配置均未修改。

## 根因与统一方案

原 profile 的 `condition_on_previous_text=True` 与整段粗粒度 segment 时钟在静音段有真实幻觉和时轴问题。原静音基线 3.5 秒会输出 `Thank you.`，并把结束时间置为 29.98 秒；严格 validator 正确拒绝。新实现按输入 PCM 的 20 ms RMS 静音帧划分，每段最多 25 秒，每个原始帧只属于一个窗口，不重叠、不删除。每段独立自动语言检测，关闭 previous-text conditioning，用已安装同一 SDK 的 native cross-attention/DTW word alignment 映射回原始时轴。完整 native output 包括 segments/words 均保存在原始 envelope；不删文字、不去重、不按预期修正，不把生成时间裁剪到窗口制造通过。

统一前置 guard 使用固定 −45 dBFS 活动门限与谱平坦度 ≥ 0.4 且活动帧比例 ≥ 95% 判定均匀噪声。这是信号质量拒绝边界，不是语义“无人声”真值。NO_SIGNAL/NOISE_ONLY 结果没有 decoder invocation，仍由普通产品任务作为失败处理，不能成为成功的空字幕。

原有限值、正时长、单调不重叠、毫秒字幕和源文件范围校验保持；模型任一非有限 metadata 或非法窗口时间使整个任务失败，NaN 不修复为成功。资格 tuple 绑定新 helper、worker、原 executor/validator/source-authority/scorer、固定解码与分段政策、SDK/权重/预处理工具以及全部 14 正向和 3 负控制。原 8 项或缺失负控制都无法通过。

## 冻结与失败保留

run01 全 17 项有 1 个长停顿覆盖失败；run02 有 6 个窗口结束时间失败。两轮全部证据保留，不覆盖、不删样例。统一 run03 的 17 项通过原门槛；见 `run03/RESULTS.json`，这仅是 research 结果，不能独立使产品获得资格。

实际产品验收在 `product-freeze.json` 的所有 implementation 和输入 SHA 冻结后，使用 `qualify_readiness_asr_product.py` 与已有 engineering executor seam 经真实 LocalContentProvider、LocalTranscriptionJobs、offline worker 和 repository 完成。只有真实 trusted subtitle/Summary/Evidence、原评分与覆盖门槛、负控制没有 authority 全部满足，才在新隔离 `.local-transcription` 根写入已有机器 HMAC receipt。普通用户配置不能写 PASSED。

独立进程 `verify_readiness_asr_product.py` 使用普通 factory 读取 receipt，不使用 engineering admission；逐条核对精确字幕、Evidence 时间和文本以及摘要，移除隔离模型路径后再次检查历史 authority。随后真实创建 DATA 备份并恢复到另一个新根，检查一致性、SQLite integrity 和资格/模型不随恢复继承。

## 复用与限制

DIRECT：已安装 mlx-whisper 0.4.3（MIT）、MLX 0.32.0、原固定 large-v3-turbo revision a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb / weights SHA951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6；原项目 ffmpeg、严格 validator/scorer、机器资格封印、任务和 Backup/Restore。

ADAPT：项目专用 PCM 帧划分、前置信号拒绝与整数源时轴映射；没有复制第三方实现或修改 SDK。来源与模型许可证记录沿用 `docs/REUSE_REGISTER.md` / 既有 model-origin，不扩展模型分发范围。

14 正向为既有 macOS 合成语音冻结材料，包括独立、中长、混合、弱音与轻噪声，不能据此声称自然录音总体准确率。低于固定信号门限或大部分呈噪声谱的真实语音可能被误拒绝；连续语音遇 25 秒硬窗口可能影响边缘词，必须承受相同门槛。仅冻结矩阵的真实通过可以证明本轮资格；正式激活、真实 GUI 端到端和主分支采用由 root 独立验收决定。

## 独立审查整改

首轮review发现harness在报告FAILED（如缺Summary/Evidence）时可能先写PASSEDreceipt。整改将全部真实产品authority条件绑定到qualification completed，并在seal之前核对evaluate与reportverdict；不一致直接拒绝、无receipt写入。新增5个CPU回归，126 focused全部通过。原实测17项完整evidence经新predicate重放仍canonical逐字节一致，原HMACreceipt认证不变；见REVIEW_P1_REPLAY.json，无新推理/历史receipt重写。原product-freeze保留，新harness独立冻结product-freeze-review-p1.json。run02摘要已按原JSON纠正为11/17、6失败。完整后端4033pass+1既有asset前提skip及新增测试覆盖见CHECKS.json。
