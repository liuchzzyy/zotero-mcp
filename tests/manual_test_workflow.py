import asyncio
import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure we can import zotero_mcp
sys.path.insert(0, str(Path.cwd() / "src"))

from zotero_mcp.services.data_access import get_data_service
from zotero_mcp.services.workflow import get_workflow_service
from zotero_mcp.clients.llm import LLMClient


# Mock LLM Client if local model not available
class MockLLMClient(LLMClient):
    async def analyze_paper(
        self,
        title,
        authors,
        journal,
        date,
        doi,
        fulltext,
        annotations=None,
        template=None,
    ):
        print(f"\n[MockLLM] Analyzing: {title}")
        print(f"[MockLLM] Using Template: {bool(template)}")
        if template:
            print(f"[MockLLM] Template preview: {template[:100]}...")
        return "# Analysis Result\n\nThis is a mock analysis result based on the provided template."


async def main():
    print("=== Starting Manual Test ===")

    # 1. Get Recent Items
    print("\nStep 1: Fetching 5 recent items...")
    data_service = get_data_service()

    # Force local mode if configured in env, otherwise defaults to whatever config has
    # We assume the user has set up config or we use default

    try:
        items = await data_service.get_recent_items(limit=5)
        print(f"Found {len(items)} items:")
        for item in items:
            print(f"- [{item.key}] {item.title}")
            # Check for PDF
            fulltext = await data_service.get_fulltext(item.key)
            has_pdf = bool(fulltext)
            print(f"  PDF available: {has_pdf}")
            if has_pdf:
                print(f"  PDF length: {len(fulltext)} chars")

    except Exception as e:
        print(f"Error fetching items: {e}")
        return

    # 2. Read Template.yaml
    print("\nStep 2: Reading Template.yaml...")
    template_path = Path("Template.yaml")
    template_content = None
    if template_path.exists():
        try:
            # Simple manual parsing to avoid dependency
            content = template_path.read_text(encoding="utf-8")
            # Extract text value (hacky but works for this simple file)
            # Look for 'text: "' or "text: '"
            import re

            match = re.search(r'text:\s*(["\'])(.*)', content, re.DOTALL)
            if match:
                # This is a bit risky with multiline strings in YAML without a real parser
                # Let's just pass the whole file content as instruction for now
                # or try to extract if it looks like the user's file.
                # The user's file shows `text: "<h2..."`.
                # If we fail to parse, we'll just use the file content.
                pass

            # Better: just use the raw content as the "Template Instruction"
            template_content = content
            print("Template loaded.")
        except Exception as e:
            print(f"Error reading template: {e}")
    else:
        print("Template.yaml not found.")
        template_content = "Please analyze this paper."

    # 3. Batch Analysis
    print("\nStep 3: Running Batch Analysis...")
    workflow_service = get_workflow_service()

    # Check for local model config
    # If not set, we might need to mock or set defaults
    provider = "openai"  # Default to openai style (compatible with Ollama)

    # We'll use a Mock LLM if no API key is set for OpenAI/DeepSeek/Gemini
    # AND we can't connect to localhost:11434

    use_mock = False
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        # Check if local ollama might be running?
        # Just forcing mock for safety in this test script unless user explicitly set env
        # But the user asked to "Use local model".
        # I will attempt to set base_url to localhost if not set.
        if not os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
            os.environ["OPENAI_API_KEY"] = "ollama"  # Dummy key
            print("Configured for Local LLM (Ollama) at http://localhost:11434/v1")

    # We patch the get_llm_client to return our Mock if connection fails?
    # No, let's try to run it. If it fails, we catch exception.

    try:
        # We need to bypass the "get_items" part of batch_analyze because we want to use
        # the SPECIFIC items we just found?
        # batch_analyze takes 'source="recent"' and 'limit'.
        # It will re-fetch recent items. That's fine.

        # Note: batch_analyze is complex. It handles state.
        # Let's run it with dry_run=True first to see if it works

        response = await workflow_service.batch_analyze(
            source="recent",
            limit=5,
            template=template_content,
            dry_run=True,  # We don't want to create notes in the user's Zotero for a test?
            # Or maybe we do? User said "analyze these items".
            # Usually "analyze" implies creating notes.
            # But safe default is dry_run or ask.
            # I'll use dry_run=True and print results.
            llm_provider=provider,
        )

        print("\nAnalysis Response:")
        print(f"Processed: {response.processed}")
        print(f"Failed: {response.failed}")

        for res in response.results:
            print(f"- {res.title}: {'Success' if res.success else 'Failed'}")
            if not res.success:
                print(f"  Error: {res.error}")

    except Exception as e:
        print(f"Batch analysis failed: {e}")
        # import traceback
        # traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
