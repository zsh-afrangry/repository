from motor.motor_asyncio import AsyncIOMotorClient

from app.tradesim.core.config import settings


mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = mongo_client[settings.MONGO_DB_NAME]
mongo_collection = mongo_db[settings.MONGO_COLLECTION_LOGS]


def close_tradesim_connections() -> None:
    mongo_client.close()
