# V3 Phase 2.7 Operational Evidence Context Demo

The demo declares inc-001 over [2026-09-18T09:50:00Z, 2026-09-18T10:10:00Z], with exact affected ID payment-service and ONE_HOP scope. The generated result is persisted in experiments/archive/v3_phase2_7/DEMO_RESULT.json and the snapshot in incident_snapshots/inc-001.json.

| Item | Count | Interpretation |
| --- | ---: | --- |
| direct entities | 1 | payment-service |
| expanded entities | 3 | direct entity plus exact inventory neighbors |
| directed relations | 2 | one inbound calls and one outbound reads_from |
| events | 2 | in-window events for the selected one-hop entity scope |
| changes | 2 | in-window changes for the selected one-hop entity scope |
| semantic terms | 0 | no safe exact-ID linkage to glossary IDs |
| unresolved | 7 | retained raw-preprocessing issues; no silent loss |

One trace is snapshot to relation evidence ev-74dec7967eb0bd5ff5ae70e0 to raw record ev-74dec7967eb0bd5ff5ae70e0 to topology/dependencies.jsonl record 1 to the demo manifest. The persisted result also records a payment-service inventory trace.

The co-occurrence of deployment/configuration changes and log events is only time-bounded evidence organization. This demo does not determine a cause.
