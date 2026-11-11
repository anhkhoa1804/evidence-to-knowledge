# V3 Phase 2.8 Metric Evidence

The archived metric contract and diagnostics are in experiments/archive/v3_phase2_8/METRIC_EVIDENCE.json.

| Diagnostic | Result |
| --- | ---: |
| raw metric records | 12 |
| valid observations | 10 |
| invalid observations | 2 |
| resolved targets | 9 |
| unresolved targets | 1 |
| metric series | 7 |
| gauges | 9 |
| counters | 1 |
| sampling metadata coverage | 10 / 10 |
| unit-conflict records | 5 |

Supported units are preserved without conversion. The byte and millisecond request_latency observations remain separate series and produce explicit conflict evidence. No observation is called anomalous, normal, high, low, degraded, or causal.
