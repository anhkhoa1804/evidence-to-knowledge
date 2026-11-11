"""Safe environment-backed configuration for optional remote model experiments."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values as read_dotenv_values
from dotenv import load_dotenv


@dataclass(frozen=True)
class DotenvState:
    """Secret-free view of process and dotenv credential resolution."""

    process_present: bool
    dotenv_present: bool
    values_equal: bool | None
    dotenv_file_present: bool

    def as_dict(self) -> dict[str, bool | None]:
        return {
            "process_present": self.process_present,
            "dotenv_present": self.dotenv_present,
            "values_equal": self.values_equal,
            "dotenv_file_present": self.dotenv_file_present,
        }


def dotenv_values(path: Path) -> dict[str, str]:
    """Read simple dotenv assignments without echoing their values."""
    return {key: value for key, value in read_dotenv_values(path).items() if value is not None}


def dotenv_state(api_key_env: str, path: Path) -> DotenvState:
    values = dotenv_values(path)
    process_token = os.environ.get(api_key_env)
    dotenv_token = values.get(api_key_env)
    return DotenvState(
        process_present=bool(process_token),
        dotenv_present=bool(dotenv_token),
        values_equal=process_token == dotenv_token if process_token is not None and dotenv_token is not None else None,
        dotenv_file_present=path.exists(),
    )


def load_dotenv_file(path: Path, override: bool = False) -> bool:
    """Optionally load a local dotenv file; process values win by default."""
    return load_dotenv(path, override=override)


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    provider: str
    model: str | None
    base_url: str | None
    api_key_env: str
    host_header: str | None
    base_url_alias: str = "company-ai-gateway"
    temperature: float = 0.0
    max_tokens: int = 256
    config_source: str = "process_environment"

    @classmethod
    def from_environment(cls, config_source: str = "process_environment") -> "OpenAICompatibleConfig":
        return cls(
            provider=os.environ.get("CDOI_LLM_PROVIDER", "openai-compatible"),
            model=os.environ.get("CDOI_LLM_MODEL"),
            base_url=os.environ.get("CDOI_LLM_BASE_URL"),
            api_key_env=os.environ.get("CDOI_LLM_API_KEY_ENV", "DMP_MERCURY"),
            host_header=os.environ.get("CDOI_LLM_HOST_HEADER"),
            temperature=float(os.environ.get("CDOI_LLM_TEMPERATURE", "0")),
            max_tokens=int(os.environ.get("CDOI_LLM_MAX_TOKENS", "256")),
            config_source=config_source,
        )

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)

    def headers(self) -> dict[str, str]:
        return {"Host": self.host_header} if self.host_header else {}

    def public_metadata(self) -> dict[str, object]:
        return {"provider": self.provider, "model": self.model, "base_url_alias": self.base_url_alias, "credential_configured": bool(self.api_key()), "host_header_configured": bool(self.host_header), "temperature": self.temperature, "max_tokens": self.max_tokens, "config_source": self.config_source}
