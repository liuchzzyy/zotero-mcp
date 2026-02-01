"""
PDF to Markdown conversion using PyMuPDF4LLM.

Provides LLM-optimized markdown conversion that:
- Preserves document structure (headings, lists, tables)
- Extracts images with base64 encoding
- Maintains reading order
- Handles multi-column layouts
"""

import logging
from pathlib import Path
from typing import Any

import pymupdf4llm

logger = logging.getLogger(__name__)


class PDFToMarkdownConverter:
    """
    Convert PDF to markdown using PyMuPDF4LLM.

    PyMuPDF4LLM is optimized for LLM consumption:
    - Better structure preservation than raw text extraction
    - Automatic image embedding
    - Table formatting as markdown tables
    - Handles complex layouts
    """

    def to_markdown(
        self,
        pdf_path: Path,
        show_progress: bool = False,
        page_breaks: bool = True,
        extract_images: bool = True,
    ) -> str:
        """
        Convert PDF to markdown.

        Args:
            pdf_path: Path to PDF file
            show_progress: Show conversion progress (default: False)
            page_breaks: Insert page break markers (default: True)
            extract_images: Extract and embed images (default: True)

        Returns:
            Markdown string
        """
        try:
            # Use PyMuPDF4LLM's to_markdown function
            md_text = pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=None,  # All pages
                hdr_info=None,  # Auto-detect headers
                show_progress=show_progress,
                page_breaks=page_breaks,
            )

            return md_text

        except Exception as e:
            logger.error(f"Failed to convert PDF to markdown: {e}")
            raise

    def to_markdown_with_images(
        self,
        pdf_path: Path,
        image_format: str = "base64",
        max_image_size: int = 5 * 1024 * 1024,  # 5MB limit
    ) -> dict[str, Any]:
        """
        Convert PDF to markdown with extracted images.

        Args:
            pdf_path: Path to PDF file
            image_format: 'base64' or 'path'
            max_image_size: Maximum image size in bytes

        Returns:
            Dictionary with 'markdown' and 'images' keys
        """
        result = {
            "markdown": "",
            "images": [],
        }

        try:
            # Convert to markdown with images
            md_text = pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=None,
                hdr_info=None,
                show_progress=False,
                page_breaks=True,
            )

            result["markdown"] = md_text

            # Extract images separately if needed
            if image_format == "base64":
                # Note: PyMuPDF4LLM already embeds images in markdown
                # This is for structured access if needed
                from zotero_mcp.clients.zotero.pdf_extractor import (
                    MultiModalPDFExtractor,
                )

                extractor = MultiModalPDFExtractor()
                elements = extractor.extract_elements(pdf_path, extract_images=True)
                result["images"] = elements["images"]

        except Exception as e:
            logger.error(f"Failed to convert PDF with images: {e}")
            raise

        return result
