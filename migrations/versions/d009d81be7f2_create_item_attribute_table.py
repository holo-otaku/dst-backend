"""create_item_attribute_table

Revision ID: 749edc1aace0
Revises: d009d81be7f2
Create Date: 2023-07-19 15:06:59.655852

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '749edc1aace0'
down_revision = 'd009d81be7f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('item_attribute',
                    sa.Column('item_id', sa.Integer(), nullable=False),
                    sa.Column('field_id', sa.Integer(), nullable=False),
                    sa.Column('value', sa.String(length=50), nullable=True),
                    sa.ForeignKeyConstraint(['field_id'], ['field.id'], ),
                    sa.ForeignKeyConstraint(['item_id'], ['item.id'], ),
                    sa.PrimaryKeyConstraint('item_id', 'field_id')
                    )


def downgrade():
    op.drop_table('item_attribute')
