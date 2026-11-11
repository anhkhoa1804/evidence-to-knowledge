# V2.6.3 Diagnostic — Rank-1 Acceptance Profile

## Measured result

This diagnostic reused the persisted V2.6.2 R1 Top-20 candidate artifact and
computed R2 components only for those candidates. Retrieval was not rerun and
gold was used only for grouping after scores were calculated.

| Group | N | Median R1 lexical | Median R2 context | Median R2 combined | Median threshold margin | Median Top1–Top2 R1 margin |
| --- | --: | --: | --: | --: | --: | --: |
| A1 rank-1 gold, correctly emitted | 1,015 | 1.0000 | 0.2000 | 0.8400 | +0.1800 | 0.3056 |
| A2 rank-1 gold, abstained | 175 | 0.7076 | 0.1481 | 0.6027 | -0.1124 | 0.0917 |
| A3 rank-1 incorrect | 0 | N/A | N/A | N/A | N/A | N/A |

For A1, R2 combined mean/standard deviation are 0.8362/0.0489; for A2 they
are 0.5989/0.0719. A2 has lower lexical similarity and a substantially smaller
Top1–Top2 margin. Context medians differ modestly, not categorically.

| Evidence availability | A1 | A2 |
| --- | ---: | ---: |
| Definition for both profiles | 0.0000 | 0.0000 |
| Parent context | 1.0000 | 1.0000 |
| Child context | 0.1182 | 0.1086 |
| Property context | 0.2926 | 0.3429 |

## Diagnostic interpretation

The measurable distinction is principally lexical score and candidate margin,
not missing definitions or parent-context availability. This supports an
acceptance/discrimination hypothesis for non-trivial rank-1 cases, but does not
establish causality or justify changing the frozen threshold.
