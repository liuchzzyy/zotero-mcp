"""
Tests for LLM capability detection system.
"""

from zotero_mcp.clients.llm.capabilities import (
    get_provider_capability,
)


def test_deepseek_capability():
    """Test DeepSeek is text-only"""
    cap = get_provider_capability("deepseek")

    assert not cap.supports_images
    assert cap.supports_text
    assert cap.max_input_tokens > 0


def test_claude_cli_capability():
    """Test Claude CLI supports vision"""
    cap = get_provider_capability("claude-cli")

    assert cap.supports_images
    assert cap.supports_text


def test_openai_capability():
    """Test OpenAI supports vision"""
    cap = get_provider_capability("openai")

    assert cap.supports_images
    assert cap.supports_text


def test_gemini_capability():
    """Test Gemini supports vision"""
    cap = get_provider_capability("gemini")

    assert cap.supports_images
    assert cap.supports_text


def test_capability_check():
    """Test capability checking"""
    cap = get_provider_capability("deepseek")

    assert not cap.can_handle_images()
    assert cap.can_handle_text()


def test_is_multimodal():
    """Test multi-modal detection"""
    deepseek = get_provider_capability("deepseek")
    claude = get_provider_capability("claude-cli")

    assert not deepseek.is_multimodal()
    assert claude.is_multimodal()


def test_unknown_provider():
    """Test unknown provider raises error"""
    try:
        get_provider_capability("unknown-provider")
        raise AssertionError("Should raise ValueError")
    except ValueError as e:
        assert "Unknown provider" in str(e)
        assert "unknown-provider" in str(e)
