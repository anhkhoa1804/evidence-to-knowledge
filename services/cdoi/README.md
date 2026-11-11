# Cross-Domain Continual Ontology Integration (CDOI)

CDOI is a Python research prototype for safely building and evolving an enterprise knowledge graph across multiple domains. Rather than turning raw text directly into an ontology, it separates evidence extraction, schema induction, ontology alignment, bridge mappings, human review, versioning, and KG population. The current work also evaluates evidence-aware candidate generation for root-cause-analysis (RCA) data without allowing experimental results to alter the canonical ontology or KG.

## What this repository contains

| Area | Purpose |
| --- | --- |
| `src/cdoi/` | Integration pipeline, CLI, semantic decision logic, validation, evaluation, and RCA evidence tooling. |
| `ontologies/` | Versioned RDF/Turtle ontology modules: foundation, core, domain, application, and bridge layers. |
| `config/` | Project configuration and policy inputs. |
| `tests/` | Offline, deterministic unit and experiment tests. |
| `docs/`, `experiments/` | Architecture, protocols, experiment manifests, evidence, and research gates. |
| `data/` | Small versioned fixtures and ontology artifacts. Downloaded external corpora and generated runtime outputs are intentionally ignored. |

## Safety model

The system is intentionally conservative. Candidate matches are evidence, not facts: automatic retrieval scores alone cannot create cross-domain equivalence; unvalidated or unapproved proposals remain in staging; and every approved change is reviewable and versioned. Experimental RCA hypotheses are separate runtime artifacts and do not establish causality or modify the ontology/KG.

## Run

```powershell
python -m venv .venv
python -m pip --python .\.venv\Scripts\python.exe install -e ".[dev,validation]"
.\.venv\Scripts\cdoi demo
.\.venv\Scripts\python -m pytest
```

The default demo has no credentials, GPU, or remote-model dependency. It writes run journals under `data/integration_runs`, immutable snapshots/deltas under `data/ontology_versions`, the canonical KG at `data/outputs/knowledge_graph.ttl`, and pending/rejected facts at `data/outputs/staging_knowledge_graph.ttl`. These local outputs are excluded from Git; `.env.example` documents optional gateway settings without secrets.

For a first orientation, read [the architecture](ARCHITECTURE.md), then [the V3 architecture](docs/V3_ARCHITECTURE.md). For benchmark data that is not stored in Git, follow [the external-data setup guide](data/benchmarks/external/README.md).

## V1 semantic boundaries

- **ABox extraction vs TBox induction:** `pod-32` is an ABox observation. A `Kubernetes Pod` class candidate is induced separately from type hints, relation signatures, source context, and evidence. Every schema candidate records the source ABox IDs and evidence that support it.
- **Ontology alignment vs entity resolution:** `CustomerRole` versus `SubscriberRole` is schema alignment. `customer_123` versus `subscriber_456` is entity resolution. The baseline resolver never writes `owl:sameAs` from weak evidence.
- **Bridge mapping vs shared abstraction vs equivalence:** a commerce-to-logistics `fulfilledBy` bridge is an independently owned mapping. It does not assert identity, equivalence, or a shared abstraction. Core promotion is a separate reviewable proposal and never deletes domain concepts.
- **Canonical KG vs staging KG:** a type/property mapping reaches the canonical KG only after a valid, approved ontology version. Invalid, unresolved, and review-pending facts remain in staging.

## Architecture

```text
External Foundation (version-pinned, immutable)
        |
Enterprise Core modules: identity | party-role | event | measurement | provenance | resource
        |
Domain modules: distributed systems | commerce | logistics | finance | fintech | telecom
        |                         \
Bridge modules --------------------> explicit, independently owned mappings
        |
Approved schema mappings -> Canonical KG -> Applications
                         \
                          -> Staging KG (pending/rejected/unresolved)
```

RCA is an application concern, not a mandatory L3 ontology layer. Reusable concepts such as Observation and Evidence live in core modules; temporary hypotheses and rankings remain runtime objects unless a query/persistence need is established.

## Pipeline

```text
Source -> Preprocess -> Extract ABox candidates -> Persist evidence
       -> Induce class/object-property/data-property candidates -> Conceptualize
       -> Local retrieval/alignment (foundation + core + current domain)
       -> Controlled cross-domain mapping discovery -> Bridge proposal
       -> Validate (policy + taxonomy reasoner + pySHACL) -> impact analysis
       -> review gate -> batch version commit -> approved mapping
       -> entity-resolution boundary -> canonical KG population
```

Promotion runs after ingestion, using persistent domain-schema evidence and bridge evidence. It produces immutable proposals and does not silently alter domain modules.

## Evaluation

`data/benchmark/gold.json` is a compact gold set covering class, object-property, data-property, bridge, unsafe-equivalence, unresolved, subclass, and new-concept cases. Metrics cover false-merge rate, property alignment, bridge precision, promotion precision, review rate, validation failures, and the V0 alignment measures. `order_sensitivity_experiment` runs isolated ingestion permutations and reports mappings, duplicates, promotions, false merges, versions, bridge counts, and final module structure.

## Optional adapters

`OpenAICompatibleLLM` and `CachingLLMClient` are structured-output adapters. `HashingEmbeddingProvider` is a deterministic ablation baseline; a local or hosted embedding provider can replace it through the retrieval interface. Scores remain visible separately, and lexical/embedding scores alone cannot produce cross-domain equivalence.

## V2 Experiments

V2 freezes the semantic architecture and adds a reproducible evaluation layer. Run deterministic experiments with `cdoi experiment experiments/configs/b6_full_cdoi.yaml`, `continual_orders.yaml`, or `downstream.yaml`. Each output records the manifest, split dataset hash, calibration on the development split, held-out predictions, component configuration, seed, ontology starting version, bootstrap interval, and zero-cost/no-call operational counters for deterministic runs.

`data/benchmarks/cdoi_bench` is project-specific synthetic evaluation data, not production input or a claim about enterprise data. `data/benchmarks/EXTERNAL_SETUP.md` documents adapters for externally obtained OET-style, OAEI-style, LLMs4OL, and RCAEval-compatible data. `data/benchmarks/ONBOARDING.md` documents the separate production onboarding contract.

## V2.5 Evaluation

V2.5 freezes the semantic core and adds failure-driven evaluation around it. `cdoi experiment` accepts manifests for evidence degradation, deterministic noise, late evidence, expanded order sensitivity, optional local sentence-transformer embeddings, and license-aware external OAEI, concept-placement, and RCAEval adapters.

The default test/demo path remains offline and credential-free. External data, model weights, and LLM credentials are never silently downloaded or required; unavailable configurations persist a clear `skipped` result. See [EVALUATION.md](EVALUATION.md), [BENCHMARKS.md](BENCHMARKS.md), and [external setup](data/benchmarks/external/README.md). Synthetic validation is not external validation; embedding signal is not a real embedding model; controlled fixture performance is not enterprise performance; and external benchmark performance is not proof of production readiness.

## V2.6 Execution Status

V2.6 adds safe OpenAI-compatible model configuration, `cdoi model probe`, bounded structured-output retries, secret-free cache metadata, and external-run reporting. Company gateway settings are read only from `CDOI_LLM_*` variables and the API key named by `CDOI_LLM_API_KEY_ENV`; `.env.example` contains placeholders only. The project remains credential-free by default: missing credentials, unavailable data, and incompatible optional model runtimes become persisted `skipped` results rather than test or demo failures.

The V2.6 OAEI Anatomy run is a reference-positive-pair abstention experiment, not a full OAEI matcher. Its result must not be read as precision, false-merge rate, or production performance. See [V2_6_RESULTS.md](experiments/V2_6_RESULTS.md) and [FAILURE_ANALYSIS.md](experiments/FAILURE_ANALYSIS.md) for the executed scope, limitations, and observed external-validity gap.

## V3 Semantic-Decision Phase 1

V3 freezes the V2.6.6 diagnostic baseline and adds an experiment-only,
behavior-preserving separation between candidate retrieval, ambiguity evidence,
semantic selection, technical unavailability, commitment-confidence protocol,
and review-only decision policy. It does not change normal ingestion, the 0.82
frozen evaluator threshold, validation/review/commit rules, or canonical KG
population. See [V3 architecture](docs/V3_ARCHITECTURE.md), [selector
contract](docs/V3_SELECTOR_CONTRACT.md), and
[V3 research gate](experiments/V3_RESEARCH_GATE.md).

## V3 Phase 2 Evidence Acquisition

Phase 2 preserves the Phase-1 policy boundary and records reproducibility,
frozen-artifact interface parity, raw-versus-extracted profile evidence, dense
runtime status, second-domain qualification, and relation-diversity gaps. See
[reproducibility baseline](experiments/V3_REPRODUCIBILITY_BASELINE.md) and the
[Phase-2 research gate](experiments/V3_PHASE2_RESEARCH_GATE.md).

## V3 Phase 2.5 Source-Faithful Evidence Recovery

Phase 2.5 evaluates raw, provenance-preserved OBO synonym and definition
annotations through experiment-only profile conditions. It leaves `_profiles`,
normal ingestion, R1/R2, review/commit, canonical-KG behavior, routing, and
commitment calibration unchanged. See the [profile enrichment
report](experiments/V3_PHASE2_5_PROFILE_ENRICHMENT.md) and [Phase-2.5 research
gate](experiments/V3_PHASE2_5_RESEARCH_GATE.md).

## V3 Phase 2.6 Representation Validation

Phase 2.6 versions an RDF annotation-object resolution correction after finding
that Phase-2.5 had retained local annotation-node IDs rather than their labels.
Historical Phase-2.5 artifacts remain intact. The corrected profiles and
selector evidence are experiment-only; dense runtime, Qwen access, external
validation, routing, and commitment calibration remain separately gated. See
the [Phase-2.6 research gate](experiments/V3_PHASE2_6_RESEARCH_GATE.md).

The Phase-2.6 follow-up adds deterministic residual-error diagnostics and a
Linux/WSL Dense smoke/full-run contract. It does not alter profiles in
production, QSEM V1, policy, routing, calibration, review, or canonical-KG
behavior. See the [follow-up gate](experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md).

## Current research track

The V3 Phase 2.10--2.12 track applies the same evidence and safety boundaries
to RCA evaluation. Phase 2.10 constructs an incident evidence graph; Phase
2.11 generates deterministic, unranked cause candidates; and Phase 2.12
records a preregistered holdout-integrity check before evaluation. These are
research artifacts only: they do not rank root causes, prove causality, or
change production ingestion, review, ontology versions, or canonical-KG
population. See the [Phase 2.10 evidence graph](experiments/V3_PHASE2_10_INCIDENT_EVIDENCE_GRAPH.md), [Phase 2.11 report](experiments/V3_PHASE2_11_REPORT.md), and [Phase 2.12 integrity record](experiments/archive/v3_phase2_12/PRE_HOLDOUT_INTEGRITY.json).
