# MINIMUM_PUBLIC_PROVENANCE_V1

**Status: `PROFILE SATISFIED BY EXTRACTIONPACKAGE 1.1.0 FOR THE TWO MEASURED CPU PDF CASES`.** This profile covers source-backed KP consumption and truthful evidence explanation. It is a minimum, not a copy of the producer's internal Document or observation diagnostics.

| Field / meaning | Public v1? | Why / measured consumer need |
|---|---|---|
| Contract name and version | YES | KP must validate the exact wire contract and fail closed on unsupported versions. |
| `source_document_id`, `source_hash`, `source_name` | YES | Identify the source, bind evidence to original bytes, and show the cited source name. Both real PDFs retained the source ID/hash. |
| `extraction_run_id` | YES | Link evidence to one extraction execution; both real run IDs survived into `DocumentIR` and `EvidenceRef`. The production allocator/lifecycle remains a separate operational decision. |
| Producer identity/version | YES | Bind the run to an implementation revision for reproducible provenance. The extraction run ID remains the execution identity. |
| Run-level backend/version | RUN CONTEXT; NOT OBJECT ATTRIBUTION | Useful to describe the run, but omission does not prevent source citation or evidence identity when the run ID and object-to-provenance references are present. Never present it as each object’s backend. |
| Extraction timestamp | NO / OPTIONAL RUN METADATA | A timestamp alone does not establish run identity or enable evidence reconstruction; the stable run ID does that. |
| Transformation chain | YES | Preserve the declared derivation chain through `DocumentIR` and evidence. Current measured value is `doc-extraction-document/1.4.0`; it is schema lineage, not a detailed stage graph. |
| Element ID/type/text and reading order | YES | Support semantic processing and stable evidence identity. Reading order must be producer-declared; the V2 exporter rejects incomplete order rather than guessing. |
| Physical locator | YES | Page/sheet/slide/section as applicable; page was retained for both PDFs. For table evidence, include table ID, cell ID, row and column. |
| Table and cell identity/structure | YES when present | Preserve table ID, cell ID, row/column, spans and cell text; the real 3×3 case retained all nine cells. |
| Object-to-provenance attribution | **YES — provided by contract 1.1.0** | The measured package links text to `pymupdf-native` and table/cell evidence to `pymupdf_tables`; KP retains the refs and the resolved operation/backend list in evidence metadata. The run-level backend remains `baseline`. See `docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md`. |
| Warning/error state | YES | Preserve warning severity/detail where present; fatal extraction failure must remain a technical failure and never become an empty semantic document or `UNRESOLVED`. Measured warning detail survives; no error occurred in either real run. |
| Header flag (`is_header`) | NO / DEFERRED for current KP v1 | KP's current table semantic adapter uses row 0 and does not consume the producer flag. Limitation: non-row-0 and multi-level header semantics are not established. |
| Coordinate origin | NO / DEFERRED for current KP v1 | KP's audited Ask/Why evidence path uses page/table/cell locators and does not calculate with bbox geometry. Bbox-level spatial reconstruction is not supported by this contract profile. |
| Full producer configuration snapshot | NO for current Ask/Why | It is useful for internal diagnostics/replay but was not required to identify the source evidence or reconstruct its physical locator. The contract carries run ID and producer/run provenance; exact replay from contract alone is not claimed. |
| Local source path, logs, per-stage telemetry, model internals | NO | These remain private extraction diagnostics unless a downstream consumer demonstrates a source-evidence need. |

The public object attribution is represented as a reference to one or more accepted provenance steps, not a bare backend string. That handles single-backend objects measured today and permits multi-ref objects; the latter is contract-tested with a synthetic fixture only. The producer projection uses canonical per-element/table backends and does not expose the private ObservationLedger. `transformation_chain` remains schema lineage and is not reused as the operation graph.

The measured 1.1 packages meet the required profile on the simple and 3×3 table PDFs. This does not qualify OCR fusion, all formats, all backend combinations, or bbox-level reconstruction.
