# V3 Phase 2.13 — Candidate Evidence and Read-Only RCA Agent V0

Status: `DEVELOPMENT_ONLY`.

Phase 2.13 adds an additive, read-only path:

```text
normalized telemetry → existing unranked CauseCandidates → CandidateEvidenceProfiles
→ bounded evidence tools → optional agent hypothesis report
```

`CauseCandidate` remains an eligibility hypothesis, not a cause. An agent's
primary hypothesis is an uncalibrated investigation ordering, not causal proof.
No ontology/KG write, selector change, commitment, review bypass, or remediation
operation is reachable through this path.

## Implemented contracts

- `candidate_evidence_profile_v1` deterministically describes metrics, traces,
  events, changes, bounded topology, temporal relationships, evidence IDs, and
  explicit missing modalities. It contains no score or causal probability.
- `read_only_rca_tools_v1` provides bounded/paged incident, candidate, profile,
  metric, trace, event, change, topology, and evidence-ID access.
- `RCAOrchestrator` reuses preprocessing, incident context, SQLite evidence
  storage, and the frozen H1/H5 generator without changing any Phase 2.11 rule.
- `RCAReport` allows only `RCA_HYPOTHESIS`, `INSUFFICIENT_EVIDENCE`, and
  `TECHNICAL_FAILURE`. Every cited candidate/evidence ID is validated.
- `RCAAgentV0` is provider-neutral, budget-bounded, prompt-versioned, and emits
  an auditable `AGENT_TRACE.json`. A missing provider produces a technical
  failure rather than a fabricated live result.

## Development result

The frozen Phase 2.13 archive uses one local deterministic demo incident only;
it does not read Phase 2.12 per-case artifacts or ground truth. It generated
five deterministic profile records across H1/H5 candidate bundles. Profile
replay was identical, cited evidence was resolvable, and the scripted-model
integration produced an evidence-cited `RCA_HYPOTHESIS`. The profile-only and
deterministic baseline modes correctly abstained instead of ranking.

The scripted model is infrastructure coverage, not model evidence. No live
provider was configured or invoked, so live-agent behavior is
`MODEL_RUNTIME_BLOCKER`; independent RCA-agent validation data is `DATA_MISSING`.
The frozen Phase 2.13 decision is
`EVIDENCE_PROFILE_SUPPORTED_AGENT_RUNTIME_BLOCKED`.

## Candidate-source policy

`H1_SHORTLIST`, `H5_EXPANDED`, and `H1_THEN_H5_FALLBACK` are explicit input
modes. The fallback mode starts with H1 and exposes H5-minus-H1 only through an
explicit read-only tool. It is a development policy surface, not an adopted
production policy.

## Frozen-boundary verification

Phase 2.12 remains `HOLDOUT_VALIDATION_TECHNICALLY_INCOMPLETE`: all 78 cases
were accounted for, 77 were evaluated after the Phase-A freeze, and one case
was an acquisition failure. This Phase 2.13 run did not rerun or tune from that
holdout. Archive hashes and manifest hashes for Phase 2.13 validate with no
mismatch.

## Remaining blockers

- Live model runtime: unavailable; no live claims were made.
- Independent RCA validation set: absent.
- Host binding, KnownProblem, Procedure, and business-impact evidence: absent
  and represented as non-blocking product/data gaps.
- Causal inference, calibrated RCA confidence, production routing, and
  production RCA remain unimplemented by design.
