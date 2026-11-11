# Preprocessing MVP Demo

The deterministic fixture execution used `tests/fixtures/preprocessing_demo/manifest.yaml` and produced the machine-readable artifact set in `experiments/archive/preprocessing_mvp_demo/`.

| Measure | Count |
| --- | ---: |
| raw records | 14 |
| normalized entities | 3 |
| normalized relations | 3 |
| normalized events | 3 |
| valid declared changes | 4 |
| normalized semantic terms | 3 |
| unresolved / invalid records | 4 |
| unreviewed class candidates | 4 |
| unreviewed object-property candidates | 2 |

The evidence-schema bridge aggregates three service observations into one `SoftwareService` candidate, and three dependency observations into `calls` (support 2, one partial unknown-target observation) and `reads_from` property candidates. Example trace: `calls` → two normalized relation evidence IDs → `topology/dependencies.jsonl` records 1 and 3 → their immutable raw evidence IDs. `SoftwareService` → three normalized entity evidence IDs → `inventory/services.csv` records 2–4. The three glossary candidates remain distinct and still pass through the existing `StructuredExtractor` boundary. Inventory services, dependency topology, and log events were not emitted as ontology classes. `manifest.json` contains input/source/generated hashes, schema diagnostics, versions, and rule usage.

The change source has six raw records: four valid changes, one unresolved target, and two invalid declarations (timestamp/type). It records a payment-service deployment at 09:55 and an error log at 10:00, but makes no causal claim. `changes.jsonl` preserves the version transition and rollback reference separately from logs.

This is an engineering fixture, not an Anatomy, Dense, Qwen, or external-benchmark result. It makes no semantic policy, routing, calibration, commitment, RCA, or canonical-KG change.
