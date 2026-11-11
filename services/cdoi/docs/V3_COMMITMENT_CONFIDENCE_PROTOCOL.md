# V3 Commitment-Confidence Protocol

Commitment confidence is not retrieval score, selection score, margin, or
policy. Its future input contract is `CandidateSet`, `AmbiguityEvidence`,
`SelectionResult`, semantic evidence, and selector agreement when observable.
Its output is `CommitmentEvidence(status, method, calibration_id,
calibration_version, score, evidence_fields)`.

Phase 1 implements only `UncalibratedCommitmentConfidence`: it always emits
`NOT_CALIBRATED` and no score. This is intentional. No model is fit on Anatomy,
no Anatomy-derived policy is installed, and no confidence evidence can commit a
proposal or populate the canonical KG.

Future calibration records must identify calibration dataset/split, feature
definition, method, version, target risk metric, and independence status.
`v3_evaluation.risk_coverage` is evaluation-only and consumes a separately
joined `reference_correct` label. It reports coverage, precision, risk,
accepted-error rate, and abstention. Anatomy use for calibration must be marked
`EXPLORATORY_NON_INDEPENDENT`, never final independent validation.
