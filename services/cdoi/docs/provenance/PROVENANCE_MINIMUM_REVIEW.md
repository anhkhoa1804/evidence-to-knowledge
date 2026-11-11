# Provenance minimum review

Historical pre-1.1 review. Its object-provenance blocker was resolved by the additive contract and KP adapter in the V3/V2 integration. The current minimum is in [`docs/provenance/PUBLIC_PROVENANCE_PROFILE_V1.md`](PUBLIC_PROVENANCE_PROFILE_V1.md), with measured results in [`docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md`](OBJECT_PROVENANCE_TEST_RESULTS.md).

| Field | KP consumer evidence | Classification for current boundary | Gate effect |
|---|---|---|---|
| Source file hash, filename, document ID | `DocumentSource` and `EvidenceRef` use source identity/hash; returned in `DocumentIR` | `PUBLIC_CONTRACT_MINIMUM` | Preserved; pass |
| Extraction run ID and producer/version/time | KP has run provenance and contract provenance; run identity is required by package | `PUBLIC_CONTRACT_MINIMUM` | Preserved in local `DocumentIR`; pass |
| Element/table/cell ID and page/row/column | `DocumentEvidence` points to element/table/cell coordinates; KP onboarding and evidence use these locators | `PUBLIC_CONTRACT_MINIMUM` | Preserved in local `DocumentIR`; pass |
| Cell header flag | KP semantic processing treats row 0 as header and does not consult producer `is_header`. | `PRIVATE / DEFERRED` for current KP flow | Non-row-0 and multi-level header semantics remain unestablished; not a current gate blocker |
| Coordinate origin | KP stores bbox and unit but current semantic/evidence path does not read bbox for matching or citation. | `PRIVATE / DEFERRED` for current KP flow | Bbox-level spatial reconstruction is unsupported; not a current gate blocker |
| Per-object backend | Package 1.1 has accepted object refs; KP resolves those refs to operation/backend and keeps run backend separate. | `PUBLIC_CONTRACT_MINIMUM; IMPLEMENTED` | Real table PDF now reports text as `pymupdf-native` and table/cell as `pymupdf_tables` in evidence metadata |
| Transformation chain | It is an explicit field in package `ExtractionProvenance`; KP IR now retains it in run provenance. | `PUBLIC_CONTRACT_MINIMUM` when supplied | Preserved after the latest adapter change; pass |
| Warning/error/failed status | KP contract has WARNING/ERROR/FATAL; KP adapter rejects FATAL. Producer hard failure raises and produces no successful `Document`. | Technical failure is separate from semantic `UNRESOLVED`; partial/nonfatal error policy remains open | Fatal consumer control passes; owner decision only for partial/nonfatal behavior |

## Recommendation

For the measured CPU PDF onboarding path, source identity, run lineage, physical locators and fatal technical-failure separation are preserved. Coordinate origin and header markers remain deferred under the frozen decisions above. Object provenance is now public in ExtractionPackage 1.1 and survives into KP evidence.

The simple PDF and 3×3 table round-trips pass for the measured cases. The gate does not claim every Extraction internal field belongs in the public contract, nor does it qualify other formats or backend combinations.
