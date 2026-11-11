# V3 Phase 2.10E — Evaluation Protocol

The frozen chain is:

RCAEval telemetry → research adapter → existing Normalized evidence →
OperationalEvidenceContext → EvidenceSnapshot → frozen incident graph →
frozen CauseCandidates.

The adapter is research-only. It does not alter production preprocessing or
Phase 2.10. Its deterministic service mapping is only case folding, documented
service/services/default prefix stripping, and .svc/.svc.cluster.local suffix
stripping. Anything else remains unresolved.

Ground truth has the independent contract subject_type = SERVICE: exact
normalized candidate subject ID must equal exact normalized root_cause_service.
The adapter accepts no root-cause service, fault label, or root-cause
indicator. Case directory names are opaque identifiers.

The first evaluation window is explicitly ORACLE_WINDOW: five minutes before
through ten minutes after inject_time. Injection time is a benchmark anchor,
not a production detection signal. There is no DETECTION_WINDOW result in this
phase.

The pilot was frozen before telemetry scoring: two repetition-1 cases per
fault selected by a deterministic fault-index rotation across services (12
cases); the other 78 RE2-OB cases are held out. CASE_SPLIT.json is the
authoritative list.

Predeclared ablations are A0 full evidence, A1 metrics removed, A2 logs/events
removed, and A3 traces removed. The adapter preserves unsupplied metric unit
and metric kind as UNIT_UNSPECIFIED and METRIC_KIND_UNSPECIFIED; it does not
treat that absence as malformed data.

An initial no-label resource characterization of the first cached case was
stopped before a candidate output. It showed 246,079 spans in the fixed
window. Before any coverage score, the evaluator therefore froze an
exhaustive-graph ceiling of 100,000 spans per window. Above that ceiling the
result is TECHNICAL_UNAVAILABLE; the evaluator does not sample, truncate,
rank, or change candidate rules.
