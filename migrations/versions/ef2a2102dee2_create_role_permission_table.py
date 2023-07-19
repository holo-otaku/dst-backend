"""create_role_permission_table

Revision ID: ef2a2102dee2
Revises: bec43b917265
Create Date: 2023-07-19 15:03:36.997280

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef2a2102dee2'
down_revision = 'bec43b917265'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('role_permission',
                    sa.Column('role_id', sa.Integer(), nullable=False),
                    sa.Column('permission_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['permission_id'], ['permissions.id'], ),
                    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
                    sa.PrimaryKeyConstraint('role_id', 'permission_id')
                    )


def downgrade():
    op.drop_table('role_permission')
