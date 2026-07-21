"""fase6_bloco2_remove_faturamento_sessao

Revision ID: 6a1c2e9d0b3f
Revises: 875225a1f9ac
Create Date: 2026-07-20 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a1c2e9d0b3f'
down_revision: Union[str, None] = '875225a1f9ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Addendum v2.1, RF-08/RF-16: reverte a proposta de Faturamento por Sessão
    # (Fase 5 bloco 3) — a clínica não controla mais cobrança dentro do Behavior Hub.
    op.drop_index(op.f('ix_session_charges_session_id'), table_name='session_charges')
    op.drop_index(op.f('ix_session_charges_patient_id'), table_name='session_charges')
    op.drop_index(op.f('ix_session_charges_individual_owner_id'), table_name='session_charges')
    op.drop_index(op.f('ix_session_charges_id'), table_name='session_charges')
    op.drop_index(op.f('ix_session_charges_clinic_id'), table_name='session_charges')
    op.drop_table('session_charges')
    sa.Enum(name='paymentstatus').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    payment_status = sa.Enum('PENDING', 'PAID', 'OVERDUE', name='paymentstatus')
    payment_status.create(op.get_bind(), checkfirst=True)
    op.create_table('session_charges',
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('clinic_id', sa.Uuid(), nullable=True),
    sa.Column('individual_owner_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('payment_status', payment_status, nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR (clinic_id IS NULL AND individual_owner_id IS NOT NULL)', name='ck_session_charges_single_tenant_owner'),
    sa.CheckConstraint('amount > 0', name='ck_session_charges_amount_positive'),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['individual_owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_charges_clinic_id'), 'session_charges', ['clinic_id'], unique=False)
    op.create_index(op.f('ix_session_charges_id'), 'session_charges', ['id'], unique=False)
    op.create_index(op.f('ix_session_charges_individual_owner_id'), 'session_charges', ['individual_owner_id'], unique=False)
    op.create_index(op.f('ix_session_charges_patient_id'), 'session_charges', ['patient_id'], unique=False)
    op.create_index(op.f('ix_session_charges_session_id'), 'session_charges', ['session_id'], unique=True)
