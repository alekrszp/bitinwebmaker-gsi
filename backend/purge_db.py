"""Apaga TODOS os BITins (Postgres + MongoDB). Uso: --yes é obrigatório, senão só mostra
o que seria apagado (dry-run) -- correção do achado na revisão do backend de referência
(purge_db.py de lá apagava tudo sem nenhuma confirmação nem trava)."""

import argparse
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, text

from backend.config import settings


async def purge(confirmado: bool) -> None:
    modo = "APAGANDO" if confirmado else "DRY-RUN (nada será apagado; use --yes pra confirmar)"
    print(f"--- {modo} ---")

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM bitins")).scalar()
        print(f"Postgres: {count} linha(s) na tabela 'bitins'.")
        if confirmado and count:
            conn.execute(text("DELETE FROM bitins"))
            conn.commit()
            print(f" -> Removidas {count} linha(s).")

    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB_NAME]
    collection = db["bitin_contents"]
    count = await collection.count_documents({})
    print(f"MongoDB: {count} documento(s) em 'bitin_contents'.")
    if confirmado and count:
        result = await collection.delete_many({})
        print(f" -> Removidos {result.deleted_count} documento(s).")
    client.close()

    print("--- CONCLUÍDO ---" if confirmado else "--- Nada foi alterado (dry-run) ---")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Confirma a exclusão de verdade")
    args = parser.parse_args()
    asyncio.run(purge(args.yes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
