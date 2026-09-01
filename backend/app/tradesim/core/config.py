import os
from pathlib import Path

from dotenv import load_dotenv


# TradeSim shares KnowledgeMap's single MySQL connection (app.database) for
# its relational simulation index; this module only holds Mongo/LLM settings.
_BACKEND_DIR = Path(__file__).resolve().parents[3]
load_dotenv(_BACKEND_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _configured(value: str) -> bool:
    return bool(value) and value.lower() not in {"xxx", "your-api-key", "your_api_key"}


def _resolve_llm_config() -> tuple[str, str, str]:
    """Resolve the active OpenAI-compatible provider with legacy support."""
    legacy_key = _env("TRADESIM_LLM_API_KEY")
    legacy_base_url = _env("TRADESIM_LLM_BASE_URL")
    legacy_model = _env("TRADESIM_LLM_MODEL")
    if _configured(legacy_key):
        return (
            legacy_key,
            legacy_base_url or "https://api.deepseek.com",
            legacy_model or "deepseek-chat",
        )

    deepseek_key = _env("DEEPSEEK_API_KEY")
    if _configured(deepseek_key):
        return (
            deepseek_key,
            _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            _env("DEEPSEEK_MODEL", "deepseek-chat"),
        )

    openai_key = _env("OPENAI_API_KEY")
    if _configured(openai_key):
        return (
            openai_key,
            _env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            _env("OPENAI_MODEL", "gpt-4o-mini"),
        )

    return (
        _env("LLM_API_KEY"),
        legacy_base_url or _env("LLM_BASE_URL", "https://api.deepseek.com"),
        legacy_model or _env("LLM_MODEL", "deepseek-chat"),
    )


LLM_API_KEY, LLM_BASE_URL, LLM_MODEL = _resolve_llm_config()


class Settings:
    MONGO_URL: str = _env("TRADESIM_MONGO_URL", _env("MONGO_URL", "mongodb://127.0.0.1:27017"))
    MONGO_DB_NAME: str = _env("TRADESIM_MONGO_DB_NAME", "tradesim")
    MONGO_COLLECTION_LOGS: str = _env("TRADESIM_MONGO_COLLECTION_LOGS", "simulation_logs")

    LLM_API_KEY: str = LLM_API_KEY
    LLM_MODEL: str = LLM_MODEL
    LLM_BASE_URL: str = LLM_BASE_URL


settings = Settings()
