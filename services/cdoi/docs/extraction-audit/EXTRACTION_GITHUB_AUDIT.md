# Doc-Extraction GitHub Audit

Audit date: 2026-10-07. Repository cloned to `/home/anh-khoa/doc-extraction`; the KP/CDOI checkout was not replaced.

## Repository and refs

| Ref | Commit | Commit date (UTC) | Finding |
|---|---|---|---|
| GitHub `origin/master` | `d08abb12aea43a0450e2b8c88ea26fb762431f72` | 2026-09-02 | Older production baseline |
| GitHub `origin/fix/table-text-ownership` | `e6835cd1529a87823680e2d698fe0251e286538e` | 2026-10-02 | Newer production/research history; selected local base |

The clone exposed two remote branches, `origin/master` and `origin/fix/table-text-ownership`; no tags were present. The latter has 85 commits beyond `origin/master`, with the master commit as its merge base and no divergence (`0` commits ahead on the master side, `85` on the selected branch side). It contains substantially newer production code, tests, resource/security hardening, and explicit public-boundary documentation. It also retains a large historical research archive, which is not part of the production import path.

Only GitHub `origin` exists in the clone. A search of tracked files, `.git/config`, and reachable history did not discover a Bitbucket URL. `BITBUCKET_REMOTE_NOT_DISCOVERED`; the KP repository's Bitbucket remote was not reused or inferred as an extraction URL. No Bitbucket fetch was attempted.

## Contract and implementation

The producer's internal canonical representation is `Document`, serialized with internal schema version `1.4.0` at the selected commit. The public API is `doc_extraction.cli.process_file(...)` or the CLI; output includes a `Document` JSON, metadata, warnings/errors, pages, elements, tables/cells, and physical source information.

There is no implemented or authoritative `ExtractionPackage v1` schema, validator, canonical example, adapter, or KP consumer entry point in this checkout. The current branch's `docs/extractionpackage-v1-integration.md` explicitly records the contract-authority blocker. Internal `Document.schema_version=1.4.0` is not evidence of ExtractionPackage v1 compatibility.

## Supported inputs and paths

The source documents PDF, DOCX, XLSX, PPTX, and raster images. CPU-capable native paths include PyMuPDF PDF text/table parsing and native Office parsers. CPU visual/OCR paths are optional: Docling/EasyOCR require a separate install and roughly 1.5 GB of model artifacts according to the README; the default core install does not include them. Table Transformer and other model backends are optional and are not needed for native digital-PDF extraction. CUDA configuration exists but is not required.

The production boundary is physical extraction. The README and canonical IR attach no ontology/entity/relation semantics. Tests cover schema serialization/version, routing, native parsing, office parsing, tables, reading order, resource limits, and security. The repository's documented full test command is `.venv/bin/python -m pytest -q` after setup; environment-specific failures from this machine are listed in `docs/alignment/LOCAL_EVALUATION_RESULTS.md`.

The producer's core dependency set includes PyMuPDF, whose project documentation identifies the AGPL-3.0/commercial dual license. This local qualification is not a redistribution decision; any closed-product packaging needs a separate license-compliance review.

## Decision

The local integration branch is based on `origin/fix/table-text-ownership`, not `master`, because it is a direct descendant and includes the newest relevant implementation and tests. The public contract remains blocked pending owner-supplied authority. No merge to `master`, push, history rewrite, or producer-internal import into KP was performed.

## Later integration update

The user clarified that GitHub is the only existing Extraction repository and there is no Extraction Bitbucket upstream. The live-verified KP feature branch at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3` supplies the existing `DocumentExtractionContract` 1.0.0 authority candidate. A producer-side JSON projection now exists on isolated branch `local/kp-extraction-contract-v1`; its real PDF outputs were accepted by KP and converted to `DocumentIR v2`. See `docs/extraction-kp-contract/EXTRACTION_TO_KP_MAPPING_V1.md` and `LIVE_EXTRACTION_KP_INTEROP_REPORT.md` for remaining losses and gate status.
