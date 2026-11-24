# TASK-READINESS-CAPACITY-HOST-FIX 交接报告

## 元数据

- Role: Implementer；Agent: `native_scan_resume`
- Exact base: `d34b56022f76c134bf6fbbed8186b74d8ef933de`
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-capacity-host-fix`
- Branch: `codex/task-readiness-capacity-host-fix`
- Reported: 2026-10-16；Head 随本报告实现 commit，以最终回传 SHA / Git HEAD 为准。
- Reviewer: `local_text_review_resume`，本报告不自签接受。

## 目标与实际范围

修复固定 Ollama 0.40.1 安装的 legacy downgrade anchor 被误当 API/public model digest 的真实主机阻塞。实际仅 local_model_capacity、once harness 的 verify_resources、host/harness unit tests 和本报告。root 最新 task 补充明确允许同根因 harness 修复及真实 manifests-v2 API tag 身份；仅只读 root task，没有 cherry-pick 并行产品树。

无 installed tag/manifest/blob/binary 修改，无 profile/model digest/参数/资格/依赖/Schema/Backup/UI/API/composition/distillation 差异。没有模型 HTTP、load、debug、generation 或真实 permit/qualification；仅在明确授权范围读取固定本地安装字节/进程元数据。

## 根因、来源与复用

root 原真实失败原样保留于 `docs/validation/end-to-end-user-readiness/CAPACITY_REAL_HOST_FAIL_2026_10_16.json`：head25322c6，只读 observe_host 在任何 load 前 `CapacityUnavailable: model manifest differs`。此前178/563工程 PASS 没有证明真实 installed manifest shape，不能把它们追认真实主机 PASS。

安装存在三个不同对象：

| 对象 | 固定内容/关联 |
|---|---|
| legacy `manifests/registry.ollama.ai/library/qwen3.5/9b-q4_K_M` | 1,252 bytes；SHA256 `7dd7bb310c1f18ad132c7fd72e73d4f6cff2e916c596a818701d2a1269037c7f` |
| parent blob | 1,088 bytes；SHA256/public profile digest `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90` |
| API tag `manifests-v2/ollama.com/library/qwen3.5/9b-q4_K_M` | symlink 精确 `../../../../blobs/sha256-56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90` |

legacy wrapper 的 config + 原五 payload layers 完整保持，最后额外追加 parent manifest descriptor。旧代码错误要求 wrapper hash 等于 parent digest，并把七个 wrapper descriptors 与六 payload set 比较。

REFERENCE：仅参考固定官方 [Ollama v0.40.1 manifest.go](https://github.com/ollama/ollama/blob/v0.40.1/manifest/manifest.go)、[paths.go](https://github.com/ollama/ollama/blob/v0.40.1/manifest/paths.go)、[server/images.go](https://github.com/ollama/ollama/blob/v0.40.1/server/images.go)、[model_list.go](https://github.com/ollama/ollama/blob/v0.40.1/server/model_list.go) 和 [MIT LICENSE](https://github.com/ollama/ollama/blob/v0.40.1/LICENSE)。缓存完整官方源码树 identity 为 `cf2a313a298066d572c36812e5ad30a21c0db13b`，本次不足文件由 GitHub connector 按缓存 immutable Git blob SHA 有界取得，逐 Git blob SHA 复验；只存 `/tmp`，不执行或复制第三方实现入产品。

| 官方源码 | Git blob SHA | SHA256 |
|---|---|---|
| manifest/manifest.go | f476743b4f1c9367707d8438fd048df8510a8cf7 | 2b534fa50c385a71d7b6e4d4bb6664feb8e65df209f91af84562424d8858936e |
| manifest/paths.go | cf3bfa2569bf1a3fbc69ef12455566e259515a2d | ce16336074693e19fa8c75147c67b155b9be03542a5dd77500e8be42dba8ff04 |
| server/images.go | 7df4dd179322ce3540c8717663adf89e2c92a961 | 550d1c3f870cacec72f0484f543c53a8f442dd136499c89c30ba37d923d4eda7 |
| server/model_list.go | 9976b4b6688c8a6261f154746cc5abb34fc61d48 | e94d041825d2455933eb77edd700bcededed6a2bc23f4b7eb9f31e99d1b7bb33 |
| LICENSE | 8e3dc978a7ca8c53f56bbedc5b558116140fc02e | 5934ed2ce0d15154bcdb9c85203210abac0da4314af34081e36df4599f90b226 |

依据：WriteLegacyAnchor 追加 manifest blob 防旧 GC 删除；resolveManifestPath 优先 v2，v2 public host 规范为 ollama.com；GetModelForRunner/describeModelFromManifest 使用被选 manifest digest，PsHandler 使用 ManifestDigest。这里只接受精确当前双 manifest 和 tag，不增加任意 wrapper、manifest list、runner 或 fallback 接受。

DIRECT：已批准标准库 json/hashlib/os/pathlib 和原固定 BLOBS/BINARIES、file/host guard。ADAPT：把共同 installed-byte gate 供 observe_host 与 once harness 复用。REJECT/DEFER：改 tag 或 profile digest、下载/升级模型或依赖、删校验/用 API digest bool 代替文件字节、修改 arm/claim/资格来绕过。

## 实现与验收合同

- 双 manifest 各自固定 SHA/精确长度；bounded read(size+1)、严格 UTF-8/重复 JSON key 拒绝；config、五 payload layers 的顺序/全部字段、mediaType/from/size、schemaVersion、runner/format，以及唯一末尾 parent descriptor 完整比较，类型与未知字段也拒绝。
- v2 tag 必须为上述精确相对目标 symlink，解析到当前 parent；lstat/link text 与 target identity 同时纳入 HostObservation 和最终 readiness identity。missing/普通文件/错误 target、即使指向同内容的替换 symlink 都关闭。
- parent blob、wrapper、v2 target、全部六 payload、三个 binary 纳入 before/after snapshot；每个文件打开 fd 的 fstat 必须与该初始 identity 一致，读取/哈希结束再检查 fd/path identity。修复仅前后路径 stat 无法发现“读取 approved 替身后恢复原 inode”的真实离线反证。
- `verify_installed_model_bytes` 不做 process/HTTP/load/generation；observe_host 在其后仍执行原唯一 server/runner、实际 slot 与资源检查。harness verify_resources 复用同一字节 gate，保留 runtime/capacity proof hashes、compiled bound、reviewer/resource/permit 检查和原内存/磁盘预算；不再将错误单 manifest hash 断言称保留。描述、prepare、execute、once/arm/claim 其它函数 AST 均无差异。
- 原资源 host fixture 的11项正/负断言保留，setup 从单个简化 blob 改为六个真实小字节文件、完整 parent/wrapper/v2-link 形状；没有弱化测试、删除/skip 或把 tiny fixture 当真实安装证明。另有 exact 1,088/1,252 原 metadata 样本正例；生产固定 hash 未被其 monkeypatch。
- 原 profile/registry/resource、distillation、Backup、API、composition 全字节不变；CODE_FILES 已含该容量模块，因此 code binding 正常改变，records[] 保持关闭。harness hash 待 root 统一 freeze，本任务不签发 permit。

## 检查证据

| 检查 | 结果/证据 |
|---|---|
| 语法 compileall、Ruff src/tests/scripts | PASS；`.var/host-fix/final-ruff.log` |
| strict mypy src + harness | PASS，106 source files；`.var/host-fix/final-mypy.log` |
| fixed metadata正例 + 初始变异 | 20 PASS；`.var/host-fix/manifest-green.log` |
| fd身份、六payload逐个改字节、reference/parent/原资源反证 | 81 PASS；`.var/host-fix/identity-green.log` |
| 共同harness字节gate初验 | 119 PASS；`.var/host-fix/shared-bytes-green.log` |
| 原独立unknown/Unicode/restart/Settings/once/thread/lsof反证 | 28 PASS / 4.79s；`.var/host-fix/previous-independent-tests.log`。从原 `/tmp/test_capacity_independent_review.py` 仅修 import root 到本 WT 的 ignored 副本，断言不改 |
| 原178及Cloud/8b/39/Backup/ASR/composition关键回归+新增manifest/harness负控 | **488 PASS / 271.40s**，1个既有恶意 ZIP duplicate-path 负控 warning；`.var/host-fix/affected-tests.log`。无失败/skip |
| 只读当前 installed bytes | PASS，2026-10-16T06:52:32Z–06:52:36Z；`.var/host-fix/installed-bytes-readonly.json`。包括双manifest/v2引用/全部payload和3binary，打开fd身份校验；强制 urlopen forbidden，0模型HTTP/load/debug/generation，不调用observe_host/prepare，不宣称资源/slot/资格通过 |
| frozen boundaries / Diff | PASS，`.var/host-fix/frozen-boundaries.json`；`git diff --check` |

复验命令：`PYTHONPATH=src:. .venv/bin/pytest -q` 加 unit 的 `test_capacity_host_manifest.py test_local_model_capacity.py test_local_grounding_harness.py test_local_grounding_qualification.py test_local_grounding_profile.py test_ollama_local_distillation.py test_ollama_analysis_adapter.py test_evidence_translation.py test_openai_distillation_adapter.py test_moonshot_distillation_adapter.py test_backup_restore.py`，integration 的 `test_local_capacity_composition.py test_local_grounding_proof.py test_offline_transcription_jobs.py test_local_intelligence_text.py test_runtime_composition.py`。所有测试用隔离临时路径与 fake model HTTP；未连接模型 HTTP 或正式数据。Ruff/mypy 最终再次 PASS（`.var/host-fix/commit-ruff.log`、`commit-mypy.log`）。

## 原失败、RED 与剩余边界

- root 原真实 `model manifest differs` receipt 未修改，等待独立审查后由 root 真正 observe_host 复验；作者 installed-byte PASS 不能替代完整主机/资源/runner/load-only/语义验收。
- 新真实 metadata 测试 RED：`.var/host-fix/manifest-red.log` 1 FAIL，helper 尚不存在；固定原始 metadata/asserted hashes 后实现，不换样本制造通过。
- TOCTOU RED：`.var/host-fix/identity-red.log` 1 FAIL `DID NOT RAISE CapacityUnavailable`，打开 approved 替身后恢复原 bad inode；随后 fd identity 绑定通过同一断言，没有重复失败方法。
- harness RED：`.var/host-fix/harness-red.log` 1 FAIL `installed runtime or manifest differs`，准确证明旧 wrapper==parent 错误；改为复用完整固定 gate，原 once/资源/permit 条件与负控保留。
- 当前真实仅有 server，现 ps 与 -ww 的完整 args 一致，`.var/host-fix/ps-width-readonly.json`；无 actual runner 截断证据，因此不修改 ps 方法，不加载模型来探测。
- 固定安装升级/迁移、不同v2链接或任一字节/顺序变化继续关闭，需重新审查；应用锁仍不控制外部 Ollama client，不宣称物理 exactly-once。warm case 的资源预算仍原严格标准，不能凭本次 manifest 修复推断资源始终足够。
- 无 frontend/Schema/Backup/状态/owner 数据修改，不重复 frontend/GUI；不跑真实模型 HTTP/load/debug/generation。所有资格 false。

## 实现者结论

建议 IN_REVIEW；提交后 clean STOP，等待独立 Reviewer 与 root 真实 host 复验。不自行 merge/main/push 或变更公共任务状态。

## 独立 Reviewer — APPROVE（2026-10-16）

- Reviewer `local_text_review_resume`，累计 exact base `d34b56022f76c134bf6fbbed8186b74d8ef933de` → author `9be84b882bfe9350657407758e25ba48987c421f`。author 开始/结束产品审查均 clean STOP，本 Reviewer 仅追加本 handoff。已读 task/package、root `a3b0c59` 的实际 v2 tag/harness 同根因补充、累计 diff、原真实 FAIL 及原容量合同；图中新增三个 helper 尚无节点，以该 exact SHA 实际源码为准。
- **APPROVE，P0=0 / P1=0 / P2=0**，仅接受固定安装关联与共同字节校验的工程修复。没有把此前178/563 fixture PASS追认为真实 host PASS，也没有授模型资格。root 原 `CAPACITY_REAL_HOST_FAIL_2026_10_16.json` 原样保留；完整 observe_host/process/slot/resource/prepare/load-only/真实语义仍由 root 后续独立验收。

### 五轴及安全结论

- 正确性：公开/API profile digest 保持 parent `56671c2a…`，不是 wrapper `7dd7bb31…`。固定 wrapper1252B、parent1088B 各校验自己的 SHA与完整严格对象；有序 config+五 payload descriptors 的 mediaType/from/size、runner/format及唯一末尾 parent layer逐项关联，不允许任意 wrapper、额外/重复/重排层或“API说digest对就放行”。六 payload原字节与三个 fixed binaries实际 hash全部仍验证。
- API真正选择的 `manifests-v2/ollama.com/...` 必须为精确 relative symlink目标，lstat/dev/inode/size/mtime/link text 及 target identity同时绑定。普通文件、缺失/错误链接、指向同内容但换 inode 的链接、parent/wrapper/引用在检查中变化均关闭。file_hash与manifest read把打开fd的fstat绑定初始identity，读后再核fd和path；独立补 wrapper/parent 的“读approved替身后恢复bad原inode”负控，两者都在fd gate拒绝；另外直接hash的读中mtime/换path inode也拒绝。
- 架构与范围：harness只有 `verify_resources` 函数 AST改变，复用生产相同 fixed-byte gate；cache限定当前批准模型缓存，runtime/capacity proof hash、compiled容量界、reviewer与resource/permit边界保留。独立将 foreign cache/wrong runtime/不足的declared memory 写入并重算proof hash仍拒绝，foreign/runtime错误在尝试读取新cache之前拒绝。新helper只读文件，无进程/API/load/claim行为。
- 历史/授权：LocalCapacitySession、ApplicationHeavyLease、SharedHeavyGuard、unresolved_local_work、_stopped_after_unknown、validate_runner、wire_bytes 的 AST与base完全相同；原TTL arm/once/claim不可抹/claim后无metadata/unknown/cancel边界不改。state/distillation/profile/qualification reader+empty resource/Backup/local_api/runtime_composition 全字节相同。CODE_FILES本就含容量模块，代码改变正常使旧binding不匹配；harness新hash只能在未来统一freeze登记，本任务没有permit/资格。
- 测试质量/可读性/性能：原capacity test全部test names和参数集合保留，除host fixture函数外其余测试AST相同；host fixture从不真实的简化单manifest升级为完整双manifest+v2+六个小payload，原资源/错误目标保留，positive identity set加强，没有删skip/降低断言。实现是固定安装形状的有界标准库校验，不引入任意格式解析、依赖或第三方执行；manifest bounded read(size+1)，大payload仍stream hash，不将文件hash耗时冒作可用资源/slot承诺。

### 独立真实安装与来源证据

- 本 Reviewer独立执行 `verify_installed_model_bytes(Path.home()/'.ollama/models')`，**PASS_FIXED_INSTALLED_BYTES_ONLY**；精确观察时间 **2026-10-16T07:08:52.590407Z–07:08:56.790662Z**，日志 `/tmp/capacity-host-review-installed-readonly.json`。wrapper/parent/v2 reference、六payload和三个binary共12个路径身份（reference与parent指同物理文件）及symlink身份通过；profile digest原字节不变。执行时将urlopen与subprocess.run替换为拒绝，证明该操作不做HTTP或process准备；load/generation/qualification均0。这是该时间点的安装字节证据，**不是**当前或未来runner/slot/resource/readiness authority。
- 重新阅读缓存官方 WriteLegacyAnchor、resolveManifestPath、GetModelForRunner及describeModelFromManifest，确证legacy GC anchor/v2优先选择/public digest语义。独立复算四份缓存文件Git blob SHA及SHA256，均与上述固定来源值一致：`/tmp/capacity-host-review-official-source-hashes.json`。未联网取材、执行或复制第三方实现。

### 本 Reviewer 实际复验

| 检查 | 独立结果与日志 |
|---|---|
| unit capacity_host_manifest/local_model_capacity/local_grounding_harness/local_grounding_qualification/local_grounding_profile + integration local_capacity_composition/local_grounding_proof | **232 PASS / 83.22s**；`/tmp/capacity-host-review-focused.log`，包含原178及新增manifest/harness负控 |
| unit ollama_local_distillation/openai_distillation_adapter/moonshot_distillation_adapter/backup_restore + integration local_intelligence_text/offline_transcription_jobs/runtime_composition | **233 PASS / 187.22s**；`/tmp/capacity-host-review-regression.log`，仅既有 malicious duplicate ZIP-path warning |
| 原独立Unicode/unknown/resource truth/restart/Settings/once/thread/真实lsof反证，只有import WT路径切到本树 | **28 PASS / 5.25s**；`/tmp/test_capacity_host_previous_independent.py`、`/tmp/capacity-host-review-previous-independent.log`，原断言无改 |
| 新独立wrapper/parent fd替身、direct hash读后fd/path变化、rehash后的harness cache/runtime/memory反证 | **7 PASS / 1.14s**；`/tmp/test_capacity_host_extra_review.py`、`/tmp/capacity-host-review-extra.log` |
| `PYTHONPATH=src:. .venv/bin/mypy src scripts/qualify_local_grounding_v1.py`、Ruff src/tests/scripts、compileall src/harness、累计diff check | **PASS，mypy106**；`/tmp/capacity-host-review-{mypy,ruff}.log`；compile/diff exit0 |
| 独立AST/字节/原测试边界复核 | **PASS**；`/tmp/capacity-host-review-frozen-boundaries.json` |

合计本次独立 **500 PASS**，无skip/deselected，不冒充作者488是本 Reviewer新执行。额度中断后先核实际 Git/日志/进程，已完成232/233/28未重启，只继续尚未完成的来源/边界审查与7项新反证。原作者/root全部FAIL/RED与既有独立反证保持原样；本次没有未处置失败。

### 限制与 clean STOP

- 固定版本、固定受信安装假设保持；任何另一个wrapper/tag/link/parent/payload/runtime继续closed，不推断升级兼容或任意manifest-list支持。应用gate不控制外部Ollama client，不宣称物理exactly-once或对恶意同机进程的密码学进程绑定。
- 0实际模型HTTP/load/debug/generation，0正式/owner/Vault/配置修改；未触root服务，没有frontend diff而不重复Chrome/全前端。当前只读安装证据不替代完整host或真实语义验收；资格全false。
- 本 Reviewer仅handoff提交后clean STOP，等待root调度；无main/merge/push，不并发review或实现tracked Retry。
