# V3 Phase 2.12 Protected Holdout Validation

This is a one-shot validation of frozen, unranked Phase 2.11 candidate generation. It does not rank candidates or establish causality. Every holdout candidate artifact was frozen before its GT evaluation artifact was written.

```json
{
  "ablations": {
    "H0_FROZEN_PHASE210": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.998001998001998,
        "median": 1.0
      },
      "candidate_service_ratio": {
        "mean": 0.001998001998001998,
        "median": 0.0
      },
      "candidate_set_size": {
        "max": 1,
        "mean": 0.025974025974025976,
        "median": 0,
        "min": 0,
        "p90": 0,
        "p95": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "coverage_wilson_95_interval": [
        0,
        0.04751842528243408
      ],
      "covered_count": 0,
      "evaluated_count": 77,
      "missed_count": 77,
      "statuses": {
        "EVALUATED_GT_MISSED": 77
      },
      "zero_candidate_count": 75,
      "zero_candidate_rate": 0.974025974025974
    },
    "H1_METRIC": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.7770229770229771,
        "median": 0.8461538461538461
      },
      "candidate_service_ratio": {
        "mean": 0.222977022977023,
        "median": 0.15384615384615385
      },
      "candidate_set_size": {
        "max": 12,
        "mean": 2.896103896103896,
        "median": 2,
        "min": 1,
        "p90": 5,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.9524815747175658,
        0.9999999999999999
      ],
      "covered_count": 77,
      "evaluated_count": 77,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 77
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "H2_TRACE_PARTICIPATION": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.8857808857808858,
        "median": 1.0
      },
      "candidate_service_ratio": {
        "mean": 0.11421911421911422,
        "median": 0.0
      },
      "candidate_set_size": {
        "max": 7,
        "mean": 1.4935064935064934,
        "median": 0,
        "min": 0,
        "p90": 4,
        "p95": 6
      },
      "candidate_stage_root_cause_coverage": 0.16883116883116883,
      "coverage_wilson_95_interval": [
        0.10140668708276007,
        0.2677288932991118
      ],
      "covered_count": 13,
      "evaluated_count": 77,
      "missed_count": 64,
      "statuses": {
        "EVALUATED_GT_COVERED": 13,
        "EVALUATED_GT_MISSED": 64
      },
      "zero_candidate_count": 40,
      "zero_candidate_rate": 0.5194805194805194
    },
    "H3_BOUNDED_TOPOLOGY": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.998001998001998,
        "median": 1.0
      },
      "candidate_service_ratio": {
        "mean": 0.001998001998001998,
        "median": 0.0
      },
      "candidate_set_size": {
        "max": 1,
        "mean": 0.025974025974025976,
        "median": 0,
        "min": 0,
        "p90": 0,
        "p95": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "coverage_wilson_95_interval": [
        0,
        0.04751842528243408
      ],
      "covered_count": 0,
      "evaluated_count": 77,
      "missed_count": 77,
      "statuses": {
        "EVALUATED_GT_MISSED": 77
      },
      "zero_candidate_count": 75,
      "zero_candidate_rate": 0.974025974025974
    },
    "H4_TEMPORAL_CHANGE": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.998001998001998,
        "median": 1.0
      },
      "candidate_service_ratio": {
        "mean": 0.001998001998001998,
        "median": 0.0
      },
      "candidate_set_size": {
        "max": 1,
        "mean": 0.025974025974025976,
        "median": 0,
        "min": 0,
        "p90": 0,
        "p95": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "coverage_wilson_95_interval": [
        0,
        0.04751842528243408
      ],
      "covered_count": 0,
      "evaluated_count": 77,
      "missed_count": 77,
      "statuses": {
        "EVALUATED_GT_MISSED": 77
      },
      "zero_candidate_count": 75,
      "zero_candidate_rate": 0.974025974025974
    },
    "H5_COMBINED": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6876456876456877,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.3123543123543124,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 12,
        "mean": 4.064935064935065,
        "median": 4,
        "min": 1,
        "p90": 7,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.9524815747175658,
        0.9999999999999999
      ],
      "covered_count": 77,
      "evaluated_count": 77,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 77
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    }
  },
  "fault_groups": {
    "CPU": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6725838264299803,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.32741617357001973,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 7,
        "mean": 4.3076923076923075,
        "median": 4,
        "min": 2,
        "p90": 6,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7719046276458016,
        0.9999999999999999
      ],
      "covered_count": 13,
      "evaluated_count": 13,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 13
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "DELAY": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6745562130177515,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.3254437869822485,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 7,
        "mean": 4.230769230769231,
        "median": 4,
        "min": 2,
        "p90": 5,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7719046276458016,
        0.9999999999999999
      ],
      "covered_count": 13,
      "evaluated_count": 13,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 13
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "DISK": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6607495069033531,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.33925049309664695,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 7,
        "mean": 4.384615384615385,
        "median": 4,
        "min": 2,
        "p90": 7,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7719046276458016,
        0.9999999999999999
      ],
      "covered_count": 13,
      "evaluated_count": 13,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 13
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "LOSS": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6568047337278107,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.3431952662721894,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 12,
        "mean": 4.461538461538462,
        "median": 4,
        "min": 1,
        "p90": 8,
        "p95": 12
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7719046276458016,
        0.9999999999999999
      ],
      "covered_count": 13,
      "evaluated_count": 13,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 13
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "MEM": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6730769230769231,
        "median": 0.6923076923076923
      },
      "candidate_service_ratio": {
        "mean": 0.3269230769230769,
        "median": 0.3076923076923077
      },
      "candidate_set_size": {
        "max": 10,
        "mean": 4.25,
        "median": 4.0,
        "min": 1,
        "p90": 7,
        "p95": 10
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7575059933447592,
        1
      ],
      "covered_count": 12,
      "evaluated_count": 12,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 12
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "SOCKET": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.7869822485207101,
        "median": 0.7692307692307692
      },
      "candidate_service_ratio": {
        "mean": 0.21301775147928995,
        "median": 0.23076923076923078
      },
      "candidate_set_size": {
        "max": 7,
        "mean": 2.769230769230769,
        "median": 3,
        "min": 1,
        "p90": 5,
        "p95": 7
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "coverage_wilson_95_interval": [
        0.7719046276458016,
        0.9999999999999999
      ],
      "covered_count": 13,
      "evaluated_count": 13,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 13
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    }
  },
  "h1_vs_h5": {
    "both_cover": [
      "re2ob_checkoutservice_cpu_2",
      "re2ob_checkoutservice_cpu_3",
      "re2ob_checkoutservice_delay_1",
      "re2ob_checkoutservice_delay_2",
      "re2ob_checkoutservice_delay_3",
      "re2ob_checkoutservice_disk_1",
      "re2ob_checkoutservice_disk_2",
      "re2ob_checkoutservice_disk_3",
      "re2ob_checkoutservice_loss_1",
      "re2ob_checkoutservice_loss_2",
      "re2ob_checkoutservice_loss_3",
      "re2ob_checkoutservice_mem_2",
      "re2ob_checkoutservice_mem_3",
      "re2ob_checkoutservice_socket_2",
      "re2ob_checkoutservice_socket_3",
      "re2ob_currencyservice_cpu_1",
      "re2ob_currencyservice_cpu_2",
      "re2ob_currencyservice_cpu_3",
      "re2ob_currencyservice_delay_1",
      "re2ob_currencyservice_delay_2",
      "re2ob_currencyservice_delay_3",
      "re2ob_currencyservice_disk_2",
      "re2ob_currencyservice_disk_3",
      "re2ob_currencyservice_loss_2",
      "re2ob_currencyservice_loss_3",
      "re2ob_currencyservice_mem_1",
      "re2ob_currencyservice_mem_2",
      "re2ob_currencyservice_mem_3",
      "re2ob_currencyservice_socket_1",
      "re2ob_currencyservice_socket_2",
      "re2ob_currencyservice_socket_3",
      "re2ob_emailservice_cpu_2",
      "re2ob_emailservice_cpu_3",
      "re2ob_emailservice_delay_2",
      "re2ob_emailservice_delay_3",
      "re2ob_emailservice_disk_1",
      "re2ob_emailservice_disk_2",
      "re2ob_emailservice_disk_3",
      "re2ob_emailservice_loss_1",
      "re2ob_emailservice_loss_2",
      "re2ob_emailservice_loss_3",
      "re2ob_emailservice_mem_2",
      "re2ob_emailservice_mem_3",
      "re2ob_emailservice_socket_2",
      "re2ob_emailservice_socket_3",
      "re2ob_productcatalogservice_cpu_1",
      "re2ob_productcatalogservice_cpu_2",
      "re2ob_productcatalogservice_cpu_3",
      "re2ob_productcatalogservice_delay_1",
      "re2ob_productcatalogservice_delay_2",
      "re2ob_productcatalogservice_delay_3",
      "re2ob_productcatalogservice_disk_1",
      "re2ob_productcatalogservice_disk_2",
      "re2ob_productcatalogservice_disk_3",
      "re2ob_productcatalogservice_loss_2",
      "re2ob_productcatalogservice_loss_3",
      "re2ob_productcatalogservice_mem_2",
      "re2ob_productcatalogservice_mem_3",
      "re2ob_productcatalogservice_socket_1",
      "re2ob_productcatalogservice_socket_2",
      "re2ob_productcatalogservice_socket_3",
      "re2ob_recommendationservice_cpu_1",
      "re2ob_recommendationservice_cpu_2",
      "re2ob_recommendationservice_cpu_3",
      "re2ob_recommendationservice_delay_2",
      "re2ob_recommendationservice_delay_3",
      "re2ob_recommendationservice_disk_2",
      "re2ob_recommendationservice_disk_3",
      "re2ob_recommendationservice_loss_1",
      "re2ob_recommendationservice_loss_2",
      "re2ob_recommendationservice_loss_3",
      "re2ob_recommendationservice_mem_1",
      "re2ob_recommendationservice_mem_2",
      "re2ob_recommendationservice_mem_3",
      "re2ob_recommendationservice_socket_1",
      "re2ob_recommendationservice_socket_2",
      "re2ob_recommendationservice_socket_3"
    ],
    "h5_gt_recoveries_beyond_h1": [],
    "mean_candidate_expansion_h5_minus_h1": 1.1688311688311688,
    "neither": [],
    "only_h1": [],
    "only_h5": [],
    "schema_version": "v3_phase2_12_h1_vs_h5_v1"
  },
  "integrity": {
    "candidate_schema": {
      "candidate_status": "CANDIDATE_UNEVALUATED",
      "hypothesis_version": "evidence_aware_hypothesis_generation_v1",
      "status": "PASS"
    },
    "dataset_revision": {
      "expected": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e",
      "status": "PASS",
      "stored": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
    },
    "holdout_split": {
      "case_count": 78,
      "sha256": "3e9ff2332bd9bd7e527d0961d87b6071c11ef0962c4ae5d37593b0202d91b566",
      "status": "PASS"
    },
    "hypothesis_generator_source": {
      "actual_sha256": "e4ecc00044eb8af21c02d4dbb3f8f85f6c196c20edeca2cba8e7714ecffe5d1c",
      "detail": "Phase 2.11 archive hashes its artifacts but does not contain an individual implementation-source digest; current source is frozen by this Phase 2.12 preregistration.",
      "status": "DOCUMENTED_PRE_EXISTING_DISCREPANCY"
    },
    "phase211_configuration": {
      "actual": {
        "baseline_seconds": 300,
        "metric_median_relative_shift": 0.5,
        "metric_minimum_observations": 60,
        "metric_persistent_fraction": 0.6,
        "schema_version": "evidence_aware_hypothesis_generation_v1",
        "trace_minimum_spans_per_partition": 100,
        "trace_volume_shift_factor": 2.0
      },
      "status": "PASS",
      "stored": {
        "baseline_seconds": 300,
        "metric_median_relative_shift": 0.5,
        "metric_minimum_observations": 60,
        "metric_persistent_fraction": 0.6,
        "schema_version": "evidence_aware_hypothesis_generation_v1",
        "trace_minimum_spans_per_partition": 100,
        "trace_volume_shift_factor": 2.0
      }
    },
    "phase211_hashes": {
      "sha256": "284588a85e897727f8242b932c5a2a6abc98ad3788281784e70b47ed66786a2b",
      "status": "PASS"
    },
    "phase211_manifest": {
      "sha256": "8a6b081ab9065ae13243536496ed0b6e8986f655aa8a03d7837a8f603a26211f",
      "status": "PASS"
    },
    "pilot_split": {
      "sha256": "dac2e9fd334a902c9ba7ceadd2b4f10595e4182bed37b8553134f38455d45e55",
      "status": "PASS"
    },
    "sqlite_store_source": {
      "actual_sha256": "27be5119c306ed62d6bba3da9154732e2926bfdbf4a54890779a4a209c61affd",
      "detail": "Phase 2.11 archive does not contain an individual store-source digest.",
      "status": "DOCUMENTED_PRE_EXISTING_DISCREPANCY",
      "store_version": "incident_evidence_store_v1"
    }
  },
  "performance": {
    "boundedness": "SQLite indexed trace aggregation; no full trace execution graph materialized.",
    "max_sqlite_bytes": 172429312,
    "mean_seconds": 28.210373538959765,
    "mean_spans_per_second": 8402.374015030178,
    "mean_sqlite_bytes": 153144280.1038961,
    "median_seconds": 29.256243899988476,
    "p90_seconds": 32.01220130000729,
    "total_seconds": 2172.198762499902
  },
  "primary_h5": {
    "candidate_reduction_relative_to_all_services": {
      "mean": 0.6876456876456877,
      "median": 0.6923076923076923
    },
    "candidate_service_ratio": {
      "mean": 0.3123543123543124,
      "median": 0.3076923076923077
    },
    "candidate_set_size": {
      "max": 12,
      "mean": 4.064935064935065,
      "median": 4,
      "min": 1,
      "p90": 7,
      "p95": 7
    },
    "candidate_stage_root_cause_coverage": 1.0,
    "coverage_wilson_95_interval": [
      0.9524815747175658,
      0.9999999999999999
    ],
    "covered_count": 77,
    "evaluated_count": 77,
    "missed_count": 0,
    "statuses": {
      "EVALUATED_GT_COVERED": 77
    },
    "zero_candidate_count": 0,
    "zero_candidate_rate": 0.0
  },
  "research_gate": {
    "decision": "HOLDOUT_VALIDATION_TECHNICALLY_INCOMPLETE",
    "holdout_consumed_once": true,
    "holdout_generation_before_gt": "SUPPORTED",
    "next_step": "Preserve this holdout result. Do not tune Phase 2.11 on these cases.",
    "no_phase211_tuning": "SUPPORTED",
    "primary_endpoint": "H5_COMBINED",
    "schema_version": "v3_phase2_12_research_gate_v1"
  },
  "trace_incremental_value": {
    "case_count_trace_adds_gt": 0,
    "cases_trace_adds_only_non_gt_candidates": [
      "re2ob_checkoutservice_cpu_2",
      "re2ob_checkoutservice_cpu_3",
      "re2ob_checkoutservice_disk_1",
      "re2ob_checkoutservice_loss_2",
      "re2ob_checkoutservice_mem_3",
      "re2ob_checkoutservice_socket_3",
      "re2ob_currencyservice_cpu_2",
      "re2ob_currencyservice_disk_2",
      "re2ob_currencyservice_mem_2",
      "re2ob_emailservice_cpu_2",
      "re2ob_emailservice_cpu_3",
      "re2ob_emailservice_delay_2",
      "re2ob_emailservice_delay_3",
      "re2ob_emailservice_disk_1",
      "re2ob_emailservice_disk_2",
      "re2ob_emailservice_disk_3",
      "re2ob_emailservice_loss_1",
      "re2ob_emailservice_loss_2",
      "re2ob_emailservice_loss_3",
      "re2ob_emailservice_mem_2",
      "re2ob_emailservice_socket_2",
      "re2ob_emailservice_socket_3",
      "re2ob_productcatalogservice_cpu_1",
      "re2ob_productcatalogservice_cpu_2",
      "re2ob_productcatalogservice_disk_1",
      "re2ob_productcatalogservice_disk_3",
      "re2ob_productcatalogservice_mem_2",
      "re2ob_productcatalogservice_socket_3",
      "re2ob_recommendationservice_cpu_1",
      "re2ob_recommendationservice_cpu_2",
      "re2ob_recommendationservice_delay_3",
      "re2ob_recommendationservice_disk_2",
      "re2ob_recommendationservice_disk_3"
    ],
    "h5_gt_recoveries_beyond_h1": [],
    "interpretation_boundary": "Additional candidates are not characterized as false causes or causal effects.",
    "mean_additional_candidates_h5_minus_h1": 1.1688311688311688,
    "schema_version": "v3_phase2_12_trace_incremental_value_v1"
  }
}
```

The holdout is consumed and must not be used to tune Phase 2.11. Non-GT candidates are candidate expansion, not causal false positives.
