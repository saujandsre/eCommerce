"""Create orders and order items tables."""
from alembic import op
import sqlalchemy as sa
revision="0001"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    status=sa.Enum("PENDING","CONFIRMED","REJECTED","CANCELLED",name="order_status")
    op.create_table("orders",sa.Column("id",sa.Integer(),autoincrement=True,nullable=False),sa.Column("restaurant_id",sa.Integer(),nullable=False),sa.Column("status",status,nullable=False),sa.Column("total_npr",sa.Numeric(14,2),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),sa.CheckConstraint("total_npr > 0",name="ck_orders_total_positive"),sa.PrimaryKeyConstraint("id"))
    op.create_table("order_items",sa.Column("id",sa.Integer(),autoincrement=True,nullable=False),sa.Column("order_id",sa.Integer(),nullable=False),sa.Column("product_id",sa.Integer(),nullable=False),sa.Column("quantity",sa.Integer(),nullable=False),sa.Column("unit_price_npr",sa.Numeric(12,2),nullable=False),sa.CheckConstraint("quantity > 0",name="ck_order_items_quantity_positive"),sa.CheckConstraint("unit_price_npr > 0",name="ck_order_items_price_positive"),sa.ForeignKeyConstraint(["order_id"],["orders.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_order_items_order_id","order_items",["order_id"])
def downgrade():
    op.drop_index("ix_order_items_order_id",table_name="order_items"); op.drop_table("order_items"); op.drop_table("orders"); sa.Enum(name="order_status").drop(op.get_bind(),checkfirst=True)
