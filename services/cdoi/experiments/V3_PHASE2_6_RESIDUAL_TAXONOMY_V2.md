# V3 Phase 2.6 Residual Taxonomy V2

**IMPLEMENTED FACT:** V2 separates alias availability, exact normalized alias overlap, semantic surface patterns, and structural-profile comparison. It is post-inference diagnostic data only.

## Population

Derived residual N = **138**; no count is hard-coded.

## Alias availability

| Field | Observable state | N |
| --- | --- | --- |
| source_alias_state | NO_RESOLVED_SOURCE_ALIAS_OBSERVED | 127 |
| source_alias_state | RESOLVED_SOURCE_ALIAS_PRESENT | 11 |
| gold_alias_state | NO_RESOLVED_GOLD_TARGET_ALIAS_OBSERVED | 112 |
| gold_alias_state | RESOLVED_GOLD_TARGET_ALIAS_PRESENT | 26 |
| wrong_alias_state | RESOLVED_WRONG_TARGET_ALIAS_PRESENT | 71 |
| wrong_alias_state | NO_RESOLVED_WRONG_TARGET_ALIAS_OBSERVED | 67 |

## Semantic surface patterns

| Pattern | N |
| --- | --- |
| LATERALITY_OR_REGION_SPECIFICITY | 14 |
| UNCLASSIFIED_SEMANTIC_PATTERN | 91 |
| GENERIC_SPECIFIC_CONFUSION | 33 |
| LEXICAL_NEAR_DUPLICATE | 27 |

## Structural comparison

| Observable status | N |
| --- | --- |
| STRUCTURAL_PROFILE_DIFFERENCE_PRESENT | 128 |
| STRUCTURAL_PROFILE_DIFFERENCE_NOT_OBSERVED | 10 |

## Interpretation boundary

`NO_RESOLVED_*_ALIAS_OBSERVED` describes this P1 profile only; it does not claim a source ontology lacks synonyms. `STRUCTURAL_PROFILE_DIFFERENCE_PRESENT` does not claim structural evidence is necessary or sufficient to correct a selection. No selector/scoring/policy behavior changed.
