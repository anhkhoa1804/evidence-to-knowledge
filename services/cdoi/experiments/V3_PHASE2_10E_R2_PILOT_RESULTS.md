# V3 Phase 2.10E-R2 Pilot Results



```json
{
  "headline": {
    "candidate_reduction_ratio_mean": 0.015384615384615385,
    "candidate_set_size": {
      "max": 1,
      "mean": 0.2,
      "median": 0,
      "min": 0,
      "p90": 1
    },
    "candidate_stage_root_cause_coverage": 0.0,
    "covered_count": 0,
    "evaluated_count": 5,
    "missed_count": 5,
    "statuses": {
      "EVALUATED_GT_MISSED": 5
    },
    "zero_candidate_count": 4,
    "zero_candidate_rate": 0.8
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
    }
  ]
}
```
