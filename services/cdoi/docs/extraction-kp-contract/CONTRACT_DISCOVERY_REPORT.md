# Extraction ↔ KP contract discovery

> Historical baseline report for KP `master` (`0d063821…`) and Extraction `e6835cd…`. A later authenticated Bitbucket-ref audit verified the KP-owned `DocumentExtractionContract` and consumer on `feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`. The earlier local candidate is superseded as the primary design; current implementation and conformance results are in `LIVE_EXTRACTION_KP_INTEROP_REPORT.md`.

> Historical status below predates discovery of the team contract and the ExtractionPackage 1.1 implementation. Do not use its `CONTRACT_PROPOSAL_READY_FOR_REVIEW` or `NOT PASS` as current gate status.

**Outcome: `CONTRACT_PROPOSAL_READY_FOR_REVIEW`.** This is a discovery result, not an approved contract or live interoperability claim. No producer or KP runtime code was changed. SemTab Round-1 remains sealed: 30 IDs frozen, gold unopened, predictions unrun, population `UNUSED`.

## Preserved checkout state

| Repository | HEAD / branch | Worktree at discovery | Notes |
|---|---|---|---|
| KP/CDOI `/home/anh-khoa/vdt-infra-knowledge-graph` | `0d06382142a16a24ca50e87ca088fcfac3301199` / `master` | `.gitignore` modified; prior-session audit/report files and `data/external_eval/` untracked | Preserved as found; no reset, clean, stash, or deletion |
| Extraction `/home/anh-khoa/doc-extraction` | `e6835cd1529a87823680e2d698fe0251e286538e` / `local/kp-extraction-integration-20261007` | untracked `qualification/` | Preserved as found; contains the prior synthetic CPU qualification inputs/results |

The selected Extraction branch remains 85 commits ahead of GitHub master with merge-base at `d08abb12…`, as recorded in `docs/extraction-audit/EXTRACTION_BRANCH_AUDIT.md`. Its own integration document still says that no authoritative ExtractionPackage v1 is present. The internal producer schema version is `1.4.0`; it is not a public KP contract.

## Producer boundary actually available

The nearest persisted boundary is `Document` (`src/doc_extraction/schemas/document.py`), serialized by `utils.serde.write_json()` to `outputs/<document_id>/final/document.json`. The Python extraction function returns that Pydantic object; CLI output writes its JSON form. This is the producer’s canonical internal representation, not a public ExtractionPackage. `Document.to_markdown()` is explicitly lossy.

The serialized object contains run metadata (input filename/path, SHA-256, file type, route/backend/model versions, timestamp, status, errors and warnings), page containers, elements, tables, and assets. Pages carry a zero-based container index, rendered-page flag, optional one-based physical page/slide/sheet number, coordinate convention, page-level route/backend, and element-ID reading order. Elements carry document-local IDs, physical element type/text/bbox/confidence/backend/source ID/order/table link. Tables carry ID, dimensions, page number, bbox/backend and cells with zero-based row/column, spans, text, header flag, optional bbox/confidence.

Format location semantics are intentionally heterogeneous: PDF has rendered pages; PPTX uses rendered slides; XLSX has logical sheets with one-based sheet number and sheet name in backend extras; DOCX has a logical body and no fabricated page number. A cross-format contract must preserve that distinction. Cell objects have no stable `cell_id`; table and element IDs are present. The table relationship is an element of type `table` pointing by `table_id` to a table on its page. Reading order is a list of element IDs.

The producer supports run statuses `success`, `success_with_warnings`, and `failed`; its docs state it does not emit a separate `partial` status. Failed extraction must therefore remain a technical failure and cannot be interpreted as an empty document or semantic `UNRESOLVED`. The producer documents that vertical merge spans are unavailable on its PyMuPDF table route. Existing table ownership logic and regression tests address geometric text-to-cell assignment, but do not prove semantic ownership perfect for arbitrary overlays or scans. A proposed contract must retain available structures and limitations, not claim stronger ownership.

## KP consumer actually present

`src/cdoi/preprocessing.py` returns `DocumentChunk(text, SourceReference)` for UTF-8 JSON leaves, Markdown paragraphs, or generic text paragraphs. This is a preview path. `ContinualIntegrationPipeline.ingest()` calls `StructuredExtractor`, which reads only JSON `concepts` records and emits semantic candidate entities from their explicit labels/definitions/type hints/relations. It does not consume the chunks as general document text; it assigns the first chunk’s reference to each extracted concept. PDFs, office documents, layout, tables, or images do not enter this semantic ingestion path.

KP’s existing evidence types are `Evidence(text, reference, confidence)` and `SourceReference(source_path, source_system, source_span, hierarchy, metadata)`. `Provenance` belongs to KP’s semantic processing and includes its own extraction ID/run ID/model metadata. The current code does not require a producer element ID, physical page locator, bbox, reading order, or table/cell structure because it has no document-package consumer. Those may be valuable candidate-package data, but are not existing KP requirements. `EvidenceReference` types found in operational/alignment modules are specialized records, not a generic document IR consumer.

No `DocumentIR` class or serialized ExtractionPackage consumer entry point was found in KP source. The exact missing interface is a KP-owned function/service that accepts a validated serialized package and creates a KP-owned physical-source/evidence representation usable by semantic candidate generation. Current `ingest(path, domain)` cannot fill that role: its input semantics are the explicit concept JSON envelope, and invoking it on extracted text would silently cross an unsupported semantic boundary.

## Field accounting

The field-level evidence and counts are in `docs/extraction-kp-contract/CONTRACT_FIELD_PROVENANCE.csv`. The CSV has 31 rows including three explicitly forbidden semantic fields. Excluding those forbidden examples, the candidate inventory has 28 fields: 21 producer-native (`P`), 2 required by an existing KP evidence model (`K`: evidence text and source path), 1 deterministic adapter derivation (`D`), and 4 proposal-only (`PROPOSED / OWNER_DECISION_REQUIRED`). `K` records a field required to construct existing KP evidence types, not proof of a live package consumer. KP source span has a default and no approved locator grammar; source system defaults to `fixture` and producer has no matching field, so neither is marked `K`. No field is marked invented-and-approved. In particular, no ontology class, entity identity, relation meaning, business domain, approval, or canonical KG field is proposed for the producer.

The only candidate deterministic derivation is a stable cell reference formed from a producer table ID and row/column when the KP owner decides that a cell reference is needed. The producer has no cell ID; whether this derived identifier becomes part of the public contract is an owner decision. A source locator string that combines format + producer locator is likewise not included as an approved field; format-specific locator semantics remain explicit in the candidate.

## Serialization feasibility and gate

Producer serialization can preserve the producer’s own physical fields: IDs, text, locations, table grids, reading order, backend/run metadata and status. This is a measured property of its internal JSON serialization and synthetic qualification, not a serialization into an approved ExtractionPackage. No actual producer-to-candidate projection or KP round-trip was run, because the package envelope/version policy and consumer semantics remain unresolved.

At the time of this historical report, the gate was `NOT PASS` and a local contract proposal was awaiting a KP consumer. That state was superseded by the discovered KP contract and the measured ExtractionPackage 1.1 implementation. The prior synthetic PDF results remain historical and are not the current producer-to-KP evidence.

## Parallel alignment diagnostics and sealed population

Existing repository records show prior historical OAEI Anatomy experiments, persisted ranking diagnostics, and a fixed-candidate pathway; they do not establish the user-defined D0–D7 ladder as completed. Dense ranking is explicitly `RUNTIME_BLOCKER`, and independent external validation is `DATA_MISSING`. This task did not run a new alignment matcher or score a new population. Gate-by-gate audit is in `docs/alignment/ALIGNMENT_D0_D7_STATUS.md`.

SemTab state remains `UNUSED`: 30 Round-1 IDs remain frozen; no selected case tables or gold labels were opened, no prediction was produced, and no scoring occurred.
