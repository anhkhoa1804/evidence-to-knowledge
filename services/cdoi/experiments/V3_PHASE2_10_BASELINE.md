# V3 Phase 2.10 Baseline

Frozen before incident-graph implementation.

{
  "baseline_version": "v3_phase2_10_pre_graph_v1",
  "context_contract": "operational_evidence_context_v1",
  "evidence_modalities": [
    "entity",
    "relation",
    "event",
    "change_event",
    "metric",
    "trace_span",
    "semantic_term"
  ],
  "phase": "V3 Phase 2.10 \u2014 Incident Evidence Graph & Candidate Cause Representation",
  "policy_invariants": [
    "no new adapters",
    "no anomaly detection",
    "no causal inference or RCA ranking",
    "no automatic commitment",
    "canonical KG unchanged",
    "semantic decision policy unchanged"
  ],
  "preprocessing_contract": "cdoi_preprocessing_v1",
  "protected_artifacts": {
    "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md": "1c6f4bb9753bdb68cb86d7ce186e134be283ffc247e5eac79d6c22552680a0aa",
    "experiments/V3_PHASE2_8_RESEARCH_GATE.md": "faa5226b462587d352714e307d0e76d2088a43d77c4b38287fc578a85ebc9d34",
    "experiments/V3_PHASE2_9_RESEARCH_GATE.md": "f3fbeb0d6cb4a508727182c4d680bf732ab504a2046bcb3e24ed6afff3052404",
    "experiments/archive/v3_external_dh/MANIFEST.json": "db0a3287f1a63bb67e6bb0ec6488861c88c511cdb7e07590a3fbafffddfd7618",
    "experiments/archive/v3_phase2_7/MANIFEST.json": "8fb37e57b8def3cef389ccdf268f2b5eb1d07cbda9085f678cb4f592a556e858",
    "experiments/archive/v3_phase2_8/MANIFEST.json": "e7e3920ab9520e578ce9c2d85696f0a72c1182f6442fd52f1b8f568836388586",
    "experiments/archive/v3_phase2_9/DEMO_RESULT.json": "9870cf959c4a189fcb46361f41eb953e7bf108de0052ac29a9acd32b7d689528",
    "experiments/archive/v3_phase2_9/MANIFEST.json": "347d682f905c5ce5219172f776bf51f87d5899a225233dc2077c4bb1b2cbbad8"
  },
  "runtime": {
    "implementation": "CPython",
    "machine": "AMD64",
    "platform": "Windows-10-10.0.19045-SP0",
    "python": "3.12.7 (tags/v3.12.7:0b05ead, Oct  1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]"
  },
  "source_tree_sha256": "fca5eec3d58ac1e755f67cd6a3a833588b7ea4ca6c06ef11f3b41f42db4925f3",
  "test_count": 167,
  "test_tree_sha256": "0cb4b9cd0eef7adf3679ce0a268148df686725f9e079c932dc3ef86ef9bb95e6"
}
