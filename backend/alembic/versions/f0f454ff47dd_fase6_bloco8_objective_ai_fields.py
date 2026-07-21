"""fase6_bloco8_objective_ai_fields

Revision ID: f0f454ff47dd
Revises: 6120d163231c
Create Date: 2026-07-21 19:19:04.098319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0f454ff47dd'
down_revision: Union[str, None] = '6120d163231c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nota: mesmo drift pré-existente e não relacionado sinalizado pelo autogenerate
    # nas migrations anteriores desta fase (FKs use_alter de clinics/users, índices
    # de objectives/sessions) — removido daqui para manter esta migration restrita
    # à mudança pretendida (RF-05).
    op.add_column(
        'objectives',
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('objectives', sa.Column('ai_source_document_id', sa.Uuid(), nullable=True))
    op.add_column('objectives', sa.Column('ai_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_objectives_ai_source_document_id',
        'objectives', 'treatment_plan_attachments', ['ai_source_document_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_objectives_ai_source_document_id', 'objectives', type_='foreignkey')
    op.drop_column('objectives', 'ai_reviewed_at')
    op.drop_column('objectives', 'ai_source_document_id')
    op.drop_column('objectives', 'ai_generated')
