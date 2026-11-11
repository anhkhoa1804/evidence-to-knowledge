# V3 Phase 2.10E-R2 Trivial Baselines



```json
{
  "baselines": {
    "ALL_SERVICES": {
      "headline": {
        "candidate_reduction_ratio_mean": 1.0,
        "candidate_set_size": {
          "max": 13,
          "mean": 13.0,
          "median": 13,
          "min": 13,
          "p90": 13
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 5,
        "evaluated_count": 5,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 5
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "per_case": [
        {
          "baseline": "ALL_SERVICES",
          "candidate_count": 13,
          "candidate_reduction_ratio": 1.0,
          "candidate_subject_ids": [
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "frontend",
            "frontend-external",
            "frontendservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "redis",
            "shippingservice"
          ],
          "case_id": "re2ob_checkoutservice_cpu_1",
          "covered": true,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_COVERED"
        },
        {
          "baseline": "ALL_SERVICES",
          "candidate_count": 13,
          "candidate_reduction_ratio": 1.0,
          "candidate_subject_ids": [
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "frontend",
            "frontend-external",
            "frontendservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "redis",
            "shippingservice"
          ],
          "case_id": "re2ob_currencyservice_disk_1",
          "covered": true,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_COVERED"
        },
        {
          "baseline": "ALL_SERVICES",
          "candidate_count": 13,
          "candidate_reduction_ratio": 1.0,
          "candidate_subject_ids": [
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "frontend",
            "frontend-external",
            "frontendservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "redis",
            "shippingservice"
          ],
          "case_id": "re2ob_emailservice_socket_1",
          "covered": true,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_COVERED"
        },
        {
          "baseline": "ALL_SERVICES",
          "candidate_count": 13,
          "candidate_reduction_ratio": 1.0,
          "candidate_subject_ids": [
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "frontend",
            "frontend-external",
            "frontendservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "redis",
            "shippingservice"
          ],
          "case_id": "re2ob_productcatalogservice_loss_1",
          "covered": true,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_COVERED"
        },
        {
          "baseline": "ALL_SERVICES",
          "candidate_count": 13,
          "candidate_reduction_ratio": 1.0,
          "candidate_subject_ids": [
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "frontend",
            "frontend-external",
            "frontendservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "redis",
            "shippingservice"
          ],
          "case_id": "re2ob_recommendationservice_delay_1",
          "covered": true,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_COVERED"
        }
      ]
    },
    "ERROR_EVENT_SERVICES": {
      "headline": {
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
        "evaluated_count": 5,
        "missed_count": 5,
        "statuses": {
          "EVALUATED_GT_MISSED": 5
        },
        "zero_candidate_count": 5,
        "zero_candidate_rate": 1.0
      },
      "per_case": [
        {
          "baseline": "ERROR_EVENT_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_checkoutservice_cpu_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_EVENT_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_currencyservice_disk_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_EVENT_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_emailservice_socket_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_EVENT_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_productcatalogservice_loss_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_EVENT_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_recommendationservice_delay_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        }
      ]
    },
    "ERROR_TRACE_SERVICES": {
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
      "per_case": [
        {
          "baseline": "ERROR_TRACE_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_checkoutservice_cpu_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_TRACE_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_currencyservice_disk_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_TRACE_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_emailservice_socket_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_TRACE_SERVICES",
          "candidate_count": 1,
          "candidate_reduction_ratio": 0.07692307692307693,
          "candidate_subject_ids": [
            "frontendservice"
          ],
          "case_id": "re2ob_productcatalogservice_loss_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        },
        {
          "baseline": "ERROR_TRACE_SERVICES",
          "candidate_count": 0,
          "candidate_reduction_ratio": 0.0,
          "candidate_subject_ids": [],
          "case_id": "re2ob_recommendationservice_delay_1",
          "covered": false,
          "eligible_service_count": 13,
          "status": "EVALUATED_GT_MISSED"
        }
      ]
    }
  },
  "schema_version": "v3_phase2_10e_r2_trivial_baselines_v1"
}
```
