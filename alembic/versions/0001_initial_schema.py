"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-13 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app import models

    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app import models

    bind = op.get_bind()
    models.Base.metadata.drop_all(bind=bind)