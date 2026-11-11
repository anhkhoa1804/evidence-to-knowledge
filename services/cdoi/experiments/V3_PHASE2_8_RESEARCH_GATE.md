# V3 Phase 2.8 Research Gate

| Area | Status | Evidence |
| --- | --- | --- |
| metric preprocessing | SUPPORTED | Constrained optional CSV emits typed immutable observations and issues. |
| metric identity | SUPPORTED | Exact service ID plus unit/kind/aggregation-aware series key. |
| unit semantics | PARTIALLY_SUPPORTED | Supported units are preserved and conflicts are explicit; no conversion catalog exists. |
| metric-kind semantics | SUPPORTED | Declared gauge/counter kinds remain distinct; no kind inference. |
| sampling metadata | SUPPORTED | Declared interval is retained; no inference from neighboring samples. |
| aggregation semantics | SUPPORTED | Raw, avg, and p95 remain distinct series dimensions. |
| temporal filtering | SUPPORTED | Exact inclusive UTC membership reuses Phase 2.7 semantics. |
| exact entity correlation | SUPPORTED | Unknown metric targets are explicit and excluded from selected scope. |
| snapshot integration | SUPPORTED | Metrics enter the existing readonly context and snapshot artifact. |
| snapshot determinism | SUPPORTED | Stable ordering and content-derived snapshot IDs are tested. |
| metric provenance | SUPPORTED | Raw record, source file, and manifest chain is retained. |
| counter safety | SUPPORTED | Raw counter readings are preserved; no window-total interpretation. |
| anomaly-separation safety | SUPPORTED | No anomaly labels, baseline learning, thresholds, or trend claims. |
| causal-separation safety | SUPPORTED | No causal scoring, relation, ranking, or RCA output. |
| trace readiness | PARTIALLY_SUPPORTED | Context accepts another modality, but trace/span/parent/sampling contracts remain absent. |
| RCA readiness | NOT_IMPLEMENTED | Candidate causes, reasoning, abstention, ground truth, and evaluation protocol remain absent. |

Metrics intake is implemented. Distributed traces, anomaly detection, candidate-cause generation, RCA ranking, and causal inference are not implemented.
