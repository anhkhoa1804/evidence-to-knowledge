# Per-object provenance necessity experiment

Historical finding: P2 led to ExtractionPackage 1.1 and KP support. The prior
`PUBLIC_CONTRACT_GAP` is resolved for the measured CPU PDF cases; current
implementation and regression results are in `docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md`.

## Result

Outcome: **P2 — `PUBLIC_CONTRACT_GAP` for truthful KP evidence provenance.** The experiment used the existing real table PDF; no OCR model, GPU, external dataset, or new document was needed.

The run is heterogeneous. In the producer's canonical `Document` 1.4.0:

| Physical contribution | Producer identity | Producer `source_backend` |
|---|---|---|
| Native paragraph `p0-e0` | Page 1, text paragraph | `pymupdf-native` |
| Table element `p0-etbl0` / table `p0-t0` | Page 1, 3×3 table | `pymupdf_tables` |
| Cell `p0-t0:r0:c0` | Row 0, column 0, text `Item` | Inherits the owning table's physical extraction source; the canonical `Cell` itself has no backend field |

The public package reports run-level `extraction_backend=baseline`, an empty `document_metadata` object (no config snapshot), and `transformation_chain=["doc-extraction-document/1.4.0"]`. It does not contain the per-object backends or a reference from an evidence object to a producer operation. The chain identifies internal schema lineage, not which stage produced a given text/table object.

KP converts both elements and the table to `source_backend=baseline`. A real table-cell `DocumentEvidence` was then traced through the existing KP evidence formatter. Its `SourceReference.metadata` contains both `extractor_backend=baseline` and `source_backend=baseline`; `evidence_ref_from_document_evidence()` likewise emits `EvidenceRef.provenance.backend=baseline`. The onboarding code stores evidence on the reviewed fact, and the `Why` path returns that fact evidence as answer provenance. Therefore a Why result for this cell would expose the run-level label where the producer attributes the cited table to `pymupdf_tables`.

The same source and locators still identify the source evidence correctly. The loss affects the explanation of *how this physical object was produced*. Because KP currently exposes that value under `source_backend`, treating `baseline` as object-level provenance is misleading. A run-level backend/config plus IDs, locator and the current one-item schema chain cannot reconstruct the two distinct contributors from the contract alone.

## What is required

The public minimum needs an object-to-provenance reference that resolves to the operation/observation supporting an element, table, or cell. It must support multiple references for a fused object; a flat `element.backend` string would assume one producer per object and would not describe joined text/layout/table contributions. The reference should bind to the existing run ID and preserve the original source locator.

The latest Extraction source does contain an `ObservationLedger` in `src/doc_extraction/evaluation/evidence_integrity.py`. Its module documentation calls it a private, opt-in observation/evidence-integrity instrument that deliberately does not extend the public `Document` schema. It records backend observations, derivation references, and public-object references; the pipeline hooks are on the modular scanned-page route. The ledger is not attached to the canonical `Document` or emitted in `final/document.json` / the current ExtractionPackage projection, and the measured digital-PDF round-trip did not serialize it. Thus this is evidence that some internal lineage can be observed, not an existing public lineage contract. The canonical IR still has a backend string on elements/tables and no backend on cells. This task records the minimum requirement and blocker without promoting the research ledger, inventing public step IDs, changing strict v1, or implementing an unapproved extension.

## Scope and limits

The qualification PDF contains no OCR contribution; the experiment measures native text plus the CPU PyMuPDF table path. It proves heterogeneous object provenance within one successful run, not multi-backend fusion inside one cell. A future producer provenance model should allow many-to-many attribution even though the measured case can use one source step per object.

The qualification table (`Item`, `Qty`, `Price`) does not trigger KP's semantic cue vocabulary, so no document-derived approved fact or user-facing `Why` answer was created. The real `DocumentEvidence`/`EvidenceRef` serialization was traced, and current onboarding code was inspected: approved facts store their evidence and `ask("Why …")` returns it as provenance. This is enough to demonstrate the backend field reaches the explanation channel; it is not a claim that semantic extraction or review was qualified on this PDF.
