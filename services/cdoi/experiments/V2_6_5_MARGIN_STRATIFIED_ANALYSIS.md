# V2.6.5 Diagnostic — Margin-Stratified Same-Case Comparison

All accuracies are conditional on candidate-valid Qwen outputs in each original
R1 margin bucket. Technical validity uses all sampled cases in that bucket.

| Margin | Sampled / valid | R1 | R2 | Qwen | Qwen abstain | Non-trivial |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| <0.02 | 21 / 19 | 0.2632 | 0.3158 | 0.6316 | 0.3684 | 1.0000 |
| 0.02–0.05 | 26 / 25 | 0.3200 | 0.3600 | 0.6800 | 0.3200 | 1.0000 |
| 0.05–0.10 | 37 / 35 | 0.6571 | 0.6571 | 0.8571 | 0.1143 | 0.8108 |
| 0.10–0.20 | 31 / 29 | 0.8621 | 0.8621 | 0.8276 | 0.1034 | 0.9677 |
| 0.20–0.30 | 24 / 23 | 0.6522 | 0.6522 | 0.8696 | 0.0870 | 0.6250 |
| >=0.30 | 11 / 11 | 0.9091 | 0.9091 | 0.9091 | 0.0000 | 0.0909 |

## Diagnostic interpretation

Qwen’s largest measured gains occur below margin 0.10; at >=0.30 it adds no
measured target-selection benefit. The 0.10–0.20 bucket is a counterexample to
a simplistic monotonic routing story: Qwen is slightly below deterministic
selection there. These are exploratory diagnostic strata, not a fitted or
production routing cutoff.
