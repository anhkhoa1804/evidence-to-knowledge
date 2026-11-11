# Bug and Issue Ledger

| ID | Status | Finding | Evidence / next action |
|---|---|---|---|
| B-001 | `PARTIALLY RESOLVED` | Producer did not emit the KP ExtractionPackage v1 wire contract | A deterministic PDF projection and real serialized KP round-trip now pass for represented fields; remaining contract losses/owner decisions are in `docs/extraction-kp-contract/OWNER_DECISIONS.md` |
| B-002 | `RESOURCE_BLOCKED` | OCR/layout model path is not installed on this 8 GiB CPU machine | Keep native PDF/Office path; qualify a single CPU OCR case only after a compact existing backend is available |
| B-003 | `ENVIRONMENT_LIMITATION` | Full test suite has five optional-data/model failures | 478 pass, 16 skip; absent benchmark data, Docling, Torch/Transformers; do not install a heavy stack solely to clear them |
| B-004 | `NOT MEASURED` | SemTab selected sample has not been checked for NIL/noisy/ambiguous strata | Gold is sealed; after predictions are frozen, report the actual strata and move the sample to DEV if any code is tuned |
| B-005 | `OPEN` | First Extraction Bitbucket handoff destination is unspecified | Keep the branch local; obtain the exact destination URL and agreed branch name before adding a second remote or pushing |

No extraction code defect was inferred from the environment-only test failures. No historical producer experiment output was overwritten.
