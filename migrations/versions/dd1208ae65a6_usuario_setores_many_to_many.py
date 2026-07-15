"""usuario_setores many-to-many

Revision ID: dd1208ae65a6
Revises: 11420a31c617
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd1208ae65a6'
down_revision: Union[str, Sequence[str], None] = '11420a31c617'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Usuario.sector_id (FK única nullable) -> many-to-many, pedido explícito do usuário
    # (2026-07-15): "um usuário poder ser tanto armazenagem tanto quanto proteina". Tabela de
    # associação pura (sem colunas extras além das duas FKs) -- padrão SQLAlchemy pra
    # many-to-many sem payload próprio, ver backend/auth/models.py::usuario_setores.
    op.create_table(
        'usuario_setores',
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('setor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['setor_id'], ['setores.id']),
        sa.PrimaryKeyConstraint('usuario_id', 'setor_id'),
    )

    # Backfill: todo usuário que já tinha um sector_id ganha exatamente essa linha em
    # usuario_setores antes da coluna ser derrubada -- sem isso, a migração perderia dado real
    # (os 3 usuários já cadastrados no bitin_backend.db real têm sector_id preenchido).
    conn = op.get_bind()
    conn.execute(sa.text(
        "INSERT INTO usuario_setores (usuario_id, setor_id) "
        "SELECT id, sector_id FROM usuarios WHERE sector_id IS NOT NULL"
    ))

    # SQLite não suporta DROP COLUMN direto -- precisa do modo batch (recria a tabela por trás
    # dos panos). Primeira migração desta base que dropa uma coluna, por isso é a primeira a
    # precisar de batch_alter_table.
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('sector_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Downgrade é COM PERDA de propósito quando um usuário tem 2+ setores: só um volta pra
    # sector_id (o de menor id, escolha arbitrária mas determinística) -- não tem como um
    # único valor nullable representar "pertence a 2 setores" de novo. Aceitável porque isso
    # só entra em jogo se alguém rodar downgrade depois de já ter usado o many-to-many de
    # verdade (fora do fluxo normal esperado).
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sector_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_usuarios_sector_id_setores', 'setores', ['sector_id'], ['id'])

    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE usuarios SET sector_id = ("
        "  SELECT MIN(setor_id) FROM usuario_setores WHERE usuario_setores.usuario_id = usuarios.id"
        ")"
    ))

    op.drop_table('usuario_setores')
