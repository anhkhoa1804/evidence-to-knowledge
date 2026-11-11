# V2.6.6 Diagnostic — Technical Failure Characterization

The frozen V2.6.5 run had 7 final empty HTTP-200/`length` responses and one
HTTP 502. Valid-case mean/median prompt length was 2,629.7/2,536 characters;
the eight final-invalid cases were 2,825.6/2,588. This modest difference is not
evidence of causal prompt-complexity dependence.

The eight final-invalid sources were rechecked with unchanged profile/prompt
semantics at 512 and 1024 tokens.

| Budget | Valid | Empty | Mean latency |
| ---: | ---: | ---: | ---: |
| 512 | 3/8 | 5/8 | 14,336.0 ms |
| 1024 | 5/8 | 3/8 | 20,344.9 ms |

Two sources remained empty at both budgets; one recovered only at 1024. All
technical failures remain `candidate_valid=false` with no inferred semantic
`NONE`; valid schema `NONE` is recorded separately as model abstention.

## Interpretation

A larger budget recovers some formerly invalid cases but adds latency and does
not remove persistent failures. This supports bounded, fail-closed proposal
experiments only; it is not a reliability basis for commitment.
