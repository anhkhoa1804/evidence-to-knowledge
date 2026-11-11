# Local Environment

Snapshot date: 2026-10-07 (Asia/Bangkok)

## Machine snapshot

| Item | Observed |
|---|---|
| OS | Ubuntu 24.04.5 LTS (Noble Numbat) |
| CPU | Intel Core i7-8700 @ 3.20 GHz; 6 cores / 12 logical CPUs |
| RAM | 7.6 GiB total; 3.5 GiB available at snapshot |
| GPU | `nvidia-smi` unavailable; no NVIDIA GPU path detected |
| Free disk | 93 GiB on `/dev/nvme0n1p2` (116 GiB filesystem) |
| Python | Python 3.12.3 (`python3`; `python` alias unavailable) |
| Git | 2.43.0 |
| Docker | unavailable on PATH |
| Java | unavailable on PATH |
| Package manager | system pip 24.0; Python venv available; no `uv` detected |

## Repository preservation

The KP/CDOI repository was clean at the initial snapshot. Current branch: `master`. HEAD: `0d06382` (`Add V4 enterprise source discovery and RCA POC`). The only configured remote is `origin` at `http://<internal-git-host>/scm/<project-key>/vdt-infra-knowledge-graph.git` (fetch and push). No untracked or modified paths were reported by `git status --short`.

## LOCAL_CPU_PROFILE

- Keep processing to one document or a small batch at a time; default workers: at most 2 unless measured memory use supports more.
- Prefer native text and document parsers before OCR.
- Do not install CUDA-only packages or large local language/vision models.
- Avoid loading multiple copies of model runtimes; cache reusable extraction outputs.
- Treat CPU OCR as optional and qualify it on one case before expanding.
- Freeze small case lists before predictions and record runtime and peak memory when available.

## Constraints and unmeasured details

This is a CPU-first local machine with about 8 GiB RAM. GPU availability is not established beyond the absence of `nvidia-smi`. The reported per-case peak RSS is process high-water mark, not an incremental memory measurement.
