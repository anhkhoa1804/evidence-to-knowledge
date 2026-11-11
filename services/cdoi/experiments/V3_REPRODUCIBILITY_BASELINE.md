# V3 Reproducibility Baseline

Machine-readable capture: `experiments/archive/v3_phase1_baseline/BASELINE.json`.
It substitutes deterministic source/data/config/runtime fingerprints for a Git
commit because this workspace is not a Git repository.

| Scope | Files | Aggregate SHA-256 |
| --- | ---: | --- |
| `src/cdoi` | 49 | `ea8c97a9b89e449cfd98fb06560cdd63cd9ba26c6029f3490776cab19589f850` |
| `tests` | 22 | `a6a4c45379bc5ea4c62c47fd783facb899ed6af8892940c72c3be988dff3d008` |
| `experiments/configs` | 39 | `60821e8201f01e66b1a7a6c46c2fef621a0587cd90fd6bfd3ed84e6ce3d6e183` |
| `data/fixtures` | 8 | `ac12d11018a27d7a78d26010ad8fcb28dc5737f9c04bb465d175b2d1a36ba140` |
| `ontologies` | 16 | `5f97d1297c9c489507943185c0a7a7bd012600a9b33e052efad9e54bcb5e97e9` |
| Anatomy source/target/reference/index | 4 | `6784872932ec21ae8782697e4a1909555b6db4c855ffa62f3d7e06f5f2b8e7bf` |

Runtime: CPython 3.12.7, Windows 10.0.19045, AMD64/64-bit, 63 installed
packages, pip-freeze SHA-256
`3b0455c6e97500e807bd9c90d86c3a989c1d3693174434acac5df9d009248220`.

The baseline also hashes the frozen V2.6 post-ranking, Qwen-validation, and
unified evidence artifacts. `tree_manifest()` in `v3_phase2.py` reproduces a
path-sorted, content-hashed manifest without reading secrets. A matching future
capture establishes same selected code/data/config/runtime; a mismatch must be
treated as a different experiment environment.
