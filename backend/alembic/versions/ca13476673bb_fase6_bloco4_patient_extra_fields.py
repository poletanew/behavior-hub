"""fase6_bloco4_patient_extra_fields

Revision ID: ca13476673bb
Revises: a0d04ef52aa7
Create Date: 2026-07-20 17:40:36.812905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca13476673bb'
down_revision: Union[str, None] = 'a0d04ef52aa7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('address', sa.String(length=500), nullable=True))
    op.add_column('patients', sa.Column('phone', sa.String(length=30), nullable=True))
    op.add_column('patients', sa.Column('school_name', sa.String(length=255), nullable=True))
    school_shift = sa.Enum('MANHA', 'TARDE', 'INTEGRAL', 'NAO_FREQUENTA', name='schoolshift')
    school_shift.create(op.get_bind(), checkfirst=True)
    op.add_column('patients', sa.Column('school_shift', school_shift, nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'school_shift')
    op.drop_column('patients', 'school_name')
    op.drop_column('patients', 'phone')
    op.drop_column('patients', 'address')
    sa.Enum(name='schoolshift').drop(op.get_bind(), checkfirst=True)
