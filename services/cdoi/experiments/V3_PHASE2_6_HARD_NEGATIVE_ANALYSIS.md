# V3 Phase 2.6 Hard-Negative and Difficult-Case Analysis

Only deterministic, corrected-profile results are measured. Dense is blocked and Qwen is unavailable, so this report does not attribute any stronger-selector effect.

## Non-trivial gold versus strongest wrong

| Condition | Scope | Gold available | Gold > wrong | Tie | Gold < wrong | Mean | Median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_CURRENT_V1 | full corpus | 568 | 270 | 4 | 294 | -0.0199 | -0.0053 |
| P0_CURRENT_V1 | frozen Top-20 | 456 | 270 | 4 | 182 | 0.0254 | 0.0371 |
| P1_SYNONYMS_RESOLVED_V2 | full corpus | 568 | 353 | 3 | 212 | 0.0496 | 0.0579 |
| P1_SYNONYMS_RESOLVED_V2 | frozen Top-20 | 456 | 315 | 3 | 138 | 0.0778 | 0.0698 |
| P2_DEFINITIONS_RESOLVED_V2 | full corpus | 568 | 270 | 4 | 294 | -0.0199 | -0.0053 |
| P2_DEFINITIONS_RESOLVED_V2 | frozen Top-20 | 456 | 270 | 4 | 182 | 0.0254 | 0.0371 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | full corpus | 568 | 353 | 3 | 212 | 0.0496 | 0.0579 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | frozen Top-20 | 456 | 315 | 3 | 138 | 0.0778 | 0.0698 |
| P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2 | full corpus | 568 | 353 | 3 | 212 | 0.0496 | 0.0579 |
| P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2 | frozen Top-20 | 456 | 315 | 3 | 138 | 0.0778 | 0.0698 |

## Fixed-Top-20 difficult cases

| Condition | Diagnostic group | N | Accuracy |
| --- | --- | --- | --- |
| P0_CURRENT_V1 | <0.02 | 122 | 0.2131 |
| P0_CURRENT_V1 | 0.02-0.05 | 105 | 0.3143 |
| P0_CURRENT_V1 | 0.05-0.10 | 128 | 0.5938 |
| P0_CURRENT_V1 | 0.10-0.20 | 241 | 0.8548 |
| P0_CURRENT_V1 | >=0.20 | 901 | 0.9534 |
| P0_CURRENT_V1 | nontrivial | 568 | 0.4771 |
| P0_CURRENT_V1 | rank2-5 | 125 | 0.1040 |
| P0_CURRENT_V1 | rank6-10 | 41 | 0.0244 |
| P1_SYNONYMS_RESOLVED_V2 | <0.02 | 122 | 0.3443 |
| P1_SYNONYMS_RESOLVED_V2 | 0.02-0.05 | 105 | 0.4762 |
| P1_SYNONYMS_RESOLVED_V2 | 0.05-0.10 | 128 | 0.6562 |
| P1_SYNONYMS_RESOLVED_V2 | 0.10-0.20 | 241 | 0.8631 |
| P1_SYNONYMS_RESOLVED_V2 | >=0.20 | 901 | 0.9545 |
| P1_SYNONYMS_RESOLVED_V2 | nontrivial | 568 | 0.5563 |
| P1_SYNONYMS_RESOLVED_V2 | rank2-5 | 125 | 0.3440 |
| P1_SYNONYMS_RESOLVED_V2 | rank6-10 | 41 | 0.2195 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | <0.02 | 122 | 0.3443 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | 0.02-0.05 | 105 | 0.4762 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | 0.05-0.10 | 128 | 0.6562 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | 0.10-0.20 | 241 | 0.8631 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | >=0.20 | 901 | 0.9545 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | nontrivial | 568 | 0.5563 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | rank2-5 | 125 | 0.3440 |
| P3_SYNONYMS_DEFINITIONS_RESOLVED_V2 | rank6-10 | 41 | 0.2195 |
