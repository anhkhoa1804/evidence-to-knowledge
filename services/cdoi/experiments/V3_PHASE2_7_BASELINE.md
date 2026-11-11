# V3 Phase 2.7 Baseline

This immutable baseline was captured before the operational-context contract was introduced. The workspace is not a Git repository; deterministic content hashes are therefore the provenance anchor.

{
  "baseline_version": "v3_phase2_7_pre_context_v1",
  "demo_artifact_tree_sha256": "82b37a93d48ed5990a86eb8f3b2e709ae535a3d58838962be1a7ff153073e9a3",
  "evidence_schema_sha256": "e796d5a4b8bd3e1b7e45f86d0af6c0b1672d8a014c7ad7c5f8b6b9b7512e5f48",
  "fixture_tree_sha256": "97ab5e579e9b3dba43c79568e86626034001720dbf9749b850bdf023aafff87e",
  "phase": "V3 Phase 2.7 \u2014 Operational Evidence Context & Pre-RCA Validation",
  "policy_invariants": [
    "semantic decision policy unchanged",
    "no selector/routing/threshold/calibration change",
    "no automatic commitment",
    "canonical-KG safety gate unchanged",
    "exact-ID entity resolution only",
    "no causal inference or RCA"
  ],
  "preprocessing_contract": "cdoi_preprocessing_v1",
  "protected_artifacts": {
    "experiments/V3_PHASE2_6_DENSE_REPRESENTATION.md": "a5b4a96cff640ad3dafbae16790bf08a0fb443d30cb00208c395ad90a790f915",
    "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md": "1c6f4bb9753bdb68cb86d7ce186e134be283ffc247e5eac79d6c22552680a0aa",
    "experiments/archive/preprocessing_mvp_demo/manifest.json": "0a6908f298f4bc142645f28feaa4788db8c631cf48887756de54c773e6c4ffab",
    "experiments/archive/v3_external_dh/MANIFEST.json": "db0a3287f1a63bb67e6bb0ec6488861c88c511cdb7e07590a3fbafffddfd7618"
  },
  "raw_preprocessing_sha256": "da5b2b66b1d93d4189ec8c2a96c2eff63c9319459226b2548fcd55f7a01f4caa",
  "runtime": {
    "implementation": "CPython",
    "machine": "AMD64",
    "platform": "Windows-10-10.0.19045-SP0",
    "python": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]"
  },
  "source_tree_sha256": "86f286b8d041fde43ccc7ac8b26ec6df74a00015a539b0f13fc8b474cd63f246",
  "supported_source_types": [
    "service_inventory_csv",
    "dependency_jsonl",
    "log_jsonl",
    "glossary_yaml",
    "deployment_change_csv"
  ],
  "test_count": 135,
  "test_tree_sha256": "86829dec462ec6aca1a46b84cb572a91e5fe405f8c6e1e18673db204b50102ef"
}
