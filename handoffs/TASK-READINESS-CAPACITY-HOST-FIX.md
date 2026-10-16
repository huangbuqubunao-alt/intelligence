# TASK-READINESS-CAPACITY-HOST-FIX 交接报告

## 元数据

- Role: Implementer；Agent: `native_scan_resume`
- Exact base: `d34b56022f76c134bf6fbbed8186b74d8ef933de`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-capacity-host-fix`
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
