# V3 Phase 2.6 Alias-Collision Reconciliation

**MEASURED RESULT:** the earlier 8-case report is the P0-correct to P1-wrong transition population. Its labels classify where aliases were available, not necessarily exact text equality. V2 records exact normalized overlap separately.

| Regression source | In residual-138? | Legacy placement label | V2 exact-overlap field |
| --- | --- | --- | --- |
| muscle | no | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | SOURCE_LABEL_EQUALS_WRONG_ALIAS |
| pigmented retinal epithelium | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |
| upper respiratory tract | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |
| gall bladder smooth muscle | yes | SOURCE_ALIAS_TO_WRONG_LABEL_COLLISION | NONE |
| urinary bladder fundus region | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |
| right lung lobe | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |
| urinary bladder wall | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |
| pancreas secretion | yes | SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION | NONE |

All regressions = 8; in residual-138 = 7; exact normalized overlap = 1.

The old residual `ALIAS_COLLISION=0` was not a selector inconsistency: it used a narrower residual population and a different, exact-overlap interpretation than the legacy placement label. V2 removes the overloaded term.
