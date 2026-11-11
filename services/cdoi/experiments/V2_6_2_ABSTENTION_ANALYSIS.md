# V2.6.2 Diagnostic — R1 Threshold Abstentions

## Measured result

The machine-readable artifact contains all 342 mutually exclusive
`THRESHOLD_ABSTENTION` cases, including source/gold labels, normalized labels,
gold rank, Top-20 candidate IDs and scores, score components, threshold margin,
and evidence availability. It is stored in the persisted diagnostic result, not
in this report, to keep the review surface concise.

| Gold-rank bucket | N |
| --- | --: |
| 1 | 175 |
| 2–5 | 109 |
| 6–10 | 30 |
| 11–20 | 28 |

| Margin below 0.82 | N |
| --- | --: |
| Within 0.02 | 33 |
| 0.02–0.05 | 31 |
| 0.05–0.10 | 77 |
| More than 0.10 | 201 |

All 342 cases have different normalized source/gold labels; none are exact
normalized-label cases. All selected candidates have both lexical and context
features available (two available feature types).

## Gold-rank conditional selection

| Gold rank | N | Emission | Abstention | Correct selection | Wrong target |
| --- | --: | ---: | ---: | ---: | ---: |
| 1 | 1,190 | 0.8529 | 0.1471 | 0.8529 | 0.0000 |
| 2–5 | 125 | 0.1280 | 0.8720 | 0.0000 | 0.1280 |
| 6–10 | 41 | 0.2683 | 0.7317 | 0.0000 | 0.2683 |
| 11–20 | 29 | 0.0345 | 0.9655 | 0.0000 | 0.0345 |
| >20 | 112 | 0.0714 | 0.9286 | 0.0000 | 0.0714 |

## Diagnostic interpretation

Rank-1 gold cases isolate acceptance behavior: 175 rank-1 cases abstain, and
many are well below the threshold rather than merely borderline. For ranks 2–20,
the frozen top-1 emitter cannot select the gold without a reranker: any emitted
candidate is necessarily a wrong target. These are different failure mechanisms
and must not be addressed by a single threshold adjustment.
