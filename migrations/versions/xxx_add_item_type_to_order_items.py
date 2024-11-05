"""add item_type to order_items

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-11-03 22:39:14

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加 item_type 字段
    op.add_column('order_items', sa.Column('item_type', sa.String(20), nullable=True))
    
    # 更新现有数据
    op.execute("""
        UPDATE order_items 
        SET item_type = CASE 
            WHEN item_id IS NOT NULL THEN 'item'
            WHEN set_meal_id IS NOT NULL THEN 'set_meal'
            ELSE NULL
        END
    """)
    
    # 将字段设为非空
    op.alter_column('order_items', 'item_type',
                    existing_type=sa.String(20),
                    nullable=False)

def downgrade():
    # 删除 item_type 字段
    op.drop_column('order_items', 'item_type') 