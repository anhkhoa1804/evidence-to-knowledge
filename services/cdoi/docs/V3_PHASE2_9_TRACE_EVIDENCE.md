# V3 Phase 2.9 — Distributed Trace Evidence

Phase 2.9 adds one optional manifest source, trace_span_jsonl at traces/spans.jsonl. It produces immutable NormalizedTraceSpanEvidence records under cdoi_preprocessing_v1 and reconstructs a read-only TraceExecutionGraph from declared parent span references.

## Contract and identity

Required fields are trace_id, span_id, service_id, and start_time. Optional fields include parent_span_id, operation, duration_ms, end_time, status, kind, sampled, error_code, peer_service_id, and attributes. Span identity is trace_id plus span_id; duplicate span IDs within a trace are explicit issues and never overwrite a prior span. Service ownership uses only exact manifest-local service IDs.

Start time is timezone-aware UTC. A declared end time is preserved; otherwise a finite non-negative duration derives end time. If neither is supplied, the span is a point observation at its start. A declared end and duration conflict is invalid. Zero duration is valid explicit evidence. Incident membership uses inclusive interval overlap: span_start <= incident_end and span_end >= incident_start.

## Execution graph and partial safety

Graph nodes are normalized span evidence. Graph edges are only declared parent span to child span relationships. Missing parents, unresolved services, cycles, and multiple roots are preserved as partial-trace conditions. Cycle edges are withheld from traversal; no parent edge is inferred from timestamps. Fan-out and repeated same-operation spans are retained as distinct records.

DIRECT_ONLY and ONE_HOP incident entity scope remain authoritative. Trace content cannot expand the selected entity scope. Out-of-scope spans are excluded from snapshot membership, while the selected trace graph retains the source trace partial status.

## Separation guarantees

Static dependency is not observed execution edge. Observed execution edge is not causal relation. ERROR status is observed status, not root cause. Duration is observed duration, not anomaly. Trace evidence creates zero SchemaCandidates, DataPropertyCandidates, topology mutations, proposals, approvals, or KG assertions.

Normalized trace metadata retains only attributes_present; arbitrary span attributes remain in the raw source record and are not copied into high-level snapshot reports. Provenance retains raw evidence ID, source record/file, manifest dataset, adapter, and normalization version.
