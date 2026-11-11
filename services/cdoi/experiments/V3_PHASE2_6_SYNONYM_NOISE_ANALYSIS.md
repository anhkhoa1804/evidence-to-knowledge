# V3 Phase 2.6 Synonym Noise Analysis

This is a systematic inspection of all P0-correct to resolved-P1-wrong fixed-CandidateSet transitions. Categories report observable alias placement, not causal certainty; no blacklist or Anatomy-specific filter was created.

| Transition | Count |
| --- | --- |
| correct_to_correct | 1192 |
| correct_to_wrong | 8 |
| wrong_to_correct | 52 |
| wrong_to_wrong | 245 |

## Observed regression cases

| Source | Gold | Resolved-P1 wrong target | Observed alias pattern | Original margin |
| --- | --- | --- | --- | --- |
| muscle | Muscle | Muscle_Tissue | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.1750 |
| pigmented retinal epithelium | Retinal_Pigment_Epithelium | Pigment_Epithelium | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.0375 |
| upper respiratory tract | Upper_Respiratory_System | Respiratory_System | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.0774 |
| gall bladder smooth muscle | Gallbladder_Smooth_Muscle_Tissue | Artery_Smooth_Muscle_Tissue | SOURCE_ALIAS_TO_WRONG_LABEL_COLLISION | 0.1079 |
| urinary bladder fundus region | Bladder_Fundus | Bladder_Trigone | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.0586 |
| right lung lobe | Lobe_of_the_Right_Lung | Lower_Lobe_of_the_Right_Lung | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.0350 |
| urinary bladder wall | Bladder_Wall | Bladder | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.1403 |
| pancreas secretion | Pancreatic_Secretion | Pancreatic_Endocrine_Secretion | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | 0.0883 |

The actual raw annotation object and resolved label are preserved in the versioned provenance artifact.
