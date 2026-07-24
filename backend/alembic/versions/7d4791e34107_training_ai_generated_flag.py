"""training_ai_generated_flag

Revision ID: 7d4791e34107
Revises: e44599f16618
Create Date: 2026-07-24 03:01:12.544464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d4791e34107'
down_revision: Union[str, None] = 'e44599f16618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trainings',
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('trainings', 'ai_generated')
