"""rename Setor para Subgrupo (setores/usuario_setores -> subgrupos/usuario_subgrupos)

Revision ID: c8946839825e
Revises: dd1208ae65a6
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8946839825e'
down_revision: Union[str, Sequence[str], None] = 'dd1208ae65a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Renomeia Setor -> Subgrupo (2026-07-16): o nome "Setor" passou a colidir com o novo
    # campo Usuario.setor (rótulo descritivo de cargo cadastro/gestor/usuario, ver a próxima
    # migração) -- são dois conceitos diferentes (este continua sendo Proteína Animal/
    # Armazenagem de Grãos) e precisavam de nomes diferentes. SQLite suporta rename de tabela
    # direto via op.rename_table, sem precisar de batch mode (batch mode só é necessário pra
    # DROP/ALTER COLUMN em SQLite).
    op.rename_table('setores', 'subgrupos')
    op.rename_table('usuario_setores', 'usuario_subgrupos')

    # A coluna da tabela de associação também se chamava setor_id -- renomeia pra subgrupo_id
    # pra consistência com o resto (SQLite precisa de batch mode pra renomear coluna).
    with op.batch_alter_table('usuario_subgrupos', schema=None) as batch_op:
        batch_op.alter_column('setor_id', new_column_name='subgrupo_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('usuario_subgrupos', schema=None) as batch_op:
        batch_op.alter_column('subgrupo_id', new_column_name='setor_id')

    op.rename_table('usuario_subgrupos', 'usuario_setores')
    op.rename_table('subgrupos', 'setores')
