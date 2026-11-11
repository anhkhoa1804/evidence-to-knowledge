"""Check the optional Phase-2.6 Dense runtime without emitting benchmark metrics."""

from __future__ import annotations

import argparse
import json
import sys

from cdoi.v3_phase2_6_followup import dense_runtime_check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--no-normalize", action="store_true")
    args = parser.parse_args()
    result = dense_runtime_check(args.model_id, revision=args.revision, device=args.device, normalize_embeddings=not args.no_normalize)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "DENSE_RUNTIME_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
