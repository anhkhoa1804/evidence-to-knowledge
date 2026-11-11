# V2.6.6 Diagnostic — Neutral Prompt-Paraphrase Sensitivity

The same N=20 candidate sets and full profiles were evaluated with three neutral
instruction variants; schema and task were unchanged.

| Prompt | Valid | Accuracy on valid | Non-trivial | Abstain |
| --- | ---: | ---: | ---: | ---: |
| P0 frozen | 20/20 | 0.7500 | 0.6875 | 0.2000 |
| P1 compact paraphrase | 19/20 | 0.7368 | 0.6667 | 0.2105 |
| P2 alternate instruction order | 16/20 | 0.5625 | 0.4615 | 0.3750 |

Eighteen of 20 sources remained target/relation invariant when valid; two are
`REPRESENTATION_SENSITIVE`. P2 also produced four empty outputs.

## Interpretation

The frozen prompt and close paraphrase are similar, but instruction ordering is
materially sensitive. This falsifies a strong representation-robustness claim
and means prompt versioning/fallback must remain explicit in future research.
