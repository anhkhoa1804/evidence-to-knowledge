# Enterprise source boundary (V3 closure)

This document specifies intended source responsibilities, **not verified connectivity or completed ingestion**. The closure process found no configured Coroot/Kibana/Elastic endpoint or source-specific access instructions in the current repository/process. Access asserted outside the repository therefore remains `EXTERNAL_NOT_VERIFIABLE` until a bounded, authorized metadata probe is recorded.

| Intended source | Evidence responsibility | Current state |
| --- | --- | --- |
| Coroot staging | Runtime service/workload inventory, instances, topology/dependency direction, incidents/alerts, health/metrics, eBPF traces, and observed deployments only if its API exposes them | Access, project visibility, schema, time coverage, and data acquisition not verified |
| Kibana staging | Application logs/events and field/time-coverage discovery | Access, data-view visibility, aligned log coverage, and data acquisition not verified |

This does not make either source authoritative for root-cause labels. Incident declaration and confirmed root target require governed provenance and a physically separate label package. A Coroot or Kibana credential belongs only in secure read-only source configuration: never a prompt, EvidenceSnapshot, RCA report, audit artifact, documentation example, or committed file. Use secret-store/environment-variable references, scoped read-only permissions, bounded windowed queries, and redacted connection metadata. No collector or query is implemented by this V3 closure.

Exact service/instance/host joins require an authoritative identity map valid for the incident window. Missing mappings remain unresolved. Timestamps require explicit offsets and UTC normalization without window expansion. Topology is context, not incident telemetry or causal proof. The common package contract is [CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md](CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md); VDT-specific requested corrections remain in [VDT_RCA_DATA_ACQUISITION_REQUEST_V2.md](VDT_RCA_DATA_ACQUISITION_REQUEST_V2.md).
