# Doc-Extraction Branch Audit

Audit date: 2026-10-07. No remote branch was merged.

| Remote | Branch | HEAD | Last commit | Ahead / behind GitHub master | Contract changes | Tests / docs | Candidate |
|---|---|---|---|---:|---|---|---|
| GitHub | `master` | `d08abb12` | 2026-09-02, `research: build the EN/VI production corpus and rank real failures` | baseline | Internal canonical IR; no ExtractionPackage | Older baseline | No |
| GitHub | `fix/table-text-ownership` | `e6835cd1` | 2026-10-02, `Add reproducible benchmark infrastructure` | 85 ahead / 0 behind; merge-base is master | Internal IR now `1.4.0`; still explicitly blocked on external ExtractionPackage v1 authority | New production boundary/API docs, output/resource/security docs, broad parser and regression tests | Yes, local base only |
| Bitbucket | not discovered | — | — | — | — | No URL in GitHub config, tracked content, or reachable history | No |

The selected branch has relevant changes in `src/doc_extraction/`, `tests/`, `docs/`, `README.md`, and `pyproject.toml`. It is a direct descendant of `master`, so the differences are incremental rather than a merge of unrelated branch histories. The branch includes the explicit `docs/extractionpackage-v1-integration.md` blocker and does not contain a producer adapter that KP can safely consume.

The local repository branch `local/kp-extraction-integration-20261007` points to `e6835cd1529a87823680e2d698fe0251e286538e`. This is a reviewable local integration base only; no push or merge was made.
