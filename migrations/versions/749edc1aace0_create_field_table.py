"""create_field_table

Revision ID: d009d81be7f2
Revises: 32e4051e9460
Create Date: 2023-07-19 15:06:20.740234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd009d81be7f2'
down_revision = '32e4051e9460'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('field',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=50), nullable=False),
                    sa.Column('data_type', sa.String(
                        length=50), nullable=False),
                    sa.Column('is_required', sa.Boolean(), nullable=True),
                    sa.Column('is_filtered', sa.Boolean(), nullable=True),
                    sa.Column('series_id', sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(['series_id'], ['series.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('field')
