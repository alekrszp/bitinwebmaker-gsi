from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db = None


db = MongoDB()


async def get_mongo_db():
    return db.db


async def connect_to_mongo() -> None:
    db.client = AsyncIOMotorClient(settings.MONGO_URL)
    db.db = db.client[settings.MONGO_DB_NAME]


async def close_mongo_connection() -> None:
    if db.client:
        db.client.close()
        db.client = None
        db.db = None
