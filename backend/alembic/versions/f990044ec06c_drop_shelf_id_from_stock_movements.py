"""drop shelf_id from stock_movements

Revision ID: f990044ec06c
Revises: efc0d6de8e2f
Create Date: 2026-06-07 03:55:05.776483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f990044ec06c'
down_revision: Union[str, None] = 'efc0d6de8e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 的 ALTER TABLE DROP COLUMN 不会自动清理外键约束，
    # 需要重建整个表来同时删除 shelf_id 列和对应的 FK 约束
    op.execute("""
        CREATE TABLE stock_movements_new (
            id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            direction VARCHAR(10) NOT NULL,
            reason VARCHAR(30) NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price FLOAT,
            delivery_id INTEGER,
            subscription_order_id INTEGER,
            purchase_order_id INTEGER,
            retail_order_id INTEGER,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(product_id) REFERENCES products (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO stock_movements_new
            (id, product_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id, retail_order_id, created_at)
        SELECT
            id, product_id, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id, retail_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_new RENAME TO stock_movements")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE stock_movements_old (
            id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            shelf_id INTEGER NOT NULL,
            direction VARCHAR(10) NOT NULL,
            reason VARCHAR(30) NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price FLOAT,
            delivery_id INTEGER,
            subscription_order_id INTEGER,
            purchase_order_id INTEGER,
            retail_order_id INTEGER,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(product_id) REFERENCES products (id),
            FOREIGN KEY(shelf_id) REFERENCES shelves (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO stock_movements_old
            (id, product_id, shelf_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id, retail_order_id, created_at)
        SELECT
            id, product_id, 0, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id, retail_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_old RENAME TO stock_movements")
