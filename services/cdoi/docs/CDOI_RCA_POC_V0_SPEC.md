# CDOI RCA POC V0 Specification

## Purpose and boundary

CDOI RCA POC V0 is a narrow, development-only, one-incident service-level investigation interface. It turns a supported operational evidence package into exactly one terminal result: `RCA_HYPOTHESIS`, `INSUFFICIENT_EVIDENCE`, or `TECHNICAL_FAILURE`.

An `RCA_HYPOTHESIS` is an evidence-backed investigation hypothesis, not causal proof, calibrated probability, approved knowledge, remediation advice, or a canonical-KG write. `INSUFFICIENT_EVIDENCE` is a validated abstention. A provider, tool, report, package, identity, or temporal failure remains `TECHNICAL_FAILURE`; it is never converted to an abstention.

POC V0 uses frozen deterministic H1/H5 candidate generation and the V2.4 read-only agent contract. It does not change candidate semantics, semantic selection policy, ontology policy, thresholds, retries, repair bounds, or canonical KG behavior.

## Supported package

One package contains one incident. The required files are `manifest.json`, `incident.json`, and a `service_inventory_csv` source. Other current constrained preprocessing sources are optional: `dependency_jsonl`, `log_jsonl`, `metric_observation_csv`, `trace_span_jsonl`, and `deployment_change_csv`. The manifest declares their relative paths; the conventional layout is:

```text
incident_package/
  manifest.json
  incident.json
  inventory/services.csv
  topology/dependencies.jsonl
  telemetry/logs.jsonl
  metrics/metrics.csv
  traces/spans.jsonl
  changes/deployments.csv
```

`manifest.json` must have `schema_version: "cdoi_rca_poc_v0"`, an opaque `incident_id`, package environment/timezone/provenance, and a nonempty `sources` list. Each source has a unique `id`, a supported `type`, and a non-absolute relative `path` that remains in the package. Required schemas for the source files are the existing constrained preprocessing contracts; POC V0 does not infer arbitrary CSV or JSONL schemas.

`incident.json` must have the same opaque `incident_id`, timezone-qualified `start_time` and `end_time`, an optional environment/summary, and a nonempty `affected_service_ids` string list. Times are normalized to UTC. Service identity is exact only: no alias, nearest-name, fuzzy, or model-based resolution occurs.

The manifest and incident files must not contain label-like fields including `root_service`, `root_cause`, `root_component`, `root_entity`, `ground_truth`, `expected_answer`, `confirmed_diagnosis`, or evaluator metadata. Their presence is `INPUT_SCHEMA_ERROR`. A future label package is separate from POC execution and is never required or read.

`--preflight-only` is an audit/preparation mode, not an RCA judgement. The current V0 serializer emits public status `INSUFFICIENT_EVIDENCE` with limitation `PREFLIGHT_ONLY_NOT_A_SEMANTIC_ABSTENTION`; consumers must use `RUNTIME.json.execution_mode` and that limitation to exclude it from semantic abstention metrics. This status overlap is a known V0 contract caveat and must be addressed by a separately versioned interface before production use.

## Temporal and data-quality policy

The POC retains normalized records only when they overlap the declared incident window according to the current evidence-snapshot contract. Preflight records per modality the accepted count, earliest/latest selected timestamp, overlap status, and rejected preprocessing-record count. If none of logs, metrics, traces, or changes overlap the window, execution terminates as `TEMPORAL_ALIGNMENT_ERROR`. Missing individual modalities are visible warnings, not invented evidence.

Unresolved incident anchor identity is `IDENTITY_RESOLUTION_ERROR`. Other unresolved source identity remains an auditable data-quality warning. Topology is contextual and not itself incident telemetry or root-cause ground truth.

## Orchestration

```text
Incident Package
      ↓
Input Validation
      ↓
Operational Normalization
      ↓
EvidenceSnapshot
      ↓
IncidentEvidenceGraph
      ↓
Frozen H1/H5 Candidate Generation
      ↓
CandidateEvidenceProfiles
      ↓
Read-only RCA Tools
      ↓
V2.4 Agent (only when explicitly configured)
      ↓
Strict Report Validation
      ↓
POC Result + Audit Bundle
```

There is no path from an agent to remediation, ontology commitment, or canonical KG mutation.

The live option uses one explicitly configured OpenAI-compatible provider: `CDOI_POC_RCA_BASE_URL`, `CDOI_POC_RCA_API_KEY_ENV`, and optional `CDOI_POC_RCA_MODEL`, host header, timeout, and output-token variables. It retains V2.4's eight read-only tool-call limit, zero transport retries, one tool-action correction, one report repair, exact allowed candidate/evidence IDs, candidate-scoped citations, and fail-closed validation. There is no automatic provider fallback.

## Public result and audit

`FINAL_RESULT.json` uses `cdoi_rca_poc_result_v0` and includes the terminal status, concise summary, hypotheses, candidates considered, cited evidence IDs, missing modalities, data/technical warnings, safe runtime metadata, limitations, and optional stable public error code. It never includes a confidence probability.

Each output directory contains input validation, normalization and preflight summaries, snapshot summary, incident graph, candidates, profiles, optional agent trace, `FINAL_RESULT.json`, a human-readable `RCA_REPORT.md`, safe `RUNTIME.json`, `HASHES.json`, and `MANIFEST.json`. Internal normalized package copies are included only to make execution inputs auditable; credentials, authorization headers, and raw provider text are not written.

Public failure categories include `INPUT_SCHEMA_ERROR`, `TEMPORAL_ALIGNMENT_ERROR`, `IDENTITY_RESOLUTION_ERROR`, `NO_USABLE_EVIDENCE`, `CANDIDATE_GENERATION_ERROR`, `PROVIDER_TIMEOUT`, `PROVIDER_TRANSPORT_ERROR`, `TOOL_CONTRACT_FAILURE`, `REPORT_CONTRACT_FAILURE`, `UNKNOWN_EVIDENCE_REFERENCE`, `UNKNOWN_CANDIDATE_REFERENCE`, and `INTERNAL_ERROR`.

## Run

```powershell
python -m cdoi.rca_poc run data/poc_demo/incident-001 --output experiments/poc_runs/demo-001
```

Add `--live` only after the explicit provider variables are configured. Without it, the POC deliberately returns an auditable technical outcome rather than fabricating a diagnosis. This package is consumed development/demo material only; it is not independent validation.

For deterministic data readiness and cost control, use `--preflight-only`. It executes the same package validation, normalization, exact-ID/time checks, `EvidenceSnapshot`, `IncidentEvidenceGraph`, frozen H1/H5 candidate generation, and `CandidateEvidenceProfiles`, then stops before any provider, model, tool, repair, or report-generation invocation. It writes `PREFLIGHT_ONLY.json`; its terminal wrapper result is explicitly marked `PREFLIGHT_ONLY_NOT_A_SEMANTIC_ABSTENTION` and must not be interpreted as an RCA abstention.

## Non-goals

POC V0 is not a general data lake or arbitrary schema ingestion tool, fuzzy entity resolver, causal graph inducer, model fine-tuning system, generic multi-provider router, automatic corrective-action system, business-impact prioritizer, ontology alignment runtime, canonical-KG writer, production HA/SLO/multi-tenant service, or independent RCA-validation result.
