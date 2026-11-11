# V3 Phase 2.5 Hard-Negative Enrichment

Gold is used only to evaluate an already scored ranking. Strongest wrong targets are selected by the pre-specified enriched diagnostic score.

| Condition | Scope | Population | Gold available | Gold > wrong | Tie | Gold < wrong | Mean separation | Median separation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT | Full corpus | overall | 1497 | 1199 | 4 | 294 | 0.1660 | 0.2041 |
| P0_CURRENT | Full corpus | nontrivial | 568 | 270 | 4 | 294 | -0.0199 | -0.0053 |
| P0_CURRENT | Frozen Top-20 | overall | 1385 | 1199 | 4 | 182 | 0.1959 | 0.2200 |
| P0_CURRENT | Frozen Top-20 | nontrivial | 456 | 270 | 4 | 182 | 0.0254 | 0.0371 |
| P1_SYNONYMS | Full corpus | overall | 1497 | 1173 | 3 | 321 | 0.1585 | 0.1962 |
| P1_SYNONYMS | Full corpus | nontrivial | 568 | 244 | 3 | 321 | -0.0261 | -0.0286 |
| P1_SYNONYMS | Frozen Top-20 | overall | 1385 | 1193 | 4 | 188 | 0.1928 | 0.2200 |
| P1_SYNONYMS | Frozen Top-20 | nontrivial | 456 | 264 | 4 | 188 | 0.0224 | 0.0359 |
| P2_DEFINITIONS | Full corpus | overall | 1497 | 1199 | 4 | 294 | 0.1660 | 0.2041 |
| P2_DEFINITIONS | Full corpus | nontrivial | 568 | 270 | 4 | 294 | -0.0199 | -0.0053 |
| P2_DEFINITIONS | Frozen Top-20 | overall | 1385 | 1199 | 4 | 182 | 0.1959 | 0.2200 |
| P2_DEFINITIONS | Frozen Top-20 | nontrivial | 456 | 270 | 4 | 182 | 0.0254 | 0.0371 |
| P3_SYNONYMS_DEFINITIONS | Full corpus | overall | 1497 | 1173 | 3 | 321 | 0.1585 | 0.1962 |
| P3_SYNONYMS_DEFINITIONS | Full corpus | nontrivial | 568 | 244 | 3 | 321 | -0.0261 | -0.0286 |
| P3_SYNONYMS_DEFINITIONS | Frozen Top-20 | overall | 1385 | 1193 | 4 | 188 | 0.1928 | 0.2200 |
| P3_SYNONYMS_DEFINITIONS | Frozen Top-20 | nontrivial | 456 | 264 | 4 | 188 | 0.0224 | 0.0359 |
| P4_FULL_SOURCE_FAITHFUL | Full corpus | overall | 1497 | 1173 | 3 | 321 | 0.1585 | 0.1962 |
| P4_FULL_SOURCE_FAITHFUL | Full corpus | nontrivial | 568 | 244 | 3 | 321 | -0.0261 | -0.0286 |
| P4_FULL_SOURCE_FAITHFUL | Frozen Top-20 | overall | 1385 | 1193 | 4 | 188 | 0.1928 | 0.2200 |
| P4_FULL_SOURCE_FAITHFUL | Frozen Top-20 | nontrivial | 456 | 264 | 4 | 188 | 0.0224 | 0.0359 |

The Top-20 analysis excludes gold targets absent from the frozen candidate set. Candidate membership and order are verified unchanged for every profile condition.
