"""adjust_ItemAttribute_value_length

Revision ID: 1bc3a5460140
Revises: ceb17bf80564
Create Date: 2023-08-21 13:22:14.823809

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '1bc3a5460140'
down_revision = 'ceb17bf80564'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('field', schema=None) as batch_op:
        batch_op.alter_column('is_required',
                              existing_type=mysql.TINYINT(display_width=1),
                              nullable=False)
        batch_op.alter_column('is_filtered',
                              existing_type=mysql.TINYINT(display_width=1),
                              nullable=False)
    with op.batch_alter_table('item_attribute', schema=None) as batch_op:
        batch_op.alter_column('value',
                              existing_type=sa.String(length=256),
                              nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
