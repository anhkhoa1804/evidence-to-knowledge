# V3 Phase 2.5 Research Gate

| Question | Status | Evidence |
| --- | --- | --- |
| synonym extraction value | NOT_SUPPORTED | P1-P0 enriched-diagnostic full-corpus R@1 = -0.0180 |
| definition extraction value | NOT_SUPPORTED | P2-P0 enriched-diagnostic full-corpus R@1 = +0.0000; Mouse has no raw definitions |
| structural evidence value | SUPPORTED | Phase-2 raw audit found 100% recognized structural extraction recall; P4 adds none over P3 |
| preprocessing limitation contribution | PARTIALLY_SUPPORTED | Raw aliases/definitions are source-provided but absent from P0; this deterministic representation does not show a positive retrieval gain |
| deterministic enriched selector | NOT_SUPPORTED | P3-P0 fixed-Top-20 accuracy = -0.0040; R1/R2 remain unchanged |
| Qwen enriched selector | UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE |
| dense enriched selector | RUNTIME_BLOCKER | Existing Windows PyTorch blocker remains |
| semantic-profile readiness | PARTIALLY_SUPPORTED | Source-faithful profiles are reproducible; Anatomy does not justify production adoption |

No semantic decision policy change.
No production profile change.
No routing change.
No commitment calibration.

Phase 3 is not started. Independent calibration data, an external second ontology pair, and a working dense runtime remain prerequisites for their respective future research decisions.
