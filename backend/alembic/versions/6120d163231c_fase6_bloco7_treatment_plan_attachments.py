"""fase6_bloco7_treatment_plan_attachments

Revision ID: 6120d163231c
Revises: 840eb3f0af78
Create Date: 2026-07-21 18:54:58.232678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6120d163231c'
down_revision: Union[str, None] = '840eb3f0af78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nota: o autogenerate também sinalizou drift pré-existente e não relacionado
    # (FKs use_alter de clinics.owner_user_id/users.clinic_id, índice GIN trgm de
    # objectives, índice composto de sessions) — removido daqui para manter esta
    # migration restrita à mudança pretendida (RF-04).
    #
    # Gotcha: `sa.Enum(..., create_type=False)` (o tipo genérico) descarta o kwarg
    # `create_type` silenciosamente — só o `postgresql.ENUM` dialect-specific o
    # respeita. Sem isso, op.create_table tenta recriar o tipo `treatmentarea`
    # (já existente desde Objective.area) e falha com DuplicateObject.
    op.create_table(
        'treatment_plan_attachments',
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column(
            'area',
            postgresql.ENUM(
                'PSICOLOGIA', 'ABA', 'FONOAUDIOLOGIA', 'TERAPIA_OCUPACIONAL', 'PSICOPEDAGOGIA',
                'FISIOTERAPIA', 'NUTRICAO', 'OUTRA', name='treatmentarea', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('file_key', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['treatment_plans.id']),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_treatment_plan_attachments_id'), 'treatment_plan_attachments', ['id'], unique=False)
    op.create_index(op.f('ix_treatment_plan_attachments_plan_id'), 'treatment_plan_attachments', ['plan_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_treatment_plan_attachments_plan_id'), table_name='treatment_plan_attachments')
    op.drop_index(op.f('ix_treatment_plan_attachments_id'), table_name='treatment_plan_attachments')
    op.drop_table('treatment_plan_attachments')
