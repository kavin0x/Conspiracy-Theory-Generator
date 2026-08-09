from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

Provider = Literal["openai", "openrouter"]

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4.1-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class Settings:
    provider: Provider
    api_key: str
    model: str
    base_url: str | None = None
    app_url: str = "http://127.0.0.1:5000"
    app_name: str = "Conspiracy Theory Generator"

    @property
    def uses_chat_completions(self) -> bool:
        return self.provider == "openrouter"


def _detect_provider() -> Provider:
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit in ("openai", "openrouter"):
        return explicit  # type: ignore[return-value]
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    return "openai"


def load_settings(*, dotenv: bool = True) -> Settings:
    if dotenv:
        load_dotenv()

    provider = _detect_provider()

    if provider == "openrouter":
        api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set."
            )
        model = (os.getenv("MODEL") or DEFAULT_OPENROUTER_MODEL).strip()
        return Settings(
            provider="openrouter",
            api_key=api_key,
            model=model,
            base_url=OPENROUTER_BASE_URL,
            app_url=(os.getenv("APP_URL") or "http://127.0.0.1:5000").strip(),
            app_name=(os.getenv("APP_NAME") or "Conspiracy Theory Generator").strip(),
        )

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY, or set OPENROUTER_API_KEY / LLM_PROVIDER=openrouter."
        )
    model = (os.getenv("MODEL") or DEFAULT_OPENAI_MODEL).strip()
    return Settings(provider="openai", api_key=api_key, model=model)
