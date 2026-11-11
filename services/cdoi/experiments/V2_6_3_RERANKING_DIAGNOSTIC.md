# V2.6.3 Diagnostic — Deterministic Shared-Top-K Reranking

## Protocol

R2 scores were calculated independently for every candidate in the already
persisted R1 candidate set. Candidate scoring and reranking never read the gold
target. Gold is used only afterward for metrics. Reranking is reported before
any frozen-threshold acceptance.

| K | Oracle@K | Reranked Top-1 | Gap to oracle | Rank>1 promoted to 1 | Rank-1 preserved | Rank-1 damaged | Net target-selection gain |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.8784 | 0.8009 | 0.0775 | 13 | 1,186 | 4 | +9 |
| 10 | 0.9058 | 0.8016 | 0.1042 | 14 | 1,186 | 4 | +10 |

At K=10, 62 gold candidates move upward, 10 move downward, and 1,284 remain at
the same rank. Non-trivial reranked Top-1 accuracy is 0.4771. Applying the
unchanged 0.82 threshold to R2 after reranking yields only 0.4736 correct
accepted mappings, demonstrating the score-scale issue rather than reranking
quality.

## Diagnostic interpretation

The fixed R2 score recovers a small but real set of rank>1 gold targets while
damaging four rank-1 cases. It does not close the oracle gap and is not safe to
adopt as production policy. The result supports further diagnostic work on a
separate commitment-confidence signal, not a global threshold change.
