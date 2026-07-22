"""fase6_bloco9_assessment_plan_draft

Revision ID: 4aca9daacefc
Revises: f0f454ff47dd
Create Date: 2026-07-21 21:40:33.761617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aca9daacefc'
down_revision: Union[str, None] = 'f0f454ff47dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nota: mesmo drift pré-existente e não relacionado sinalizado pelo autogenerate
    # nas migrations anteriores desta fase (FKs use_alter de clinics/users, índices
    # de objectives/sessions) — removido daqui para manter esta migration restrita
    # à mudança pretendida (RF-06).
    op.add_column('assessments', sa.Column('ai_generated_plan_draft', sa.JSON(), nullable=True))
    op.add_column('assessments', sa.Column('plan_draft_activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('objectives', sa.Column('ai_source_assessment_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_objectives_ai_source_assessment_id',
        'objectives', 'assessments', ['ai_source_assessment_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_objectives_ai_source_assessment_id', 'objectives', type_='foreignkey')
    op.drop_column('objectives', 'ai_source_assessment_id')
    op.drop_column('assessments', 'plan_draft_activated_at')
    op.drop_column('assessments', 'ai_generated_plan_draft')
