# V3 Phase 2.10E-R1 Linux Runner

Use Python 3.12 with pyarrow available in the research environment. Cache the
frozen Hugging Face revision under data/benchmarks/external/rcaeval and retain
the cases.parquet SHA-256 recorded in the R1 baseline.

Run:

    python tools/run_v3_phase2_10e_r1.py

Artifacts are written to experiments/archive/v3_phase2_10e_r1. The runtime is
CPU-only: SQLite indexes selected spans in configured chunks of 1,000 and does
not require CUDA or a GPU. Windows and Linux use the same case split, input
hashes, ORACLE_WINDOW, frozen candidate rules, and artifact schemas.
