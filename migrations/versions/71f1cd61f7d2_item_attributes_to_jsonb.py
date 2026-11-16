"""item_attribute (EAV) -> item.attributes (jsonb)

Revision ID: 71f1cd61f7d2
Revises: 13fdcde5ad3f
Create Date: 2026-10-28 12:00:00.000000

只支援 PostgreSQL。值的規則同 controller/field_value.stored：
空值不放 key，布林轉成 true/false，其他型別維持原本的字串。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '71f1cd61f7d2'
down_revision = '13fdcde5ad3f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('item', sa.Column(
        'attributes', postgresql.JSONB(), nullable=False, server_default='{}'))
    op.execute("""
        UPDATE item SET attributes = a.attributes
        FROM (
            SELECT ia.item_id, jsonb_object_agg(
                ia.field_id::text,
                CASE WHEN f.data_type = 'boolean' THEN to_jsonb(ia.value = '1') ELSE to_jsonb(ia.value) END
            ) AS attributes
            FROM item_attribute ia JOIN field f ON f.id = ia.field_id
            WHERE ia.value <> ''
            GROUP BY ia.item_id
        ) a
        WHERE item.id = a.item_id
    """)
    op.drop_table('item_attribute')


def downgrade():
    op.create_table(
        'item_attribute',
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('item.id'), primary_key=True),
        sa.Column('field_id', sa.Integer(), sa.ForeignKey('field.id'), primary_key=True),
        sa.Column('value', sa.String(length=256)),
    )
    op.execute("""
        INSERT INTO item_attribute (item_id, field_id, value)
        SELECT item.id, a.key::int,
               CASE WHEN f.data_type = 'boolean' THEN (CASE WHEN a.value = 'true' THEN '1' ELSE '0' END)
                    ELSE a.value END
        FROM item CROSS JOIN LATERAL jsonb_each_text(item.attributes) a
        JOIN field f ON f.id = a.key::int
    """)
    op.drop_column('item', 'attributes')
