# External Results

| Experiment | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Bridge P | Review Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EXT_OAEI_B6 | oaei | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| EXT_OAEI_ANATOMY_B0 | oaei | 7580 | N/A | N/A | 0.009894459102902375 | N/A | N/A | 0.009894459102902375 |
| EXT_OAEI_ANATOMY_B2 | oaei | 7580 | N/A | N/A | 0.009894459102902375 | N/A | N/A | 0.009894459102902375 |
| EXT_OAEI_ANATOMY_B3 | oaei | 7580 | N/A | N/A | 0.8680738786279684 | N/A | N/A | 0.8680738786279684 |
| EXT_OAEI_ANATOMY_B6 | oaei | 7580 | N/A | N/A | 0.06992084432717678 | N/A | N/A | 0.06992084432717678 |
| OET_B0 | concept_placement | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| RCA_FULL_CDOI | rcaeval | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_FULL_CORPUS_R0_EXACT_LEXICAL | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_FULL_CORPUS_R1_FUZZY_LEXICAL | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_FULL_CORPUS_R2_LEXICAL_CONTEXT | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_POST_RANKING_DIAGNOSTICS_R1_R2 | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_QWEN_SHARED_TOPK_R1 | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_V263_PERSISTED_POSTRANKING | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| OAEI_V263_QWEN_COMPACT_RELIABILITY | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V264_GOLD_HARD_NEGATIVE_AND_PAIRWISE_DIAGNOSTIC | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V264_QWEN_COMPACT_SHARED_TOPK_SEMANTIC | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V265_QWEN_SEMANTIC_VALIDATION | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V265_SEMANTIC_CONFIDENCE_EVIDENCE | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V265_QWEN_IDENTICAL_PROMPT_CONSISTENCY | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V266_QWEN_ORDER_ROBUSTNESS | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V266_QWEN_PROFILE_ABLATION | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V266_QWEN_PROMPT_ROBUSTNESS | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V266_QWEN_FAILURE_DIAGNOSTIC | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| V266_QWEN_OPAQUE_ID | oaei | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Dataset Status

The table includes executed and explicitly unavailable external runs. `N/A` means a dataset was unavailable or its supported metric was not supplied; it is not a zero score. Synthetic CDOI-Bench results are deliberately excluded.

## Execution Notes

- `EXT_OAEI_B6`: `OAEI data not found at data\benchmarks\external\oaei. Follow data/benchmarks/external/README.md.`.
- `OET_B0`: `Concept-placement split 'test' is missing from local external/oet storage. Follow data/benchmarks/external/README.md.`.
- `RCA_FULL_CDOI`: `RCAEval normalized case index is missing from local external/rcaeval storage. Follow data/benchmarks/external/README.md.`.
