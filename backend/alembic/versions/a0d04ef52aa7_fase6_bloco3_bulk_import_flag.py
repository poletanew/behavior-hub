"""fase6_bloco3_bulk_import_flag

Revision ID: a0d04ef52aa7
Revises: 6a1c2e9d0b3f
Create Date: 2026-07-20 17:29:06.679449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0d04ef52aa7'
down_revision: Union[str, None] = '6a1c2e9d0b3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clinic_permission_settings',
        sa.Column('bulk_import_enabled', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('clinic_permission_settings', 'bulk_import_enabled')
