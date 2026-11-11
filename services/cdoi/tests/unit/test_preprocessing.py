from pathlib import Path

from cdoi.preprocessing import preprocess


ROOT = Path(__file__).resolve().parents[2]


def test_json_preserves_json_path_and_source_path():
    chunks = preprocess(ROOT / "data/fixtures/finance.json")
    assert chunks
    assert chunks[0].reference.source_path.endswith("finance.json")
    assert chunks[0].reference.source_span.startswith("$.")


def test_markdown_uses_headings_for_structure():
    chunks = preprocess(ROOT / "data/fixtures/incident.md")
    assert any("Runtime" in chunk.reference.hierarchy for chunk in chunks)


def test_plain_text_uses_paragraphs():
    assert len(preprocess(ROOT / "data/fixtures/structured.txt")) == 2
