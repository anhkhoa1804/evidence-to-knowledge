# Benchmarks

| Benchmark | Type | Included | License/status | Intended measurement |
| --- | --- | --- | --- | --- |
| CDOI-Bench | project-owned synthetic | yes | repository fixture | mechanism, safety hard negatives, property/bridge/promotion decisions |
| OAEI | external ontology alignment | no | track-specific setup required | class/property correspondence and false-merge behavior |
| OET / LM placement export | external concept placement | no | source-specific setup required | retrieval and parent placement |
| RCAEval | external downstream RCA | no | source-specific setup required | ranking utility with explicit graph contribution variants |

Do not average synthetic and external scores. Every external run must store its exact source release, license/terms, checksum, transformed-case count, split policy, and transformation mapping in the result manifest.

The adapters use normalized imports only at their boundaries. They do not modify the CDOI ontology schemas or vendor upstream code/data.

## Alignment reporting rule (added 2026-10-27)

Alignment results must not be reported as exact-triple precision alone. Report, per emission set and with denominators: EXACT_MATCH / ENTAILED_MATCH / CONTRADICTED / UNADJUDICATED counts, the share of emissions whose target is an ontology root (depth 0, uninformative), and the informative share (exact or entailed with a non-root target). UNADJUDICATED is not an error and entailed matches are not credited as exact. Generator: `tools/alignment_benchmark_report_v1.py`; semantics and first application: `experiments/alignment_evidence_ceiling_v1/PREREG_E4.md`, `BENCHMARK_REPORT_E4.md`.
