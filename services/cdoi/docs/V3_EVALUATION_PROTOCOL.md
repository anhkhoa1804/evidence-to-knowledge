# V3 Evaluation Protocol

Anatomy remains a diagnostic/regression corpus. It must not be used to train a
routing/confidence method and then presented as independent final validation.
The V3 harness compares selectors on the same CandidateSet and reports
selection availability, semantic abstention, technical unavailability,
same-case accuracy only after reference join, latency, and agreement. Agreement
is evidence, not an accept rule.

Dense-selector experiments require a clean runtime and must report R@1/5/10/20,
MRR, non-trivial R@K, hard-negative discrimination, shared-Top-K selection,
same-case R1/R2/Qwen comparison, latency, reliability, and resources. Current
status is `RUNTIME_BLOCKER`, not a missing semantic algorithm.

The second-domain adapter must receive a source ontology, full target corpus,
reference mappings and relation types, license/provenance, and a reproducible
semantic-profile extraction path. No qualifying bundled corpus was found;
status is `DATA_MISSING`.
