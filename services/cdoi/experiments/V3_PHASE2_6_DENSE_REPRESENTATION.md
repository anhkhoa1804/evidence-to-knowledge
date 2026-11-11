# V3 Phase 2.6 Dense Representation

Dense evaluation was attempted before new scoring research. WSL exists but has no installed distribution. The project environment and a freshly created isolated CPU environment both fail on PyTorch `c10.dll` with `WinError 1114`; no dense result was fabricated.

## Frozen representation design

`dense_structured_profile_v1` serializes present fields deterministically as labelled lines: canonical label, aliases, definition, parents, children, and properties. The configurable lazy backend is `SentenceTransformerBackend(model_id, revision, device, normalize_embeddings)` and returns normal V3 dense scores/SelectionResults when a runtime is available. No Anatomy weight search occurred.

## Runtime status

| Runtime | Status |
| --- | --- |
| WSL | No installed Linux distribution |
| Project Python | RUNTIME_BLOCKER: c10.dll / WinError 1114 |
| Fresh CPU venv (torch 2.14.0) | RUNTIME_BLOCKER: same c10.dll / WinError 1114 |
| Dense retrieval/reranking | Not measured; no fabricated values |
