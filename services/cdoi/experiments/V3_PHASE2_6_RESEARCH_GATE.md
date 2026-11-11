# V3 Phase 2.6 Research Gate

Phase 2.5 V1 historical results are retained but not used to conclude synonym utility: it preserved RDF annotation-object IDs rather than their labelled text. Phase 2.6 V2 corrects and versions that extraction.

| Area | Status | Evidence |
| --- | --- | --- |
| preprocessing evidence preservation | SUPPORTED | Resolved RDF annotation-object labels are now versioned with field provenance |
| synonym utility under deterministic representation | PARTIALLY_SUPPORTED | P1-P0 fixed-Top-20 delta = +0.0294 |
| definition utility | NOT_SUPPORTED | Definitions are one-sided: Mouse 0 mapped cases; Human coverage reported |
| dense representation value | RUNTIME_BLOCKER | Clean CPU runtime reproduces c10.dll failure |
| dense enriched-profile value | RUNTIME_BLOCKER | No live dense embedding result |
| Qwen current-profile value | UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE |
| Qwen enriched-profile value | UNAVAILABLE | QWEN_LIVE_EVAL_UNAVAILABLE |
| hard-negative separation | PARTIALLY_SUPPORTED | Corrected deterministic evidence is measured; no stronger-selector comparison |
| easy-case preservation | SUPPORTED | P0 correct to P1 wrong at margin >=0.20: 0 |
| external generalization | DATA_MISSING | No qualifying second ontology pair |
| relation diversity | UNRESOLVED | RELATION_DIVERSITY_EVIDENCE_GAP |
| commitment-calibration readiness | DATA_MISSING | Independent calibration data absent |

No semantic decision policy change.
No production preprocessing/profile change.
No routing change.
No commitment calibration.

Phase 3 remains blocked. Dense selector research requires a functioning runtime; stronger-selector and hybrid research require same-case results plus independent external validation; commitment calibration requires independent calibration data and held-out validation.
