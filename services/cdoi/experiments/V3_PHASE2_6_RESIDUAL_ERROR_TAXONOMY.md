# V3 Phase 2.6 Residual Error Taxonomy

**IMPLEMENTED FACT:** This versioned, post-inference diagnostic derives its population from the corrected P1 persisted result and frozen CandidateSets. It does not change selectors, scoring, thresholds, profiles, or policy. Category labels are multi-label observable patterns, not causal findings.

## Primary population

`P1 resolved-synonyms V2; frozen Top-20; non-trivial; gold available; gold score < strongest wrong score`. Actual derived N = **138**. P1 ties remain a distinct population (N = 3).

## Observable category counts

| Category | Raw count | Residual % |
| --- | --- | --- |
| ALIAS_COLLISION | 0 | 0.0% |
| GRANULARITY_CONFUSION | 0 | 0.0% |
| PARENT_CHILD_CONFUSION | 0 | 0.0% |
| PART_WHOLE_CONFUSION | 0 | 0.0% |
| GENERIC_SPECIFIC_CONFUSION | 33 | 23.9% |
| LATERALITY_OR_REGION_SPECIFICITY | 14 | 10.1% |
| COMPOUND_CONCEPT_DECOMPOSITION | 0 | 0.0% |
| LEXICAL_NEAR_DUPLICATE | 27 | 19.6% |
| MISSING_SOURCE_SYNONYM | 127 | 92.0% |
| MISSING_TARGET_SYNONYM | 50 | 36.2% |
| STRUCTURAL_CONTEXT_NEEDED | 128 | 92.8% |
| POSSIBLE_REFERENCE_AMBIGUITY | 0 | 0.0% |
| OTHER_OBSERVED_PATTERN | 0 | 0.0% |
| INSUFFICIENT_OBSERVABLE_EVIDENCE | 0 | 0.0% |
| UNCLASSIFIED | 0 | 0.0% |

Categories overlap: `True`; percentages intentionally do not sum to 100%.

## Frozen ambiguity and gold-rank distributions

| Original frozen margin | Residual count |
| --- | --- |
| <0.02 | 30 |
| 0.02-0.05 | 32 |
| 0.05-0.10 | 23 |
| 0.10-0.20 | 22 |
| >=0.20 | 31 |

| Original frozen gold rank | Residual count |
| --- | --- |
| rank1 | 10 |
| rank2-5 | 80 |
| rank6-10 | 32 |
| rank11-20 | 16 |

## P0 → P1 selection transitions

| Transition | Count |
| --- | --- |
| correct_to_correct | 1192 |
| correct_to_wrong | 8 |
| wrong_to_correct | 52 |
| wrong_to_wrong | 245 |

Correct → wrong records: 8; wrong → correct records: 52. Existing P0-correct/P1-wrong alias placement remains inspected separately in each record.

## Read-only structural diagnostic

| Status | Residual count |
| --- | --- |
| STRUCTURAL_SIGNAL_PRESENT | 128 |
| STRUCTURAL_SIGNAL_NOT_OBSERVED | 10 |
| STRUCTURAL_DATA_UNAVAILABLE | 0 |

A structural difference is evidence that distinguishable text exists, not evidence that it would fix a decision.

## Interpretation boundary

**MEASURED RESULT:** corrected P1 retains a non-trivial gold-below-strongest-wrong residual population.

**DIAGNOSTIC INTERPRETATION:** residual failures exhibit observable alias, lexical-specificity, and/or structural-context patterns.

**RESEARCH HYPOTHESIS:** some residual cases may require a representation beyond lexical alias matching.

No causal claim is made that a synonym caused a result; no alias blacklist or Anatomy-specific heuristic was created.
