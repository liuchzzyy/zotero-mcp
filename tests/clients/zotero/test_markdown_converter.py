"""
Tests for PDF to Markdown converter using PyMuPDF4LLM.
"""

from pathlib import Path

import pytest

from zotero_mcp.clients.zotero.markdown_converter import PDFToMarkdownConverter

# Use pytest skip if no test PDF is available
PDF_PATH = Path("tests/fixtures/sample.pdf")


@pytest.mark.skipif(not PDF_PATH.exists(), reason=f"Test PDF not found at {PDF_PATH}")
def test_convert_pdf_to_markdown():
    """Test PDF to markdown conversion with PyMuPDF4LLM"""
    converter = PDFToMarkdownConverter()

    result = converter.to_markdown(PDF_PATH)

    assert isinstance(result, str)
    assert len(result) > 0
    # Markdown should contain headings, text, etc.
    assert "#" in result or "##" in result


@pytest.mark.skipif(not PDF_PATH.exists(), reason=f"Test PDF not found at {PDF_PATH}")
def test_convert_with_page_breaks():
    """Test conversion preserves page structure"""
    converter = PDFToMarkdownConverter()

    result = converter.to_markdown(
        PDF_PATH,
        show_progress=False,
        page_breaks=True,
    )

    assert "---" in result  # Page breaks in markdown


def test_converter_instantiation():
    """Test that converter can be instantiated"""
    converter = PDFToMarkdownConverter()
    assert converter is not None
    assert hasattr(converter, "to_markdown")
    assert hasattr(converter, "to_markdown_with_images")
