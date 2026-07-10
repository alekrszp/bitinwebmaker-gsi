"""Geração do número sequencial do BITin (P6601/26), só no momento do envio.

Corrige um achado da revisão do backend de referência: gerar o próximo número
(MAX(sequencial)+1) e inserir sem proteção é uma condição de corrida -- dois envios
simultâneos podem calcular o mesmo próximo número. Aqui, a inserção é retentada quando a
constraint 'unique' do código dispara, em vez de estourar um erro pro usuário.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models_sql import BitinSQL

SETOR_PREFIXO = {
    "Proteína Animal": "P",
    "Armazenagem de Grãos": "A",
}

MAX_RETRIES = 5


class SetorInvalido(ValueError):
    pass


def prefixo_para_setor(setor: str) -> str:
    if setor not in SETOR_PREFIXO:
        raise SetorInvalido(
            f"setor {setor!r} inválido — valores aceitos: {', '.join(SETOR_PREFIXO)}"
        )
    return SETOR_PREFIXO[setor]


def gerar_e_salvar_bitin_sql(
    db: Session, setor: str, mongo_document_id: str, criado_por: str | None = None,
) -> BitinSQL:
    prefixo = prefixo_para_setor(setor)
    ano = datetime.now().year % 100

    for _ in range(MAX_RETRIES):
        last_seq = (
            db.query(func.max(BitinSQL.sequencial))
            .filter(BitinSQL.prefixo == prefixo, BitinSQL.ano == ano)
            .scalar()
        )
        next_seq = (last_seq or 0) + 1
        codigo = f"{prefixo}{next_seq}/{ano:02d}"

        bitin_sql = BitinSQL(
            codigo=codigo, prefixo=prefixo, ano=ano, sequencial=next_seq,
            mongo_document_id=mongo_document_id, criado_por=criado_por,
        )
        db.add(bitin_sql)
        try:
            db.commit()
            db.refresh(bitin_sql)
            return bitin_sql
        except IntegrityError:
            db.rollback()
            continue

    raise RuntimeError(
        f"não foi possível gerar um número sequencial único após {MAX_RETRIES} tentativas"
    )
