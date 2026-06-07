"""add return_orders

Revision ID: 5ace976a1380
Revises: 8a8999fe4a83
Create Date: 2026-06-07 14:06:57.231532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5ace976a1380"
down_revision: Union[str, None] = "8a8999fe4a83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 return_orders 表（幂等，已存在的场景跳过）
    op.execute("""
        CREATE TABLE IF NOT EXISTS return_orders (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            source_type VARCHAR(20),
            source_order_id INTEGER,
            note VARCHAR(500) DEFAULT '',
            status VARCHAR(20) DEFAULT 'confirmed',
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customers (id)
        )
    """)

    # --- stock_movements 加 return_order_id 列 + FK ---
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
        INSERT INTO stock_movements_new
            (id, product_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id,
             retail_order_id, created_at)
        SELECT
            id, product_id, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id,
            retail_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_new RENAME TO stock_movements")

    # --- transactions 加 return_order_id 列 + FK ---
    op.execute("""
        CREATE TABLE transactions_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            supplier_id INTEGER,
            category VARCHAR(30) NOT NULL,
            amount FLOAT NOT NULL,
            delivery_id INTEGER,
            purchase_order_id INTEGER,
            subscription_order_id INTEGER,
            retail_order_id INTEGER,
            return_order_id INTEGER,
            note VARCHAR(500) DEFAULT '',
            created_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customers (id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id),
            FOREIGN KEY(return_order_id) REFERENCES return_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO transactions_new
            (id, customer_id, supplier_id, category, amount,
             delivery_id, purchase_order_id, subscription_order_id,
             retail_order_id, note, created_at)
        SELECT
            id, customer_id, supplier_id, category, amount,
            delivery_id, purchase_order_id, subscription_order_id,
            retail_order_id, note, created_at
        FROM transactions
    """)
    op.execute("DROP TABLE transactions")
    op.execute("ALTER TABLE transactions_new RENAME TO transactions")


def downgrade() -> None:
    # --- transactions 去掉 return_order_id ---
    op.execute("""
        CREATE TABLE transactions_old (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            supplier_id INTEGER,
            category VARCHAR(30) NOT NULL,
            amount FLOAT NOT NULL,
            delivery_id INTEGER,
            purchase_order_id INTEGER,
            subscription_order_id INTEGER,
            retail_order_id INTEGER,
            note VARCHAR(500) DEFAULT '',
            created_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customers (id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO transactions_old
            (id, customer_id, supplier_id, category, amount,
             delivery_id, purchase_order_id, subscription_order_id,
             retail_order_id, note, created_at)
        SELECT
            id, customer_id, supplier_id, category, amount,
            delivery_id, purchase_order_id, subscription_order_id,
            retail_order_id, note, created_at
        FROM transactions
    """)
    op.execute("DROP TABLE transactions")
    op.execute("ALTER TABLE transactions_old RENAME TO transactions")

    # --- stock_movements 去掉 return_order_id ---
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
            created_at DATETIME,
            FOREIGN KEY(product_id) REFERENCES products (id),
            FOREIGN KEY(delivery_id) REFERENCES deliveries (id),
            FOREIGN KEY(subscription_order_id) REFERENCES subscription_orders (id),
            FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id),
            FOREIGN KEY(retail_order_id) REFERENCES retail_orders (id)
        )
    """)
    op.execute("""
        INSERT INTO stock_movements_old
            (id, product_id, direction, reason, quantity, unit_price,
             delivery_id, subscription_order_id, purchase_order_id,
             retail_order_id, created_at)
        SELECT
            id, product_id, direction, reason, quantity, unit_price,
            delivery_id, subscription_order_id, purchase_order_id,
            retail_order_id, created_at
        FROM stock_movements
    """)
    op.execute("DROP TABLE stock_movements")
    op.execute("ALTER TABLE stock_movements_old RENAME TO stock_movements")

    op.execute("DROP TABLE IF EXISTS return_orders")
