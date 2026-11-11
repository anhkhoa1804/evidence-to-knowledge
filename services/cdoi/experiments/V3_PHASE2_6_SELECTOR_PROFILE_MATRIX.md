# V3 Phase 2.6 Selector x Profile Matrix

All deterministic entries use the same 1,497 persisted R1 Top-20 CandidateSets. The frozen R1/R2 wrappers remain exact-parity baselines and intentionally do not consume experimental evidence. `R2 enriched diagnostic` is the versioned Phase-2.6 source-faithful analysis only, not production R2.

| Selector | P0 current | P1 resolved synonyms | P2 resolved definitions | P3 resolved both | P4 full faithful |
| --- | --- | --- | --- | --- | --- |
| R1 frozen wrapper (does not consume enrichment) | 0.7949 / 1497 | 0.7949 / 1497 | 0.7949 / 1497 | 0.7949 / 1497 | 0.7949 / 1497 |
| R2 frozen wrapper (does not consume enrichment) | 0.8016 / 1497 | 0.8016 / 1497 | 0.8016 / 1497 | 0.8016 / 1497 | 0.8016 / 1497 |
| R2 enriched diagnostic | 0.8016 / 1497 | 0.8310 / 1497 | 0.8016 / 1497 | 0.8310 / 1497 | 0.8310 / 1497 |
| Dense | RUNTIME_BLOCKER | RUNTIME_BLOCKER | RUNTIME_BLOCKER | RUNTIME_BLOCKER | RUNTIME_BLOCKER |
| Qwen | QWEN_LIVE_EVAL_UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE |

## Corrected full-corpus retrieval (1,497 reference cases)

| Condition | R@1 | R@5 | R@10 | R@20 | MRR | Non-trivial R@1 | Rank improved | Rank worsened | Entered 5 | Entered 10 | Entered 20 | Left 20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT_V1 | 0.8016 | 0.8965 | 0.9178 | 0.9292 | 0.8433 | 0.4771 | 0 | 0 | 0 | 0 | 0 | 0 |
| P1_SYNONYMS_RESOLVED_V2 | 0.8550 | 0.9359 | 0.9506 | 0.9606 | 0.8914 | 0.6232 | 122 | 95 | 67 | 58 | 52 | 5 |
| P2_DEFINITIONS_RESOLVED_V2 | 0.8016 | 0.8965 | 0.9178 | 0.9292 | 0.8433 | 0.4771 | 0 | 1 | 0 | 0 | 0 | 0 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | 0.8550 | 0.9359 | 0.9506 | 0.9606 | 0.8914 | 0.6232 | 122 | 95 | 67 | 58 | 52 | 5 |
| P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2 | 0.8550 | 0.9359 | 0.9506 | 0.9606 | 0.8914 | 0.6232 | 122 | 95 | 67 | 58 | 52 | 5 |

Definition asymmetry: source definition available = 0/1497; target definition available = 280/1497; both = 0; one-sided = 280.

Easy-control regression count (P0 correct to P1 wrong at original margin >=0.20): 0.

Dense has no valid population because initialization is blocked. Qwen has no configured live evaluation; historical Qwen metrics were not substituted. The frozen QSEM V1 payload exposes aliases but not `SemanticEvidence.definition`; therefore a Qwen definition-ablation cannot be run without changing the frozen prompt protocol, which Phase 2.6 forbids.
