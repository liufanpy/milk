"""add _items_json to purchase_orders

Revision ID: fd8619064486
Revises: 4f8c814d983b
Create Date: 2026-06-08 01:25:02.393695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd8619064486'
down_revision: Union[str, None] = '4f8c814d983b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_orders', sa.Column('_items_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('purchase_orders', '_items_json')
