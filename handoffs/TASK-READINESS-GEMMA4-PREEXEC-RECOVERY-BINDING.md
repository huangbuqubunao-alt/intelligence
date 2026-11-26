# TASK-READINESS-GEMMA4-PREEXEC-RECOVERY-BINDING

**APPROVE_BOUND_MANUAL_RECOVERY_COMMAND_ONLY.** No unresolved P0/P1/P2 finding. This approves the exact planned manual command and current cold-owner/package/launch bindings under the already reviewed runtime guards. It does not prove resource availability, model quality, qualification or adoption.

Reviewer `/root/preexec_recovery_review`, 2026-10-26; continuing WT `/Users/developer/Documents/yia-worktrees/readiness-gemma4-preexec-recovery-review`, branch `codex/task-readiness-gemma4-preexec-recovery-review`, prior source review `f73183c1ce9f9e9ea3285247c8c29667e0acdab3`. Reviewed unchanged author `8e864d91bbba0a9c5800ab1792438488f374f39c`; Root stage2 task/prompt at `7e9d09b`. Read both appended stage2 instructions and immutable Root cold-binding receipt. Only this new handoff and own ignored `binding/**` evidence were written. No source/C/G/Root/product/configuration/credentials/qualification changes, HTTP, runtime/Terminal/model startup, signals, app closure or subagents.

Y = `/Users/developer/Documents/yia-worktrees/readiness-gemma4-preexec-recovery/.var/gemma4-preexec-recovery`; C = `/Users/developer/Documents/yia-worktrees/readiness-gemma4-e4b-ready/.var/gemma4-e4b-ready`; G = `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/gemma4-e4b-20261025`.

## Exact independent bindings

| Artifact | SHA-256 / result |
|---|---|
| G/recovery-cold-binding.json | `727aa3910415bbf15533a002d70c39bb9dae9c1a53e52ba6c7b90de30612a3f8` |
| Y/checks/artifact-manifest.json | `e7ae5a9d635a7ecc7c857df06a5de02dac3d778722e3ff94d99887a1ac384f54`; all24 entries unchanged |
| C/checks/artifact-manifest.json | `b1dd89a7b6f070ac8087f8cc24e6221ddd82c4d944a1726a9af8987403558a57`; all53 entries unchanged |
| C/package-template.json | `a03aacbd18b586141fd19c19abd375b5286d41c9cb0bf2e345f98f0c8cbdc6a7`;9 fields/1888 bindings |
| Y/daemon-owner.json | `c71373bb9a443db6333cf5cd400399149e80f1d1c9b586851eae6b950f861513`;342B |
| C/recovery-reviewed-package-20261026.json | `7cc9a6ca04a550943787e6b23eb97039d3d7cee378c4b56342828e2e2263e6ee`;460156B/9 fields |
| Y/reviewed-launch.json | `5bb0561e70b0b530642ce664221f37c1d5d60ea829285011ed591fd18eb6d70e`;2132B/11 fields |
| G/planned-Start-Gemma4-Recovery.command.txt | `2505765b16569cff3e68c311f7c3e7d9ec63a97da2896ac1d2bfe95a3216be74`;832B/nonexecutable |
| Y/Setup-Recovery-Metadata.command | `145bd0923c3061855819efae06abe55eb9ed22db838c7541da4872324cf8f134`;670B/exact one source-SHA substitution |

The derived packet equals the original a03 value with **only daemon_owner** replaced by the exact Y owner binding. All1888 frozen inputs and all source/candidate/proofs rehash correctly through unchanged original `h.package` and `RealBackend.validate`; packet size differs only because of pretty serialization and new owner path. The11-field launch equals the already reviewed bdd30d14 template with **only owner/package** replaced. Unchanged launcher/helper/plan hashes remain6acda637…996d0f/5ebbd505…8251e/64d4b424…b709, and unchanged `checked_launch` passes the current fixed source chain.

The planned command is byte-for-byte the reviewed Start template with exactly two single replacements: launcher SHA and concrete reviewed-launch SHA. Fixed absolute interpreter/PYTHONPATH/source/argument bindings remain; `zsh -n` passes. Y/Start-Gemma4-Recovery.command was absent at final check; it has not been opened and there is no controller/countdown running. Root may only materialize identical reviewed832 bytes after this approval.

## Actual cold ownership and preserved execution state

Independently observed owner is **67013 Mon Oct 26 13:59:32 2026**, exact pinned runtime `ollama serve`, PPID1. Read-only original daemon/mapping guards verify actual ARM64, launch **2026-10-26 13:59:32.378 +0800**, exact main executable path/device/inode/start identity and sole loopback11438 listener. No fixed llama-server runner exists. Owner/no-runner state was checked again after all binding/protection reads. Complete fixed artifacts independently hash-verified: five payloads5493450969B, distinct canonical manifest/reference, three pinned runtime binaries; full main5493439296B SHA370c2879…d39c and actual bounded GGUF header/proofs through unchanged `artifact_ready.validate`. No tensor decoding or model load.

Captured metadata helper chain is67003→zsh66967→login66966→Terminal66963→launchd1, exact pid/ppid links and no Codex/ChatGPT ancestor. Independent current Terminal66963 executable/PPID1 matches. The completed helper is historical captured evidence, not claimed live. Reviewed metadata source and daemon-process record fix private G/models,127.0.0.1:11438/no-cloud; same fixed-store tag/manifest/payload metadata corroborates that binding. No unrelated process environment or credentials were read.

All ten Root-bound metadata/ancestry/setup/owner/launch files match their recorded hashes. Version0.40.9; ps exactly models[]; tags contain only the fixed Gemma alias/text manifest; show passes original strict small-Gemma/parser/architecture/context/BOS/auto-add/no-remote/Q4_K_M validator. Root's first fresh GETps14:01:08 has exact same owner before/after and no runner. At reviewer's request Root supplied a second new file, **G/recovery-fresh-cold-ps-2.json**, SHA **`0e258c1a19fd3c2b5a41c7794f959d7703d15cf9aff56e719e424ccc2cf6d041`**, completed **2026-10-26T14:03:41.869799+08:00**, HTTP200/models[], same complete67013 owner before/after, no runner,0load/0generation/qualificationfalse. Reviewer independently verified hash, contents and response SHA; no reviewer HTTP. Current Y daemon log has exactly six requests, all metadata: version/ps/tags/show/ps/ps, no load/chat/generate.

Original zero-call history still passes:354 app-open observations, immutable WAIT_TIMEOUT/OWNER_STOPPED/NO_RUNNER and old metadata-only log. Old59941/60673 remain absent. All2518 protected SHA values match stage1, and585 scoped product files remain identical to a2076db. Original **C/generation-start.json**, **C/real-once-gemma4-e4b-20261026**, old child stdout/stderr and new **Y/recovery-launch.json/manual-run** remain absent, including dangling-symlink checks. No original once/output or failure was reset.

## Reproduction, findings and exact limit

Own `.var/gemma4-preexec-recovery-review/binding/verify_binding.py` ran with fixed Root `.venv/bin/python -B`, bytecode disabled and exact author `src` PYTHONPATH; exit0, all assertions passed. Only read-only file/process/mapping/port operations occurred. `binding-summary.json` and `verify.log` SHA **`cf8309532f7652a3d88be6e012178d92eb16f49fb66aca8ccc20cf027b5f86c7`**; script SHA `c630ad6389fbb7b6c289a8dfab62853c93c41b9ae42fc0d02b3e922f7a70a47f`; supplemental fresh-ps/final-absence evidence SHA `36ddbc0ebeff0b3ac74439f913fbebdca181704c6c82f43205bf1485c9997761`. Local evidence index binds them. No verification failure. Sources unchanged, so stage1 independent41/157 remain prior evidence; no unnecessary suite rerun or newly claimed full6003/1026/model test.

Root may copy the exact reviewed832-byte plan to **Y/Start-Gemma4-Recovery.command**, rehash it and give the user the normal-quit-then-click flow. **Do not open it in advance.** User manually quits Codex/ChatGPT while keeping Terminal/Jimmm, then clicks; first app/resource refusal must still stop before launch/preload/cleanup without touching cold owner. This approval does not claim app absence, available RAM, actual native N or peak usage. Preserve freshRAM7640934617B/disk10GiB, original source/artifact/owner/lease/once/native non-speculative/draft0/one-BOS/freshN/capacity/count/300-second/public-only guards.

Exactly one original English diagnostic may run after user click and all fresh gates, using the **original GLOBAL/CHILD**, then STOP on every outcome with qualification=false. Preserve raw opaquely/public final only; Root must independently review actual semantics/grounding/cleanup afterward. No retry/later/negative case, paid cloud, model qualification, formal owner change or main adoption. Full ordinary-user Intelligence/Evidence/save/topic/trust/receipts/restart/backup/restore Goal remains unproven. Reviewer returns this handoff commit and clean STOP; Root owns delivery, status and execution.
