"""create_user_table

Revision ID: ab5943dc6793
Revises: 
Create Date: 2023-07-19 14:57:29.909338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab5943dc6793'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('username', sa.String(
                        length=50), nullable=False),
                    sa.Column('password', sa.String(
                        length=128), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('username')
                    )


def downgrade():
    op.drop_table('users')
