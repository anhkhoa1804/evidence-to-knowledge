# V3 Phase 2.10E-R2A Failure Characterization

```json
{
  "cases": [
    {
      "case_id": "re2ob_checkoutservice_cpu_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 1290,
        "metric_observation_count": 5406,
        "metric_series_count": 6,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 5810
      }
    },
    {
      "case_id": "re2ob_currencyservice_disk_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 30210,
        "metric_observation_count": 6884,
        "metric_series_count": 8,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 30369
      }
    },
    {
      "case_id": "re2ob_emailservice_socket_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 419,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 779
      }
    },
    {
      "case_id": "re2ob_productcatalogservice_loss_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "CANDIDATES_EXIST_GT_ABSENT"
      ],
      "zero_candidate_evidence_inventory": null
    },
    {
      "case_id": "re2ob_recommendationservice_delay_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 8035,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 16426
      }
    },
    {
      "case_id": "re2ob_checkoutservice_mem_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 1368,
        "metric_observation_count": 5406,
        "metric_series_count": 6,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 6182
      }
    },
    {
      "case_id": "re2ob_emailservice_cpu_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 398,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 757
      }
    },
    {
      "case_id": "re2ob_emailservice_delay_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 420,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 780
      }
    },
    {
      "case_id": "re2ob_productcatalogservice_mem_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY",
        "PARTIAL_TRACE_LIMITATION"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 0,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 12,
        "service_resolved": true,
        "trace_span_count": 46063
      }
    },
    {
      "case_id": "re2ob_recommendationservice_disk_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 8128,
        "metric_observation_count": 6307,
        "metric_series_count": 7,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 16580
      }
    },
    {
      "case_id": "re2ob_checkoutservice_socket_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 1167,
        "metric_observation_count": 5406,
        "metric_series_count": 6,
        "partial_trace_unresolved_parent_count": 0,
        "service_resolved": true,
        "trace_span_count": 5486
      }
    },
    {
      "case_id": "re2ob_currencyservice_loss_1",
      "status": "EVALUATED_GT_MISSED",
      "taxonomy": [
        "ZERO_CANDIDATES",
        "NO_ELIGIBLE_RULE_TRIGGERED",
        "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE",
        "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE",
        "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY",
        "PARTIAL_TRACE_LIMITATION"
      ],
      "zero_candidate_evidence_inventory": {
        "error_log_event_count": 0,
        "error_trace_span_count": 0,
        "incident_scope_member": true,
        "log_event_count": 22316,
        "metric_observation_count": 6774,
        "metric_series_count": 8,
        "partial_trace_unresolved_parent_count": 4,
        "service_resolved": true,
        "trace_span_count": 21813
      }
    }
  ],
  "schema_version": "v3_phase2_10e_r2a_failure_cases_v1"
}
```
