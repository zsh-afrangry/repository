from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.tradesim.core.config import settings


tradesim_engine = create_engine(
    settings.MYSQL_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
TradeSimSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tradesim_engine,
)


def get_tradesim_db():
    db = TradeSimSessionLocal()
    try:
        yield db
    finally:
        db.close()


mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = mongo_client[settings.MONGO_DB_NAME]
mongo_collection = mongo_db[settings.MONGO_COLLECTION_LOGS]


def close_tradesim_connections() -> None:
    mongo_client.close()
