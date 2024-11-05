"""add id to set_meal_items

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-11-03 01:22:34

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 先删除外键约束
    op.execute("""
        ALTER TABLE set_meal_items 
        DROP FOREIGN KEY set_meal_items_ibfk_1,
        DROP FOREIGN KEY set_meal_items_ibfk_2;
    """)
    
    # 删除主键
    op.execute("""
        ALTER TABLE set_meal_items 
        DROP PRIMARY KEY;
    """)
    
    # 添加 id 字段并设置为主键
    op.execute("""
        ALTER TABLE set_meal_items 
        ADD COLUMN id INT AUTO_INCREMENT FIRST,
        ADD PRIMARY KEY (id);
    """)
    
    # 重新添加外键约束
    op.execute("""
        ALTER TABLE set_meal_items
        ADD CONSTRAINT set_meal_items_ibfk_1 
        FOREIGN KEY (set_meal_id) REFERENCES set_meals(id),
        ADD CONSTRAINT set_meal_items_ibfk_2 
        FOREIGN KEY (item_id) REFERENCES items(id);
    """)

def downgrade():
    # 先删除外键约束
    op.execute("""
        ALTER TABLE set_meal_items 
        DROP FOREIGN KEY set_meal_items_ibfk_1,
        DROP FOREIGN KEY set_meal_items_ibfk_2;
    """)
    
    # 删除主键和 id 字段
    op.execute("""
        ALTER TABLE set_meal_items 
        DROP PRIMARY KEY,
        DROP COLUMN id;
    """)
    
    # 重新设置原来的主键和外键约束
    op.execute("""
        ALTER TABLE set_meal_items 
        ADD PRIMARY KEY (set_meal_id, item_id),
        ADD CONSTRAINT set_meal_items_ibfk_1 
        FOREIGN KEY (set_meal_id) REFERENCES set_meals(id),
        ADD CONSTRAINT set_meal_items_ibfk_2 
        FOREIGN KEY (item_id) REFERENCES items(id);
    """)