# Version domain audit

**Result: internal `Document` schema `1.4.0` and KP `DocumentExtractionContract` `1.0.0` version different objects. They are not directly comparable.**

At Extraction commit `e6835cd1529a87823680e2d698fe0251e286538e`, `Document.schema_version` is `1.4.0` and is serialized in `final/document.json`. `schemas/version.py` describes it as the canonical producer IR version. At KP commit `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`, `ExtractionPackage.contract_version` is `1.0.0`, and `cross_team_contracts.py` validates that package identity against `DocumentExtractionContract`.

The direct legacy adapter `DocExtractionBackend` validates the producer `schema_version` and currently accepts `1.0.0`, `1.1.0`, and `1.2.0`; its test asserts this allowlist. Passing producer `1.4.0` to that legacy adapter yields `DOC_EXTRACTION_SCHEMA_VERSION_UNSUPPORTED`. This is the expected result of using the wrong boundary for the new integration. It does not establish that an `ExtractionPackage` `1.0.0` is incompatible.

The projection writes `contract_version: "1.0.0"` and retains producer schema lineage separately as `provenance.transformation_chain: ["doc-extraction-document/1.4.0"]`. KP parses the serialized package as contract 1.0.0, copies the transformation chain into its own `DocumentIR v2` provenance, and completes the round-trip. This validates the version-domain distinction.

Therefore the earlier `DOC_EXTRACTION_SCHEMA_VERSION_UNSUPPORTED` was **version-domain confusion** when producer `Document.schema_version` was sent to the legacy adapter. The contract-package path is compatible at the version gate. It still has separate field-semantics gaps documented in `docs/extraction-kp-contract/EXTRACTION_TO_KP_MAPPING_V1.md` and `docs/extraction-kp-contract/OWNER_DECISIONS.md`.
