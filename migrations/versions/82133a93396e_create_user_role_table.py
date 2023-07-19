"""create_user_role_table

Revision ID: 82133a93396e
Revises: ef2a2102dee2
Create Date: 2023-07-19 15:04:21.301119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82133a93396e'
down_revision = 'ef2a2102dee2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user_role',
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('role_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('user_id', 'role_id')
                    )


def downgrade():
    op.drop_table('user_role')
