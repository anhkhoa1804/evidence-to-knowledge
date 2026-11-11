# Extraction full-suite failure classification

Recorded baseline on selected producer branch `e6835cd1529a87823680e2d698fe0251e286538e`: **478 passed, 16 skipped, 5 failed**. Focused CPU parser qualification was **76 passed, 4 skipped**. The five failures were not reproduced in this task; classification below is based on the recorded pytest outcomes and test dependency/data requirements, not a new test run.

| Failed pytest node | Count | Classification | Basis / limit |
|---|---:|---|---|
| `tests/test_benchmark_registry.py::test_all_registry_manifests_are_strict_and_deterministic` | 1 | `MISSING_EXTERNAL_DATA` | Test requires `OmniDocBench_demo.json`; that external data file was absent. Registry assertion is data-dependent. |
| `tests/test_config_and_backends.py::test_installed_backends_report_available` | 1 | `OPTIONAL_BACKEND_UNAVAILABLE` | Asserts Table Transformer is installed/available; reference environment has Torch/Transformers, local lightweight environment does not. |
| `tests/test_config_and_backends.py::test_docling_pipeline_options_follow_configured_device[cpu]` and `[cuda]` | 2 | `OPTIONAL_BACKEND_UNAVAILABLE` | Test imports Docling to inspect configuration; Docling is not installed. The CUDA parameter is config plumbing, not evidence of a CUDA-only core route. |
| `tests/test_config_and_backends.py::test_table_transformer_moves_inputs_to_its_device` | 1 | `OPTIONAL_BACKEND_UNAVAILABLE` | Test needs Torch/Transformers even though model calls are stubbed; those dependencies are absent. |

No failure is classified `CORE_REGRESSION` from the current evidence. The prior pytest cache retained all five node IDs; detailed exception text was not retained, so classification follows each test’s explicit data/dependency requirements and does not substitute for captured tracebacks. The focused native PDF tests and generated native PDF/table qualification passed. A missing data asset or optional model library is not a code regression by itself.

`core local CPU path = TESTED` for the focused native text/table qualification, not for every document family or OCR route. OCR has no locally installed/qualified backend. No CUDA or large model dependency was added.
