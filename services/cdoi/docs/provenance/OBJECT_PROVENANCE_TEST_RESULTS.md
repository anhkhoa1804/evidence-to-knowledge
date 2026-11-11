# Object provenance test results

The producer generated both packages from the same real local PDF inputs using
CPU baseline parsing and the Extraction integration V3 worktree at
`54c27c86f5d2ba8b8c65c59c0654e4af48a28932` and its V1.1 projection. KP consumed those serialized JSON files through
`ExtractionPackage.model_validate_json()`, the existing adapter, and
`DocumentIR v2`.

| Case | Result | Object attribution | Structure and source trace |
|---|---|---|---|
| `qualification.pdf` | PASS | `p0-e0 → pymupdf-native`; run backend remains `baseline` | Original SHA-256, run ID, element ID/text, page, schema lineage and warning detail preserved |
| `table-qualification.pdf` | PASS | Native text → `pymupdf-native`; table anchor/table and all cells → `pymupdf_tables` | Source SHA-256, run ID, page 1, table ID, 3×3 dimensions, 9 cell IDs/text/row/column, warning detail and lineage preserved |

The table evidence trace was built with the same KP `document_evidence_for()`
helper used by semantic extraction and serialized through the `Why` evidence
metadata formatter. The output names `table-qualification.pdf`, its original
source hash, page 1/table `p0-t0`/cell `p0-t0:r0:c0`, `run_backend=baseline`,
`source_backend=pymupdf_tables`, and the resolved `detect_table` provenance
step. The existing Why path returns approved fact evidence as answer
provenance. The qualification PDF's `Item / Qty / Price` table does not trigger
KP semantic cues, so this does not claim a document-derived approved fact or a
full user-facing Ask/Why E2E answer.

## Contract controls

- Legacy 1.0 package validates and reaches `DocumentIR`; KP marks object
  backend unavailable instead of copying `baseline` into it.
- A synthetic 1.1 object with two refs resolves both backend steps and leaves
  scalar `source_backend` null.
- Dangling object refs, dangling parent refs, cycles, 1.2.0 and 1.0.0 carrying
  1.1-only keys fail closed.
- KP's 1.0 serializer omits the new fields, preserving the old strict wire
  shape. Current KP runtime advertises 1.1.0 and support for 1.0.0/1.1.0.
- EvidenceRef v1 remains unchanged and reports a scalar backend only when
  unambiguous; the full refs remain in KP Ask/Why evidence metadata.

Focused validation on the implementation worktrees:

```text
Extraction: 80 passed
KP:         80 passed
```

Extraction coverage includes IR/schema, table serialization/spans, backend
conformance, warning propagation, pipeline and contract projection. KP
coverage includes the two real-package round trips, legacy package path,
contract validation, DocumentIR, onboarding, EvidenceRef and release runtime
metadata. No GPU, OCR model, external benchmark, or SemTab case was used.

A fresh post-final-KP-code run repeated `process_file` on both original PDFs, projected and validated new packages, and passed them through KP preview ingestion. It produced package SHA-256 `2c736e0a05ef263ed0d98ed32159eaacedb69fa84ec4ce6666091560c76e5c9b` for the simple PDF and `d47d9392a325c04cdf8fafc9d8cdfe28c262775dd7b420d81e44c24e1b8ecb95` for the table PDF; see `integration_artifacts/extraction_v3/LIVE_INTEROP_V1_FREEZE.json`. The multi-ref case is synthetic only. The real PDF pair demonstrates distinct single-step refs on different objects, not a fused object supported by two backends. Current KP live contract base was verified at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`; the focused run used the local integration descendant.
