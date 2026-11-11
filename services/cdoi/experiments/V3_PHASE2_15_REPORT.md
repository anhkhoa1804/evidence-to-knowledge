# V3 Phase 2.15 — Internal Qwen Live RCA V1

Final gate: `QWEN_RUNTIME_SUPPORTED_RCA_QUALITY_INSUFFICIENT`.

Diagnostic: `V1_INVESTIGATION_NOT_ACTIVATED`.

## Runtime and V1 outcome

The internal runtime requested `vllm/Qwen3.8-27B` and resolved
`Qwen3.8-27B`. Its bounded qualification passed 12/12 interactions, including
structured output, one native tool, and serial two-tool continuation.

The immutable V1 development batch accounted for all 12 consumed Phase 2.11
cases: nine `INSUFFICIENT_EVIDENCE`, two provider transport failures, and one
strictly rejected `RCA_HYPOTHESIS` without a primary hypothesis. It produced
zero accepted hypotheses, zero tool calls, zero fallback activations, zero
citations, and Top-1 0/12. Transport failures remain technical outcomes, not
wrong RCA diagnoses.

## Input and investigation audit

Every initial RCA request included incident context, H1 candidate records, and
ten read-only native tool definitions with provider-auto tool choice. Full
`CandidateEvidenceProfile` objects were not preloaded; they were available
through `get_candidate_profile`, which the model never called. The supported
diagnosis is `TOOLS_ATTACHED_BUT_UNUSED` with text-report termination before
investigation. Prompt overweighting of abstention is plausible but not
identifiable from the frozen artifacts.

V1 did not send a `max_tokens` field. Nine of ten recorded provider responses
exceeded 256 completion tokens and the maximum was 1,737, so
`CDOI_LLM_MAX_TOKENS=256` did not truncate this V1 path. Finish reasons and
failed-request HTTP/timeout details were not recorded.

## Stability and grounding

Nine exact-configuration repeats covered a one-candidate abstention, a
nine-candidate abstention, and a prior transport-failure case. All 9/9 again
made zero tool calls and used no fallback. Six successful responses abstained;
the nine-candidate case failed transport in all three repeats; the earlier
transport-failure case succeeded and abstained in all three repeats.

The frozen artifacts contain no unknown evidence ID or invalid candidate ID.
No tool grounding occurred. Because raw natural-language model output was not
retained, claim-level supported/unsupported counts are `NOT_EVALUATED`; the
result is `NO_TOOL_GROUNDING_OCCURRED`, not fabricated tool evidence.

## Performance and boundaries

Ten primary-batch responses retained provider metrics: mean latency 13,620.6
ms, median 12,642.9 ms, and p90 18,513.6 ms. They used 18,412 input tokens and
8,549 output tokens (26,961 total). Failed-request duration and actual retry
attempts were not persisted.

No semantic policy, H1/H5 rule, canonical KG, review gate, or Phase 2.12
artifact changed. Independent RCA-agent validation remains `DATA_MISSING`.

Final regression: 214 collected, 214 passed, 0 failed, 0 skipped.
