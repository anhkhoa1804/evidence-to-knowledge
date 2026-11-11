# V2.6.6 Diagnostic — Semantic-Profile Ablation

All five conditions used the same N=30 cases, opaque handles, original order,
model, schema, and retry policy. Only profile fields changed.

| Mode | Valid | Accuracy | Non-trivial | Abstain |
| --- | ---: | ---: | ---: | ---: |
| Q0 label | 28/30 | 0.7500 | 0.6818 | 0.2143 |
| Q1 + aliases | 28/30 | 0.7500 | 0.6818 | 0.2143 |
| Q2 + parent | 28/30 | 0.7857 | 0.7273 | 0.1786 |
| Q3 + child | 28/30 | 0.7857 | 0.7273 | 0.1786 |
| Q4 + properties | 28/30 | 0.7857 | 0.7273 | 0.1786 |

On the 28 Q0/Q4 jointly valid cases, one changes from wrong to correct and none
from correct to wrong. One source is representation-sensitive across modes.

## Interpretation

Labels account for most observed performance on this subset. Parent context
shows a modest incremental improvement; child and property fields show no
additional measured gain here. This is partial, not conclusive, support for
contextual semantic evidence beyond lexical/world knowledge.
