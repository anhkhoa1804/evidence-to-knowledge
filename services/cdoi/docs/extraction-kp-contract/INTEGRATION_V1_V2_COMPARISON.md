# Extraction integration V1 versus V2

V1 producer source was `e6835cd1529a87823680e2d698fe0251e286538e`, with local projection commit `ffeab65a899dfa54ae14c6475d9d59a3b41c9d5d`. V2 source is latest fetched upstream `011b2a4cd01f3f6f4d96780f7288b239cd80789a`, plus local projection branch `60713327704b4c90b16ee0689875b5a431f3969b`. Both used the same two PDF input bytes. V1 package fixtures and V2 generated packages were validated by KP integration commit `78117e66d0e076f7270eaceb286a31bc8911b729`.

| Property | V1 / old producer package | V2 / latest producer package | After KP boundary |
|---|---|---|---|
| simple PDF text | Same one extracted paragraph | Same text | Same text in `DocumentIR` |
| source SHA-256 | `b6617020…fa265` | `b6617020…fa265` | Preserved |
| document/element IDs | `qualification-b6617020`, `p0-e0` | Same | Preserved |
| page locator | page 1 | page 1 | Preserved |
| run ID | V1 harness ID | V2 harness ID | Both caller-supplied, preserved |
| transformation chain | `doc-extraction-document/1.4.0` | Same | Preserved in `DocumentIR v2` |
| table source SHA-256 | `4c712d79…afaa2e` | `4c712d79…afaa2e` | Preserved |
| table ID and shape | `p0-t0`, 3×3, 9 cells | Same | Same |
| cell IDs / row-column | `<table>:r<row>:c<column>` | Same | Preserved and referentially valid |
| cell text | Same 9 texts | Same 9 texts | Preserved |
| producer header flags | Row 0 true, rows 1–2 false | Same | `None` for all cells; current KP consumer uses row 0 directly |
| producer per-object backend | `pymupdf-native` and `pymupdf_tables` | Same | `baseline` from run-level contract value on each IR object |
| coordinate origin | top-left in producer schema | top-left in producer schema | Not represented in KP bbox model; KP v1 stores values and unit |
| internal Document schema | 1.4.0 | 1.4.0 | Public package version remains 1.0.0 |

No behavioral regression was observed for the measured PDFs. The comparison does not prove parity across document classes or backends. Latest extraction adds stricter schema and table serialization checks and improved ownership handling; the V2 table run still yields the qualified 3×3 grid. Package hashes and the new run times are in [`integration_artifacts/extraction_v2/MANIFEST.json`](../../integration_artifacts/extraction_v2/MANIFEST.json). The pre-existing V1 fixtures remain unchanged as the comparison baseline.
