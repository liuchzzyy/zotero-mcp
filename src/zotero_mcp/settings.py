"""Configuration management using Pydantic Settings."""

from importlib.metadata import version as _pkg_version

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_version() -> str:
    try:
        return _pkg_version("zotero-mcp")
    except Exception:
        return "0.0.0"


class ZoteroSettings(BaseSettings):
    """Zotero MCP Server settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ZOTERO_",
        extra="ignore",
    )

    server_name: str = Field(default="zotero-mcp")
    server_version: str = Field(default_factory=_get_version)


settings = ZoteroSettings()
