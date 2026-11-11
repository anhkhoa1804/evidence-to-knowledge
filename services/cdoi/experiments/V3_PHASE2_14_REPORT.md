# V3 Phase 2.14 — Qwen RCA Bring-up and Semantic-Track Audit

Status: `DEVELOPMENT_ONLY`.

## Operational/Qwen track

`QwenRCAAgentModel` implements the existing provider-neutral RCA model contract
via Qwen OpenAI-compatible Chat Completions. Its default is pinned to
`qwen3.8-max-0902`; it sends `enable_thinking: false`, disables parallel tool
calls, uses bounded retries, and preserves serial tool-call continuation. The
Qwen RCA prompt is versioned `rca_agent_qwen_v1`, separately from the
proposal-only Qwen semantic-selector path.

This environment is `QWEN_PROVIDER_UNCONFIGURED`: no Qwen/DashScope credential
or endpoint is configured. No network request, live RCA run, synthetic live
run, pilot run, or Phase 2.12 holdout access occurred. Live quality metrics are
therefore `NOT_EVALUATED`, not zero.

Mock-transport tests cover serial calls, multi-turn continuation, report
validation, malformed tool calls, timeout retry, and secret-free metadata. The
RCA gate is `QWEN_AUTH_OR_PROVIDER_BLOCKED`.

## Semantic track

Dense remains `DENSE_RUNTIME_STILL_BLOCKED`: Windows PyTorch again failed to
load `c10.dll` (`WinError 1114`), while no WSL Linux distribution is installed.
This is technical evidence, not Dense performance. The qualified IDAI/PACTOLS
DH pair remains a narrow second-domain retrieval result (six mappings,
equivalence only). Qwen semantic-selector evaluation remains unavailable.

No semantic policy, routing, calibration, ontology schema, or canonical-KG
state changed.

## Frozen boundaries

Phase 2.12's 176 recorded artifact hashes remain unchanged. Phase 2.13 hashes
were verified before the Phase 2.14 RCA run. The new RCA and semantic archives
are independent and hash-manifested.
