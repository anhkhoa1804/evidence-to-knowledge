# Active blockers and limits

No blocker remains for `LIVE_EXTRACTION_KP_INTEROP_V1` on the qualified CPU PDF path. The remaining limits are:

1. `RUN_ID_LIFECYCLE_OWNER_DECISION`: integration uses caller-supplied IDs; production allocator and retry/uniqueness policy remain unspecified. This does not affect the measured local gate.
2. `PARTIAL_ERROR_POLICY_NOT_QUALIFIED`: warnings are preserved and fatal errors fail closed; producer partial/nonfatal error behavior is not qualified.
3. `EXTRACTION_BITBUCKET_TARGET_UNKNOWN`: the supplied Bitbucket repository is KP/Agent. Do not push standalone Extraction history there. No separate Extraction repository/clone URL or monorepo policy was supplied.
4. `OCR_LOCAL_RESOURCE_NOT_QUALIFIED`: local live round-trips used born-digital PDFs and CPU native text/table parsing. No OCR/VLM model or GPU path was run.
5. `ALIGNMENT_DIAGNOSTIC_LADDER_INCOMPLETE`: see `docs/alignment/ALIGNMENT_D0_D7_STATUS.md`; independent of this provenance gate.
6. `OFFICIAL_BENCHMARK_SCORING_NOT_RUN`: OmniDocBench/Kleister scoring remains unmeasured; no GPU-heavy experiment was run.
7. `PYMUPDF_LICENSE_REVIEW`: local research qualification does not settle redistribution or closed-product packaging rights for PyMuPDF.
8. `BITBUCKET_REFRESH_FROM_THIS_EXECUTION_ENVIRONMENT`: the user-confirmed authenticated `git ls-remote` previously verified live refs and contract base `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`. This turn's extra read-only refresh could not connect to the configured network proxy before a Bitbucket response; this does not invalidate the confirmed live-ref state or local pinned measurements.

Not blockers for this gate: producer `is_header` (KP uses row 0 and ignores it) and bbox coordinate origin (current Ask/Why uses page/table/cell locators, not bbox geometry). Bbox-level spatial reconstruction and non-row-0/multi-level header behavior remain unsupported.

SemTab: 30 frozen IDs unchanged, gold unopened, no predictions or scoring; population remains `UNUSED`.


## Alignment diagnostic continuation — 2026-10-07

`ALIGNMENT_FREEZE_NOT_AVAILABLE_LOCALLY`: exact tag `cdoi-v3.12-adl-v1-freeze-20261007` and commit `54cfa19eb87697d788bcedf7fa3be3794b427633` are missing from local refs/object storage. `git fetch origin --prune --tags` and exact `git ls-remote` returned HTTP 503. The exact population manifest and hash-bound gold/candidate/prediction artifacts are also unavailable. D0–D7 were not run; do not substitute another population. See `docs/alignment/ALIGNMENT_FREEZE_INVENTORY.md` and `docs/alignment/ALIGNMENT_DIAGNOSTIC_FINAL_REPORT.md`.

SemTab remains sealed and `UNUSED`. `LIVE_EXTRACTION_KP_INTEROP_V1 = PASS` remains frozen and unaffected.
