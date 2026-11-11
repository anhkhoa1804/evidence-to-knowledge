# V3 Phase 2.11 Evidence-Aware Hypothesis Generation

Phase 2.11 adds an explicit, deterministic hypothesis-generation layer above the immutable Phase 2.10 candidate generator. It generates unranked `CauseCandidate` hypotheses only: it does not perform RCA ranking and it does not establish causality.

## Rules and provenance

H0 retains frozen Phase 2.10 candidates. H1 adds within-window metric level-shift aggregates, H2 adds trace-volume participation shifts, H3 makes one declared topology hop from evidence-backed seeds, H4 records pre-cutoff change context for those seeds, and H5 combines the families. Rules are fixed in the experiment manifest; their aggregate provenance records service/series, time bounds, counts, source digest, and input manifest. Candidate serialization is stable by subject and candidate ID and is explicitly non-semantic.

Metric eligibility excludes declared counters and unit-conflicted series. It requires at least 60 observations in each partition, a 50% median level shift, and 60% persistent post-cutoff excursion. Trace eligibility requires at least 100 pre/post spans and a twofold service-local volume shift. These fixed, label-independent constants are configuration, not scores.

## Anti-leakage and scope

For each pilot case the generator writes `CASE_RESULTS/<case>.json` before reading that single case's GT row; GT appears only in `CASE_EVALUATIONS`. The 78-case holdout is not loaded, enumerated, evaluated, or used for tuning. The operational evidence graph remains separate from the ontology/KG.

## Measured Results

```json
{
  "ablations": {
    "runs": {
      "H0_FROZEN_PHASE210": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.9935897435897436,
            "median": 1.0
          },
          "candidate_service_ratio": {
            "mean": 0.006410256410256411,
            "median": 0.0
          },
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
        "per_case": [
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "frontendservice"
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_MISSED"
          }
        ],
        "unique_gt_recoveries_vs_h0": []
      },
      "H1_METRIC": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.75,
            "median": 0.8846153846153846
          },
          "candidate_service_ratio": {
            "mean": 0.25,
            "median": 0.11538461538461539
          },
          "candidate_set_size": {
            "max": 10,
            "mean": 3.25,
            "median": 1.5,
            "min": 1,
            "p90": 9
          },
          "candidate_stage_root_cause_coverage": 1.0,
          "covered_count": 12,
          "evaluated_count": 12,
          "missed_count": 0,
          "statuses": {
            "EVALUATED_GT_COVERED": 12
          },
          "zero_candidate_count": 0,
          "zero_candidate_rate": 0.0
        },
        "per_case": [
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "checkoutservice"
            ],
            "case_id": "re2ob_checkoutservice_cpu_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-7f50127d9549f745d2274b92",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "checkoutservice"
            ],
            "case_id": "re2ob_checkoutservice_mem_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-affa8440ce3770e0b15ee697",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "checkoutservice"
            ],
            "case_id": "re2ob_checkoutservice_socket_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-3191cec13537bf103ffac2ea",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 3,
            "candidate_service_ratio": 0.23076923076923078,
            "candidate_subject_ids": [
              "checkoutservice",
              "currencyservice",
              "frontend"
            ],
            "case_id": "re2ob_currencyservice_disk_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-b77d688b9a37fb4d8097224c",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 9,
            "candidate_service_ratio": 0.6923076923076923,
            "candidate_subject_ids": [
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "emailservice",
              "frontend",
              "paymentservice",
              "productcatalogservice",
              "recommendationservice",
              "shippingservice"
            ],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "emailservice"
            ],
            "case_id": "re2ob_emailservice_cpu_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-4628a74192feaeda412c39cc",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "checkoutservice",
              "emailservice"
            ],
            "case_id": "re2ob_emailservice_delay_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-41028c9cd296c61dc2a8a84f",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "emailservice"
            ],
            "case_id": "re2ob_emailservice_socket_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-2215e4fea2ed1c50d7daef52",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 10,
            "candidate_service_ratio": 0.7692307692307693,
            "candidate_subject_ids": [
              "adservice",
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "frontend",
              "frontendservice",
              "paymentservice",
              "productcatalogservice",
              "recommendationservice",
              "shippingservice"
            ],
            "case_id": "re2ob_productcatalogservice_loss_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1",
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-938e18d154f1979f88b89d4d",
            "ground_truth_service_id": "productcatalogservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 7,
            "candidate_service_ratio": 0.5384615384615384,
            "candidate_subject_ids": [
              "adservice",
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "frontend",
              "productcatalogservice",
              "recommendationservice"
            ],
            "case_id": "re2ob_productcatalogservice_mem_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-3225613db76d45a19fcaf3b5",
            "ground_truth_service_id": "productcatalogservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "frontend",
              "recommendationservice"
            ],
            "case_id": "re2ob_recommendationservice_delay_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-2dac39527e1803aafc7e8869",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "recommendationservice"
            ],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_COVERED"
          }
        ],
        "unique_gt_recoveries_vs_h0": [
          "re2ob_checkoutservice_cpu_1",
          "re2ob_checkoutservice_mem_1",
          "re2ob_checkoutservice_socket_1",
          "re2ob_currencyservice_disk_1",
          "re2ob_currencyservice_loss_1",
          "re2ob_emailservice_cpu_1",
          "re2ob_emailservice_delay_1",
          "re2ob_emailservice_socket_1",
          "re2ob_productcatalogservice_loss_1",
          "re2ob_productcatalogservice_mem_1",
          "re2ob_recommendationservice_delay_1",
          "re2ob_recommendationservice_disk_1"
        ]
      },
      "H2_TRACE_PARTICIPATION": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.9102564102564102,
            "median": 0.9230769230769231
          },
          "candidate_service_ratio": {
            "mean": 0.08974358974358974,
            "median": 0.07692307692307693
          },
          "candidate_set_size": {
            "max": 4,
            "mean": 1.1666666666666667,
            "median": 1.0,
            "min": 0,
            "p90": 3
          },
          "candidate_stage_root_cause_coverage": 0.25,
          "covered_count": 3,
          "evaluated_count": 12,
          "missed_count": 9,
          "statuses": {
            "EVALUATED_GT_COVERED": 3,
            "EVALUATED_GT_MISSED": 9
          },
          "zero_candidate_count": 5,
          "zero_candidate_rate": 0.4166666666666667
        },
        "per_case": [
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "currencyservice"
            ],
            "case_id": "re2ob_checkoutservice_cpu_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-7f50127d9549f745d2274b92",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_checkoutservice_mem_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-affa8440ce3770e0b15ee697",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "currencyservice"
            ],
            "case_id": "re2ob_checkoutservice_socket_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-3191cec13537bf103ffac2ea",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_cpu_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-4628a74192feaeda412c39cc",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 3,
            "candidate_service_ratio": 0.23076923076923078,
            "candidate_subject_ids": [
              "checkoutservice",
              "emailservice",
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_delay_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-41028c9cd296c61dc2a8a84f",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 4,
            "candidate_service_ratio": 0.3076923076923077,
            "candidate_subject_ids": [
              "currencyservice",
              "emailservice",
              "frontendservice",
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_socket_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-2215e4fea2ed1c50d7daef52",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "frontendservice",
              "productcatalogservice"
            ],
            "case_id": "re2ob_productcatalogservice_loss_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-938e18d154f1979f88b89d4d",
            "ground_truth_service_id": "productcatalogservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_recommendationservice_delay_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-2dac39527e1803aafc7e8869",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "emailservice",
              "paymentservice"
            ],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_MISSED"
          }
        ],
        "unique_gt_recoveries_vs_h0": [
          "re2ob_emailservice_delay_1",
          "re2ob_emailservice_socket_1",
          "re2ob_productcatalogservice_loss_1"
        ]
      },
      "H3_BOUNDED_TOPOLOGY": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.9935897435897436,
            "median": 1.0
          },
          "candidate_service_ratio": {
            "mean": 0.006410256410256411,
            "median": 0.0
          },
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
        "per_case": [
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "frontendservice"
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_MISSED"
          }
        ],
        "unique_gt_recoveries_vs_h0": []
      },
      "H4_TEMPORAL_CHANGE": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.9935897435897436,
            "median": 1.0
          },
          "candidate_service_ratio": {
            "mean": 0.006410256410256411,
            "median": 0.0
          },
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
        "per_case": [
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_MISSED"
          },
          {
            "candidate_count": 0,
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "frontendservice"
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
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
            "candidate_service_ratio": 0.0,
            "candidate_subject_ids": [],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": false,
            "eligible_service_count": 13,
            "generation_rules": [],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_MISSED"
          }
        ],
        "unique_gt_recoveries_vs_h0": []
      },
      "H5_COMBINED": {
        "headline": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.6923076923076923,
            "median": 0.7692307692307692
          },
          "candidate_service_ratio": {
            "mean": 0.3076923076923077,
            "median": 0.23076923076923078
          },
          "candidate_set_size": {
            "max": 10,
            "mean": 4,
            "median": 3.0,
            "min": 1,
            "p90": 9
          },
          "candidate_stage_root_cause_coverage": 1.0,
          "covered_count": 12,
          "evaluated_count": 12,
          "missed_count": 0,
          "statuses": {
            "EVALUATED_GT_COVERED": 12
          },
          "zero_candidate_count": 0,
          "zero_candidate_rate": 0.0
        },
        "per_case": [
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "checkoutservice",
              "currencyservice"
            ],
            "case_id": "re2ob_checkoutservice_cpu_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-7f50127d9549f745d2274b92",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 1,
            "candidate_service_ratio": 0.07692307692307693,
            "candidate_subject_ids": [
              "checkoutservice"
            ],
            "case_id": "re2ob_checkoutservice_mem_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-affa8440ce3770e0b15ee697",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "checkoutservice",
              "currencyservice"
            ],
            "case_id": "re2ob_checkoutservice_socket_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-3191cec13537bf103ffac2ea",
            "ground_truth_service_id": "checkoutservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 3,
            "candidate_service_ratio": 0.23076923076923078,
            "candidate_subject_ids": [
              "checkoutservice",
              "currencyservice",
              "frontend"
            ],
            "case_id": "re2ob_currencyservice_disk_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-b77d688b9a37fb4d8097224c",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 9,
            "candidate_service_ratio": 0.6923076923076923,
            "candidate_subject_ids": [
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "emailservice",
              "frontend",
              "paymentservice",
              "productcatalogservice",
              "recommendationservice",
              "shippingservice"
            ],
            "case_id": "re2ob_currencyservice_loss_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
            "ground_truth_service_id": "currencyservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "emailservice",
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_cpu_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-4628a74192feaeda412c39cc",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 3,
            "candidate_service_ratio": 0.23076923076923078,
            "candidate_subject_ids": [
              "checkoutservice",
              "emailservice",
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_delay_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-41028c9cd296c61dc2a8a84f",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 4,
            "candidate_service_ratio": 0.3076923076923077,
            "candidate_subject_ids": [
              "currencyservice",
              "emailservice",
              "frontendservice",
              "paymentservice"
            ],
            "case_id": "re2ob_emailservice_socket_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-2215e4fea2ed1c50d7daef52",
            "ground_truth_service_id": "emailservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 10,
            "candidate_service_ratio": 0.7692307692307693,
            "candidate_subject_ids": [
              "adservice",
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "frontend",
              "frontendservice",
              "paymentservice",
              "productcatalogservice",
              "recommendationservice",
              "shippingservice"
            ],
            "case_id": "re2ob_productcatalogservice_loss_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1",
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-938e18d154f1979f88b89d4d",
            "ground_truth_service_id": "productcatalogservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 7,
            "candidate_service_ratio": 0.5384615384615384,
            "candidate_subject_ids": [
              "adservice",
              "cartservice",
              "checkoutservice",
              "currencyservice",
              "frontend",
              "productcatalogservice",
              "recommendationservice"
            ],
            "case_id": "re2ob_productcatalogservice_mem_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-3225613db76d45a19fcaf3b5",
            "ground_truth_service_id": "productcatalogservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 2,
            "candidate_service_ratio": 0.15384615384615385,
            "candidate_subject_ids": [
              "frontend",
              "recommendationservice"
            ],
            "case_id": "re2ob_recommendationservice_delay_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-2dac39527e1803aafc7e8869",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_COVERED"
          },
          {
            "candidate_count": 3,
            "candidate_service_ratio": 0.23076923076923078,
            "candidate_subject_ids": [
              "emailservice",
              "paymentservice",
              "recommendationservice"
            ],
            "case_id": "re2ob_recommendationservice_disk_1",
            "covered": true,
            "eligible_service_count": 13,
            "generation_rules": [
              "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
              "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
            ],
            "graph_id": "iegview-18d8b7413b44b91c2303a1df",
            "ground_truth_service_id": "recommendationservice",
            "status": "EVALUATED_GT_COVERED"
          }
        ],
        "unique_gt_recoveries_vs_h0": [
          "re2ob_checkoutservice_cpu_1",
          "re2ob_checkoutservice_mem_1",
          "re2ob_checkoutservice_socket_1",
          "re2ob_currencyservice_disk_1",
          "re2ob_currencyservice_loss_1",
          "re2ob_emailservice_cpu_1",
          "re2ob_emailservice_delay_1",
          "re2ob_emailservice_socket_1",
          "re2ob_productcatalogservice_loss_1",
          "re2ob_productcatalogservice_mem_1",
          "re2ob_recommendationservice_delay_1",
          "re2ob_recommendationservice_disk_1"
        ]
      }
    },
    "schema_version": "v3_phase2_11_ablation_results_v1"
  },
  "data_characterization": {
    "aggregate": {
      "metric_kinds": {
        "METRIC_KIND_UNSPECIFIED": 784103
      },
      "metric_observation_count": 784103,
      "metric_series_count": 873,
      "trace_span_count": 2688969,
      "units": [
        "UNIT_UNSPECIFIED"
      ]
    },
    "cases": [
      {
        "case_id": "re2ob_checkoutservice_cpu_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 64870
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 64870,
        "metric_series_count": 72,
        "metric_value_ranges": {
          "cpu": {
            "max": 20.031263076095414,
            "min": 0.10875333333333495
          },
          "diskio": {
            "max": 104673.37486024597,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.43750000000000006,
            "min": 0.0018655913978494624
          },
          "latency-90": {
            "max": 1.1499999999999995,
            "min": 0.004378279569892473
          },
          "mem": {
            "max": 111775744.0,
            "min": 3006464.0
          },
          "socket": {
            "max": 31.0,
            "min": 3.0
          },
          "workload": {
            "max": 159.533,
            "min": 0.333
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0011098779134295356,
          "mean": 3.082994203970932e-05
        },
        "sampling_interval_seconds": {
          "max": 2.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 900
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 246079,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_checkoutservice_mem_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 63068
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 63068,
        "metric_series_count": 70,
        "metric_value_ranges": {
          "cpu": {
            "max": 30.96784827616027,
            "min": 0.11188333333333132
          },
          "diskio": {
            "max": 141522.92358803985,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 1.4655172413793103,
            "min": 0.001764771460423634
          },
          "latency-90": {
            "max": 2.5,
            "min": 0.00436098104793757
          },
          "mem": {
            "max": 268439552.0,
            "min": 2994176.0
          },
          "socket": {
            "max": 35.0,
            "min": 2.0
          },
          "workload": {
            "max": 162.467,
            "min": 0.267
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.002219755826859071,
          "mean": 3.171079752655816e-05
        },
        "sampling_interval_seconds": {
          "max": 3.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 899
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 255069,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_checkoutservice_socket_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 66449
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 66449,
        "metric_series_count": 75,
        "metric_value_ranges": {
          "cpu": {
            "max": 36.53371354081803,
            "min": 0.11775000000000091
          },
          "diskio": {
            "max": 229130.8448317598,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.42857142857142855,
            "min": 0.001647865459249676
          },
          "latency-90": {
            "max": 0.8409090909090909,
            "min": 0.004338572574178026
          },
          "mem": {
            "max": 101621760.0,
            "min": 2920448.0
          },
          "socket": {
            "max": 23.0,
            "min": 2.0
          },
          "workload": {
            "max": 166.667,
            "min": 0.4
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.7691453940066593,
          "mean": 0.016662967073621904
        },
        "sampling_interval_seconds": {
          "max": 4.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901,
          "min": 208
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 252114,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_currencyservice_disk_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 66350
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 66350,
        "metric_series_count": 74,
        "metric_value_ranges": {
          "cpu": {
            "max": 20.01752860144763,
            "min": 0.08017333333332506
          },
          "diskio": {
            "max": 5061175758.373363,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 1.8076952660951908,
            "min": 0.001853085463465014
          },
          "latency-90": {
            "max": 4.25,
            "min": 0.004371973587674247
          },
          "mem": {
            "max": 134205440.0,
            "min": 3026944.0
          },
          "socket": {
            "max": 40.0,
            "min": 3.0
          },
          "workload": {
            "max": 156.533,
            "min": 0.133
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.3596004439511654,
          "mean": 0.0048594654587995325
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 577
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 218060,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_currencyservice_loss_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 66158
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 66158,
        "metric_series_count": 74,
        "metric_value_ranges": {
          "cpu": {
            "max": 19.358814573428173,
            "min": 0.02190336995490448
          },
          "diskio": {
            "max": 105304.65335504328,
            "min": 0.0
          },
          "error": {
            "max": 11.2,
            "min": 0.0
          },
          "latency-50": {
            "max": 45.0,
            "min": 0.001629441624365482
          },
          "latency-90": {
            "max": 57.0,
            "min": 0.00436844732900649
          },
          "mem": {
            "max": 185405440.0,
            "min": 3026944.0
          },
          "socket": {
            "max": 59.0,
            "min": 3.0
          },
          "workload": {
            "max": 152.6,
            "min": 0.0
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.4816870144284129,
          "mean": 0.007739148693643698
        },
        "sampling_interval_seconds": {
          "max": 16.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 467
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 163687,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_emailservice_cpu_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 64872
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 64872,
        "metric_series_count": 72,
        "metric_value_ranges": {
          "cpu": {
            "max": 20.03727174397147,
            "min": 0.1282766666666646
          },
          "diskio": {
            "max": 105672.92532607137,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.35227272727272724,
            "min": 0.0017615241140420998
          },
          "latency-90": {
            "max": 0.9750000000000004,
            "min": 0.00435358067299396
          },
          "mem": {
            "max": 110522368.0,
            "min": 3006464.0
          },
          "socket": {
            "max": 59.0,
            "min": 3.0
          },
          "workload": {
            "max": 151.8,
            "min": 0.333
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0,
          "mean": 0.0
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 901
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 243226,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_emailservice_delay_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 66674
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 66674,
        "metric_series_count": 74,
        "metric_value_ranges": {
          "cpu": {
            "max": 34.635456009870836,
            "min": 0.10517000000000108
          },
          "diskio": {
            "max": 214675.05241090147,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.3590425531914893,
            "min": 0.0020453893932154805
          },
          "latency-90": {
            "max": 0.48984375,
            "min": 0.0044258958432871484
          },
          "mem": {
            "max": 109047808.0,
            "min": 2957312.0
          },
          "socket": {
            "max": 26.0,
            "min": 3.0
          },
          "workload": {
            "max": 169.733,
            "min": 0.2
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0,
          "mean": 0.0
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 901
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 255539,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_emailservice_socket_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 66674
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 66674,
        "metric_series_count": 74,
        "metric_value_ranges": {
          "cpu": {
            "max": 35.17145648651208,
            "min": 0.10836666666666606
          },
          "diskio": {
            "max": 142349.31982921262,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.175,
            "min": 0.002057791769732404
          },
          "latency-90": {
            "max": 0.31249999999999983,
            "min": 0.0044243850709238565
          },
          "mem": {
            "max": 104820736.0,
            "min": 2945024.0
          },
          "socket": {
            "max": 22.0,
            "min": 3.0
          },
          "workload": {
            "max": 162.133,
            "min": 0.2
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0,
          "mean": 0.0
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 901
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 254238,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_productcatalogservice_loss_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 64376
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 64376,
        "metric_series_count": 72,
        "metric_value_ranges": {
          "cpu": {
            "max": 19.221558764166613,
            "min": 0.028742500000005222
          },
          "diskio": {
            "max": 676856.9776088573,
            "min": 0.0
          },
          "error": {
            "max": 0.933,
            "min": 0.0
          },
          "latency-50": {
            "max": 16.419753086419753,
            "min": 0.0014902077151335304
          },
          "latency-90": {
            "max": 50.86153846153846,
            "min": 0.004300890207715133
          },
          "mem": {
            "max": 179073024.0,
            "min": 2932736.0
          },
          "socket": {
            "max": 59.0,
            "min": 3.0
          },
          "workload": {
            "max": 157.2,
            "min": 0.0
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.439511653718091,
          "mean": 0.007645825625847823
        },
        "sampling_interval_seconds": {
          "max": 31.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 505
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 133521,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_productcatalogservice_mem_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 64872
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 64872,
        "metric_series_count": 72,
        "metric_value_ranges": {
          "cpu": {
            "max": 20.973243758276645,
            "min": 0.05539333333331343
          },
          "diskio": {
            "max": 257835.6779243527,
            "min": 0.0
          },
          "error": {
            "max": 0.533,
            "min": 0.0
          },
          "latency-50": {
            "max": 3.305555555555556,
            "min": 0.0022606488633855663
          },
          "latency-90": {
            "max": 6.582474226804124,
            "min": 0.004478260869565218
          },
          "mem": {
            "max": 134234112.0,
            "min": 3006464.0
          },
          "socket": {
            "max": 48.0,
            "min": 3.0
          },
          "workload": {
            "max": 148.801,
            "min": 0.067
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0,
          "mean": 0.0
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901.0,
          "min": 901
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 182379,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_recommendationservice_delay_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 63971
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 63971,
        "metric_series_count": 71,
        "metric_value_ranges": {
          "cpu": {
            "max": 30.322425249169775,
            "min": 0.11682333333332905
          },
          "diskio": {
            "max": 217881.9983155282,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.3690671031096563,
            "min": 0.0016861125451729478
          },
          "latency-90": {
            "max": 0.7773584905660378,
            "min": 0.004357046979865772
          },
          "mem": {
            "max": 108687360.0,
            "min": 2994176.0
          },
          "socket": {
            "max": 37.0,
            "min": 3.0
          },
          "workload": {
            "max": 166.2,
            "min": 0.267
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.0,
          "mean": 0.0
        },
        "sampling_interval_seconds": {
          "max": 1.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901,
          "min": 901
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 241523,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      },
      {
        "case_id": "re2ob_recommendationservice_disk_1",
        "metric_kinds": {
          "METRIC_KIND_UNSPECIFIED": 65769
        },
        "metric_names": [
          "cpu",
          "diskio",
          "error",
          "latency-50",
          "latency-90",
          "mem",
          "socket",
          "workload"
        ],
        "metric_observation_count": 65769,
        "metric_series_count": 73,
        "metric_value_ranges": {
          "cpu": {
            "max": 19.89960779010008,
            "min": 0.11487999999999943
          },
          "diskio": {
            "max": 10742593190.939966,
            "min": 0.0
          },
          "error": {
            "max": 0.0,
            "min": 0.0
          },
          "latency-50": {
            "max": 0.38749999999999996,
            "min": 0.001939552594002856
          },
          "latency-90": {
            "max": 0.97,
            "min": 0.004396287482151357
          },
          "mem": {
            "max": 471859200.0,
            "min": 3006464.0
          },
          "socket": {
            "max": 37.0,
            "min": 3.0
          },
          "workload": {
            "max": 160.067,
            "min": 0.267
          }
        },
        "relative_series_missingness": {
          "definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule",
          "max": 0.002219755826859071,
          "mean": 6.081522813312524e-05
        },
        "sampling_interval_seconds": {
          "max": 3.0,
          "median": 1.0,
          "min": 1.0
        },
        "series_observation_count": {
          "max": 901,
          "median": 901,
          "min": 899
        },
        "series_with_unit_conflict": 0,
        "service_count_with_metrics": 12,
        "trace_span_count": 243534,
        "units": [
          "UNIT_UNSPECIFIED"
        ]
      }
    ],
    "purpose": "Operational telemetry characterization; GT labels were not used to select metric or trace mechanics.",
    "schema_version": "v3_phase2_11_data_characterization_v1"
  },
  "experiment_manifest": {
    "baseline_pilot_hash_metadata": {
      "authoritative_r2a": "dac2e9fd334a902c9ba7ceadd2b4f10595e4182bed37b8553134f38455d45e55",
      "status": "PRE_EXISTING_BASELINE_METADATA_DISCREPANCY_PRESERVED",
      "stored": "4cf641d0f04e4c2e5e5f948d421c850fe6a1b09334aae95a1f5e27c3cd5742b8"
    },
    "baseline_sha256": "e92543c3cbd612cf33cae924915efba037890687272878951b0bfaa2e13377e1",
    "case_index_sha256": "c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb",
    "configuration": {
      "baseline_seconds": 300,
      "metric_median_relative_shift": 0.5,
      "metric_minimum_observations": 60,
      "metric_persistent_fraction": 0.6,
      "schema_version": "evidence_aware_hypothesis_generation_v1",
      "trace_minimum_spans_per_partition": 100,
      "trace_volume_shift_factor": 2.0
    },
    "dataset_revision": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e",
    "hypothesis_generation_version": "evidence_aware_hypothesis_generation_v1",
    "pilot_case_ids": [
      "re2ob_checkoutservice_cpu_1",
      "re2ob_checkoutservice_mem_1",
      "re2ob_checkoutservice_socket_1",
      "re2ob_currencyservice_disk_1",
      "re2ob_currencyservice_loss_1",
      "re2ob_emailservice_cpu_1",
      "re2ob_emailservice_delay_1",
      "re2ob_emailservice_socket_1",
      "re2ob_productcatalogservice_loss_1",
      "re2ob_productcatalogservice_mem_1",
      "re2ob_recommendationservice_delay_1",
      "re2ob_recommendationservice_disk_1"
    ],
    "pilot_split_sha256": "dac2e9fd334a902c9ba7ceadd2b4f10595e4182bed37b8553134f38455d45e55",
    "protected_holdout": "NOT_READ_OR_EVALUATED",
    "r2a_manifest_sha256": "c954897459dc7e9f32f2359a7e91b0e834cfd2c118f1223c1289411442f815c7",
    "runtime": {
      "platform": "Windows-10-10.0.19045-SP0",
      "python": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]"
    },
    "schema_version": "v3_phase2_11_experiment_manifest_v1",
    "variants": {
      "H0_FROZEN_PHASE210": [
        false,
        false,
        false,
        false
      ],
      "H1_METRIC": [
        true,
        false,
        false,
        false
      ],
      "H2_TRACE_PARTICIPATION": [
        false,
        true,
        false,
        false
      ],
      "H3_BOUNDED_TOPOLOGY": [
        false,
        false,
        true,
        false
      ],
      "H4_TEMPORAL_CHANGE": [
        false,
        false,
        false,
        true
      ],
      "H5_COMBINED": [
        true,
        true,
        true,
        true
      ]
    }
  },
  "failures": {
    "cases": []
  },
  "performance": {
    "cases": [
      {
        "case_id": "re2ob_checkoutservice_cpu_1",
        "combined_generation_seconds": 1.4271645999979228,
        "in_window_trace_count": 246079,
        "raw_trace_count": 391997,
        "spans_per_second": 7610.660647770215,
        "sqlite_bytes": 154402816,
        "total_seconds": 32.33346110000275,
        "valid_trace_count": 391997
      },
      {
        "case_id": "re2ob_checkoutservice_mem_1",
        "combined_generation_seconds": 1.4831405000004452,
        "in_window_trace_count": 255069,
        "raw_trace_count": 405917,
        "spans_per_second": 7157.955722373469,
        "sqlite_bytes": 160092160,
        "total_seconds": 35.634336100003566,
        "valid_trace_count": 405917
      },
      {
        "case_id": "re2ob_checkoutservice_socket_1",
        "combined_generation_seconds": 1.4394613000040408,
        "in_window_trace_count": 252114,
        "raw_trace_count": 404289,
        "spans_per_second": 7309.919753396966,
        "sqlite_bytes": 163819520,
        "total_seconds": 34.489297899999656,
        "valid_trace_count": 404289
      },
      {
        "case_id": "re2ob_currencyservice_disk_1",
        "combined_generation_seconds": 1.2467436000006273,
        "in_window_trace_count": 218060,
        "raw_trace_count": 361288,
        "spans_per_second": 7569.868294428804,
        "sqlite_bytes": 139251712,
        "total_seconds": 28.806313599998248,
        "valid_trace_count": 361288
      },
      {
        "case_id": "re2ob_currencyservice_loss_1",
        "combined_generation_seconds": 0.9356444000004558,
        "in_window_trace_count": 163687,
        "raw_trace_count": 286200,
        "spans_per_second": 7435.155142495385,
        "sqlite_bytes": 104185856,
        "total_seconds": 22.015276999998605,
        "valid_trace_count": 286200
      },
      {
        "case_id": "re2ob_emailservice_cpu_1",
        "combined_generation_seconds": 1.3545851999951992,
        "in_window_trace_count": 243226,
        "raw_trace_count": 392420,
        "spans_per_second": 7504.631477887373,
        "sqlite_bytes": 152633344,
        "total_seconds": 32.41011910000816,
        "valid_trace_count": 392420
      },
      {
        "case_id": "re2ob_emailservice_delay_1",
        "combined_generation_seconds": 1.4727748000004794,
        "in_window_trace_count": 255539,
        "raw_trace_count": 406121,
        "spans_per_second": 7521.265797077313,
        "sqlite_bytes": 160141312,
        "total_seconds": 33.975531100004446,
        "valid_trace_count": 406121
      },
      {
        "case_id": "re2ob_emailservice_socket_1",
        "combined_generation_seconds": 1.741606600000523,
        "in_window_trace_count": 254238,
        "raw_trace_count": 408640,
        "spans_per_second": 6856.353263847446,
        "sqlite_bytes": 159367168,
        "total_seconds": 37.080644799993024,
        "valid_trace_count": 408640
      },
      {
        "case_id": "re2ob_productcatalogservice_loss_1",
        "combined_generation_seconds": 0.7870141000021249,
        "in_window_trace_count": 133521,
        "raw_trace_count": 254889,
        "spans_per_second": 6879.7235979402585,
        "sqlite_bytes": 88993792,
        "total_seconds": 19.407901800004765,
        "valid_trace_count": 254889
      },
      {
        "case_id": "re2ob_productcatalogservice_mem_1",
        "combined_generation_seconds": 1.022976899999776,
        "in_window_trace_count": 182379,
        "raw_trace_count": 317085,
        "spans_per_second": 7599.58046818784,
        "sqlite_bytes": 121540608,
        "total_seconds": 23.998561600004905,
        "valid_trace_count": 317085
      },
      {
        "case_id": "re2ob_recommendationservice_delay_1",
        "combined_generation_seconds": 1.3290433999936795,
        "in_window_trace_count": 241523,
        "raw_trace_count": 393688,
        "spans_per_second": 7874.022576386087,
        "sqlite_bytes": 162230272,
        "total_seconds": 30.67339440000069,
        "valid_trace_count": 393688
      },
      {
        "case_id": "re2ob_recommendationservice_disk_1",
        "combined_generation_seconds": 1.3821859999879962,
        "in_window_trace_count": 243534,
        "raw_trace_count": 391177,
        "spans_per_second": 7751.477745006162,
        "sqlite_bytes": 163221504,
        "total_seconds": 31.417751299988595,
        "valid_trace_count": 391177
      }
    ],
    "headline": {
      "boundedness": "Trace participation uses indexed SQLite GROUP BY and ordered evidence-ID digests; no trace execution graph is materialized.",
      "mean_seconds": 30.18688248333395,
      "mean_spans_per_second": 7422.55120723311,
      "mean_sqlite_bytes": 144156672,
      "total_seconds": 362.2425898000074
    },
    "schema_version": "v3_phase2_11_performance_v1"
  },
  "pilot": {
    "comparison": {
      "frozen_phase210_r2a": {
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
      "trivial_baselines": {
        "ALL_SERVICES": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.0,
            "median": 0.0
          },
          "candidate_service_ratio": {
            "mean": 1.0,
            "median": 1.0
          },
          "candidate_set_size": {
            "max": 13,
            "mean": 13,
            "median": 13.0,
            "min": 13,
            "p90": 13
          },
          "candidate_stage_root_cause_coverage": 1.0,
          "covered_count": 12,
          "evaluated_count": 12,
          "missed_count": 0,
          "statuses": {
            "EVALUATED_GT_COVERED": 12
          },
          "zero_candidate_count": 0,
          "zero_candidate_rate": 0.0
        },
        "ERROR_EVENT_SERVICES": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 1.0,
            "median": 1.0
          },
          "candidate_service_ratio": {
            "mean": 0.0,
            "median": 0.0
          },
          "candidate_set_size": {
            "max": 0,
            "mean": 0,
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
          "zero_candidate_count": 12,
          "zero_candidate_rate": 1.0
        },
        "ERROR_TRACE_SERVICES": {
          "candidate_reduction_relative_to_all_services": {
            "mean": 0.9935897435897436,
            "median": 1.0
          },
          "candidate_service_ratio": {
            "mean": 0.006410256410256411,
            "median": 0.0
          },
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
        }
      }
    },
    "fault_type_breakdown": {
      "CPU": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.8461538461538461,
          "median": 0.8461538461538461
        },
        "candidate_service_ratio": {
          "mean": 0.15384615384615385,
          "median": 0.15384615384615385
        },
        "candidate_set_size": {
          "max": 2,
          "mean": 2,
          "median": 2.0,
          "min": 2,
          "p90": 2
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "DELAY": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.8076923076923077,
          "median": 0.8076923076923077
        },
        "candidate_service_ratio": {
          "mean": 0.19230769230769232,
          "median": 0.19230769230769232
        },
        "candidate_set_size": {
          "max": 3,
          "mean": 2.5,
          "median": 2.5,
          "min": 2,
          "p90": 3
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "DISK": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.7692307692307692,
          "median": 0.7692307692307692
        },
        "candidate_service_ratio": {
          "mean": 0.23076923076923078,
          "median": 0.23076923076923078
        },
        "candidate_set_size": {
          "max": 3,
          "mean": 3,
          "median": 3.0,
          "min": 3,
          "p90": 3
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "LOSS": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.2692307692307692,
          "median": 0.2692307692307692
        },
        "candidate_service_ratio": {
          "mean": 0.7307692307692308,
          "median": 0.7307692307692308
        },
        "candidate_set_size": {
          "max": 10,
          "mean": 9.5,
          "median": 9.5,
          "min": 9,
          "p90": 10
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "MEM": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.6923076923076923,
          "median": 0.6923076923076923
        },
        "candidate_service_ratio": {
          "mean": 0.3076923076923077,
          "median": 0.3076923076923077
        },
        "candidate_set_size": {
          "max": 7,
          "mean": 4,
          "median": 4.0,
          "min": 1,
          "p90": 7
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      },
      "SOCKET": {
        "candidate_reduction_relative_to_all_services": {
          "mean": 0.7692307692307692,
          "median": 0.7692307692307692
        },
        "candidate_service_ratio": {
          "mean": 0.23076923076923078,
          "median": 0.23076923076923078
        },
        "candidate_set_size": {
          "max": 4,
          "mean": 3,
          "median": 3.0,
          "min": 2,
          "p90": 4
        },
        "candidate_stage_root_cause_coverage": 1.0,
        "covered_count": 2,
        "evaluated_count": 2,
        "missed_count": 0,
        "statuses": {
          "EVALUATED_GT_COVERED": 2
        },
        "zero_candidate_count": 0,
        "zero_candidate_rate": 0.0
      }
    },
    "headline": {
      "candidate_reduction_relative_to_all_services": {
        "mean": 0.6923076923076923,
        "median": 0.7692307692307692
      },
      "candidate_service_ratio": {
        "mean": 0.3076923076923077,
        "median": 0.23076923076923078
      },
      "candidate_set_size": {
        "max": 10,
        "mean": 4,
        "median": 3.0,
        "min": 1,
        "p90": 9
      },
      "candidate_stage_root_cause_coverage": 1.0,
      "covered_count": 12,
      "evaluated_count": 12,
      "missed_count": 0,
      "statuses": {
        "EVALUATED_GT_COVERED": 12
      },
      "zero_candidate_count": 0,
      "zero_candidate_rate": 0.0
    },
    "results": [
      {
        "candidate_count": 2,
        "candidate_service_ratio": 0.15384615384615385,
        "candidate_subject_ids": [
          "checkoutservice",
          "currencyservice"
        ],
        "case_id": "re2ob_checkoutservice_cpu_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-7f50127d9549f745d2274b92",
        "ground_truth_service_id": "checkoutservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 1,
        "candidate_service_ratio": 0.07692307692307693,
        "candidate_subject_ids": [
          "checkoutservice"
        ],
        "case_id": "re2ob_checkoutservice_mem_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-affa8440ce3770e0b15ee697",
        "ground_truth_service_id": "checkoutservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 2,
        "candidate_service_ratio": 0.15384615384615385,
        "candidate_subject_ids": [
          "checkoutservice",
          "currencyservice"
        ],
        "case_id": "re2ob_checkoutservice_socket_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-3191cec13537bf103ffac2ea",
        "ground_truth_service_id": "checkoutservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 3,
        "candidate_service_ratio": 0.23076923076923078,
        "candidate_subject_ids": [
          "checkoutservice",
          "currencyservice",
          "frontend"
        ],
        "case_id": "re2ob_currencyservice_disk_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-b77d688b9a37fb4d8097224c",
        "ground_truth_service_id": "currencyservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 9,
        "candidate_service_ratio": 0.6923076923076923,
        "candidate_subject_ids": [
          "cartservice",
          "checkoutservice",
          "currencyservice",
          "emailservice",
          "frontend",
          "paymentservice",
          "productcatalogservice",
          "recommendationservice",
          "shippingservice"
        ],
        "case_id": "re2ob_currencyservice_loss_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-f3babe4e831cfb8eb8a63a37",
        "ground_truth_service_id": "currencyservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 2,
        "candidate_service_ratio": 0.15384615384615385,
        "candidate_subject_ids": [
          "emailservice",
          "paymentservice"
        ],
        "case_id": "re2ob_emailservice_cpu_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-4628a74192feaeda412c39cc",
        "ground_truth_service_id": "emailservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 3,
        "candidate_service_ratio": 0.23076923076923078,
        "candidate_subject_ids": [
          "checkoutservice",
          "emailservice",
          "paymentservice"
        ],
        "case_id": "re2ob_emailservice_delay_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-41028c9cd296c61dc2a8a84f",
        "ground_truth_service_id": "emailservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 4,
        "candidate_service_ratio": 0.3076923076923077,
        "candidate_subject_ids": [
          "currencyservice",
          "emailservice",
          "frontendservice",
          "paymentservice"
        ],
        "case_id": "re2ob_emailservice_socket_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-2215e4fea2ed1c50d7daef52",
        "ground_truth_service_id": "emailservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 10,
        "candidate_service_ratio": 0.7692307692307693,
        "candidate_subject_ids": [
          "adservice",
          "cartservice",
          "checkoutservice",
          "currencyservice",
          "frontend",
          "frontendservice",
          "paymentservice",
          "productcatalogservice",
          "recommendationservice",
          "shippingservice"
        ],
        "case_id": "re2ob_productcatalogservice_loss_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1",
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-938e18d154f1979f88b89d4d",
        "ground_truth_service_id": "productcatalogservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 7,
        "candidate_service_ratio": 0.5384615384615384,
        "candidate_subject_ids": [
          "adservice",
          "cartservice",
          "checkoutservice",
          "currencyservice",
          "frontend",
          "productcatalogservice",
          "recommendationservice"
        ],
        "case_id": "re2ob_productcatalogservice_mem_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-3225613db76d45a19fcaf3b5",
        "ground_truth_service_id": "productcatalogservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 2,
        "candidate_service_ratio": 0.15384615384615385,
        "candidate_subject_ids": [
          "frontend",
          "recommendationservice"
        ],
        "case_id": "re2ob_recommendationservice_delay_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-2dac39527e1803aafc7e8869",
        "ground_truth_service_id": "recommendationservice",
        "status": "EVALUATED_GT_COVERED"
      },
      {
        "candidate_count": 3,
        "candidate_service_ratio": 0.23076923076923078,
        "candidate_subject_ids": [
          "emailservice",
          "paymentservice",
          "recommendationservice"
        ],
        "case_id": "re2ob_recommendationservice_disk_1",
        "covered": true,
        "eligible_service_count": 13,
        "generation_rules": [
          "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1",
          "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
        ],
        "graph_id": "iegview-18d8b7413b44b91c2303a1df",
        "ground_truth_service_id": "recommendationservice",
        "status": "EVALUATED_GT_COVERED"
      }
    ],
    "schema_version": "v3_phase2_11_pilot_results_v1"
  },
  "research_gate": {
    "anti_leakage": "SUPPORTED: generation artifacts precede per-case GT reads",
    "decision": "EVIDENCE_AWARE_HYPOTHESIS_GENERATION_SUPPORTED_BY_PILOT",
    "next_step": "Freeze Phase 2.11 and validate once on the protected holdout without tuning.",
    "no_ranking_or_causal_claim": "SUPPORTED",
    "pilot_complete": true,
    "protected_holdout": "UNTOUCHED",
    "schema_version": "v3_phase2_11_research_gate_v1"
  }
}
```

## Interpretation and limitations

These results measure candidate-stage GT coverage and candidate-set reduction jointly. A metric, trace, topology relation, or temporal association is eligibility/support/context evidence, not proof that its service caused an incident. RCAEval supplies no static topology or change evidence in this pilot, so H3/H4 can be inactive without invalidating their bounded synthetic mechanism tests. The next permitted action is governed by `RESEARCH_GATE.json`; no ranking is introduced here.
