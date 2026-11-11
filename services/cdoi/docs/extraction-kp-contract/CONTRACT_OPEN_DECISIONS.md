# Contract decisions requiring owner approval

> This decision list belongs to the earlier locally derived candidate from the GitHub-derived Extraction / KP master audit. A KP-owned contract and consumer have since been discovered on the live-verified Bitbucket feature branch. Do not use this list to revise the KP contract; use `docs/extraction-kp-contract/CONTRACT_CANDIDATE_REASSESSMENT.md` for current gaps and owner decisions.

No producer/KP owner approval was available in this task. These decisions remain open; they prevent implementation of an authoritative contract and live adapter.

| ID | Decision | Evidence / choices to settle | Consequence while open |
|---|---|---|---|
| CD-01 | Public contract owner, canonical name and version | Producer has internal `Document` schema 1.4.0; no ExtractionPackage v1 artifact or authoritative schema | Candidate remains proposal only |
| CD-02 | Compatibility policy | Define major mismatch, newer minor producer, unknown fields, missing optional fields and null/omission behavior | Validator behavior cannot be finalized; future adapter must fail closed |
| CD-03 | KP consumer owner and entry point | KP has `DocumentChunk` preview and explicit JSON `StructuredExtractor`; no serialized package consumer or `DocumentIR` | No KP adapter/runtime round-trip |
| CD-04 | Cross-format locator shape | PDF page, PPTX slide, XLSX sheet, DOCX logical body; optional physical number may be null | Do not flatten to one integer or invent canonical locator strings |
| CD-05 | Stable cell reference | Producer `Cell` has row/column but no ID | Any `(table_id,row,col)` key remains derived and unapproved |
| CD-06 | Source-system identity and source hash scope | Producer has input path/name/hash; KP source system defaults to `fixture`; define path privacy and whether hash means raw bytes | No mapping from local producer path to a public source URI |
| CD-07 | Confidence meaning | Producer confidence exists where backend emits it; KP evidence confidence defaults to 1.0 but is not calibrated from extraction confidence | Do not equate physical/OCR confidence with semantic confidence |
| CD-08 | Technical failure/partial outcome envelope | Producer has success, success-with-warnings, failed; docs say no partial status | Confirm status mapping and whether partial becomes a future explicit status |
| CD-09 | Backend/config provenance exposure | Producer metadata includes route/backend/model versions/config; some values may contain environment-specific paths | Approve a stable, privacy-safe subset |
| CD-10 | Table ownership guarantee | Producer has geometric ownership logic and tests; backend limitations remain | Define consumer interpretation and unsupported/ambiguous ownership signals |
| CD-11 | Reading-order semantics | Producer carries element order IDs but fallback exists when reading_order is empty | Confirm whether empty means unknown and whether producer must always emit a complete order |
| CD-12 | KP semantic handoff | Current semantic ingestion consumes explicit concept JSON, not extracted text/tables | Define whether extraction feeds a new reviewed semantic proposal path; never infer semantics in producer |

Approval of CD-01 through CD-03 and the applicable field semantics is a prerequisite to implementation. This task intentionally stops before writing a candidate JSON Schema, validator, KP adapter, or fabricated fixture.
