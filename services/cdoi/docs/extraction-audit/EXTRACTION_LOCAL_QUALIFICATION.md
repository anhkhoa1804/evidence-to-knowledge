# Doc-Extraction Local Qualification

Machine: Ubuntu 24.04.5, Intel Core i7-8700, 12 logical CPUs, 7.6 GiB RAM (3.5 GiB available at initial snapshot), 93 GiB free disk. No `nvidia-smi`, Docker, or Java was found. See [docs/status/LOCAL_ENVIRONMENT.md](../status/LOCAL_ENVIRONMENT.md).

## Runtime profile

Installed only the producer's core and developer dependencies in `/home/anh-khoa/doc-extraction/.venv`; no Docling, EasyOCR, Torch, CUDA package, or model weights were installed. Core parser versions included PyMuPDF 1.28.2, Pydantic 2.13.5, python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, Pillow 12.3.0, and pytest 9.1.1.

| Component | Local status | Evidence / limitation |
|---|---|---|
| Born-digital PDF text | `CPU_READY` | Synthetic one-page native PDF extraction passed on CPU, route `digital_pdf`; wall time 0.0212 s, process peak RSS 104.6 MiB |
| Digital PDF tables | `CPU_READY` | Synthetic ruled table returned the expected 3×3 cells and page 1 locator; wall time 0.0260 s |
| DOCX / XLSX / PPTX native parsing | `CPU_READY` dependency path | Core libraries installed; focused office/parser tests passed. No real benchmark office case was run |
| Native image parsing | `NOT MEASURED` | Image route may invoke optional visual/OCR backends; no OCR package/models installed |
| Docling layout/OCR | `NOT INSTALLED` | Optional dependency plus about 1.5 GB model artifacts according to producer README; not installed on this 8 GiB machine |
| EasyOCR / scanned PDF OCR | `NOT INSTALLED` | Model download and runtime not qualified; CPU scan OCR remains `RESOURCE_BLOCKED` for this stage |
| Tesseract | `NOT AVAILABLE` | `tesseract` executable not found |
| Table Transformer | `NOT INSTALLED` | Optional Torch/Transformers stack; excluded by CPU/RAM policy |
| PaddleOCR, MinerU, VLM | `UNAVAILABLE` | Optional heavy/model or external paths; not installed or evaluated |
| CUDA | `UNAVAILABLE` | No NVIDIA tooling/device observed; no CUDA dependency installed |

The measured PDFs are generated qualification fixtures, not external benchmark documents. They establish the native CPU path and internal output only; they do not establish ExtractionPackage compatibility or live KP interoperability. No memory delta was measured; RSS is the Python process high-water mark.

The core native PDF path uses PyMuPDF, which the producer documents as AGPL-3.0 or commercial-license software. Treat packaging/redistribution as a separate license decision.
