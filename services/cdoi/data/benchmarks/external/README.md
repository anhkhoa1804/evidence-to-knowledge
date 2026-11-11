# External Benchmark Setup

External material is intentionally absent from this repository. Record the exact source, release or year, license, checksum, acquisition date, and transformation manifest before running an external experiment.

| Dataset | Expected directory | Adapter | Task | Status in this checkout |
| --- | --- | --- | --- | --- |
| OAEI alignment track | `data/benchmarks/external/oaei/` | `OAEIAlignmentAdapter` | class/property correspondence | setup required |
| OET or LM concept placement export | `data/benchmarks/external/oet/` | `ConceptPlacementAdapter` | retrieval and parent placement | setup required |
| RCAEval normalized case index | `data/benchmarks/external/rcaeval/` | `RCAEvalAdapter` | downstream rank scoring | setup required |

## OAEI

Official source: [OAEI](https://oaei.ontologymatching.org/). Record the selected campaign year/track and its data-use terms. Place `source.owl`, `target.owl`, and `reference.rdf` in the OAEI directory, or place a reviewed normalized `cases.json` there. The RDF adapter only translates labels, OWL type, and reference cells; it does not change CDOI core structures.

## Concept placement

Official implementation source: [LM ontology concept placement](https://github.com/KRR-Oxford/LM-ontology-concept-placement) (MIT repository license; the underlying source datasets can have additional terms). Place `test.json` and optional `dev.json` in the OET directory. Each normalized item requires `case_id`, `candidate` or `mention`, `parent_id`, and `candidate_parents` (`id`/`label` objects or identifiers). Preserve original IDs and a source pointer in every item.

## RCAEval

Official source: [RCAEval](https://github.com/phamquiluan/RCAEval) (repository and dataset license must be recorded for the selected release). RCAEval is large and remains external. Create a small, reproducible `cases.json` index with `case_id`, `gold_service`, `ranking`, source release, and source path. The adapter scores supplied rankings only; it does not present a synthetic connectivity fixture as an external RCA result.
