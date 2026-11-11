# V2.6.3 Diagnostic — Compact Qwen Structured-Output Reliability

## Protocol

The microbenchmark used two deterministic persisted R1 Top-5 candidate sets and
the compact `QREL_COMPACT_V1` schema: `candidate_id` from the supplied list or
`NONE`, plus `EQUIVALENT` or `NONE`. It did not include gold/reference fields,
did not retry, and recorded only safe lifecycle metadata.

| Budget | N | Valid candidate response | Technical invalid | Mean latency |
| ---: | ---: | ---: | ---: | ---: |
| 512 | 2 | 1.0000 | 0.0000 | 2,837.6 ms |
| 1024 | 2 | 1.0000 | 0.0000 | 2,729.3 ms |

All four calls returned HTTP 200 with `finish_reason=stop`, non-empty content,
JSON extraction/parsing success, schema validation success, and supplied-set
membership validation success. There were no transport, empty, truncation,
JSON, schema, or out-of-candidate failures.

## Diagnostic interpretation

The V2.6.2 zero-valid-result batch was caused by the verbose reusable structured
prompt/client path, not by gateway reachability. This N=2 microbenchmark shows
the compact direct schema is technically viable at 512 tokens. It does **not**
measure target-selection quality; a larger bounded shared-Top-K experiment is
needed before any deterministic-versus-Qwen quality conclusion.
