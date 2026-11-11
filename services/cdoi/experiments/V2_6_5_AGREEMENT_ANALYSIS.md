# V2.6.5 Diagnostic — R1/R2/Qwen Agreement Evidence

| Agreement category | N | Qwen-valid accuracy | Non-trivial | Median margin |
| --- | ---: | ---: | ---: | ---: |
| All agree | 87 | 0.9655 | 0.7011 | 0.1219 |
| R1=R2, Qwen differs | 27 | Qwen 0.9259; R1/R2 0.0370 | 1.0000 | 0.0542 |
| R2=Qwen, R1 differs | 2 | Qwen/R2 1.0000 | 1.0000 | 0.0157 |
| All disagree | 2 | Qwen 1.0000 | 1.0000 | 0.0465 |
| Qwen abstains | 24 | Qwen 0.0000; R1/R2 0.0417 | 1.0000 | 0.0429 |
| Qwen technical-invalid | 8 | N/A | 0.8750 | 0.0813 |

On the 142 candidate-valid cases, Qwen corrects 29 R1-wrong cases while
disagreeing incorrectly with 2 R1-correct cases (net +27); against R2 the
corresponding net is +25. R1 threshold-abstention/Qwen-correct is 45 cases,
but this remains retrospective diagnostic evidence rather than a runtime rule.

## Diagnostic interpretation

Unanimous agreement is highly reliable on this sample. The most informative
disagreement pattern is R1=R2 with Qwen differing: it is low-margin,
non-trivial, and Qwen is usually correct. Agreement is promising future
confidence evidence, but needs independent calibration before any deployment.
