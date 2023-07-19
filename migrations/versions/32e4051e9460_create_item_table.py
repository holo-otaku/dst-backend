"""create_item_table

Revision ID: 32e4051e9460
Revises: b23ebf856fbc
Create Date: 2023-07-19 15:06:01.118097

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32e4051e9460'
down_revision = 'b23ebf856fbc'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('item',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('series_id', sa.Integer(), nullable=True),
                    sa.Column('name', sa.String(length=50), nullable=True),
                    sa.ForeignKeyConstraint(['series_id'], ['series.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('item')
