# V3 Phase 2.10E-R2A Pilot Results

```json
{
  "fault_type_breakdown": {
    "CPU": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    },
    "DELAY": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    },
    "DISK": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    },
    "LOSS": {
      "candidate_reduction_ratio_mean": 0.038461538461538464,
      "candidate_set_size": {
        "max": 1,
        "mean": 0.5,
        "median": 0.5,
        "min": 0,
        "p90": 1
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 1,
      "zero_candidate_rate": 0.5
    },
    "MEM": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    },
    "SOCKET": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    }
  },
  "headline": {
    "candidate_reduction_ratio_mean": 0.006410256410256411,
    "candidate_set_size": {
      "max": 1,
      "mean": 0.08333333333333333,
      "median": 0.0,
      "min": 0,
      "p90": 0
    },
    "candidate_stage_root_cause_coverage": 0.0,
    "covered_count": 0,
    "evaluated_count": 12,
    "missed_count": 12,
    "statuses": {
      "EVALUATED_GT_MISSED": 12
    },
    "zero_candidate_count": 11,
    "zero_candidate_rate": 0.9166666666666666
  },
  "results": [
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_checkoutservice_cpu_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-7f50127d9549f745d2274b92",
      "ground_truth_service_id": "checkoutservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_currencyservice_disk_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-b77d688b9a37fb4d8097224c",
      "ground_truth_service_id": "currencyservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_emailservice_socket_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-2215e4fea2ed1c50d7daef52",
      "ground_truth_service_id": "emailservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 1,
      "candidate_reduction_ratio": 0.07692307692307693,
      "candidate_subject_ids": [
        "frontendservice"
      ],
      "candidates": [
        {
          "candidate_artifact_sha256": "7c305dfe77d88875d0a7728f3aa829e51f2611f26fa20779735e30f06c54b1bf",
          "candidate_id": "candidate-4d7ee71b8b768a2e7850f46f",
          "candidate_kind": "OBSERVED_ERROR_CANDIDATE",
          "candidate_subject": "frontendservice",
          "context_evidence": {
            "METRIC_OBSERVATION": 0
          },
          "generation_rule_ids": [
            "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1"
          ],
          "supporting_evidence": {
            "TRACE_SPAN": 4
          }
        }
      ],
      "case_id": "re2ob_productcatalogservice_loss_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [
        "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1"
      ],
      "graph_id": "iegview-938e18d154f1979f88b89d4d",
      "ground_truth_service_id": "productcatalogservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_recommendationservice_delay_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-2dac39527e1803aafc7e8869",
      "ground_truth_service_id": "recommendationservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_checkoutservice_mem_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-affa8440ce3770e0b15ee697",
      "ground_truth_service_id": "checkoutservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_emailservice_cpu_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-4628a74192feaeda412c39cc",
      "ground_truth_service_id": "emailservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_emailservice_delay_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-41028c9cd296c61dc2a8a84f",
      "ground_truth_service_id": "emailservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_productcatalogservice_mem_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-3225613db76d45a19fcaf3b5",
      "ground_truth_service_id": "productcatalogservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_recommendationservice_disk_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-18d8b7413b44b91c2303a1df",
      "ground_truth_service_id": "recommendationservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_checkoutservice_socket_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-3191cec13537bf103ffac2ea",
      "ground_truth_service_id": "checkoutservice",
      "status": "EVALUATED_GT_MISSED"
    },
    {
      "candidate_count": 0,
      "candidate_reduction_ratio": 0.0,
      "candidate_subject_ids": [],
      "candidates": [],
      "case_id": "re2ob_currencyservice_loss_1",
      "covered": false,
      "eligible_service_count": 13,
      "generation_rules": [],
      "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
      "ground_truth_service_id": "currencyservice",
      "status": "EVALUATED_GT_MISSED"
    }
  ],
  "root_cause_service_breakdown": {
    "checkoutservice": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 3,
      "missed_count": 3,
      "statuses": {
        "EVALUATED_GT_MISSED": 3
      },
      "zero_candidate_count": 3,
      "zero_candidate_rate": 1.0
    },
    "currencyservice": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    },
    "emailservice": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 3,
      "missed_count": 3,
      "statuses": {
        "EVALUATED_GT_MISSED": 3
      },
      "zero_candidate_count": 3,
      "zero_candidate_rate": 1.0
    },
    "productcatalogservice": {
      "candidate_reduction_ratio_mean": 0.038461538461538464,
      "candidate_set_size": {
        "max": 1,
        "mean": 0.5,
        "median": 0.5,
        "min": 0,
        "p90": 1
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 1,
      "zero_candidate_rate": 0.5
    },
    "recommendationservice": {
      "candidate_reduction_ratio_mean": 0.0,
      "candidate_set_size": {
        "max": 0,
        "mean": 0.0,
        "median": 0.0,
        "min": 0,
        "p90": 0
      },
      "candidate_stage_root_cause_coverage": 0.0,
      "covered_count": 0,
      "evaluated_count": 2,
      "missed_count": 2,
      "statuses": {
        "EVALUATED_GT_MISSED": 2
      },
      "zero_candidate_count": 2,
      "zero_candidate_rate": 1.0
    }
  },
  "schema_version": "v3_phase2_10e_r2a_pilot_results_v1"
}
```
