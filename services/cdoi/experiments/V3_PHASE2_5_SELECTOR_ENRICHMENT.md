# V3 Phase 2.5 Selector Enrichment

`R2_ENRICHED_DIAGNOSTIC` reranks exact persisted V2.6 R1 Top-20 CandidateSets. Candidate IDs, membership, order, source population, and reference protocol remain fixed; only profile evidence changes. It does not modify R1/R2 or emit mappings. The 0.82 count is observational only.

| Condition | Accuracy | Non-trivial accuracy | Rank-1 preserved | Rank 2-5 recovery | Rank 6-10 recovery | <0.82 diagnostic | Low-margin accuracy | Candidate sets frozen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT | 0.8016 | 0.4771 | 1186 | 13 | 1 | 780 | 0.2599 | yes |
| P1_SYNONYMS | 0.7976 | 0.4665 | 1179 | 12 | 2 | 780 | 0.2511 | yes |
| P2_DEFINITIONS | 0.8016 | 0.4771 | 1186 | 13 | 1 | 780 | 0.2599 | yes |
| P3_SYNONYMS_DEFINITIONS | 0.7976 | 0.4665 | 1179 | 12 | 2 | 780 | 0.2511 | yes |
| P4_FULL_SOURCE_FAITHFUL | 0.7976 | 0.4665 | 1179 | 12 | 2 | 780 | 0.2511 | yes |

## Selector availability

- R1/R2 wrappers: frozen and unchanged; V2.6.6 parity remains exact.
- Qwen enriched-profile comparison: `QWEN_LIVE_EVAL_UNAVAILABLE`; no historical Qwen metric was substituted.
- Dense enriched-profile comparison: `RUNTIME_BLOCKER`; no embedding result was fabricated.
