# V3 Phase 2 Relation-Diversity Inventory

| Dataset/artifact | Relation coverage | Source type | Evaluation quality |
| --- | --- | --- | --- |
| OAEI Anatomy full-corpus diagnostic | 1,497 reference correspondences, equivalence only | External licensed benchmark | Full target corpus, but equivalence-only |
| CDOI-Bench / `gold.json` | equivalence, subclass, new concept, unresolved, properties, bridge and unsafe-equivalence safety cases | Project synthetic controlled | Regression/controlled evidence only |
| Domain fixtures and bridge heuristic | class/property proposals plus one Order-to-Shipment bridge pattern | Synthetic fixtures | No independent reference corpus |
| RCA application fixture | impact edges, not ontology relation labels | Synthetic controlled | Not selector relation validation |

Status: `RELATION_DIVERSITY_EVIDENCE_GAP`. Current external evidence supports
neither general subclass/superclass/relation classification nor bridge
generalization. Synthetic cases remain useful for safety regression but must
not be presented as independent semantic validation.
