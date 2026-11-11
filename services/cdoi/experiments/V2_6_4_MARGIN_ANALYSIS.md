# V2.6.4 Diagnostic — R1 Candidate Margin and Ambiguity

## Measured result

Margins use the original R1 lexical retrieval score only. They are descriptive
and are not a new acceptance rule.

| Top1–Top2 margin | N | Top-1 correct | Abstention | Non-trivial |
| --- | ---: | ---: | ---: | ---: |
| <0.02 | 122 | 0.1721 | 0.9672 | 1.0000 |
| 0.02–0.05 | 107 | 0.2804 | 0.9252 | 1.0000 |
| 0.05–0.10 | 130 | 0.5846 | 0.8000 | 0.9385 |
| 0.10–0.20 | 237 | 0.8608 | 0.3629 | 0.5907 |
| 0.20–0.30 | 360 | 0.8944 | 0.1028 | 0.1944 |
| >=0.30 | 541 | 0.9926 | 0.0037 | 0.0129 |

Gold-rank distributions and Top1–Top5 spreads are retained in the result
artifact for every bucket.

## Diagnostic interpretation

Low candidate separation is strongly associated with lower R1 Top-1 correctness,
abstention, and non-trivial mappings in this corpus. This supports H2 as an
ambiguity signal. It does not show that margin should replace the frozen 0.82
threshold or be applied as a production rule.
