"""fase6_bloco5_training_patient_link

Revision ID: 4034a82a11f6
Revises: ca13476673bb
Create Date: 2026-07-21 17:58:01.497155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4034a82a11f6'
down_revision: Union[str, None] = 'ca13476673bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('training_patient_links',
    sa.Column('training_id', sa.Uuid(), nullable=False),
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('linked_by_user_id', sa.Uuid(), nullable=False),
    sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('PRESCRIBED', 'APPLIED', name='traininglinkstatus'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['linked_by_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['training_id'], ['trainings.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('training_id', 'patient_id', name='uq_training_patient_link')
    )
    op.create_index(op.f('ix_training_patient_links_id'), 'training_patient_links', ['id'], unique=False)
    op.create_index(op.f('ix_training_patient_links_patient_id'), 'training_patient_links', ['patient_id'], unique=False)
    op.create_index(op.f('ix_training_patient_links_training_id'), 'training_patient_links', ['training_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_training_patient_links_training_id'), table_name='training_patient_links')
    op.drop_index(op.f('ix_training_patient_links_patient_id'), table_name='training_patient_links')
    op.drop_index(op.f('ix_training_patient_links_id'), table_name='training_patient_links')
    op.drop_table('training_patient_links')
    sa.Enum(name='traininglinkstatus').drop(op.get_bind(), checkfirst=True)
