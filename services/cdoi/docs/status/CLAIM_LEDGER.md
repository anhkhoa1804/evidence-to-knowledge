# Claim ledger

| Claim | Status | Evidence / limit |
|---|---|---|
| Latest Extraction upstream SHA | `MEASURED` | GitHub `fix/table-text-ownership` at `011b2a4cd01f3f6f4d96780f7288b239cd80789a` |
| Extraction integration V3 | `IMPLEMENTED` | `local/kp-extraction-contract-v3` at `54c27c86f5d2ba8b8c65c59c0654e4af48a28932`; adds deterministic ExtractionPackage 1.1 projection |
| KP live contract base | `MEASURED` | Authenticated live refs confirmed by task starting state; `feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3` |
| KP integration V2 (final tested code) | `IMPLEMENTED` | `local/extraction-contract-consumer-v2` at `5ef7507c2466ee36287bb4f304886d161daa575a`, based on pinned integration `78117e66d0e076f7270eaceb286a31bc8911b729` |
| Extraction focused tests | `TESTED` | 80 passed on integration V3 worktree; CPU-only parser/schema/table/projection set |
| KP focused tests | `TESTED` | 80 passed at `5ef7507c…`; EvidenceRef v1 remains unchanged; includes 1.0/1.1 packages, adapter/DocumentIR/onboarding/EvidenceRef/runtime tests |
| Simple PDF provenance | `MEASURED` | Source SHA `b6617020…fa265`; `p0-e0 → pymupdf-native`; run backend remains `baseline` |
| Table PDF provenance | `MEASURED` | Source SHA `4c712d79…afaa2e`; text → `pymupdf-native`; table and 9 cells → `pymupdf_tables`; 3×3 structure preserved |
| Transformation chain | `MEASURED` | `doc-extraction-document/1.4.0` preserved as schema lineage, separate from object steps |
| Multi-ref object | `MEASURED (synthetic)` | KP accepts two refs, preserves both, and leaves scalar object backend null |
| Legacy ExtractionPackage 1.0.0 | `TESTED` | New KP reader accepts it; object backend remains unavailable rather than inheriting run backend |
| Dangling/parent/cycle refs | `TESTED` | KP validator fails closed; exact version 1.2.0 and 1.0 with 1.1 fields also rejected |
| LIVE_EXTRACTION_KP_INTEROP_V1 | `PASS` | Two real CPU PDFs preserve required source identity, IDs, locators, table structure, run and object provenance, warnings; pinned commit pair in manifest |
| Bitbucket live contract base | `MEASURED` | User-confirmed authenticated live `git ls-remote`; exact contract branch SHA recorded above. This turn's optional refresh was blocked at the local network proxy before server response. |
| Extraction push to Bitbucket | `NOT PUSHED` | Supplied repository is KP/Agent; separate Extraction repository/monorepo policy unknown |
| SemTab qualification population | `UNUSED` | 30 frozen IDs unchanged; gold unopened; no predictions or scoring |
| External benchmark scores | `NOT MEASURED` | OmniDocBench/Kleister not scored; no GPU-heavy run |


## Alignment diagnostic continuation — 2026-10-07

| Claim | Status | Evidence / limit |
|---|---|---|
| V3.12 freeze reproducibility | `NOT REPRODUCIBLE IN THIS WORKSPACE` | Requested tag/commit absent locally; Bitbucket fetch and exact ls-remote returned HTTP 503. See `docs/alignment/ALIGNMENT_FREEZE_INVENTORY.md`. |
| Alignment D0–D7 | `NOT RUN` | D0 hard gate withheld because population, gold, evaluator, and hashes cannot be tied to the exact freeze. No matcher results inferred. |
| Diagnostic classification | `PARTIALLY_INTERPRETABLE` | Historical V2/V3 evidence exists but is not attributable to the requested V3.12 freeze. |
| Extraction ↔ KP interop | `PASS / FROZEN` | Prior two-real-PDF CPU result remains unchanged; this alignment task did not modify it. |
| SemTab | `UNUSED` | 30 frozen IDs unchanged; gold unopened; no predictions/scoring. |
