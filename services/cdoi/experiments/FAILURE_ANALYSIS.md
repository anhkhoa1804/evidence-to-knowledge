# Failure Analysis

## V2.6 Observations

1. `class_relation_error`: 7050 on OAEI Anatomy reference-positive pairs.
2. `false_unresolved`: 530 on the same protocol.
3. `unsafe_equivalence`: 0; this is not a precision estimate because OAEI negatives were absent.
4. Real embedding execution: blocked by PyTorch DLL initialization in this Windows runtime after optional dependency installation.
5. Qwen execution: skipped before network access because `DMP_MERCURY` was absent; no endpoint conclusion follows.

## Interpretation

The external result is a failure signal, not a ranking claim. The current pair-level adapter cannot separate target retrieval failure from alignment selection. The next research step is an externally valid candidate-retrieval protocol, followed by real-model reruns in a compatible runtime.
