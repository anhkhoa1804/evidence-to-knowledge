# Robustness Results

| Experiment | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Bridge P | Review Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| continual_orders | cdoi_bench | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| CDOI_CONFLICTS | cdoi_conflicts | 2.0 | N/A | N/A | N/A | N/A | N/A | N/A |
| CDOI_EVIDENCE_DEGRADATION:Full | cdoi_bench | 14 | 1.0 | 0.0 | 0.21428571428571427 | 1.0 | 1.0 | 0.21428571428571427 |
| CDOI_EVIDENCE_DEGRADATION:NoDefinition | cdoi_bench | 14 | 1.0 | 0.0 | 0.21428571428571427 | 1.0 | 1.0 | 0.21428571428571427 |
| CDOI_EVIDENCE_DEGRADATION:NoRelations | cdoi_bench | 14 | 0.5 | 0.0 | 0.35714285714285715 | 0.5 | 1.0 | 0.35714285714285715 |
| CDOI_EVIDENCE_DEGRADATION:NoNeighborhood | cdoi_bench | 14 | 0.8571428571428571 | 0.0 | 0.35714285714285715 | 1.0 | 1.0 | 0.35714285714285715 |
| CDOI_EVIDENCE_DEGRADATION:NoDomain | cdoi_bench | 14 | 0.8 | 0.0 | 0.2857142857142857 | 0.75 | 1.0 | 0.2857142857142857 |
| CDOI_EVIDENCE_DEGRADATION:LabelOnly | cdoi_bench | 14 | 0.0 | 0.0 | 0.42857142857142855 | 0.25 | 1.0 | 0.42857142857142855 |
| CDOI_NOISE:0 | cdoi_bench | 14 | 1.0 | 0.0 | 0.21428571428571427 | 1.0 | 1.0 | 0.21428571428571427 |
| CDOI_NOISE:5 | cdoi_bench | 14 | 1.0 | 0.0 | 0.2857142857142857 | 1.0 | 1.0 | 0.2857142857142857 |
| CDOI_NOISE:10 | cdoi_bench | 14 | 1.0 | 0.0 | 0.2857142857142857 | 1.0 | 1.0 | 0.2857142857142857 |
| CDOI_NOISE:20 | cdoi_bench | 14 | 1.0 | 0.0 | 0.2857142857142857 | 1.0 | 1.0 | 0.2857142857142857 |
| CDOI_NOISE:30 | cdoi_bench | 14 | 0.8 | 0.0 | 0.2857142857142857 | 0.75 | 1.0 | 0.2857142857142857 |
| CDOI_LATE_EVIDENCE | cdoi_late_evidence | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Scope

Evidence/noise rows are controlled CDOI-Bench transformations with case-level origin metadata. Late-evidence and order outputs retain their detailed audit and structural records in machine-readable result files. They are robustness analysis, not estimates of enterprise data quality.
