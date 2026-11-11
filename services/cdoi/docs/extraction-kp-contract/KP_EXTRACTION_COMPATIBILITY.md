# KP ↔ Doc-Extraction compatibility

**Current result: `LIVE_EXTRACTION_KP_INTEROP_V1 = PASS` on two local CPU PDF cases.** The KP base is the authenticated live-verified `feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`.

```text
real PDF → Extraction Document 1.4.0 → ExtractionPackage 1.1.0 projection
         → KP validator → existing adapter → DocumentIR v2
         → onboarding preview / evidence provenance formatter
```

The schema versions remain distinct: producer `Document` 1.4.0 is internal;
the public package contract is 1.1.0. The new KP reader continues to accept
legacy package 1.0.0 and does not claim its run backend as object provenance.
The V1.1 package preserves object-to-operation refs, with run backend
`baseline` separated from object backends `pymupdf-native` and
`pymupdf_tables`.

Header flags and coordinate origin remain private/deferred for current KP
behavior: KP uses row 0 for headers and page/table/cell locators for current
evidence. This qualification does not cover other formats, OCR, GPU models,
or every backend combination. Exact hashes, commit pins and test counts are
in `LIVE_EXTRACTION_KP_INTEROP_REPORT.md` and
`docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md`.
