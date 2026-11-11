# V2.6.6 Diagnostic — V3 Evidence Gate

| Hypothesis | Status |
| --- | --- |
| H1 Margin identifies ambiguity | SUPPORTED |
| H2 Qwen adds ambiguous-set selection value | PARTIALLY_SUPPORTED |
| H3 Benefit survives candidate order changes | SUPPORTED |
| H4 Benefit survives opaque IDs | SUPPORTED |
| H5 Structural context adds incremental value | PARTIALLY_SUPPORTED |
| H6 Selection is representation-robust | PARTIALLY_SUPPORTED |
| H7 Reliability supports proposal-only research | PARTIALLY_SUPPORTED |
| H8 Selective semantic reranking merits V3 research | PARTIALLY_SUPPORTED |
| H9 Qwen supports automatic semantic commitment | NOT_SUPPORTED |

## Evidence boundary

The observed limitation is not a macro-architecture failure. It is primarily a
semantic-selection and commitment-confidence evidence gap: deterministic R1/R2
are weak on difficult retrieved sets, while Qwen retains value under order and
opaque-ID controls but is prompt-sensitive and technically imperfect. Existing
review/validation/commit safeguards therefore remain necessary.

External validity remains limited by Anatomy-only evaluation, possible
pretraining familiarity, no real dense embedding baseline (`RUNTIME_BLOCKER`),
no second suitable ontology pair (`DATA_MISSING`), and limited relation diversity.

No V3 architecture, routing policy, threshold, or automatic commitment was
implemented.
