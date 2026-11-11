# V3 External DH Evidence Coverage

| Field | P0 | P1 |
| --- | --- | --- |
| mapped_cases | 6 | 6 |
| source_labels | 6 | 6 |
| target_labels | 6 | 6 |
| both_labels | 6 | 6 |
| source_aliases | 0 | 0 |
| target_aliases | 0 | 0 |
| bilateral_aliases | 0 | 0 |
| source_definitions | 0 | 0 |
| target_definitions | 0 | 0 |
| bilateral_definitions | 0 | 0 |
| source_parents | 2 | 2 |
| target_parents | 6 | 6 |

| Raw definition field | Mapped cases |
| --- | --- |
| source_raw_definition_candidates | 0 |
| target_raw_definition_candidates | 6 |
| bilateral_raw_definition_candidates | 0 |

| Ontology / predicate | Count | Profile field | P1 extracted / status |
| --- | --- | --- | --- |
| source http://thesauri.dainst.org/schema#memberOf | 13 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/1999/02/22-rdf-syntax-ns#type | 1348 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#altLabel | 134 | alias | True / EXTRACTED |
| source http://www.w3.org/2004/02/skos/core#broader | 1347 | parent | True / EXTRACTED |
| source http://www.w3.org/2004/02/skos/core#closeMatch | 3 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#definition | 2 | definition | True / EXTRACTED |
| source http://www.w3.org/2004/02/skos/core#editorialNote | 5 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#exactMatch | 9 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#example | 8 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#historyNote | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#inScheme | 1348 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#narrower | 1347 | child | True / EXTRACTED |
| source http://www.w3.org/2004/02/skos/core#prefLabel | 1311 | label | True / EXTRACTED |
| source http://www.w3.org/2004/02/skos/core#related | 55 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#relatedMatch | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#scopeNote | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| source http://www.w3.org/2004/02/skos/core#topConceptOf | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://purl.org/dc/terms/description | 70 | definition | False / UNSUPPORTED_STANDARD_DEFINITION_PREDICATE |
| target http://purl.org/dc/terms/identifier | 60 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://purl.org/umu/uneskos#memberOf | 60 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/1999/02/22-rdf-syntax-ns#type | 60 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2000/01/rdf-schema#type | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#altLabel | 14 | alias | True / EXTRACTED |
| target http://www.w3.org/2004/02/skos/core#broadMatch | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#broader | 59 | parent | True / EXTRACTED |
| target http://www.w3.org/2004/02/skos/core#definition | 1 | definition | True / EXTRACTED |
| target http://www.w3.org/2004/02/skos/core#exactMatch | 4 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#inScheme | 60 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#narrower | 59 | child | True / EXTRACTED |
| target http://www.w3.org/2004/02/skos/core#prefLabel | 60 | label | True / EXTRACTED |
| target http://www.w3.org/2004/02/skos/core#related | 48 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#relatedMatch | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |
| target http://www.w3.org/2004/02/skos/core#topConceptOf | 1 | other | False / OUT_OF_SCOPE_RELATION_OR_METADATA |

Definition status: `INSUFFICIENT_BILATERAL_DEFINITION_EVIDENCE`. `dcterms:description` is audited as a standard definition-like predicate but is not silently added to P0/P1. SKOS `prefLabel`, `altLabel`, `definition`, and `broader`/`narrower` were consumed only in the research extractor. P0 keeps alias extraction disabled; P1 enables it without replacing labels.
