# CDOI RCA Data Acquisition Specification V1

## Purpose

This is an operational data-acquisition contract for deterministic RCA POC readiness. It is not an ontology schema, an RCA algorithm specification, or a request to infer missing facts. Evidence data and authoritative RCA labels are separate deliveries.

## Frozen temporal contract

For every selected incident, supply timezone-qualified timestamps for a bounded interval:

```text
pre-window → incident_start → incident interval → incident_end → post-window
```

CDOI preserves the declared incident bounds and uses its existing inclusive UTC snapshot policy. It does not widen a window, shift timestamps by an assumed timezone, or accept records merely because they exist elsewhere in the export. Per modality, acceptance records earliest/latest time, incident start/end, overlap duration, and pre/inside/post counts.

## Required acquisition matrix

| Dataset | Why needed | Minimum fields | Recommended fields | Identity key | Required temporal coverage | Current status | Can crawl automatically? | Likely source/system | If unavailable, ask whom? | Priority | Acceptance condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Incident | Declares evidence window and anchor | incident_id, start, end, affected service/component, environment | severity, declaration source, status | stable incident_id | declared pre/incident/post interval | VDT: 36 valid of 100; 63 lack end | Group B | incident management / SLO system | incident-management owner | P0 | explicit timezone, end ≥ start, exact anchor |
| Logs/events | Minimum operational evidence | event_id, timestamp, service/application ID, event type/message, source, environment | severity, instance/host, trace/request ID | exact service/application ID | must overlap each selected incident | VDT logs are Sep 10–11; valid windows end Sep 5 | Group B | logging platform | observability/logging owner | P0 | parseable, exact identity, in-window record |
| Metrics | Supports deterministic metric candidate evidence | timestamp, service ID, metric name, finite value, unit, kind | aggregation, sampling interval, dimensions | service + series key | incident interval; pre/post preferred | VDT: not delivered | Group B | monitoring backend | observability owner | P0/P1 | typed finite points with in-window coverage |
| Traces | Supports trace participation evidence | trace_id, span_id, service ID, start/end or duration | parent span, status, kind, operation, sampling | trace/span/service IDs | span overlaps selected window | VDT: not delivered | Group B | tracing backend | observability owner | P1 | valid span identity, exact service, retained parent issues |
| Deployments/changes | Context only; never causal proof | change_id, timestamp, service ID, type | version, before/after, status, rollback | change_id + service ID | pre/inside incident period | VDT: not delivered | Group B | CI/CD or change system | CI/CD owner | P1 | timestamped exact target; lifecycle semantics documented |
| Topology/dependencies | Bounded contextual expansion | source ID, target ID, relation | observation time, direction, source | exact endpoint IDs | static snapshot provenance; not telemetry | VDT: delivered | Group A | local governed export | service-map owner | P1 | no dangling identity silently repaired |
| Identity map | Resolves service/application/workload names | authoritative source ID, canonical service ID | environment, namespace, workload, validity period | exact authoritative IDs | applies to selected window | VDT: partial service map | Group B | CMDB/runtime context | CMDB/runtime-context owner | P0 | no fuzzy mapping; unresolved retained |
| Runtime instances | Enables infrastructure-aware scope | instance/pod ID, workload, service ID, host/node ID | validity start/end, namespace | exact workload/instance IDs | valid during selected window | VDT: not delivered | Group B | Kubernetes/CMDB | platform owner | P1 | exact mapping and time applicability |
| Infrastructure/host | Supports host attribution only | host/node ID, environment | OS/zone/cluster, ownership | exact host/node ID | valid during selected window | VDT: not delivered | Group B | CMDB/infrastructure inventory | infrastructure owner | P1 | source/provenance present; never guessed from logs |
| Provenance | Makes evidence auditable | source system, collection method, export time, source hash | owner, filter rules, retention, known gaps | source artifact hash | applies to every delivery | VDT: hashes only; owner/method unknown | Group B | source owners | data steward / source owner | P0 | required metadata or explicit gap |
| RCA labels | Evaluation only, never inference | incident_id, confirmed root service/component/entity | category, resolution, version | incident_id + exact target map | created after resolution as documented | VDT: no governed label | Group C | incident/postmortem system | SRE / incident commander | P0 for evaluation | separate physical package and provenance |

## Optional/later data

`ConfigProfile`, `ServiceBusinessProfile`, `KnownProblem`, `Procedure`, business SLA/criticality, and ownership routing are P2. Missing fields stay null; technical telemetry must not be used to infer them.

## Acquisition groups

- Group A — machine-collectable: logs, metrics, traces, topology, deployments, runtime inventory when an authorized export/API exists.
- Group B — machine-collectable with owner/access: incident system, CMDB, monitoring/tracing backends, CI/CD, runtime context, provenance metadata.
- Group C — authoritative human-reviewed: confirmed root target/category, label verification/independence, service owner, business criticality, resolution facts.

## Evidence and label separation

Evidence packages may contain incident metadata, telemetry, topology, exact identity, runtime context, and provenance. Label packages contain only evaluation targets/provenance and must never flow to normalization, snapshots, candidate generation, profiles, tools, or an agent. Label schema can be validated separately by field name without reading label values.

## Cost-control rule

Tier 0 deterministic code is required for inventory, validation, joins, counts, temporal coverage, package construction, and preflight. Scripted backends are Tier 1 contract tests only. A future live backend may be considered only after deterministic preflight passes and after it separately demonstrates the structured-report, tool, unknown-ID, repair, and abstention contracts with bounded retries. No model is required by this specification.
