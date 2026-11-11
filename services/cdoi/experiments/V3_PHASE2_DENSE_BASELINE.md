# V3 Phase 2 Dense Baseline

Status: `RUNTIME_BLOCKER`.

Attempted environments:

| Environment | Result |
| --- | --- |
| Existing Windows project virtual environment | `torch` import fails: PyTorch `c10.dll`, WinError 1114 |
| WSL Linux CPU | `wsl.exe` is installed but no Linux distribution is installed |
| Clean in-repository alternative | None is provisioned; no model/runtime was silently downloaded |

No dense retrieval, shared-Top-K reranking, hard-negative comparison, latency,
or resource result was recorded. Zero performance is not implied.

The configurable `DenseSemanticSelector` is implemented against the common V3
selector contract and has mock-backend tests for selected and
technical-unavailable outcomes. It is ready for D2 fixed-candidate evaluation.
A dense retriever must be run only in a clean CPU/Linux runtime and report
R@1/5/10/20, MRR, non-trivial retrieval, discrimination, same-case selector
comparison, latency, reliability, resources, and `COST_NOT_MEASURED` unless a
measured cost source is available.
