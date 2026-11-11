# V3 Selector Baseline

The frozen diagnostic baseline is archived at
`experiments/archive/v2_6_6_baseline/BASELINE.json`; historical reports remain
unchanged. R1/R2 are wrapped as selectors with separate retrieval and selection
metadata. Qwen is an experiment-only selector backend with protocol metadata.

| Selector | Status | Phase-1 behavior |
| --- | --- | --- |
| R1 fuzzy lexical | IMPLEMENTED | Select immutable rank-1 candidate; frozen 0.82 remains outside selection |
| R2 lexical + neighbourhood | IMPLEMENTED | Select by frozen R2 ranking; score remains retrieval evidence |
| Qwen compact | PARTIALLY_SUPPORTED | Valid selection/abstention and fail-closed technical state; no automatic routing/commit |
| Dense selector | RUNTIME_BLOCKER | Interface ready; Windows PyTorch c10.dll/WinError 1114 remains unresolved |

No new fixed voting heuristic, global threshold, routing rule, or semantic
commit policy was added.
