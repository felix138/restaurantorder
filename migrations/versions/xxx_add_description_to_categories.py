"""add description to categories

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-11-03 00:57:22.761

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加 description 字段
    op.add_column('categories', sa.Column('description', sa.Text, nullable=True))

def downgrade():
    # 删除 description 字段
    op.drop_column('categories', 'description') 