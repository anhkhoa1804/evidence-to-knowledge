# VDT Data Owner Request Matrix

| Dataset | Likely source | Required fields | Current gap | Can collect internally? | Access needed? | Responsible owner/team | Exact question to ask | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Incident declarations | incident/SLO system | ID, start/end, exact affected service, environment | 63 missing end times | Unknown | likely | incident-management owner | Can you export authoritative closed incident intervals and declaration source for the governed population? | P0 |
| Logs/events | log platform | timestamp, service ID, event, source, environment | delivered logs do not overlap incidents | likely | likely | logging platform owner | Can you export events covering the same UTC intervals as supplied valid incidents, including collection-gap metadata? | P0 |
| Identity map | CMDB/runtime context | source ID to canonical service mapping | authority/validity unknown | unknown | likely | CMDB or runtime-context owner | Which authoritative exact mapping applies to service/application/workload IDs during these incident windows? | P0 |
| Provenance | delivery/source systems | owner, collection/export/filtering metadata | mostly absent | unknown | likely | data steward / source owner | What collection period, filters, retention, known gaps, and owner apply to each supplied export? | P0 |
| RCA labels | postmortem/incident system | confirmed root target and provenance | no governed root target | no | yes | SRE / incident commander | Can you supply a separate, reviewed root-target package with creation, review, and independence metadata? | P0 for evaluation |
| Metrics | monitoring backend | typed time series | absent | likely | likely | observability team | Which export/API can provide finite typed service metrics over selected incident windows? | P1 |
| Traces | tracing backend | trace/span/parent/service/time/status | absent | likely | likely | observability team | Which export/API can provide incident-overlapping trace spans with exact service identity? | P1 |
| Deployments/changes | CI/CD/change system | change/service/time/type/version | absent | likely | likely | CI/CD owner | Can you export timestamped deployment/change records for selected incident windows? | P1 |
| Runtime/host mapping | Kubernetes/CMDB | instance/workload/service/host validity | absent | likely | likely | platform/infrastructure owner | Can you export exact pod/workload/service/node mappings with validity periods? | P1 |
| Config/business/procedures | governed service systems | profile/criticality/known problem/procedure | absent | unknown | likely | service owner / governance owner | Is there a governed export suitable for a later operational-assistance phase? | P2 |
