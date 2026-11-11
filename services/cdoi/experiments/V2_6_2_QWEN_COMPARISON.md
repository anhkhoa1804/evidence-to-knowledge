# V2.6.2 Diagnostic — Shared Top-K Deterministic vs Qwen

## Protocol

`OAEI_SHARED_TOPK_QWEN_COMPARISON` used a deterministic stratified N=8 sample:
threshold abstentions, deterministic wrong targets, non-trivial cases, and
trivial lexical cases. Every Qwen prompt contained only the source and the same
persisted R1 Top-5 candidate profiles used by the deterministic result. Gold
target IDs were withheld until after the model response. Out-of-candidate target
IDs are invalid; attempts were bounded at two.

## Measured result

| Metric | Value |
| --- | ---: |
| Sample size | 8 |
| Model calls | 16 |
| Valid final response rate | 0.0000 |
| Parse/schema failure rate | 1.0000 |
| Retry rate | 1.0000 |
| Out-of-candidate rate | 0.0000 |
| Final abstention rate | 1.0000 |
| Mean per-case latency | 13,526.6 ms |

The run had six successful transport/structured calls and ten parse failures at
the underlying client boundary, but no case produced a final candidate-valid
selection after the bounded retry policy. It is therefore a structured-output
reliability measurement, not a Qwen target-selection score. No Qwen output was
accepted or committed to ontology/KG state.

## Diagnostic interpretation

The earlier N=1 direct prompt established that the gateway can return valid JSON
with enough response budget. This shared-Top-K batch establishes that the
current reusable structured prompt/client combination is not reliable enough to
measure Qwen selection on this sample. Before comparing Qwen with deterministic
selection, investigate prompt compactness and diagnostic response budget while
retaining candidate-membership validation and the bounded retry limit.
