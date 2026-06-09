"""store_and_source_refactor

Revision ID: 34ed9ac735fa
Revises: f2ff32c1835c
Create Date: 2026-06-10 03:42:14.425995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34ed9ac735fa'
down_revision: Union[str, None] = 'f2ff32c1835c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新建表
    op.create_table('stores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('address', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('inventory_checks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_number', sa.String(length=20), nullable=True),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('check_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_checks_order_number'), 'inventory_checks', ['order_number'], unique=True)
    op.create_table('inventory_check_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('actual_quantity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['check_id'], ['inventory_checks.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('check_id', 'product_id', name='uq_check_product')
    )

    # deliveries: 加 store_id
    with op.batch_alter_table('deliveries') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_deliveries_store_id', 'stores', ['store_id'], ['id'])

    # stock_movements: 加新列
    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.add_column(sa.Column('source_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('source_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('customer_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_stock_movements_store_id', 'stores', ['store_id'], ['id'])
        batch_op.create_foreign_key('fk_stock_movements_customer_id', 'customers', ['customer_id'], ['id'])

    # 回填数据
    op.execute("UPDATE stock_movements SET source_type='delivery', source_id=delivery_id WHERE delivery_id IS NOT NULL")
    op.execute("UPDATE stock_movements SET source_type='purchase', source_id=purchase_order_id WHERE purchase_order_id IS NOT NULL")
    op.execute("UPDATE stock_movements SET source_type='retail', source_id=retail_order_id WHERE retail_order_id IS NOT NULL")
    op.execute("UPDATE stock_movements SET source_type='return', source_id=return_order_id WHERE return_order_id IS NOT NULL")
    op.execute("UPDATE stock_movements SET source_type='wastage', source_id=wastage_order_id WHERE wastage_order_id IS NOT NULL")
    op.execute("UPDATE stock_movements SET source_type='subscription', source_id=subscription_order_id WHERE subscription_order_id IS NOT NULL")

    # stock_movements: 删旧列
    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.drop_column('retail_order_id')
        batch_op.drop_column('subscription_order_id')
        batch_op.drop_column('return_order_id')
        batch_op.drop_column('wastage_order_id')
        batch_op.drop_column('purchase_order_id')
        batch_op.drop_column('delivery_id')

    # transactions: 加新列
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.add_column(sa.Column('source_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('source_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_transactions_store_id', 'stores', ['store_id'], ['id'])

    # 回填数据
    op.execute("UPDATE transactions SET source_type='delivery', source_id=delivery_id WHERE delivery_id IS NOT NULL")
    op.execute("UPDATE transactions SET source_type='purchase', source_id=purchase_order_id WHERE purchase_order_id IS NOT NULL")
    op.execute("UPDATE transactions SET source_type='retail', source_id=retail_order_id WHERE retail_order_id IS NOT NULL")
    op.execute("UPDATE transactions SET source_type='return', source_id=return_order_id WHERE return_order_id IS NOT NULL")
    op.execute("UPDATE transactions SET source_type='subscription', source_id=subscription_order_id WHERE subscription_order_id IS NOT NULL")

    # transactions: 删旧列
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_column('retail_order_id')
        batch_op.drop_column('subscription_order_id')
        batch_op.drop_column('return_order_id')
        batch_op.drop_column('purchase_order_id')
        batch_op.drop_column('delivery_id')


def downgrade() -> None:
    # transactions: 加回旧列
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.add_column(sa.Column('delivery_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('purchase_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('return_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('subscription_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('retail_order_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_txn_delivery', 'deliveries', ['delivery_id'], ['id'])
        batch_op.create_foreign_key('fk_txn_purchase', 'purchase_orders', ['purchase_order_id'], ['id'])
        batch_op.create_foreign_key('fk_txn_retail', 'retail_orders', ['retail_order_id'], ['id'])
        batch_op.create_foreign_key('fk_txn_return', 'return_orders', ['return_order_id'], ['id'])
        batch_op.create_foreign_key('fk_txn_subscription', 'subscription_orders', ['subscription_order_id'], ['id'])

    # 反向回填
    op.execute("UPDATE transactions SET delivery_id=source_id WHERE source_type='delivery'")
    op.execute("UPDATE transactions SET purchase_order_id=source_id WHERE source_type='purchase'")
    op.execute("UPDATE transactions SET retail_order_id=source_id WHERE source_type='retail'")
    op.execute("UPDATE transactions SET return_order_id=source_id WHERE source_type='return'")
    op.execute("UPDATE transactions SET subscription_order_id=source_id WHERE source_type='subscription'")

    # transactions: 删新列
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.drop_column('store_id')
        batch_op.drop_column('source_id')
        batch_op.drop_column('source_type')

    # stock_movements: 加回旧列
    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.add_column(sa.Column('delivery_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('purchase_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('wastage_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('return_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('subscription_order_id', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('retail_order_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_sm_wastage', 'wastage_orders', ['wastage_order_id'], ['id'])
        batch_op.create_foreign_key('fk_sm_return', 'return_orders', ['return_order_id'], ['id'])
        batch_op.create_foreign_key('fk_sm_delivery', 'deliveries', ['delivery_id'], ['id'])
        batch_op.create_foreign_key('fk_sm_purchase', 'purchase_orders', ['purchase_order_id'], ['id'])
        batch_op.create_foreign_key('fk_sm_retail', 'retail_orders', ['retail_order_id'], ['id'])
        batch_op.create_foreign_key('fk_sm_subscription', 'subscription_orders', ['subscription_order_id'], ['id'])

    # 反向回填
    op.execute("UPDATE stock_movements SET delivery_id=source_id WHERE source_type='delivery'")
    op.execute("UPDATE stock_movements SET purchase_order_id=source_id WHERE source_type='purchase'")
    op.execute("UPDATE stock_movements SET retail_order_id=source_id WHERE source_type='retail'")
    op.execute("UPDATE stock_movements SET return_order_id=source_id WHERE source_type='return'")
    op.execute("UPDATE stock_movements SET wastage_order_id=source_id WHERE source_type='wastage'")
    op.execute("UPDATE stock_movements SET subscription_order_id=source_id WHERE source_type='subscription'")

    # stock_movements: 删新列
    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.drop_column('customer_id')
        batch_op.drop_column('store_id')
        batch_op.drop_column('source_id')
        batch_op.drop_column('source_type')

    # deliveries: 删 store_id
    with op.batch_alter_table('deliveries') as batch_op:
        batch_op.drop_constraint('fk_deliveries_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')

    op.drop_table('inventory_check_items')
    op.drop_index(op.f('ix_inventory_checks_order_number'), table_name='inventory_checks')
    op.drop_table('inventory_checks')
    op.drop_table('stores')
