# V2.6.5 Diagnostic — Pre-specified Compact Qwen Validation

## Protocol

The frozen `QSEM_COMPACT_PROFILE_V1` prompt and candidate/relation schema were
used unchanged. A duplicate-free, seed-265 N=150 Top-10 sample was assigned
before Qwen inference by this priority: rank-1 threshold abstention, gold rank
2–5, gold rank 6–10, R2 failure, margin <0.05, margin 0.05–0.10, remaining
non-trivial, then easy control. Gold-rank and R2-failure strata are explicitly
**reference-aware diagnostic sampling**, not population estimates or deployable
routing features. All methods used the identical persisted candidate list.

| Stratum | N |
| --- | ---: |
| Rank-1 threshold abstention | 21 |
| Gold rank 2–5 | 21 |
| Gold rank 6–10 | 20 |
| R2 failure | 20 |
| Margin <0.05 | 8 |
| Margin 0.05–0.10 | 20 |
| Remaining non-trivial | 20 |
| Easy control | 20 |

## Measured result

There were 164 calls for 150 sampled cases. Candidate-valid output was 142/150
(0.9467); semantic metrics are conditional on those 142 cases. R1, R2, and
Qwen accuracy on the same valid population were 0.6056, 0.6197, and 0.7958.
Qwen combined mapping accuracy is also 0.7958; relation accuracy is 0.8310 and
semantic abstention is 0.1690. Non-trivial Qwen accuracy is 0.7500.

For explicit easy controls, Qwen, R1, and R2 were each correct on all 20/20
candidate-valid cases. Among rank-1 deterministic selections, Qwen was correct
on 64/65 valid cases; this one regression is retained rather than hidden.
For gold rank 2–5, Qwen was 15/20 correct versus R1 0/20 and R2 2/20; for gold
rank 6–10, Qwen was 14/16 correct versus R1/R2 0/16. For gold >10, no method
selected gold; Qwen abstained in 18/20 cases.

## Diagnostic interpretation

The N=50 advantage survives this larger, deliberately difficult,
reference-aware validation sample. It is concentrated in retrieved-but-not-top1
cases, while easy controls show no observed damage in this sample. This is
evidence for a future selective semantic-reranking research direction only;
it does not establish a production router, commitment threshold, or automatic
acceptance mechanism.
