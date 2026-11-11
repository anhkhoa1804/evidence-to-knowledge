# V3 Phase 2.9 Baseline

Frozen before distributed trace evidence was introduced. This workspace has no Git provenance; deterministic content hashes are the baseline anchor.

{
  "baseline_version": "v3_phase2_9_pre_traces_v1",
  "evidence_modalities": [
    "entity",
    "relation",
    "event",
    "change_event",
    "metric",
    "semantic_term"
  ],
  "operational_context_contract": "operational_evidence_context_v1",
  "phase": "V3 Phase 2.9 \u2014 Distributed Trace Evidence Integration",
  "policy_invariants": [
    "execution path is not causal path",
    "no anomaly detection",
    "no RCA or causal scoring",
    "exact-ID entity correlation only",
    "no schema expansion from traces",
    "no automatic commitment",
    "canonical-KG safety gate unchanged",
    "semantic decision policy unchanged"
  ],
  "preprocessing_contract": "cdoi_preprocessing_v1",
  "protected_artifacts": {
    "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md": "1c6f4bb9753bdb68cb86d7ce186e134be283ffc247e5eac79d6c22552680a0aa",
    "experiments/V3_PHASE2_7_RESEARCH_GATE.md": "39387238696bd4fd9ed81f0b2bc746ddf8d1d3d5678ff91425cf37d771aa7e1f",
    "experiments/V3_PHASE2_8_RESEARCH_GATE.md": "faa5226b462587d352714e307d0e76d2088a43d77c4b38287fc578a85ebc9d34",
    "experiments/archive/v3_external_dh/MANIFEST.json": "db0a3287f1a63bb67e6bb0ec6488861c88c511cdb7e07590a3fbafffddfd7618",
    "experiments/archive/v3_phase2_7/MANIFEST.json": "8fb37e57b8def3cef389ccdf268f2b5eb1d07cbda9085f678cb4f592a556e858",
    "experiments/archive/v3_phase2_8/DEMO_RESULT.json": "7248250f2bcede7e0931773b100f7a54536e90ab9048343954770511d0f5cc3c",
    "experiments/archive/v3_phase2_8/MANIFEST.json": "e7e3920ab9520e578ce9c2d85696f0a72c1182f6442fd52f1b8f568836388586",
    "experiments/archive/v3_phase2_8/RESEARCH_GATE.json": "a957b56804512e3c195d9ccad1a542a2edb3a782b73bb8cf3f90a7e01accc443"
  },
  "runtime": {
    "implementation": "CPython",
    "machine": "AMD64",
    "platform": "Windows-10-10.0.19045-SP0",
    "python": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]"
  },
  "source_tree_sha256": "a83825f58e82afaf2099d02a62b79fef1561b787cd1c29847224375e4d623fa4",
  "test_count": 155,
  "test_tree_sha256": "f5f3b0363bacfd739983a7a75542f1edf77dc3d227f572d3ece79e4ddbf7731d"
}
