from zotero_mcp.utils.formatting.helpers import is_local_mode


def test_is_local_mode_defaults_to_false(monkeypatch):
    monkeypatch.delenv("ZOTERO_LOCAL", raising=False)
    assert is_local_mode() is False


def test_is_local_mode_honors_false(monkeypatch):
    monkeypatch.setenv("ZOTERO_LOCAL", "false")
    assert is_local_mode() is False


def test_is_local_mode_honors_true(monkeypatch):
    monkeypatch.setenv("ZOTERO_LOCAL", "true")
    assert is_local_mode() is True
