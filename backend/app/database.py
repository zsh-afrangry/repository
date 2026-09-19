import os
from pathlib import Path
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR / ".env")


def _build_database_url() -> str:
    """组装 MySQL 连接串。

    优先级：
    1. `DATABASE_URL` / `MYSQL_URL` —— 整串连接串，保留给部署环境（最高优先级）；
    2. 由分项配置拼装 —— 键名沿用 .env 里既有的 `MySQL_USER` / `MySQL_PASSWORD`
       大小写，另外支持 `MySQL_HOST` / `MySQL_PORT` / `MySQL_DATABASE`。
       用户名列与密码列都做 URL 转义，避免密码里的 @ : / 等字符把连接串拆坏。

    在 2026-09-20 之前，`MySQL_USER` / `MySQL_PASSWORD` 两个键虽然写在 .env 里，
    却没有任何代码读取，实际连接一律走下面的默认值。现在它们真正生效了；
    默认值与改动前的硬编码值完全一致（root:root@127.0.0.1:3306/knowledgemap），
    因此这是一次行为等价的规范化。
    """
    explicit_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if explicit_url:
        return explicit_url

    user = quote_plus(os.getenv("MySQL_USER", "root"))
    password = quote_plus(os.getenv("MySQL_PASSWORD", "root"))
    host = os.getenv("MySQL_HOST", "127.0.0.1")
    port = os.getenv("MySQL_PORT", "3306")
    database = os.getenv("MySQL_DATABASE", "knowledgemap")
    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    )


DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
