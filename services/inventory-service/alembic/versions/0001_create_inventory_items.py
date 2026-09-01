"""Create inventory items table."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("inventory_items", sa.Column("product_id", sa.Integer(), nullable=False), sa.Column("sku", sa.String(100), nullable=False), sa.Column("quantity_available", sa.Integer(), nullable=False), sa.Column("quantity_reserved", sa.Integer(), nullable=False), sa.CheckConstraint("quantity_available >= 0", name="ck_inventory_available_nonnegative"), sa.CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_nonnegative"), sa.PrimaryKeyConstraint("product_id"), sa.UniqueConstraint("sku"))
def downgrade() -> None: op.drop_table("inventory_items")
