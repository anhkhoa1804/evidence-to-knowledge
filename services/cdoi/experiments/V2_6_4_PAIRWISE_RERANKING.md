# V2.6.4 Diagnostic — Fixed Component-Vote Pairwise Reranking

## Protocol

The label-free comparator votes across existing lexical, parent, child, and
property components; ties use persisted retrieval rank, then candidate ID. It
has no fitted weights and reads gold only after ranking. This is a diagnostic
test, not a new CDOI ranker.

| K | R1 Top-1 | R2 scalar Top-1 | Pairwise Top-1 | Oracle@K | Pairwise rank>1 promotions | Pairwise rank-1 damage | Pairwise net gain |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.7949 | 0.8009 | 0.7943 | 0.8784 | 3 | 4 | -1 |
| 10 | 0.7949 | 0.8016 | 0.7929 | 0.9058 | 3 | 6 | -3 |

At K=10, pairwise non-trivial Top-1 is 0.4630, below the R2 scalar diagnostic
(0.4771). Its outcome taxonomy is 1,184 correct preserved, 3 correct promoted,
6 correct demoted, 163 gold still below Top-1, and 141 gold not in Top-10.

## Diagnostic interpretation

The fixed component-vote rule does not close more oracle gap than the existing
scalar R2 reranker and causes additional rank-1 damage. H3 is not supported by
this particular untuned comparator. No pairwise rule is productionized.
