# V3 Phase 2 Second-Domain Qualification

Status: `DATA_MISSING`.

| Asset inspected | Qualification result |
| --- | --- |
| OAEI Anatomy 2026 | Qualifies as the existing diagnostic pair; not a second domain. |
| OET / concept-placement location | No local split artifact; source/target full-corpus/reference package unavailable. |
| RCAEval location | No normalized `cases.json`; it is a ranking adapter, not an ontology-pair selector corpus. |
| CDOI-Bench and fixture ontologies | Synthetic controlled regression data; not independent external validation. |
| OAEI positive-pair adapter | Reference-positive diagnostics only; lacks a general full target-corpus second-pair evaluation package. |

A qualifying future `DatasetAdapter` must provide source profiles, full target
profiles, mapping references, per-mapping relation types, license/provenance,
and a reproducible profile extraction version. `OntologyPairDataset` enforces
that references point into supplied source/target corpora and accepts arbitrary
identifiers; it contains no Anatomy-specific identifier assumption.
