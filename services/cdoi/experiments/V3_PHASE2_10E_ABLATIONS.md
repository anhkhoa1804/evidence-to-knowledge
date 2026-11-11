# V3 Phase 2.10E — Ablations

A0 (full evidence), A1 (metrics removed), A2 (logs/events removed), and A3
(traces removed) are frozen in the protocol. They were not executed because
the full-evidence pilot case is resource unavailable and the other selected
case telemetry is intentionally not downloaded yet.

No inference is made about metric usefulness. In particular, the frozen
Phase 2.10 eligibility rules use metrics as context rather than an eligibility
trigger, so an eventual unchanged coverage result after A1 would only show
that current rules do not use metrics for eligibility.
