"""add updated_at to orders

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-11-03 22:38:28

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加 updated_at 字段
    op.add_column('orders', sa.Column('updated_at', sa.DateTime, nullable=True))

def downgrade():
    # 删除 updated_at 字段
    op.drop_column('orders', 'updated_at') 