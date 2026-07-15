"""senha_temporaria em usuarios

Revision ID: 11420a31c617
Revises: 6c6372519927
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11420a31c617'
down_revision: Union[str, Sequence[str], None] = '6c6372519927'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='0' (mesmo padrão de email_verificado na migração anterior,
    # 6c6372519927): sem isso, ADD COLUMN NOT NULL falharia em cima dos 3 usuários já
    # cadastrados no bitin_backend.db real. "0"/False é o valor seguro pra quem já existe --
    # contas antigas não têm senha temporária pendente nenhuma.
    op.add_column(
        'usuarios',
        sa.Column('senha_temporaria', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('usuarios', 'senha_temporaria')
