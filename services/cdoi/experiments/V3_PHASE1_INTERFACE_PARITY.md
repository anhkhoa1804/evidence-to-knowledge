# V3 Phase 1 Interface Parity

## Scope

V3 wraps, rather than rewrites, the diagnostic selection behavior. `R1` selects
the original CandidateSet rank 1. `R2` keeps V2.6's descending
`r2_combined_score`, candidate-ID tie break. The compact Qwen adapter keeps the
existing schema and maps only a valid `NONE` response to semantic abstention.
Empty, invalid, out-of-candidate, schema, transport and timeout outcomes are
technical unavailable.

## Parity result

| Behavior | V2.6.6 baseline | V3 Phase 1 |
| --- | --- | --- |
| Candidate ordering | Persisted retrieval order | Immutable `CandidateSet` ranks 1..N |
| R1 selector | Original rank 1 | `R1DeterministicSelector` rank 1 |
| R2 selector | Descending R2, ID tie break | `R2DeterministicSelector` identical rule |
| Qwen valid NONE | Semantic abstention | `SEMANTIC_ABSTAIN` |
| Qwen technical invalid | Candidate-valid false, not NONE | `TECHNICAL_UNAVAILABLE` |
| R1 threshold | 0.82 frozen evaluator policy | Unchanged; not used as selector confidence |
| Commit/KG policy | Existing validation/review/version gate | Unchanged; V3 is not wired to pipeline |

The V3 unit fixtures prove deterministic selections, prompt ordering/opaque
mapping/reference absence, and fail-closed Qwen states. They do not rerun a
credentialed historical Qwen experiment; reproducibility of remote output is
therefore `PARTIALLY_SUPPORTED`, while protocol parity is `IMPLEMENTED`.
