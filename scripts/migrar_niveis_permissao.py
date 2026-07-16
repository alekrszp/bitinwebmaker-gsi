"""Migra permission_level dos usuários existentes do esquema antigo (0 = usuário, 1 = gestor,
99 = admin) pro novo esquema de 4 níveis (66 = usuário, 77 = gestor, 88 = cadastro, 99 = admin
-- ver backend/auth/deps.py NIVEL_*, revisão do modelo de permissões de 2026-07-16).

Só remapeia 0->66 e 1->77; 99 fica como está (admin não muda). Não existe usuário 88 (Cadastro)
antes desta migração -- é um nível novo, ninguém precisa ser remapeado pra ele aqui.

DADOS, não schema: a coluna já é um Integer simples, sem migração de tipo/shape necessária --
só o VALOR de linhas existentes precisa mudar. Idempotente (rodar 2x não faz mal: na 2ª vez as
condições WHERE permission_level = 0/1 não batem com nada, porque já foram remapeadas).

Uso (mesmo padrão de segurança de backend/purge_db.py -- dry-run por padrão, `--confirm`
obrigatório pra aplicar de verdade):
    .venv/Scripts/python.exe scripts/migrar_niveis_permissao.py           # dry-run
    .venv/Scripts/python.exe scripts/migrar_niveis_permissao.py --confirm  # aplica de verdade
"""

import argparse

from sqlalchemy import create_engine, text

from backend.config import settings

REMAPEAMENTO = {0: 66, 1: 77}  # 99 (admin) não entra aqui -- fica como está


def migrar(confirmado: bool) -> None:
    modo = "APLICANDO" if confirmado else "DRY-RUN (nada será alterado; use --confirm pra aplicar)"
    print(f"--- {modo} ---")

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        for nivel_antigo, nivel_novo in REMAPEAMENTO.items():
            count = conn.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE permission_level = :nivel"),
                {"nivel": nivel_antigo},
            ).scalar()
            print(f"permission_level = {nivel_antigo} -> {nivel_novo}: {count} usuário(s).")
            if confirmado and count:
                conn.execute(
                    text("UPDATE usuarios SET permission_level = :novo WHERE permission_level = :antigo"),
                    {"novo": nivel_novo, "antigo": nivel_antigo},
                )
                conn.commit()
                print(f" -> {count} linha(s) atualizada(s).")

    print("--- CONCLUÍDO ---" if confirmado else "--- Nada foi alterado (dry-run) ---")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Aplica a migração de verdade")
    args = parser.parse_args()
    migrar(args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
