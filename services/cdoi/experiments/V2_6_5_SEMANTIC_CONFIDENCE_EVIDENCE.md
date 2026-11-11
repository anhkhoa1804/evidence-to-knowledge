# V2.6.5 Diagnostic — Unified Semantic-Confidence Evidence Table

The machine-readable V2.6.5 result contains one entry per sampled source with
two deliberately separate objects:

- `observable_at_inference`: R1/R2 candidates and scores, margin/spread,
  existing lexical/context/structural features, Qwen validity/selection,
  agreement flags, and diagnostic stratum.
- `reference_only`: gold candidate/rank, non-trivial flag, and correctness
  labels, attached only after inference.

No model is trained from this table. It is preparation for an independently
split and calibrated future semantic-confidence study, not a production model.

Real embeddings remain **RUNTIME_BLOCKER** in this Windows environment due to
the existing PyTorch `c10.dll` / WinError 1114 failure. Anatomy also primarily
measures equivalence alignment, so these results do not establish general
relation-classification competence.
