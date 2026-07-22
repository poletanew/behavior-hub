"""fase6_bloco10_resource_ai_fields

Revision ID: f42cc4c0c8bd
Revises: 4aca9daacefc
Create Date: 2026-07-21 21:53:10.438771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f42cc4c0c8bd'
down_revision: Union[str, None] = '4aca9daacefc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nota: mesmo drift pré-existente e não relacionado sinalizado pelo autogenerate
    # nas migrations anteriores desta fase (FKs use_alter de clinics/users, índices
    # de objectives/sessions) — removido daqui para manter esta migration restrita
    # à mudança pretendida (RF-12).
    op.add_column(
        'resources',
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('resources', sa.Column('ai_reviewed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('resources', 'ai_reviewed_at')
    op.drop_column('resources', 'ai_generated')
