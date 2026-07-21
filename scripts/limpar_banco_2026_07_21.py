"""Exclui todos os usuários EXCETO o super-admin (backend/auth/security.py::CONTAS_SUPER_ADMIN)
e apaga TODOS os BITins (coleção `bitin_contents` no MongoDB) -- pedido explícito do usuário:
"exclui todos os usuários (menos o meu) do banco e os bitins de teste também", confirmado
como "apaga tudo" (usuários + BITins) antes de rodar.

Diferente do script irmão (scripts/resetar_usuarios_setores_2026_07_20.py), este NÃO recria
contas de teste depois -- só limpa, deixando o banco vazio (exceto o super-admin) pra validação
manual do zero.

Uso (mesmo padrão de segurança dos outros scripts de migração -- dry-run por padrão,
`--confirm` obrigatório pra aplicar de verdade):
    .venv/Scripts/python.exe scripts/limpar_banco_2026_07_21.py            # dry-run
    .venv/Scripts/python.exe scripts/limpar_banco_2026_07_21.py --confirm  # aplica
"""

import argparse
import asyncio

import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.auth.models import Usuario
from backend.auth.security import CONTAS_SUPER_ADMIN
from backend.config import settings


def limpar_usuarios(confirmado: bool) -> None:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        alvo = db.query(Usuario).filter(~Usuario.email.in_(CONTAS_SUPER_ADMIN)).all()
        print(f"Usuários a excluir (todos exceto super-admin): {len(alvo)}.")
        for u in alvo:
            print(f"  - id={u.id} {u.email} (permission_level={u.permission_level}, setor='{u.setor}')")

        if confirmado and alvo:
            ids = [u.id for u in alvo]
            placeholders = ", ".join(str(i) for i in ids)
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM sessoes_usuario WHERE usuario_id IN ({placeholders})"))
                conn.commit()
            for u in alvo:
                db.delete(u)
            db.commit()
            print(f" -> {len(alvo)} usuário(s) excluído(s).")
    finally:
        db.close()


async def limpar_bitins(confirmado: bool) -> None:
    client = AsyncIOMotorClient(settings.MONGO_URL, tlsCAFile=certifi.where())
    try:
        colecao = client[settings.MONGO_DB_NAME]["bitin_contents"]
        total = await colecao.count_documents({})
        print(f"\nBITins a excluir (coleção bitin_contents inteira): {total}.")
        if confirmado and total:
            resultado = await colecao.delete_many({})
            print(f" -> {resultado.deleted_count} BITin(s) excluído(s).")
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Aplica a exclusão de verdade")
    args = parser.parse_args()

    modo = "APLICANDO" if args.confirm else "DRY-RUN (nada será alterado; use --confirm pra aplicar)"
    print(f"--- {modo} ---")

    limpar_usuarios(args.confirm)
    asyncio.run(limpar_bitins(args.confirm))

    print("\n--- CONCLUÍDO ---" if args.confirm else "\n--- Nada foi alterado (dry-run) ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
