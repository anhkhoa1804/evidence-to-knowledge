# V3 Phase 2 Interface Parity

## Deterministic execution

`phase2_parity` executed `R1DeterministicSelector` and
`R2DeterministicSelector` through the V3 contracts on all 1,497 frozen V2.6
shared-Top-10 rows from `OAEI_V263_PERSISTED_POSTRANKING`.

| Comparison | Result | Classification |
| --- | ---: | --- |
| R1 selected candidate and status | 1,497 / 1,497 exact | EXACT_PARITY |
| R2 selected candidate and status | 1,497 / 1,497 exact | EXACT_PARITY |
| R2 selected score | 1,497 / 1,497 exact | EXACT_PARITY |
| R1 Top-1 correctness | 0.794923 | EXACT_PARITY |
| R2 Top-1 correctness | 0.801603 | EXACT_PARITY |
| R1 non-trivial correctness | 0.459507 | EXACT_PARITY |
| R2 non-trivial correctness | 0.477113 | EXACT_PARITY |

The V3 CandidateSet adapter copies only observable candidate fields from rows
that also contain reference labels. It does not copy gold target/rank/
correctness into inference objects. No deterministic difference was observed.

## Qwen protocol parity

The frozen 150-case V2.6.5 validation artifact, opaque-ID artifact, and
`QSEM_COMPACT_PROFILE_V1` protocol were inspected. V3 retains candidate order,
opaque handle mapping, `candidate_id_relation_v1`, bounded retry, and the
distinction between valid `NONE` (`SEMANTIC_ABSTAIN`) and malformed/empty/
out-of-candidate/transport output (`TECHNICAL_UNAVAILABLE`).

No new remote invocation was made: current credentials are not part of the
baseline and remote output is not expected to be bit-identical. Classification:
`UNAVAILABLE` for live-output parity; `EXACT_PARITY` for local protocol/state
handling.
