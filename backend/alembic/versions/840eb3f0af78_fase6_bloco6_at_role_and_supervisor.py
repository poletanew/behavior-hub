"""fase6_bloco6_at_role_and_supervisor

Revision ID: 840eb3f0af78
Revises: 4034a82a11f6
Create Date: 2026-07-21 18:14:18.455765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '840eb3f0af78'
down_revision: Union[str, None] = '4034a82a11f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Novo papel de usuário (Addendum v2.1, RF-11) — autogenerate não detecta
    # valores novos em um enum Postgres já existente, só tipos inteiramente novos.
    op.execute("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'AT'")

    op.add_column('users', sa.Column('supervisor_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_users_supervisor_id', 'users', 'users', ['supervisor_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_users_supervisor_id', 'users', type_='foreignkey')
    op.drop_column('users', 'supervisor_id')
