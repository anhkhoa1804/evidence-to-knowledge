# V3 Selector Contract

`src/cdoi/semantic_decision.py` defines the Phase-1 contract.

`CandidateSet` is immutable and has source/profile reference, ordered
`CandidateEvidence`, retriever/version/index metadata, and deterministic
artifact hash. It cannot contain gold/reference/correctness fields. Original
rank order is preserved; opaque presentation handles (`C01`, `C02`, ...) map
only at presentation time.

`AmbiguityEvidence` contains observable top-1/top-2 score/margin, top-K spread,
candidate count, profile completeness, R1/R2 disagreement and structural
evidence availability. It is diagnostic evidence only; no margin cutoff is a
V3 routing or commitment rule.

`SemanticSelector.select(source_profile, candidate_set, evidence)` returns a
`SelectionResult` with exactly one of:

- `SELECTED`: candidate and relation are required.
- `SEMANTIC_ABSTAIN`: candidate and relation are absent after a valid response.
- `TECHNICAL_UNAVAILABLE`: candidate and relation are absent after a failure.

Phase-1 adapters are `R1DeterministicSelector`, `R2DeterministicSelector`, and
experiment-only `QwenCompactSelector`. R2 preserves the V2.6 tie breaker:
descending `r2_combined_score`, then candidate ID. Qwen protocol metadata is
explicit: `QSEM_V1`, `QSEM_COMPACT_PROFILE_V1`,
`candidate_id_relation_v1`, response budget, bounded retry policy and model
identifier. No selector has permission to commit ontology/KG state.

`EvidenceAssembler` supplies labels, aliases, definitions, parents, children,
and properties only when present. It neither fabricates missing values nor
accepts reference fields. The QSEM snapshot test asserts included fields,
candidate order, opaque-handle mapping, schema text, and gold/reference
absence; it does not assert model output.

The frozen QSEM V1 compact payload currently serializes label, aliases,
parents, children, and properties. It does not serialize definitions. That is
a protocol fact, not an absence of preserved source evidence: a Qwen
definition-ablation requires a separately versioned future prompt protocol and
cannot be silently folded into V3 Phase 2.6.

## SourceEvidence preservation contract

`SourceEvidence` is an experiment-safe preservation record, not a selection
or policy object. It carries source-available field values with their raw
annotation provenance and profile-condition version. Reference/gold fields are
forbidden. A selector must explicitly choose which fields it consumes through
`EvidenceAssembler` or its fixed representation serialization. Therefore a
field can be faithfully preserved while R1/R2 ignore it, and no preserved
field can bypass review, approval, versioning, or canonical-KG gates.
