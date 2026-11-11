# Evaluation

## Scope

V2.5 evaluates the frozen CDOI V1/V2 semantic core. Synthetic CDOI-Bench is a proof-of-mechanism fixture; it is not external validation, enterprise validation, or a production-readiness claim.

## Modes

`offline deterministic`: CDOI-Bench, controlled degradation/noise, late evidence, and continual-order experiments. No network, credentials, or model downloads are required.

`external benchmark`: OAEI, concept placement, and RCAEval adapters run only after the license-aware setup in [external setup](data/benchmarks/external/README.md).

`model`: sentence-transformer and LLM experiments are optional. Model ID, normalization, cache behavior, prompt version, calls, token/cost fields where available, and skip reason are persisted.

## Metrics

Alignment reports exact relation accuracy, equivalence precision/recall/F1, false-merge count/rate, class placement, separately scoped object/data-property metrics, bridge and promotion precision, unresolved rate, review rate, auto-decision coverage, selective accuracy, and sample counts. Bootstrap intervals are descriptive 95% percentile intervals with a fixed seed.

Placement reports retrieval recall@1/@5/@10, Top-1/Top-5 parent accuracy, and MRR. Alignment conditional on retrieval is intentionally kept separate from retrieval misses.

Robustness experiments preserve source-case provenance. They report raw metrics and clean-minus-noisy degradation. Late-evidence traces record the prior decision, new evidence, proposed state, validation/review state, version transition, and any simulated approved KG effect.

## Interpretation

Embedding signal is not a real embedding model. Controlled fixture performance is not enterprise performance. External benchmark performance is still not proof of production readiness. Results are separated in `experiments/EXTERNAL_RESULTS.md`, `experiments/ROBUSTNESS_RESULTS.md`, `experiments/MODEL_RESULTS.md`, and `experiments/V2_5_RESULTS.md`.
