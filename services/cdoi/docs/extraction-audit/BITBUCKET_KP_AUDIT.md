# KP/CDOI Bitbucket branch audit

**Status: live contract base verified.** Authenticated `git ls-remote` confirms `feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3` on `http://<internal-git-host>/scm/<project-key>/vdt-infra-knowledge-graph.git`. The previous local 503 attempt is superseded. A later optional refresh from this environment could not connect to its network proxy before a Bitbucket response; that does not change the supplied verified live ref.

## Candidate branch

`origin/feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`, dated 2026-10-06 21:48 +07, is a direct descendant of KP master (`0d063821…`), 13 commits ahead and 0 behind. It descends from `origin/AIAgent` (`3370f5a…`, 2 commits ahead of master) by 11 commits. It contains later governed evidence-support work while retaining the document boundary code. Audit worktree: `/home/anh-khoa/audit-kp-agent-cdoi` (detached at `eeb41c7…`); the active KP `master` worktree was not switched or edited by branch inspection.

The independent `origin/feature/agent-upgrade` ref has no merge base with current master and its visible history is a separate ontology/demo snapshot. It is not a reasonable extraction integration base from available evidence.

## Contract and consumer findings

The KP branch defines a strict, JSON-serializable Pydantic `ExtractionPackage` in `src/cdoi/cross_team_contracts.py` with identity `contract_name=DocumentExtractionContract`, `contract_version=1.0.0`. `ContractModel` forbids unknown fields. `ExtractionPackage` validates contract identity, globally unique element/table/cell IDs, matching package/provenance backend, and rejects secret-like metadata keys. The generated cross-team JSON Schema and a canonical example are present. `docs/CROSS_TEAM_CONTRACTS_V1.md` defines ownership, strict version policy, null behavior, and error families.

The KP branch also has a separate versioned `DocumentIR` (`cdoi_document_ir_v2`), `extraction_package_to_document_ir()`, `DocumentSemanticAdapter`, `DocumentIngestionService.preview_extraction_package()`, and onboarding `add_extraction_package()`. It has a producer-specific JSON compatibility adapter, `DocExtractionBackend`, `preview_doc_extraction_output()`, and `add_doc_extraction_output()`.

The JSON compatibility adapter accepts only upstream `schema_version` 1.0.0, 1.1.0, or 1.2.0; it rejects other 1.x versions explicitly. The current audited producer emits internal schema 1.4.0. That path is not compatible as-is. Separately, the KP-owned `ExtractionPackage` is the intended stable wire contract for a new producer, but the selected extraction checkout does not emit it. A Pydantic model/schema on KP is not proof of producer conformance.

The candidate local contract proposal from the earlier audit is superseded as the primary design by this discovered KP-owned contract. Preserve the local proposal and its report as historical discovery; do not silently rewrite it or implement it. A field-by-field reassessment and concrete contract gaps are in `docs/extraction-kp-contract/CONTRACT_CANDIDATE_REASSESSMENT.md`.

## Source and history

The contract, adapter, and integration source first appear in commit `3370f5a2` (“feat: add complete CDOI capability integration sources”). `docs/CDOI_DOCUMENT_EXTRACTION_CONTRACT_V1.md` says the Extraction Team should target `ExtractionPackage` directly and keeps the old serialized `Document` adapter only for known compatibility versions. The adoption checklist says Extraction must implement conformance tests. `experiments/archive/agent_cdoi_capability_v0_1_20261002/BITBUCKET_HANDOFF.md` explicitly states `LIVE_EXTRACTION_INTEROPERABILITY_NOT_MEASURED`; it identifies the contract, not a live producer/consumer round-trip.

## Focused test result

On the audit worktree at `eeb41c7…`, these focused tests passed: contract model, producer JSON adapter, document ingestion, and knowledge onboarding. Exact result and limits are in `docs/extraction-audit/BITBUCKET_FOCUSED_TEST_RESULTS.md`. These tests validate the KP-side implementation; they do not test the current extraction producer or a live cross-repository round-trip.
