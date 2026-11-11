# Producer object provenance mapping

Producer baseline: GitHub `011b2a4cd01f3f6f4d96780f7288b239cd80789a`, plus
the V3 projection changes based on Extraction V2 `60713327704b4c90b16ee0689875b5a431f3969b`.
Consumer baseline: live KP contract branch
`feature/agent-cdoi-capability-v0.1.0` at
`eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`, plus KP integration V2 changes
based on `78117e66d0e076f7270eaceb286a31bc8911b729`.

| Public object | Producer input | Projection | KP behavior | Evidence |
|---|---|---|---|---|
| Text/paragraph element | `Element.id`, `Element.source_backend`, `Element.type` | `extract_element` step; backend name direct; exact matching model version or null; element ref points to step | `DocumentIR.elements[].provenance_refs`; a single backend is exposed as object `source_backend` | Real simple PDF: `p0-e0 → pymupdf-native` |
| Table anchor | `Element.type=table`, `Element.source_backend`, table ID | `detect_table` step for the element anchor | Ref resolved separately from run-level backend | Real table PDF: `p0-etbl0 → pymupdf_tables` |
| Table | `Table.id`, `Table.source_backend` | `detect_table` step; table refs point to it | `DocumentIR.tables[].provenance_refs` | Real table PDF: `p0-t0 → pymupdf_tables` |
| Cell | `Table` provenance; canonical `Cell` has no separate backend | No duplicated cell ref; null/omitted v1.1 cell refs inherit table refs | KP resolves cell evidence to the owning table refs; explicit empty refs mean unknown | Real table PDF: all nine cells inherit `pymupdf_tables` |
| Run | `RunMetadata.backend`, model versions, timestamp, caller run ID | Existing package run-level fields unchanged | Stored in `DocumentIR.run_provenance`; surfaced as `run_backend`, never a substitute for object refs | Real PDFs: run `baseline`; object backends differ |
| Schema lineage | `Document.schema_version` | Existing `transformation_chain=[doc-extraction-document/1.4.0]` | Preserved separately from object provenance steps | Both real PDFs |

## Deterministic IDs and version values

Step IDs are `prov-` plus the first 16 hex characters of SHA-256 over
`operation + NUL + backend_name`. They are stable for a given operation/backend
and scoped to the package/run. A backend version is included only when the
producer metadata map has an exact key equal to the object backend. The
measured metadata has a `pymupdf` entry, not `pymupdf-native` or
`pymupdf_tables`, so the object step version is null; no version is guessed.

The current canonical `Document` has one backend value per element/table and
none per cell. The V1.1 projection can therefore report accepted object
backend attribution, but it cannot claim multi-stage fusion or explain hidden
reconciliation. The contract supports multiple refs; that capability has a
synthetic validator test only.
