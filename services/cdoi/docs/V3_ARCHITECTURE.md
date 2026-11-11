# V3 Semantic-Decision Architecture

V3 is an additive, behavior-preserving refactor of semantic-decision research
artifacts. It does not alter the foundation/core/domain/bridge architecture,
proposal validator, `ReviewGate`, `ProposalApplier`, version store, or
canonical-versus-staging KG behavior.

```text
Semantic profile -> CandidateRetriever -> immutable CandidateSet
  -> AmbiguityEvidence + EvidenceAssembler -> SemanticSelector
  -> SelectionResult -> CommitmentConfidence protocol -> DecisionPolicy
  -> existing validation/review/commit boundary
```

## Terms

- **SourceEvidence** is the source-faithful preservation layer. It retains
  available labels, aliases, definitions, hierarchy, properties, and their
  raw-source provenance before any selector chooses to consume a field. It
  excludes gold/reference information. Preserving a field does not authorize
  a selector to weight it, route on it, or modify a production profile.
- **Retrieval** ranks candidates into a `CandidateSet`; its score is retrieval
  evidence, not commitment confidence.
- **Ambiguity** is observable separation/completeness evidence (for example,
  top-1/top-2 margin); it does not route, accept, or reject.
- **Selection** chooses a candidate/relation from the supplied immutable set.
- **Semantic abstention** is a valid selector response that no candidate should
  be chosen (`SEMANTIC_ABSTAIN`).
- **Technical unavailable** is timeout, transport, empty, malformed,
  out-of-candidate, or selector failure (`TECHNICAL_UNAVAILABLE`), never an
  inferred semantic abstention.
- **Commitment confidence** is separately calibrated evidence. Phase 1 returns
  `NOT_CALIBRATED`; it is not a similarity score.
- **Policy** maps selector/commitment evidence to reviewable outcomes. The V3
  Phase-1 policy can only propose review or return unresolved.
- **Review** remains the existing validation/review gate.
- **Commit** remains existing `ProposalApplier`/versioning behavior only.

## Evidence preservation is not evidence consumption

```text
SourceEvidence (available source fields + provenance)
        -> EvidenceAssembler (selector-visible fields)
        -> SemanticSelector (explicit representation/consumption choice)
        -> CommitmentConfidence (future calibrated safety estimate)
        -> DecisionPolicy (review-only action)
```

This distinction prevents a negative result from one selector representation
from being treated as a reason to discard valid source information. Phase 2.6
uses versioned experimental profiles for source-faithful annotation-object
resolution; normal `_profiles`, ingestion, and review/commit/KG paths remain
unchanged.

## Preserved policy

No semantic decision policy change. The frozen R1 threshold is still `0.82`
where existing V2.6 evaluation uses it. R2 remains `0.8 * lexical + 0.2 *
context` retrieval/ranking evidence, not a calibrated probability. Normal
`ContinualIntegrationPipeline` does not invoke a V3 selector or Qwen.

## Safety boundaries

`CandidateSet`, `SemanticEvidence`, and its candidate evidence reject
reference-only keys such as gold target/rank/correctness. Evaluation joins such
fields only after inference. `QwenCompactSelector` is experiment-only and maps
all invalid/empty/transport/schema/out-of-candidate outcomes to
`TECHNICAL_UNAVAILABLE`. `ConservativeDecisionPolicy` has no auto-accept
action. Existing canonical KG population still requires an approved ontology
version and remains independent of selector output.

## Status

- IMPLEMENTED: immutable candidate, ambiguity, selector, result, protocol,
  and review-only-policy contracts in `semantic_decision.py`.
- IMPLEMENTED: V2.6-compatible R1/R2 and compact-Qwen adapters.
- IMPLEMENTED: evaluation-only selector comparison/risk-coverage scaffold.
- RUNTIME_BLOCKER: real dense embeddings remain blocked by the recorded
  Windows PyTorch `c10.dll` / WinError 1114 issue.
- DATA_MISSING: no second suitable ontology-pair corpus is bundled.
- NOT_SUPPORTED: automatic Qwen commitment and production selective routing.
