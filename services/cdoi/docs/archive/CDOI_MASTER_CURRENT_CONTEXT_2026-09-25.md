# CDOI Master Current Context — 2026-09-25

> Historical handoff only. It describes the 2026-09-25 worktree and is superseded for current-state claims by `docs/archive/CDOI_V3_FINAL_SNAPSHOT_2026-09-28.md` and the independently verified closure archive. Preserve the observations below as dated history; do not treat old runtime, data, or test-count statements as current.

## Purpose, audit basis, and authority

This is the self-contained handoff and current source of truth for **Cross-Domain Continual Ontology Integration (CDOI)** as audited on 2026-09-25. It is written for a new engineer or AI session with no chat history.

Authority order used in this document is:

```text
latest live source and artifacts
  > latest final report / research gate
  > CDOI_CURRENT_VERIFICATION_MATRIX.md
  > current snapshots and handoffs
  > historical reports
```

Paths below are repository-relative. An artifact described as frozen is evidence for its recorded run, not necessarily a release of the entire working tree.

**Repository caveat.** At audit time the worktree had 139 changed/untracked entries, including the current verification matrix, 2026-09-25 ontology/gateway/VDT artifacts, and newly added source/tests; `tools/run_v3_phase2_12.py` was modified. Therefore the current research state is usable and audited, but is **not an immutable committed/released baseline**. Do not erase, reset, overwrite, or silently normalize those artifacts. See `git status --short` and `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md`.

### Evidence labels used throughout

- **IMPLEMENTED FACT** — source and deterministic tests/contracts exist; this does not assert research validity.
- **MEASURED RESULT** — a scoped experimental outcome with the named population and artifact.
- **DIAGNOSTIC INTERPRETATION** — a bounded inference from measured evidence, not a causal/prod conclusion.
- **RESEARCH HYPOTHESIS** — plausible but not established; it must not be operationalized as fact.
- **PRODUCTION POLICY** — a safety boundary or authorization decision, not an accuracy result.

## Executive summary

CDOI is a Python research prototype for conservative, continual integration of heterogeneous enterprise ontology/KG sources. Its product aspiration is a governed system that can turn source evidence into auditable schema proposals, align them safely, obtain human approval, version approved ontology changes, and populate a canonical knowledge graph without converting similarity into identity or automatic commitment. `README.md`, `ARCHITECTURE.md`, and `docs/CDOI_USER_INPUT_CONTRACT.md` are the architectural starting points.

The research program additionally evaluates whether operational evidence can produce bounded, auditable RCA candidate sets and assist a read-only investigator. The ontology and RCA tracks deliberately share provenance and safety concepts but remain separate at runtime. There is no authorized production RCA pipeline and no automatic ontology/KG mutation from a model or RCA result.

Current maturity: **research prototype with a mature deterministic safety/contract layer, partially supported external ontology evidence, and technically/data-blocked RCA quality evidence.** It is not production-ready, not a causal RCA system, and not an auto-commit ontology system.

## Authoritative architecture

### Ontology / semantic branch

```text
raw package or normalized semantic input
  → deterministic preprocessing / extraction
  → ABox EntityCandidate + RelationCandidate evidence graph
  → persisted provenance and SemanticCandidateGraph
  → TBox induction: Class/ObjectProperty/DataProperty candidates
  → ConceptProfile and immutable CandidateSet retrieval
  → ambiguity evidence (margin/spread; evidence only)
  → SemanticSelector result / proposal candidate
  → policy + taxonomy + pySHACL + impact validation
  → review decision
  → batch version commit only for approved material
  → canonical KG population with approved ontology version
       otherwise: staging KG / unresolved / rejected material

independent cross-domain mapping discovery → bridge proposal → separate review/commit
persisted domain + bridge evidence → conservative core-promotion proposal → review
```

**IMPLEMENTED FACT:** extraction observations are ABox evidence; schema candidates are induced separately. Retrieval produces a CandidateSet; selection is a later step; commitment is later still. `ARCHITECTURE.md`, `src/cdoi/models.py`, `src/cdoi/semantic_decision.py`, `src/cdoi/pipeline.py`.

**PRODUCTION POLICY:** foundation ontology is external/read-only/version-pinned; high-risk equivalence, bridge, promotion, and canonical writes remain review/version controlled. Cross-domain mapping is not equivalence; entity resolution is downstream of approved schema mapping and does not write `owl:sameAs` from weak evidence. `ARCHITECTURE.md`, `src/cdoi/versioning.py`, `src/cdoi/kg.py`.

### Operational / RCA branch

```text
inventory + topology + logs + metrics + traces + changes + declared incident window
  → normalized operational evidence, exact IDs, UTC normalization, provenance
  → immutable EvidenceSnapshot (DIRECT_ONLY or bounded directed ONE_HOP)
  → IncidentEvidenceGraph (typed observation graph, not a causal graph)
  → deterministic unranked CauseCandidate eligibility records
       H0 frozen baseline
       H1 metric level shift
       H2 trace participation shift
       H3 bounded topology expansion
       H4 pre-cutoff change context
       H5 combined families
  → CandidateEvidenceProfile and bounded read-only evidence tools
  → optional RCA agent report: RCA_HYPOTHESIS / INSUFFICIENT_EVIDENCE / TECHNICAL_FAILURE

No arrow from this path writes ontology, proposal approval, canonical KG, remediation,
or a causal/root-cause fact.
```

**IMPLEMENTED FACT:** `EvidenceSnapshot`, `IncidentEvidenceGraph`, unranked `CauseCandidate`, profile generation, SQLite evidence views and read-only tool contracts exist. `src/cdoi/operational_context.py`, `src/cdoi/incident_evidence_graph.py`, `src/cdoi/hypothesis_generation.py`, `src/cdoi/candidate_evidence_profile.py`, `src/cdoi/rca_investigation.py`, `src/cdoi/scalable_evidence.py`.

**PRODUCTION POLICY:** an evidence graph is not the canonical KG; trace traversal is not a causal path; metric degradation is not anomaly proof; temporal precedence is not causality; a candidate is not a root cause.

### Intended convergence

The branches may eventually reuse approved ontology/core semantics for governed operational query and explanation. Today they converge only at safe interfaces: common provenance/identity concepts and a possible future read-only semantic context. RCA hypotheses cannot promote ontology terms, and ontology alignment cannot serve as RCA causality. `ARCHITECTURE.md` explicitly keeps RCA as an application concern rather than mandatory ontology layer.

## Repository map and current authorities

| Area | Key files/directories | Responsibility and authority |
| --- | --- | --- |
| Project orientation | `README.md`, `ARCHITECTURE.md`, `docs/V3_ARCHITECTURE.md` | Architecture and safety model; live source plus current artifacts override historical wording. |
| Semantic core | `src/cdoi/models.py`, `semantic_decision.py`, `retrieval.py`, `alignment.py`, `pipeline.py`, `validation.py`, `versioning.py`, `kg.py` | Candidate contracts, retrieval/selection separation, validation/review/version/KG behavior. |
| Ontologies | `ontologies/foundation`, `core`, domain folders, `bridges`, `applications/rca` | Versioned foundation/core/domain/bridge TTL modules. `applications/rca/rca.ttl` is not loaded as a mandatory core layer. |
| Input/preprocessing | `src/cdoi/raw_preprocessing.py`, `evidence_schema.py`, `operational_context.py`, `trace_evidence.py` | Constrained raw-package adapters, schema induction bridge, context and trace contracts. |
| RCA research | `incident_evidence_graph.py`, `hypothesis_generation.py`, `scalable_evidence.py`, `candidate_evidence_profile.py`, `rca_investigation.py`, `rca_agent_v2.py`, `rca_agent_v2_1.py` | Non-causal evidence/candidate/agent paths. |
| Model/gateway | `qwen_rca*.py`, `provider_output.py`, `gateway_observability.py`, `company_gateway.py` | Bounded OpenAI-compatible provider, output normalization, safe request correlation. |
| Benchmarks | `data/benchmarks/`, `BENCHMARKS.md`, `EVALUATION.md`, `data/benchmarks/external/README.md` | Fixtures, adapters and external-data qualification constraints. |
| Tests | `tests/`, particularly `tests/v3/` and `tests/unit/` | Contract/regression tests; passing tests are not semantic/RCA validity. |
| Current verification index | `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md` | Live subsystem status matrix; primary reconciliation reference. |
| Latest semantic evidence | `experiments/archive/v3_ontology_relation_aware_selection_20260925/` | Latest ontology relation gate, metrics, prediction freeze, hashes, regression. |
| Latest RCA/runtime evidence | `experiments/archive/v3_phase2_16_*_20260925/`, `v3_gateway_observability_escalation_20260925/` | Latest V2.1 gateway/payload state. |
| Latest VDT evidence | `experiments/archive/v3_vdt_*_20260925/` | Read-only VDT ingest, temporal/label diagnosis and acquisition requirements. |

## Core object and contract glossary

| Contract | Meaning and boundary | Authority |
| --- | --- | --- |
| `EntityCandidate`, `RelationCandidate`, `SemanticCandidateGraph` | ABox source observations with evidence/provenance; not schema assertions. | `src/cdoi/models.py` |
| `ConceptProfile` / “SemanticProfile” | Current code name is `ConceptProfile`: conceptualization of a **schema** candidate. “SemanticProfile” in older notes is not a separate authoritative runtime object. | `src/cdoi/models.py`, `ARCHITECTURE.md` |
| `CandidateSet` | Immutable retrieved ontology alternatives plus score/evidence context. It does not choose or commit a mapping. | `src/cdoi/semantic_decision.py` |
| Retrieval | Candidate generation/ranking over foundation/core/current domain. Retrieval miss must be reported separately from selection error. | `src/cdoi/retrieval.py`, `semantic_decision.py` |
| Ambiguity evidence | Margin/spread and related diagnostics. It is evidence, not calibrated confidence or automatic routing. | `src/cdoi/semantic_decision.py`, `experiments/V3_RESEARCH_GATE.md` |
| `SemanticSelector` | Selector protocol; R1/R2 deterministic, Dense optional, Qwen compact proposal adapter. | `src/cdoi/semantic_decision.py` |
| `SelectionResult` | Selection outcome with reason/evidence; no approval by itself. | `src/cdoi/semantic_decision.py` |
| `CommitmentConfidence` | Protocol/scaffold for a later confidence mechanism. It is explicitly uncalibrated and cannot authorize commitment. | `src/cdoi/semantic_decision.py`, `docs/V3_COMMITMENT_CONFIDENCE_PROTOCOL.md` |
| Ontology proposal | Immutable proposed mapping/schema change, followed by validation, review state and eventual version association. | `src/cdoi/proposals.py`, `pipeline.py` |
| `EvidenceSnapshot` | Immutable incident-scoped, exact-ID, inclusive-UTC observation selection with declared topology scope. | `src/cdoi/operational_context.py` |
| `IncidentEvidenceGraph` | Reproducible typed incident graph fusing context evidence. It is not a causal graph or KG mutation. | `src/cdoi/incident_evidence_graph.py` |
| `CauseCandidate` | Deterministic eligibility hypothesis with supporting/context/contradictory evidence and `CANDIDATE_UNEVALUATED`; no score/rank/probability/root-cause conclusion. | `src/cdoi/incident_evidence_graph.py` |
| H0–H5 | Fixed candidate-generation families: H0 frozen baseline; H1 metric; H2 trace; H3 topology; H4 change; H5 combined. Constants are configuration, not learned scores. | `src/cdoi/hypothesis_generation.py`, `experiments/V3_PHASE2_11_REPORT.md` |
| `CandidateEvidenceProfile` | GT-free deterministic profile of evidence, missing modalities and resolvable IDs for a candidate. It has no causal probability. | `src/cdoi/candidate_evidence_profile.py` |
| `RCAReport` | Strict report status and cited candidate/evidence-ID validation. A technical failure is distinct from an abstention. | `src/cdoi/rca_investigation.py` |
| Agent V0 | Provider-neutral, read-only, budgeted historical orchestration. | `src/cdoi/rca_investigation.py` |
| Agent V2 | H1-profile preload / H1→H5 fallback design; historical implementation has a discovered fail-open default-abstention bypass. | `src/cdoi/rca_agent_v2.py`, `experiments/archive/v3_phase2_16_agent_v2_development_retry_20260924/FINAL_REPORT.md` |
| Agent V2.1 | Separately versioned V2 policy with fail-closed raw status validation and one repair bound; deterministic contract supported, live quality unmeasured. | `src/cdoi/rca_agent_v2_1.py` |

## Current input and data contracts

### Ontology/semantic inputs

- Legacy executable input: normalized concept JSON.
- Additive MVP: raw manifest package → deterministic preprocessing → normalized evidence → evidence-backed schema candidates.
- Inventory produces entity evidence; topology produces declared relations; logs produce event evidence; changes/deployments produce change event evidence; glossary produces semantic terms. Exact identifiers and source spans/provenance are retained.
- Induction is deliberately bounded: generic service type, bounded relations and glossary terms; it is not arbitrary ontology learning. `ARCHITECTURE.md`, `src/cdoi/raw_preprocessing.py`, `src/cdoi/evidence_schema.py`.

### Operational package

- Inventory, topology, logs, metrics CSV, trace-span JSONL, change/deployment records, incident declaration and glossary are optional constrained adapters.
- Metrics preserve finite value, declared unit/kind/aggregation/sampling and series key. Counters and unit conflicts are guarded in H1 eligibility.
- Traces preserve trace/span/parent identity, service, start/end/duration, status, kind and sampling. Missing parents, cycles/fan-out/roots remain visible.
- Snapshot scope is exact service identity, inclusive UTC interval and `DIRECT_ONLY` or bounded directed `ONE_HOP`; no fuzzy identity/alias merge exists.
- Current limits: no generic collectors, no application-host binding, no instance/config-profile/known-problem/procedure/business-impact ingestion, no distributed causal model, no production onboarding execution. `docs/CDOI_USER_INPUT_CONTRACT.md`, `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md`.

### Benchmark adapters

OAEI, concept placement/OET and RCAEval adapters require local, license-aware acquisition plus source/release/checksum/transformation/split manifest. They are not silently downloaded and do not alter CDOI ontology schemas. `data/benchmarks/external/README.md`, `BENCHMARKS.md`.

## Chronological research history

### V1 and V2 foundations

- **V1 — IMPLEMENTED FACT:** corrected V0’s direct entity-to-KG behavior by separating ABox extraction, TBox induction, review/versioned ontology approval and canonical-vs-staging KG population. `ARCHITECTURE.md`.
- **V2 — MEASURED RESULT:** created reproducible manifests, project-owned synthetic CDOI-Bench, robustness/order/late-evidence tests and benchmark adapters. Controlled CDOI-Bench is mechanism/safety evidence only.
- **V2.5 — IMPLEMENTED FACT:** froze semantic core and added failure-driven evaluation, optional model adapters and external adapters. No model/download is required for default offline path. `EVALUATION.md`, `experiments/V2_5_RESULTS.md`.
- **V2.6–V2.6.6 — MEASURED RESULT:** OAEI Anatomy diagnostic revealed severe external-validity gap. The original pair-only positive-reference protocol reported B0 lexical positive-reference recall 0.6339 over 7,580 and B6 full CDOI 0.0; it cannot measure precision/F1/false merges. Controlled CDOI-Bench F1=1.0, N=14 must not be compared as enterprise performance. `experiments/V2_6_RESULTS.md`.
- **Historical conflict and resolution:** Phase 2.5 initially interpreted synonym enrichment, but preserved RDF annotation-object IDs rather than labels. Phase 2.6 corrected/versioned annotation-object resolution; Phase 2.5 synonym-utility conclusions are not authoritative. `experiments/V3_PHASE2_6_RESEARCH_GATE.md` is authoritative over `V3_PHASE2_5_*` interpretation.

### V3 semantic research

- **Phase 1 — IMPLEMENTED FACT:** behavior-preserving separation of CandidateSet retrieval, ambiguity evidence, selection, technical unavailability, confidence protocol and review-only policy; normal ingestion/commit/KG behavior unchanged. Frozen deterministic selector parity was measured on 1,497 Anatomy cases. `experiments/V3_RESEARCH_GATE.md`, `experiments/V3_PHASE1_INTERFACE_PARITY.md`.
- **Phase 2 — MEASURED/DIAGNOSTIC:** reproducibility, profiles, Dense/Qwen readiness, relation-diversity and second-domain gap audit. Dense and Qwen did not become production routes. `experiments/V3_PHASE2_RESEARCH_GATE.md`.
- **Phase 2.5 — MEASURED RESULT, historically corrected:** source-faithful OBO aliases/definitions were inspected. Before correction, enriched diagnostic P1-P0 full-corpus R@1=-0.0180 and fixed-Top-20 selection delta=-0.0040; no policy changed. `experiments/V3_PHASE2_5_RESEARCH_GATE.md`.
- **Phase 2.6/follow-up — MEASURED RESULT:** corrected synonym extraction yielded P1-P0 fixed-Top-20 delta +0.0294; definition utility remained unsupported because definitions are one-sided (Mouse mapped cases lack them). Residual difficult population N=138: 127 missing-source-synonym, 50 missing-target-synonym, 128 structural signal present (overlapping labels); 52 wrong→correct and 8 correct→wrong transitions. This is diagnostic only. `experiments/V3_PHASE2_6_RESEARCH_GATE.md`, `experiments/V3_PHASE2_6_RESIDUAL_ERROR_TAXONOMY.md`.
- **External DH/iDAI–PACTOLS — MEASURED RESULT:** qualified before scoring: iDAI English 1,311 SKOS concepts, PACTOLS English 60, six usable equivalence mappings to five targets. It supported only narrow second-pair retrieval evidence; relation diversity, calibration and broad replication remained absent. `experiments/V3_EXTERNAL_DH_PAIR_QUALIFICATION.md`, `experiments/V3_EXTERNAL_DH_RESEARCH_GATE.md`.
- **2026-09-25 ontology blocker resolution — MEASURED RESULT:** selected STW–TheSoz, froze all-source candidate sets before GT parsing, and established data relation diversity. Dense remained not run; QSEM remained unavailable. `experiments/archive/v3_ontology_blocker_resolution_20260925/FINAL_REPORT.md`.
- **2026-09-25 relation-aware selection — MEASURED RESULT:** evaluated deterministic proposal-only relation classification on frozen STW–TheSoz targets. This is the latest ontology authority; details are in the dedicated semantic section below. Gate: `ONTOLOGY_RELATION_DATA_SUPPORTED_SELECTION_PARTIAL`. `experiments/archive/v3_ontology_relation_aware_selection_20260925/RESEARCH_GATE.json`.

### V3 operational/RCA research

- **2.7 — IMPLEMENTED FACT:** incident `EvidenceSnapshot` context with provenance and bounded topology. `experiments/V3_PHASE2_7_RESEARCH_GATE.md`.
- **2.8 — IMPLEMENTED FACT:** metric normalization and non-causal typed observations. `experiments/V3_PHASE2_8_RESEARCH_GATE.md`.
- **2.9 — IMPLEMENTED FACT:** trace normalization/execution graph; no causal traversal. `experiments/V3_PHASE2_9_RESEARCH_GATE.md`.
- **2.10 / 2.10E R1/R2/R2A — IMPLEMENTED FACT / MEASURED RESULT:** IncidentEvidenceGraph and unranked candidates, then RCAEval RE2-OB acquisition/splits/anti-leakage. RCAEval frozen index: 735 cases total; RE2-OB 90 cases, six fault labels × three repetitions × five root-cause services. Static topology, independent changes and glossary were unavailable and were not fabricated. `experiments/V3_PHASE2_10E_RCAEVAL_QUALIFICATION.md`, `experiments/V3_PHASE2_10E_R2A_RESEARCH_GATE.md`.
- **2.11 — MEASURED RESULT:** fixed H0–H5, 12-case development pilot; H0 coverage 0/12, H1 12/12 mean 3.25 candidates, H2 3/12 mean 1.17, H5 12/12 mean 4.0 and 69.23% mean all-service reduction. Candidate artifacts precede GT reads. It is consumed development evidence. `experiments/V3_PHASE2_11_REPORT.md` and archive manifest (35/35 artifacts validated).
- **2.12 — MEASURED RESULT:** preregistered, one-shot 78-case protected holdout. 77 post-freeze cases evaluated; one acquisition failure. H5 cover 77/77, mean 4.0649 candidates, 31.235% candidate-service ratio, 68.765% mean reduction; H5 added no GT recoveries beyond H1 and added mean 1.1688 candidates. Gate is technically incomplete despite integrity because one protected acquisition failed. Do not rerun/tune this holdout. `experiments/archive/v3_phase2_12/HOLDOUT_RESULTS.json`, `RESEARCH_GATE.json`, `PHASE_A_FREEZE.json`, `HASHES.json`.
- **2.13 — IMPLEMENTED FACT:** deterministic CandidateEvidenceProfiles, bounded read-only tools and scripted V0 demonstration; five development-only profiles replayed deterministically with resolvable citations. No live model and no external validation. `experiments/V3_PHASE2_13_REPORT.md`, archive gate.
- **2.14 — IMPLEMENTED FACT / runtime-blocked:** Qwen RCA adapter mock-tested; then no credential/provider was available. Semantic Dense remained blocked; iDAI–PACTOLS was still six equivalence mappings. `experiments/V3_PHASE2_14_REPORT.md`.
- **2.15 — MEASURED RESULT:** internal Qwen V1 runtime/tool capability qualified (12/12 bounded interactions), but the frozen 12-case development batch yielded no accepted hypotheses and no tool/fallback activity. Final gate: `QWEN_RUNTIME_SUPPORTED_RCA_QUALITY_INSUFFICIENT`. `experiments/V3_PHASE2_15_REPORT.md`.
- **2.16 / 2.16R — MEASURED RESULT:** V2 synthetic qualification passed 15/15. First V2 development then retry both became technically incomplete; retry had 10 invalid default abstentions, two transport failures and zero contract-compliant reports. 2.16R then qualified provider output normalization through 10/10 synthetic live probes, but did not measure RCA quality. `experiments/archive/v3_phase2_16_agent_v2/FINAL_REPORT.md`, `experiments/archive/v3_phase2_16_agent_v2_development_retry_20260924/FINAL_REPORT.md`, `experiments/archive/v3_phase2_16r_qwen_output_contract_live_20260924/FINAL_REPORT.md`.
- **V2.1, 2026-09-25 — IMPLEMENTED FACT / RUNTIME BLOCKED:** fail-closed status contract passes deterministic tests. Health ladder pass does not extend to P1-sized full payload. Payload controls identify intermittent non-terminal behavior, not a root cause. `experiments/archive/v3_phase2_16_agent_v2_1_status_contract/RESEARCH_GATE.json`, `v3_phase2_16_agent_v2_1_full_payload_blocked_20260925/RESEARCH_GATE.json`.
- **VDT, 2026-09-25 — MEASURED RESULT:** source-specific read-only ingestion works structurally, but valid incident windows and logs are temporally disjoint and labels are not RCA outcomes. VDT cannot currently validate RCA quality. `experiments/archive/v3_vdt_temporal_label_diagnosis_20260925/FINAL_REPORT.md`.

## Current status matrix

| Subsystem | Current state | What is supported / constrained authority |
| --- | --- | --- |
| ABox/TBox, provenance, proposal/review/version/KG safety | **IMPLEMENTED / SUPPORTED** | Deterministic contracts and safety tests; no automatic approval. |
| Raw operational preprocessing, metrics/traces/context | **IMPLEMENTED / SUPPORTED** | Constrained package adapters, not generic collectors. |
| CandidateSet retrieval and R1/R2 selection | **IMPLEMENTED / SUPPORTED** | Deterministic interface parity; external generalization limited. |
| Dense selector | **SCAFFOLD_ONLY / RUNTIME_BLOCKED** | Interface/tests exist; no valid Dense result. |
| QSEM semantic selector | **EXPERIMENTAL / PARTIALLY_SUPPORTED** | Proposal-only adapter, no authorized external relation-aware runtime. |
| STW exact selection | **PARTIALLY_SUPPORTED** | Source-level parity only, one mapping family. |
| STW broad/narrow/related relation selection | **NOT_SUPPORTED** | Low joint accuracy; no routing/commit. |
| Direction normalization | **IMPLEMENTED / SUPPORTED** | Canonicalization only, not safe semantic selection. |
| Commitment calibration | **SCAFFOLD_ONLY / DATA_BLOCKED** | No independent calibration split/negatives. |
| Incident graph/H0–H5 | **IMPLEMENTED / EXPERIMENTAL** | Candidate generation, not ranking/causality. |
| RCAEval H5 candidate coverage | **MEASURED, NOT PRODUCTION AUTHORIZED** | 77/77 protected candidate coverage; no RCA correctness claim. |
| Candidate profiles/read-only tools | **IMPLEMENTED / DEVELOPMENT_ONLY** | Deterministic + scripted integration. |
| Agent V0 | **EXPERIMENTAL / NOT_SUPPORTED for quality** | Runtime works historically, but V1 did not investigate or produce valid hypotheses. |
| Agent V2 | **PARTIALLY_SUPPORTED** | Synthetic contracts pass; historical default-abstention bypass invalidates quality interpretation. |
| Agent V2.1 | **IMPLEMENTED / RUNTIME_BLOCKED** | Fail-closed deterministic contract; live quality not run. |
| Gateway correlation | **PARTIALLY_SUPPORTED** | Safe local lifecycle and returned IDs, provider internals unavailable. |
| VDT ingest | **PARTIALLY_SUPPORTED** | Exact-ID normalization; temporal/label/provenance blocks evaluation. |
| RCA causality/confidence/ranking | **NOT_IMPLEMENTED / NOT_SUPPORTED** | Agent ordering is at most experimental; no calibrated causal model. |
| Production ingestion/governance/RCA | **PRODUCTION_NOT_AUTHORIZED** | Collectors, governed data, SLOs, calibration, causality and validation absent. |

The detailed live reconciliation is `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md`.

## Ontology / semantic branch in depth

### Anatomy history and residual findings

**MEASURED RESULT:** OAEI Anatomy was acquired locally and heavily used as diagnostic/development evidence. The older V2.6 reference-positive protocol has 7,580 pairs and cannot estimate precision, F1 or false merge risk because it is positive-only and pair-presented. `experiments/V2_6_RESULTS.md`.

**Conflict:** Phase 2.5 reported raw synonym/definition profiles but persisted annotation-object identifiers rather than labels, making synonym-utility claims invalid. Phase 2.6’s resolved RDF labels supersede that interpretation. The newer authority records P1-P0 fixed-Top-20 deterministic delta +0.0294 but keeps definition utility unsupported; it does not authorize profile/routing/policy change. `experiments/V3_PHASE2_5_RESEARCH_GATE.md`, `experiments/V3_PHASE2_6_RESEARCH_GATE.md`.

**MEASURED RESULT:** corrected residual difficult population is N=138, with 3 ties. Observable categories overlap: missing source synonym 127, missing target synonym 50, generic/specific 33, lexical near duplicate 27, and structural signal present 128. The evidence shows distinguishable representation patterns, not that a structural feature or synonym would fix a mapping. `experiments/V3_PHASE2_6_RESIDUAL_ERROR_TAXONOMY.md`.

**DIAGNOSTIC INTERPRETATION:** Anatomy supports profile/extraction diagnostics and deterministic residual characterization, but it is consumed diagnostic/development evidence and cannot establish external generalization, relation competence, calibration or production behavior.

### STW–TheSoz relation-aware experiment: latest authority

**IMPLEMENTED FACT:** relation-aware selection runs only after a frozen target selection. Input excludes mapping predicates, GT targets, labels and evaluation artifacts until `RELATION_PREDICTIONS_FREEZE.json` is written. No retrieval was changed and no proposal can commit. `experiments/archive/v3_ontology_relation_aware_selection_20260925/PREREGISTRATION.json`, `RELATION_SELECTOR_PREREGISTRATION.json`, `ANTI_LEAKAGE_AUDIT.json`.

**MEASURED RESULT:** before conflict filtering, 6,344 mapping rows across 2,475 sources: exact 2,969, broad 1,398, narrow 1,398, related 579. Canonical source→target normalization excluded 37 contradictory pairs for audit. The post-normalization evaluable population is 4,872 rows. `SECOND_ONTOLOGY_RESULTS.json`, `MAPPING_CONFLICTS.json`, `RELATION_RESULTS.json`.

| Gold relation | Evaluated rows | Target Top-1 / R@1 | R@5 | R@20 | Joint target+relation R1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `exactMatch` | 2,932 | 50.4434% | 59.5498% | 65.9618% | 42.1555% |
| `broadMatch` | 33 | 9.0909% | 18.1818% | 24.2424% | 0.0000% |
| `narrowMatch` | 1,349 | 1.7791% | 13.1949% | 26.5382% | 0.2965% |
| `relatedMatch` | 558 | 4.1219% | 14.1577% | 29.2115% | 0.1792% |

**MEASURED RESULT:** comparable historical source-level exact metric is 1,489/2,383 = **62.4843%**, exactly parity with historic frozen baseline. It differs from the 50.4434% per-row value because a source with multiple exact targets is counted once in the source-level “any canonical exact target” definition but once per mapping row in the newer metric. `RELATION_RESULTS.json`.

**MEASURED RESULT:** failure counts include 2,409 GT targets not retrieved, 934 wrong Top-1 target selections, and 28 exact overgeneralizations. R1 hierarchy changed 21 relation proposals, did not change target selection, and only improved a conditional narrow relation diagnostic. `RELATION_FAILURE_ANALYSIS.json`, `RELATION_ABLATION_RESULTS.json`.

**DIAGNOSTIC INTERPRETATION:** non-equivalence failure is principally retrieval plus relation discrimination; relation classification cannot repair a target absent from Top-20. Broad/narrow/related joint accuracy is insufficient for safe selection. Positive-only mappings cannot estimate false-positive rate, specificity, unsafe-mapping probability or calibrated precision.

**PRODUCTION POLICY:** exact target parity, direction canonicalization, or a selector output do not authorize routing, automatic commitment, canonical KG writes, or a broad generalization claim. Latest gate: `ONTOLOGY_RELATION_DATA_SUPPORTED_SELECTION_PARTIAL`; regression: 263 collected, 263 passed, 0 failed/skipped. `FINAL_REPORT.md`, `RESEARCH_GATE.json`, `REGRESSION.json`.

### Dense, QSEM/Qwen, calibration, validity

- **Dense — RUNTIME_BLOCKED:** Windows PyTorch fails `c10.dll` / WinError 1114; no usable WSL, Docker or Podman Linux runtime. No Dense candidate set, accuracy, safety or degradation metric exists. `experiments/archive/v3_ontology_blocker_resolution_20260925/DENSE_RESULTS.json`.
- **QSEM — EXPERIMENTAL/UNRESOLVED:** proposal-only schema/interface exists, but no authorized non-RCA runtime, frozen provider prompt or relation-aware execution. `QSEM_RELATION_AWARE_READINESS.json` in the latest relation archive.
- **Commitment confidence — DATA_BLOCKED:** current STW data has no held-out calibration split or validated negatives. `CALIBRATION_DATA_READINESS.json`.
- **External validity — PARTIALLY_SUPPORTED only:** STW is one external mapping family; iDAI–PACTOLS is six equivalence mappings; Anatomy is consumed diagnostic evidence. A third independently acquired/frozen relation-diverse pair is required to test portability rather than repeat a single family.

## RCA / operational branch in depth

### Phase 2.7 onward and H0–H5

**IMPLEMENTED FACT:** Phase 2.7–2.10 introduced context, metrics, traces, execution evidence and graph/candidate contracts without anomaly labels, ranking or causality. `experiments/V3_PHASE2_7_RESEARCH_GATE.md`, `V3_PHASE2_8_RESEARCH_GATE.md`, `V3_PHASE2_9_RESEARCH_GATE.md`, `V3_PHASE2_10_RESEARCH_GATE.md`.

H0 is frozen Phase 2.10 eligibility. H1 requires within-window metric shift (at least 60 observations per partition, 50% median shift, 60% persistent post-cutoff excursion; counters/unit conflicts excluded). H2 requires at least 100 spans per partition and a 2× local volume shift. H3 makes one declared topology hop; H4 records pre-cutoff change context; H5 combines rules. These are fixed label-independent rules, not causal scores. `experiments/V3_PHASE2_11_REPORT.md`.

**MEASURED RESULT:** SQLite indexed trace aggregation in Phase 2.12 handled the recorded workload without materializing full execution graph: mean 28.21s/case, p90 32.01s, mean 8,402 spans/s, mean SQLite bytes 153MB. This is a bounded experiment, not production scalability/SLO proof. `experiments/V3_PHASE2_12_REPORT.md`.

### RCAEval pilot and protected holdout

**IMPLEMENTED FACT:** RCAEval revision `afeacb11...` index was qualified with SHA-256 recorded; 735 total rows, 90 RE2-OB rows. Root service/fault are isolated evaluation labels before evidence adaptation. `experiments/V3_PHASE2_10E_RCAEVAL_QUALIFICATION.md`, `archive/v3_phase2_10e_rcaeval/DATASET_HASHES.json`.

**MEASURED RESULT:** Phase 2.11 12-case pilot H1 and H5 achieved candidate-stage coverage 12/12; it was consumed for development. Phase 2.12 protected holdout froze candidate artifacts before GT read. H5 77/77 coverage says only that the known root service was contained in an unranked candidate set. It is not Top-1, ranking, causal validity, false-candidate characterization, or agent quality. `archive/v3_phase2_12/HOLDOUT_RESULTS.json`.

**PRODUCTION POLICY:** Phase 2.12’s 78-case holdout is consumed once and protected. Preserve it; do not rerun it for optimization, tune H0–H5 constants after seeing it, or retroactively modify candidates/evaluations. One acquisition failure means the gate remains `HOLDOUT_VALIDATION_TECHNICALLY_INCOMPLETE`. `archive/v3_phase2_12/RESEARCH_GATE.json`, `PHASE_A_BOUNDARY_CORRECTION.json`, `PHASE_A_FREEZE.json`.

### Profiles, agents, Qwen and gateway

- **Phase 2.13 — IMPLEMENTED FACT:** five deterministic development profile records, resolvable citations, scripted-model V0 trace and deterministic baseline abstention. No live provider behavior was measured. `experiments/V3_PHASE2_13_REPORT.md`.
- **V1 — MEASURED RESULT:** Qwen runtime/tool capability had 12/12 bounded interactions, but fixed 12-case development had 9 abstentions, 3 technical failures, no accepted hypothesis, no tool calls, no H5 fallback and Top-1 0/12. Tool attachment is not tool investigation. `experiments/V3_PHASE2_15_REPORT.md`.
- **V2 — MEASURED RESULT:** 15/15 synthetic structural/transport probes passed and 222 tests passed, but frozen development retry had 10 invalid default abstentions plus two timeout failures and zero valid reports. The V2 raw-status default bypass is an implementation defect in that historical version; do not reinterpret those artifacts as valid abstentions. `archive/v3_phase2_16_agent_v2/SYNTHETIC_RESULTS.json`, `archive/v3_phase2_16_agent_v2_development_retry_20260924/FINAL_REPORT.md`.
- **V2.1 — IMPLEMENTED FACT:** raw report status must be exact `RCA_HYPOTHESIS` or `INSUFFICIENT_EVIDENCE`; missing/null/empty/unknown/case mismatch reject. Status-specific fields are validated before `RCAReport`, with one readable repair then fail-closed. `src/cdoi/rca_agent_v2_1.py`, `archive/v3_phase2_16_agent_v2_1_status_contract/RESEARCH_GATE.json`.
- **Provider output — MEASURED RESULT:** Phase 2.16R live synthetic contract passed 10/10 required probes and 9/9 reliability runs, including structured report, tool call/serial continuation and bounded repair; this does not measure incident RCA quality. `archive/v3_phase2_16r_qwen_output_contract_live_20260924/FINAL_REPORT.md`.

### Full-payload/gateway blocker

**MEASURED RESULT:** V2.1 A1 plain-text/A2 tiny JSON/A3 minimal structured health ladder returned 3/3 terminal HTTP 200 in 0.96–1.24 seconds. A frozen P1-sized request with H1 preload and ten tool schemas was 20,923 bytes plus 2,160 schema bytes and did not return terminal response in the existing bounded allowance. `archive/v3_phase2_16_agent_v2_1_live_resume_20260925/RESEARCH_GATE.json`, `v3_phase2_16_agent_v2_1_full_payload_blocked_20260925/PAYLOAD_COMPARISON.json`.

**MEASURED RESULT:** A0 with no profiles/tools timeout twice; response-format OFF also timeout twice; same-size plain-text padding succeeded; two later exact structured A0 repeats succeeded (14.6s, 15.9s). Thus payload size, structured format, response format, profiles and tools are not demonstrated necessary or sufficient causes. `v3_phase2_16_v2_1_payload_isolation_20260925/PAYLOAD_RUN_RESULTS.json`, `v3_phase2_16_v2_1_response_format_control_20260925/RESPONSE_FORMAT_RESULT.json`, `v3_phase2_16_v2_1_payload_padding_control_20260925/PADDING_CONTROL_RESULT.json`, `v3_phase2_16_v2_1_payload_boundary_repeats_20260925/REPEAT_RESULTS.json`.

**DIAGNOSTIC INTERPRETATION:** behavior is intermittent gateway/provider runtime failure, not proven client payload root cause. Bounded correlation sample recorded 3 HTTP responses, 3 non-terminal calls, three safe provider request IDs. Client can retain attempt/elapsed/status and safe returned headers, but cannot see receipt, queue, route, worker assignment, tokenization, generation, cancellation or return path. `v3_gateway_observability_escalation_20260925/BOUNDED_CORRELATION_RESULTS.json`, `GATEWAY_OBSERVABILITY_GAP_ANALYSIS.json`.

**PRODUCTION POLICY:** do not compact profiles/remove tools/change timeout/response format or alter RCA policy on this evidence. Gateway-provider telemetry is required.

### VDT

**MEASURED RESULT:** VDT source inventory has 714 service rows, 2,941 dependencies, 1,479 logs, 100 incidents and 714 identity-map rows. Exact-ID adapter normalized 696 services, 2,941 relations and 1,454 events, retaining 43 issues. `archive/v3_vdt_integration_20260925/VDT_PIPELINE_RESULTS.json`, `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md`.

**MEASURED RESULT:** 36/100 incident windows are valid/resolvable; 63 lack valid end interval and one lacks identity. Valid incidents end 2026-09-05 while logs begin 2026-09-10: zero direct/topology overlaps; nearest subsequent event median 480,673 seconds. Explicit UTC/offset timestamps make UTC+7/+8 reinterpretation unjustified. `archive/v3_vdt_temporal_label_diagnosis_20260925/FINAL_REPORT.md`.

**MEASURED RESULT:** `rca_status` is `AI disabled` for 100/100 and is an aggregate automation/workflow field, not root service/component/category label. Ownership, collection, label creation and independence are unknown. The label-free five-incident pipeline ran, but had zero H1/H5 candidates/profiles due absent aligned metrics/traces/changes/events. `archive/v3_vdt_integration_20260925/VDT_PIPELINE_RESULTS.json`.

**PRODUCTION POLICY:** VDT is not currently independent RCA-quality evidence. The required governed delivery is specified in `archive/v3_vdt_data_acquisition_request_20260925/FINAL_REPORT.md` and its acceptance validator.

## Dataset and benchmark catalog

| Dataset / asset | Provenance and population | State/consumption | Supported claims and limits |
| --- | --- | --- | --- |
| CDOI-Bench | Project-owned synthetic fixture; repository has five compact benchmark files. | Development/regression, consumed. | Mechanism, safety hard negatives, property/bridge/promotion decisions; never external/enterprise validation. `BENCHMARKS.md`. |
| OAEI Anatomy 2026 | External local Anatomy source/target/reference; historical pair-positive protocol N=7,580. | Diagnostic/development, heavily consumed. | Profile/extraction/abstention diagnostics only; positive-only pair protocol cannot measure broad retrieval, precision/F1/false merge or external generalization. `experiments/V2_6_RESULTS.md`. |
| STW–TheSoz | Local frozen STW and TheSoz SKOS assets plus mapping; 6,344 raw rows/2,475 sources, four SKOS relations. | Latest external ontology relation evaluation; prediction/GT ordering frozen. | Exact parity and relation failure evidence; one mapping family, positive-only risk limit, no production selection. Latest archive. |
| iDAI–PACTOLS (DH) | MIT benchmark; iDAI English 1,311 concepts, PACTOLS English 60, six usable equivalence mappings. | External pilot, consumed diagnostic. | Narrow retrieval portability only; insufficient relation diversity/calibration/generalization. `experiments/V3_EXTERNAL_DH_PAIR_QUALIFICATION.md`. |
| CMT–Conference | Referenced by adapter/benchmark inventory where available; no authoritative current executed result was found. | Not qualified/executed in current gates. | Do not claim an evaluation or use as third replication without acquisition/freeze/protocol. |
| OET / concept placement | External adapter target; local required `test.json` absent in V2.6. | Data missing/not run. | Would measure retrieval and parent placement only after licensed acquisition. `data/benchmarks/external/README.md`. |
| RCAEval | Upstream RCAEval, revision/hash qualified; 735 index cases, RE2-OB 90. | RE2-OB pilot consumed; 78-case holdout consumed once. Other suites reserved. | Candidate coverage under frozen rules, not ranking/causality/independent final validation. `experiments/V3_PHASE2_10E_RCAEVAL_QUALIFICATION.md`. |
| VDT | Five supplied source files; 100 incidents and operational snapshots described above. | Read-only ingestion/diagnosis; not quality-evaluable. | Adapter compatibility and data-gap evidence only; no aligned telemetry/labels/provenance. |
| Foundation/domain TTL and raw demo fixtures | Versioned project ontology stack and small fixtures. | Development source. | Canonical schema/safety testing, not external benchmark evidence. |

## Frozen experiment inventory and invariants

- Relation archive contains preregistration, anti-leakage audit, direction audit, prediction freeze, full predictions/results/failures, gate, SHA-256 manifest and regression. `experiments/archive/v3_ontology_relation_aware_selection_20260925/MANIFEST.json`, `HASHES.json`.
- STW candidate sets were frozen before mapping GT parsing; relation selector input excludes labels/targets/mapping predicates. Do not revise frozen predictions after observing results.
- Phase 2.11 development pilot is consumed. Preserve its 35/35 recorded artifact manifest and do not call it independent validation.
- Phase 2.12 has protected split/hash/preregistration, Phase-A boundary correction and freeze before GT evaluation. 77 candidate evaluations are frozen; one failure is part of the accounted 78. Do not optimize/rerun/modify for performance.
- Phase 2.13+ historical archives must remain immutable. Phase 2.15/2.16 reports separately verify archived hashes; Phase 2.12 is checked root-manifest-only in later work to protect its case artifacts.
- V2 development failure and retry are negative evidence, not data to “repair” retrospectively. V2.1 is deliberately separately versioned.
- A technical failure is neither a semantic abstention nor a wrong semantic prediction. Passing contract tests are neither benchmark quality nor production readiness.

## Current research and safety invariants

```text
retrieval != selection != commitment
technical failure != semantic abstention
candidate != root cause
trace path != causal path
metric degradation != anomaly proof
temporal precedence != causality
ontology alignment != entity resolution
cross-domain mapping != semantic equivalence
EvidenceGraph != Canonical KG
LLM/model proposal != approved ontology/KG mutation
```

Keep foundation immutable; never derive `owl:sameAs` from weak evidence; never write canonical KG from an unapproved proposal; never substitute model score for calibrated commitment confidence; never expose protected GT into candidate generation; never convert VDT `rca_status` into a label; never use source data to fabricate topology/change/glossary modalities.

## Failure taxonomy and bottleneck tree

```text
CDOI current bottlenecks
├─ Semantic evidence
│  ├─ retrieval: STW non-exact GT usually absent from Top-20 (2,409 misses)
│  ├─ target selection: 934 wrong frozen Top-1 targets
│  ├─ relation discrimination: broad/narrow/related joint accuracy near zero
│  ├─ commitment risk: positive-only mappings; no negatives/calibration split
│  ├─ runtime: Dense blocked by Windows Torch; QSEM external runtime absent
│  └─ validity: only one large relation-diverse family; third pair missing
├─ RCA evidence
│  ├─ acquisition/temporal: VDT incident windows and logs do not overlap
│  ├─ labels/provenance: VDT has no governed root-cause outcome/independence
│  ├─ reasoning: H0–H5 are candidates, not ranking or causal inference
│  └─ evaluation: protected holdout consumed/technically incomplete; no unused set
├─ RCA runtime
│  ├─ historical V2 status default bypass
│  ├─ V2.1 full payload intermittently non-terminal
│  └─ observability: provider queue/worker/generation/cancellation opaque
└─ Production gap
   ├─ no generic collectors / host binding / real operational governance
   ├─ no calibrated commitment/RCA confidence or causal method
   └─ no reliability/scale/SLO/security/governance qualification
```

| Bottleneck | Evidence / affected subsystem | Impact and what is not established | Type | Exact unblock/falsification evidence |
| --- | --- | --- | --- | --- |
| STW non-equivalence retrieval | R@20 broad 24.24%, narrow 26.54%, related 29.21%; 2,409 GT misses. | Relation selector cannot select a missing target; this does not prove a particular retrieval redesign. | Research/engineering | Frozen same-case retrieval experiment with independent pair and per-relation recall/error accounting. |
| Target selection | 934 wrong Top-1; exact per-row 50.44%. | Historical exact parity is not selection safety across relations. | Research | Predeclared retrieval/selection ablation with negatives and held-out pair. |
| Relation discrimination | joint broad 0/33, narrow 4/1,349, related 1/558. | No broad/narrow/related routing/commitment is justified. | Research/production | Independent relation-diverse data, frozen targets, positive+negative risk evaluation. |
| Commitment risk | STW positive-only; no false-positive/calibration estimate. | Similarity/Top-1 cannot become confidence. | Data/research/production | Independent calibration split with validated positives and negatives, then calibrated risk/coverage study. |
| Dense Linux runtime | Windows `c10.dll`/1114; Linux runtime unavailable. | No Dense gain/loss/unsafe selection result exists. | Engineering | Clean pinned Linux CPU execution of frozen Dense config and same-CandidateSet outputs. |
| Independent ontology replication | Anatomy consumed; DH narrow; STW one family; third pair absent. | No broad external generalization. | Data/research | Acquire/license/freeze third relation-diverse source/target/reference family pre-scoring. |
| Qwen/gateway reliability | small 3/3 success; full P1 blocked; A0 repeats mixed. | Payload component is not proven root cause; runtime availability is not RCA quality. | Engineering/research | Provider lifecycle telemetry plus frozen qualification terminal/reliability results. |
| Provider observability | Client lacks queue/route/worker/tokenization/generation/cancel/return states. | Cannot assign client/gateway/model causality. | Engineering/external dependency | Gateway telemetry correlated by returned request IDs or timestamp/request hashes. |
| VDT alignment/labels | zero incident-event overlap; 36 valid windows; `AI disabled` status only. | VDT is not independent RCA-quality data. | Data/acquisition/research | Governed incident-aligned telemetry + exact identities + valid windows + post-freeze RCA labels + provenance/independence. |
| RCA ranking/causality | H5 coverage only; no valid V2 report, no calibrated confidence/causal model. | Candidate coverage is not diagnosis correctness or causality. | Research/production | Unused governed RCA set, valid report contract, preregistered ranking/grounding/abstention/causal evaluation. |
| Scalability | SQLite measured on Phase 2.12 workload only. | No production throughput/retention/multi-tenant/SLO claim. | Engineering/production | Representative load, resource, retention, recovery and SLO measurements. |
| Production ingestion/governance | no collectors/host binding, authoritative sources, business/process data or operating policy. | No deployment readiness. | Product/data/production | Governed onboarding contract fulfillment, security/access review, ownership, review workflows, rollback/SLO runbooks. |

## Research hypothesis ledger

| Hypothesis | Status | Evidence and boundary |
| --- | --- | --- |
| Corrected source-faithful synonym extraction changes deterministic Anatomy behavior | **PARTIALLY_SUPPORTED** | Phase 2.6 P1-P0 +0.0294 fixed-Top-20; Anatomy-only, no production profile change. `V3_PHASE2_6_RESEARCH_GATE.md`. |
| Definitions improve semantic selection | **NOT_SUPPORTED / UNRESOLVED** | One-sided definition coverage; no bilateral evidence. |
| Residual Anatomy errors need more than lexical alias matching | **PARTIALLY_SUPPORTED** as a diagnostic hypothesis | N=138 residual patterns/structural signal; no stronger selector test. |
| Dense improves semantic selection | **NOT YET TESTED** | Runtime blocked; no result exists. |
| STW exact selection preserves historical exact behavior | **SUPPORTED narrowly** | 1,489/2,383 parity; one data family. |
| Hierarchy makes non-equivalence relation selection safe | **NOT_SUPPORTED** | 21 proposal changes, target unchanged, joint metrics inadequate. |
| H1/H5 contain the root service in RE2-OB candidate sets | **SUPPORTED for the frozen population** | H5 77/77 candidate coverage; no ranking/causal claim. |
| Trace H2 adds holdout GT recovery beyond H1 | **NOT_SUPPORTED** | zero H5 GT recoveries beyond H1; it expands candidates. |
| V1 Qwen investigates evidence when tools are attached | **NOT_SUPPORTED** | zero tool/fallback calls. |
| V2.1 contract fails closed locally | **SUPPORTED** | deterministic status/repair tests; live payload not qualified. |
| Full-payload failure is caused by response format, payload size, tools or profiles | **UNRESOLVED** | Controls/repeats are nondeterministic; provider telemetry missing. |
| VDT can independently evaluate RCA | **NOT_SUPPORTED** | temporal/label/provenance gaps. |

## Dead ends and negative results: do not repeat blindly

- Do not use arbitrary heuristic voting or lower global thresholds solely for recall; this turns retrieval weakness into unsafe selection/commitment.
- Do not treat lexical/embedding similarity, margin, Top-1, or a model’s score as calibrated confidence.
- Do not repeat Phase 2.5 synonym conclusion without the Phase 2.6 annotation-object correction; do not build Anatomy-specific alias blacklist/heuristic from residual diagnostics.
- Do not assume ERROR spans, traces, changes or temporal order identify cause; H0 ERROR-only pilot coverage was 0/12 and a trace path is non-causal.
- Do not tune H0–H5 from Phase 2.12 results or rerun protected holdout for optimization.
- Do not call V1 tool attachment tool use, V2 orchestration-state reach model comparison, or passing synthetic tests live RCA quality.
- Do not remove profiles/tools, disable response format, or change timeouts based on intermittent V2.1 payload observations.
- Do not interpret positive-only mapping data as evidence of low false-positive risk.
- Do not call benchmark/fixture results enterprise generalization or production readiness.

## What is proven, measured, unknown, and not authorized

### Proven implementation facts

The deterministic safety architecture, review/version/KG boundaries, constrained preprocessing, CandidateSet/selector contracts, relation direction canonicalization, incident graph/candidate/profile/read-only tool contracts, and V2.1 fail-closed local report validation are implemented.

### Measured but narrowly scoped results

Anatomy profile diagnostics; iDAI–PACTOLS six-mapping pilot; STW exact parity/relation failures; RCAEval pilot/holdout candidate coverage; V1/V2 agent negative development results; V2.1 health/payload behavior; and VDT data insufficiency are all scoped to their named artifacts and populations.

### Diagnostic interpretations only

Residual errors may need richer representation; retrieval is a dominant non-equivalence bottleneck; gateway behavior appears intermittent; VDT delivery is temporally disjoint. None establishes causal mechanism or a specific fix.

### Unknown / research hypotheses

Dense utility, QSEM relation-aware behavior, calibrated semantic/RCA confidence, broad ontology generalization, valid RCA ranking/grounding/abstention quality, causal inference, gateway failure root cause and VDT future-data suitability.

### Explicitly not authorized for production

Automatic ontology commitment/canonical KG writing; non-equivalence mapping routing; selector-based commitment; production RCA ranking/remediation; causal claims; VDT quality evaluation; production use of any agent; and production-readiness claims.

## Production-readiness gap

Before a reasonable production-readiness assessment, CDOI needs: governed source ownership/access/authority; generic collectors and application/host binding; identity rules beyond exact IDs where justified; full review operations/approval UX/rollback; independent calibration positives/negatives; relation-diverse external replication; reliable dense/model/gateway runtime; production-scale load/SLO/retention/recovery evidence; unused governed RCA validation labels and aligned multimodal telemetry; calibrated abstention/ranking; causal methodology if causal claims are desired; security/privacy/audit/incident-response operating controls; and an explicitly approved product policy. None is implied by current test or benchmark success.

## Latest regression and test state

Latest full recorded regression is the relation-aware archive: **263 collected, 263 passed, 0 skipped, 0 failed**. `experiments/archive/v3_ontology_relation_aware_selection_20260925/REGRESSION.json` and `FINAL_REPORT.md` are authoritative. A subsequent payload-diagnostics regression has exit code 0, 0 failures/skips but records no numeric collection count; it must not replace the 263 count. `experiments/archive/v3_payload_diagnostics_regression_20260925/REGRESSION.json`.

Historical counts remain scoped: Phase 2.16 synthetic archive 222/222; Phase 2.15 finalization 214/214; V2 retry 235/235; they are not current full-suite counts.

## Open research questions

1. Can frozen retrieval improve non-equivalence GT availability without reducing safety on independently held-out relation-diverse pairs?
2. Can a relation selector achieve safe broad/narrow/related discrimination with valid negatives and calibrated commitment risk?
3. Does Dense add value under the pinned Linux configuration, and where does it fail relative to deterministic retrieval?
4. Can an authorized QSEM protocol add proposal quality without routing/commitment leakage?
5. Can an unused governed RCA dataset support ranking, grounding and abstention evaluation after contract-qualified live runtime?
6. What server-side lifecycle state causes intermittent full-payload non-terminal gateway behavior?
7. Can a corrected VDT delivery satisfy alignment, identity, modality, label and independence requirements?
8. What product/governance model should decide whether ontology-informed RCA is useful after the operational baseline is valid?

## Prioritized roadmap

### P0 — preserve evidence and unblock external dependencies

1. Preserve all frozen archives, especially Phase 2.12; do not tune/rerun/retrofit them. Dependency: none. Expected evidence: unchanged hashes/manifests. Decision enabled: trustworthy future comparison.
2. Submit `experiments/archive/v3_gateway_observability_escalation_20260925/GATEWAY_PROVIDER_ESCALATION.md` and request provider lifecycle telemetry keyed by safe request IDs/timestamps/hashes. Dependency: gateway owner. Expected evidence: queue/route/worker/generation/cancellation/return-path diagnosis. Decision enabled: whether retry/config or infrastructure action is justified.
3. Obtain a clean Linux runtime and execute the already frozen Dense configuration without tuning. Dependency: Linux/PyTorch environment. Expected evidence: same-CandidateSet Dense outputs, safety/errors/latency. Decision enabled: whether Dense merits further research.

### P1 — make evaluation scientifically admissible

1. Acquire/freeze an independent third ontology pair with relation diversity, documented licence/provenance and reference mappings before scoring. Dependency: data acquisition. Expected evidence: independent retrieval/selection/relation replication. Decision enabled: external-validity and relation research direction.
2. Acquire independent calibration positives/validated negatives and a split policy. Dependency: governed labels. Expected evidence: calibrated risk/coverage, not score proxy. Decision enabled: whether any commitment-confidence research is defensible.
3. Deliver VDT-aligned data per acquisition packet: valid incidents, aligned logs/metrics/traces/changes, exact IDs, governed post-freeze root labels and provenance/independence. Dependency: source owner. Expected evidence: acceptance validator pass. Decision enabled: whether VDT can enter RCA evaluation.

### P2 — resume bounded RCA qualification only after P0/P1 dependencies

1. After provider telemetry resolves the runtime issue, run only frozen V2.1 minimal P1–P12 qualification. Dependency: reliable terminal response. Expected evidence: terminal/reliability/status/repair/tool contract results. Decision enabled: whether a separately frozen development-quality run is legitimate.
2. If and only if qualification succeeds, run a separately versioned development batch on already-consumed development data; keep Phase 2.12 protected material unread. Dependency: P2.1. Expected evidence: valid reports, grounding, abstention and Top-k measures. Decision enabled: whether an independent unused evaluation is worthwhile.

### P3 — production/product research, not current implementation work

Define governed onboarding/collectors, host binding, business/process evidence, scale/SLO/security controls and product review/remediation policy; then consider causal methodology only if the product need requires causal claims. Dependency: valid data/runtime/calibration evidence. Decision enabled: a real production-readiness review.

## Exact resume point

A new session must begin read-only, in this order:

1. Read this file, then `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md`.
2. Read newest ontology authority: `experiments/archive/v3_ontology_relation_aware_selection_20260925/FINAL_REPORT.md`, `RESEARCH_GATE.json`, `RELATION_RESULTS.json`, `RELATION_ABLATION_RESULTS.json`, `RELATION_PREDICTIONS_FREEZE.json`, `HASHES.json`.
3. Read latest gateway authority: `experiments/archive/v3_gateway_observability_escalation_20260925/FINAL_REPORT.md`, `RESEARCH_GATE.json`, `GATEWAY_OBSERVABILITY_GAP_ANALYSIS.json`; then V2.1 full-payload and repeat/control archives.
4. Read protected-holdout gate only at manifest/report level unless the task is explicitly authorized as integrity verification. Do not open/use its GT artifacts to tune any rule.
5. Read `experiments/archive/v3_vdt_temporal_label_diagnosis_20260925/FINAL_REPORT.md` and the acquisition request before treating VDT as data.
6. Inspect `git status --short`; preserve unrelated dirty work. The next legitimate task is **external coordination for gateway telemetry and/or provision of clean Linux Dense runtime**, not a new selector/payload redesign or another quality experiment.

## CURRENT STATE IN ONE PAGE

CDOI is a conservative ontology-integration research prototype plus a strictly separated non-causal RCA evidence research path. The ontology path implements ABox/TBox separation, evidence-backed schema candidates, CandidateSet retrieval, deterministic selection, validation, human review, immutable versioning and approved-only canonical KG writes. The RCA path implements raw operational adapters, exact-ID/UTC incident snapshots, evidence graph, H0–H5 unranked candidates, profiles and read-only agents. Neither branch authorizes model-driven ontology/KG mutation.

Latest ontology result is STW–TheSoz relation-aware proposal evaluation: exact historical source-level parity 1,489/2,383=62.4843%, but only 50.4434% per-row exact Top-1; broad 0/33, narrow 4/1,349, related 1/558 joint target+relation. 2,409 GT targets were not retrieved, 934 Top-1 targets were wrong, 28 exact overgeneralizations occurred, and 37 conflicting mappings were excluded. This supports deterministic direction canonicalization and limited exact evidence only. It does not support non-equivalence routing, calibrated commitment, automatic KG writes or generalization. Dense has no result because Windows Torch fails and Linux runtime is unavailable; QSEM is proposal-only/runtime unavailable.

RCAEval RE2-OB candidate generation is strong only at the candidate-containment level: protected H5 has 77/77 coverage with mean 4.0649 candidates, but this is neither ranking nor root-cause correctness/causality. The 78-case holdout is consumed once; one acquisition failure keeps its gate technically incomplete and it must never be tuned/rerun for optimization. V1 Qwen runtime/tools worked but did not investigate or return accepted hypotheses. V2 synthetic contracts passed but live development had invalid default abstentions; V2.1 fixes that contract deterministically but its full payload intermittently does not receive terminal gateway response. Small health probes succeeding do not prove full RCA reliability. Provider telemetry is now the immediate runtime dependency.

VDT ingest is structurally compatible but not valid RCA evidence: incidents and logs are temporally disjoint, labels are not root-cause labels, and provenance/independence are unknown. Current production readiness is absent: no calibrated risk/confidence, relation-diverse replication, unused independent RCA data, causal method, production collectors/governance, runtime reliability or scale/SLO evidence. Latest recorded full regression is 263 passed / 0 failed.

## TOP 10 THINGS A NEW AI MUST NOT FORGET

1. Retrieval, selection and commitment are separate; no score or Top-1 can auto-commit ontology/KG material.
2. Phase 2.12 is a consumed protected holdout: do not tune, rerun for optimization or read GT to modify H0–H5.
3. Candidate coverage is not RCA ranking accuracy, diagnosis correctness, causality or production utility.
4. STW non-equivalence relation selection is unsupported; broad/narrow/related outputs cannot route or commit.
5. STW mapping data is positive-only; it cannot estimate false-positive risk or calibrate commitment confidence.
6. Dense has no measured result; Windows runtime failure is technical evidence only.
7. V2 historical abstentions are invalid when status default bypassed required fields; V2.1 is separate and fail-closed.
8. Small Qwen health successes do not prove full-payload reliability; gateway provider telemetry is missing.
9. VDT is not independent RCA validation: zero incident/log overlap and no governed root-cause labels/provenance.
10. Passing tests prove contracts/regression only, never semantic validity, RCA quality, external generalization or production readiness.

## NEXT SESSION START HERE

- Run no experiment and change no code until the current task is explicit.
- Inspect `git status --short`; preserve the dirty current research artifacts.
- Re-read latest relation archive gate/results and gateway observability gate before making any semantic or RCA claim.
- Treat `experiments/CDOI_CURRENT_VERIFICATION_MATRIX.md` plus this file as live reconciliation; use older reports only for history and explicitly note conflicts.
- If coordinating externally, send the existing gateway telemetry packet and/or VDT data acquisition request unchanged.
- If provisioning runtime, use the frozen Dense Linux configuration exactly; record result separately and do not tune.
- If data arrives, validate it through the existing VDT delivery validator before reading labels or evaluating RCA.
- Do not authorize production routing, automatic commitment, causal RCA, or benchmark-to-enterprise claims.
