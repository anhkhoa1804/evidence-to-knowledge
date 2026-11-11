# V3 Phase 2.6 Dense Linux Readiness

**IMPLEMENTED FACT:** `scripts/check_dense_runtime.py` executes the frozen `dense_structured_profile_v1` smoke contract through `SentenceTransformerBackend`; it has no automatic installation behavior and emits no accuracy metrics on a technical failure.

## Current status

`RUNTIME_BLOCKER`

Technical cause: `torch_import` / `OSError` — [WinError 1114] A dynamic link library (DLL) initialization routine failed. Error loading "<project-root>\code_v1\.venv\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies.

## Runtime checks

| Check | Result |
| --- | --- |
| PYTHON_OK | PASS |
| TORCH_IMPORT_OK | FAIL |

## Recorded runtime metadata

| Field | Value |
| --- | --- |
| platform | Windows-10-10.0.19045-SP0 |
| python | 3.12.7 |
| device | cpu |
| model_id | sentence-transformers/all-MiniLM-L6-v2 |
| model_revision | None |
| normalize_embeddings | True |
| relevant_package_versions | {'torch': '2.14.0', 'sentence-transformers': '5.7.0', 'transformers': '5.17.0', 'numpy': '2.5.3'} |
| relevant_package_versions_sha256 | cc3f9ce0d8f258d04be2b2375a1551485e787190e03beac963e719e77e4f8060 |
| dense_backend_sources_sha256 | a77cf4b3ea2c91a79d2afd794f74aa02e4e7d9a89870a42b6b9c6fca7442e32e |

## Linux CPU execution

On a clean Linux or WSL distribution, create a separate virtual environment, install the project with `.[models,dev]`, and run `python scripts/check_dense_runtime.py --device cpu`. Only a `DENSE_RUNTIME_READY` smoke result authorizes a subsequent full fixed-CandidateSet Dense runner. Model ID, revision, normalization, serialization, CandidateSet membership, and evaluation population must remain frozen. A blocker is `RUNTIME_BLOCKER`, never zero performance or semantic abstention.

The existing baseline freezes `sentence-transformers/all-MiniLM-L6-v2`, CPU, normalized embeddings, and `dense_structured_profile_v1`; no Anatomy model or weight search occurred.
