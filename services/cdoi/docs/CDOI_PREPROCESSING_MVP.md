# CDOI Preprocessing MVP

This additive MVP accepts a small, manifest-defined customer/domain package and produces deterministic, provenance-preserving evidence artifacts before the existing CDOI semantic pipeline. **This MVP is not a generic enterprise ETL platform.**

## Supported package

```text
dataset/
  manifest.yaml
  inventory/services.csv       # service_id, name required; description, owner, environment optional
  topology/dependencies.jsonl  # source_id, relation, target_id required
  telemetry/logs.jsonl         # timestamp, service_id, event required
  semantics/glossary.yaml      # terms[].id, terms[].label required
  changes/deployments.csv      # optional declared change evidence
```

The fixed dependency vocabulary is `calls`, `depends_on`, `reads_from`, `writes_to`, `publishes_to`, and `consumes_from`. Glossary definitions and aliases are optional. Unknown source types and missing required fields fail closed or are recorded in `unresolved.jsonl`; they are never converted to semantic abstentions.

## Flow and safety

```text
raw records -> RawEvidenceRecord -> normalized evidence -> evidence-backed schema candidates
                                                   -> glossary semantic envelope -> existing StructuredExtractor
```

Inventory becomes `NormalizedEntityEvidence`, topology becomes `NormalizedRelationEvidence`, logs become `NormalizedEventEvidence`, and glossary entries become `NormalizedSemanticTerm`. All have dataset/source-file/source-record/raw-evidence identifiers and normalization-version provenance. Exact service-ID correlation is permitted only within the manifest namespace. Unknown IDs remain unresolved; no fuzzy merge, `owl:sameAs`, equivalence relation, ontology class, or KG fact is created from raw input.

`deployment_change_csv` additionally produces `NormalizedChangeEventEvidence` for declared deployments, rollbacks, configuration/version/feature changes, restarts, and other declared changes. Required columns are `change_id`, `timestamp`, `service_id`, and `change_type`; before/after version and configuration fields remain separate. Change targets correlate by exact service ID only. `changes_for_entity(entity_id, start, end)` returns ordered evidence in the inclusive UTC interval. Temporal proximity between a deployment and a log is observable evidence, **not proof of causality**. RCA reasoning and causal inference are NOT IMPLEMENTED.

There are four distinct levels: raw evidence, normalized evidence, an unreviewed `SchemaCandidate`, and approved ontology/KG material. A schema candidate is evidence-supported and is **not ontology truth**. The adapter emits deterministic existing `ClassCandidate` / `ObjectPropertyCandidate` values with raw-evidence links, but does not invoke proposal commit, validation, review, routing, Qwen, Dense, or RCA reasoning.

The explicit induction rules are `ENTITY_SERVICE_ADAPTER_TYPE_V1` (aggregate declared service-inventory records into the generic `SoftwareService` candidate), `RELATION_BOUNDED_VOCABULARY_V1` (aggregate each accepted topology verb into one property candidate), and `GLOSSARY_DIRECT_SEMANTIC_TERM_V1` (preserve direct glossary evidence without merging it with inventory observations). Log events remain ABox/event evidence; their message text does not produce event classes. Unknown topology endpoints preserve partial relation support but contribute no fabricated range type.

## Artifacts and operation

Run `cdoi preprocess dataset/manifest.yaml --output output/`, or use `--dry-run` to parse, validate, normalize, and calculate in-memory schema diagnostics without generated files. Inputs are read-only. A manifest containing changes also emits typed `changes.jsonl`; older manifests do not require it. Output contains versioned JSONL records, `schema_candidates.jsonl`, `unresolved.jsonl`, `provenance.json`, `semantic_envelope.json`, and `manifest.json` with SHA-256 source and output hashes.

Timestamps must be timezone-aware and normalize to UTC while retaining their original value. Current limitations: no generic CSV inference, APIs, databases, streaming, traces/metrics, enterprise entity resolution, embeddings/LLMs, automatic ontology commitment, or root-cause analysis. Logs establish correlation readiness only; they do not establish causes.

V3 Phase 2.7 adds a separate operational-context consumer, not a new preprocessing source type. A constrained incidents/incidents.csv declaration can select a deterministic EvidenceSnapshot from already-normalized inventory, topology, logs, and changes. It uses exact IDs, inclusive UTC interval membership, and direct or bounded one-hop directed topology scope. The incident declaration is control input rather than semantic evidence; snapshots preserve evidence provenance and selection reasons but make no causal, ontology, proposal, review, approval, or KG assertion. See V3_PHASE2_7_OPERATIONAL_EVIDENCE_CONTEXT.md.

## Optional metric evidence

V3 Phase 2.8 adds an optional metric_observation_csv manifest source at metrics/metrics.csv. Required columns are metric_id, timestamp, service_id, metric_name, value, unit, and metric_kind. Valid records become immutable NormalizedMetricEvidence and write to a separate metrics.jsonl artifact; metric observation is not log event and is not operational change.

Values must be finite numeric observations. Supported declared units are preserved without conversion; unsupported units and incompatible units within an otherwise matching series become explicit preprocessing issues. The series key includes exact entity ID, metric name, unit, declared kind, and aggregation. Gauge and counter readings remain distinct raw observations. The adapter does not calculate anomalies, trends, counter totals/deltas, causal relations, ontology classes, or data properties. See V3_PHASE2_8_METRICS_EVIDENCE.md.

## Optional trace evidence

V3 Phase 2.9 adds an optional trace_span_jsonl manifest source at traces/spans.jsonl. Required span fields are trace_id, span_id, service_id, and start_time. Valid records become immutable NormalizedTraceSpanEvidence and write to a separate traces.jsonl artifact. Span hierarchy is represented separately as a read-only TraceExecutionGraph from declared parent span relationships only.

Trace service ownership uses exact IDs. Start/end/duration are timezone-aware and validated; incident membership uses inclusive temporal overlap. Missing parents, duplicate spans, unresolved services, cycles, and multiple roots are explicit partial-evidence states. A trace execution edge neither replaces static topology nor proves causality. Trace evidence creates no schema candidate, data property, topology mutation, ontology proposal, approval, or KG fact. See V3_PHASE2_9_TRACE_EVIDENCE.md.
