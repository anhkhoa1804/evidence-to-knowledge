# V3 Phase 2.8 — Metrics Evidence Integration

Phase 2.8 adds one optional manifest source: metric_observation_csv. It produces immutable NormalizedMetricEvidence records under the existing backward-compatible cdoi_preprocessing_v1 contract. The independent metric record contract is metric_evidence_v1.

## Source contract

The constrained CSV requires metric_id, timestamp, service_id, metric_name, value, unit, and metric_kind. Optional fields are aggregation, sampling_interval, window_start, window_end, source_metric_name, attributes, and environment. This phase does not add scraping, API, database, streaming, Prometheus, or OpenTelemetry collectors.

The numeric value is a finite JSON number. NaN, infinity, negative infinity, and malformed numeric input become INVALID_METRIC_VALUE; they are never silently turned into zero. The raw input record remains preserved.

Supported declared metric kinds are GAUGE, COUNTER, HISTOGRAM_SAMPLE, SUMMARY_SAMPLE, and OTHER_DECLARED. The adapter never guesses a kind from a metric name. Gauge observations remain point-in-time observations. Counter observations remain raw counter readings; Phase 2.8 does not calculate a window total or delta.

## Unit and series semantics

Supported declared units are ms, s, bytes, percent, ratio, count, and requests_per_second. They are preserved without automatic conversion, and normalized_unit equals the supported declared unit. Unsupported units become UNSUPPORTED_METRIC_UNIT. Observations with the same service, metric name, kind, and aggregation but incompatible supported units remain separate and generate METRIC_UNIT_CONFLICT records.

Metric-series identity is content-derived from exact entity ID, metric name, unit, metric kind, and aggregation. Sampling interval and aggregation are preserved rather than inferred. Therefore average request latency, p95 request latency, and a byte-valued observation sharing a display name cannot silently collapse into one series.

## Context and snapshot integration

OperationalEvidenceContext now has an additive metrics field. operational_evidence_context_v1 remains the serialization version because metrics is an optional additive field; old snapshots that omit metrics are interpreted as an empty metric collection and historical Phase 2.7 artifacts were not rewritten.

Metric selection uses the same exact-ID and inclusive UTC interval contract as logs and changes. DIRECT_ONLY includes only direct incident entities. ONE_HOP additionally includes metrics of existing one-hop topology neighbors; no metric changes graph scope. Selection provenance uses METRIC_DIRECT_ENTITY_IN_WINDOW_V1 or METRIC_ONE_HOP_ENTITY_IN_WINDOW_V1.

## Safety boundary

A metric is an observation, not an interpretation. Metric value does not imply anomaly. Temporal ordering does not imply causality. This phase creates no metric-derived SchemaCandidate or DataPropertyCandidate, no semantic glossary alignment, no proposal/review/approval result, and no ontology or canonical-KG assertion.

Metric fields retain normalized evidence ID and provenance back to raw evidence ID, source record/file, adapter, dataset manifest, and declared timezone.
