# V3 Phase 2.8 Baseline

Frozen before metric evidence was introduced. This workspace has no Git provenance; deterministic content hashes are the baseline anchor.

{
  "baseline_version": "v3_phase2_8_pre_metrics_v1",
  "operational_context_contract": "operational_evidence_context_v1",
  "operational_context_sha256": "9521ef8bb840608d554d97575bfd753956e8b2b30d947be4d4a2e98869d3bd90",
  "phase": "V3 Phase 2.8 \u2014 Metrics Evidence Integration",
  "policy_invariants": [
    "no anomaly detection",
    "no causal inference or RCA",
    "exact-ID entity correlation only",
    "no schema expansion from changes",
    "no automatic commitment",
    "canonical-KG safety gate unchanged",
    "semantic decision policy unchanged"
  ],
  "preprocessing_contract": "cdoi_preprocessing_v1",
  "protected_artifacts": {
    "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md": "1c6f4bb9753bdb68cb86d7ce186e134be283ffc247e5eac79d6c22552680a0aa",
    "experiments/V3_PHASE2_7_RESEARCH_GATE.md": "39387238696bd4fd9ed81f0b2bc746ddf8d1d3d5678ff91425cf37d771aa7e1f",
    "experiments/archive/v3_external_dh/MANIFEST.json": "db0a3287f1a63bb67e6bb0ec6488861c88c511cdb7e07590a3fbafffddfd7618",
    "experiments/archive/v3_phase2_7/DEMO_RESULT.json": "3412b33442de68f11e915febc40de04ad72fcb2da04e512ad7b73a34060e554b",
    "experiments/archive/v3_phase2_7/MANIFEST.json": "8fb37e57b8def3cef389ccdf268f2b5eb1d07cbda9085f678cb4f592a556e858",
    "experiments/archive/v3_phase2_7/RESEARCH_GATE.json": "d47ba1520ba09c6b872c05f231571e10593e3dc7eaa819bd7a9cf4f28af4eb1b"
  },
  "raw_preprocessing_sha256": "da5b2b66b1d93d4189ec8c2a96c2eff63c9319459226b2548fcd55f7a01f4caa",
  "runtime": {
    "implementation": "CPython",
    "machine": "AMD64",
    "platform": "Windows-10-10.0.19045-SP0",
    "python": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]"
  },
  "source_tree_sha256": "cfac2f5ab7e978290db852930415a2e7fa70f8de45d391567e46b45f56710e56",
  "supported_evidence_types": [
    "entity",
    "relation",
    "event",
    "change_event",
    "semantic_term"
  ],
  "test_count": 143,
  "test_tree_sha256": "402b461eadc4e094f3d2ab17d05c481de6974c8929020bd22da25b0750a12733"
}
