# Historical: Extraction 1.4.0 → KP contract 1.0.0 mapping

This V1.0.0 field map is retained as historical evidence and is superseded by [`docs/provenance/OBJECT_PROVENANCE_MAPPING.md`](../provenance/OBJECT_PROVENANCE_MAPPING.md), which maps the implemented ExtractionPackage 1.1.0 boundary. Source was GitHub `fix/table-text-ownership` at `011b2a4cd01f3f6f4d96780f7288b239cd80789a`, with the V2 projection at `60713327704b4c90b16ee0689875b5a431f3969b` and KP V1 consumer at `78117e66d0e076f7270eaceb286a31bc8911b729`.

| KP package field | Latest producer source / transform | Classification | Result / limit |
|---|---|---|---|
| `contract_name`, `contract_version` | Fixed literals `DocumentExtractionContract`, `1.0.0` | `DIRECT` | Deliberately separate from internal `Document.schema_version=1.4.0` |
| `extraction_run_id` | Caller-supplied argument to projection | `OWNER_DECISION_REQUIRED` | Deterministic for a fixed caller value; production owner and uniqueness lifecycle are not defined by producer |
| `source_document_id` | `Document.document_id` | `DIRECT` | Matches KP identity on both same-source comparisons; producer derives this from filename/hash key, not an independent acquisition ID |
| `source_name` | `RunMetadata.input_filename` | `DIRECT` | Both real PDFs preserved |
| `source_mime_type` | `file_type == pdf` → `application/pdf` | `DERIVED_DETERMINISTIC` | PDF only; other formats fail closed |
| `source_hash` | `RunMetadata.file_hash_sha256` over original input bytes | `DIRECT` | Both hashes match the exact source files |
| `source_size_bytes` | Not present in canonical Document | `UNSUPPORTED` | Optional in KP v1; omitted |
| `extraction_backend` and provenance backend | `RunMetadata.backend` | `DIRECT` | `baseline`; correctly identifies the run path at current contract granularity |
| backend version | `model_versions.get(metadata.backend)` | `DIRECT` | Null for these baseline runs because no `baseline` key exists; null is accepted |
| `extracted_at` | `RunMetadata.timestamp` | `DIRECT` | Preserved |
| language hints | No first-class canonical source | `UNSUPPORTED` | Empty tuple in package |
| `document_metadata` | Empty allowlisted object | `UNSUPPORTED` | No undocumented internal config is copied |
| sections | One section per producer page; page index/number and IDs copied | `DERIVED_DETERMINISTIC` | PDF page section semantics only |
| element ID/type/text/table ID/page | Corresponding `Element` fields | `DIRECT` | Text, IDs and page locators survive both real round-trips |
| element reading order | Explicit per-page order flattened by page sequence | `DERIVED_DETERMINISTIC` | Complete order required; local exporter now rejects incomplete order instead of inventing one |
| bbox and unit | Producer bbox plus owning page unit | `DIRECT` | Coordinates/unit survive; `coordinate_origin` has no KP v1 field |
| `parent_element_id`, confidence | Producer parent/confidence | `DIRECT` to package | Projection emits both. KP's current `DocumentElement` adapter does not retain `parent_element_id`; confidence survives. Parent retention is not needed by the tested onboarding path. |
| table ID, dimensions, cell row/column/spans/text | Corresponding `Table` / `Cell` values | `DIRECT` | 3×3, nine cells, text and structural coordinates survive |
| cell ID | No producer cell ID; composed as `<table_id>:r<row>:c<column>` | `DERIVED_DETERMINISTIC` | KP validates uniqueness and preserves IDs; row/column identity is stable within table |
| `is_header` | Producer `Cell.is_header` | `PRIVATE_EXTRACTION_METADATA` for current KP v1 consumer | Not represented in contract; current KP semantic path treats row 0 as header and does not read `is_header` |
| element/table source backend | Producer per-object `source_backend`; package only has run-level backend | `PUBLIC_CONTRACT_GAP` | The real heterogeneous run shows the loss reaches KP `Why` provenance as `source_backend=baseline` for objects produced by different components. A provenance reference is required; do not encode it as an unversioned string. |
| source IDs / internal `extra` | Producer-only fields | `PRIVATE_EXTRACTION_ONLY` for tested PDF path | Reported by projection losses; not needed to resolve current text/cell evidence |
| warnings | Warning strings → `ContractIssue(WARNING, PRODUCER_WARNING)` | `DERIVED_DETERMINISTIC` | Both real PDFs emitted `text_quality: insufficient_text`; KP retains the detail in `DocumentIR.run_provenance.warnings`. The generic code remains a broader taxonomy limitation. |
| producer errors / partial | Producer errors are rejected; failed Documents cannot be published | `UNSUPPORTED` | No successful empty package is produced; partial/error mapping is not qualified |
| transformation chain | `doc-extraction-document/1.4.0` | `DIRECT` | Survives in KP `DocumentIR v2` at pinned integration HEAD |
| local source path / route | Deliberately not exported / no public v1 counterpart | `PRIVATE_EXTRACTION_ONLY` | No current KP source citation requires local path or route |

At the time of this V1.0.0 measurement, object-to-provenance attribution was the remaining gap. It was addressed by ExtractionPackage 1.1.0; see the current interop report and provenance design. Coordinate origin and header flags remain deferred for current KP behavior. This qualification did not claim general multi-format or partial-document support.
