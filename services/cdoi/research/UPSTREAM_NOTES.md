# Upstream Inspection Notes

All repositories under `research/upstream` are shallow, read-only research checkouts. No upstream code is vendored into `src/cdoi`.

| Repository | Commit | License | Inspected | Reused in V1 | Intentionally not reused |
| --- | --- | --- | --- | --- | --- |
| semanticarts/gist | d7564e4 | CC BY 4.0 (`LICENSE.txt`) | ontology layout, validation assets, foundation vocabulary | immutable adapter concept and selected classes | full import; runtime needs a compact portable fixture |
| hkust-knowcomp/autoschemakg | d0a1666 | MIT | conceptualization/schema-induction organization | context-aware conceptualization boundary | end-to-end one-shot schema workflow; CDOI is stateful |
| sciknoworg/OntoAligner | 65e5fe3 | Apache-2.0 | tutorials, parser/alignment/evaluation organization | transparent retrieval/alignment separation | dependency-heavy execution stack |
| KRR-Oxford/DeepOnto | 35c91c0 | Apache-2.0 | OWL/reasoner adapters and taxonomy operations | optional reasoner adapter boundary | mandatory Java integration |
| LiberAI/OntoEKG | 8cd17ca | MIT | extraction and hierarchy-induction baseline | extraction/schema separation | its pipeline architecture |
| edmcouncil/fibo | 08322e9 | MIT | finance ontology organization | optional reference-index boundary | full runtime graph import |
| HamedBabaei/LLMs4OL | a0bca35 | MIT | ontology-learning task/evaluation framing | metric adapter boundary | benchmark dependency/runtime |
| KRR-Oxford/LM-ontology-concept-placement | 5d07bac | MIT | placement research framing | future placement evaluation boundary | model/runtime stack |

Upstream content was inspected as research material; exact license eligibility must be reviewed before any future code or artifact redistribution. The EDC paper has no verified official repository included in this checkout; its retrieval/canonicalization sequence is documented as paper-inspired only.
