# Reassessment of the earlier local contract candidate

The earlier `docs/extraction-kp-contract/EXTRACTION_KP_CONTRACT_CANDIDATE_V1.md` was grounded in the GitHub-derived Extraction `Document` 1.4.0 and KP master, which had no consumer. The live-verified KP Bitbucket feature branch reveals an existing KP-owned `DocumentExtractionContract` 1.0.0, `ExtractionPackage`, strict JSON Schema, producer JSON compatibility adapter, `DocumentIR`, and ingestion/onboarding consumers. The old proposal is therefore **`SUPERSEDED_BY_DISCOVERED_TEAM_CONTRACT` as the primary path**. Preserve the old file unchanged as a historical proposal; do not delete or silently rewrite it.

## Field-by-field reassessment

| Earlier candidate field | Discovered KP contract / consumer | Reassessment |
|---|---|---|
| Contract name/version | `DocumentExtractionContract` / `1.0.0`; strict `extra="forbid"` | `SUPERSEDED_BY_EXISTING_FIELD` |
| Producer schema version | `producer_version` and provenance fields; separate legacy adapter schema allowlist | `SEMANTICS_CHANGED`; producer must implement the package or a reviewed compatibility path |
| Document ID/name/hash | `source_document_id`, `source_name`, `source_hash` | `SUPERSEDED_BY_EXISTING_FIELD`; package adapter requires non-null source hash even though contract model allows null |
| File type/MIME | `source_mime_type` | `RENAMED`; producer `file_type` values such as `pdf` need an agreed MIME mapping |
| Extraction run ID | Required `extraction_run_id` | `STILL_OPEN`; producer `RunMetadata` has no extraction-run ID. Do not silently substitute stable document ID or timestamp |
| Backend/version | Package `extraction_backend`, provenance producer/backend version; current adapter maps the top-level backend to every element/table | `SEMANTICS_CHANGED`; per-page/per-element multi-backend provenance is not carried by a dedicated wire field or preserved by the conversion |
| Page/sheet/slide locator | `ExtractionSection` and item fields have page/sheet/slide | `SUPERSEDED_BY_EXISTING_FIELD`, with semantic gap: producer page-list index / `is_rendered_page` distinction is not directly represented |
| BBox | `BoundingBox` with optional unit | `SUPERSEDED_BY_EXISTING_FIELD`; coordinate origin is not represented in the package type |
| Element IDs/text/type/order | `ExtractionElement.element_id`, `raw_text`, `element_type`, `reading_order` | `SUPERSEDED_BY_EXISTING_FIELD`; producer order list must be projected to numeric order |
| Source span | `source_span`, `span_start`, `span_end` | `STILL_OPEN`; producer `source_id` is not automatically a text span and has different semantics |
| Table ID/dimensions/cells | `ExtractionTable`, `ExtractionTableCell` | `SUPERSEDED_BY_EXISTING_FIELD`, but review gaps below remain |
| Cell ID | Required `cell_id` | `STILL OPEN`; producer has no cell ID. A deterministic `table_id + row + column` encoding is plausible, but public identity semantics require approval |
| Cell header flag | KP `DocumentTableCell` supports `is_header`, but wire `ExtractionTableCell` has no such field and adapter cannot preserve producer `Cell.is_header` | `SEMANTICS_CHANGED` / contract gap; resolve before claiming lossless table handoff |
| Normalized text | Wire model has `normalized_text`, consumer conversion uses only `raw_text` | `NO_LONGER_NEEDED` for current semantic adapter; normalization semantics and preservation remain unresolved if a consumer needs it |
| Extraction warnings/errors | `ContractIssue` with severity, code, source location; fatal issue aborts conversion | `SUPERSEDED_BY_EXISTING_FIELD`, but status/error policy is unresolved: no explicit package status/partial enum; nonfatal `ERROR` issues are copied into provenance and do not abort the current conversion |
| Source size | Optional `source_size_bytes` | `STILL OPEN`; absent from current producer result |
| Per-element/per-table source backend | Package has top-level backend; elements allow primitive metadata but table/cell have no backend field; current adapter stamps top-level backend onto all | `SEMANTICS_CHANGED`; extraction can mix backends, so provenance may be lossy |
| Reading order | `ExtractionElement.reading_order` | `SUPERSEDED_BY_EXISTING_FIELD`; contract allows null, while consumer falls back to array index |
| KP semantic fields | No semantic fields in extraction package | `NO_LONGER_NEEDED`; remain forbidden at producer boundary |

## Specific contract/consumer gaps found

1. Current GitHub-derived producer emits `Document.schema_version=1.4.0`. `DocExtractionBackend` accepts only `1.0.0`, `1.1.0`, and `1.2.0`, and rejects unsupported 1.x versions. The direct `ExtractionPackage` path is a KP DTO and conversion path, not evidence that the producer emits that package.
2. `ExtractionTableCell` has no `is_header`, while producer `Cell.is_header` exists and KP `DocumentTableCell` has a field for it. `extraction_package_to_document_ir()` cannot carry header state.
3. `ExtractionPackage` requires a cell ID but producer cells have only row/column. A stable derivation rule needs owner approval.
4. The package has only one top-level backend. The conversion assigns it as backend for every element/table. Producer metadata/page/elements can indicate mixed routes/backends; this can lose physical provenance.
5. `extraction_run_id` is required in the package but not present in producer `RunMetadata`. KP `DocumentIR.run_provenance` currently does not retain the package run ID either.
6. Contract bounding boxes can retain a unit, but the package model does not express producer coordinate origin. The current producer documents top-left origin; confirm whether that is fixed by contract or needs an explicit field.
7. `ExtractionPackage.source_hash` is optional in the Pydantic DTO, but KP conversion rejects a missing source hash (`EXTRACTION_SOURCE_HASH_REQUIRED_FOR_KP_ADAPTER`).
8. Package errors distinguish WARNING/ERROR/FATAL but have no explicit SUCCESS/PARTIAL/FAILED run status. Current conversion aborts only on FATAL; decide whether nonfatal `ERROR` can proceed to semantic preview.
9. The docs state null/unknown and multi-format locator rules, but the package/DocumentIR handoff does not directly preserve the producer’s `is_rendered_page` bit or all page container semantics. Confirm format-specific null/index meaning.
10. KP exposes a typed `preview_extraction_package(package: ExtractionPackage)` and typed `add_extraction_package(...)`; a dedicated serialized package file loader is not evident. Decide the public file/CLI boundary before live integration.

## Recommendation

Do not implement the earlier local candidate. Treat the KP contract as the discovered contract authority candidate and reconcile the gaps with the Extraction contract owner. The producer branch is still unselected pending Bitbucket source discovery. `LIVE_EXTRACTION_KP_INTEROP_V1` remains `NOT READY`.
