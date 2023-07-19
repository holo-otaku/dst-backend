"""create_series_table

Revision ID: b23ebf856fbc
Revises: 82133a93396e
Create Date: 2023-07-19 15:04:57.472077

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b23ebf856fbc'
down_revision = '82133a93396e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('series',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.Column('created_by', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('status', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('series')
