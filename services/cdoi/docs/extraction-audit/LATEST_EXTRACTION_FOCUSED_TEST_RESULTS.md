# Latest Extraction focused test results

Producer worktree: `/home/anh-khoa/doc-extraction-latest-integration`, branch `local/kp-extraction-contract-v2`, HEAD `60713327704b4c90b16ee0689875b5a431f3969b`; upstream base `011b2a4cd01f3f6f4d96780f7288b239cd80789a`.

Command:

```bash
PYTHONPATH=src /home/anh-khoa/doc-extraction/.venv/bin/python -m pytest -q \
  tests/test_ir_schema.py tests/test_table_serialization.py \
  tests/test_table_spans.py tests/test_backend_conformance.py \
  tests/test_page_warning_propagation.py tests/test_dispatcher.py \
  tests/test_pdf_routing.py tests/unit/test_kp_contract_v1_projection.py
```

Result: **68 passed, 5 skipped in 0.64 s**. The environment initially resolved the editable install to the old V1 source; explicit `PYTHONPATH=src` corrected source selection. The first V2 projection suite exposed an invalid test that attempted to instantiate a failed canonical `Document`, which is rejected before projection. The test now asserts that canonical boundary rejection. A further test confirms incomplete reading order fails closed instead of using storage order.

The two additional skips are optional backend tests in this focused selection; no test failure remains. Native PDF qualification was also run directly on the two real local PDF inputs through `process_file()` using `configs/cpu.yaml` and CPU. It produced 1 text element for the simple PDF and a 3×3/9-cell table for the table PDF. Measured full runtimes were 0.01896 s and 0.01912 s, respectively. No CUDA, Torch model, Docling OCR model or benchmark evaluator was loaded for these born-digital PDFs.

KP consumer tests on local integration HEAD `78117e66d0e076f7270eaceb286a31bc8911b729`:

```bash
PYTHONPATH=src /home/anh-khoa/doc-extraction/.venv/bin/python -m pytest -q \
  tests/unit/test_cross_team_contracts.py \
  tests/unit/test_doc_extraction_adapter.py \
  tests/unit/test_document_ingestion.py \
  tests/unit/test_knowledge_onboarding.py \
  tests/integration/test_live_extraction_package_v1.py
```

Result: **45 passed**. The five live package tests accepted v1, rejected unsupported versions, preserved the required source hash, rejected fatal extraction errors, and exercised the existing onboarding preview.

The two V2 JSON packages were separately parsed by `ExtractionPackage.model_validate_json`, converted by `extraction_package_to_document_ir()`, and passed to `DocumentIngestionService.preview_extraction_package()`. This used a pinned local KP integration commit, not a refreshed Bitbucket HEAD. See the artifact manifest for package and producer-document SHA-256 values.
