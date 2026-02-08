"""
Paper Analyzer integration.

Wraps internal analyzer for use in the MCP integration layer.
"""

from __future__ import annotations

from typing import Any

from zotero_mcp.config import Config


class AnalyzerIntegration:
    """Bridges analyzer module into zotero-mcp."""

    def __init__(self, config: Config):
        from zotero_mcp.analyzer import PDFAnalyzer, PDFExtractor
        from zotero_mcp.analyzer.templates import TemplateManager

        # Build LLM client based on provider
        llm_client = self._create_llm_client(config)
        self.analyzer = PDFAnalyzer(
            llm_client=llm_client,
            template_manager=TemplateManager(),
            extractor=PDFExtractor(),
        )
        self._config = config

    @staticmethod
    def _create_llm_client(config: Config):
        """Create the appropriate LLM client."""
        if config.llm_provider == "openai":
            from zotero_mcp.analyzer.clients import OpenAIClient

            return OpenAIClient(
                api_key=config.llm_api_key,
                base_url=config.llm_base_url or "https://api.openai.com/v1",
                model=config.llm_model,
            )
        else:
            from zotero_mcp.analyzer.clients import DeepSeekClient

            return DeepSeekClient(
                api_key=config.llm_api_key,
                model=config.llm_model or "deepseek-chat",
            )

    async def analyze_pdf(
        self,
        file_path: str,
        template_name: str = "default",
        extract_images: bool = False,
    ) -> dict[str, Any]:
        """Analyze a PDF file directly."""
        result = await self.analyzer.analyze(
            file_path=file_path,
            template_name=template_name,
            extract_images=extract_images,
        )
        return {
            "summary": result.summary,
            "key_points": result.key_points,
            "methodology": result.methodology,
            "conclusions": result.conclusions,
            "llm_provider": result.llm_provider,
            "model": result.model,
            "processing_time": result.processing_time,
            "raw_output": result.raw_output,
        }

    async def analyze_text(
        self,
        text: str,
        title: str = "Untitled",
        template_name: str = "default",
    ) -> dict[str, Any]:
        """Analyze pre-extracted text."""
        result = await self.analyzer.analyze_text(
            text=text,
            title=title,
            template_name=template_name,
        )
        return {
            "summary": result.summary,
            "key_points": result.key_points,
            "methodology": result.methodology,
            "conclusions": result.conclusions,
            "llm_provider": result.llm_provider,
            "model": result.model,
            "processing_time": result.processing_time,
            "raw_output": result.raw_output,
        }

    @staticmethod
    def format_result(result: dict[str, Any]) -> str:
        """Format analysis result as Markdown."""
        lines = [
            "## Analysis Result\n",
            f"**Provider**: {result.get('llm_provider', 'N/A')}",
            f"**Model**: {result.get('model', 'N/A')}",
            f"**Time**: {result.get('processing_time', 0):.1f}s\n",
        ]

        if result.get("summary"):
            lines.append("### Summary")
            lines.append(result["summary"])
            lines.append("")

        if result.get("key_points"):
            lines.append("### Key Points")
            for point in result["key_points"]:
                lines.append(f"- {point}")
            lines.append("")

        if result.get("methodology"):
            lines.append("### Methodology")
            lines.append(result["methodology"])
            lines.append("")

        if result.get("conclusions"):
            lines.append("### Conclusions")
            lines.append(result["conclusions"])
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_batch_results(results: list[dict[str, Any]]) -> str:
        """Format batch analysis results."""
        lines = [f"## Batch Analysis: {len(results)} papers\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"### Paper {i}")
            if r.get("summary"):
                lines.append(r["summary"][:200])
            lines.append("")
        return "\n".join(lines)
