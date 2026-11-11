# KP consumer requirements discovered in current code

This records current implementation requirements, not a target architecture.

| Need | Why / current code | Classification for a future Extraction consumer |
|---|---|---|
| Evidence text | `Evidence.text` carries source wording into semantic candidate evidence. Current `StructuredExtractor` uses explicit JSON definition/label text. | KP evidence-model need (`K`); no extracted-document consumer today |
| Source path | `SourceReference.source_path` identifies the source path. | KP evidence-model field (`K`); package-to-consumer mapping absent |
| Source span | `SourceReference.source_span` supports a textual/source locator; JSON preprocessing uses JSON paths and text preprocessing uses paragraph labels. | Optional field with a default; mapping physical package locators to this string is an owner decision |
| Source system | `SourceReference.source_system` exists and defaults to `fixture`. | Optional field with a default; no approved mapping from producer backend/route |
| Hierarchy | `SourceReference.hierarchy` is an optional list used by Markdown preprocessing. | Optional; no current table/page consumer requirement |
| Metadata | `SourceReference.metadata` is an arbitrary dict. | Optional extension field; not suitable as an ungoverned substitute for typed physical fields |
| Evidence confidence | `Evidence.confidence` defaults to `1.0`; structured extractor does not derive calibrated confidence. | Optional in current KP model; do not copy producer confidence as semantic confidence without owner policy |
| Stable physical item ID | No current document consumer asks for one. | Candidate provenance value only; owner must decide if required |
| Page/sheet/slide locator | No current document consumer consumes one. | Candidate physical provenance only; preserve producer’s format-specific semantics |
| Table/cell structure | Current generic semantic ingestion does not parse extracted tables. | No current requirement; future consumer interface and table policy needed |
| Extraction status/errors | Current `ingest(path, domain)` has no producer extraction-result envelope. | Required boundary behavior to distinguish technical failure from semantic absence; contract owner must approve mapping |
| Ontology/entity/relation semantics | These are generated or governed by KP semantic pipeline/review/ontology code. | Forbidden in producer contract |

## Actual KP entry points and limitation

`cdoi preprocess PATH` produces `DocumentChunk` previews from UTF-8 JSON, Markdown or text. `ContinualIntegrationPipeline.ingest(path, domain)` invokes `StructuredExtractor`, which parses only an explicit JSON `concepts` list. It does not consume the `DocumentChunk` list as an unstructured document extraction interface. There is no PDF/DOCX/XLSX/PPTX/image consumer, no `DocumentIR`, and no adapter that accepts an ExtractionPackage.

Therefore the minimum KP-side interface still missing is a KP-owned package consumer that: (1) validates a serialized public package, (2) creates a physical evidence/document representation preserving source IDs and locations, (3) exposes content to semantic proposal generation without treating physical extraction as ontology semantics, and (4) propagates technical extraction failure separately from semantic abstention. This task deliberately does not invent this interface or claim that current `ingest()` is compatible.

`SourceReference`/`Evidence` offer useful existing evidence shapes, but their existence alone does not prove that they can represent producer pages/tables without loss or that downstream semantic code consumes them appropriately.
