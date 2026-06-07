"""add wastage_orders

Revision ID: 4f8c814d983b
Revises: 5ace976a1380
Create Date: 2026-06-07 14:15:05.048176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f8c814d983b"
down_revision: Union[str, None] = "5ace976a1380"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 wastage_orders 表（幂等）
    op.execute("""
        CREATE TABLE IF NOT EXISTS wastage_orders (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            note VARCHAR(500) DEFAULT '',
            status VARCHAR(20) DEFAULT 'confirmed',
            created_at DATETIME,
            updated_at DATETIME
        )
    """)

    # --- stock_movements 加 wastage_order_id 列 + FK ---
    op.execute("""
        CREATE TABLE stock_movements_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            direction VARCHAR(10) NOT NULL,
            reason VARCHAR(30) NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price FLOAT,
            delivery_id INTEGER,
            subscription_order_id INTEGER,
            purchase_order_id INTEGER,
            retail_order_id INTEGER,
            return_order_id INTEGER,
            wastage_order_id INTEGER,
            created_at DATETIME,
            FOREIGN KEY(product_id) REFERENCES products (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id),
            FOREIGN KEY(return_order_id) REFERENCES return_orders (id),
            FOREIGN KEY(wastage_order_id) REFERENCES wastage_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO stock_movements_new
            (id, product_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id,
             retail_order_id, return_order_id, created_at)
        SELECT
            id, product_id, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id,
            retail_order_id, return_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_new RENAME TO stock_movements")


def downgrade() -> None:
    # --- stock_movements 去掉 wastage_order_id ---
    op.execute("""
        CREATE TABLE stock_movements_old (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            direction VARCHAR(10) NOT NULL,
            reason VARCHAR(30) NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price FLOAT,
            delivery_id INTEGER,
            subscription_order_id INTEGER,
            purchase_order_id INTEGER,
            retail_order_id INTEGER,
            return_order_id INTEGER,
            created_at DATETIME,
            FOREIGN KEY(product_id) REFERENCES products (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id),
            FOREIGN KEY(return_order_id) REFERENCES return_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO stock_movements_old
            (id, product_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id,
             retail_order_id, return_order_id, created_at)
        SELECT
            id, product_id, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id,
            retail_order_id, return_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_old RENAME TO stock_movements")

    op.execute("DROP TABLE IF EXISTS wastage_orders")
