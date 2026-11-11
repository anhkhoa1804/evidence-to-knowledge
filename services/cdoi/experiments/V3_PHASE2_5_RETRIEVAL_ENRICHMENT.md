# V3 Phase 2.5 Retrieval Enrichment

Full-corpus rankings use all 3,304 Human targets and read the OAEI reference only after ranking. `P0_CURRENT` exactly reduces to the frozen label-only lexical score. Enriched conditions use a pre-specified best label/alias term-pair comparison, avoiding artificial broadening from concatenating every alias into one string. `Enriched diagnostic` is 0.8 x max(term-pair lexical, source-derived definition support) + 0.2 x already-extracted structural overlap. Neither diagnostic is a production R2 change or tuned on references.

## Retrieval metrics

| Condition | Mode | R@1 | R@5 | R@10 | R@20 | MRR | Non-trivial R@1 | Non-trivial MRR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT | Alias-aware lexical diagnostic | 0.7949 | 0.8784 | 0.9058 | 0.9252 | 0.8332 | 0.4595 | 0.5603 |
| P0_CURRENT | Enriched diagnostic | 0.8016 | 0.8965 | 0.9178 | 0.9292 | 0.8433 | 0.4771 | 0.5871 |
| P1_SYNONYMS | Alias-aware lexical diagnostic | 0.7756 | 0.8584 | 0.8791 | 0.8931 | 0.8132 | 0.4085 | 0.5077 |
| P1_SYNONYMS | Enriched diagnostic | 0.7836 | 0.8771 | 0.8951 | 0.9078 | 0.8246 | 0.4296 | 0.5377 |
| P2_DEFINITIONS | Alias-aware lexical diagnostic | 0.7949 | 0.8784 | 0.9058 | 0.9252 | 0.8332 | 0.4595 | 0.5603 |
| P2_DEFINITIONS | Enriched diagnostic | 0.8016 | 0.8965 | 0.9178 | 0.9292 | 0.8433 | 0.4771 | 0.5871 |
| P3_SYNONYMS_DEFINITIONS | Alias-aware lexical diagnostic | 0.7756 | 0.8584 | 0.8791 | 0.8931 | 0.8132 | 0.4085 | 0.5077 |
| P3_SYNONYMS_DEFINITIONS | Enriched diagnostic | 0.7836 | 0.8771 | 0.8951 | 0.9078 | 0.8246 | 0.4296 | 0.5377 |
| P4_FULL_SOURCE_FAITHFUL | Alias-aware lexical diagnostic | 0.7756 | 0.8584 | 0.8791 | 0.8931 | 0.8132 | 0.4085 | 0.5077 |
| P4_FULL_SOURCE_FAITHFUL | Enriched diagnostic | 0.7836 | 0.8771 | 0.8951 | 0.9078 | 0.8246 | 0.4296 | 0.5377 |

## Paired enriched-diagnostic rank delta versus P0

| Condition | Improved | Unchanged | Worsened | Entered top-20 | Left top-20 |
| --- | --- | --- | --- | --- | --- |
| P0_CURRENT | 0 | 1497 | 0 | 0 | 0 |
| P1_SYNONYMS | 16 | 1389 | 92 | 2 | 34 |
| P2_DEFINITIONS | 0 | 1497 | 0 | 0 | 0 |
| P3_SYNONYMS_DEFINITIONS | 16 | 1389 | 92 | 2 | 34 |
| P4_FULL_SOURCE_FAITHFUL | 16 | 1389 | 92 | 2 | 34 |

P2 can only add Human definitions because no raw Mouse definition annotation exists. P4 is structurally identical to P3 under this source pair.
