# VDT RCA Data Acquisition Request V2

## Current deterministic finding

The current VDT delivery is structurally parseable but is not POC-ready: valid incident windows end no later than `2026-09-05`, while usable logs begin on `2026-09-10`. This is temporal misalignment, not merely low log volume. Incident times must not be changed and CDOI will not widen windows.

## Requested P0 delivery

For the governed population of valid VDT incidents, provide separate evidence and label packages.

| Dataset | Exact request | Time requirement | Required fields |
| --- | --- | --- | --- |
| Incident declarations | Corrected/exported incident windows for governed selected incidents | explicit start/end with offsets | incident_id, start_time, end_time, affected service/component, environment, declaration source |
| Logs/events | Event export for the same incident periods, including bounded pre/inside/post coverage | overlaps each selected incident | event_id, timestamp, service/application ID, event/message code, severity, source system, environment |
| Exact identity map | Authoritative service/application/workload mapping | valid for selected incident windows | raw source ID, canonical service ID, environment, validity where applicable |
| Provenance | Delivery metadata | applies to every artifact | source system, owner role, collection method, export time, filters, known gaps, source hash |
| RCA labels — separate package | Governed evaluation targets only; do not include with evidence | post-resolution creation details | incident_id, confirmed root service/component/entity, optional category, label source/method/reviewer/time/version/independence |

## P1 delivery

Metrics: timestamp, service ID, metric name, finite value, unit, kind, aggregation and sampling metadata; traces: trace/span/parent/service/start/end/status/kind; deployments: change ID/service/timestamp/type/version/status; topology: exact endpoints and declared relation; runtime mapping: pod/instance/workload/service/host with time applicability.

## No new delivery required

Current service inventory, dependency topology, and service-ID map are already delivered structurally. They still require provenance/ownership confirmation and exact endpoint validation. Metrics, traces, changes, instance/host mapping, and governed RCA labels have not been delivered.

## Acceptance rule

CDOI will run `python -m cdoi.vdt_acceptance validate SOURCE --output RESULT.json` before building any POC package. A package is built only for `ACCEPTED_FOR_POC_PREFLIGHT` incidents. Labels are not read by the package builder or POC preflight. No live model call is authorized by this request.
