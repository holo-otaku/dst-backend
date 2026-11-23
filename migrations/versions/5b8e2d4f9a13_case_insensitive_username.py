"""users.username 不分大小寫唯一（和 MySQL 的 collation 一樣）

Revision ID: 5b8e2d4f9a13
Revises: 71f1cd61f7d2
Create Date: 2026-10-28 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b8e2d4f9a13'
down_revision = '71f1cd61f7d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('uq_users_username_lower', 'users', [sa.text('lower(username)')], unique=True)


def downgrade():
    op.drop_index('uq_users_username_lower', table_name='users')
