# V3 Phase 2.10E — Frozen CauseCandidate Baseline

Phase 2.10 was frozen before external evaluation. The graph/candidate
implementation SHA-256 is
3e4a8ac8e2b33b72f042a3730c8d31130220079a9420df635843588bfa981bd0.
The Phase 2.10 demo artifacts and contract hashes are recorded in
archive/v3_phase2_10e_rcaeval/FROZEN_PHASE210.json.

## Pilot execution result

No candidate coverage number is reported. Of 12 preselected RE2-OB pilot
cases, eleven are not cached and one cached case
re2ob_checkoutservice_cpu_1 is TECHNICAL_UNAVAILABLE: its fixed
ORACLE_WINDOW contains 246,079 trace spans, exceeding the 100,000-span
exhaustive-graph limit frozen after a preliminary no-label resource
characterization and before any coverage score.

This is not GROUND_TRUTH_MISSED, NO_CANDIDATE, zero coverage, or a negative
RCA result. It is an external scalability/reliability result for the frozen
graph representation. Candidate set size, reduction ratio, fault and service
breakdowns, and trivial-baseline comparison remain unavailable until the
evaluation infrastructure can execute without changing the frozen candidate
mechanism.
