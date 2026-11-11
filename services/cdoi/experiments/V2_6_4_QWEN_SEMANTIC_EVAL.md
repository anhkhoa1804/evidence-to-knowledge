# V2.6.4 Diagnostic — Compact Qwen Shared-Top-K Semantic Selection

## Protocol

`OAEI_QWEN_COMPACT_SHARED_TOPK_SEMANTIC_V1` used a deterministic stratified
N=50 sample from the persisted R1 Top-20 artifact, with the same supplied
Top-10 candidates for every comparator. The compact prompt contained source
and candidate semantic profiles only (IDs, labels, aliases, parent/child and
property neighbourhoods). It contained no reference target, gold rank, or
correctness field. Responses were bounded to two attempts and no raw output or
model reasoning was persisted.

| Stratum | N sampled |
| --- | ---: |
| Rank-1 threshold abstention | 7 |
| Gold rank 2–5 | 8 |
| Gold rank 6–10 | 7 |
| Pairwise diagnostic failure | 6 |
| Remaining non-trivial | 7 |
| Remaining low-margin | 7 |
| Easy control | 8 |

## Measured result

There were 53 calls for 50 cases (retry rate 0.0600). Forty-seven cases
(0.9400) were technically/candidate-valid; three final records were empty
responses. There were no transport, truncation, JSON, schema, or
out-of-candidate failures. Mean recorded case latency was 3,577.4 ms.

All semantic metrics below are conditional on those 47 candidate-valid cases.

| Metric | Value |
| --- | ---: |
| Qwen target selection / combined mapping accuracy | 0.8085 |
| Qwen relation accuracy | 0.8511 |
| Qwen abstention rate | 0.1489 |
| R1 target accuracy on same cases | 0.5957 |
| R2 scalar reranker on same cases | 0.6170 |
| Pairwise component-vote diagnostic on same cases | 0.4681 |
| Qwen non-trivial accuracy | 0.6667 |
| Rank-1-abstention recovery | 1.0000 |
| Gold-rank-2–5 recovery | 0.7500 |
| Gold-rank-6–10 recovery | 0.8000 |
| Easy-control accuracy | 1.0000 |

The pairwise-Qwen disagreement matrix is: deterministic-correct/Qwen-correct
16; deterministic-correct/Qwen-wrong 0; deterministic-wrong/Qwen-correct 6;
deterministic-wrong/Qwen-wrong 2; R1-abstained/Qwen-correct 16; and
R1-abstained/Qwen-wrong 7.

## Diagnostic interpretation

The compact path remains mostly reliable but is not perfect at N=50: the three
empty responses must remain separate from semantic abstention, and all quality
figures are conditional on valid outputs. On this bounded, non-independent
diagnostic sample, Qwen selects the gold supplied target more often than the
fixed deterministic comparators, especially in the difficult strata. This is
support for H4 as diagnostic evidence only; it is not a production routing
policy, auto-acceptance rule, or claim of statistical certainty.

No Qwen proposal was committed to ontology or KG state.
