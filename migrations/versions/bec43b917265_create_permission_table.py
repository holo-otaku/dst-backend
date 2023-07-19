"""create_permission_table

Revision ID: bec43b917265
Revises: 4d61c9ab0c3c
Create Date: 2023-07-19 15:03:17.041657

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bec43b917265'
down_revision = '4d61c9ab0c3c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('permissions',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name')
                    )


def downgrade():
    op.drop_table('permissions')
