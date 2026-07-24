"""assessment_protocol_socially_savvy

Revision ID: a9ff88b1975d
Revises: 7d4791e34107
Create Date: 2026-07-24 14:13:16.321092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9ff88b1975d'
down_revision: Union[str, None] = '7d4791e34107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pré-lançamento: nenhuma clínica real usa ABLLS-R ainda neste banco, mas
    # removemos qualquer avaliação de teste com esse protocolo antes de trocar
    # o tipo enum (domain_code de ABLLS-R não existe em Socially Savvy).
    op.execute("DELETE FROM assessments WHERE protocol = 'ABLLS_R'")
    op.execute("ALTER TYPE assessmentprotocol RENAME TO assessmentprotocol_old")
    op.execute("CREATE TYPE assessmentprotocol AS ENUM ('VB_MAPP', 'SOCIALLY_SAVVY')")
    op.execute("ALTER TABLE assessments ALTER COLUMN protocol DROP DEFAULT")
    op.execute(
        "ALTER TABLE assessments ALTER COLUMN protocol TYPE assessmentprotocol "
        "USING protocol::text::assessmentprotocol"
    )
    op.execute("DROP TYPE assessmentprotocol_old")


def downgrade() -> None:
    op.execute("DELETE FROM assessments WHERE protocol = 'SOCIALLY_SAVVY'")
    op.execute("ALTER TYPE assessmentprotocol RENAME TO assessmentprotocol_new")
    op.execute("CREATE TYPE assessmentprotocol AS ENUM ('VB_MAPP', 'ABLLS_R')")
    op.execute(
        "ALTER TABLE assessments ALTER COLUMN protocol TYPE assessmentprotocol "
        "USING protocol::text::assessmentprotocol"
    )
    op.execute("DROP TYPE assessmentprotocol_new")
