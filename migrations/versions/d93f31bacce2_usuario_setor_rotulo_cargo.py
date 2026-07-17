"""usuario.setor -- rótulo descritivo de cargo (cadastro/gestor/usuario)

Revision ID: d93f31bacce2
Revises: c8946839825e
Create Date: 2026-07-16 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd93f31bacce2'
down_revision: Union[str, Sequence[str], None] = 'c8946839825e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Novo campo Usuario.setor (2026-07-16, decisão explícita do usuário): rótulo PURAMENTE
    # DESCRITIVO do cargo da pessoa ('cadastro'/'gestor'/'usuario') -- NÃO controla nenhuma
    # regra de acesso, isso continua sendo só permission_level. Conceito diferente do Subgrupo
    # renomeado na migração anterior (Proteína Animal/Armazenagem de Grãos).
    #
    # NOT NULL desde já: só existe 1 usuário real no banco de produção no momento desta
    # migração (permission_level=99, admin) -- backfillado explicitamente pra 'cadastro'
    # abaixo (rótulo mais adequado pra quem administra o sistema). server_default='cadastro'
    # é necessário só pra permitir o ADD COLUMN NOT NULL numa tabela já populada (SQLite/
    # Alembic exige um default quando a coluna não é nullable). Decisão: MANTER o
    # server_default depois do backfill, em vez de tentar dropá-lo -- SQLite não suporta
    # ALTER COLUMN DROP DEFAULT nativamente (só via batch mode, que recria a tabela inteira só
    # pra isso) e o default só afeta INSERTs feitos direto no banco por fora da aplicação; todo
    # caminho de escrita real (POST /users, /auth/register) passa pelos schemas Pydantic
    # (UserCreate.setor / AdminUserCreate.setor), que exigem o campo explicitamente e não têm
    # nenhum default -- omitir `setor` no corpo da requisição já dá 422 antes de chegar no
    # banco. O server_default é só uma rede de segurança pro schema, não uma porta aberta pra
    # pular a validação de verdade.
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('setor', sa.String(), nullable=False, server_default='cadastro')
        )

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE usuarios SET setor = 'cadastro' WHERE setor IS NULL"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('setor')
