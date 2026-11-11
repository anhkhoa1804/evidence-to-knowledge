# Latest Extraction upstream audit

## Source state

`origin/fix/table-text-ownership` fetched successfully on 2026-10-07 and resolves to `011b2a4cd01f3f6f4d96780f7288b239cd80789a` (`Finalize Phase 1 extraction improvements and experiments`). It is 24 commits ahead of the previously audited `e6835cd1529a87823680e2d698fe0251e286538e`, 0 behind, and 109 commits ahead of `origin/master` (`d08abb12…`). The previous local integration commit `ffeab65…` was not in this upstream history.

The latest upstream range changes 121 files (+50,752/-267), much of it benchmark output and optional GPU/model experiment infrastructure. Relevant changes include table text ownership, backend conformance, strict canonical document validation, serialization checks, warning propagation, and new contract adoption documentation. No GPU benchmark or model workload was run here.

## Contract and representation findings

The producer's internal `Document.schema_version` remains `1.4.0`. The latest branch adds validation and serialization safeguards around the existing representation; it does not add an ExtractionPackage exporter, JSON Schema, public package validator, or KP adapter. The new `docs/extractionpackage-v1-integration.md` and `docs/contract-adoption-audit.md` explicitly distinguish internal Document 1.4.0 from `DocumentExtractionContract` 1.0.0 / ExtractionPackage v1 and say producer adoption is unconfirmed in upstream.

Physical representation remains adequate for the two PDF projections exercised: elements have stable IDs, page number, reading order, bbox and `source_backend`; tables have IDs, dimensions, cells, spans, `is_header`, bbox and `source_backend`. Cells still have no native ID, so the local projection derives the contract ID from table ID plus row/column. Page coordinate origin is documented as top-left; it is not a contract field. The PDF table ownership changes were re-run on the same qualification PDF and still produce one 3×3 table with nine cells.

## V1 integration change disposition

`ffeab65a899dfa54ae14c6475d9d59a3b41c9d5d` adds `src/doc_extraction/integrations/kp_contract_v1.py` and a projection test. Those paths are absent at upstream `011b2a4`; the new upstream contract docs describe adoption requirements but do not implement this projection. Classification: **STILL_REQUIRED** as a local integration change.

The projection was ported explicitly to a fresh branch from `011b2a4`, then tightened in two small follow-up commits: the failed-run test now checks the canonical Document rejection that happens before projection, and incomplete producer reading order fails with `INCOMPLETE_READING_ORDER` instead of being guessed from storage order. Current local branch is `local/kp-extraction-contract-v2` at `60713327704b4c90b16ee0689875b5a431f3969b`. The old V1 branch at `ffeab65…` and source worktree at `e6835cd…` were not switched or rewritten.

## Focused evidence

V2 focused producer tests: **68 passed, 5 skipped**. The two real PDF runs used the native CPU baseline path and completed in about 0.019 seconds each. Exact package hashes, source hashes, producer-document hashes, runtimes, projection losses and KP pin are recorded in [`integration_artifacts/extraction_v2/MANIFEST.json`](../../integration_artifacts/extraction_v2/MANIFEST.json). No OmniDocBench GPU experiments were rerun.

The upstream documentation is useful adoption guidance, not evidence of a producer implementation. The authenticated live KP contract base is verified at `feature/agent-cdoi-capability-v0.1.0` / `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`. Current round-trip results use the pinned local KP integration descendant documented in the V3 manifest.
