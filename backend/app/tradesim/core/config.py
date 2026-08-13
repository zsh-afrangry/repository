import os
from pathlib import Path

from dotenv import load_dotenv


# The integrated application has one runtime.  TradeSim keeps its own
# configuration namespace so it cannot accidentally reuse KnowledgeMap's
# database or external-service settings.
_BACKEND_DIR = Path(__file__).resolve().parents[3]
load_dotenv(_BACKEND_DIR / ".env")


class Settings:
    MYSQL_URL: str = os.getenv(
        "TRADESIM_MYSQL_URL",
        os.getenv("MYSQL_URL", "mysql+pymysql://root:root@127.0.0.1:3306/tradesim"),
    )
    MONGO_URL: str = os.getenv(
        "TRADESIM_MONGO_URL",
        os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"),
    )
    MONGO_DB_NAME: str = os.getenv("TRADESIM_MONGO_DB_NAME", "tradesim")
    MONGO_COLLECTION_LOGS: str = os.getenv("TRADESIM_MONGO_COLLECTION_LOGS", "simulation_logs")

    LLM_API_KEY: str = os.getenv("TRADESIM_LLM_API_KEY", os.getenv("LLM_API_KEY", ""))
    LLM_MODEL: str = os.getenv("TRADESIM_LLM_MODEL", os.getenv("LLM_MODEL", "qwen-max"))
    LLM_BASE_URL: str = os.getenv(
        "TRADESIM_LLM_BASE_URL",
        os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )


settings = Settings()
