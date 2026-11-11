# Doc-Extraction → KP ExtractionPackage 1.0.0 mapping

This mapping uses the real producer `Document` at Extraction commit `e6835cd1529a87823680e2d698fe0251e286538e` and the KP transport models at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`. The producer projection lives at `src/doc_extraction/integrations/kp_contract_v1.py` in the isolated Extraction worktree. It emits JSON-shaped data only; KP remains the owner of contract validation and conversion to `DocumentIR v2`.

| KP field | Extraction source | Transform | Lossless? | Decision |
|---|---|---|---|---|
| `contract_name` | KP contract constant | `DocumentExtractionContract` | Yes | `KP_REQUIRED` |
| `contract_version` | KP contract constant | `1.0.0` | Yes | `KP_REQUIRED`; never copy producer `Document.schema_version` |
| `extraction_run_id` | Caller | Required explicit input | Yes | `KP_REQUIRED`; caller owns run identity |
| `source_document_id` | `Document.document_id` | Direct | Yes | `DIRECT` |
| `source_name` | `metadata.input_filename` | Direct; local path is not exposed | Yes | `DIRECT` |
| `source_mime_type` | `metadata.file_type` | Explicit PDF map: `pdf` → `application/pdf` | Yes for qualified PDF | `DERIVED_DETERMINISTIC`; other formats rejected for now |
| `source_hash` | `metadata.file_hash_sha256` | Direct; producer computes SHA-256 over original input bytes | Yes | `DIRECT` |
| `source_size_bytes` | Not in serialized `Document` | Omitted | No | Unsupported by producer boundary |
| `extraction_backend` | `metadata.backend` | Direct run-level configured backend (`baseline` in qualification) | Only at run level | `DIRECT`; does not identify mixed per-element backends |
| `extraction_backend_version` | `metadata.model_versions` | Lookup by exact `metadata.backend` key | Currently `null` for `baseline` | `UNSUPPORTED`; no guessing from unrelated package versions |
| `extracted_at` | `metadata.timestamp` | Direct | Yes | `DIRECT` |
| `language_hints` | No producer field | Empty tuple | No | Unsupported |
| `document_metadata` | No selected producer field | Empty object | No | `DEFAULTED`; no title inference |
| `sections[].section_id` | `Page.index` | `page-{1-based position}` | Deterministic | `DERIVED_DETERMINISTIC` |
| `sections[].section_type` | Qualified PDF page | Constant `page` | Yes for PDF | `DIRECT` within PDF-only support |
| `sections[].index` | `Page.index` / list order | Direct | Yes | `DIRECT` |
| `sections[].page` | Page list position | `index + 1` | Yes for rendered PDF pages | `DERIVED_DETERMINISTIC` |
| `sections[].element_ids`, `table_ids` | Page contents | Direct IDs | Yes | `DIRECT` |
| `elements[].element_id`, `element_type`, `raw_text`, `table_id`, `parent_element_id`, `confidence` | `Element.id/type/text/table_id/parent_id/confidence` | Direct; enum type serialized as its value | Yes | `DIRECT` |
| `elements[].page` | `Element.page_number` | Direct; null remains null | Yes | `DIRECT`; no fabricated page number |
| `elements[].bounding_box` | `Element.bbox`, owning `Page.coordinate_unit` | Copy coordinates and unit | Coordinates/unit survive; origin does not | `DIRECT` + `OWNER_DECISION_REQUIRED` for origin semantics |
| `elements[].reading_order` | `Page.reading_order` | Flatten page order lists into a document-wide zero-based rank | Ordering survives | `DERIVED_DETERMINISTIC` |
| `elements[].normalized_text`, `source_span`, `span_start`, `span_end` | No corresponding producer fields | Omitted | No | Unsupported |
| `elements[].sheet`, `slide` | Not relevant to PDF | Omitted | N/A | Other-format mapping not qualified |
| `elements[].metadata` | Producer has `source_id` and arbitrary `extra`, but KP gives no key semantics | Empty object | No | Do not smuggle undocumented keys; source/backend details are losses |
| `tables[].table_id`, `page`, `bounding_box`, `rows`, `columns`, `confidence` | `Table.id/page_number/bbox/n_rows/n_cols/confidence` | Direct plus bbox unit | Yes for represented fields | `DIRECT`; coordinate origin remains unrepresented |
| `tables[].cells[].cell_id` | Producer has no cell ID | `{table_id}:r{row}:c{column}`; format matches KP's published example | Deterministic | `DERIVED_DETERMINISTIC` |
| `cells[].row`, `column`, `raw_text`, `row_span`, `column_span`, `confidence` | `Cell.row/col/text/row_span/col_span/confidence` | Direct (`col` → `column`) | Yes | `DIRECT` |
| `cells[].page`, `bounding_box` | Owning table/page and `Cell.bbox` | Table page direct; bbox coordinates/unit copied | Yes for represented fields | `DIRECT`; coordinate origin remains unrepresented |
| `cells[].normalized_text`, `source_span`, `span_start`, `span_end` | No corresponding producer fields | Omitted | No | Unsupported |
| `cells[].is_header` | Producer has `Cell.is_header`; KP contract has no field | Not serialized | No | `LOSS_AT_CONTRACT_BOUNDARY`; owner decision required before claiming header preservation |
| `warnings[]` | `metadata.warnings` | Each string → `PRODUCER_WARNING`, severity `WARNING`, same detail | Detail survives | Severity/code are deterministic projection policy; owner should confirm |
| `errors[]` / partial status | `metadata.errors/status` | Projection rejects producer errors and failed status; contract has no explicit run status | No package for failure | `OWNER_DECISION_REQUIRED` for nonfatal error and partial-result policy |
| `provenance.producer` | Producer identity | `doc-extraction` | Yes | `DIRECT` identity constant |
| `provenance.producer_version` | Extraction package metadata | `0.1.0` | Yes | `DIRECT` |
| `provenance.extraction_backend`, `extracted_at` | Run metadata | Direct | Yes at run level | `DIRECT` |
| `provenance.transformation_chain` | Producer schema lineage | `doc-extraction-document/1.4.0` | Yes through `DocumentIR.run_provenance.transformation_chain` | `DERIVED_DETERMINISTIC` |
| Per-element/table backend, route, route reason | `Element.source_backend`, `Table.source_backend`, `Page.source_*`, run metadata | Contract v1 only has one package-level backend | No | `LOSS_AT_CONTRACT_BOUNDARY`; owner decision required for a versioned representation |

Counting the 38 mapping rows above as grouped paths (each row may contain multiple sibling fields), 17 groups map producer-native data directly, 7 are deterministic projections, 2 are KP-owned contract constants, and 1 is caller-required (`extraction_run_id`). Eight groups are absent/unsupported or intentionally empty. Six policy choices remain open: run-ID lifecycle, run-level versus per-object backend provenance, coordinate-origin semantics, header representation, nonfatal error/partial status, and generic warning code/severity. The producer projection rejects non-PDF formats rather than inventing sheet/slide/document locator rules.

The KP adapter was extended only inside KP's own IR: `DocumentIR.run_provenance.extraction_run_id` and `transformation_chain` now retain package provenance, and `DocumentTableCell.cell_id` retains contract cell identity. The wire contract is unchanged. The adapter still cannot preserve header flags, per-object backend provenance, or bbox origin without a contract/consumer policy.
