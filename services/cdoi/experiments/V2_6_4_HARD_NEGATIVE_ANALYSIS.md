# V2.6.4 Diagnostic — Gold vs Strongest Wrong Candidate

## Measured result

This post-retrieval analysis reused the persisted R1 Top-20 candidate artifact.
It contains 1,385 source cases whose reference target was already in Top-20;
the reference was attached only after candidate features were generated. The
hard negative is the highest-ranked supplied candidate that is not the gold
candidate. No retrieval, score calculation, or comparator receives gold data.

| Feature | Gold mean | Strongest-wrong mean | Gold > wrong | Tie |
| --- | ---: | ---: | ---: | ---: |
| Lexical | 0.8961 | 0.6702 | 0.8556 | 0.0087 |
| Context | 0.2243 | 0.1268 | 0.5487 | 0.3220 |
| R2 combined | 0.7618 | 0.5615 | 0.8729 | 0.0029 |
| Parent similarity | 0.3199 | 0.1625 | 0.3935 | 0.5242 |
| Child similarity (available N=52) | 0.5533 | 0.1463 | 0.7885 | 0.0385 |
| Property similarity (available N=427) | 0.5316 | 0.3574 | 0.5222 | 0.3560 |

Definitions are unavailable, so no definition-similarity value was invented.
For the 456 non-trivial eligible cases, gold wins on lexical in 0.5614,
context in 0.5307, and R2 combined in 0.6140 of pairs. Parent and property
components overlap heavily; child evidence is sparse despite a high win rate
when present.

## Diagnostic interpretation

Existing evidence does distinguish many gold candidates, principally through
lexical and the fixed R2 combination. It is much less decisive on non-trivial
cases, and structural components have many ties. This supports H1 (hard-negative
overlap), especially for difficult mappings; it does not establish that context
is useless or justify a production policy change.

Machine-readable distributions, quantiles, and per-pair deltas are in
`V264_GOLD_HARD_NEGATIVE_AND_PAIRWISE_DIAGNOSTIC/exp-bfe5c97ad5d8/result.json`.
