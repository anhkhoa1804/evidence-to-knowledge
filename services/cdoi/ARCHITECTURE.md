# Architecture

## From V0 to V1

V0 passed extracted `EntityCandidate` objects directly through conceptualization and placed their types into the KG immediately after a per-proposal validation call. V1 retains V0's conservative proposal and immutable-foundation policies, but corrects the integration boundary: extracted entities are ABox observations; TBox candidates are separately induced, auditable objects; canonical KG population is conditional on an approved schema version.

## Module model

The loaded stack is intentionally not a rigid L0-L3 chain.

```text
gist adapter (external, read-only, version-pinned)
  -> reusable core modules (identity, party-role, event, measurement, provenance, resource)
  -> separately owned domain modules
  -> bridge modules for cross-domain mappings
  -> canonical knowledge graph
  -> applications
```

The legacy RCA file remains an application artifact but is not loaded by `OntologyStore.load_defaults`. It may use approved core/domain semantics, while temporary RCA hypotheses remain runtime state.

## Data contracts

### Intake boundary MVP

The legacy executable path remains `normalized concept JSON -> CDOI core`. The additive MVP path is `raw manifest package -> deterministic preprocessing -> normalized evidence -> evidence-backed schema candidates`, while explicit glossary terms also continue through a semantic envelope to the existing extractor. The inducer reuses existing class/property candidate contracts and stops at `CANDIDATE_UNREVIEWED`; it does not directly create ontology or KG material. The longer-term architecture remains collectors -> raw evidence store -> normalization -> identity/time correlation -> semantic evidence -> ontology/KG; only constrained file-package normalization and bounded evidence-backed schema induction are implemented.

Inventory yields entity evidence, topology relation evidence, logs event evidence, declared deployments/configuration changes separate change-event evidence, and glossary semantic-term evidence. Change evidence is time-normalized and exact-ID correlated for future read-only temporal queries; it is not RCA or causal inference.

V3 Phase 2.7 additionally implements an immutable, read-only operational evidence context: declared incident window plus normalized inventory/topology/log/change records yields a deterministic EvidenceSnapshot. It uses exact service IDs, inclusive UTC time windows, and explicit DIRECT_ONLY or bounded directed ONE_HOP topology scope. Snapshot selection retains normalized-to-raw-to-source-to-manifest provenance and non-causal selection reasons. A snapshot does not add a schema candidate, proposal, approval, ontology version, or canonical/staging KG assertion.

V3 Phase 2.8 adds optional constrained metric CSV normalization. Metric observations remain distinct from logs and changes; preserve finite numeric value, declared unit, kind, aggregation, sampling metadata, exact target resolution, and a unit/kind/aggregation-aware series key. Snapshot membership uses the same scope and inclusive UTC interval. Metric values are observations only: no anomaly label, trend, counter delta/window total, causal claim, metric-derived schema candidate, data-property candidate, proposal, or KG assertion is implemented. Distributed traces, anomaly detection, candidate-cause generation, RCA ranking, causal inference, and commitment calibration remain unimplemented.

V3 Phase 2.9 adds optional constrained trace-span JSONL normalization and a read-only execution graph. Trace span evidence preserves explicit trace/span identity, exact service identity, UTC start/end/duration, status, kind, sampling state, and declared parent hierarchy. Trace graph edges are only declared parent-to-child execution evidence; partial samples, missing parents, cycles, fan-out, and multiple roots remain visible. Static topology is not an execution path, and execution traversal is not a causal path. Traces create no ontology/schema candidates, data properties, topology mutations, proposals, approvals, or KG assertions. Incident Evidence Graph construction, candidate cause representation, RCA ranking, and causal inference remain unimplemented.

V3 Phase 2.10 adds an incident-scoped, reproducible IncidentEvidenceGraph built from EvidenceSnapshot only, followed by unranked CauseCandidate eligibility records. The graph fuses typed entity, event, change, metric, static topology, and trace-span evidence without mutating canonical KG or ontology. Candidates retain explicit deterministic rules, supporting/context/contradictory evidence roles, and CANDIDATE_UNEVALUATED status; they have no score, rank, probability, or root-cause conclusion. Hypothesis scoring, RCA ranking, causal inference, and root-cause selection remain unimplemented.

`SemanticCandidateGraph` contains ABox `EntityCandidate` and `RelationCandidate` observations with source span evidence. `DeterministicSchemaInducer` creates `ClassCandidate`, `ObjectPropertyCandidate`, and `DataPropertyCandidate` values. Each schema candidate records supporting ABox IDs, type hints, relation signature, provenance, and evidence. This trace is persisted in every `IntegrationRun` directory.

`ConceptProfile` is a conceptualization result for a schema candidate, never for an instance directly. Class and property retrieval/alignment run through separate paths. `OntologyCandidate` exposes lexical, embedding, structural, and relation-signature components.

## Integration workflow

1. Preprocess and extract ABox observations.
2. Persist raw candidate graph and source evidence under a generated `run_id`.
3. Induce typed TBox candidates.
4. Conceptualize, retrieve from foundation/core/current-domain modules, and align locally.
5. Build immutable ontology/property proposals and validate them with policy checks, `TaxonomyReasoner`, real pySHACL, and impact analysis.
6. Persist `ProposalState`, including review decision, validation report, final mapping state, and eventual ontology version.
7. Commit all approved material proposals for a source as one batch version. Per-proposal commits remain available through `ProposalApplier.apply` for debugging.
8. Populate only approved ABox type mappings into the canonical KG and annotate them with the approved version. Keep all other observations in the staging KG.
9. Run controlled cross-domain mapping discovery over relevant domain evidence and emit bridge proposals. Review/commit them independently.
10. Run core promotion separately from persisted domain candidates plus bridge evidence.

## Safety policy

The foundation cannot be modified. `ADD_EQUIVALENCE` is very high risk and review-gated. Label equality across domains becomes unresolved unless stronger evidence is supplied by a future calibrated policy. Bridge mappings are not equivalence mappings. Promotion does not merge or remove existing concepts.

`ImpactAnalyzer` reports affected taxonomy neighbours, properties, mappings, constraints, and detectable instance typings before a high-risk review. The portable default reasoner performs taxonomy-cycle analysis; stronger DL reasoners remain adapter candidates rather than mandatory infrastructure.

## Persistent state and replay

`data/integration_runs/run-*/run.json` records run status and source/version context. Its `proposals/` files persist pending review decisions across restarts. `VersionStore` writes snapshots and deltas, with `run_id`, all proposal IDs, and per-proposal validation details for batch commits. Re-ingestion is idempotent for the deterministic fixtures: already represented local schema candidates become `NO_CHANGE` and do not alter module triples.

## Entity resolution

The resolver is explicitly downstream of approved schema mapping. The deterministic baseline only emits a same-entity candidate for identical source identifiers and never writes `owl:sameAs`. This preserves the distinction between entity identity and ontology alignment.

## V2 Experimental Layer

`ExperimentRunner` sits outside the integration core. It consumes manifests, benchmark adapters, and persisted CDOI artifacts; it does not change how ontology proposals are created or approved. CDOI-Bench has development and held-out test splits, while external benchmark adapters require separately acquired data and transformations.

```text
manifest -> calibration on dev -> frozen thresholds -> held-out evaluation
         -> persisted predictions/metrics/report -> comparison across baselines
```

Baselines expose B0 lexical, B1 embedding signal, B2 lexical plus embedding, B3 structural context, and B6 full conservative CDOI. B4/B5 are optional structured-output LLM comparisons through the existing cached adapter boundary. The runner records feature flags, separate score components, random seed, prompt version, model identifiers, data hash, timing, cache/call counters, and git commit where available.

The controlled downstream evaluator compares raw/native, extracted, domain-aligned, full-CDOI, and full-without-bridge graphs. It reports synthetic business-impact, RCA ranking, query, explanation-path, competency-question, provenance, and staging-leakage measures. It is intentionally an experimental fixture, not evidence of real-world task improvement.
