# LIVE_EXTRACTION_KP_INTEROP_V1

**Status: `PASS` for the declared CPU PDF scope.** ExtractionPackage 1.1.0 carries accepted object-to-provenance refs; KP preserves and resolves them into DocumentIR and evidence/Why metadata. The run backend remains separate from object backend attribution.

## Pinned source and consumer

| Side | Branch / role | Exact SHA |
|---|---|---|
| Extraction upstream | GitHub `fix/table-text-ownership` | `011b2a4cd01f3f6f4d96780f7288b239cd80789a` |
| Extraction integration | `local/kp-extraction-contract-v3` | `54c27c86f5d2ba8b8c65c59c0654e4af48a28932` |
| KP live contract base | Bitbucket `feature/agent-cdoi-capability-v0.1.0` | `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3` |
| KP integration code tested | `local/extraction-contract-consumer-v2` | `5ef7507c2466ee36287bb4f304886d161daa575a` |
| KP integration branch tip | same branch, evidence-freeze-only follow-up | `0178b1a271b875efa17e113a819c1916475c2702` |

The authenticated Bitbucket `git ls-remote` verification and live contract-base SHA are confirmed in the task starting state. A separate read-only refresh attempt during this session could not connect to the configured network proxy before receiving a server response; it produced no Bitbucket HTTP or authentication status. This does not replace the confirmed live-ref evidence. KP tests were run against the pinned local integration commit, a descendant of the verified contract base.

## Provenance decisions

- `provenance.transformation_chain` is retained as schema lineage (`doc-extraction-document/1.4.0`). It is not suitable for object refs because it has no operation/backend identity, parent graph, or output binding.
- ExtractionPackage 1.1.0 adds `provenance_steps[]` (`step_id`, `operation`, `backend.name`, optional `backend.version`, `parent_refs`) and `provenance_refs[]` on elements/tables. Table cells inherit table refs when omitted/null; explicit empty refs mean unknown.
- KP enforces unique step IDs, referential integrity, acyclicity, and no unused steps. It retains steps in `DocumentIR.run_provenance` and refs on evidence objects. `run_backend` is distinct from `source_backend`; multiple backend refs remain a list and do not collapse to one scalar.
- Legacy ExtractionPackage 1.0.0 remains accepted. KP does not claim its run backend as an object's backend. The strict 1.0 serializer omits 1.1-only fields; a 1.0 reader cannot accept a 1.1 payload and must fail closed.
- Header semantics and coordinate origin remain `PRIVATE / DEFERRED`; current KP uses row 0 for headers and page/table/cell locators for evidence.

## Real local round trips

Both sources were re-extracted by the real CPU producer at integration V3, projected by its V1.1 function, parsed by KP's contract model, adapted to `DocumentIR v2`, and sent through the onboarding preview.

| Case | Source SHA-256 | Provenance result | Structure / result |
|---|---|---|---|
| Simple PDF | `b6617020237f962ef796e17d9b201c08830df3ff4ca15a46ee6da9d1ef6fa265` | `p0-e0 → pymupdf-native`; run `baseline` | Source/hash/run/ID/text/page/schema lineage/warning preserved; PASS |
| Table PDF | `4c712d79fac1a4b96998d50083d78b7606eaa3d7c5a74db8bda9277a53afaa2e` | Text → `pymupdf-native`; table and 9 cells → `pymupdf_tables`; run `baseline` | 3×3, nine cells, IDs, text, row/column/page, hash/run/lineage/warning preserved; PASS |

The table evidence was passed through KP's shared `document_evidence_for()` and evidence formatter. The emitted Why evidence metadata includes source filename/hash, page 1, table and cell identity, `run_backend=baseline`, `source_backend=pymupdf_tables`, and the resolved `detect_table` step. The fixture's labels do not trigger semantic candidates, so a document-derived approved fact and full user-facing Ask/Why answer were not measured.

Package hashes and source mapping are recorded in [`integration_artifacts/extraction_v3/MANIFEST.json`](integration_artifacts/extraction_v3/MANIFEST.json); fresh post-final-code round-trip hashes are in [`integration_artifacts/extraction_v3/LIVE_INTEROP_V1_FREEZE.json`](integration_artifacts/extraction_v3/LIVE_INTEROP_V1_FREEZE.json). The details are in [`OBJECT_PROVENANCE_TEST_RESULTS.md`](docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md).

## Verification and limits

```text
Extraction focused tests: 80 passed
KP focused tests:         80 passed
Contract:                 DocumentExtractionContract 1.1.0
Evidence refs:             evidence_ref_v1 unchanged; refs remain in DocumentIR and Ask/Why metadata
```

Synthetic controls verify multiple refs on one object, unknown backend version handling, legacy 1.0 ingestion, exact-version rejection, and fail-closed dangling/parent/cycle cases. Multi-ref support is not claimed as a naturally measured PDF output. No OCR/VLM/GPU path, other document format, or external benchmark was run. SemTab remains `UNUSED` with its 30 IDs unchanged and gold unopened.

The gate is measured on Extraction integration `54c27c8…` and KP integration code `5ef7507…`; the KP branch tip `0178b1a…` only adds the evidence manifest after test execution. It does not claim all document formats, backend combinations, or current Bitbucket reachability from this execution environment.
