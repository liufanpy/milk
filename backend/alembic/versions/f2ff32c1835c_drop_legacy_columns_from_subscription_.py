"""drop legacy columns from subscription_orders

Revision ID: f2ff32c1835c
Revises: e9c7cd0f6068
Create Date: 2026-06-08 03:19:45.725948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2ff32c1835c'
down_revision: Union[str, None] = 'e9c7cd0f6068'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE subscription_orders_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            order_number VARCHAR(20),
            customer_id INTEGER NOT NULL,
            paid_amount FLOAT NOT NULL,
            remaining_amount FLOAT NOT NULL,
            note VARCHAR(500) DEFAULT '',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    op.execute("""
        INSERT INTO subscription_orders_new
            (id, order_number, customer_id, paid_amount, remaining_amount, note, status, created_at)
        SELECT id, order_number, customer_id, paid_amount,
               CAST(remaining_amount AS FLOAT), note, status, created_at
        FROM subscription_orders
    """)
    op.execute("DROP TABLE subscription_orders")
    op.execute("ALTER TABLE subscription_orders_new RENAME TO subscription_orders")
    op.create_index(op.f('ix_subscription_orders_order_number'), 'subscription_orders', ['order_number'], unique=True)


def downgrade() -> None:
    op.execute("""
        CREATE TABLE subscription_orders_old (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            order_number VARCHAR(20),
            customer_id INTEGER NOT NULL,
            paid_amount FLOAT NOT NULL,
            total_bottles INTEGER NOT NULL DEFAULT 0,
            paid_bottles INTEGER,
            free_bottles INTEGER,
            remaining_amount FLOAT NOT NULL,
            note VARCHAR(500) DEFAULT '',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    op.execute("""
        INSERT INTO subscription_orders_old
            (id, order_number, customer_id, paid_amount, total_bottles, remaining_amount, note, status, created_at)
        SELECT id, order_number, customer_id, paid_amount, 0,
               CAST(remaining_amount AS FLOAT), note, status, created_at
        FROM subscription_orders
    """)
    op.execute("DROP TABLE subscription_orders")
    op.execute("ALTER TABLE subscription_orders_old RENAME TO subscription_orders")
    op.create_index(op.f('ix_subscription_orders_order_number'), 'subscription_orders', ['order_number'], unique=True)
