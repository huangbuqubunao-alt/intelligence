# V1 Implementation Impact Matrix

| Domain / feature | Current implementation | Disposition | Owner | Risk |
| --- | --- | --- | --- | --- |
| Video, artifacts, jobs, provider calls | Existing SQLite authority | REUSE; reference only | 018–024 | high trust coupling |
| Evidence / Intelligence / revisions / claim classification / edges / deletion impact | absent | ADD | 018/018A/019 | high |
| Trusted scoring read | `AuthoritativeScoringReader` | REUSE; DO NOT reinterpret | 019/026 | critical |
| Feedback / preference | absent; global model preference is unrelated | ADD | 020 | high intent boundary |
| Source drawer/config | SourceSubscription + m005 policy | MODIFY/REUSE | 021/026 | migration compatibility |
| Filtering disposition / manual override | absent | ADD | 021 | safety semantics |
| Personalized distillation | current scoring/summary runtime only | ADAPT behind new application service | 022 | evidence/cost |
| Resource ledger | provider-call usage exists but no product ledger | ADD, reference provider calls | 022 | cost integrity |
| Topic/timeline | absent | ADD | 023 | revision coupling |
| Scheduler/automation runs | bounded m005 service tick | REUSE/MODIFY | 024 | duplicate effects |
| Weekly generic report | reports + frozen Weekly V2 unavailable | REUSE/ADD V1 projection; preserve V2 | 025 | dual authority |
| Dashboard/Videos/Weekly/Automation/Activity/Settings | existing FCC presentation routes | REUSE/RELOCATE/REFRAME | 026 | IA and authority |
| Intelligence/Topics/Investigations IA | absent | ADD Intelligence/Topics; RESERVE Investigations | 026 | V2 leakage |
| Deep Analysis / Investigation / Signals / Ask / Daily | blocked or absent | RESERVE only | all | critical product scope |
| Test/demo fixtures | PO demo + unit/integration/E2E basis | REUSE/ADD synthetic V1 fixtures | 027 | false acceptance |

No V1 capability is deleted or retired merely because the IA changes: old Dashboard becomes intelligence entry, Videos/raw transcript become contextual drill-down, Weekly generic output remains clearly distinct, Automation/Activity move into operational/supporting projections, and Settings retains model/credential-safe posture.
