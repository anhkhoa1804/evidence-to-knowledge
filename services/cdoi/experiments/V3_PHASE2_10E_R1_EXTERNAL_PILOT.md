# V3 Phase 2.10E-R1 External Pilot

The original blocked case is now EVALUATED with the unchanged dataset revision,
case ID, service mapping, ORACLE_WINDOW, and frozen rules.

| Case | Raw / valid / processed window traces | Candidate count | Eligible services | GT coverage | Status |
| --- | ---: | ---: | ---: | --- | --- |
| re2ob_checkoutservice_cpu_1 | 391,997 / 391,997 / 246,079 | 0 | 13 | no | GROUND_TRUTH_MISSED |

This is the first external candidate-stage result. It is a genuine observed
candidate miss: no frozen CHANGE, ERROR event, or ERROR trace rule triggered.
It is not caused by the former materialization limit.

Eleven frozen pilot cases are still not cached. They retain their original
case IDs and are reported as DOWNLOAD_FAILED / CACHE_MISSING_REQUIRED_TELEMETRY
without substituting cases.
