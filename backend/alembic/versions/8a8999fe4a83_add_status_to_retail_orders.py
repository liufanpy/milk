"""add status to retail_orders

Revision ID: 8a8999fe4a83
Revises: f990044ec06c
Create Date: 2026-06-07 06:22:52.832876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a8999fe4a83'
down_revision: Union[str, None] = 'f990044ec06c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('retail_orders', sa.Column('status', sa.String(length=20), nullable=False, server_default='confirmed'))
    op.add_column('retail_orders', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('retail_orders', 'updated_at')
    op.drop_column('retail_orders', 'status')
