# V3 Phase 2.5 Source-Faithful Profile Enrichment

All enrichment is experiment-only. `P0_CURRENT` is the frozen `_profiles` representation; normal ingest, historical artifacts, R1/R2, review/commit, and canonical-KG behavior were not modified. Profile construction did not read reference mappings. Every added value is `SOURCE_PROVIDED`; no model-generated enrichment exists.

## Discovered predicates

| Ontology | Predicate | Field | Triples | Current extraction |
| --- | --- | --- | --- | --- |
| Mouse | `http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym` | aliases | 344 | no |
| Human | `http://www.geneontology.org/formats/oboInOwl#hasDefinition` | definition | 840 | no |
| Human | `http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym` | aliases | 5264 | no |

## Coverage by condition

| Condition | Side | Concepts | Labels | Synonym profiles | Mean synonyms | Definition profiles | Parents | Children | Properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT | Mouse | 2744 | 2744 | 0 | 0.0000 | 0 | 2736 | 483 | 726 |
| P0_CURRENT | Human | 3304 | 3304 | 0 | 0.0000 | 0 | 3297 | 673 | 3291 |
| P1_SYNONYMS | Mouse | 2744 | 2744 | 305 | 0.1254 | 0 | 2736 | 483 | 726 |
| P1_SYNONYMS | Human | 3304 | 3304 | 3291 | 1.5932 | 0 | 3297 | 673 | 3291 |
| P2_DEFINITIONS | Mouse | 2744 | 2744 | 0 | 0.0000 | 0 | 2736 | 483 | 726 |
| P2_DEFINITIONS | Human | 3304 | 3304 | 0 | 0.0000 | 840 | 3297 | 673 | 3291 |
| P3_SYNONYMS_DEFINITIONS | Mouse | 2744 | 2744 | 305 | 0.1254 | 0 | 2736 | 483 | 726 |
| P3_SYNONYMS_DEFINITIONS | Human | 3304 | 3304 | 3291 | 1.5932 | 840 | 3297 | 673 | 3291 |
| P4_FULL_SOURCE_FAITHFUL | Mouse | 2744 | 2744 | 305 | 0.1254 | 0 | 2736 | 483 | 726 |
| P4_FULL_SOURCE_FAITHFUL | Human | 3304 | 3304 | 3291 | 1.5932 | 840 | 3297 | 673 | 3291 |

P4 has the same structural fields as P3 because Phase 2 established 100% recall for recognized hierarchy/property extraction. Mouse contains no raw definitions. Full annotation-level provenance is in `experiments/archive/v3_phase2_5_profile_enrichment/PROFILE_PROVENANCE.json`.
