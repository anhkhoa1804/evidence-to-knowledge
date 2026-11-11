# V2.6.6 Diagnostic — Candidate-Order Robustness

## Measured result

Thirty deterministic V2.6.5 candidate-valid cases were evaluated with original,
reverse, and two seeded Top-10 permutations. Only display order changed.

| Condition | Valid | Accuracy on valid | Non-trivial | Abstain |
| --- | ---: | ---: | ---: | ---: |
| Original | 29/30 | 0.7586 | 0.6957 | 0.2069 |
| Reverse | 29/30 | 0.7586 | 0.6957 | 0.2069 |
| Seed A | 28/30 | 0.7857 | 0.7273 | 0.1786 |
| Seed B | 27/30 | 0.7778 | 0.7143 | 0.1852 |

Across all four conditions, 29/30 cases had an invariant target and relation
whenever valid; zero cases selected different semantic candidates. One case was
technically unavailable under every ordering. Display-position counts vary, but
the same selected identity moved with its permutation, so they are not evidence
of position-driven target changes in this bounded sample.

## Interpretation

This supports candidate-order robustness conditional on valid output. It does
not prove the absence of positional bias, and technical empties remain a
separate fail-closed limitation.
