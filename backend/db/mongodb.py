import certifi
from motor.motor_asyncio import AsyncIOMotorClient

from backend.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db = None


db = MongoDB()


async def get_mongo_db():
    return db.db


async def connect_to_mongo() -> None:
    # tlsCAFile=certifi.where() explícito (2026-07-16, achado ao configurar MongoDB Atlas real
    # pela primeira vez): sem isso, o handshake TLS com o Atlas falhava de forma intermitente
    # nesta máquina (Windows + Python 3.14 + OpenSSL 3.0.18) com
    # "SSL: TLSV1_ALERT_INTERNAL_ERROR" -- o driver caindo no trust store do SO em vez do bundle
    # do certifi parece ser a causa; forçar o bundle do certifi resolveu em todos os testes
    # (antes falhava na maioria das tentativas). Inofensivo contra mongomock-motor (usado nos
    # testes) -- esse client ignora argumentos de TLS por ser só um mock em memória.
    db.client = AsyncIOMotorClient(settings.MONGO_URL, tlsCAFile=certifi.where())
    db.db = db.client[settings.MONGO_DB_NAME]


async def close_mongo_connection() -> None:
    if db.client:
        db.client.close()
        db.client = None
        db.db = None
