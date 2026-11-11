# V3 Research Gate

| Area | Status | Evidence boundary |
| --- | --- | --- |
| Macro architecture | SUPPORTED | V3 does not alter it |
| Semantic-decision separation | IMPLEMENTED | Candidate, ambiguity, selection, commitment, policy contracts |
| Retrieval abstraction | IMPLEMENTED | Immutable CandidateSet |
| Selector abstraction | IMPLEMENTED | R1/R2/Qwen adapters |
| Ambiguity evidence | IMPLEMENTED | Margin/spread are evidence, not routing |
| Dense baseline | RUNTIME_BLOCKER | Windows PyTorch c10.dll / WinError 1114 |
| Qwen selector | PARTIALLY_SUPPORTED | Diagnostic value with prompt/reliability limits |
| Commitment-confidence protocol | IMPLEMENTED | Uncalibrated fail-closed scaffold only |
| Second-domain validity | DATA_MISSING | No suitable bundled pair |
| Relation diversity | NOT_SUPPORTED | Anatomy evidence is primarily equivalence |
| Application safety boundary | SUPPORTED | Existing review/version/canonical staging gates unchanged |

Before selective routing: measure dense baseline and obtain independent
second-domain evidence. Before commitment calibration: define an independent
calibration split and evaluate risk/coverage. Before production use: demonstrate
reliability, relation diversity, application-level validity, and governance
controls. Better selector accuracy alone is not authorization to auto-commit.
