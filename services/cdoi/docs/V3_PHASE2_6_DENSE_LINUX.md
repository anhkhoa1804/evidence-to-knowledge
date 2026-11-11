# V3 Phase 2.6 Dense Linux Runtime

The Dense experiment is optional, experiment-only, and uses the frozen
`dense_structured_profile_v1` serializer with
`sentence-transformers/all-MiniLM-L6-v2`, CPU, and normalized embeddings. It
does not change production profiles, selection policy, routing, or commitment.

On a clean Linux or WSL distribution, use a separate environment:

```bash
python3 -m venv .venv-v3-dense
. .venv-v3-dense/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[models,dev]'
python scripts/check_dense_runtime.py --device cpu
```

The check records Python/platform, torch, sentence-transformers, model ID and
revision, device, normalization, model load, finite embedding shape,
normalization, and an immutable-CandidateSet Dense selection smoke test. It
does not install software automatically and returns `RUNTIME_BLOCKER` on any
failure. Do not treat a failure as a score, an abstention, or a completed
benchmark.

Only after `DENSE_RUNTIME_READY` may a full same-CandidateSet P0/P1 reranking
run be performed. Freeze the raw source/target profiles, candidate membership
and order, reference population, model revision, representation serialization,
normalization, scoring semantics, and metric definitions before it starts.
