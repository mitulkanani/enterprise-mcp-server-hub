from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Local .env support. Environment variables always take precedence.
load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Enterprise MCP Server Hub")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_path: str = os.getenv("DATABASE_PATH", "./data/mcp_hub.sqlite3")
    resource_server_url: str = os.getenv(
        "MCP_RESOURCE_SERVER_URL", "http://127.0.0.1:8000/mcp"
    )
    issuer_url: str = os.getenv("MCP_ISSUER_URL", "https://identity.example.test")
    allow_local_stdio_identity: bool = _bool("MCP_ALLOW_LOCAL_STDIO_IDENTITY", False)

    @property
    def static_tokens(self) -> dict[str, dict[str, Any]]:
        raw = os.getenv("MCP_STATIC_TOKENS", "{}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("MCP_STATIC_TOKENS must be valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("MCP_STATIC_TOKENS must be a JSON object.")
        return value


settings = Settings()


def ensure_database_directory(path: str) -> None:
    if path != ":memory:":
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
