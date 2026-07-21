"""Exclui todos os usuários EXCETO o super-admin (backend/auth/security.py::CONTAS_SUPER_ADMIN)
e recria um conjunto de contas de teste cobrindo a estrutura nova de permissões (2ª revisão,
2026-07-20 -- ver backend/auth/deps.py NIVEL_INDIVIDUAL/NIVEL_GESTOR/NIVEL_ADMIN e
backend/auth/schemas.py SETOR_CADASTRO/SETOR_PROCESSOS/SETOR_ENGENHARIA).

Pedido explícito do usuário: "quero que exclua o que já tinha e faça novamente com a nova
estrutura de permissões e setores" -- em vez de migrar os valores antigos (script irmão,
scripts/migrar_setores_2026_07_20.py), este apaga tudo e recomeça do zero.

Cria 6 contas de teste, senha "123" pra todas (mesmo padrão usado em sessões anteriores):
    individual.cadastro@example.com    -- 77, cadastro
    gestor.cadastro@example.com        -- 88, cadastro
    individual.processos@example.com   -- 77, processos
    gestor.processos@example.com       -- 88, processos
    individual.engenharia@example.com  -- 77, engenharia, subgrupo Proteína Animal
    gestor.engenharia@example.com      -- 88, engenharia, subgrupo Armazenagem de Grãos

Subgrupos (Proteína Animal/Armazenagem de Grãos) precisam já existir -- não são recriados
aqui (são um recurso à parte, GET/POST /subgrupos); se nenhum existir ainda, as duas contas
de Engenharia são criadas sem subgrupo (fica pro admin atribuir depois via Gestão de
usuários).

Uso (mesmo padrão de segurança de scripts/migrar_niveis_permissao.py -- dry-run por padrão,
`--confirm` obrigatório pra aplicar de verdade):
    .venv/Scripts/python.exe scripts/resetar_usuarios_setores_2026_07_20.py            # dry-run
    .venv/Scripts/python.exe scripts/resetar_usuarios_setores_2026_07_20.py --confirm  # aplica
"""

import argparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.auth.models import Subgrupo, Usuario
from backend.auth.security import CONTAS_SUPER_ADMIN, get_password_hash
from backend.config import settings

CONTAS_NOVAS = [
    {"email": "individual.cadastro@example.com", "nome": "Individual Cadastro", "permission_level": 77, "setor": "cadastro"},
    {"email": "gestor.cadastro@example.com", "nome": "Gestor Cadastro", "permission_level": 88, "setor": "cadastro"},
    {"email": "individual.processos@example.com", "nome": "Individual Processos", "permission_level": 77, "setor": "processos"},
    {"email": "gestor.processos@example.com", "nome": "Gestor Processos", "permission_level": 88, "setor": "processos"},
    {"email": "individual.engenharia@example.com", "nome": "Individual Engenharia", "permission_level": 77, "setor": "engenharia", "subgrupo_nome": "Proteína Animal"},
    {"email": "gestor.engenharia@example.com", "nome": "Gestor Engenharia", "permission_level": 88, "setor": "engenharia", "subgrupo_nome": "Armazenagem de Grãos"},
]

SENHA_TESTE = "123"


def resetar(confirmado: bool) -> None:
    modo = "APLICANDO" if confirmado else "DRY-RUN (nada será alterado; use --confirm pra aplicar)"
    print(f"--- {modo} ---")

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
            # Sessões primeiro (FK pra usuarios.id) -- raw SQL porque SessaoUsuario não tem
            # relationship com cascade configurado (não precisava até agora).
            placeholders = ", ".join(str(i) for i in ids)
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM sessoes_usuario WHERE usuario_id IN ({placeholders})"))
                conn.commit()
            for u in alvo:
                db.delete(u)
            db.commit()
            print(f" -> {len(alvo)} usuário(s) excluído(s).")

        print(f"\nContas novas a criar: {len(CONTAS_NOVAS)}.")
        for c in CONTAS_NOVAS:
            print(f"  - {c['email']} (permission_level={c['permission_level']}, setor='{c['setor']}')")

        if confirmado:
            for c in CONTAS_NOVAS:
                existente = db.query(Usuario).filter(Usuario.email == c["email"]).first()
                if existente:
                    print(f"  ! {c['email']} já existe, pulando.")
                    continue
                subgrupos = []
                subgrupo_nome = c.get("subgrupo_nome")
                if subgrupo_nome:
                    sub = db.query(Subgrupo).filter(Subgrupo.nome == subgrupo_nome).first()
                    if sub:
                        subgrupos = [sub]
                    else:
                        print(f"  ! Subgrupo '{subgrupo_nome}' não encontrado -- {c['email']} criado sem subgrupo.")
                novo = Usuario(
                    email=c["email"],
                    nome=c["nome"],
                    hashed_password=get_password_hash(SENHA_TESTE),
                    permission_level=c["permission_level"],
                    setor=c["setor"],
                    subgrupos=subgrupos,
                    email_verificado=True,
                    senha_temporaria=False,
                )
                db.add(novo)
            db.commit()
            print(f" -> Contas criadas (senha '{SENHA_TESTE}' pra todas).")
    finally:
        db.close()

    print("--- CONCLUÍDO ---" if confirmado else "--- Nada foi alterado (dry-run) ---")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Aplica a exclusão/recriação de verdade")
    args = parser.parse_args()
    resetar(args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
