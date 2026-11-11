# V2.6.6 Diagnostic — Opaque Candidate Handles

Original IRIs were replaced in the prompt by deterministic reversible `C01`–
`C10` handles; labels and profile fields were unchanged and original IDs were
not exposed to Qwen.

| Condition | Valid | Accuracy on valid | Non-trivial | Abstain |
| --- | ---: | ---: | ---: | ---: |
| Original ID | 26/30 | 0.7692 | 0.7000 | 0.1923 |
| Opaque ID | 23/30 | 0.7391 | 0.6471 | 0.2609 |

Every case with at least one valid response had the same mapped-back semantic
target across ID conditions; there were no representation-sensitive target
changes. The opaque condition suffered more technical failures (7 versus 4),
so its modest conditional accuracy drop cannot be cleanly separated from this
reliability variation. The result weakens—but cannot eliminate—the possibility
that ontology identifiers explain the observed Qwen gain.
