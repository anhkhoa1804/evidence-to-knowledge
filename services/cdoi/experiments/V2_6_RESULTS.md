# CDOI V2.6 Results

## Environment

- Offline deterministic tests and demo remain the baseline path.
- Optional `sentence-transformers` was installed in the project virtual environment; its runtime status is recorded below.
- OAEI Anatomy 2026 was acquired locally under the track terms. OET and RCAEval were not bundled.

## Qwen Connectivity

- Status: `missing_credential`.
- Credential present: `False`; gateway reached: `N/A`; model accepted: `N/A`; structured JSON: `N/A`.
- The adapter supports an environment-supplied Bearer token, configured `Host` header, JSON mode, schema validation, bounded retry, and secret-free cache/report metadata. No network call is made when credentials are absent.

## External Benchmark Results

| Dataset | Status | N | Result | License |
| --- | --- | ---: | --- | --- |
| OAEI Anatomy 2026 | EXECUTED | 7580 | positive-reference recall 0.0; alignment F1 N/A | track_terms_required |
| Concept placement | READY_BUT_DATA_MISSING | 0 | Concept-placement split 'test' is missing from local external/oet storage. Follow data/benchmarks/external/README.md. | local dataset license required |
| RCAEval | READY_BUT_DATA_MISSING | 0 | RCAEval normalized case index is missing from local external/rcaeval storage. Follow data/benchmarks/external/README.md. | selected release license required |

OAEI was evaluated as a reference-positive-pair abstention protocol, not a full-corpus OAEI matcher: it has no negative correspondences and does not support precision, F1, or false-merge estimates. Those fields are intentionally N/A.

| Method | Dataset | N | Positive-reference recall | Alignment F1 | False Merge | Unresolved |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B0 lexical | OAEI Anatomy | 7580 | 0.6339050131926122 | N/A | N/A | 0.009894459102902375 |
| B1 real embedding | OAEI Anatomy | N/A | N/A | N/A | N/A | N/A |
| B2 lexical + embedding signal | OAEI Anatomy | 7580 | 0.6339050131926122 | N/A | N/A | 0.009894459102902375 |
| B3 structural | OAEI Anatomy | 7580 | 0.0 | N/A | N/A | 0.8680738786279684 |
| B6 full CDOI | OAEI Anatomy | 7580 | 0.0 | N/A | N/A | 0.06992084432717678 |

## Real Model Results

| Method | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Review Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| lexical/full deterministic | CDOI-Bench controlled | 14 | 1.0 | 0.0 | 0.2143 | 1.0 | 0.2143 |
| real embedding | CDOI-Bench | 0 | N/A | N/A | N/A | N/A | N/A | (embedding_runtime_unavailable:OSError)
| Qwen B4/B5/B6Q/B7 | CDOI-Bench | 0 | N/A | N/A | N/A | N/A | N/A | (missing_credential)

## Robustness

Controlled deterministic evidence/noise/late-evidence/property-stress results remain in `ROBUSTNESS_RESULTS.md`. Real-model variants could not run in this environment, so no model robustness comparison is claimed.

## Failure Analysis

- OAEI reference-pair evaluation: class relation errors `7050` and false unresolved `530`; unsafe equivalence `0`.
- Dominant observed external failure: semantic decision/over-abstention after pair presentation. Retrieval quality cannot be measured fairly in this pair-only protocol.
- Model execution blockers: missing Qwen credential and local PyTorch DLL initialization failure for the real embedding provider.

## External Validity Gap

Controlled CDOI-Bench full-context F1 is 1.0 (N=14); OAEI Anatomy reference-positive recall is 0.0 (N=7,580). These metrics are not directly comparable, but the observed gap rejects any claim that controlled performance generalizes to this external track.

## V3 Recommendation

Prioritize a fair external retrieval-and-ranking protocol with target-corpus candidate sets, then diagnose retrieval miss versus relation-choice error. Re-run real embeddings after resolving the local PyTorch runtime and run Qwen only when the credential is available; do not redesign semantic policy before those measurements.
