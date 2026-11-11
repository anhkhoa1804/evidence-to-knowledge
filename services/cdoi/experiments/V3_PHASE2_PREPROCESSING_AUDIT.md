# V3 Phase 2 Raw-versus-Extracted Preprocessing Audit

The audit parsed raw Anatomy OWL files and compared profile availability against
the existing `_profiles` extractor. It used no reference mappings.

| Field | Mouse raw / extracted / recall | Human raw / extracted / recall | Interpretation |
| --- | --- | --- | --- |
| label | 2,737 / 2,744 / 100% | 3,298 / 3,304 / 100% | Seven/six local-name fallbacks are `FILTERED_BY_DESIGN`, not raw labels. |
| aliases | 305 / 0 / 0% | 3,291 / 0 / 0% | `UNSUPPORTED_PREDICATE`, not absence. |
| definitions | 0 / 0 / N/A | 840 / 0 / 0% | Human definitions are `UNSUPPORTED_PREDICATE`. |
| parents | 2,736 / 2,736 / 100% | 3,297 / 3,297 / 100% | Remaining nodes have no raw parent edge. |
| children | 483 / 483 / 100% | 673 / 673 / 100% | Remaining nodes have no raw child edge. |
| outgoing property neighbourhood | 316 / 316 / 100% | 3,291 / 3,291 / 100% | Current structural extraction is complete for its definition. |
| incoming property neighbourhood | 506 / 506 / 100% | 533 / 533 / 100% | Current structural extraction is complete for its definition. |

## Discovered annotation predicates

| Ontology | Predicate | Triple count | Mapped field | Currently extracted |
| --- | --- | ---: | --- | --- |
| Mouse | `rdfs:label` | 3,084 | label | yes |
| Mouse | `oboInOwl:hasRelatedSynonym` | 344 | aliases | no |
| Human | `rdfs:label` | 9,403 | label | yes |
| Human | `oboInOwl:hasRelatedSynonym` | 5,264 | aliases | no |
| Human | `oboInOwl:hasDefinition` | 840 | definition | no |

## Result categories

`ABSENT_IN_SOURCE` accounts for missing mouse definitions, leaf children, root
parents, and genuinely absent relation edges. `UNSUPPORTED_PREDICATE` accounts
for all extracted-profile alias loss and human-definition loss. No raw edge was
found and then silently dropped by the recognized hierarchy/property extractors.
`FILTERED_BY_DESIGN` records local-name label fallbacks rather than an invented
annotation.

## Experimental enrichment only

`experimental_enriched_profiles` supplements only predicates whose local names
explicitly indicate synonym/alias/definition. It adds aliases to 305 mouse and
3,291 human profiles, plus definitions to 840 human profiles. It does not alter
the frozen `_profiles` function or normal CDOI pipeline. On fixed candidate
sets, R1/R2 selection is unchanged by design; Dense is runtime-blocked and
Qwen has no credentialed Phase-2 run, so no semantic-value conclusion is made.
