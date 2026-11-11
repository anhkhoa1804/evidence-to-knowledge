# Historical pre-1.1 minimum provenance trace audit

This records the V1.0 loss that led to the object-reference extension. It is
superseded for current status by `docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md` and the
V3/V2 interop report; its `NOT PASS` conclusion applies to the old package
boundary only.

All consumer checks below use pinned KP integration HEAD `78117e66d0e076f7270eaceb286a31bc8911b729`, not current Bitbucket HEAD. Both producer files are the same source bytes as the V1 qualification; V2 package artifacts and hashes are in `integration_artifacts/extraction_v2/`.

| Trace value | `qualification.pdf` | `table-qualification.pdf` | Result at KP boundary |
|---|---|---|---|
| Original source identity/hash | ID `qualification-b6617020`; SHA-256 `b6617020237f962ef796e17d9b201c08830df3ff4ca15a46ee6da9d1ef6fa265` | ID `table-qualification-4c712d79`; SHA-256 `4c712d79fac1a4b96998d50083d78b7606eaa3d7c5a74db8bda9277a53afaa2e` | Both preserved in `DocumentIR`; table-case `EvidenceRef` also retained ID/hash |
| Run identity | `v2-simple-20261007` | `v2-table-20261007` | Preserved in `DocumentIR.run_provenance` and evidence refs |
| Run-level producer/backend | `doc-extraction` projection; `baseline` | Same | Preserved as run-level value; no full config snapshot is sent |
| Element identity/text | `p0-e0`; native text | `p0-e0` native paragraph and `p0-etbl0` table anchor | IDs/text survive; page 1 survives |
| Table/cell identity | None | Table `p0-t0`; cells `p0-t0:r0:c0` … `r2:c2`; row/column 0–2 | Table, 3×3 dimensions, all nine texts, cell IDs and locators survive |
| Transformation chain | `doc-extraction-document/1.4.0` | Same | Preserved in `DocumentIR v2`; this is schema lineage, not per-stage attribution |
| Warning | `text_quality: insufficient_text` | `text_quality: insufficient_text` | Package issue has `WARNING`; KP retains detail in `run_provenance.warnings` |
| Errors | Empty | Empty | No producer error was emitted; separate KP fatal-issue test rejects as `EXTRACTION_PACKAGE_FAILED` |
| Object backend | Producer simple text: `pymupdf-native` | Text: `pymupdf-native`; table/cell evidence: `pymupdf_tables` | KP assigns `baseline` to every object; exact producer attribution is lost |
| Header | No table | First table row marked header in producer | KP cell `is_header` is `None`; current semantic consumer uses row 0 directly |
| Coordinate origin | Producer top-left | Producer top-left | Not in package/KP bbox model; current KP evidence path uses page/cell locators, not bbox geometry |

## Exact evidence trace for table cell `Item`

Producer source object:

```text
source SHA-256: 4c712d79fac1a4b96998d50083d78b7606eaa3d7c5a74db8bda9277a53afaa2e
run ID:         v2-table-20261007
run backend:    baseline
element:        p0-etbl0 (table anchor), page 1, producer backend pymupdf_tables
table:          p0-t0, 3×3, producer backend pymupdf_tables
cell:           p0-t0:r0:c0, row 0, column 0, text "Item"
```

KP's package-to-IR conversion preserves the source hash, run ID, table/cell identity and page/row/column. It sets the table anchor and table's `source_backend` to `baseline`. The actual KP evidence object therefore serializes:

```text
DocumentEvidence.extractor_backend = baseline
DocumentEvidence.source_backend   = baseline
SourceReference.source_path       = table-qualification.pdf
SourceReference.source_span       = element p0-etbl0
SourceReference.metadata          = source hash identity + page/table/cell coordinates + both backend fields
EvidenceRef.location              = page 1 / element p0-etbl0 / table p0-t0 / row 0 / column 0
EvidenceRef.provenance.backend    = baseline
```

The current `Why` path returns the approved fact's evidence objects as answer provenance. The source citation remains resolvable, but its object-level backend attribution would say `baseline`, not `pymupdf_tables`. This is the measured public gap. The package has no config snapshot or per-object provenance reference from which KP could recover the missing attribution.

## Gate field audit

The following required profile values pass on both cases: source identity/hash, run ID, producer/run identity, element identity/text, page locator, transformation chain, warning detail, and technical-error separation. Table identity, cell ID/text, row/column and table shape pass on the table case. Exact per-object provenance attribution fails on the table case. Header and bbox origin are explicitly deferred for current KP v1 semantics and are not gate failures.

Conclusion: `LIVE_EXTRACTION_KP_INTEROP_V1 = NOT PASS` until a versioned object-to-provenance reference is supported end to end, or the owners explicitly revise the evidence meaning so KP does not claim object-level backend attribution. No `LIVE_INTEROP_V1_FREEZE.json` was created.
