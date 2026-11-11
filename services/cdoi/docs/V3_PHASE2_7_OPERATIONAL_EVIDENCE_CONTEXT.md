# V3 Phase 2.7 — Operational Evidence Context

Phase 2.7 establishes operational_evidence_context_v1: a deterministic, read-only collection boundary for normalized operational evidence. It is an input to possible future RCA research, not RCA, causal inference, anomaly detection, or an ontology/KG update path.

## Architecture audit and boundary

Before this phase, raw_preprocessing.py already emitted immutable normalized inventory, directed topology, log, change, and glossary evidence under cdoi_preprocessing_v1. Its identity namespace is the exact manifest-local service ID. Its log/change timestamps are timezone-aware, normalized to UTC, and its normalized records retain raw record ID, source file, source record, adapter, and manifest provenance. EvidenceSchemaInducer separately consumes inventory/topology/glossary evidence into unreviewed schema candidates. It does not consume changes, and neither it nor the new context module writes to state.py, kg.py, proposal review, or canonical KG.

The missing boundary was a reproducible answer to “which normalized evidence is relevant to this declared operational window?” src/cdoi/operational_context.py supplies that boundary without changing preprocessing serialization or the existing semantic/ontology pipeline.

Declared incident CSV control input plus normalized inventory, topology, log, and change evidence produces OperationalEvidenceContext, then EvidenceSnapshot. Normalized glossary terms remain separately available. Snapshot membership does not imply SchemaCandidate, proposal, review, approval, or canonical KG fact.

## Contracts

IncidentWindow is frozen and requires a non-empty incident ID, timezone-aware start/end timestamps, and one or more affected entity IDs. The CSV is a constrained operational control input, not a new raw semantic-evidence adapter. Multiple IDs use | and source record/file provenance is retained.

OperationalEvidenceContext is frozen and contains the declared incident, topology scope, direct and expanded exact-ID entity scope, selected immutable normalized records, unresolved records, and selection provenance.

EvidenceSnapshot is a frozen deterministic wrapper. It serializes as operational_evidence_context_v1 with a content-derived SHA-256 ID and hash. It contains no runtime timestamp.

## Selection semantics

The interval is inclusive [start_time, end_time] after explicit UTC normalization. The same rule applies to events and changes. Naive timestamps and reversed intervals fail closed.

Entity correlation is exact-ID only. A missing declared ID produces UNRESOLVED_INCIDENT_ENTITY; no label match, fuzzy resolution, or fabricated entity is attempted.

DIRECT_ONLY selects exact affected inventory entities and directed relations touching them. ONE_HOP, the frozen default, selects those relations and existing inventory endpoints adjacent to the direct entities. It does not expand relations again from those neighbors, so it is bounded to one hop. Direction is preserved exactly as normalized: calls remains source to target. In-window events and changes match the selected entity scope, which is direct scope for DIRECT_ONLY and expanded scope for ONE_HOP.

No safe exact linkage exists between service IDs and glossary term IDs in the MVP. Therefore snapshot semantic_terms is empty and marks NOT_LINKED_BY_EXACT_ID; the glossary remains available separately.

Each selected record has a non-causal stable reason, including DIRECT_INCIDENT_ENTITY_V1, ONE_HOP_TOPOLOGY_NEIGHBOR_V1, EVENT_IN_TIME_WINDOW_V1, and CHANGE_IN_TIME_WINDOW_V1. Raw preprocessing issues are retained separately with PREPROCESSING_UNRESOLVED_EVIDENCE_V1.

## Safety

Temporal proximity is observed membership, not causality: a deployment at 09:55 and an error at 10:00 can appear in the same snapshot without any assertion that one produced the other. Snapshot artifacts never generate root-cause, causal-score, causal-edge, culprit, ontology commitment, review decision, mapping, or owl:sameAs fields.

The new module has no imports from selectors, calibration, QSEM, Dense, pipeline commitment, state store, or KG writer. Existing preprocessing remains cdoi_preprocessing_v1; the context has its own additive version.

## Operation

Run .venv\Scripts\python.exe tools\run_v3_phase2_7_demo.py. It reads the existing demo manifest and incidents/incidents.csv, then writes a snapshot under experiments/archive/v3_phase2_7/incident_snapshots/. It never modifies the source package, ontology versions, or KG.

## Additive metric field

Phase 2.8 extends the readonly context with an optional metrics collection. The operational_evidence_context_v1 serialization stays versioned as v1 because metrics is additive: historical snapshots without the field are interpreted as having an empty metric collection, and their archived files were not rewritten. Metrics use the same exact-ID selected entity scope and inclusive UTC time interval as events and changes. See V3_PHASE2_8_METRICS_EVIDENCE.md.
