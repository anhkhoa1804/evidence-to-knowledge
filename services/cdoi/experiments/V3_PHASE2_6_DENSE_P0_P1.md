# V3 Phase 2.6 Dense P0/P1

**IMPLEMENTED FACT:** the full runner remains smoke-gated and frozen to shared CandidateSets, MiniLM, CPU, normalized embeddings, and `dense_structured_profile_v1`.

## Status

`RUNTIME_BLOCKER`: Windows `torch_import` / `OSError`. Linux/WSL execution is also unavailable: no installed WSL distribution exists and this non-admin session cannot provision the required runtime. No Dense P0/P1 metrics, intersection counts, abstentions, or zero scores were emitted.

A clean Linux/WSL environment must pass the smoke contract before the existing full runner is allowed to calculate P0/P1 same-CandidateSet metrics.
