"""create_role_table

Revision ID: 4d61c9ab0c3c
Revises: ab5943dc6793
Create Date: 2023-07-19 14:59:48.638793

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d61c9ab0c3c'
down_revision = 'ab5943dc6793'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('roles',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )


def downgrade():
    op.drop_table('roles')
