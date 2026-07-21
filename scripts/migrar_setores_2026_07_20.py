"""Migra permission_level/setor dos usuários existentes pro esquema novo (2ª revisão do
modelo de permissões, 2026-07-20 -- ver backend/auth/deps.py NIVEL_INDIVIDUAL/NIVEL_GESTOR/
NIVEL_ADMIN e backend/auth/schemas.py SETOR_CADASTRO/SETOR_PROCESSOS/SETOR_ENGENHARIA).

Esquema ANTIGO: permission_level fixo por papel (66 Usuário, 77 Gestor, 88 Cadastro, 89
Processos, 99 Admin), `setor` era só um rótulo descritivo (cadastro/gestor/usuario/processos)
sem função de acesso.

Esquema NOVO: só 3 ranks (77 Individual, 88 Gestor, 99 Admin), cruzados com `setor`
(cadastro/processos/engenharia) que agora CONTROLA acesso de verdade. Remapeamento (baseado
no permission_level ANTIGO, que era a fonte de verdade -- o `setor` antigo é ignorado de
propósito, era só decorativo):
    66 (Usuário)   -> permission_level=77, setor="engenharia"
    77 (Gestor)    -> permission_level=88, setor="engenharia"
    88 (Cadastro)  -> permission_level=77, setor="cadastro"
    89 (Processos) -> permission_level=77, setor="processos"
    99 (Admin)     -> inalterado (rank já correto; `setor` só é ajustado se o valor atual não
                       for um dos 3 válidos novos, ver ADMIN_SETOR_PADRAO abaixo)

Ninguém vira Gestor de Cadastro/Processos automaticamente (esse conceito não existia antes) --
depois de migrar, promova manualmente quem precisar via Gestão de usuários.

Idempotente (rodar 2x não faz mal: na 2ª vez as condições WHERE não batem com nada, porque já
foram remapeadas -- exceto o ajuste de setor do Admin, que só roda se o valor ainda for
inválido).

Uso (mesmo padrão de segurança de scripts/migrar_niveis_permissao.py -- dry-run por padrão,
`--confirm` obrigatório pra aplicar de verdade):
    .venv/Scripts/python.exe scripts/migrar_setores_2026_07_20.py            # dry-run
    .venv/Scripts/python.exe scripts/migrar_setores_2026_07_20.py --confirm  # aplica de verdade
"""

import argparse

from sqlalchemy import create_engine, text

from backend.config import settings

# (permission_level_antigo) -> (permission_level_novo, setor_novo)
REMAPEAMENTO = {
    66: (77, "engenharia"),
    77: (88, "engenharia"),
    88: (77, "cadastro"),
    89: (77, "processos"),
}

SETORES_VALIDOS_NOVOS = {"cadastro", "processos", "engenharia"}
# Setor padrão pra Admin com um `setor` antigo inválido (ex.: "usuario"/"gestor") -- escolhido
# "engenharia" por ser neutro; ajuste manual depois via Gestão de usuários se o admin real
# trabalhar em Cadastro/Processos (ver Sidebar.tsx::adminCadastro/adminProcessos).
ADMIN_SETOR_PADRAO = "engenharia"


def migrar(confirmado: bool) -> None:
    modo = "APLICANDO" if confirmado else "DRY-RUN (nada será alterado; use --confirm pra aplicar)"
    print(f"--- {modo} ---")

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        for nivel_antigo, (nivel_novo, setor_novo) in REMAPEAMENTO.items():
            count = conn.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE permission_level = :nivel"),
                {"nivel": nivel_antigo},
            ).scalar()
            print(f"permission_level = {nivel_antigo} -> {nivel_novo}, setor -> '{setor_novo}': {count} usuário(s).")
            if confirmado and count:
                conn.execute(
                    text(
                        "UPDATE usuarios SET permission_level = :novo, setor = :setor "
                        "WHERE permission_level = :antigo"
                    ),
                    {"novo": nivel_novo, "setor": setor_novo, "antigo": nivel_antigo},
                )
                conn.commit()
                print(f" -> {count} linha(s) atualizada(s).")

        placeholders = ", ".join(f"'{s}'" for s in SETORES_VALIDOS_NOVOS)
        count_admin = conn.execute(
            text(
                f"SELECT COUNT(*) FROM usuarios WHERE permission_level = 99 "
                f"AND setor NOT IN ({placeholders})"
            )
        ).scalar()
        print(f"Admin (99) com setor antigo inválido -> '{ADMIN_SETOR_PADRAO}': {count_admin} usuário(s).")
        if confirmado and count_admin:
            conn.execute(
                text(
                    f"UPDATE usuarios SET setor = :setor WHERE permission_level = 99 "
                    f"AND setor NOT IN ({placeholders})"
                ),
                {"setor": ADMIN_SETOR_PADRAO},
            )
            conn.commit()
            print(f" -> {count_admin} linha(s) atualizada(s).")

    print("--- CONCLUÍDO ---" if confirmado else "--- Nada foi alterado (dry-run) ---")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Aplica a migração de verdade")
    args = parser.parse_args()
    migrar(args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
