# V2.6.2 Diagnostic — Threshold, Coverage, and Available Evidence

## Measured result

This is an isolated `OAEI_POST_RANKING_DIAGNOSTICS_R1_R2` run over the frozen
R1 Top-20 rankings. It does not modify the production/frozen 0.82 threshold and
uses the reference only after retrieval for evaluation.

| Threshold | Coverage | Abstentions | Precision | Recall | F1 | Incorrect emitted | Non-trivial recall |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.50 | 0.9913 | 13 | 0.7999 | 0.7929 | 0.7964 | 297 | 0.4542 |
| 0.60 | 0.9446 | 83 | 0.8303 | 0.7842 | 0.8066 | 240 | 0.4313 |
| 0.70 | 0.8330 | 250 | 0.8901 | 0.7415 | 0.8090 | 137 | 0.3187 |
| 0.78 | 0.7361 | 395 | 0.9428 | 0.6941 | 0.7995 | 63 | 0.1937 |
| **0.82 frozen** | **0.7021** | **446** | **0.9657** | **0.6780** | **0.7967** | **36** | **0.1514** |
| 0.84 | 0.6673 | 498 | 0.9840 | 0.6566 | 0.7877 | 16 | 0.0951 |
| 0.95 | 0.6306 | 553 | 0.9905 | 0.6246 | 0.7661 | 9 | 0.0106 |

The complete deterministic grid and all per-case values are in the persisted
`result.json` for experiment `OAEI_POST_RANKING_DIAGNOSTICS_R1_R2`.

## Available-evidence D0/D1 comparison

D0 exactly preserves the R2 evaluation score (`0.8 * lexical + 0.2 * context`,
with unavailable context contributing zero). D1 is an isolated post-ranking
counterfactual: it removes only the unavailable context weight for candidates
where context is unavailable, without modifying the corpus ranking, global
weights, or production policy.

| Mode | N | Score changed | Decision changed | Correct decisions |
| --- | --: | --: | --: | --: |
| D0 frozen | 1,497 | — | — | 709 |
| D1 available-feature normalized | 1,497 | 1 | 0 | 709 |

## Diagnostic interpretation

Lower thresholds increase recall and non-trivial recall but produce materially
more incorrect commitments (36 at frozen 0.82 versus 297 at 0.50). This is not
evidence to change the production threshold. The D1 result does not support
unavailable R2 context as the explanation for the observed abstentions in this
corpus run.
