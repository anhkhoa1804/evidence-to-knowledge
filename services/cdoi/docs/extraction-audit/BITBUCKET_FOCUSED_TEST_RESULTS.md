# Focused Bitbucket candidate test results

KP audit commit: `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3` in detached worktree `/home/anh-khoa/audit-kp-agent-cdoi`.

Command:

```bash
PYTHONPATH=src /tmp/cdoi-bitbucket-audit-venv/bin/python -m pytest \
  tests/unit/test_cross_team_contracts.py \
  tests/unit/test_doc_extraction_adapter.py \
  tests/unit/test_document_ingestion.py \
  tests/unit/test_knowledge_onboarding.py
```

Result: **40 passed in 0.91 s**. The temporary CPU-only venv contains the project’s lightweight dependencies plus the declared optional `pyshacl` validation dependency; no OCR/model/CUDA packages were installed. The audit worktree remains clean.

The canonical JSON example also loaded as `DocumentExtractionContract` 1.0.0. A direct compatibility check against producer schema `1.4.0` returned `DOC_EXTRACTION_SCHEMA_VERSION_UNSUPPORTED`, as specified by the adapter allowlist.

Coverage includes strict package models, package-to-DocumentIR conversion, fatal extraction failure handling, table/cell evidence coordinates, producer JSON adapter version rejection, provenance, and onboarding. This validates the KP-side pinned local integration derived from the contract branch; authenticated live refs now confirm the contract base at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`. It is not a producer test and not a live document round-trip. The initial invocation before `PYTHONPATH=src` and dependencies was setup-blocked; it is not counted as a code test failure.

Extraction Bitbucket candidate tests: **not run** because the exact remote URL and branch refs are unavailable. Existing selected GitHub-derived branch `e6835cd…` qualification results remain 76 passed / 4 skipped for focused CPU extraction, but do not qualify a Bitbucket branch.
