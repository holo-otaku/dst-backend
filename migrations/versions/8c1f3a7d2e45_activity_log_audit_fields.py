"""activity_log 加上狀態碼、IP、User-Agent

Revision ID: 8c1f3a7d2e45
Revises: 5b8e2d4f9a13
Create Date: 2026-11-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c1f3a7d2e45'
down_revision = '5b8e2d4f9a13'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('activity_log') as batch_op:
        batch_op.add_column(sa.Column('status', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ip', sa.String(length=45), nullable=True))
        batch_op.add_column(sa.Column('user_agent', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('activity_log') as batch_op:
        batch_op.drop_column('user_agent')
        batch_op.drop_column('ip')
        batch_op.drop_column('status')
