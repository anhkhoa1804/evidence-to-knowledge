# V3 Preprocessing Semantic-Profile Audit

## Corpus and parser

This audit reads the existing Anatomy 2026 normalized full-corpus index:
`data/benchmarks/external/oaei/anatomy-2026/normalized_full_corpus_index.json`.
The extraction path is `_profiles` in `oaei_full_corpus.py`: labels from
`rdfs:label` (local name fallback); aliases from `skos:altLabel`/`skos:prefLabel`;
definitions from `rdfs:comment`/`skos:definition`; parents/children from
`rdfs:subClassOf`; and lightweight property neighbourhood from graph predicates.
No missing field is fabricated.

| Field | Source: 2,744 | Target: 3,304 | Source annotation/parser | Missing reason |
| --- | ---: | ---: | --- | --- |
| label | 100.00% | 100.00% | `rdfs:label`, local-name fallback | None after fallback |
| normalized label | 100.00% | 100.00% | `normalize(label)` | Derived deterministically |
| aliases | 0.00% | 0.00% | SKOS alt/pref label | No extracted annotation values |
| definition | 0.00% | 0.00% | comment/SKOS definition | No extracted annotation values |
| parents | 99.71% | 99.79% | `rdfs:subClassOf` objects | Root/unconnected classes |
| children | 17.60% | 20.37% | inverse `rdfs:subClassOf` | Leaf classes |
| object-property neighbourhood | 11.52% | 99.61% | outgoing non-schema predicates | Ontology graph asymmetry / no outgoing predicates |
| data-property neighbourhood | 18.44% | 16.13% | incoming non-schema predicates | No matching incoming predicates |

## Interpretation

IMPLEMENTED FACT: labels and parent context have near-complete coverage; alias
and definition extraction did not find values in this index. MEASURED RESULT:
V2.6.6 found label-heavy Qwen behavior and modest parent-context gain on its
bounded subset. DIAGNOSTIC INTERPRETATION: semantic weakness may reflect source
annotation sparsity as well as model selection. RESEARCH HYPOTHESIS: richer
property context will help elsewhere; the audit does not establish it.
