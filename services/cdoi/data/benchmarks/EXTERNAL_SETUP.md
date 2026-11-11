# External Benchmark Setup

CDOI does not vendor OET/concept-placement, OAEI, LLMs4OL, or RCAEval data. Use `ExternalBenchmarkSetupAdapter` after obtaining data under each benchmark's license and recording the source URL, release/commit, checksum, transformation mapping, and split policy in an experiment manifest.

Concept-placement data validates induction and parent placement. OAEI-style data validates schema/property alignment and separately, where available, instance matching. RCAEval or an equivalent validates downstream ranking. None of these external datasets should alter core CDOI contracts or be required for the deterministic project benchmark.
